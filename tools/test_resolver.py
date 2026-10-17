"""Build and run host-native resolver edge cases only with --write.

Host tests validate the same C parser used by PPU wrappers; they do not execute
PowerPC instructions. The compiled DLL stays in ignored local output storage.
"""
import argparse
import ctypes
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');args=p.parse_args()
 output=ROOT/'work/output/tests/resolver.dll'
 command=[sys.executable,'-m','ziglang','cc','-shared','-O2',str(ROOT/'tools/text_resolver.c'),'-o',str(output)]
 print(json.dumps(dict(command=command),indent=2))
 if not args.write:print('Dry run: no compiler invoked.');return
 output.parent.mkdir(parents=True,exist_ok=True);subprocess.run(command,check=True)
 library=ctypes.CDLL(str(output));resolve=library.resolve_text
 resolve.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint,ctypes.POINTER(ctypes.c_void_p),ctypes.c_uint,ctypes.POINTER(ctypes.c_void_p),ctypes.c_uint]
 resolve.restype=ctypes.c_void_p
 strings=[ctypes.create_string_buffer(s) for s in [b'A full English item name',b'Another name',b'x'*2048]]
 table=(ctypes.c_void_p*len(strings))(*(ctypes.addressof(s) for s in strings))
 # Byte values, not source pointer identity: native code copies these to stack.
 alias_strings=[ctypes.create_string_buffer(s) for s in [bytes.fromhex('e4b8bb3a'),b'M:',bytes.fromhex('e799bbe98cb2'),b'Register']]
 aliases=(ctypes.c_void_p*6)(ctypes.addressof(alias_strings[0]),ctypes.addressof(alias_strings[1]),1,
                           ctypes.addressof(alias_strings[2]),ctypes.addressof(alias_strings[3]),0)
 cases=[(b'plain',4096,b'plain'),(b'~T00000000~',4096,strings[0].value),
        (b'Actor uses ~T00000000~!',4096,b'Actor uses '+strings[0].value+b'!'),
        (b'~T00000000~ / ~T00000001~',4096,strings[0].value+b' / '+strings[1].value),
        (b'~TFFFFFFFF~',4096,b'~TFFFFFFFF~'),(b'~T0000000',4096,b'~T0000000'),
        (b'~T0000000G~',4096,b'~T0000000G~'),(b'~',4096,b'~'),
        (b'~T00000002~',16,b'~T00000002~'),(b'~T00000000~',0,b'~T00000000~'),
        (b'~T00000000~',len(strings[0].value)+1,strings[0].value),
        (alias_strings[0].value+b'~T00000001~',4096,b'M:Another name'),
        (alias_strings[2].value,4096,b'Register'),
        (alias_strings[2].value+b'x',4096,alias_strings[2].value+b'x'),
        (b'x'+alias_strings[2].value,4096,b'x'+alias_strings[2].value),
        (alias_strings[2].value,7,alias_strings[2].value),
        (alias_strings[0].value[:2],4096,alias_strings[0].value[:2])]
 for source,capacity,expected in cases:
  original=ctypes.create_string_buffer(source);buffer=ctypes.create_string_buffer(max(1,capacity))
  result=resolve(ctypes.addressof(original),ctypes.addressof(buffer),capacity,table,len(strings),aliases,2)
  if ctypes.string_at(result)!=expected:raise AssertionError('Resolver edge case failed')
 from build import DEFERRED_UI_IDS
 from check_translation import read_sources,read_english
 sources,english=read_sources(),read_english()
 alias_keys=sorted(DEFERRED_UI_IDS)+sorted(k for k,r in sources.items() if r['source']=='ui_literals')
 labels=[];values=[]
 for key in alias_keys:
  original=ctypes.create_string_buffer(sources[key]['ja'].encode('utf8'))
  translated=ctypes.create_string_buffer(english[key]['en'].encode('utf8'))
  labels.extend([original,translated]);values.extend([ctypes.addressof(original),ctypes.addressof(translated),int(key in {'X1337','X1338'})])
 native_aliases=(ctypes.c_void_p*len(values))(*values)
 for i,key in enumerate(alias_keys):
  # Reproduce a compiler-sized copy, including the original terminator, into
  # an independently allocated stack-like buffer. Pointer lookup would fail.
  copied=ctypes.create_string_buffer(len(labels[2*i].raw));ctypes.memmove(copied,labels[2*i],len(labels[2*i].raw))
  output_buffer=ctypes.create_string_buffer(4096)
  result=resolve(ctypes.addressof(copied),ctypes.addressof(output_buffer),4096,table,len(strings),native_aliases,len(alias_keys))
  if ctypes.string_at(result)!=english[key]['en'].encode('utf8'):raise AssertionError('Native fixed-copy alias failed: '+key)
 # The party Equipment header reuses the preceding item-name buffer. Its
 # original seven-byte copy must terminate before the old token's 030~ tail.
 equipment_index=alias_keys.index('X0055')
 reused=ctypes.create_string_buffer(b'~T00000030~',64)
 original=labels[equipment_index*2]
 ctypes.memmove(reused,original,len(original.raw))
 output_buffer=ctypes.create_string_buffer(4096)
 result=resolve(ctypes.addressof(reused),ctypes.addressof(output_buffer),4096,table,len(strings),native_aliases,len(alias_keys))
 if ctypes.string_at(result)!=english['X0055']['en'].encode('utf8'):raise AssertionError('Equipment retained previous token suffix')
 print(json.dumps(dict(result='passed',native_cases=len(cases),fixed_copy_labels=len(DEFERRED_UI_IDS),immediate_labels=len(alias_keys)-len(DEFERRED_UI_IDS),equipment_reused_buffer=True,powerpc_execution=False),indent=2))


if __name__=='__main__':main()
