"""Compile and inspect the freestanding dialogue presenter. Default dry run."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from elftools.elf.elffile import ELFFile
ROOT=Path(__file__).resolve().parents[1]


def message_code(path):
    with Path(path).open('rb') as stream:
        elf=ELFFile(stream)
        if elf.little_endian or elf['e_machine']!='EM_PPC64':raise ValueError('Expected big-endian PPC64')
        text=elf.get_section_by_name('.text').data()
        entries={};allowed_relocations=set()
        for name in ('present_dialogue','present_battle','present_narration'):
            symbols=elf.get_section_by_name('.symtab').get_symbol_by_name(name)
            if not symbols or len(symbols)!=1:raise ValueError('Missing message presenter: '+name)
            offset=symbols[0]['st_value']
            if offset%4 or not 0<=offset<len(text):raise ValueError('Invalid message presenter entry')
            toc=text[offset:offset+8]==bytes.fromhex('3c4c000038420000')
            entries[name]=offset+(8 if toc else 0)
            if toc:allowed_relocations.update((offset+2,offset+6))
        for section in elf.iter_sections():
            if section.name in ('.rela.text','.rel.text'):
                if any(r['r_offset'] not in allowed_relocations or r['r_info_type'] not in (250,252) for r in section.iter_relocations()):raise ValueError('Unresolved dialogue relocation')
            if section.name.startswith(('.rodata','.toc','.data','.bss')) and section['sh_size']:
                raise ValueError('Presenter requires runtime data: '+section.name)
        return text,entries['present_dialogue'],entries['present_battle'],entries['present_narration']


def dialogue_code(path):
    return message_code(path)[:2]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');args=p.parse_args()
    source=ROOT/'tools/dialogue_layout.c';output=ROOT/'work/output/dialogue_layout.o'
    command=[sys.executable,'-m','ziglang','cc','-target','powerpc64-freestanding','-mabi=elfv2',
             '-O2','-fno-builtin','-fno-stack-protector','-mno-altivec','-mno-vsx',
             '-c',str(source),'-o',str(output)]
    print(json.dumps(dict(command=command),indent=2))
    if not args.write:print('Dry run: no compiler invoked.');return
    subprocess.run(command,check=True)
    code,entry,battle,narration=message_code(output)
    report=dict(code_bytes=len(code),local_entry=entry,battle_local_entry=battle,narration_local_entry=narration,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                object_sha256=hashlib.sha256(output.read_bytes()).hexdigest())
    output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
