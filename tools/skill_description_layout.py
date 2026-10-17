"""Reflow skill-description display copies without changing canonical rows.

Default read-only; --write saves an English-only report.
"""
import argparse
import json
from check_translation import ROOT
from spell_description_layout import render as wrap, width as measure

WIDTH=264
HORIZONTAL_SIZE=22
VERTICAL_SIZE=22
LINE_PITCH=23
MAX_LINES=8


def is_description(row):
    return bool(row['occurrences']) and all(o.get('archive')=='table.enc' and o.get('member')==9 and o.get('kind')=='description' for o in row['occurrences'])


def width(text):return measure(text,HORIZONTAL_SIZE)


def render(text):
    return wrap(text,available_width=WIDTH,horizontal_size=HORIZONTAL_SIZE,max_lines=MAX_LINES,kind='Skill')


def display_text(row,decision):return render(decision['en']) if is_description(row) else decision['en']


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');args=p.parse_args()
    from check_translation import read_sources,read_english
    sources,english=read_sources(),read_english();cases=[]
    for key,row in sources.items():
        if not is_description(row):continue
        before=english[key]['en'];after=render(before);lines=after.split('\n')
        cases.append(dict(id=key,text=after,lines=len(lines),maximum_width=max(map(width,lines)),changed=before!=after,words_preserved=True))
    report=dict(descriptions=len(cases),reflowed=sum(r['changed'] for r in cases),maximum_lines=max(r['lines'] for r in cases),
                horizontal_size=HORIZONTAL_SIZE,vertical_size=VERTICAL_SIZE,line_pitch=LINE_PITCH,
                cases=cases,in_game_verified=False)
    print(json.dumps(report,indent=2))
    if args.write:(ROOT/'work/output/tests/skill_descriptions.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')


if __name__=='__main__':main()
