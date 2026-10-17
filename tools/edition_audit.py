"""Read-only comparison with NPJB00099; does not authorize binary reuse."""
from pathlib import Path
import json
import struct
from text_census import executable

ROOT=Path(__file__).resolve().parents[1]


def main():
    newpath=ROOT/'work/source/NPJB00162/USRDIR/EBOOT.elf'
    oldpath=ROOT.parent/'Wizardry Prisoners of the Lost City/work/source/NPJB00099/USRDIR/EBOOT.elf'
    a,b=newpath.read_bytes(),oldpath.read_bytes()
    old,_=executable(oldpath)
    new,_=executable(newpath)
    by={r['text']:r['address'] for r in new}
    mapping={r['address']:by[r['text']] for r in old if r['text'] in by}
    ranges=[]
    for lo,hi in [(0x50ea0c,0x50eac4),(0x529d90,0x529db4),(0x52aa20,0x52aa58),(0x52b1f8,0x52b1fc)]:
        block=b[lo:hi]
        values=struct.unpack('>'+'I'*(len(block)//4),block)
        translated=b''.join(struct.pack('>I',mapping.get(v,v)) for v in values)
        pos=a.find(translated)
        hits=[]
        for at in range(0,len(a)-3,4):
            if a[at:at+len(translated)]==translated:
                hits.append(hex(at))
        ranges.append(dict(old_file_span=[hex(lo),hex(hi)],new_file_offsets=hits,
                           words=len(values),source_string_pointers=sum(v in mapping for v in values)))
    print(json.dumps(dict(mixed_pointer_arrays=ranges),indent=2))
    for lo,hi in [(0x529d90,0x529db4)]:
        rows=[]
        for at in range(lo,hi,4):
            ov=struct.unpack_from('>I',b,at)[0]
            nv=struct.unpack_from('>I',a,at+0x100)[0]
            rows.append(dict(old_offset=hex(at),old_value=hex(ov),new_value=hex(nv),
                             japanese_pointer_matches=mapping.get(ov)==nv,
                             old_target=b[ov-0x10000:ov-0x10000+48].split(b'\0')[0].decode('utf8','replace') if 0x3d0000<ov<0x420000 else None,
                             new_target=a[nv-0x10000:nv-0x10000+48].split(b'\0')[0].decode('utf8','replace') if 0x3d0000<nv<0x420000 else None))
        print(json.dumps(rows,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
