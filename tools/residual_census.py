"""Bounded UTF-8 audit of decoded non-table members; dry run by default.

These are candidates, not additional player-facing text. Japanese review
strings are saved only under ignored work/output when --write is requested.
"""
import argparse
import json
import re
from pathlib import Path
from text_census import ROOT,JAPANESE


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');args=p.parse_args()
 rows=[];files=0
 for path in sorted((ROOT/'work/source/decoded').rglob('*.dat')):
  if any(x in ('table.enc','addtable01.enc','addtable02.enc') for x in path.parts):continue
  files+=1;data=path.read_bytes()
  texts=[]
  for match in re.finditer(rb'[^\x00]+',data):
   if len(match[0])>8192 or match.end()==len(data):continue
   try:text=match[0].decode('utf8')
   except UnicodeDecodeError:continue
   if any(ord(c)<32 and c not in '\r\n\t' for c in text):continue
   if JAPANESE.search(text):texts.append(dict(offset=match.start(),text=text))
  if texts:rows.append(dict(file=path.relative_to(ROOT/'work/source/decoded').as_posix(),candidates=len(texts),strings=texts))
 print(json.dumps(dict(members_inspected=files,candidate_members=len(rows),model_members=sum('/obj/' in r['file'] for r in rows),nonmodel=[dict(file=r['file'],candidates=r['candidates']) for r in rows if '/obj/' not in r['file']]),indent=2))
 if args.write:(ROOT/'work/output/text_census/residual.ja.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 else:print('Dry run: no writes. Individual non-NUL runs over 8192 bytes excluded.')


if __name__=='__main__':main()
