"""Rebuild this game's retail PKG for RPCS3; default is a read-only plan.

Preserves the source CTR IV, payload start and all untouched payload bytes.
This does not sign a retail package. The original authentication fields are
retained as opaque bytes and are INVALID for the rebuilt content. No console
compatibility is claimed. RPCS3 installation/boot requires a separate test.

Format/loader reference: RPCS3/rpcs3, Crypto/unpkg.cpp and Emu/System.cpp.
No personal license files are read or needed.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import struct

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from pkg_read import Package, PKG_KEY

CHUNK = 4 * 1024 * 1024
CONTENT_ID = 'JP0048-NPJB00162_00-WIZDL0000000BLUR'


def sha_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk := stream.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def safe_name(name):
    if (not isinstance(name, str) or not name or name.startswith('/')
            or '\\' in name or ':' in name or '\0' in name
            or any(p in ('', '.', '..') for p in name.split('/'))):
        raise ValueError('Unsafe overlay path')
    return name


def align16(value):
    return (value + 15) & ~15


def package_hash(pkg, entry):
    digest = hashlib.sha256()
    for at in range(0, entry['size'], CHUNK):
        digest.update(pkg.read(entry['offset'] + at, min(CHUNK, entry['size'] - at)))
    return digest.hexdigest()


def plan(original, build):
    original, build = Path(original).resolve(), Path(build).resolve()
    manifest_path = build / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf8'))
    if manifest.get('target') != 'NPJB00162' or not re.fullmatch(r'0\.\d+\.\d+', manifest.get('version', '')):
        raise ValueError('Expected a versioned NPJB00162 build')
    root = (build / 'overlay').resolve()
    replacements, seen = {}, set()
    for row in manifest['files']:
        name = safe_name(row['file'])
        path = (root / name).resolve()
        if root not in path.parents or not path.is_file():
            raise ValueError('Overlay path missing or escapes build')
        if name.casefold() in seen:
            raise ValueError('Duplicate overlay path')
        seen.add(name.casefold())
        if path.stat().st_size != row['bytes'] or sha_file(path) != row['sha256']:
            raise ValueError('Overlay manifest mismatch: ' + name)
        target = 'USRDIR/EBOOT.BIN' if name == 'USRDIR/EBOOT.elf' else name
        if target.casefold() in {n.casefold() for n in replacements}:
            raise ValueError('Conflicting executable/path mapping')
        replacements[target] = dict(file=path, source_file=name, size=row['bytes'], sha256=row['sha256'])
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if actual != {r['file'] for r in manifest['files']}:
        raise ValueError('Unmanifested overlay files')
    boot = replacements.get('USRDIR/EBOOT.BIN')
    if boot is None or boot['source_file'] != 'USRDIR/EBOOT.elf':
        raise ValueError('Build must contain the translated EBOOT.elf')
    with boot['file'].open('rb') as stream:
        elf = stream.read(20)
    if len(elf) < 20 or elf[:6] != b'\x7fELF\x02\x02' or struct.unpack_from('>H', elf, 18)[0] != 21:
        raise ValueError('Expected a big-endian PPC64 ELF boot executable')
    pkg = Package(original)
    try:
        if pkg.content_id != CONTENT_ID:
            raise ValueError('Wrong game package content ID')
        pkg.stream.seek(0)
        header = bytearray(pkg.stream.read(pkg.start))
        if len(header) != pkg.start or pkg.start < 0xc0:
            raise ValueError('Truncated package preamble')
        raw = pkg.read(0, pkg.count * 32)
        entries = []
        for i, entry in enumerate(pkg.entries):
            row = dict(entry)
            row['reserved'] = struct.unpack_from('>I', raw, i * 32 + 28)[0]
            entries.append(row)
        payloads = sorted((e['offset'], e['offset'] + e['size']) for e in entries if not e['directory'] and e['size'])
        if not payloads or payloads[0][0] < pkg.count * 32:
            raise ValueError('Invalid first payload boundary')
        if any(b > c for (_, b), (c, _) in zip(payloads, payloads[1:])):
            raise ValueError('Overlapping original file payloads')
        old = {e['path']: e for e in entries}
        folded = {n.casefold(): n for n in old}
        for name in replacements:
            if name.casefold() in folded and name not in old:
                raise ValueError('Case-changing path collision')
            if name in old and old[name]['directory']:
                raise ValueError('Overlay replaces a directory')
            for parent in PurePosixPath(name).parents:
                if str(parent) != '.' and (str(parent) not in old or not old[str(parent)]['directory']):
                    raise ValueError('Overlay needs an unlisted parent directory: ' + str(parent))
        additions = sorted(set(replacements) - set(old))
        for name in additions:
            entries.append(dict(path=name, offset=0, size=0, flags=0x80000003, reserved=0, directory=False))
        table_bytes = len(entries) * 32
        if table_bytes > payloads[0][0]:
            raise ValueError('Expanded entry table overlaps original file payload')
        # Put every name beyond the original payload; table growth may overwrite
        # the former names, but must never overwrite an unchanged file.
        name_start = align16(pkg.size)
        names = bytearray()
        for entry in entries:
            # RPCS3 starts CTR at floor(offset/16) without skipping intra-block
            # keystream bytes. Match the retail format: every name begins on
            # a 16-byte boundary and name_size excludes its padding/NUL.
            names.extend(b'\0' * (align16(len(names)) - len(names)))
            encoded = entry['path'].encode('utf8')
            entry['name_offset'] = name_start + len(names)
            entry['name_size'] = len(encoded)
            names.extend(encoded)
        cursor = align16(name_start + len(names))
        changed = []
        for entry in entries:
            replacement = replacements.get(entry['path'])
            if replacement is None:
                continue
            before = old.get(entry['path'])
            if before is None or replacement['size'] > before['size']:
                entry['offset'] = cursor
                cursor = align16(cursor + replacement['size'])
                placement = 'append'
            else:
                placement = 'original slot'
            entry['size'] = replacement['size']
            changed.append(dict(path=entry['path'], source_file=replacement['source_file'],
                                size=entry['size'], offset=entry['offset'], placement=placement,
                                sha256=replacement['sha256'], new=before is None))
        data_size = cursor
        # Preserve the opaque trailer; it is explicitly NOT a valid signature.
        pkg.stream.seek(pkg.start + pkg.size)
        trailer = pkg.stream.read()
        total = pkg.start + data_size + len(trailer)
        struct.pack_into('>I', header, 0x14, len(entries))
        struct.pack_into('>Q', header, 0x18, total)
        struct.pack_into('>Q', header, 0x28, data_size)
        meta_start, meta_count = struct.unpack_from('>II', header, 8)
        at = meta_start
        size_fields = []
        for _ in range(meta_count):
            if at + 8 > len(header):
                raise ValueError('Metadata exceeds package preamble')
            kind, size = struct.unpack_from('>II', header, at)
            if at + 8 + size > len(header):
                raise ValueError('Metadata payload exceeds package preamble')
            if kind == 4:
                if size != 8 or struct.unpack_from('>Q', header, at + 8)[0] != pkg.size:
                    raise ValueError('Unexpected package-size metadata')
                struct.pack_into('>Q', header, at + 8, data_size)
                size_fields.append(at + 8)
            at += 8 + size
        table = bytearray()
        for e in entries:
            table.extend(struct.pack('>IIQQII', e['name_offset'], e['name_size'], e['offset'], e['size'], e['flags'], e['reserved']))
        return dict(original=original, build=build, source_sha256=sha_file(original), manifest_sha256=sha_file(manifest_path),
                    version=manifest['version'], header=header, trailer=trailer, names=names,
                    name_start=name_start, table=table, entries=entries, changed=changed,
                    replacements=replacements, start=pkg.start, old_size=pkg.size,
                    size=data_size, total=total, iv=pkg.iv, old_count=pkg.count,
                    first_payload=payloads[0][0], metadata_size_fields=size_fields)
    finally:
        pkg.close()


def public_plan(p):
    return dict(version=p['version'], target='NPJB00162', content_id=CONTENT_ID,
                compatibility='RPCS3 only; installation and boot not yet tested',
                retail_authentication_valid=False, original=str(p['original']),
                source_sha256=p['source_sha256'], build_manifest_sha256=p['manifest_sha256'],
                source_entries=p['old_count'], output_entries=len(p['entries']),
                source_payload_bytes=p['old_size'], output_payload_bytes=p['size'],
                output_bytes=p['total'], payload_start=p['start'],
                first_original_payload=p['first_payload'], entry_table_bytes=len(p['table']),
                relocated_names_bytes=len(p['names']), relocated_names_offset=p['name_start'],
                metadata_size_fields=p['metadata_size_fields'], changed=p['changed'])


def encrypt_to(out, p, offset, source):
    """CTR encryption at an arbitrary payload offset, including unaligned ones."""
    block, skip = divmod(offset, 16)
    cipher = Cipher(algorithms.AES(PKG_KEY), modes.CTR((p['iv'] + block).to_bytes(16, 'big'))).encryptor()
    if skip:
        cipher.update(b'\0' * skip)
    out.seek(p['start'] + offset)
    while chunk := source.read(CHUNK):
        out.write(cipher.update(chunk))
    out.write(cipher.finalize())


def rpcs3_metadata(path):
    """Independently reproduce RPCS3's aligned table/name decryption.

    Unlike Package.read, unpkg.cpp's decrypt starts the counter at offset//16
    and does not consume offset%16 keystream bytes. An unaligned name is thus
    an installer incompatibility even when a general CTR reader accepts it.
    """
    with Path(path).open('rb') as stream:
        header = stream.read(0xc0)
        count = struct.unpack_from('>I', header, 0x14)[0]
        start = struct.unpack_from('>Q', header, 0x20)[0]
        iv = int.from_bytes(header[0x70:0x80], 'big')

        def decrypt(offset, size):
            stream.seek(start + offset)
            cipher = Cipher(algorithms.AES(PKG_KEY), modes.CTR((iv + offset // 16).to_bytes(16, 'big'))).decryptor()
            return cipher.update(stream.read(size)) + cipher.finalize()

        table = decrypt(0, count * 32)
        rows = []
        for i in range(count):
            no, ns, offset, size, flags, reserved = struct.unpack_from('>IIQQII', table, i * 32)
            if no % 16 or (size and offset % 16):
                raise ValueError('RPCS3 requires block-aligned names/file payloads')
            name_bytes = decrypt(no, ns)
            if b'\0' in name_bytes:
                raise ValueError('Retail name_size must exclude NUL/padding')
            name = safe_name(name_bytes.decode('utf8'))
            rows.append(dict(path=name, offset=offset, size=size, flags=flags,
                             reserved=reserved, directory=(flags & 0xff) == 4))
        return rows


def write_package(p, destination):
    destination = Path(destination).resolve()
    report = destination.with_suffix('.verification.json')
    human = destination.with_suffix('.audit.txt')
    if any(path.exists() for path in (destination, report, human)):
        raise ValueError('Output package or audit already exists')
    before_hash = sha_file(p['original'])
    if before_hash != p['source_sha256'] or sha_file(p['build'] / 'manifest.json') != p['manifest_sha256']:
        raise ValueError('Package/build manifest changed after planning')
    if any(sha_file(r['file']) != r['sha256'] for r in p['replacements'].values()):
        raise ValueError('Overlay changed after planning')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with p['original'].open('rb') as source, destination.open('xb') as out:
        remaining = p['start'] + p['old_size']
        while remaining:
            chunk = source.read(min(CHUNK, remaining))
            if not chunk:
                raise ValueError('Source changed or truncated during rebuild')
            out.write(chunk)
            remaining -= len(chunk)
        # Padding in newly added ciphertext space is deterministic zero bytes;
        # no directory entry refers to it.
        out.truncate(p['total'])
        out.seek(0)
        out.write(p['header'])
        encrypt_to(out, p, 0, io.BytesIO(p['table']))
        encrypt_to(out, p, p['name_start'], io.BytesIO(p['names']))
        for change in p['changed']:
            replacement = p['replacements'][change['path']]
            with replacement['file'].open('rb') as payload:
                encrypt_to(out, p, change['offset'], payload)
        out.seek(p['start'] + p['size'])
        out.write(p['trailer'])
    audit = verify(p, destination)
    if sha_file(p['original']) != before_hash:
        raise ValueError('Source package changed during rebuild')
    audit.update(source_sha256=before_hash, source_unchanged=True,
                 output_sha256=sha_file(destination), result='verified',
                 verification_scope='all entry payloads and preserved ciphertext; no runtime test')
    report.write_text(json.dumps(audit, indent=2) + '\n', encoding='utf8')
    human.write_text(
        f"Wizardry English {p['version']} RPCS3 package\n"
        f"Source SHA-256: {audit['source_sha256']}\nOutput SHA-256: {audit['output_sha256']}\n"
        f"Entries verified: {len(audit['entries'])}; overlay payloads: {len(p['changed'])}\n"
        f"Unselected entries and untouched ciphertext verified byte-for-byte.\n"
        "Translated EBOOT.elf is installed as USRDIR/EBOOT.BIN.\n"
        "Retail authentication is invalid. RPCS3 installation/boot has NOT been tested by this tool.\n"
        "PKG00/the other game is outside this input package and is untouched.\n",
        encoding='utf8')
    return audit


def verify(p, destination):
    """Read every file through the existing, independent Package reader."""
    original, output = Package(p['original']), Package(destination)
    try:
        native = rpcs3_metadata(destination)
        for actual_row, expected_row in zip(native, p['entries']):
            if any(actual_row[k] != expected_row[k] for k in actual_row):
                raise ValueError('RPCS3 table/name decode mismatch')
        if len(native) != len(p['entries']):
            raise ValueError('RPCS3 table entry count mismatch')
        expected = {e['path']: e for e in p['entries']}
        actual = {e['path']: e for e in output.entries}
        if output.iv != original.iv or output.start != original.start or output.content_id != original.content_id:
            raise ValueError('Package identity/CTR layout changed')
        if set(actual) != set(expected) or output.size != p['size'] or Path(destination).stat().st_size != p['total']:
            raise ValueError('Output entry set/size mismatch')
        with Path(destination).open('rb') as stream:
            if stream.read(p['start']) != p['header']:
                raise ValueError('Rebuilt package preamble mismatch')
            stream.seek(p['start'] + p['size'])
            if stream.read() != p['trailer']:
                raise ValueError('Opaque trailer changed')
        if output.read(0, len(p['table'])) != p['table'] or output.read(p['name_start'], len(p['names'])) != p['names']:
            raise ValueError('Rebuilt table/name pool mismatch')
        old = {e['path']: e for e in original.entries}
        rows = []
        for name, e in actual.items():
            exp = expected[name]
            if any(e[k] != exp[k] for k in ('offset', 'size', 'flags', 'directory')):
                raise ValueError('Entry layout mismatch: ' + name)
            if e['directory']:
                rows.append(dict(path=name, directory=True))
                continue
            digest = package_hash(output, e)
            replacement = p['replacements'].get(name)
            source_hash = replacement['sha256'] if replacement else package_hash(original, old[name])
            if digest != source_hash:
                raise ValueError('Payload mismatch: ' + name)
            rows.append(dict(path=name, size=e['size'], sha256=digest, overlay=replacement is not None))
        # Verify *all* old encrypted data outside the table and in-place changes,
        # including original name bytes, old appended-away files and padding.
        intervals = [(0, len(p['table']))]
        intervals.extend((c['offset'], c['offset'] + c['size']) for c in p['changed'] if c['placement'] == 'original slot')
        intervals.sort()
        merged = []
        for a, b in intervals:
            if merged and a <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
            else:
                merged.append((a, b))
        cursor, checked = 0, 0
        with p['original'].open('rb') as src, Path(destination).open('rb') as dst:
            for a, b in merged + [(p['old_size'], p['old_size'])]:
                if a > cursor:
                    src.seek(p['start'] + cursor)
                    dst.seek(p['start'] + cursor)
                    remaining = a - cursor
                    while remaining:
                        size = min(CHUNK, remaining)
                        if src.read(size) != dst.read(size):
                            raise ValueError('Untouched encrypted data changed')
                        checked += size
                        remaining -= size
                cursor = max(cursor, b)
        result = public_plan(p)
        result.update(entries=rows, unchanged_ciphertext_bytes=checked,
                      entry_payloads_verified=True, iv_preserved=True,
                      rpcs3_aligned_table_and_names_verified=True,
                      unchanged_entry_offsets_preserved=True,
                      executable_mapping='USRDIR/EBOOT.elf -> USRDIR/EBOOT.BIN')
        return result
    finally:
        original.close()
        output.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original', type=Path)
    parser.add_argument('build', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    p = plan(args.original, args.build)
    summary = public_plan(p)
    samples = summary.pop('changed')
    summary['overlay_files'] = len(samples)
    summary['new_files'] = sum(c['new'] for c in samples)
    summary['appended_files'] = sum(c['placement'] == 'append' for c in samples)
    summary['samples'] = samples[:5]
    print(json.dumps(summary, indent=2))
    if not args.write:
        print('Dry run: nothing written. Review this plan, then use --write with a fresh output path.')
        return
    audit = write_package(p, args.output)
    print('Verified package:', args.output)
    print('All %d entry payloads checked. Runtime installation/boot test remains required.' % len(audit['entries']))


if __name__ == '__main__':
    main()
