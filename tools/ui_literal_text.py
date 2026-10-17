"""Recover three equipment-slot labels emitted as immediate UTF-8 bytes.

Default dry run. --write exports source rows under ignored local storage.
"""
import argparse
import json
import struct
from check_translation import ROOT

# Byte 0, byte 1, byte 2: each address names a guarded `li` instruction.
LITERALS=[('U0000','Hands',[(0x60d74,0x3800ffe6),(0x60d6c,0x3920ff89),(0x60d80,0x3800ff8b)]),
          ('U0001','Feet',[(0x60ce0,0x3800ffe8),(0x60cd8,0x3920ffb6),(0x60cec,0x3800ffb3)]),
          ('U0002','Head',[(0x60eb8,0x3800ffe9),(0x60eb0,0x3920ffa0),(0x60ec4,0x3800ffad)])]


def collect(data=None):
    if data is None:data=(ROOT/'work/source/NPJB00162/USRDIR/EBOOT.elf').read_bytes()
    rows=[]
    for key,meaning,instructions in LITERALS:
        encoded=bytearray()
        for address,expected in instructions:
            actual=struct.unpack_from('>I',data,address-0x10000)[0]
            if actual!=expected:raise ValueError('Equipment-slot immediate changed at '+hex(address))
            encoded.append(actual&255)
        rows.append(dict(id=key,ja=encoded.decode('utf8'),kind='equipment_slot_literal',
                         occurrences=[dict(file='EBOOT.elf',kind='immediate_utf8',
                                           instructions=[dict(address=a,expected=w) for a,w in instructions])],
                         contexts=[dict(note='Item detail equipment-slot value: '+meaning)]))
    return rows


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');args=p.parse_args()
    rows=collect();print(json.dumps(dict(rows=len(rows),instructions=sum(len(r['occurrences'][0]['instructions']) for r in rows)),indent=2))
    if args.write:
        (ROOT/'work/translation/ja/ui_literals.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    else:print('Dry run: no files written.')


if __name__=='__main__':main()
