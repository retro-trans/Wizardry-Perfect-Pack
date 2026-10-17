"""Check screenshot-measured menu budgets with the native font advance model.

Read-only unless --write saves a local report. This is a metric check, not an
updated in-game screenshot or execution of the PPU layout code.
"""
import argparse
import json
from fontTools.ttLib import TTFont
from check_translation import ROOT, read_english
from check_vwf import cache_width, pen_positions


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write',action='store_true')
    args=parser.parse_args()
    manifest=json.loads((ROOT/'work/ui/menus.en.json').read_text(encoding='utf8'))
    english=read_english()
    font=TTFont(ROOT/'work/source/NPJB00162/USRDIR/FOT-UtrilloPro-DB.otf')
    metrics=font['hmtx'].metrics;em=font['head'].unitsPerEm
    widths={chr(k):cache_width(metrics[v][0],em) for k,v in font.getBestCmap().items()}
    cases=[]
    for row in manifest['fit_cases']:
        decision=english[row['id']]
        text=(decision.get('display',decision['en']) if row.get('use')=='display' else decision['en'])+row.get('suffix','')
        width=pen_positions(text,row['font_size'],widths)[1]
        cases.append(dict(row,text=text,measured_width=width,fits=width<=row['available_width']))
    report=dict(result='passed' if all(r['fits'] for r in cases) else 'failed',cases=cases,
                actual_updated_game_capture=False)
    print(json.dumps(dict(result=report['result'],cases=len(cases),failures=[r for r in cases if not r['fits']],actual_updated_game_capture=False),indent=2))
    if args.write:
        destination=ROOT/'work/output/tests/menu_layout.json'
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    if report['result']!='passed':raise SystemExit(1)


if __name__=='__main__':main()
