"""Inspect PAMF packs or replace AVC access units without moving any other byte.

Read-only unless --write is supplied. The replacement path is experimental;
passing structural checks does not establish PS3 playback compatibility.
Format references: RPCS3 cellPamf.h and cellDmuxPamf.cpp.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'work/source/NPJB00162/USRDIR/movie/opening.pam'
EXPECTED = 'a6873df0b1e506b4afd29e2f6fb603957410bf8f4d44aa0c6432f7f7c7d423bd'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inspect(data):
    assert data[:8] == b'PAMF0041', 'Unsupported PAMF header'
    start = int.from_bytes(data[8:12], 'big') * 2048
    length = int.from_bytes(data[12:16], 'big') * 2048
    assert start + length == len(data), 'Header size does not match file'
    spans, counts, private, maps, timestamps = [], Counter(), bytearray(), [], []
    untouched = hashlib.sha256(data[:start])
    for offset in range(start, len(data), 2048):
        pack = data[offset:offset + 2048]
        assert pack[:4] == b'\0\0\1\xba', ('Missing sector pack header', offset)
        pos = 14 + (pack[13] & 7)
        while pack[pos:pos + 4] in (b'\0\0\1\xbb', b'\0\0\1\xbf'):
            size = 6 + int.from_bytes(pack[pos + 4:pos + 6], 'big')
            if pack[pos + 3] == 0xbf:
                maps.append((offset + pos, size, sha(pack[pos:pos + size])))
            pos += size
        assert pack[pos:pos + 3] == b'\0\0\1', ('Bad PES prefix', offset)
        sid = pack[pos + 3]
        counts[hex(sid)] += 1
        end = pos + 6 + int.from_bytes(pack[pos + 4:pos + 6], 'big')
        payload = pos + 9 + pack[pos + 8]
        assert pos < payload < end <= 2048, ('Invalid PES bounds', offset)
        if pack[pos + 7] & 0xc0:
            timestamps.append((offset + pos + 7, pack[pos + 7:payload].hex()))
        if sid == 0xe0:
            spans.append((offset + payload, end - payload))
            untouched.update(pack[:payload])
            untouched.update(pack[end:])
        elif sid == 0xbd:
            private.extend(pack[pos:end])
            untouched.update(pack)
        else:
            raise AssertionError(('Unexpected stream', sid))
    elementary = b''.join(data[p:p + size] for p, size in spans)
    report = dict(source_sha256=sha(data), bytes=len(data), header_bytes=start,
                  declared_stream_bytes=length, streams=dict(counts),
                  video_bytes=len(elementary), private_packet_sha256=sha(private),
                  random_access_maps=len(maps),
                  random_access_map_sha256=sha(json.dumps(maps).encode()),
                  timestamp_headers=len(timestamps),
                  timestamp_headers_sha256=sha(json.dumps(timestamps).encode()),
                  header_sha256=sha(data[:start]),
                  all_non_video_bytes_sha256=untouched.hexdigest())
    return report, spans, elementary


def ffprobe(path):
    result = subprocess.run(['ffprobe', '-v', 'error', '-f', 'mpeg',
        '-select_streams', 'v', '-show_packets', '-show_entries',
        'packet=pts,dts,size,flags', '-of', 'json', str(path)],
        capture_output=True, check=True)
    return json.loads(result.stdout)['packets']


def strip_sei(data):
    # Remove only encoder-identification user-data SEI (payload type 5).
    # HRD buffering-period/picture-timing SEI is essential when timestamps
    # are sparse in the source PES stream and must remain intact.
    starts = list(re.finditer(b'\x00\x00(?:\x00)?\x01', data))
    result = bytearray()
    for i, match in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(data)
        if not (data[match.end()] & 31 == 6 and data[match.end()+1] == 5):
            result.extend(data[match.start():end])
    return bytes(result)


def replacement(source, encoded, packet_plan):
    """Return an equal-size copy, failing before writing on any unsafe fit."""
    original_report, spans, original_es = inspect(source)
    original_packets = ffprobe(SOURCE)
    original_plan = json.loads(packet_plan.read_text(encoding='utf8'))
    encoded_bytes = encoded.read_bytes()
    assert len(original_packets) == len(original_plan), 'Frame count differs'
    assert sum(int(p['size']) for p in original_packets) == len(original_es)
    units, offset, original_offset, overflows, encoder_dts_differences = [], 0, 0, [], []
    for i, (old, new) in enumerate(zip(original_packets, original_plan)):
        # Input plan is in decode order. Packet PTS is relative to the first
        # display frame and measured at 1/30000, versus source 1/90000.
        assert int(old['pts']) - 90000 == int(new['pts']) * 3, ('PTS order differs', i)
        if int(old['dts']) - 90000 != int(new['dts']) * 3:
            # The isolated source IDR at display frame 54 forms a one-picture
            # encoder segment. Its encoder omits the usual one-picture delay.
            # Retain the source's EARLIER decode time, with identical display
            # time and decode order; rebuilt packet timestamps are checked too.
            assert i == 54 and int(new['pts']) == int(new['dts']), ('Unexpected encoder DTS',i)
            assert int(new['dts'])*3 - (int(old['dts'])-90000) == 3003
            encoder_dts_differences.append(dict(frame=i, reason='isolated one-picture IDR; original decode time retained'))
        assert ('K' in old['flags']) == bool(new['keyframe']), ('RAP differs', i)
        unit = strip_sei(encoded_bytes[offset:offset + new['size']])
        offset += new['size']
        budget = int(old['size'])
        old_unit = original_es[original_offset:original_offset+budget]
        original_offset += budget
        def idr(blob):
            return any(blob[m.end()] & 31 == 5 for m in re.finditer(b'\x00\x00(?:\x00)?\x01',blob))
        assert idr(old_unit) == idr(unit), ('IDR boundary differs',i)
        if len(unit) > budget:
            overflows.append(dict(frame=i, capacity=budget, encoded=len(unit)))
        else:
            remaining = budget - len(unit)
            # Annex B filler_data NAL or legal trailing_zero_8bits for tiny gaps.
            pad = (b'\0\0\1\x0c' + b'\xff' * (remaining - 5) + b'\x80'
                   if remaining >= 5 else b'\0' * remaining)
            units.append(unit + pad)
    assert offset == len(encoded_bytes)
    if overflows:
        raise ValueError('Encoded frames exceed original allocation: ' + json.dumps(overflows[:20]) + '; total=' + str(len(overflows)))
    new_es = b''.join(units)
    assert len(new_es) == len(original_es)
    output, offset = bytearray(source), 0
    for pos, size in spans:
        output[pos:pos + size] = new_es[offset:offset + size]
        offset += size
    rebuilt_report, rebuilt_spans, _ = inspect(output)
    assert rebuilt_spans == spans
    for key in ('bytes', 'header_sha256', 'private_packet_sha256',
                'random_access_map_sha256', 'timestamp_headers_sha256', 'all_non_video_bytes_sha256'):
        assert original_report[key] == rebuilt_report[key], ('Preservation failed', key)
    rebuilt_report['preserved'] = ['all non-video bytes', 'source file size',
        'every video access-unit byte offset and size', 'all audio PES bytes',
        'all PES timestamps', 'all original random-access maps', 'PAMF header']
    rebuilt_report['ps3_playback_verified'] = False
    rebuilt_report['encoder_dts_differences'] = encoder_dts_differences
    return output, rebuilt_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--encoded', type=Path)
    parser.add_argument('--packet-plan', type=Path)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT/'work/output/movie/opening.en.experimental.pam')
    args = parser.parse_args()
    original = SOURCE.read_bytes()
    assert sha(original) == EXPECTED, 'Source movie hash changed'
    report, _, _ = inspect(original)
    output = None
    if args.encoded:
        assert args.packet_plan, '--packet-plan required'
        output, report = replacement(original, args.encoded, args.packet_plan)
    print(json.dumps(report, indent=2))
    if args.write:
        target = args.output.resolve()
        allowed = (ROOT/'work/output/movie').resolve()
        assert allowed in target.parents, 'Output must remain in ignored movie directory'
        target.parent.mkdir(parents=True, exist_ok=True)
        if output is not None:
            target.write_bytes(output)
        target.with_suffix('.audit.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf8')
        assert sha(SOURCE.read_bytes()) == EXPECTED, 'Original changed'
    else:
        print('Dry run: no files written.')


if __name__ == '__main__':
    main()
