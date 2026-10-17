"""Prepare contextual 80-row translation slices. Defaults to a dry run."""
import argparse
from collections import OrderedDict
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def prepare():
    census = ROOT/'work/output/text_census'
    groups = {}
    for name, prefix, source in [('events','E','events.ja.json'),
                                 ('executable','X','executable_candidates.ja.json'),
                                 ('trophies','T','trophies.ja.json')]:
        occurrences = json.loads((census/source).read_text(encoding='utf-8'))
        bytext = OrderedDict()
        for index, row in enumerate(occurrences):
            text = row['text']
            if text not in bytext:
                uid = '%s%04d' % (prefix,len(bytext))
                bytext[text] = dict(id=uid,ja=text,kind=row['kind'],occurrences=[],contexts=[])
            target = bytext[text]
            target['occurrences'].append({k:v for k,v in row.items() if k!='text'})
            if len(target['contexts']) < 3:
                start,end = max(0,index-3),min(len(occurrences),index+4)
                target['contexts'].append([
                    {k:v for k,v in r.items() if k in ('text','file','record','kind','offset','address')}
                    for r in occurrences[start:end]])
        groups[name] = list(bytext.values())
    return groups


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write',action='store_true')
    args=parser.parse_args()
    groups=prepare()
    for name,rows in groups.items():
        print('%s: %d unique rows, %d slices of at most 80' % (name,len(rows),(len(rows)+79)//80))
        for row in rows[:2]:
            print('  %s: %s (%d occurrences)' % (row['id'],row['kind'],len(row['occurrences'])))
    if not args.write:
        print('Dry run: no writes. --write creates source exports and 80-row slice files.')
        return
    dest=ROOT/'work/translation/ja'
    dest.mkdir(parents=True,exist_ok=True)
    for name,rows in groups.items():
        data=json.dumps(rows,ensure_ascii=False,indent=2)+'\n'
        (dest/(name+'.json')).write_text(data,encoding='utf-8')
        slices=dest/name
        slices.mkdir(exist_ok=True)
        for start in range(0,len(rows),80):
            (slices/('%04d.json' % start)).write_text(json.dumps(rows[start:start+80],ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'work/translation/en').mkdir(parents=True,exist_ok=True)
    print('Wrote contextual sources. Japanese exports are ignored by Git.')


if __name__=='__main__':
    main()
