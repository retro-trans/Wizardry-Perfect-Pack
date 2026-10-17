"""Validate an English-only ID-to-text draft before merging; dry run by default."""
import argparse
import json
import re
from pathlib import Path
from check_translation import ROOT,read_sources,read_english,validate


def source_lines(source,english):
 """Balance authored paragraphs over the original line/blank-line structure."""
 shape=source.split('\n');groups=[]
 for i,line in enumerate(shape):
  if line:
   if i==0 or not shape[i-1]:groups.append([])
   groups[-1].append(i)
 paragraphs=english.split('\n\n')
 if len(groups)!=len(paragraphs):raise ValueError('Paragraph count mismatch')
 output=['']*len(shape)
 for indices,paragraph in zip(groups,paragraphs):
  words=paragraph.split();count=len(indices)
  if len(words)<count:raise ValueError('Insufficient words for original line count')
  # Dynamic-programming line breaks; never alter, omit or abbreviate words.
  target=(sum(map(len,words))+len(words)-count)/count
  dp={(0,0):(0,[])}
  for lines in range(1,count+1):
   for end in range(lines,len(words)-(count-lines)+1):
    options=[]
    for start in range(lines-1,end):
     if (lines-1,start) not in dp:continue
     line=' '.join(words[start:end]);cost,previous=dp[(lines-1,start)]
     options.append((cost+(len(line)-target)**2,previous+[line]))
    dp[(lines,end)]=min(options,key=lambda v:v[0])
  for index,line in zip(indices,dp[(count,len(words))][1]):output[index]=line
 result='\n'.join(output)
 if ' '.join(result.split())!=' '.join(english.split()):raise ValueError('Line-break content mismatch')
 return result


def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('draft',type=Path)
 p.add_argument('--write',action='store_true')
 p.add_argument('--replace-existing',action='store_true',help='Replace specifically named existing decisions after review')
 args=p.parse_args()
 sources=read_sources();english=read_english()
 draft=json.loads(args.draft.read_text(encoding='utf8'))
 selected={}
 for key,value in draft['translations'].items():
  if key in english and not args.replace_existing: raise ValueError('Decision already exists: '+key)
  if key not in english and args.replace_existing:raise ValueError('No existing decision to replace: '+key)
  if key not in sources:raise ValueError('Unknown ID: '+key)
  decision=dict(en=value,status='translated') if isinstance(value,str) else value
  if draft.get('reflow_source_newlines'):
   decision['en']=source_lines(sources[key]['ja'],decision['en'])
  selected[key]=dict(decision,id=key,output_file='draft',context=draft['context'])
 result=validate(sources,selected)
 if result['errors']:raise ValueError(str(result['errors']))
 print('New decisions:',len(selected))
 print('Samples:',json.dumps(list(selected.values())[:3],ensure_ascii=False))
 if not args.write:
  print('Dry run: nothing written.');return
 files={}
 for key,decision in selected.items():
  source=sources[key]['source'];rows=[r for r in sources.values() if r['source']==source]
  index=next(i for i,r in enumerate(rows) if r['id']==key)
  dest=ROOT/'work/translation/en'/source/('%04d.en.json'%(index//80*80))
  if dest not in files:
   files[dest]=json.loads(dest.read_text(encoding='utf8')) if dest.exists() else dict(translations=[],rows_examined=0)
  if args.replace_existing:
   files[dest]['translations']=[r for r in files[dest]['translations'] if r['id']!=key]
  decision.pop('output_file')
  files[dest]['translations'].append(decision)
 for dest,doc in files.items():
  doc['translations'].sort(key=lambda r:r['id'])
  doc['rows_in_slice']=len(doc['translations'])
  doc['rows_examined']=max(doc.get('rows_examined',0),len(doc['translations']))
  doc['context_note']=draft['context']
  dest.parent.mkdir(parents=True,exist_ok=True)
  dest.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print('Updated',len(files),'English slices.')


if __name__=='__main__':main()
