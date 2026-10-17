"""Build a reversible local English overlay. Default: dry run.

Only the known Perfect Pack NPJB00162 executable is accepted. Originals are never changed.
Long executable strings move into a new read-only load segment; only verified
data/TOC pointer sections are redirected. Instructions, SPU images and other
numeric data are not scanned-and-replaced. No PS3 signing or release packaging.
"""
import argparse
from collections import defaultdict
import hashlib
import io
import json
from pathlib import Path
import struct
import xml.etree.ElementTree as ET

from elftools.elf.elffile import ELFFile
from check_translation import ROOT, read_sources, read_english, validate

EXE_HASH = '2e23b466028ac0a18f7f46522fe1847d5c918a129605a2bdc1c56ca31da82bba'
VERSION = '0.1.10'
# Native code has inlined fixed-size copies for these short Japanese labels.
# Relocating them early would omit their terminators. Expand only at the final
# font boundary, after those original copies have safely finished.
DEFERRED_UI_IDS = {'X0016', 'X0055', 'X0176', 'X0291', 'X0292', 'X1336', 'X1337',
                   'X1338', 'X2359', 'X2500', 'X1415', 'X1416', 'X1417',
                   'X1418', 'X1419', 'X1420', 'X1421', 'X0792', 'X1225'}
POINTER_SECTIONS = {(0x450440, 57784), (0x480530, 43232)}
# Mixed shader/data section: only these inspected pointer arrays are safe.
# Other aligned values (notably 0x400000) are shader words, not pointers.
EXTRA_POINTER_RANGES = [(0x50eb0c, 0x50ebc4), (0x529e90, 0x529eb4),
                        (0x52ab20, 0x52ab58), (0x52b2f8, 0x52b2fc)]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def align(value, boundary=16):
    return (value+boundary-1)//boundary*boundary


def parse_events(data):
    records, offset = [], 0
    while offset < len(data):
        if offset+8 > len(data):
            raise ValueError('Truncated event')
        opcode, size = struct.unpack_from('<II', data, offset)
        end = offset+8+size
        if size%4 or end > len(data):
            raise ValueError('Invalid event record')
        records.append((opcode, data[offset+8:end]))
        offset = end
    return records


def pack_events(records):
    return b''.join(struct.pack('<II', op, len(payload))+payload for op, payload in records)


def event_patches(source, sources, english):
    changes = defaultdict(dict)
    for key, row in sources.items():
        if row['source'] != 'events' or key not in english or english[key]['en'] is None:
            continue
        for occ in row['occurrences']:
            changes[occ['file']][occ['record']] = (row, english[key]['en'])
    files, audit = {}, []
    for name, replacements in changes.items():
        before = (source/name).read_bytes()
        records = parse_events(before)
        if pack_events(records) != before:
            raise ValueError('Original event round-trip failed')
        after_records = list(records)
        for index, (row, en) in replacements.items():
            op, payload = records[index]
            if payload.rstrip(b'\0').decode('utf8') != row['ja']:
                raise ValueError('Event source text mismatch '+row['id'])
            if op not in (0x43, 0x46, 0x49, 0x2b):
                raise ValueError('Non-text opcode selected')
            encoded = en.encode('utf8')+b'\0'
            encoded += b'\0'*(-len(encoded)%4)
            after_records[index] = (op, encoded)
        after = pack_events(after_records)
        reread = parse_events(after)
        if reread != after_records or len(reread) != len(records):
            raise ValueError('Patched event round-trip failed')
        for index, (a, b) in enumerate(zip(records, reread)):
            if a[0] != b[0] or index not in replacements and a != b:
                raise ValueError('Event bytecode changed')
        target = name.replace('.edat.unedat', '.evt')
        files[target] = after
        audit.append(dict(file=target, source_file=name, source_sha256=sha(before),
                          bytes_before=len(before), bytes_after=len(after),
                          replaced=len(replacements), records=len(records),
                          nontext_unchanged=True))
    return files, audit


