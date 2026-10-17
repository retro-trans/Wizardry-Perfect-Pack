"""Inspect the one protected event using its own executable's embedded key.

No system/user licenses are read, no key is printed or saved. Supports only
the supplied license-type-3 EDAT, with independent NPD and block hash checks.
RPCS3 format reference: rpcs3/Crypto/unedat.cpp and key_vault.h.
Default dry run decrypts/validates in memory; --write saves an ignored copy.
"""
import argparse
import hashlib
import hmac
import io
import json
from pathlib import Path
import struct
from cryptography.hazmat.primitives.ciphers import Cipher,algorithms,modes
from cryptography.hazmat.primitives.cmac import CMAC
from elftools.elf.elffile import ELFFile

ROOT=Path(__file__).resolve().parents[1]
OMAC2=bytes.fromhex('6ba52976efda16ef3c339fb2971e256b')
OMAC3=bytes.fromhex('9b515feacf75064981aa604d91a54e97')
EDAT_KEY=bytes.fromhex('be959ca8308defa2e5e180c63712a9ae')


def cmac(key,data):
    c=CMAC(algorithms.AES(key));c.update(data);return c.finalize()


def aes(key,data,iv=None,encrypt=False):
    cipher=Cipher(algorithms.AES(key),modes.ECB() if iv is None else modes.CBC(iv))
    c=cipher.encryptor() if encrypt else cipher.decryptor()
    return c.update(data)+c.finalize()


def recover(executable,data):
    elf=ELFFile(io.BytesIO(executable))
    seen=set()
    for section in elf.iter_sections():
        if section['sh_type']!='SHT_PROGBITS' or section['sh_flags']&4: continue
        lo,hi=section['sh_offset'],section['sh_offset']+section['sh_size']
        for offset in range(lo,hi-15,4):
            key=executable[offset:offset+16]
            if key in seen:continue
            seen.add(key)
            if cmac(bytes(a^b for a,b in zip(key,OMAC2)),data[:0x60])==data[0x60:0x70]:
                return key,offset
    raise ValueError('No matching embedded key found in non-code ELF data')


def decode(data,key,name):
    version,license=struct.unpack_from('>II',data,4)
    flags,block,size=struct.unpack_from('>IIQ',data,0x80)
    if data[:4]!=b'NPD\0' or version!=3 or license!=3 or flags!=0x3c:
        raise ValueError('Unsupported EDAT variant')
    if cmac(OMAC3,data[0x10:0x40]+name.encode('ascii'))!=data[0x50:0x60]:
        raise ValueError('EDAT title hash mismatch')
    output=bytearray()
    for index in range((size+block-1)//block):
        offset=0x100+index*(block+32)
        metadata=data[offset:offset+32]
        length=min(block,size-index*block)
        payload=data[offset+32:offset+32+(length+15)//16*16]
        blockkey=data[0x60:0x6c]+struct.pack('>I',index)
        result=aes(key,blockkey,encrypt=True)
        hashkey=aes(key,result,encrypt=True)
        # EDAT flag 0x08 wraps both derived keys in the version-0 key.
        result=aes(EDAT_KEY,result,bytes(16))
        hashkey=aes(EDAT_KEY,hashkey,bytes(16))+bytes(4)
        expected=bytes(a^b for a,b in zip(metadata[:16],metadata[16:]))+metadata[16:20]
        if not hmac.compare_digest(hmac.new(hashkey,payload,hashlib.sha1).digest(),expected):
            raise ValueError('EDAT block authentication failed')
        output.extend(aes(result,payload,data[0x40:0x50])[:length])
    return bytes(output)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');args=p.parse_args()
    root=ROOT/'work/source/NPJB00162/USRDIR'
    path=root/'data/event/station/S0103.edat'
    data=path.read_bytes();key,offset=recover((root/'EBOOT.elf').read_bytes(),data)
    plain=decode(data,key,path.name)
    from build import parse_events,pack_events
    records=parse_events(plain)
    if pack_events(records)!=plain:raise ValueError('Event round trip failed')
    print(json.dumps(dict(event=path.name,embedded_key_file_offset=hex(offset),bytes=len(plain),records=len(records),sha256=hashlib.sha256(plain).hexdigest(),authenticated=True),indent=2))
    if args.write:
        output=path.with_suffix('.edat.unedat')
        if output.exists():raise ValueError('Output exists')
        output.write_bytes(plain)
    else:print('Dry run: decrypted in memory; nothing written.')


if __name__=='__main__':main()
