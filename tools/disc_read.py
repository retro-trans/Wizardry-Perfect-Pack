"""Read the ISO9660 view of the supplied disc. Dry run unless --extract is used.

The disc's UDF metadata is rejected by common readers; the separate ISO9660
directory tree is checked against the physical image bounds instead.
"""
import argparse
import json
from pathlib import Path, PurePosixPath
import struct


class Disc:
    def __init__(self, path):
        self.path = Path(path)
        self.stream = self.path.open('rb')
        self.size = self.path.stat().st_size
        pvd = self.read(16 * 2048, 2048)
        if pvd[:7] != b'\x01CD001\x01':
            raise ValueError('No ISO9660 primary volume descriptor')
        if struct.unpack_from('<H', pvd, 128)[0] != 2048:
            raise ValueError('Unexpected logical block size')
        self.entries = []
        root = pvd[156:190]
        self.walk('', self.record(root), set())
        merged = []
        for entry in self.entries:
            if merged and merged[-1]['path'] == entry['path']:
                prior = merged[-1]
                if not prior.pop('continued', False) or prior['directory'] or entry['directory']:
                    raise ValueError('Unexpected duplicate path')
                prior['extents'].append((entry['offset'], entry['size']))
                prior['size'] += entry['size']
                prior['continued'] = entry['continued']
            else:
                row = dict(entry)
                row['extents'] = [(entry['offset'], entry['size'])]
                merged.append(row)
        if any(e['continued'] for e in merged):
            raise ValueError('Unfinished multi-extent file')
        self.entries = merged

    def read(self, offset, size):
        if offset < 0 or size < 0 or offset + size > self.size:
            raise ValueError('Extent outside image')
        self.stream.seek(offset)
        data = self.stream.read(size)
        if len(data) != size:
            raise ValueError('Truncated image')
        return data

    @staticmethod
    def record(raw):
        if len(raw) < 34:
            raise ValueError('Truncated directory record')
        sector, size = struct.unpack_from('<I', raw, 2)[0], struct.unpack_from('<I', raw, 10)[0]
        if sector != struct.unpack_from('>I', raw, 6)[0] or size != struct.unpack_from('>I', raw, 14)[0]:
            raise ValueError('Directory endian copies disagree')
        name = raw[33:33 + raw[32]].decode('ascii')
        return dict(name=name.split(';')[0], offset=sector * 2048, size=size,
                    directory=bool(raw[25] & 2), continued=bool(raw[25] & 128))

    def walk(self, prefix, entry, visited):
        if entry['offset'] in visited:
            raise ValueError('Directory cycle')
        visited.add(entry['offset'])
        data = self.read(entry['offset'], entry['size'])
        at = 0
        while at < len(data):
            size = data[at]
            if not size:
                at = (at // 2048 + 1) * 2048
                continue
            raw = data[at:at + size]
            if len(raw) != size:
                raise ValueError('Directory record outside extent')
            row = self.record(raw)
            at += size
            if row['name'] in ('\x00', '\x01'):
                continue
            if '/' in row['name'] or '\\' in row['name'] or ':' in row['name'] or row['name'] in ('.', '..'):
                raise ValueError('Unsafe path')
            row['path'] = prefix + '/' + row.pop('name')
            self.read(row['offset'], min(row['size'], 64))
            self.entries.append(row)
            if row['directory']:
                self.walk(row['path'], row, visited)

    def extract(self, names, destination):
        selected = [e for e in self.entries if e['path'] in names and not e['directory']]
        if len(selected) != len(names):
            raise ValueError('Missing or duplicate selected path')
        destination = Path(destination)
        targets = [(e, destination.joinpath(*PurePosixPath(e['path']).parts[1:])) for e in selected]
        if any(p.exists() for e, p in targets):
            raise ValueError('Extraction would overwrite a file')
        for entry, target in targets:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as output:
                for pos, left in entry['extents']:
                    while left:
                        chunk = self.read(pos, min(left, 4 * 1024 * 1024))
                        output.write(chunk)
                        pos += len(chunk)
                        left -= len(chunk)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('disc', type=Path)
    parser.add_argument('--path', action='append', default=[])
    parser.add_argument('--extract', type=Path)
    args = parser.parse_args()
    disc = Disc(args.disc)
    try:
        print(json.dumps(disc.entries, indent=2))
        if args.extract:
            if not args.path:
                raise ValueError('Explicit --path selection required')
            disc.extract(args.path, args.extract)
            print('Extracted selected files into', args.extract)
        else:
            print('Dry run: no files written.')
    finally:
        disc.stream.close()


if __name__ == '__main__':
    main()
