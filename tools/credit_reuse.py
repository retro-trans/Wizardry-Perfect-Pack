"""Compose edition credit lines from previously researched exact name fragments.

Default dry run; unknown names stay pending and are never guessed silently.
"""
import argparse
import json
import re
import unicodedata
from pathlib import Path
from check_translation import ROOT,read_sources,read_english,JAPANESE_PROSE


def normalized(text):return re.sub(r'\s+',' ',unicodedata.normalize('NFKC',text)).strip()


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');args=p.parse_args()
 ref=ROOT.parent/'Wizardry Prisoners of the Lost City'
 old=json.loads((ref/'work/translation/ja/databases/credits.json').read_text(encoding='utf8'))
 en={r['id']:r for f in (ref/'work/translation/en/databases/credits').glob('*.en.json') for r in json.loads(f.read_text(encoding='utf8'))['translations']}
 fragments={normalized(r['ja']):en[r['id']] for r in old}
 pattern=re.compile('|'.join(re.escape(k) for k in sorted(fragments,key=len,reverse=True)))
 known=read_english();decisions={};pending=[]
 for key,row in read_sources().items():
  if row['source']!='databases/credits' or key in known:continue
  text=normalized(row['ja']);parts=[];at=0
  for match in pattern.finditer(text):
   parts.extend([text[at:match.start()],fragments[match[0]]['en']]);at=match.end()
  parts.append(text[at:]);target=''.join(parts)
  if JAPANESE_PROSE.search(target):pending.append(dict(id=key,remaining=target));continue
  decisions[key]=dict(en=target,status='review',note='Composed from matching researched credit names; inherited reading uncertainties remain. Edition-specific grouping preserved.')
 print('Composed:',len(decisions),'Pending:',len(pending))
 print('Samples:',json.dumps(list(decisions.items())[:4],ensure_ascii=False))
 print('Pending:',json.dumps(pending,ensure_ascii=False))
 if args.write:
  (ROOT/'work/output/credits_reuse.en.json').write_text(json.dumps(dict(context='Edition credit grouping; previously researched exact staff-name fragments reused. Primary reading uncertainty retained.',translations=decisions),ensure_ascii=False,indent=2),encoding='utf8')
 else:print('Dry run: no writes.')


if __name__=='__main__':main()
