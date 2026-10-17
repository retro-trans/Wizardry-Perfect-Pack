"""Inspect retail PS3 PKG files; extraction requires --extract DIRECTORY.

Reads local packages only. Does not install a game or use/change RAP licenses.
Format reference: RPCS3/rpcs3, rpcs3/Crypto/unpkg.{cpp,h} and key_vault.h.
Requires cryptography. Original package files are always opened read-only.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import struct

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

PKG_KEY = bytes.fromhex('2e7b71d7c9c9a14ea3221f188828b8f8')


class Package:
    def __init__(self, path):
        self.path = Path(path)
        self.stream = self.path.open('rb')
        header = self.stream.read(0xc0)
        if len(header) != 0xc0 or header[:8] != bytes.fromhex('7f504b4780000001'):
            raise ValueError('Only retail PS3 packages are supported')
        self.count = struct.unpack_from('>I', header, 0x14)[0]
        total, self.start, self.size = struct.unpack_from('>QQQ', header, 0x18)
        if total != self.path.stat().st_size or self.start + self.size > total:
            raise ValueError('Package size mismatch')
        if self.count * 32 > self.size:
            raise ValueError('Invalid entry count')
        self.content_id = header[0x30:0x60].rstrip(b'\0').decode('ascii')
        self.iv = int.from_bytes(header[0x70:0x80], 'big')
        table = self.read(0, self.count * 32)
        self.entries = []
        names = set()
        for i in range(self.count):
            no, ns, offset, size, flags, reserved = struct.unpack_from('>IIQQII', table, i*32)
            name = self.read(no, ns).rstrip(b'\0').decode('utf-8')
            parts = PurePosixPath(name).parts
            if (not parts or name.startswith('/') or '\\' in name or ':' in name
                    or any(p in ('.', '..') for p in name.split('/')) or '\0' in name):
                raise ValueError('Unsafe entry path')
            if name.casefold() in names or offset + size > self.size:
                raise ValueError('Duplicate name or out-of-bounds entry')
            names.add(name.casefold())
            kind = flags & 0xff
            if kind not in (1, 2, 3, 4, 9):
                raise ValueError('Unsupported entry type: %x' % flags)
            self.entries.append(dict(path=name, offset=offset, size=size,
                                     flags=flags, directory=kind == 4))

    def read(self, offset, size):
        if offset < 0 or size < 0 or offset + size > self.size:
            raise ValueError('Read outside package data')
        block, skip = divmod(offset, 16)
        self.stream.seek(self.start + block*16)
        cipher = Cipher(algorithms.AES(PKG_KEY), modes.CTR((self.iv+block).to_bytes(16, 'big')))
        data = self.stream.read(size+skip)
        if len(data) != size+skip:
            raise ValueError('Truncated package')
        return cipher.decryptor().update(data)[skip:]

    def close(self):
        self.stream.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    parser.add_argument('--extract', type=Path)
    args = parser.parse_args()
    pkg = Package(args.package)
    try:
        files = [e for e in pkg.entries if not e['directory']]
        print(pkg.content_id)
        print('%d files, %d directories, %d bytes of file data' % (
            len(files), pkg.count-len(files), sum(e['size'] for e in files)))
        print(json.dumps(Counter(Path(e['path']).suffix.lower() for e in files), sort_keys=True))
        print('Sample paths:', ', '.join(e['path'] for e in files[:10]))
        if args.extract is None:
            print('Dry run: nothing written. Use --extract DIRECTORY to extract into a new folder.')
            return
        root = args.extract.resolve()
        if root.exists():
            raise ValueError('Extraction destination must not exist')
        # Resolve every target before making the destination; refuse symlink escapes.
        for e in pkg.entries:
            target = (root / e['path']).resolve()
            if root not in target.parents:
                raise ValueError('Path leaves destination')
        root.mkdir(parents=True)
        for e in pkg.entries:
            target = root / e['path']
            if e['directory']:
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256()
            with target.open('xb') as out:
                for offset in range(0, e['size'], 4*1024*1024):
                    chunk = pkg.read(e['offset']+offset, min(4*1024*1024, e['size']-offset))
                    out.write(chunk)
                    digest.update(chunk)
            e['sha256'] = digest.hexdigest()
        (root / '_package_inventory.json').write_text(json.dumps(dict(
            source=args.package.name, content_id=pkg.content_id, entries=pkg.entries), indent=2), encoding='utf-8')
        print('Extracted to', root)
    finally:
        pkg.close()


if __name__ == '__main__':
    main()
