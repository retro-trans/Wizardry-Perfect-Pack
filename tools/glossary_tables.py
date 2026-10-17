"""Export source-backed item/monster/spell names only. Default dry run."""
import argparse
import json
from check_translation import ROOT,read_sources,read_english


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');args=p.parse_args()
 english=read_english();entries=[]
 for key,row in read_sources().items():
  if not row['source'].startswith('databases/') or row['kind']!='name' or key not in english:continue
  en=english[key]
  entries.append(dict(ja=row['ja'],en=en['en'],status=en['status'],source=row['source'],id=key,note=en.get('note','')))
 print('Name entries:',len(entries));print('Samples:',json.dumps(entries[:4],ensure_ascii=False))
 if args.write:
  (ROOT/'work/glossary/database_names.json').write_text(json.dumps(dict(scope='Names/UI terms only; no dialogue or descriptions',entries=entries),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 else:print('Dry run: no writes.')


if __name__=='__main__':main()
