"""Independently verify a local overlay against source exports and originals.

Read-only unless --write saves a report. Does not substitute for play testing.
"""
import argparse
from collections import defaultdict
import hashlib
import io
import json
from pathlib import Path
import struct
from elftools.elf.elffile import ELFFile
from check_translation import ROOT,read_sources,read_english,validate
from enc_archive import unpack


def records(data):
 out=[];at=0
 while at<len(data):
  if at+8>len(data):raise ValueError('Short event header')
  op,size=struct.unpack_from('<II',data,at);end=at+8+size
  if size%4 or end>len(data):raise ValueError('Bad event length')
  out.append((op,data[at+8:end]));at=end
 return out


def verify(build):
 source=ROOT/'work/source/NPJB00162';overlay=build/'overlay'
 manifest=json.loads((build/'manifest.json').read_text(encoding='utf8'))
 if manifest['target']!='NPJB00162':raise ValueError('Wrong game target')
 dungeon_targets={r['file'] for r in manifest.get('dungeons',[])}
 for row in manifest['files']:
  data=(overlay/row['file']).read_bytes()
  if len(data)!=row['bytes'] or hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('Manifest mismatch')
  if not (source/row['file']).exists() and not row['file'].endswith('S0103.evt') and row['file'] not in dungeon_targets:raise ValueError('Unexpected output path')
 actual={p.relative_to(overlay).as_posix() for p in overlay.rglob('*') if p.is_file()}
 if actual!={r['file'] for r in manifest['files']}:raise ValueError('Unmanifested overlay file')
 sources,english=read_sources(),read_english();validation=validate(sources,english)
 if validation['errors'] or validation['missing']:raise ValueError('Incomplete/invalid canonical translation')
 event_changes=defaultdict(dict);fields=defaultdict(list)
 for key,row in sources.items():
  decision=english[key]
  if decision['en'] is None:continue
  for occ in row['occurrences']:
   if row['source']=='events':event_changes[occ['file']][occ['record']]=decision['en']
   elif row['source'].startswith('databases/'):
    fields[(occ['archive'],occ['member'])].append((occ,decision['en'],row))
 event_count=nontext_count=0
 for name,changes in event_changes.items():
  before=records((source/name).read_bytes());after=records((overlay/name.replace('.edat.unedat','.evt')).read_bytes())
  if len(before)!=len(after):raise ValueError('Event record count changed')
  for i,(old,new) in enumerate(zip(before,after)):
   if old[0]!=new[0]:raise ValueError('Event opcode changed')
   if i not in changes:
    if old!=new:raise ValueError('Nonselected event changed')
    nontext_count+=1
   else:
    if new[1].rstrip(b'\0').decode('utf8')!=changes[i]:raise ValueError('Event text mismatch')
    event_count+=1
 exe=(overlay/'USRDIR/EBOOT.elf').read_bytes();elf=ELFFile(io.BytesIO(exe));segments=list(elf.iter_segments())
 def memory(address,length):
  for s in segments:
   if s['p_type']=='PT_LOAD' and s['p_vaddr']<=address and address+length<=s['p_vaddr']+s['p_filesz']:
    off=s['p_offset']+address-s['p_vaddr'];return exe[off:off+length]
  raise ValueError('Read outside load segments')
 # Verify every relocated string against its own context, independently of
 # the builder's allocated pool addresses or override audit metadata.
 original_exe=(source/'USRDIR/EBOOT.elf').read_bytes()
 overrides={}
 for key,decision in english.items():
  for row in decision.get('reference_overrides',[]):
   pointer=int(row['pointer_offset'],16)
   if pointer in overrides:raise ValueError('Duplicate reference translation')
   overrides[pointer]=(key,int(row['source_address'],16),row['en'])
 deferred={r['id'] for r in manifest['executable']['runtime'].get('deferred_ui',[])}
 verified_overrides=set();executable_refs=0
 for ref in manifest['executable']['pointer_changes']:
  pointer,old,key=ref['offset'],ref['before'],ref['id']
  if struct.unpack_from('>I',original_exe,pointer)[0]!=old:raise ValueError('Original text reference changed')
  target=struct.unpack_from('>I',exe,pointer)[0]
  if target!=ref['after']:raise ValueError('Relocated text reference mismatch')
  expected=english[key]['en']
  if pointer in overrides:
   wanted_key,wanted_old,expected=overrides[pointer]
   if (key,old)!=(wanted_key,wanted_old):raise ValueError('Reference semantic context changed')
   verified_overrides.add(pointer)
  if key not in deferred:
   encoded=expected.encode('utf8')+b'\0'
   if memory(target,len(encoded))!=encoded:raise ValueError('Wrong executable reference translation')
   executable_refs+=1
 if verified_overrides!=set(overrides):raise ValueError('Context translation was not installed')
 table=int(manifest['executable']['runtime']['table_address'],16);entries=manifest['executable']['runtime']['entries'];db_count=0
 runtime=manifest['executable']['runtime'];alias_rows=runtime.get('deferred_ui',[])
 heading=runtime.get('class_heading')
 if heading:
  from class_heading import CLASS_IDS,GETTER,GETTER_BYTES,SITE
  from runtime_text import instruction,branch,load_address
  stub=int(heading['stub'],16);class_table=int(heading['table_address'],16)
  if memory(SITE,4)!=instruction(branch(SITE,stub,True)):raise ValueError('Class heading hook mismatch')
  expected=b''.join(instruction(w) for w in load_address(9,class_table))+GETTER_BYTES[4:]
  if memory(stub,len(expected))!=expected or memory(GETTER,16)!=GETTER_BYTES:raise ValueError('Class heading lookup mismatch')
  for i,key in enumerate(CLASS_IDS):
   pointer=struct.unpack('>I',memory(class_table+4*i,4))[0];text=english[key]['en'].encode('utf8')+b'\0'
   if memory(pointer,len(text))!=text:raise ValueError('Class heading name mismatch: '+key)
 for i,row in enumerate(alias_rows):
  original_address,english_address,prefix=struct.unpack('>QQQ',memory(int(runtime['alias_address'],16)+i*24,24))
  key=row['id'];original=sources[key]['ja'].encode('utf8')+b'\0';translated=english[key]['en'].encode('utf8')+b'\0'
  if memory(original_address,len(original))!=original or memory(english_address,len(translated))!=translated:raise ValueError('Deferred UI label mismatch')
  if prefix!=int(row['prefix']):raise ValueError('Deferred UI prefix mismatch')
  for occurrence in sources[key]['occurrences'] if sources[key]['source']=='executable' else []:
   refs=[r for r in manifest['executable']['pointer_changes'] if r['id']==key and r['before']==occurrence['address']]
   if not refs or any(r['after']!=r['before'] for r in refs):raise ValueError('Fixed-copy label relocated before native copy')
 if any(sources[row['id']]['source']=='ui_literals' for row in alias_rows):
  from ui_literal_text import collect as literal_sources
  literal_sources((source/'USRDIR/EBOOT.elf').read_bytes())
 item_cells=runtime.get('item_cells',{}).get('cells',[])
 if item_cells:
  from item_cell_layout import CELLS,CALLER_WIDTH_SLOT,FONT_SIZE
  from runtime_text import instruction,branch,dform
  if len(item_cells)!=len(CELLS):raise ValueError('Item fitting group count changed')
  for cell,(_,measure,_,mw,mh,sw,sh,setter,draw,cap) in zip(item_cells,CELLS):
   expected={measure:instruction(branch(measure,int(cell['bridge'],16),True)),
             mw:instruction(dform(14,5,0,FONT_SIZE)),mh:instruction(dform(14,6,0,FONT_SIZE)),
             sw:instruction(dform(32,3,1,CALLER_WIDTH_SLOT)),sh:instruction(dform(14,4,0,FONT_SIZE)),
             setter:instruction(branch(setter,0xd0794,True)),draw:instruction(branch(draw,0xd15ac,True))}
   if any(memory(address,4)!=data for address,data in expected.items()):raise ValueError('Item fitting instruction mismatch')
 preview_rows=0
 if runtime.get('item_preview'):
  from item_preview_layout import LABEL_SITES,VALUE_SITES
  for address in LABEL_SITES:
   if memory(address,4)!=bytes.fromhex('23bd008c'):raise ValueError('Armor label position mismatch')
  for address in VALUE_SITES:
   if memory(address,4)!=bytes.fromhex('3929008c'):raise ValueError('Armor value position mismatch')
  for row in runtime['item_preview'].get('weapon_changes',[]):
   if memory(int(row['address'],16),4)!=struct.pack('>I',int(row['after'],16)):raise ValueError('Weapon preview position mismatch')
  preview_rows=len(LABEL_SITES)
 panel_changes=runtime.get('menu_panels',{}).get('changes',[])
 for row in panel_changes:
  if memory(int(row['address'],16),4)!=struct.pack('>I',int(row['after'],16)):raise ValueError('Menu panel patch mismatch')
 if runtime.get('bestiary_status'):
  from bestiary_status_layout import CHANGES,COPIES
  for address,_,after in CHANGES:
   if memory(address,4)!=struct.pack('>I',after):raise ValueError('Bestiary status position mismatch')
  if not {row[0] for row in COPIES}<=deferred:raise ValueError('Bestiary fixed-copy aliases missing')
 battle=runtime.get('battle')
 collection=runtime.get('item_collection')
 if collection:
  from item_collection_layout import SITES,image,labels
  from runtime_text import instruction,branch
  stub=int(collection['stub'],16);expected,_=image(stub,labels())
  if memory(stub,len(expected))!=expected:raise ValueError('Compact collection labels/stub mismatch')
  for site in SITES:
   if memory(site,4)!=instruction(branch(site,stub,True)):raise ValueError('Collection category call mismatch')
 branding=runtime.get('title_branding')
 name_entry=runtime.get('name_entry')
 if name_entry:
  from name_entry import CHANGES,STATE_POINTER,STATE_BYTES,SETTER,LIMIT,INITIAL_OFFSET,RESULT_OFFSET
  from runtime_text import branch,instruction
  state=int(name_entry['state_address'],16)
  scratch=[s for s in segments if s['p_type']=='PT_LOAD' and s['p_vaddr']==state]
  if len(scratch)!=1 or scratch[0]['p_flags']!=6 or scratch[0]['p_filesz']!=0 or scratch[0]['p_memsz']!=STATE_BYTES:
   raise ValueError('Name-entry writable state segment mismatch')
  original_segments=list(ELFFile(io.BytesIO(original_exe)).iter_segments())
  for index,segment in enumerate(original_segments):
   if index and segment['p_memsz'] and dict(segment.header)!=dict(segments[index].header):
    raise ValueError('Original writable, TLS or process segment changed')
  if any(s['p_type']=='PT_LOAD' and s['p_vaddr']!=state and s['p_memsz'] and
         state<s['p_vaddr']+s['p_memsz'] and state+STATE_BYTES>s['p_vaddr'] for s in segments):
   raise ValueError('Name-entry state overlaps another load segment')
  if memory(STATE_POINTER,4)!=struct.pack('>I',state):raise ValueError('Name-entry state redirect mismatch')
  for address,_,word in CHANGES:
   if memory(address,4)!=instruction(word):raise ValueError('Name-entry instruction mismatch')
  if memory(SETTER,4)!=instruction(branch(SETTER,int(name_entry['helper'],16))):raise ValueError('Name setter hook mismatch')
  payload=memory(int(name_entry['helper_start'],16),name_entry['helper_bytes'])
  if hashlib.sha256(payload).hexdigest()!=name_entry['helper_sha256']:raise ValueError('Name setter payload mismatch')
  if memory(int(name_entry['helper'],16),8)!=bytes.fromhex('7863002078840020'):
   raise ValueError('Name setter argument ABI mismatch')
  if memory(int(name_entry['helper'],16)+8,4)!=instruction(branch(int(name_entry['helper'],16)+8,int(name_entry['helper_start'],16))):
   raise ValueError('Name setter entry continuation mismatch')
  if INITIAL_OFFSET+(LIMIT+1)*2>RESULT_OFFSET or RESULT_OFFSET+(LIMIT+1)*2>STATE_BYTES:
   raise ValueError('Name-entry UTF16 buffers overlap')
  if name_entry['saved_name_bytes']!=33 or name_entry['saved_name_offset']!='0x1bd' or name_entry['save_layout_changed']:
   raise ValueError('Character name/save layout mismatch')
 if branding:
  from title_branding import SITE,GUARDS,texts
  from runtime_text import instruction,branch
  if memory(SITE,4)!=instruction(branch(SITE,int(branding['bridge'],16))):raise ValueError('Title footer bridge mismatch')
  for address,expected in GUARDS:
   expected=bytes.fromhex(expected)
   for off in range(0,len(expected),4):
    if address+off==SITE:continue
    if any(int(h['function'],16)<=address+off<int(h['function'],16)+16 for h in runtime['hooks']):continue
    if memory(address+off,min(4,len(expected)-off))!=expected[off:off+4]:raise ValueError('Title footer context changed')
  for address,text in zip(branding['string_addresses'],texts(manifest['version'])):
   value=text.encode('ascii')+b'\0'
   if memory(int(address,16),len(value))!=value:raise ValueError('Title footer text/version mismatch')
 narration=runtime.get('narration')
 if narration:
  from narration_layout import SITE,EXPECTED_CONTEXT,FINAL_WAIT_SITE,EXPECTED_FINAL_WAIT
  from runtime_text import instruction,branch
  if memory(SITE,4)!=instruction(branch(SITE,int(narration['bridge'],16),True)):raise ValueError('Anonymous narration bridge mismatch')
  if memory(SITE-8,8)!=EXPECTED_CONTEXT[:8] or memory(SITE+4,len(EXPECTED_CONTEXT)-12)!=EXPECTED_CONTEXT[12:]:raise ValueError('Anonymous narration continuation changed')
  if memory(FINAL_WAIT_SITE,len(EXPECTED_FINAL_WAIT))!=EXPECTED_FINAL_WAIT:raise ValueError('Narration final script wait changed')
 inventory=runtime.get('inventory_names')
 if inventory:
  from inventory_layout import DRAW_SITE,GUARDS
  from runtime_text import instruction,branch
  if memory(DRAW_SITE,4)!=instruction(branch(DRAW_SITE,int(inventory['bridge'],16),True)):raise ValueError('Inventory name bridge mismatch')
  for address,expected in GUARDS:
   expected=bytes.fromhex(expected)
   for off in range(0,len(expected),4):
    if address+off==DRAW_SITE:continue
    if memory(address+off,4)!=expected[off:off+4]:raise ValueError('Inventory surrounding instructions changed')
 if battle:
  from runtime_text import instruction,branch
  from battle_layout import EXPECTED_CONTEXT,SITE
  if memory(SITE,4)!=instruction(branch(SITE,int(battle['bridge'],16),True)):raise ValueError('Battle reward bridge mismatch')
  if memory(SITE+4,len(EXPECTED_CONTEXT)-8)!=EXPECTED_CONTEXT[8:]:raise ValueError('Battle final wait changed')
 dungeon_count=0
 if manifest.get('dungeons'):
  from dungeon_scene import decrypt_scene,inspect_scene,NAME_CAPACITY
  from dungeon_patch import PATH_OFFSET,OLD_PATH,NEW_PATH
  original_exe=(source/'USRDIR/EBOOT.elf').read_bytes()
  if exe[PATH_OFFSET:PATH_OFFSET+len(OLD_PATH)]!=NEW_PATH+b'\0'*(len(OLD_PATH)-len(NEW_PATH)):raise ValueError('Dungeon loader redirect mismatch')
  if dungeon_targets!={'USRDIR/data/obj/Scenes/dun%02d.enc'%i for i in range(14)}:raise ValueError('Dungeon output set mismatch')
  for row in manifest['dungeons']:
   original_path=source/row['source_file']
   if row['source_file']!=row['file'].replace('.enc','.edat'):raise ValueError('Unexpected dungeon source path')
   old,_=inspect_scene(decrypt_scene(original_path.read_bytes(),original_exe,original_path.name),original_path.name)
   new,details=inspect_scene((overlay/row['file']).read_bytes(),row['file'])
   if old[0][NAME_CAPACITY:]!=new[0][NAME_CAPACITY:] or old[1:]!=new[1:]:raise ValueError('Dungeon floors, metadata or background changed')
   if row['id']:
    decision=english[row['id']]
    if details['name']!=decision.get('display',decision['en']):raise ValueError('Dungeon name translation mismatch')
    dungeon_count+=1
   elif old!=new:raise ValueError('Unselected dungeon changed')
 spell_fields=skill_fields=quest_fields=lore_fields=item_description_fields=0
 for archive in ('table.enc','addtable01.enc','addtable02.enc','ppdata.enc'):
  before=unpack((source/'USRDIR/data'/archive).read_bytes());after=unpack((overlay/'USRDIR/data'/archive).read_bytes())
  if len(before)!=len(after):raise ValueError('Archive member count changed')
  for member,(old,new) in enumerate(zip(before,after)):
   if len(old)!=len(new):raise ValueError('Database member resized')
   a,b=bytearray(old),bytearray(new)
   for occ,en,row in fields[(archive,member)]:
    at,cap=occ['offset'],occ['capacity'];token=new[at:at+cap].split(b'\0')[0]
    if len(token)!=11 or token[:2]!=b'~T' or token[-1:]!=b'~':raise ValueError('Bad relocation token')
    index=int(token[2:10],16)
    if index>=entries:raise ValueError('Relocation token out of bounds')
    pointer=struct.unpack('>Q',memory(table+index*8,8))[0]
    from spell_description_layout import render as render_spell
    from skill_description_layout import render as render_skill
    from quest_description_layout import display_text as quest_display,is_description as quest_description
    from monster_lore_layout import display_text as lore_display,is_lore
    from item_description_layout import display_text as item_display,is_description as item_description
    rendered=en
    if member==0:
     rendered=item_display(row,dict(en=en))
     if item_description(row):item_description_fields+=1
    if member==2:
     rendered=lore_display(row,dict(en=en))
     if is_lore(row):lore_fields+=1
    if member==8:
     rendered=quest_display(row,dict(en=en))
     if quest_description(row):quest_fields+=1
    if archive=='table.enc' and occ['kind']=='description':
     if member==4:rendered=render_spell(en)
     elif member==9:rendered=render_skill(en)
    expected=rendered.encode('utf8')+b'\0'
    if archive=='table.enc' and member==4 and occ['kind']=='description':spell_fields+=1
    if archive=='table.enc' and member==9 and occ['kind']=='description':skill_fields+=1
    if memory(pointer,len(expected))!=expected:raise ValueError('Wrong relocated English text')
    a[at:at+cap]=b'\0'*cap;b[at:at+cap]=b'\0'*cap;db_count+=1
   if a!=b:raise ValueError('Non-text database bytes changed')
 movie_verified=False
 if manifest.get('movie'):
  from movie_pamf import inspect as inspect_movie,EXPECTED
  original=(source/'USRDIR/movie/opening.pam').read_bytes();modified=(overlay/'USRDIR/movie/opening.pam').read_bytes()
  if hashlib.sha256(original).hexdigest()!=EXPECTED:raise ValueError('Original movie hash mismatch')
  a,_,_=inspect_movie(original);b,_,_=inspect_movie(modified)
  for key in ('bytes','streams','header_sha256','private_packet_sha256','random_access_map_sha256','timestamp_headers_sha256','all_non_video_bytes_sha256'):
   if a[key]!=b[key]:raise ValueError('Movie preservation failed: '+key)
  if manifest['movie'].get('result')!='verified' or manifest['movie'].get('output_sha256')!=hashlib.sha256(modified).hexdigest():raise ValueError('Movie report/hash mismatch')
  movie_verified=True
 return dict(result='static_overlay_verified',target='NPJB00162',version=manifest['version'],manifest_files=len(actual),
             event_text_occurrences=event_count,event_nonselected_records_unchanged=nontext_count,
             database_fields_resolved=db_count,database_nontext_bytes_unchanged=True,deferred_ui_labels_verified=len(alias_rows),
             dungeon_names_verified=dungeon_count,dungeon_nontext_members_unchanged=True,
             item_cell_groups_verified=len(item_cells),armor_preview_rows_verified=preview_rows,
             menu_panel_patches_verified=len(panel_changes),battle_reward_pagination_installed=bool(battle),
             bestiary_status_patches_verified=len(runtime.get('bestiary_status',{}).get('changes',[])),
             compact_collection_categories_verified=12 if collection else 0,
             spell_description_fields_verified=spell_fields,
             skill_description_fields_verified=skill_fields,
             quest_description_fields_verified=quest_fields,
             monster_lore_fields_verified=lore_fields,
             item_description_fields_verified=item_description_fields,
             inventory_name_fitting_installed=bool(inventory),
             anonymous_narration_pagination_installed=bool(narration),
             title_version_and_url_installed=bool(branding),
             name_entry_character_limit=name_entry['character_limit'] if name_entry else 6,
             bounded_name_setter_installed=bool(name_entry),
             original_game_unchanged=True,other_game_package_patched=False,
             canonical_decisions=validation['decisions'],review_flags=validation['review_count'],movie_container_preservation_verified=movie_verified,
             executable_text_references_verified=executable_refs,context_specific_references_verified=len(verified_overrides),
             runtime_execution_verified=False,full_playthrough_verified=False)


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('build',type=Path);p.add_argument('--write',action='store_true');args=p.parse_args()
 result=verify(args.build);print(json.dumps(result,indent=2))
 if args.write:(args.build/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')


if __name__=='__main__':main()
