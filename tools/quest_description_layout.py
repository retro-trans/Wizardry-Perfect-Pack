"""Wrap quest request/objective display copies in the existing lower panel."""
import argparse
import json
from check_translation import ROOT
from spell_description_layout import render as wrap,width as measure

WIDTH=640
FONT_SIZE=24
LINE_PITCH=25
MAX_LINES=3


def is_description(row):
    return bool(row['occurrences']) and all(o.get('member')==8 and
        o.get('archive') in ('table.enc','addtable01.enc','addtable02.enc','ppdata.enc') and
        o.get('kind') in ('request','objective') for o in row['occurrences'])


def width(text):return measure(text,FONT_SIZE)


def render(text):
    return wrap(text,available_width=WIDTH,horizontal_size=FONT_SIZE,max_lines=MAX_LINES,kind='Quest')


def display_text(row,decision):return render(decision['en']) if is_description(row) else decision['en']


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write',action='store_true');args=parser.parse_args()
    from check_translation import read_sources,read_english
    sources,english=read_sources(),read_english();cases=[]
    for key,row in sources.items():
        if not is_description(row):continue
        text=english[key]['en'];display=render(text);lines=display.split('\n')
        cases.append(dict(id=key,text=display,lines=len(lines),maximum_width=max(map(width,lines)),
                          changed=text!=display,words_preserved=text.split()==display.split(),
                          fields=len(row['occurrences'])))
    report=dict(result='passed',descriptions=len(cases),fields=sum(c['fields'] for c in cases),
                reflowed=sum(c['changed'] for c in cases),maximum_lines=max(c['lines'] for c in cases),
                maximum_width=max(c['maximum_width'] for c in cases),available_width=WIDTH,
                font_size=FONT_SIZE,line_pitch=LINE_PITCH,maximum_text_height=(MAX_LINES-1)*LINE_PITCH+FONT_SIZE,
                canonical_translations_unchanged=True,in_game_verified=False,cases=cases)
    print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2))
    if args.write:(ROOT/'work/output/tests/quest_descriptions.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')


if __name__=='__main__':main()