def executable_patch(data, sources, english, table_plan=None, table_pool=None, resolver_object=None, dialogue_object=None,version=VERSION):
    if sha(data) != EXE_HASH:
        raise ValueError('Unknown executable. Trace pointers again for this version.')
    elf = ELFFile(io.BytesIO(data))
    segments = list(elf.iter_segments())
    sections = list(elf.iter_sections())
    selected = [s for s in sections if (s['sh_addr'], s['sh_size']) in POINTER_SECTIONS]
    if len(selected) != len(POINTER_SECTIONS):
        raise ValueError('Pointer table section mismatch')
    # Use an existing empty program-header slot, leaving the original segments,
    # BSS, TLS, process parameters and every original virtual address unchanged.
    empty = [i for i, s in enumerate(segments) if s['p_type']=='PT_LOAD' and s['p_filesz']==s['p_memsz']==s['p_vaddr']==0]
    if not empty:
        raise ValueError('No unused load segment')
    base = align(max(s['p_vaddr']+s['p_memsz'] for s in segments if s['p_type']=='PT_LOAD'), 65536)
    file_base = align(len(data), 65536)
    addresses, blob, lookup = {}, bytearray(), {}
    aliases = []
    for key, row in sources.items():
        if row['source'] != 'executable' or key not in english or english[key]['en'] is None:
            continue
        encoded = english[key]['en'].encode('utf8')+b'\0'
        if encoded not in lookup:
            blob.extend(b'\0'*(-len(blob)%8))
            lookup[encoded] = base+len(blob)
            blob.extend(encoded)
        for occ in row['occurrences']:
            old = occ['address']
            expected = row['ja'].encode('utf8')+b'\0'
            if data[occ['offset']:occ['offset']+len(expected)] != expected:
                raise ValueError('Executable source text mismatch '+key)
            addresses[old] = (old if key in DEFERRED_UI_IDS else lookup[encoded], key)
        if key in DEFERRED_UI_IDS:
            aliases.append((row['occurrences'][0]['address'], lookup[encoded],
                            int(key in {'X1337', 'X1338'}), key))
    from ui_literal_text import collect as collect_ui_literals
    literal_rows=collect_ui_literals(data)
    for row in literal_rows:
        key=row['id']
        if sources[key]['ja']!=row['ja']:raise ValueError('UI literal source mismatch')
        pointers=[]
        for text in (row['ja'],english[key]['en']):
            encoded=text.encode('utf8')+b'\0'
            if encoded not in lookup:
                blob.extend(b'\0'*(-len(blob)%8));lookup[encoded]=base+len(blob);blob.extend(encoded)
            pointers.append(lookup[encoded])
        aliases.append((*pointers,0,key))
    runtime_info = None
    runtime_code = None
    runtime_patches = []
    if table_plan is not None:
        from runtime_text import make_code, resolver_code
        blob.extend(b'\0'*(-len(blob)%16))
        alias_address = base+len(blob)
        for original_address, english_address, prefix, key in aliases:
            blob.extend(struct.pack('>QQQ',original_address,english_address,prefix))
        blob.extend(b'\0'*(-len(blob)%16))
        table_address = base+len(blob)
        pool_address = table_address+len(table_plan['entries'])*8
        for entry in table_plan['entries']:
            blob.extend(struct.pack('>Q',pool_address+entry['offset']))
        blob.extend(table_pool)
        resolver, local_entry = resolver_code(resolver_object)
        from compile_dialogue import message_code
        dialogue=message_code(dialogue_object) if dialogue_object else None
        runtime_code, runtime_patches, runtime_info = make_code(data,resolver,local_entry,table_address,len(table_plan['entries']),dialogue,
                                                               alias_address,len(aliases),branding_version=version)
        runtime_info.update(table_address=hex(table_address),pool_address=hex(pool_address),entries=len(table_plan['entries']))
        runtime_info['deferred_ui'] = [dict(id=k,source_address=hex(a),english_address=hex(b),prefix=bool(p)) for a,b,p,k in aliases]
    elif aliases:
        raise ValueError('Deferred menu labels require --runtime-tables')
    result = bytearray(data)
    from dungeon_patch import redirect_loader
    redirect_loader(data,result)
    refs, count = [], defaultdict(int)
    spans = [(s['sh_offset'], s['sh_offset']+s['sh_size']) for s in selected]+EXTRA_POINTER_RANGES
    for lo, hi in spans:
        for off in range(lo, hi-3, 4):
            old = struct.unpack_from('>I', data, off)[0]
            if old in addresses:
                new, key = addresses[old]
                struct.pack_into('>I', result, off, new)
                refs.append(dict(offset=off, before=old, after=new, id=key))
                count[old] += 1
    missing = [hex(old) for old in addresses if not count[old]]
    if missing:
        raise ValueError('Unreferenced text cannot safely relocate: '+str(missing[:20]))
    if not blob:
        raise ValueError('No executable translations selected')
    result.extend(b'\0'*(file_base-len(result)))
    result.extend(blob)
    phoff = elf.header['e_phoff']+empty[0]*elf.header['e_phentsize']
    struct.pack_into('>IIQQQQQQ', result, phoff, 1, 4, file_base, base, base, len(blob), len(blob), 65536)
    if runtime_code is not None:
        from runtime_text import CODE_BASE
        off = CODE_BASE-0x10000
        result[off:off+len(runtime_code)] = runtime_code
        for patch_offset, payload in runtime_patches:
            result[patch_offset:patch_offset+len(payload)] = payload
        first = segments[0]
        if first['p_offset'] != 0 or first['p_vaddr'] != 0x10000:
            raise ValueError('Unexpected first load segment')
        end = off+len(runtime_code)
        ph0 = elf.header['e_phoff']
        struct.pack_into('>QQ',result,ph0+32,end,end)
    # Add an allocated section for auditing tools. Preserve all original section
    # indices, copy their headers, and point e_shoff to the new table.
    shoff, shsize, shnum = elf.header['e_shoff'], elf.header['e_shentsize'], elf.header['e_shnum']
    result.extend(b'\0'*(-len(result)%8))
    new_shoff = len(result)
    result.extend(data[shoff:shoff+shsize*shnum])
    result.extend(struct.pack('>IIQQQQIIQQ', 0, 1, 2, base, file_base, len(blob), 0, 0, 8, 0))
    struct.pack_into('>Q', result, 0x28, new_shoff)
    struct.pack_into('>H', result, 0x3c, shnum+1)
    patched = bytes(result)
    audit_elf = ELFFile(io.BytesIO(patched))
    new_segment = list(audit_elf.iter_segments())[empty[0]]
    if new_segment['p_vaddr'] != base or new_segment.data() != blob:
        raise ValueError('Translated load segment verification failed')
    for ref in refs:
        if struct.unpack_from('>I', patched, ref['offset'])[0] != ref['after']:
            raise ValueError('Relocated pointer verification failed')
    for section in sections:
        if section['sh_flags']&4:
            off, size = section['sh_offset'], section['sh_size']
            expected = bytearray(data[off:off+size])
            for patch_offset,payload in runtime_patches:
                if off <= patch_offset and patch_offset+len(payload) <= off+size:
                    expected[patch_offset-off:patch_offset-off+len(payload)] = payload
            if bytes(expected) != patched[off:off+size]:
                raise ValueError('Original executable instructions changed')
    return patched, dict(original_sha256=sha(data), patched_sha256=sha(patched),
                         strings=len(addresses), pointers=len(refs), segment_address=hex(base),
                         segment_bytes=len(blob), instructions_unchanged=not runtime_patches,
                         original_instructions_preserved_except_verified_hooks=True,runtime=runtime_info,
                         pointer_changes=refs, verification='Static checks only; runtime and layout pending.')


