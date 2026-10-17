"""Read-only measured bounds checks for spell, quest and settings panels."""
import argparse
import json
from check_translation import ROOT,read_english
from check_vwf import pen_positions
from spell_description_layout import advances


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');args=p.parse_args()
    manifest=json.loads((ROOT/'work/ui/panels.en.json').read_text(encoding='utf8'));english=read_english();metrics=advances();cases=[]
    def width(text,size):return pen_positions(text,size,metrics)[1]
    panel=manifest['spell_summary']
    for key in panel['school_ids']:
        measured=width(english[key]['en'],panel['horizontal_size'])
        cases.append(dict(id=key,text=english[key]['en'],measured_width=measured,fits=measured<=panel['available_label_width']))
    panel=manifest['quest_header'];measured=width(english[panel['source_id']]['en'],panel['font_size'])
    cases.append(dict(id=panel['source_id'],measured_width=measured,right=panel['text_x']+measured,fits=panel['text_x']+measured<=panel['bounds'][0]+panel['bounds'][2]-12))
    panel=manifest['quest_status']
    for key in panel['source_ids']:
        measured=width(english[key]['en'],panel['font_size']);left=panel['center_x']-measured/2;right=panel['center_x']+measured/2
        cases.append(dict(id=key,text=english[key]['en'],left=left,right=right,fits=panel['left']<=left and right<=panel['right']))
    panel=manifest['settings'];options=panel['options']
    for i,option in enumerate(options):
        end=option['x']+width(english[option['id']]['en'],panel['font_size'])
        limit=options[i+1]['x']-panel['minimum_gap'] if i+1<len(options) else panel['bounds'][0]+panel['bounds'][2]-12
        cases.append(dict(id=option['id'],right=end,limit=limit,fits=end<=limit))
    report=dict(result='passed' if all(c['fits'] for c in cases) else 'failed',cases=cases,updated_game_capture=False)
    print(json.dumps(report,indent=2))
    if args.write:(ROOT/'work/output/tests/panel_layout.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    if report['result']!='passed':raise SystemExit(1)


if __name__=='__main__':main()
