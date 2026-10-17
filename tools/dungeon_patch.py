"""Plan plain ENC dungeon overlays from authenticated protected originals."""
import hashlib
from pathlib import Path
from dungeon_scene import decrypt_scene, inspect_scene, NAME_CAPACITY
from enc_archive import pack

PATH_OFFSET=0x3fb798
OLD_PATH=b'/obj/Scenes/dun%02d.edat\0'
NEW_PATH=b'/obj/Scenes/dun%02d.enc\0'


def generate(source,sources,english):
    executable=(source/'USRDIR/EBOOT.elf').read_bytes()
    changes={}
    for key,row in sources.items():
        if row['source']!='dungeons':continue
        decision=english[key]
        value=decision.get('display',decision['en'])
        encoded=value.encode('utf8')+b'\0'
        if len(encoded)>NAME_CAPACITY:raise ValueError('Dungeon display exceeds fixed field: '+key)
        for occurrence in row['occurrences']:
            changes[occurrence['archive']]=(key,row['ja'],value,encoded)
    files,audit={},[]
    paths=sorted((source/'USRDIR/data/obj/Scenes').glob('dun[0-9][0-9].edat'))
    if [p.name for p in paths]!=['dun%02d.edat'%i for i in range(14)]:raise ValueError('Dungeon source set changed')
    for path in paths:
        before=decrypt_scene(path.read_bytes(),executable,path.name)
        members,details=inspect_scene(before,path.name)
        original=list(members)
        key=value=None
        if path.name in changes:
            key,expected,value,encoded=changes[path.name]
            if details['name']!=expected:raise ValueError('Dungeon source name changed')
            members[0]=encoded+b'\0'*(NAME_CAPACITY-len(encoded))+members[0][NAME_CAPACITY:]
        if members[0][NAME_CAPACITY:]!=original[0][NAME_CAPACITY:] or members[1:]!=original[1:]:
            raise ValueError('Non-text dungeon content changed')
        output=pack(members)
        inspect_scene(output,path.name)
        target='USRDIR/data/obj/Scenes/'+path.with_suffix('.enc').name
        files[target]=output
        audit.append(dict(file=target,source_file=path.relative_to(source).as_posix(),id=key,display=value,
                          source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                          original_authenticated=True,nontext_members_unchanged=True,
                          name_capacity=NAME_CAPACITY,floors=details['floor_count']))
    return files,audit


def redirect_loader(original,result):
    if original[PATH_OFFSET:PATH_OFFSET+len(OLD_PATH)]!=OLD_PATH:
        raise ValueError('Dungeon loader pathname mismatch')
    result[PATH_OFFSET:PATH_OFFSET+len(OLD_PATH)]=NEW_PATH+b'\0'*(len(OLD_PATH)-len(NEW_PATH))
