"""Render the translated opening into an intermediate AVC elementary stream.

Dry-run by default. Requires Python 3.12 with PyAV, NumPy and Pillow.
Tested with PyAV 19.0.1 installed locally in work/source/pamf/python.
English subtitles appear below the original Japanese lettering. No image area
is covered or masked. This step alone does not install a movie patch; VUI
restoration and independent verification are required.
"""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'work/source/pamf/python'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--crf', type=int, default=28)
    args = parser.parse_args()
    source = ROOT/'work/source/NPJB00162/USRDIR/movie/opening.pam'
    spec = json.loads((ROOT/'work/translation/en/graphics/opening.en.json').read_text(encoding='utf8'))
    assert hashlib.sha256(source.read_bytes()).hexdigest() == spec['source_sha256']
    from check_movie_captions import check
    check()
    print(json.dumps(dict(source=str(source), subtitles=len(spec['subtitle_segments']), crf=args.crf,
        output='work/output/movie/opening.rendered.h264',
        method='Preserve original imagery and Japanese lettering; add outlined bottom subtitles; preserve picture types and frame times.'), indent=2))
    if not args.write:
        print('Dry run: no files written.')
        return
    import av
    from movie_subtitles import font_for,draw_subtitle
    frame_cache = ROOT/'work/output/movie/original-frames.json'
    if frame_cache.exists():
        frames = json.loads(frame_cache.read_text(encoding='utf8'))['frames']
    else:
        result = subprocess.run(['ffprobe','-v','error','-f','mpeg',
            '-select_streams','v','-show_frames','-show_entries',
            'frame=best_effort_timestamp,key_frame,pict_type','-of','json',str(source)],
            capture_output=True,check=True)
        frames = json.loads(result.stdout)['frames']
        frame_cache.parent.mkdir(parents=True,exist_ok=True)
        frame_cache.write_bytes(result.stdout)
    assert len(frames)==2210
    assert all(f['best_effort_timestamp']==90000+i*3003 for i,f in enumerate(frames))
    font = font_for(spec['style'])
    from movie_pamf import inspect, ffprobe
    _, _, source_es = inspect(source.read_bytes())
    source_packets = ffprobe(source)
    idr_frames, offset = set(), 0
    for packet in source_packets:
        blob = source_es[offset:offset+int(packet['size'])]
        offset += int(packet['size'])
        if any(blob[m.end()] & 31 == 5 for m in re.finditer(b'\x00\x00(?:\x00)?\x01', blob)):
            idr_frames.add((int(packet['pts'])-90000)//3003)
    print('Preserving IDR display frames', sorted(idr_frames), flush=True)
    def context(start_frame=0):
        ctx = av.CodecContext.create('libx264', 'w')
        ctx.width, ctx.height, ctx.pix_fmt = 1280, 720, 'yuv420p'
        ctx.time_base, ctx.framerate = Fraction(1, 30000), Fraction(30000, 1001)
        # A single slice avoids per-slice overhead on the original 107-byte
        # held/black pictures, leaving room for the preserved timing SEI.
        ctx.thread_count = 1
        params = 'threads=1:sliced-threads=0:slices=1:fps=30000/1001:force-cfr=1:aud=1:repeat-headers=1:bframes=1:b-adapt=0:b-pyramid=none:open-gop=1:scenecut=0:keyint=9999:min-keyint=1:ref=1:colorprim=bt709:transfer=bt709:colormatrix=bt709:nal-hrd=vbr:vbv-maxrate=20000:vbv-bufsize=20000:pic-struct=1'
        if start_frame == 1024:
            # One tightly allocated flash-transition IDR. Subsequent pictures
            # immediately return to the requested CRF quality.
            params += ':zones=0,0,q=48'
        ctx.options = {'preset':'medium', 'crf':str(args.crf), 'profile':'high',
            'level':'4.1', 'forced-idr':'0',
            'x264-params':params}
        return ctx
    ctx = context()
    output = ROOT/'work/output/movie/opening.rendered.h264'
    plan = []
    def emit(packet, dest):
        blob = bytes(packet)
        dest.write(blob)
        plan.append(dict(pts=packet.pts, dts=packet.dts, size=len(blob), keyframe=packet.is_keyframe))
    count = 0
    with av.open(str(source), format='mpeg') as inp, output.open('wb') as dest:
        for i, frame in enumerate(inp.decode(video=0)):
            assert i < len(frames)
            if i and i in idr_frames:
                for packet in ctx.encode(None):
                    emit(packet, dest)
                ctx = context(i)
            # Source includes nonuniform B-picture runs; explicit source types
            # avoid changing decode order or reference-picture map offsets.
            t = i * 1001 / 30000
            cue = next((c for c in spec['subtitle_segments'] if c['start'] <= t < c['end']), None)
            if cue:
                picture = frame.to_image()
                draw_subtitle(picture,cue['en'],spec['style'],font)
                frame = av.VideoFrame.from_image(picture).reformat(format='yuv420p')
            frame.pts, frame.time_base = i*1001, Fraction(1, 30000)
            frame.pict_type = av.video.frame.PictureType[frames[i]['pict_type']]
            for packet in ctx.encode(frame):
                emit(packet, dest)
            count = i+1
            if i % 300 == 0:
                print('Encoded frame', i, flush=True)
        for packet in ctx.encode(None):
            emit(packet, dest)
    assert count == len(frames) == len(plan)
    output.with_suffix('.packets.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf8')
    print('Frames', count, 'bytes', output.stat().st_size)


if __name__ == '__main__':
    main()
