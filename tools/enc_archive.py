"""Inspect/extract the game's LZO1X ENC containers. Default is read-only.

Use a 64-bit Python with lzokay and Pillow installed. Member IDs are positional;
empty members must be retained. No archive is changed by extraction.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]


def unpack(data):
    import lzokay
    if len(data) < 4:
        raise ValueError('Truncated archive')
    count = struct.unpack_from('<I', data)[0]
    if count > 65536 or 4 + 12*count > len(data):
        raise ValueError('Invalid member count')
    members = []
    for index in range(count):
        packed, size, offset = struct.unpack_from('<III', data, 4+index*12)
        length = packed & 0x7fffffff
        if offset < 4+12*count or offset+length > len(data):
            raise ValueError('Member outside archive')
        chunk = data[offset:offset+length]
        decoded = lzokay.decompress(chunk, size) if packed >> 31 else chunk
        if len(decoded) != size:
            raise ValueError('Decoded size mismatch')
        members.append(decoded)
    return members


def pack(members, compress=True):
    import lzokay
    table = bytearray(struct.pack('<I', len(members))+b'\0'*(12*len(members)))
    table.extend(b'\0'*(-len(table) % 16))
    for index, data in enumerate(members):
        chunk = lzokay.compress(data) if compress and data else data
        flag = 0x80000000 if compress and data else 0
        struct.pack_into('<III', table, 4+index*12, len(chunk)|flag, len(data), len(table))
        table.extend(chunk)
        table.extend(b'\0'*(-len(table) % 16))
    result = bytes(table)
    if unpack(result) != members:
        raise ValueError('Repacked archive does not round-trip')
    return result


def main():
    from PIL import Image, ImageDraw
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'work/source/NPJB00162')
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    output = ROOT/'work/output/graphics'
    records, thumbs = [], []
    for path in sorted(args.source.rglob('*.enc')):
        members = unpack(path.read_bytes())
        rel = path.relative_to(args.source)
        for index, data in enumerate(members):
            row = dict(file=rel.as_posix(), member=index, bytes=len(data),
                       sha256=hashlib.sha256(data).hexdigest())
            if not data:
                row['kind'] = 'empty'
            else:
                try:
                    im = Image.open(io.BytesIO(data))
                    row.update(kind='image', format=im.format, width=im.width, height=im.height)
                    if args.write:
                        dest = output/rel/('%04d.png' % index)
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        im.save(dest)
                        thumb = im.convert('RGBA')
                        thumb.thumbnail((320, 180))
                        tile = Image.new('RGB', (340, 218), '#707070')
                        tile.paste(thumb, ((340-thumb.width)//2, 24), thumb)
                        ImageDraw.Draw(tile).text((4, 4), rel.name+' / '+str(index), fill='white')
                        thumbs.append(tile)
                except (OSError, ValueError):
                    row['kind'] = 'binary'
                    if args.write:
                        dest = ROOT/'work/source/decoded'/rel/('%04d.dat' % index)
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_bytes(data)
            records.append(row)
    print(json.dumps(dict(archives=len(set(r['file'] for r in records)), members=len(records),
                         images=sum(r['kind']=='image' for r in records),
                         binary=sum(r['kind']=='binary' for r in records), samples=records[:6]), indent=2))
    if args.write:
        output.mkdir(parents=True, exist_ok=True)
        (output/'inventory.json').write_text(json.dumps(records, indent=2)+'\n', encoding='utf8')
        for page in range(0, len(thumbs), 24):
            sheet = Image.new('RGB', (4*340, 6*218), '#202020')
            for j, tile in enumerate(thumbs[page:page+24]):
                sheet.paste(tile, ((j%4)*340, (j//4)*218))
            sheet.save(output/('contact-%03d.jpg' % (page//24)))
        print('Saved graphics previews and binary members under ignored work folders.')
    else:
        print('Dry run: no files written.')


if __name__ == '__main__':
    main()
