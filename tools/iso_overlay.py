"""Replace only PKG01 in the supplied PS3 installer ISO; dry-run by default.

Preserves all original file locations except PKG01's second extent. ISO9660,
Joliet, UDF 2.50 metadata partition, descriptor checksums, trailing anchors
and the PS3 plaintext-region end are updated together. This is an RPCS3
installer image, not a retail-signed PS3 game image. Personal keys/licenses
are neither read nor required. Source references: ECMA-167 and OpenBSD's
sys/isofs/udf/ecma167-udf.h; RPCS3 Crypto/unpkg.cpp and Emu/System.cpp.
"""
import argparse
import binascii
import hashlib
import json
from pathlib import Path
import struct

from disc_read import Disc
from pkg_overlay import sha_file

BLOCK = 2048
CHUNK = 4 * 1024 * 1024
TARGET = '/PS3_GAME/PKGDIR/PKG01/INSTALL.PKG'
SOURCE_SHA256 = '25dc1f842f42dbd9e24ee1a23e23e51e339fc406bed997c8fbdb9815d41a42a7'


def u16(data, at):
    return struct.unpack_from('<H', data, at)[0]


def u32(data, at):
    return struct.unpack_from('<I', data, at)[0]


def u64(data, at):
    return struct.unpack_from('<Q', data, at)[0]


def both32(data, at, value=None):
    if value is not None:
        struct.pack_into('<I', data, at, value)
        struct.pack_into('>I', data, at + 4, value)
        return value
    little = u32(data, at)
    if little != struct.unpack_from('>I', data, at + 4)[0]:
        raise ValueError('ISO endian copies disagree')
    return little


def check_tag(data, expected_id=None, location=None):
    if len(data) < 16 or u16(data, 2) != 3:
        raise ValueError('Unsupported/truncated UDF descriptor tag')
    if expected_id is not None and u16(data, 0) != expected_id:
        raise ValueError('Unexpected UDF descriptor type')
    if data[4] != sum(data[:4] + data[5:16]) & 255:
        raise ValueError('UDF descriptor tag checksum mismatch')
    length = u16(data, 10)
    if length > len(data) - 16 or binascii.crc_hqx(data[16:16 + length], 0) != u16(data, 8):
        raise ValueError('UDF descriptor CRC mismatch')
    if location is not None and u32(data, 12) != location:
        raise ValueError('UDF descriptor location mismatch')


def fix_tag(data, location=None):
    if location is not None:
        struct.pack_into('<I', data, 12, location)
    struct.pack_into('<H', data, 8, binascii.crc_hqx(data[16:16 + u16(data, 10)], 0))
    data[4] = sum(data[:4] + data[5:16]) & 255
    check_tag(data, location=location)
    return data


class Image:
    def __init__(self, path):
        self.path = Path(path)
        self.size = self.path.stat().st_size
        self.stream = self.path.open('rb')
        if self.size % BLOCK:
            self.close()
            raise ValueError('ISO length is not sector aligned')

    def close(self):
        self.stream.close()

    def read(self, offset, size):
        if offset < 0 or size < 0 or offset + size > self.size:
            raise ValueError('ISO read outside image')
        self.stream.seek(offset)
        data = self.stream.read(size)
        if len(data) != size:
            raise ValueError('Truncated ISO')
        return data

    def sector(self, number):
        return self.read(number * BLOCK, BLOCK)


def hash_extents(image, extents):
    digest = hashlib.sha256()
    for offset, size in extents:
        for at in range(0, size, CHUNK):
            digest.update(image.read(offset + at, min(CHUNK, size - at)))
    return digest.hexdigest()


