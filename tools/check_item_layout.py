"""Check item-screen widths with the native font model; default read-only."""
import argparse
import json
from fontTools.ttLib import TTFont
from check_translation import ROOT,read_english
from check_vwf import cache_width,pen_positions


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write',action='store_true');args=parser.parse_args()
    manifest=json.loads((ROOT/'work/ui/items.en.json').read_text(encoding='utf8'))
    english=read_english();font=TTFont(ROOT/'work/source/NPJB00162/USRDIR/FOT-UtrilloPro-DB.otf')
    widths={chr(c):cache_width(font['hmtx'][g][0],font['head'].unitsPerEm) for c,g in font.getBestCmap().items()}
    cases=[]
    for row in manifest['cell_fit_cases']+manifest['static_fit_cases']:
        text=english[row['id']]['en'] if 'id' in row else row['text']
        if 'maximum_horizontal_size' in row:
            size=row['maximum_horizontal_size'];limit=row['maximum_width']
            measured=pen_positions(text,size,widths)[1]
            if measured>limit:
                size=max(1,size*limit//int(measured))
                while size>1 and pen_positions(text,size,widths)[1]>limit:size-=1
        else:size=row['font_size'];limit=row['available_width']
        measured=pen_positions(text,size,widths)[1]
        cases.append(dict(row,text=text,horizontal_size=size,measured_width=measured,fits=measured<=limit))
    panel=manifest['preview_stat_panel'];left=panel[0];right=left+panel[2]
    for row in manifest['preview_stat_rows']:
        text=english[row['id']]['en'];size=row['font_size'];measured=pen_positions(text,size,widths)[1]
        start=manifest['preview_stat_anchor_x']-measured
        cases.append(dict(row,text=text,horizontal_size=size,measured_width=measured,x=start,
                          fits=left<=start and manifest['preview_stat_anchor_x']<right))
    for text in ('None','999','-99'):
        measured=pen_positions(text,24,widths)[1];end=manifest['preview_value_visible_x']+measured
        cases.append(dict(text=text,horizontal_size=24,measured_width=measured,right=end,fits=end<right))
    weapon=manifest['weapon_preview']
    for row in manifest['compact_stat_labels']:
        text=english[row['id']]['en'];size=row['font_size'];measured=pen_positions(text,size,widths)[1]
        start=weapon['left_anchor_x']-measured if row['id'] in weapon['left_label_ids'] else weapon['right_column_x']
        cases.append(dict(row,text=text,horizontal_size=size,measured_width=measured,x=start,
                          fits=measured<=row['maximum_width'] and left<=start and start+measured<right))
    count_start=weapon['origin_x']+weapon['attack_count_x_prefix']+pen_positions(weapon['attack_count_measure_text'],24,widths)[1]
    for damage in (weapon['reference_damage'],'999\uff5e999'):
        end=weapon['left_anchor_x']+pen_positions(damage,24,widths)[1]
        cases.append(dict(text=damage,horizontal_size=24,right=end,gap_before_count=count_start-end,fits=end+8<=count_start))
    for label,value,start,limit,padding in (
        ('','x255',count_start,right,4),('','None',weapon['left_anchor_x'],right,8),
        ('','-99',weapon['left_anchor_x'],weapon['right_column_x'],8),
        (english['X1418']['en'],'M',weapon['right_column_x'],right,8),
        (english['X1420']['en'],'999',weapon['right_column_x'],right,8)):
        text=label+value;end=start+pen_positions(text,24,widths)[1]
        cases.append(dict(text=text,horizontal_size=24,x=start,right=end,fits=left<=start and end+padding<=limit))
    report=dict(result='passed' if all(r['fits'] for r in cases) else 'failed',cases=cases,
                minimum_grid_horizontal_size=min(r['horizontal_size'] for r in cases if 'maximum_horizontal_size' in r),
                updated_game_capture=False)
    print(json.dumps(dict(result=report['result'],cases=len(cases),minimum_grid_horizontal_size=report['minimum_grid_horizontal_size'],failures=[r for r in cases if not r['fits']]),indent=2))
    if args.write:
        (ROOT/'work/output/tests/item_layout.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    if report['result']!='passed':raise SystemExit(1)


if __name__=='__main__':main()
