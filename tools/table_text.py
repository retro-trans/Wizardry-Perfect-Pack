"""Export and rebuild fixed-record game databases without altering source files.

Default is a read-only schema and text audit. --write exports ignored Japanese
working files. --rebuild DIRECTORY creates patched decoded members and a report;
full English strings are accepted without truncation, and overflows block output.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'work/source/decoded/USRDIR/data/table.enc'
JA = re.compile('[\u3040-\u30ff\u3400-\u9fff\uff66-\uff9f]')
SCHEMA = {
 'items': (0,432,[(0,42,'name'),(42,42,'alternate_name'),(96,42,'unidentified_name'),(252,90,'special_power_description'),(342,90,'description')]),
 'monsters': (2,1928,[(0,53,'name'),(53,41,'unidentified_name')]+[(200+65*i,65,'ability_%02d'%i) for i in range(17)]+[(1305,600,'lore')]),
 'spells': (4,304,[(0,49,'name'),(54,213,'description')]),
 'quests': (8,892,[(36,82,'title'),(118,82,'client'),(216,338,'request'),(554,338,'objective')]),
 'skills': (9,1123,[(0,81,'name'),(81,1024,'description')]),
 'credits': (11,258,[(0,256,'credit')])
}
PREFIX = dict(items='DI',monsters='DM',spells='DP',quests='DQ',skills='DS',credits='DC')


def collect(archive='table.enc'):
 result={}; audits=[]
 source=ROOT/'work/source/decoded/USRDIR/data'/archive
 for group,(member,stride,fields) in SCHEMA.items():
  path=source/('%04d.dat'%member)
  if not path.exists(): continue
  data=path.read_bytes()
  if not data: continue
  if archive != 'table.enc':
   if group not in ('items','monsters','quests'): continue
   if group in ('items','monsters'):
    stride+=4
    fields=[(offset+4,capacity,kind) for offset,capacity,kind in fields]
  if len(data)%stride: raise ValueError('Nonintegral record count: '+group)
  by_text={}; rows=[]; incomplete=[]
  for record in range(len(data)//stride):
   context=[]
   for offset,capacity,kind in fields:
    raw=data[record*stride+offset:record*stride+offset+capacity]
    terminated=b'\0' in raw; value=raw.split(b'\0',1)[0]
    try: text=value.decode('utf-8'); valid=True
    except UnicodeDecodeError:
     if terminated: raise
     text=value.decode('utf-8',errors='ignore');valid=False
    if any(ord(c)<32 and c not in '\r\n\t' for c in text):
     raise ValueError('Unexpected binary prefix %s %d %d'%(group,record,offset))
    if text: context.append(dict(kind=kind,text=text))
    if not text or not JA.search(text):continue
    occurrence=dict(archive=archive,member=member,record=record,stride=stride,field_offset=offset,offset=record*stride+offset,capacity=capacity,kind=kind,terminated=terminated,valid_utf8=valid,raw_sha256=hashlib.sha256(raw).hexdigest())
    if text not in by_text:
     prefix=PREFIX[group] if archive=='table.enc' else ('PP'+PREFIX[group] if archive=='ppdata.enc' else 'A'+archive[8:10]+PREFIX[group])
     row=dict(id=prefix+('%04d'%len(rows)),ja=text,kind=kind,occurrences=[],contexts=[])
     by_text[text]=row; rows.append(row)
    row=by_text[text];row['occurrences'].append(occurrence)
    if not terminated or not valid: incomplete.append(dict(id=row['id'],record=record,field=kind,valid_utf8=valid,terminated=terminated))
   for row in rows:
    if row['occurrences'][-1]['record']==record and len(row['contexts'])<3: row['contexts'].append(dict(record=record,fields=context))
  label=group if archive=='table.enc' else archive.removesuffix('.enc')+'_'+group
  result[label]=rows
  audits.append(dict(archive=archive,group=label,member=member,stride=stride,records=len(data)//stride,unique=len(rows),occurrences=sum(len(r['occurrences']) for r in rows),incomplete_fields=incomplete,sha256=hashlib.sha256(data).hexdigest()))
 return result,audits


def collect_all():
 groups={};audits=[]
 for archive in ('table.enc','addtable01.enc','addtable02.enc','ppdata.enc'):
  current,details=collect(archive);groups.update(current);audits.extend(details)
 return groups,audits


def rebuild(groups,destination):
 translations={}
 for path in (ROOT/'work/translation/en/databases').rglob('*.en.json'):
  content=json.loads(path.read_text(encoding='utf-8'))
  for row in content['translations']:
   if row['id'] in translations: raise ValueError('Duplicate translation '+row['id'])
   translations[row['id']]=row
 outputs={};report=dict(changes=[],missing=[],overflows=[],review=[])
 for group,rows in groups.items():
  member=SCHEMA[group][0];data=bytearray((SOURCE/('%04d.dat'%member)).read_bytes())
  for row in rows:
   decision=translations.get(row['id'])
   if not decision: report['missing'].append(row['id']);continue
   if decision['status']=='exclude':continue
   if decision['status']=='review':report['review'].append(row['id'])
   value=decision['en'].encode('utf-8')+b'\0'
   for occurrence in row['occurrences']:
    capacity=occurrence['capacity']; offset=occurrence['offset']
    if len(value)>capacity:
     report['overflows'].append(dict(id=row['id'],member=member,record=occurrence['record'],field=occurrence['kind'],capacity=capacity,required=len(value)));continue
    data[offset:offset+capacity]=value+b'\0'*(capacity-len(value))
    report['changes'].append(dict(id=row['id'],member=member,record=occurrence['record'],offset=offset,capacity=capacity,english_bytes=len(value)))
  outputs[member]=bytes(data)
 if destination:
  destination.mkdir(parents=True,exist_ok=True)
  (destination/'table_rebuild_report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
  if not report['overflows']:
   for member,data in outputs.items():
    (destination/('%04d.dat'%member)).write_bytes(data)
 return report


def relocation_plan(groups):
 """Prepare compact tokens and an unbounded string pool for a runtime expander.

 This only prepares data. A renderer hook is required before these members can
 be used in game. Every translated field is relocated, even when it would fit.
 """
 from spell_description_layout import display_text as spell_display
 from skill_description_layout import display_text as skill_display
 from quest_description_layout import display_text as quest_display
 from monster_lore_layout import display_text as lore_display
 translations={}
 for path in (ROOT/'work/translation/en/databases').rglob('*.en.json'):
  for row in json.loads(path.read_text(encoding='utf-8'))['translations']:
   if row['id'] in translations: raise ValueError('Duplicate translation '+row['id'])
   translations[row['id']]=row
 pool=bytearray();entries=[];members={};missing=[];sources=[]
 for group,rows in groups.items():
  archive=rows[0]['occurrences'][0]['archive']
  kind=group.split('_')[-1]
  member=SCHEMA[kind][0]
  original=(ROOT/'work/source/decoded/USRDIR/data'/archive/('%04d.dat'%member)).read_bytes();data=bytearray(original)
  sources.append(dict(archive=archive,group=group,member=member,stride=rows[0]['occurrences'][0]['stride'],bytes=len(original),sha256=hashlib.sha256(original).hexdigest()))
  for row in rows:
   decision=translations.get(row['id'])
   if decision is None:missing.append(row['id']);continue
   if decision['status']=='exclude':continue
   index=len(entries);token=('~T%08X~'%index).encode('ascii')+b'\0'
   if member==2:rendered=lore_display(row,decision)
   elif member==8:rendered=quest_display(row,decision)
   elif member==9:rendered=skill_display(row,decision)
   else:rendered=spell_display(row,decision)
   encoded=rendered.encode('utf-8')+b'\0'
   entries.append(dict(index=index,id=row['id'],offset=len(pool),bytes=len(encoded),status=decision['status'],text=rendered,
                       runtime_reflow=rendered!=decision['en']))
   pool.extend(encoded);pool.extend(b'\0'*(-len(pool)%4))
   for occurrence in row['occurrences']:
    offset=occurrence['offset'];capacity=occurrence['capacity']
    if len(token)>capacity:raise ValueError('Token cannot fit in '+row['id'])
    data[offset:offset+capacity]=token+b'\0'*(capacity-len(token))
  members[(archive,member)]=bytes(data)
 return dict(format='table-text-token-v1',marker='~T%08X~',requires_runtime_expander=True,
             pool_bytes=len(pool),entries=entries,missing=missing,sources=sources),members,bytes(pool)


def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write',action='store_true');parser.add_argument('--rebuild',type=Path);parser.add_argument('--relocate',type=Path,help='Prepare tokenized members and an unbounded string pool; requires a separately verified runtime expander.');args=parser.parse_args()
 groups,audits=collect_all()
 print(json.dumps(audits,indent=2))
 if args.write:
  root=ROOT/'work/translation/ja/databases';root.mkdir(parents=True,exist_ok=True)
  for group,rows in groups.items():
   (root/(group+'.json')).write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
   folder=root/group;folder.mkdir(exist_ok=True)
   for start in range(0,len(rows),80):
    (folder/('%04d.json'%start)).write_text(json.dumps(rows[start:start+80],ensure_ascii=False,indent=2)+'\n',encoding='utf8')
  (ROOT/'work/output/text_census/table_schema.json').write_text(json.dumps(audits,indent=2)+'\n',encoding='utf8')
  print('Exported Japanese database working files; no source changed.')
 if args.rebuild:
  raise ValueError('Perfect Pack uses relocated text; fixed-slot rebuilding is disabled.')
 if args.relocate:
  manifest,members,pool=relocation_plan(groups);args.relocate.mkdir(parents=True,exist_ok=True)
  for (archive,member),data in members.items():
   destination=args.relocate/archive;destination.mkdir(parents=True,exist_ok=True)
   (destination/('%04d.dat'%member)).write_bytes(data)
  (args.relocate/'table_text_pool.bin').write_bytes(pool)
  (args.relocate/'table_relocation.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
  print(json.dumps(dict(tokens=len(manifest['entries']),pool_bytes=len(pool),missing=len(manifest['missing']),requires_runtime_expander=True),indent=2))
 if not args.write and not args.rebuild and not args.relocate: print('Dry run: no files written.')


if __name__=='__main__':main()