class IsoView:
    """Separate ISO directory walker retaining physical directory record sites."""
    def __init__(self, image, descriptor):
        self.image, self.descriptor = image, descriptor
        vd = image.sector(descriptor)
        self.joliet = vd[0] == 2
        if vd[1:7] != b'CD001\x01' or vd[0] not in (1, 2):
            raise ValueError('Unexpected ISO volume descriptor')
        if self.joliet and vd[88:91] not in (b'%/@', b'%/C', b'%/E'):
            raise ValueError('Supplementary descriptor is not Joliet')
        if both32(vd, 80) != image.size // BLOCK or u16(vd, 128) != BLOCK:
            raise ValueError('ISO volume size/block geometry mismatch')
        self.entries = {}
        self._walk('', vd[156:156 + vd[156]], set())
        for e in self.entries.values():
            if e.pop('continued'):
                raise ValueError('Unfinished ISO multi-extent file')

    def _walk(self, prefix, raw, visited):
        offset, length = both32(raw, 2) * BLOCK, both32(raw, 10)
        if offset in visited:
            raise ValueError('ISO directory cycle')
        visited.add(offset)
        data = self.image.read(offset, length)
        at = 0
        while at < len(data):
            size = data[at]
            if not size:
                at = (at // BLOCK + 1) * BLOCK
                continue
            record = data[at:at + size]
            if len(record) != size or size < 34 or at % BLOCK + size > BLOCK:
                raise ValueError('Invalid ISO directory record')
            name_raw = record[33:33 + record[32]]
            position = offset + at
            at += size
            if name_raw in (b'\0', b'\1'):
                continue
            name = name_raw.decode('utf-16-be' if self.joliet else 'ascii').split(';')[0]
            if not name or any(c in name for c in '/\\:\0') or name in ('.', '..'):
                raise ValueError('Unsafe ISO filename')
            path = prefix + '/' + name
            loc, count = both32(record, 2) * BLOCK, both32(record, 10)
            self.image.read(loc, min(count, 1))
            directory, continuation = bool(record[25] & 2), bool(record[25] & 128)
            row = self.entries.get(path)
            if row is not None:
                if not row['continued'] or row['directory'] or directory:
                    raise ValueError('Invalid duplicate ISO path')
                row['extents'].append((loc, count))
                row['records'].append((position, bytes(record)))
                row['size'] += count
                row['continued'] = continuation
            else:
                self.entries[path] = dict(path=path, size=count, directory=directory,
                                          extents=[(loc, count)], records=[(position, bytes(record))],
                                          continued=continuation)
            if directory:
                self._walk(path, record, visited)


class UdfView:
    """Bounded UDF 2.50 metadata-partition walker, including mirror selection.

    Only recorded short/long allocation descriptors are accepted. Unexpected
    layout variants fail rather than guessing or silently using the ISO view.
    """
    def __init__(self, image, mirror=False, reserve=False):
        self.image, self.mirror = image, mirror
        anchor = image.sector(256)
        check_tag(anchor, 2, 256)
        length, start = struct.unpack_from('<II', anchor, 24 if reserve else 16)
        if length % BLOCK or length > 64 * BLOCK:
            raise ValueError('Unexpected UDF volume descriptor sequence')
        self.descriptors = {}
        for sector in range(start, start + length // BLOCK):
            raw = image.sector(sector)
            check_tag(raw, location=sector)
            kind = u16(raw, 0)
            if kind in self.descriptors:
                raise ValueError('Duplicate UDF volume descriptor')
            self.descriptors[kind] = (sector, raw)
            if kind == 8:
                break
        else:
            raise ValueError('UDF volume sequence lacks terminator')
        self.pd_sector, pd = self.descriptors[5]
        self.lvd_sector, lvd = self.descriptors[6]
        self.partition_start, self.partition_size = u32(pd, 188), u32(pd, 192)
        if self.partition_start + self.partition_size > image.size // BLOCK or u32(lvd, 212) != BLOCK:
            raise ValueError('UDF partition outside volume')
        if u32(lvd, 264) != 70 or u32(lvd, 268) != 2:
            raise ValueError('Expected physical plus metadata partition maps')
        maps = lvd[440:510]
        if maps[:2] != b'\1\6' or maps[6:8] != b'\2\x40' or b'*UDF Metadata Partition' not in maps:
            raise ValueError('Unsupported UDF partition maps')
        if u16(maps, 4) != u16(pd, 22) or u16(maps, 44) != u16(pd, 22):
            raise ValueError('UDF map partition numbers disagree')
        metadata_loc = u32(maps, 50 if mirror else 46)
        self.metadata_fe_sector = self.partition_start + metadata_loc
        metadata = image.sector(self.metadata_fe_sector)
        check_tag(metadata, 261, metadata_loc)
        if metadata[27] != (251 if mirror else 250) or u16(metadata, 34) & 7:
            raise ValueError('Unexpected UDF metadata file ICB')
        ea, adlen = u32(metadata, 168), u32(metadata, 172)
        if adlen % 8 or 176 + ea + adlen > BLOCK:
            raise ValueError('Invalid UDF metadata allocation list')
        self.metadata_extents = []
        for at in range(176 + ea, 176 + ea + adlen, 8):
            length, loc = struct.unpack_from('<II', metadata, at)
            if length >> 30 or length % BLOCK:
                raise ValueError('Unsupported UDF metadata extent')
            self.metadata_extents.append(((self.partition_start + loc) * BLOCK, length))
        if sum(n for _, n in self.metadata_extents) != u64(metadata, 56):
            raise ValueError('UDF metadata file size mismatch')
        self.integrity_sector = u32(lvd, 436)
        self.integrity = image.sector(self.integrity_sector)
        check_tag(self.integrity, 9, self.integrity_sector)
        if u32(self.integrity, 72) != 2 or u32(self.integrity, 88) != self.partition_size:
            raise ValueError('UDF integrity partition size mismatch')
        fsd_length, fsd_loc, fsd_part = struct.unpack_from('<IIH', lvd, 248)
        if fsd_part != 1 or fsd_length < 512:
            raise ValueError('Unexpected UDF file set location')
        fsd = image.read(self.address(fsd_part, fsd_loc), BLOCK)
        check_tag(fsd, 256, fsd_loc)
        _, root_loc, root_part = struct.unpack_from('<IIH', fsd, 400)
        self.entries = {}
        self._walk('', root_part, root_loc, set())

    def address(self, partition, block):
        if partition == 0:
            if block >= self.partition_size:
                raise ValueError('UDF block outside physical partition')
            return (self.partition_start + block) * BLOCK
        if partition != 1:
            raise ValueError('Unsupported UDF partition reference')
        offset = block * BLOCK
        for start, length in self.metadata_extents:
            if offset < length:
                return start + offset
            offset -= length
        raise ValueError('UDF block outside metadata file')

    def _fe(self, partition, block):
        physical = self.address(partition, block)
        raw = self.image.read(physical, BLOCK)
        check_tag(raw, 261, block)
        flags = u16(raw, 34) & 7
        width = {0: 8, 1: 16}.get(flags)
        ea, adlen = u32(raw, 168), u32(raw, 172)
        if width is None or adlen % width or 176 + ea + adlen > BLOCK:
            raise ValueError('Unsupported UDF file allocation layout')
        extents = []
        for at in range(176 + ea, 176 + ea + adlen, width):
            length, loc = struct.unpack_from('<II', raw, at)
            part = u16(raw, at + 8) if width == 16 else partition
            if length >> 30:
                raise ValueError('Unrecorded/indirect UDF allocation unsupported')
            address = self.address(part, loc)
            if address + length > self.image.size:
                raise ValueError('UDF extent exceeds image')
            if part == 0 and loc * BLOCK + length > self.partition_size * BLOCK:
                raise ValueError('UDF extent exceeds physical partition')
            extents.append((address, length))
        size = u64(raw, 56)
        if sum(n for _, n in extents) != size:
            raise ValueError('UDF information/allocation lengths disagree')
        return dict(size=size, directory=raw[27] == 4, extents=extents,
                    fe_sector=physical // BLOCK, fe=raw, allocation_at=176 + ea,
                    allocation_width=width, logical_block=block)

    def _walk(self, prefix, partition, block, visited):
        if (partition, block) in visited:
            raise ValueError('UDF directory cycle/hard link unsupported')
        visited.add((partition, block))
        entry = self._fe(partition, block)
        if prefix:
            entry['path'] = prefix
            self.entries[prefix] = entry
        if not entry['directory']:
            return
        if entry['size'] > 1024 * 1024:
            raise ValueError('Unexpectedly large UDF directory')
        data = b''.join(self.image.read(a, n) for a, n in entry['extents'])
        at = 0
        while at < len(data):
            if len(data) - at < 38:
                raise ValueError('Truncated UDF file identifier')
            name_len, impl_len = data[at + 19], u16(data, at + 36)
            length = (38 + name_len + impl_len + 3) & ~3
            raw = data[at:at + length]
            check_tag(raw, 257)
            if raw[18] & 8:
                at += length
                continue
            if raw[18] & 4:
                raise ValueError('Deleted UDF identifier unsupported')
            encoded = raw[38 + impl_len:38 + impl_len + name_len]
            if not encoded or encoded[0] not in (8, 16):
                raise ValueError('Unsupported UDF compressed Unicode name')
            name = encoded[1:].decode('latin1' if encoded[0] == 8 else 'utf-16-be')
            if not name or any(c in name for c in '/\\:\0') or name in ('.', '..'):
                raise ValueError('Unsafe UDF filename')
            _, loc, part = struct.unpack_from('<IIH', raw, 20)
            path = prefix + '/' + name
            if path in self.entries:
                raise ValueError('Duplicate UDF path')
            self._walk(path, part, loc, visited)
            at += length


def same_entries(a, b, include_directories=False):
    selected = lambda rows: {k: v for k, v in rows.items() if include_directories or not v['directory']}
    aa, bb = selected(a), selected(b)
    if set(aa) != set(bb):
        raise ValueError('Filesystem views disagree on paths')
    for name in aa:
        if any(aa[name][key] != bb[name][key] for key in ('size', 'directory', 'extents')):
            raise ValueError('Filesystem views disagree: ' + name)


def plan(original, replacement, expected_source_sha256=SOURCE_SHA256):
    original, replacement = Path(original).resolve(), Path(replacement).resolve()
    source_hash, package_hash = sha_file(original), sha_file(replacement)
    if source_hash != expected_source_sha256:
        raise ValueError('Unexpected source ISO hash')
    report = json.loads(replacement.with_suffix('.verification.json').read_text(encoding='utf8'))
    if report.get('result') != 'verified' or report.get('output_sha256') != package_hash or not report.get('rpcs3_aligned_table_and_names_verified'):
        raise ValueError('Package verification report missing or mismatched')
    image = Image(original)
    try:
        primary, joliet = IsoView(image, 16), IsoView(image, 17)
        same_entries(primary.entries, joliet.entries)
        udf_views = [UdfView(image, mirror=m, reserve=r) for r in (False, True) for m in (False, True)]
        for view in udf_views:
            same_entries(primary.entries, view.entries)
        selected = primary.entries[TARGET]
        if selected['directory'] or len(selected['extents']) != 2 or selected['extents'][0][1] % BLOCK:
            raise ValueError('Expected two original PKG01 extents')
        if hash_extents(image, selected['extents']) != report['source_sha256']:
            raise ValueError('ISO PKG01 does not match package source')
        first, first_size = selected['extents'][0]
        tail_size = replacement.stat().st_size - first_size
        if tail_size <= 0 or tail_size >= 1 << 30:
            raise ValueError('Replacement tail does not fit one UDF/ISO extent')
        tail_start = image.size
        payload_end_blocks = (tail_start + tail_size + BLOCK - 1) // BLOCK
        # Reserve a full 256-sector anchor zone after all selected payload.
        output_blocks = payload_end_blocks + 257
        patches = {}

        def patch_sector(sector, label, mutate):
            before = patches[sector]['before'] if sector in patches else image.sector(sector)
            after = bytearray(patches[sector]['after'] if sector in patches else before)
            mutate(after)
            patches[sector] = dict(sector=sector, label=label, before=before, after=bytes(after))

        region = image.sector(0)
        if struct.unpack_from('>IIIIII', region, 0) != (2, 0, 0, 511, 544, image.size // BLOCK - 1):
            raise ValueError('Unexpected PS3 plaintext region map')
        patch_sector(0, 'PS3 final plaintext region', lambda b: struct.pack_into('>I', b, 20, output_blocks - 1))
        for view in (primary, joliet):
            patch_sector(view.descriptor, 'ISO/Joliet volume size', lambda b: both32(b, 80, output_blocks))
            position, raw = view.entries[TARGET]['records'][1]
            sector, within = divmod(position, BLOCK)
            if raw[25] & 128:
                raise ValueError('Last ISO extent marked as continued')
            def change_record(b, within=within):
                both32(b, within + 2, tail_start // BLOCK)
                both32(b, within + 10, tail_size)
            patch_sector(sector, 'PKG01 second extent record', change_record)
        partition_start = udf_views[0].partition_start
        new_partition_size = output_blocks - partition_start - 1
        for sector in {v.pd_sector for v in udf_views}:
            def change_partition(b):
                struct.pack_into('<I', b, 192, new_partition_size)
                fix_tag(b)
            patch_sector(sector, 'UDF physical partition size', change_partition)
        for sector in {v.integrity_sector for v in udf_views}:
            def change_integrity(b):
                struct.pack_into('<I', b, 88, new_partition_size)
                fix_tag(b)
            patch_sector(sector, 'UDF integrity physical partition size', change_integrity)
        for view in udf_views:
            entry = view.entries[TARGET]
            if entry['allocation_width'] != 16 or len(entry['extents']) != 2:
                raise ValueError('Expected two UDF long allocation descriptors')
            sector, second_ad = entry['fe_sector'], entry['allocation_at'] + 16
            if sector in patches:
                continue  # Main and mirror metadata can share the same blocks.
            def change_file(b, at=second_ad):
                struct.pack_into('<Q', b, 56, replacement.stat().st_size)
                struct.pack_into('<Q', b, 64, (first_size + tail_size + BLOCK - 1) // BLOCK)
                if u16(b, at + 8) != 0:
                    raise ValueError('PKG01 allocation must use physical partition')
                struct.pack_into('<II', b, at, tail_size, tail_start // BLOCK - partition_start)
                fix_tag(b)
            patch_sector(sector, 'UDF PKG01 information and allocation', change_file)
        anchor_template = image.sector(256)
        anchors = {}
        for location in (output_blocks - 257, output_blocks - 1):
            raw = bytearray(anchor_template)
            fix_tag(raw, location)
            anchors[location] = bytes(raw)
        return dict(original=original, replacement=replacement, source_sha256=source_hash,
                    package_sha256=package_hash, version=report['version'], source_size=image.size,
                    size=output_blocks * BLOCK, first_extent=(first, first_size),
                    tail_extent=(tail_start, tail_size), patches=patches, anchors=anchors,
                    source_entries=primary.entries, udf_partition_start=partition_start,
                    udf_partition_size=new_partition_size)
    finally:
        image.close()


def public_plan(p):
    return dict(version=p['version'], target=TARGET,
                compatibility='RPCS3 installer ISO; retail console compatibility not claimed',
                original=str(p['original']), source_sha256=p['source_sha256'],
                replacement_pkg=str(p['replacement']), replacement_sha256=p['package_sha256'],
                source_bytes=p['source_size'], output_bytes=p['size'],
                first_extent=p['first_extent'], appended_second_extent=p['tail_extent'],
                metadata=[dict(sector=k, label=v['label']) for k, v in sorted(p['patches'].items())],
                added_anchors=sorted(p['anchors']), udf_partition_start=p['udf_partition_start'],
                udf_partition_size=p['udf_partition_size'])


def verify(p, destination):
    source, output = Image(p['original']), Image(destination)
    try:
        if output.size != p['size']:
            raise ValueError('Output ISO length mismatch')
        primary, joliet = IsoView(output, 16), IsoView(output, 17)
        same_entries(primary.entries, joliet.entries)
        readers = [UdfView(output, mirror=m, reserve=r) for r in (False, True) for m in (False, True)]
        for view in readers:
            same_entries(primary.entries, view.entries)
            if hash_extents(output, view.entries[TARGET]['extents']) != p['package_sha256']:
                raise ValueError('UDF PKG01 payload mismatch')
        independent = Disc(destination)
        try:
            same_entries(primary.entries, {e['path']: e for e in independent.entries})
        finally:
            independent.stream.close()
        for position in (256, output.size // BLOCK - 257, output.size // BLOCK - 1):
            check_tag(output.sector(position), 2, position)
        if hash_extents(output, primary.entries[TARGET]['extents']) != p['package_sha256']:
            raise ValueError('ISO9660 PKG01 payload mismatch')
        for sector, change in p['patches'].items():
            if output.sector(sector) != change['after']:
                raise ValueError('ISO metadata patch mismatch')
        for sector, data in p['anchors'].items():
            if output.sector(sector) != data:
                raise ValueError('ISO trailing anchor mismatch')
        files = []
        if set(primary.entries) != set(p['source_entries']):
            raise ValueError('ISO source/output paths changed')
        for name, entry in primary.entries.items():
            before = p['source_entries'][name]
            if name != TARGET and any(entry[k] != before[k] for k in ('size', 'directory', 'extents')):
                raise ValueError('Unselected ISO entry layout changed')
            if entry['directory']:
                continue
            digest = hash_extents(output, entry['extents'])
            wanted = p['package_sha256'] if name == TARGET else hash_extents(source, before['extents'])
            if digest != wanted:
                raise ValueError('ISO file payload mismatch: ' + name)
            files.append(dict(path=name, size=entry['size'], sha256=digest, selected=name == TARGET))
        allowed = [(a * BLOCK, (a + 1) * BLOCK) for a in p['patches']]
        a, n = p['first_extent']
        allowed.append((a, a + n))
        allowed.sort()
        cursor, unchanged = 0, 0
        for a, b in allowed + [(p['source_size'], p['source_size'])]:
            if a < cursor:
                raise ValueError('Overlapping allowed ISO changes')
            for offset in range(cursor, a, CHUNK):
                size = min(CHUNK, a - offset)
                if source.read(offset, size) != output.read(offset, size):
                    raise ValueError('ISO bytes changed outside selected payload/metadata')
                unchanged += size
            cursor = b
        result = public_plan(p)
        result.update(result='verified', files=files,
                      unchanged_physical_bytes=unchanged,
                      iso9660_joliet_udf_main_mirror_reserve_agree=True,
                      udf_descriptor_checksums_verified=True,
                      source_unchanged=sha_file(p['original']) == p['source_sha256'],
                      output_sha256=sha_file(destination),
                      verification_scope='all filesystem views, every file, unchanged physical bytes; no runtime test')
        if not result['source_unchanged']:
            raise ValueError('Original ISO changed')
        return result
    finally:
        source.close()
        output.close()


def write_iso(p, destination):
    destination = Path(destination).resolve()
    report, human = destination.with_suffix('.verification.json'), destination.with_suffix('.audit.txt')
    if any(q.exists() for q in (destination, report, human)):
        raise ValueError('Output ISO or audit already exists')
    if sha_file(p['original']) != p['source_sha256'] or sha_file(p['replacement']) != p['package_sha256']:
        raise ValueError('Input changed after planning')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with p['original'].open('rb') as source, destination.open('xb') as output:
        while data := source.read(CHUNK):
            output.write(data)
        output.truncate(p['size'])
        with p['replacement'].open('rb') as package:
            for start, size in (p['first_extent'], p['tail_extent']):
                output.seek(start)
                remaining = size
                while remaining:
                    data = package.read(min(CHUNK, remaining))
                    if not data:
                        raise ValueError('Replacement package truncated')
                    output.write(data)
                    remaining -= len(data)
            if package.read(1):
                raise ValueError('Replacement package grew')
        for sector, change in p['patches'].items():
            output.seek(sector * BLOCK)
            output.write(change['after'])
        for sector, data in p['anchors'].items():
            output.seek(sector * BLOCK)
            output.write(data)
    audit = verify(p, destination)
    report.write_text(json.dumps(audit, indent=2) + '\n', encoding='utf8')
    human.write_text(
        f"Wizardry English {p['version']} RPCS3 installer ISO\n"
        f"Source SHA-256: {p['source_sha256']}\nOutput SHA-256: {audit['output_sha256']}\n"
        f"Output bytes: {p['size']}\nSelected file: {TARGET}\n"
        "Every other file, including PKG00 and the update PUP, is unchanged.\n"
        "ISO9660, Joliet and primary/reserve UDF using main/mirror metadata agree.\n"
        "Physical bytes outside selected original payload and explicit metadata are unchanged.\n"
        "This is an installer disc for RPCS3. No retail console compatibility or runtime test is claimed.\n",
        encoding='utf8')
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original', type=Path)
    parser.add_argument('package', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    p = plan(args.original, args.package)
    print(json.dumps(public_plan(p), indent=2), flush=True)
    if not args.write:
        print('Dry run: nothing written. Review the plan, then use --write with a fresh output path.')
        return
    audit = write_iso(p, args.output)
    print('Verified ISO:', args.output)
    print('SHA-256:', audit['output_sha256'])


if __name__ == '__main__':
    main()
