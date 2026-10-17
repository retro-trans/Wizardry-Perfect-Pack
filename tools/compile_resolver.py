"""Compile the freestanding PPU text resolver with Zig/Clang. Default dry run.

Run with a 64-bit Python with ziglang installed. No game files are modified.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write',action='store_true');args=parser.parse_args()
    source=ROOT/'tools/text_resolver.c';output=ROOT/'work/output/text_resolver.o'
    command=[sys.executable,'-m','ziglang','cc','-target','powerpc64-freestanding','-mabi=elfv2',
             '-O2','-fno-builtin','-fno-stack-protector','-mno-altivec','-mno-vsx',
             '-c',str(source),'-o',str(output)]
    print(json.dumps(dict(command=command,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest()),indent=2))
    if args.write:
        output.parent.mkdir(parents=True,exist_ok=True)
        subprocess.run(command,check=True)
        from runtime_text import resolver_code
        code,entry=resolver_code(output)
        record=dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    object_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),code_bytes=len(code),local_entry=entry,command=command)
        output.with_suffix('.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
        print('Compiled and inspected the resolver. PPU runtime verification remains separate.')
    else:print('Dry run: no compiler invoked and no files written.')


if __name__=='__main__':main()
