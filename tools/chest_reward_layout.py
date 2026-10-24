"""Resolve acquired item names before the native multiline/color message queue."""
from runtime_text import CODE_BASE,CODE_LIMIT,branch,dform,instruction,load_address

SITES = ((0x1fe78,0xde680),(0x11e378,0xde4c8))
GUARDS = (
    (0x1fe4c,'7c7c1b787fa3eb784802c975600000007c7d1b787fe3fb7848038c05600000007ba40020786500207b830020480be80960000000'),
    (0x11e34c,'7c7c1b787fa3eb784bf2e475600000007c7d1b787fc3f3784bf3a705600000007ba40020786500207b8300204bfc015160000000'),
    (0x1fdc4,'3b7b0001480be06d600000007f9ad800'), # original acceptance/continuation
    (0xde680,'f821ff817c0802a6f88100b8f8010090380100b8f8a100c0f8c100c87c651b787c06037838600000388000e2'),
    (0xde4c8,'f821ff817c0802a6f88100b8f8010090380100b8f8a100c0f8c100c87c651b787c06037838600000388000f0'),
)
FRAME=0x3400
BUFFER=0x300
CAPACITY=0x3000


def bridge(address,resolver,table,count,aliases,alias_count,target):
    words=[]
    def put(*w):words.extend(w)
    def call(destination):
        put(branch(address+len(words)*4,destination,True),dform(58,2,1,0x180))
    def restore_state():
        put(*(dform(50,r,1,0x200+8*(r-1)) for r in range(1,14)))
        put(dform(58,0,1,0x178),0x7c0ff120,dform(58,0,1,0x188),0x7c0903a6)
    # All saves are beyond native ELFv1 variadic home slots through +0xe8.
    put(dform(62,1,1,-FRAME)|1,0x7c0802a6,dform(62,0,1,0x170),
        0x7c000026,dform(62,0,1,0x178),dform(62,2,1,0x180),
        0x7c0902a6,dform(62,0,1,0x188))
    put(*(dform(62,r,1,0x100+8*(r-3)) for r in range(3,13)))
    put(*(dform(54,r,1,0x200+8*(r-1)) for r in range(1,14)))
    put(dform(58,3,1,0x110),dform(14,4,1,BUFFER),dform(14,5,0,CAPACITY))
    put(*load_address(6,table),dform(14,7,0,count),*load_address(8,aliases),
        dform(14,9,0,alias_count))
    call(resolver)
    put(dform(62,3,1,0x190))
    restore_state()
    put(*(dform(58,r,1,0x100+8*(r-3)) for r in range(3,13)))
    put(dform(58,5,1,0x190))
    call(target)
    put(dform(62,3,1,0x198))
    restore_state()
    put(*(dform(58,r,1,0x100+8*(r-3)) for r in range(4,13)))
    put(dform(58,0,1,0x170),0x7c0803a6,dform(58,3,1,0x198),
        dform(14,1,1,FRAME),0x4e800020)
    return b''.join(instruction(w) for w in words)


def append_code(original,code,resolver,table,count,aliases,alias_count):
    for a,h in GUARDS:
        expected=bytes.fromhex(h)
        if original[a-0x10000:a-0x10000+len(expected)]!=expected:
            raise ValueError('Chest reward context mismatch at '+hex(a))
    addition=bytearray(b'\0'*(-len(code)%16));patches=[];rows=[]
    for site,target in SITES:
        entry=CODE_BASE+len(code)+len(addition)
        addition.extend(bridge(entry,resolver,table,count,aliases,alias_count,target))
        addition.extend(b'\0'*(-len(addition)%16))
        patches.append((site-0x10000,instruction(branch(site,entry,True))))
        rows.append(dict(site=hex(site),target=hex(target),entry=hex(entry)))
    if CODE_BASE+len(code)+len(addition)>CODE_LIMIT:
        raise ValueError('Chest reward exceeds runtime code gap')
    offset=CODE_BASE+len(code)-0x10000
    if any(original[offset:offset+len(addition)]):
        raise ValueError('Chest reward destination is not zero-filled')
    code.extend(addition)
    return patches,dict(calls=rows,resolver=hex(resolver),table=hex(table),count=count,
        aliases=hex(aliases),alias_count=alias_count,frame_bytes=FRAME,
        buffer_offset=BUFFER,capacity=CAPACITY,item_argument_register=5,
        expands_before_native_message_formatting=True,shared_mutable_storage=False,
        original_actor_format_color_icon_wait_preserved=True,
        updated_ingame_verification=False)
