"""Compile the bounded character-name setter. Default: dry run."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from elftools.elf.elffile import ELFFile

ROOT = Path(__file__).resolve().parents[1]


def name_code(path):
    with Path(path).open('rb') as stream:
        elf = ELFFile(stream)
        if elf.little_endian or elf['e_machine'] != 'EM_PPC64':
            raise ValueError('Expected big-endian PPC64 name setter')
        text = elf.get_section_by_name('.text').data()
        symbols = elf.get_section_by_name('.symtab').get_symbol_by_name('set_character_name')
        if not symbols or len(symbols) != 1:
            raise ValueError('Missing name setter')
        offset = symbols[0]['st_value']
        toc = text[offset:offset+8] == bytes.fromhex('3c4c000038420000')
        allowed = {offset+2, offset+6} if toc else set()
        for section in elf.iter_sections():
            if section.name in ('.rela.text', '.rel.text'):
                if any(r['r_offset'] not in allowed or r['r_info_type'] not in (250, 252)
                       for r in section.iter_relocations()):
                    raise ValueError('Unresolved name setter relocation')
            if section.name.startswith(('.rodata', '.toc', '.data', '.bss')) and section['sh_size']:
                raise ValueError('Name setter requires external runtime data')
        return text, offset+(8 if toc else 0)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--write', action='store_true')
    args = p.parse_args()
    source, output = ROOT/'tools/name_entry.c', ROOT/'work/output/name_entry.o'
    command = [sys.executable, '-m', 'ziglang', 'cc', '-target', 'powerpc64-freestanding',
               '-mabi=elfv2', '-O2', '-fno-builtin', '-fno-stack-protector',
               '-mno-altivec', '-mno-vsx', '-c', str(source), '-o', str(output)]
    print(json.dumps(dict(command=command), indent=2))
    if not args.write:
        print('Dry run: nothing compiled.'); return
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(command, check=True)
    code, entry = name_code(output)
    report = dict(code_bytes=len(code), local_entry=entry,
                  source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  object_sha256=hashlib.sha256(output.read_bytes()).hexdigest())
    output.with_suffix('.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
