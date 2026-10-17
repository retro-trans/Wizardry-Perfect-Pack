"""Adapt measured logo regions to Perfect Pack PNGs. Default dry run."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');args=p.parse_args()
 source=ROOT/'work/source/NPJB00162'
 ref=ROOT.parent/'Wizardry Prisoners of the Lost City/work/translation/en/graphics/package.en.json'
 doc=json.loads(ref.read_text(encoding='utf8'));assets=[]
 for row in doc['assets']:
  path=source/row['package_path']
  if not path.is_file():continue
  row['source_file']='work/source/NPJB00162/'+row['package_path']
  row['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
  row['regions']=[r for r in row['regions'] if r['id']!='trial']
  row.pop('demo_rect',None)
  if row['package_path']=='ICON0.PNG':
   row.update(edit_rect=[0,20,320,150],wordmark_rect=[7,28,307,53],fog_rect=[0,70,320,57],english_rect=[8,88,304,32],font_size=22,footer_rect=[20,128,280,24],footer='Perfect Pack')
   row['regions'].append(dict(id='edition',rect=[20,128,280,24],en='Perfect Pack',status='translated'))
  row['render_note']='Edition-specific source pixels inspected; preserves outside edit rectangle. No trial-version label in this edition.'
  assets.append(row)
 doc.update(source='NPJB00162 Perfect Pack standalone PNGs',assets=assets,assets_examined=len(assets),text_regions=sum(len(a['regions']) for a in assets),decisions=['No demo label is present.','Only existing game-specific PNGs are selected; other game package is outside scope.'])
 print(json.dumps(dict(assets=[dict(path=a['package_path'],size=[a['width'],a['height']],regions=len(a['regions'])) for a in assets]),indent=2))
 if args.write:
  (ROOT/'work/translation/en/graphics/package.en.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 else:print('Dry run: no writes.')


if __name__=='__main__':main()
