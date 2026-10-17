"""Authenticate and inspect the protected dungeon scene archives.

Default is a dry run: decrypts in memory and reports text field locations.
--write exports source rows and decoded assets under ignored work folders only.
No keys are printed or saved. This module does not create encrypted EDAT files.
Format reference: RPCS3 rpcs3/Crypto/unedat.cpp (NPD v2, EDAT flags 0x0c).
"""
import argparse
import hashlib
import hmac
import json
from pathlib import Path
import re
import struct

from embedded_event import aes, cmac, recover, OMAC2, OMAC3, EDAT_KEY
from enc_archive import unpack

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'work/source/NPJB00162/USRDIR'
NAME_CAPACITY = 53
JA = re.compile('[\u3040-\u30ff\u3400-\u9fff\uff66-\uff9f]')
_keys = {}


def decrypt_scene(data, executable, name):
    """Return an authenticated, structurally validated decoded ENC archive.

    Accepts only the supplied game's NPD v2/license 3/flags 0x0c variant.
    The executable supplies its own embedded key; no external licenses are used.
    Both NPD hashes and every encrypted block CMAC must match before returning.
    """
    if len(data) < 0x100 or data[:4] != b'NPD\0':
        raise ValueError('Missing or truncated NPD header: '+name)
    version, license_type = struct.unpack_from('>II', data, 4)
    flags, block_size, plain_size = struct.unpack_from('>IIQ', data, 0x80)
    if (version, license_type, flags, block_size) != (2, 3, 0x0c, 0x4000):
        raise ValueError('Unsupported dungeon EDAT variant: '+name)
    if not plain_size:
        raise ValueError('Empty dungeon EDAT: '+name)
    if not hmac.compare_digest(cmac(OMAC3, data[0x10:0x40]+name.encode('ascii')), data[0x50:0x60]):
        raise ValueError('NPD title hash mismatch: '+name)
    fingerprint = hashlib.sha256(executable).digest()
    key = _keys.get(fingerprint)
    if key is None or not hmac.compare_digest(cmac(bytes(a^b for a,b in zip(key, OMAC2)), data[:0x60]), data[0x60:0x70]):
        key, _offset = recover(executable, data)
        _keys[fingerprint] = key
    if not hmac.compare_digest(cmac(bytes(a^b for a,b in zip(key, OMAC2)), data[:0x60]), data[0x60:0x70]):
        raise ValueError('NPD developer hash mismatch: '+name)
    count = (plain_size+block_size-1)//block_size
    payload_start = 0x100+count*16
    if payload_start+(plain_size+15)//16*16 > len(data):
        raise ValueError('Truncated dungeon block table or payload: '+name)
    output = bytearray()
    for index in range(count):
        length = min(block_size, plain_size-index*block_size)
        offset = payload_start+index*block_size
        payload = data[offset:offset+(length+15)//16*16]
        derived = aes(key, data[0x60:0x6c]+struct.pack('>I', index), encrypt=True)
        # Flag 0x08 wraps the AES and CMAC key in the version-0 EDAT key.
        block_key = aes(EDAT_KEY, derived, bytes(16))
        expected = data[0x100+index*16:0x110+index*16]
        if not hmac.compare_digest(cmac(block_key, payload), expected):
            raise ValueError('Dungeon block authentication failed: %s block %d' % (name, index))
        output.extend(aes(block_key, payload, data[0x40:0x50])[:length])
    plain = bytes(output)
    inspect_scene(plain, name)
    return plain


def inspect_scene(plain, name):
    """Validate the four-member schema and return decoded members and audit."""
    members = unpack(plain)
    if len(members) != 4 or len(members[0]) != 62 or len(members[2]) != 4:
        raise ValueError('Unexpected dungeon ENC member schema: '+name)
    if len(members[1]) % 18 or len(members[1])//18 != members[0][54]:
        raise ValueError('Unexpected dungeon floor-record count: '+name)
    field = members[0][:NAME_CAPACITY]
    if b'\0' not in field:
        raise ValueError('Unterminated dungeon name: '+name)
    text_bytes, padding = field.split(b'\0', 1)
    text = text_bytes.decode('utf8')
    if not text or any(padding) or any(ord(c) < 32 for c in text):
        raise ValueError('Unexpected dungeon name field: '+name)
    if members[3]:
        from PIL import Image
        import io
        with Image.open(io.BytesIO(members[3])) as image:
            if image.format != 'TGA' or image.size != (1280, 720):
                raise ValueError('Unexpected dungeon background format: '+name)
            image.verify()
    table = []
    for index, member in enumerate(members):
        packed, length, offset = struct.unpack_from('<III', plain, 4+12*index)
        table.append(dict(member=index, offset=offset, packed_bytes=packed & 0x7fffffff,
                          compressed=bool(packed >> 31), decoded_bytes=length,
                          sha256=hashlib.sha256(member).hexdigest()))
    return members, dict(archive=name, name=text, name_capacity=NAME_CAPACITY,
                         floor_count=members[0][54], floor_record_bytes=18,
                         metadata_tail_hex=members[0][NAME_CAPACITY:].hex(),
                         plaintext_sha256=hashlib.sha256(plain).hexdigest(),
                         authenticated=True, members=table)


def collect(source=SOURCE, executable=None):
    """Return deduplicated Japanese location rows with exact member coordinates."""
    source = Path(source)
    executable = (source/'EBOOT.elf').read_bytes() if executable is None else executable
    rows, by_text = [], {}
    for path in sorted((source/'data/obj/Scenes').glob('dun[0-9][0-9].edat')):
        plain = decrypt_scene(path.read_bytes(), executable, path.name)
        members, audit = inspect_scene(plain, path.name)
        text = audit['name']
        if not JA.search(text):
            continue
        if text not in by_text:
            row = dict(id='L%04d' % len(rows), ja=text, kind='dungeon_name',
                       occurrences=[], contexts=[])
            rows.append(row)
            by_text[text] = row
        row = by_text[text]
        row['occurrences'].append(dict(archive=path.name, member=0, offset=0,
                                       capacity=NAME_CAPACITY, kind='dungeon_name',
                                       terminated=True, valid_utf8=True,
                                       raw_sha256=hashlib.sha256(members[0][:NAME_CAPACITY]).hexdigest()))
        row['contexts'].append(dict(archive=path.name, floor_count=audit['floor_count'],
                                    note='Shared dungeon selection and dungeon header display name.'))
    if not rows:
        raise ValueError('No dungeon source rows found')
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    executable = (SOURCE/'EBOOT.elf').read_bytes()
    rows = collect(executable=executable)
    decoded, audits = [], []
    for path in sorted((SOURCE/'data/obj/Scenes').glob('dun[0-9][0-9].edat')):
        plain = decrypt_scene(path.read_bytes(), executable, path.name)
        members, audit = inspect_scene(plain, path.name)
        decoded.append((path.name, plain, members))
        audits.append(audit)
    report = dict(archives=len(audits), rows=len(rows),
                  occurrences=sum(len(row['occurrences']) for row in rows),
                  name_capacity=NAME_CAPACITY, samples=rows[:2], audits=audits)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.write:
        # All destinations are fixed ignored paths. Original inputs are untouched.
        targets = [(ROOT/'work/translation/ja/dungeons.json',
                    (json.dumps(rows, ensure_ascii=False, indent=2)+'\n').encode('utf8'))]
        for name, plain, members in decoded:
            base = ROOT/'work/source/decoded/USRDIR/data/obj/Scenes'/name
            targets.append((base/'archive.enc', plain))
            for index, member in enumerate(members):
                targets.append((base/('%04d.%s' % (index, 'tga' if index == 3 and member else 'dat')), member))
        targets.append((ROOT/'work/source/decoded/dungeons.audit.json',
                        (json.dumps(audits, ensure_ascii=False, indent=2)+'\n').encode('utf8')))
        for path, data in targets:
            if path.exists() and path.read_bytes() != data:
                raise ValueError('Refusing to overwrite differing decoded output: '+str(path))
        for path, data in targets:
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_bytes(data)
        print('Saved authenticated decoded assets and source rows under ignored work folders.')
    else:
        print('Dry run: all archives authenticated in memory; nothing written.')


if __name__ == '__main__':
    main()
