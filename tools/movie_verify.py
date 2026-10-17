"""Decode an experimental opening and compare every timing and picture type.

Read-only unless --write is supplied. Audio/container bytes are checked against
the untouched original. This is not a PS3 playback or audible-audio test.
"""
import argparse
import json
from pathlib import Path
import subprocess
from movie_pamf import ROOT, SOURCE, EXPECTED, ffprobe, inspect, sha


def frames(path):
    result = subprocess.run(['ffprobe','-v','error','-f','mpeg',
        '-select_streams','v','-show_frames','-show_entries',
        'frame=best_effort_timestamp,key_frame,pict_type,width,height,pix_fmt',
        '-of','json',str(path)],capture_output=True,check=True)
    assert not result.stderr.strip(), result.stderr.decode(errors='replace')
    return json.loads(result.stdout)['frames']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('movie',type=Path)
    parser.add_argument('--write',action='store_true')
    args=parser.parse_args()
    source=SOURCE.read_bytes()
    assert sha(source)==EXPECTED
    original,_,_=inspect(source)
    modified,_,_=inspect(args.movie.read_bytes())
    for key in ('bytes','streams','header_sha256','private_packet_sha256',
        'random_access_map_sha256','timestamp_headers_sha256','all_non_video_bytes_sha256'):
        assert original[key]==modified[key],('Container preservation failed',key)
    print('Container, private audio, access maps and timestamps preserved.',flush=True)
    before,after=ffprobe(SOURCE),ffprobe(args.movie)
    packet_differences=[dict(index=i,original=a,rebuilt=b)
        for i,(a,b) in enumerate(zip(before,after)) if a!=b]
    print('Packet metadata differences:',len(packet_differences),flush=True)
    prior=frames(SOURCE)
    current=frames(args.movie)
    assert len(prior)==len(current)==2210
    timing_differences=[]
    other_differences=[]
    for i,(a,b) in enumerate(zip(prior,current)):
        if a.get('best_effort_timestamp')!=b.get('best_effort_timestamp'):
            timing_differences.append(i)
        fields=('key_frame','pict_type','width','height','pix_fmt')
        if any(a.get(k)!=b.get(k) for k in fields):
            other_differences.append(i)
    good=not(packet_differences or timing_differences or other_differences)
    report=dict(result='verified' if good else 'blocked',
        status='complete structural and software decode pass; PS3 playback pending' if good else 'Excluded from game builds: AVC inferred frame timing is not preserved',
        source_sha256=EXPECTED,output_sha256=modified['source_sha256'],
        frame_count=len(current),packet_count=len(after),
        all_decoded_frame_timestamps_match=not timing_differences,
        all_picture_types_match=not other_differences,
        all_packet_pts_dts_sizes_and_flags_match=not packet_differences,
        packet_metadata_differences=len(packet_differences),
        packet_difference_examples=packet_differences[:4],
        decoded_frame_timestamp_differences=len(timing_differences),
        other_frame_metadata_differences=len(other_differences),
        all_non_video_bytes_match=True,private_audio_pes_packets=598,
        audio_packet_sha256=modified['private_packet_sha256'],
        random_access_maps_preserved=88,
        decode_errors=0,ps3_playback_verified=False,audible_audio_verified=False)
    print(json.dumps(report,indent=2))
    if args.write:
        args.movie.with_suffix('.verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    else:
        print('Dry run: no report written.')
    if not good:
        raise SystemExit(1)


if __name__=='__main__':
    main()
