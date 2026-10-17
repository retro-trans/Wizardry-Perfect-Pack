"""Preserve original AVC VUI/HRD and per-frame timing SEI after strict parsing.

Input is the local experimental movie with correctly aligned translated AVC
access units. This tool keeps its coded slice bytes and SPS coding prefix,
transplants compatible source VUI, and restores original non-user-data SEI.
Read-only by default; --write creates an elementary-stream candidate only.

Syntax cross-checked against FFmpeg libavcodec/cbs_h264_syntax_template.c.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from movie_pamf import ROOT, SOURCE, EXPECTED, inspect, ffprobe, sha


def unescape(data):
    return re.sub(b'\x00\x00\x03(?=[\x00-\x03])',b'\x00\x00',data)


def escape(data):
    out=bytearray(); zeros=0
    for byte in data:
        if zeros==2 and byte<=3:
            out.append(3); zeros=0
        out.append(byte)
        zeros=zeros+1 if byte==0 else 0
    return bytes(out)


class Bits:
    def __init__(self,data):
        self.bits=''.join(f'{x:08b}' for x in data);self.pos=0
    def u(self,n=1):
        assert self.pos+n<=len(self.bits),'Truncated RBSP'
        value=int(self.bits[self.pos:self.pos+n],2);self.pos+=n;return value
    def ue(self):
        zeros=0
        while self.u()==0:
            zeros+=1;assert zeros<32,'Invalid Exp-Golomb'
        return (1<<zeros)-1+(self.u(zeros) if zeros else 0)
    def se(self):
        value=self.ue();return (value+1)//2 if value&1 else -value//2


def hrd(b):
    count=b.ue()+1;assert count<=32
    rate_scale,size_scale=b.u(4),b.u(4)
    entries=[]
    for _ in range(count):
        rate,size,cbr=b.ue(),b.ue(),b.u()
        entries.append(dict(bit_rate=(rate+1)<<(6+rate_scale),
            cpb_size=(size+1)<<(4+size_scale),cbr=bool(cbr)))
    return dict(entries=entries,initial_cpb_removal_delay_length=b.u(5)+1,
        cpb_removal_delay_length=b.u(5)+1,dpb_output_delay_length=b.u(5)+1,
        time_offset_length=b.u(5))


def vui(b):
    d={}
    if b.u():
        d['aspect_ratio_idc']=b.u(8)
        if d['aspect_ratio_idc']==255:d['sar']=[b.u(16),b.u(16)]
    if b.u():d['overscan_appropriate_flag']=b.u()
    if b.u():
        d['video_format']=b.u(3);d['full_range']=b.u()
        if b.u():d['colors']=[b.u(8),b.u(8),b.u(8)]
    if b.u():d['chroma_sample_loc']=[b.ue(),b.ue()]
    if b.u():
        d['num_units_in_tick']=b.u(32);d['time_scale']=b.u(32)
        d['fixed_frame_rate']=b.u()
    nal,vcl=b.u(),False
    if nal:d['nal_hrd']=hrd(b)
    vcl=b.u()
    if vcl:d['vcl_hrd']=hrd(b)
    if nal or vcl:d['low_delay_hrd']=b.u()
    d['pic_struct_present']=b.u()
    if b.u():
        d['motion_vectors_over_pic_boundaries']=b.u()
        for name in ('max_bytes_per_pic_denom','max_bits_per_mb_denom',
            'log2_max_mv_length_horizontal','log2_max_mv_length_vertical',
            'max_num_reorder_frames','max_dec_frame_buffering'):
            d[name]=b.ue()
    return d


def parse_sps(nal):
    assert nal[0]&31==7
    rbsp=unescape(nal[1:]);b=Bits(rbsp)
    d={'profile':b.u(8),'constraints':b.u(8),'level':b.u(8),'sps_id':b.ue()}
    d.update(chroma_format=1,bit_depth_luma=8,bit_depth_chroma=8)
    if d['profile'] in (100,110,122,244,44,83,86,118,128,138,139,134,135):
        d['chroma_format']=b.ue()
        if d['chroma_format']==3:d['separate_color_plane']=b.u()
        d['bit_depth_luma']=b.ue()+8;d['bit_depth_chroma']=b.ue()+8
        d['qpprime_transform_bypass']=b.u()
        if b.u():
            for i in range(12 if d['chroma_format']==3 else 8):
                if b.u():
                    last=next_scale=8
                    for _ in range(16 if i<6 else 64):
                        if next_scale:next_scale=(last+b.se()+256)%256
                        last=next_scale or last
    d['frame_num_bits']=b.ue()+4;d['poc_type']=b.ue()
    if d['poc_type']==0:d['poc_lsb_bits']=b.ue()+4
    elif d['poc_type']==1:
        d['delta_pic_order_always_zero']=b.u();b.se();b.se()
        for _ in range(b.ue()):b.se()
    d['max_num_ref_frames']=b.ue();d['gaps_allowed']=b.u()
    width,height=b.ue()+1,b.ue()+1
    d['frame_mbs_only']=b.u()
    if not d['frame_mbs_only']:d['mb_adaptive_frame_field']=b.u()
    d['direct_8x8']=b.u();crop=[0,0,0,0]
    if b.u():crop=[b.ue() for _ in range(4)]
    d['crop']=crop
    assert d['chroma_format']==1 and d['frame_mbs_only']==1,'Only progressive 4:2:0 supported'
    d['width']=width*16-2*(crop[0]+crop[1])
    d['height']=height*16-2*(crop[2]+crop[3])
    flag_position=b.pos;assert b.u()==1,'SPS VUI required'
    d['vui']=vui(b);end=b.pos
    assert b.u()==1 and set(b.bits[b.pos:])<=set('0'),'Invalid SPS trailing bits'
    # Byte-for-byte RBSP round trip protects parsing/escaping before edits.
    assert escape(rbsp)==nal[1:],'RBSP escape round trip failed'
    return d,b.bits[:flag_position],b.bits[flag_position:end]


def transplant(encoded,original):
    new,prefix,_=parse_sps(encoded);old,_,vui_bits=parse_sps(original)
    for key in ('profile','level','sps_id','chroma_format','bit_depth_luma',
        'bit_depth_chroma','width','height','frame_mbs_only','crop'):
        assert new[key]==old[key],('Incompatible coding/VUI geometry',key,new[key],old[key])
    a,c=new['vui'],old['vui']
    # The candidate omits SAR; square pixels are already declared by the
    # unchanged PAMF AVC header. Restoring the original explicit 1:1 is safe.
    assert a.get('aspect_ratio_idc',1)==c.get('aspect_ratio_idc',1)
    for key in ('sar','full_range','colors'):
        assert a.get(key)==c.get(key),('Incompatible VUI signal',key,a.get(key),c.get(key))
    # The experimental PyAV encode advertises its 1/30000 codec time base as
    # the picture period (60000/1 timing fields), although submitted picture
    # PTS advances by 1001 ticks. Also accept the earlier rounded-30 draft.
    # Only the VUI advertisement is replaced; packet and decoded-picture
    # timing are independently checked after remuxing.
    assert c['time_scale']*1001==c['num_units_in_tick']*2*30000
    assert (a['time_scale']*1001==a['num_units_in_tick']*2*30000
            or a['time_scale']==a['num_units_in_tick']*60
            or (a['num_units_in_tick'],a['time_scale'])==(1,60000))
    assert 'nal_hrd' in c,'Source NAL HRD required'
    if 'vcl_hrd' in c:
        # The source has both HRDs. Picture-timing SEI uses one set of timing
        # field widths, so require their shared widths before retaining SEI.
        for key in ('cpb_removal_delay_length','dpb_output_delay_length',
                    'time_offset_length'):
            assert c['nal_hrd'][key]==c['vcl_hrd'][key],('Incompatible source HRD timing',key)
    for key in ('max_num_reorder_frames','max_dec_frame_buffering',
        'log2_max_mv_length_horizontal','log2_max_mv_length_vertical'):
        assert key in a and key in c and a[key]<=c[key],('Insufficient source VUI limit',key,a.get(key),c.get(key))
    assert new['max_num_ref_frames']<=c['max_dec_frame_buffering']
    bits=prefix+vui_bits+'1';bits+='0'*((-len(bits))%8)
    body=bytes(int(bits[i:i+8],2) for i in range(0,len(bits),8))
    result=encoded[:1]+escape(body)
    after,after_prefix,_=parse_sps(result)
    assert after_prefix==prefix,'Encoded SPS coding prefix changed'
    assert after['vui']==c,'VUI transplant mismatch'
    return result,dict(source=old,encoded_before=new,encoded_after=after)


def nals(unit):
    starts=list(re.finditer(b'\x00\x00(?:\x00)?\x01',unit))
    assert starts and starts[0].start()==0,'AU must begin with Annex B start code'
    return [(m.group(),unit[m.end():(starts[i+1].start() if i+1<len(starts) else len(unit))].rstrip(b'\0'))
        for i,m in enumerate(starts)]


def sei_payloads(nal):
    data=unescape(nal[1:]);pos=0;messages=[]
    while pos<len(data) and data[pos:]!=b'\x80':
        kind=size=0
        while data[pos]==255:kind+=255;pos+=1
        kind+=data[pos];pos+=1
        while data[pos]==255:size+=255;pos+=1
        size+=data[pos];pos+=1
        assert pos+size<=len(data)
        messages.append((kind,data[pos:pos+size]));pos+=size
    return messages


def retained_sei(nal):
    messages=sei_payloads(nal)
    if all(kind!=5 for kind,_ in messages):return nal
    keep=[(kind,body) for kind,body in messages if kind!=5]
    if not keep:return None
    out=bytearray()
    for kind,body in keep:
        out.extend(b'\xff'*(kind//255)+bytes([kind%255]))
        out.extend(b'\xff'*(len(body)//255)+bytes([len(body)%255]));out.extend(body)
    return nal[:1]+escape(bytes(out)+b'\x80')


def generate(candidate):
    original=SOURCE.read_bytes();assert sha(original)==EXPECTED
    before,_,source_es=inspect(original)
    candidate_report,_,candidate_es=inspect(candidate.read_bytes())
    assert before['all_non_video_bytes_sha256']==candidate_report['all_non_video_bytes_sha256']
    packets=ffprobe(SOURCE);offset=0;active_sps=None;result=[];plan=[]
    original_sei_types=Counter();sps_reports={};overflows=[]
    vcl_before=hashlib.sha256();vcl_after=hashlib.sha256();timing_hash=hashlib.sha256()
    for i,packet in enumerate(packets):
        size=int(packet['size']);source_unit=source_es[offset:offset+size]
        encoded_unit=candidate_es[offset:offset+size];offset+=size
        old_nals=nals(source_unit);new_nals=nals(encoded_unit)
        timing=[]
        for prefix,nal in old_nals:
            if nal[0]&31==7:active_sps=nal
            if nal[0]&31==6:
                original_sei_types.update(kind for kind,_ in sei_payloads(nal))
                kept=retained_sei(nal)
                if kept:timing.append(prefix+kept)
        assert active_sps is not None
        out=[];inserted=False
        for prefix,nal in new_nals:
            kind=nal[0]&31
            if kind in (6,12):continue
            if kind==7:
                nal,parsed=transplant(nal,active_sps)
                sps_reports[sha(nal)]=parsed
            if kind in (1,5):
                if not inserted:
                    out.extend(timing);timing_hash.update(b''.join(timing));inserted=True
                vcl_before.update(nal)
            out.append(prefix+nal)
        assert inserted
        blob=b''.join(out)
        for _,nal in nals(blob):
            if nal[0]&31 in (1,5):vcl_after.update(nal)
        if len(blob)>size:overflows.append(dict(frame=i,capacity=size,encoded=len(blob)))
        result.append(blob)
        plan.append(dict(pts=(int(packet['pts'])-90000)//3,
            dts=(int(packet['dts'])-90000)//3,size=len(blob),keyframe='K' in packet['flags']))
    assert offset==len(source_es)==len(candidate_es)
    assert vcl_before.digest()==vcl_after.digest(),'Coded slice bytes changed'
    report=dict(source_sha256=EXPECTED,candidate_sha256=candidate_report['source_sha256'],
        frames=len(packets),retained_source_sei_types=dict(original_sei_types),
        retained_source_sei_sha256=timing_hash.hexdigest(),
        coded_slice_bytes_unchanged=vcl_before.digest()==vcl_after.digest(),
        coded_slice_sha256=vcl_after.hexdigest(),
        sps_coding_prefix_unchanged=True,sps_vui_compatibility=list(sps_reports.values()),
        overflow_count=len(overflows),overflow_examples=overflows[:20],
        note='Preserves original VUI/HRD and source non-user-data SEI, including recovery points. Packet timing still requires independent decode verification.')
    return b''.join(result),plan,report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',type=Path,default=ROOT/'work/output/movie/opening.en.experimental.pam')
    parser.add_argument('--write',action='store_true')
    args=parser.parse_args()
    elementary,plan,report=generate(args.candidate)
    print(json.dumps(report,indent=2))
    if args.write:
        assert report['overflow_count']==0,'Overflow blocks writing'
        out=ROOT/'work/output/movie/opening.vui.h264'
        out.write_bytes(elementary)
        out.with_suffix('.packets.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf8')
        out.with_suffix('.audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    else:print('Dry run: no files written.')


if __name__=='__main__':main()
