"""Count Japanese text without modifying game files. Default: dry run.

--write exports Japanese review text only under ignored work/output/.
Event records are parsed structurally and round-tripped byte for byte.
Executable strings remain candidates, including internal/debug labels.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import struct
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
JAPANESE = re.compile(r'[\u3040-\u30ff\u3400-\u9fff\uff66-\uff9f]')
# Valid UTF-8 only, including printable ASCII and common whitespace.
UTF8_STRING = re.compile(
    rb'(?:[\x09\x0a\x0d\x20-\x7e]|[\xc2-\xdf][\x80-\xbf]|'
    rb'\xe0[\xa0-\xbf][\x80-\xbf]|[\xe1-\xec\xee-\xef][\x80-\xbf]{2}|'
    rb'\xed[\x80-\x9f][\x80-\xbf]|\xf0[\x90-\xbf][\x80-\xbf]{2}|'
    rb'[\xf1-\xf3][\x80-\xbf]{3}|\xf4[\x80-\x8f][\x80-\xbf]{2})+\x00')
EVENT_TYPES = {0x43: 'speaker', 0x49: 'dialogue', 0x46: 'narration_message', 0x2b: 'choice'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def summary(rows):
    texts = [r['text'] for r in rows]
    return dict(occurrences=len(texts), unique=len(set(texts)),
                characters=sum(map(len, texts)), unique_characters=sum(map(len, set(texts))))


def events(root):
    rows, files = [], []
    paths = sorted(root.rglob('*.evt')) + sorted(root.rglob('*.edat.unedat'))
    for path in paths:
        if '/event/' not in path.as_posix():
            continue
        data = path.read_bytes()
        offset = index = 0
        rebuilt = bytearray()
        local = []
        while offset < len(data):
            if offset + 8 > len(data):
                raise ValueError('Truncated event header: %s at %x' % (path, offset))
            opcode, size = struct.unpack_from('<II', data, offset)
            end = offset + 8 + size
            if end > len(data) or size % 4:
                raise ValueError('Invalid event payload: %s at %x' % (path, offset))
            payload = data[offset+8:end]
            rebuilt.extend(struct.pack('<II', opcode, size))
            rebuilt.extend(payload)
            try:
                text = payload.rstrip(b'\0').decode('utf-8')
            except UnicodeDecodeError:
                text = ''
            if JAPANESE.search(text):
                if opcode not in EVENT_TYPES or '\0' in text:
                    raise ValueError('Unknown Japanese event payload: %s at %x' % (path, offset))
                row = dict(file=path.relative_to(root).as_posix(), offset=offset,
                           record=index, opcode=opcode, payload_bytes=size,
                           kind=EVENT_TYPES[opcode], text=text)
                rows.append(row)
                local.append(row)
            offset, index = end, index+1
        if bytes(rebuilt) != data:
            raise ValueError('Event round-trip mismatch: %s' % path)
        files.append(dict(file=path.relative_to(root).as_posix(), bytes=len(data),
                          records=index, sha256=digest(data), japanese=summary(local), roundtrip=True))
    return rows, files


def executable(path):
    data = path.read_bytes()
    if data[:6] != b'\x7fELF\x02\x02':
        raise ValueError('Expected a big-endian ELF64 executable')
    h = struct.unpack_from('>HHIQQQIHHHHHH', data, 16)
    sections = [struct.unpack_from('>IIQQQQIIQQ', data, h[5]+i*h[10]) for i in range(h[11])]
    rows, spans = [], []
    # Read-only, allocated, non-executable PROGBITS. Section names are stripped.
    # Excludes instructions and writable tables that produce spurious UTF-8.
    for i, s in enumerate(sections):
        if s[1] != 1 or s[2] & 7 != 2:
            continue
        address, offset, size = s[3:6]
        if offset + size > len(data):
            raise ValueError('ELF section outside file')
        spans.append(dict(section=i, address=address, offset=offset, bytes=size))
        for m in UTF8_STRING.finditer(data[offset:offset+size]):
            text = m[0][:-1].decode('utf-8')
            if JAPANESE.search(text):
                rows.append(dict(file=path.name, offset=offset+m.start(),
                                 address=address+m.start(), section=i,
                                 kind='executable_candidate', text=text))
    return rows, dict(file=path.name, sha256=digest(data), inspected_sections=spans)


def trophies(root):
    rows = []
    for path in sorted(root.rglob('*.TRP')):
        data = path.read_bytes()
        if data[:4] != bytes.fromhex('dca24d00'):
            raise ValueError('Unexpected trophy archive')
        count, stride = struct.unpack_from('>II', data, 0x10)
        if stride != 64 or 64+count*stride > len(data):
            raise ValueError('Invalid trophy archive table')
        for off in range(64, 64+count*stride, stride):
            name = data[off:off+32].split(b'\0')[0].decode('ascii')
            start, size = struct.unpack_from('>QQ', data, off+32)
            if start+size > len(data):
                raise ValueError('Trophy entry outside archive')
            if name != 'TROP.SFM':
                continue
            xml = ET.fromstring(data[start:start+size])
            for index, element in enumerate(xml.iter()):
                text = element.text or ''
                if JAPANESE.search(text):
                    rows.append(dict(file=path.relative_to(root).as_posix(), member=name,
                                     element=index, tag=element.tag, kind='trophy', text=text))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'work/source/NPJB00162')
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    event_rows, files = events(args.source)
    exe_rows, exe_info = executable(args.source/'USRDIR/EBOOT.elf')
    trophy_rows = trophies(args.source)
    kinds = defaultdict(list)
    for row in event_rows:
        kinds[row['kind']].append(row)
    report = dict(title_id='NPJB00162', date='2026-10-17',
                  event_files=len(files), event_files_with_japanese=sum(bool(f['japanese']['occurrences']) for f in files),
                  event_roundtrips_passed=len(files), event=summary(event_rows),
                  event_by_kind={k: summary(v) for k,v in kinds.items()},
                  executable_candidates=summary(exe_rows), executable=exe_info,
                  trophy=summary(trophy_rows),
                  combined_candidates=summary(event_rows+exe_rows+trophy_rows),
                  caveats=['Executable candidates include diagnostic and internal asset labels; player visibility is unverified.',
                           'Counts are source strings, not screen lines or a percentage of the complete game.',
                           'Graphics, movie text, additional downloads and executable reinsertion are not verified.',
                           'Event role labels are inferred from payload samples, not runtime tracing.',
                           'No game files were modified or translated.'])
    print(json.dumps(report, indent=2))
    if args.write:
        out = ROOT/'work/output/text_census'
        out.mkdir(parents=True, exist_ok=True)
        for name, value in [('summary.json', report), ('events.ja.json', event_rows),
                            ('executable_candidates.ja.json', exe_rows), ('trophies.ja.json', trophy_rows),
                            ('event_files.json', files)]:
            (out/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print('Wrote review exports to', out)
    else:
        print('Dry run: nothing written. Use --write to export the census and local review text.')


if __name__ == '__main__':
    main()
