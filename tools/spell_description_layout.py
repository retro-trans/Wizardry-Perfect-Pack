"""Reflow spell-description display copies; canonical translations stay intact.

Default dry run. --write saves an English-only layout report under work/output.
"""
import argparse
from functools import lru_cache
import json
import re
from fontTools.ttLib import TTFont
from check_translation import ROOT
from check_vwf import cache_width,pen_positions

WIDTH=352
HORIZONTAL_SIZE=24
VERTICAL_SIZE=22
LINE_PITCH=23
MAX_LINES=6
CONTROL=re.compile(r'@(?:[0-9]+r|RS)')


@lru_cache(maxsize=1)
def advances():
    with TTFont(ROOT/'work/source/NPJB00162/USRDIR/FOT-UtrilloPro-DB.otf') as font:
        return {chr(c):cache_width(font['hmtx'][g][0],font['head'].unitsPerEm) for c,g in font.getBestCmap().items()}


def width(text,size=HORIZONTAL_SIZE):return pen_positions(CONTROL.sub('',text),size,advances())[1]


def is_description(row):
    return bool(row['occurrences']) and all(o.get('archive')=='table.enc' and o.get('member')==4 and o.get('kind')=='description' for o in row['occurrences'])


def render(text,*,available_width=WIDTH,horizontal_size=HORIZONTAL_SIZE,max_lines=MAX_LINES,kind='Spell'):
    lines=[]
    for paragraph in re.split(r'\n\s*\n',text):
        if lines:lines.append('')
        current=''
        for word in paragraph.split():
            if width(word,horizontal_size)>available_width:raise ValueError(kind+'-description word exceeds panel width')
            candidate=(current+' '+word).strip()
            if current and width(candidate,horizontal_size)>available_width:lines.append(current);current=word
            else:current=candidate
        if current:lines.append(current)
    result='\n'.join(lines)
    if result.split()!=text.split():raise ValueError(kind+'-description words changed')
    if len(lines)>max_lines:raise ValueError(kind+' description exceeds visible lines')
    return result


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
                maximum_text_height=MAX_LINES*VERTICAL_SIZE+(MAX_LINES-1),cases=cases,in_game_verified=False)
    print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2))
    if args.write:(ROOT/'work/output/tests/spell_descriptions.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')


if __name__=='__main__':main()