def trophy_patch(data, sources, english):
    if data[:4] != bytes.fromhex('dca24d00'):
        raise ValueError('Invalid trophy archive')
    count, stride = struct.unpack_from('>II', data, 0x10)
    if stride != 64:
        raise ValueError('Unexpected trophy entry size')
    entries, changed = [], 0
    for i in range(count):
        entry = bytearray(data[64+i*64:128+i*64])
        name = entry[:32].split(b'\0')[0].decode('ascii')
        off, size = struct.unpack_from('>QQ', entry, 32)
        payload = data[off:off+size]
        if name == 'TROP.SFM':
            tree = ET.fromstring(payload)
            elements = list(tree.iter())
            for key, row in sources.items():
                if row['source'] != 'trophies' or key not in english or english[key]['en'] is None:
                    continue
                for occ in row['occurrences']:
                    el = elements[occ['element']]
                    if el.text != row['ja'] or el.tag != occ['tag']:
                        raise ValueError('Trophy source mismatch '+key)
                    el.text = english[key]['en']
                    changed += 1
            payload = ET.tostring(tree, encoding='utf-8', xml_declaration=True)
        entries.append((entry, payload))
    result = bytearray(data[:64+count*64])
    result.extend(b'\0'*(-len(result)%16))
    for i, (entry, payload) in enumerate(entries):
        struct.pack_into('>QQ', entry, 32, len(result), len(payload))
        result[64+i*64:128+i*64] = entry
        result.extend(payload)
        result.extend(b'\0'*(-len(result)%16))
    struct.pack_into('>Q', result, 8, len(result))
    # RPCS3 TRPHeader and checksum algorithm: SHA1 field begins at 0x1c.
    result[0x1c:0x30] = b'\0'*20
    result[0x1c:0x30] = hashlib.sha1(result).digest()
    verification = bytearray(result)
    verification[0x1c:0x30] = b'\0'*20
    if hashlib.sha1(verification).digest() != result[0x1c:0x30]:
        raise ValueError('Trophy checksum failed')
    return bytes(result), dict(nodes=changed, checksum_verified=True,
                              note='Console/NP signature and trophy installation unverified.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'work/source/NPJB00162')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--version', default=VERSION)
    parser.add_argument('--runtime-tables', action='store_true', help='Include relocated database text and PPU renderer wrappers')
    parser.add_argument('--resolver-object', type=Path, default=ROOT/'work/output/text_resolver.o')
    parser.add_argument('--dialogue-object', type=Path, default=ROOT/'work/output/dialogue_layout.o')
    parser.add_argument('--graphics', action='store_true', help='Include generated English title/help archives and metadata')
    parser.add_argument('--movie', type=Path, help='Include a structurally verified English opening PAMF')
    parser.add_argument('--allow-incomplete', action='store_true')
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    import re
    if not re.fullmatch(r'0\.\d+\.\d+',args.version):
        raise ValueError('Use a 0.x.y build version')
    if args.output is None:
        args.output = ROOT/'work/output'/args.version
    sources, english = read_sources(), read_english()
    validation = validate(sources, english)
    if validation['errors'] or validation['missing'] and not args.allow_incomplete:
        raise ValueError('Translation validation failed. Run check_translation.py first.')
    files, events = event_patches(args.source, sources, english)
    from dungeon_patch import generate as dungeon_files
    dungeon_overlay,dungeon_audit=dungeon_files(args.source,sources,english)
    files.update(dungeon_overlay)
    table_plan = table_pool = None
    if args.runtime_tables:
        from enc_archive import unpack, pack
        from table_text import collect_all, relocation_plan
        groups, table_schema = collect_all()
        table_plan,members,table_pool = relocation_plan(groups)
        if table_plan['missing'] and not args.allow_incomplete:
            raise ValueError('Database translation decisions missing: '+str(len(table_plan['missing'])))
        for archive in ('table.enc','addtable01.enc','addtable02.enc','ppdata.enc'):
            archive_path = 'USRDIR/data/'+archive
            original_members = unpack((args.source/archive_path).read_bytes())
            after_members = list(original_members)
            for (member_archive,member),payload in members.items():
                if member_archive==archive:
                    after_members[member] = payload
            files[archive_path] = pack(after_members)
    exe, exe_audit = executable_patch((args.source/'USRDIR/EBOOT.elf').read_bytes(), sources, english,
                                       table_plan,table_pool,args.resolver_object,args.dialogue_object,args.version)
    files['USRDIR/EBOOT.elf'] = exe
    trophy_paths=list(args.source.glob('TROPDIR/*/TROPHY.TRP'))
    if len(trophy_paths)!=1: raise ValueError('Expected exactly one trophy archive')
    trophy, trophy_audit = trophy_patch(trophy_paths[0].read_bytes(), sources, english)
    files[trophy_paths[0].relative_to(args.source).as_posix()] = trophy
    if args.graphics:
        from sfo_title import translate_sfo
        for name in ('PARAM.SFO',):
            files[name] = translate_sfo((args.source/name).read_bytes())[0]
        for name in ('title.enc','ending.enc','title2.enc'):
            path=ROOT/'work/output/graphics_english'/name
            if not path.is_file():
                raise ValueError('Generate English graphics first: '+name)
            files['USRDIR/data/texture/'+name] = path.read_bytes()
        from render_package import generate as package_graphics
        package_files,package_report=package_graphics(args.source)
        files.update(package_files)
    movie_audit = None
    if args.movie:
        # The movie tool must finish its independent preservation/decode report.
        audit_path = args.movie.with_suffix('.verification.json')
        if not audit_path.is_file():
            raise ValueError('English movie verification report missing: '+str(audit_path))
        movie_audit = json.loads(audit_path.read_text(encoding='utf8'))
        movie_data = args.movie.read_bytes()
        if movie_audit.get('output_sha256') != sha(movie_data) or movie_audit.get('result') != 'verified':
            raise ValueError('Movie verification did not pass or hash mismatched')
        files['USRDIR/movie/opening.pam'] = movie_data
    manifest = dict(version=args.version, target='NPJB00162', status='local draft; not release-ready',
                    coverage=validation['by_source'], review_flags=validation['review_count'],
                    files=[dict(file=name, bytes=len(data), sha256=sha(data)) for name,data in sorted(files.items())],
                    events=events, executable=exe_audit, trophies=trophy_audit,
                    dungeons=dungeon_audit,
                    databases=None if table_plan is None else dict(strings=len(table_plan['entries']),missing=table_plan['missing'],pool_bytes=len(table_pool),
                                                                 display_reflows=sum(e.get('runtime_reflow',False) for e in table_plan['entries'])),
                    graphics=None if not args.graphics else dict(help_pages=8,package=package_report),
                    movie=movie_audit,
                    pending=(['Opening movie playback/listening'] if args.movie and not movie_audit.get('ps3_playback_verified') else [] if args.movie else ['Opening movie captions'])+['Unreadable texture fragments', 'In-game line wrapping and clipping',
                             'Save/load and branch coverage', 'Retail console signing/installation',
                             'Scenario content/license coverage', 'Full playthrough'],
                    rollback='Delete this isolated overlay; original source files were never modified.')
    print(json.dumps(dict(version=args.version, files=len(files), events=len(events),
                          executable_strings=exe_audit['strings'], pointer_changes=exe_audit['pointers'],
                          new_segment=exe_audit['segment_address'], trophies=trophy_audit,
                          event_max_bytes=max(r['bytes_after'] for r in events),
                          pending=manifest['pending']), indent=2))
    print('Sample:', next((en['en'] for key,en in english.items() if key.startswith('E') and en['en']), ''))
    if args.write:
        if args.output.exists():
            raise ValueError('Output already exists; choose a fresh output directory.')
        args.output.mkdir(parents=True)
        for name, data in files.items():
            dest = args.output/'overlay'/name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        (args.output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf8')
        print('Created isolated local overlay:', args.output)
    else:
        print('Dry run: no game files written.')


if __name__ == '__main__':
    main()
