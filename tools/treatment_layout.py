"""Fixed headings and bounded cells for the treatment/recovery roster."""
from runtime_text import CODE_BASE,CODE_LIMIT,branch,dform,instruction,load_address
from inventory_layout import _bridge as draw_bridge
from item_cell_layout import _bridge as measure_bridge

HEADER_SITE=0xf3c10
DRAW_CELLS=((0xf3de8,116),(0xf3f44,96),(0xf4000,96))
MEASURE_CELLS=((0xf3d40,32),(0xf3c68,72))
WIDTH_SLOT=0xa8 # unused final local word; saved nonvolatile GPRs begin at+0xb0
HEADERS=((12,'Lv'),(52,'Name'),(184,'Align.'),(248,'Cls'),(288,'Race'),
         (400,'Sex'),(440,'Status'),(591,'Fee'))
CHANGES=(
    (0xf3d6c,0x39290045,0x39290028), # level: right edge40
    (0xf3db0,0x39290045,0x39290034), # name: left52
    (0xf3e48,0x392900e8,0x392900d2), # alignment: center210, clear class icon248
    (0xf3f64,0x39290198,0x39290190), # sex: left400
    (0xf3fd8,0x392901cc,0x392901b8), # status: left440
    (0xf3d50,0x38600018,dform(32,3,1,WIDTH_SLOT)), # fitted level size
    (0xf3c78,0x38600018,dform(32,3,1,WIDTH_SLOT)), # fitted fee size
)
GUARDS=(
    (0xf3b08,'7d800026f821fed1'), # frame304 and CR save; locals end before GPR16
    (0xf3b60,'83e3010c8103011882230110'),
    (0xf3bd8,'82c2acb082e2acac3c80006480a2acb48136000060840080807700003929000c3863000c5529053e5463622665290a007c634b78786300204bfdd99d'),
    (0xf40b4,'38800018386000184bfdc6d96000000082c2acb082e2acac3c80006480a2acb84bfffb14'),
    (0xf3c58,'38a00018807800007fc4f37838c0001848070e7560000000388000187c7d1b78386000184bfdcb19'),
    (0xf3d30,'8070000038c0001838a000187fc4f37848070d9d60000000388000187c7d1b78386000184bfdca41'),
    (0xf3dcc,'4bf589fd600000003c8000647bbd002078650020608400807fa3eb784bfdd7c5'),
    (0xf3f00,'392901207fbcea145529053e57bd622665290a007fe3fb787fbd4b784bf5891960000000786306207bbd00204bf5dcb1600000003c80006478650020608400807fa3eb784bfdd669'),
    (0xf3f5c,'8136000083b70000392901987fbcea145529053e57bd622665290a007fe3fb787fbd4b784bf5895d60000000786306207bbd00204bf5dda5600000003c80006478650020608400807fa3eb784bfdd605'),
    (0xf3fd0,'8136000080770000392901cc7c7c1a145529053e5463622665290a003c8000647c634b7860840080786300207fc5f3784bfdd5ad'),
    (0xf3c84,'81360000807700007d3d48507c7c1a1439290270'), # fee stays right624
    (0xf3ecc,'388000f8'), # class icon remains at248
)


def header_image(address):
    """Packed draw ABI, eight labels, font/state/volatile/varargs preserved."""
    w=[];strings=[];relocations=[]
    def put(*v):w.extend(v)
    def call(target):put(branch(address+len(w)*4,target,True),dform(58,2,1,0xe0))
    def state():
        put(*(dform(50,r,1,0x130+8*(r-1)) for r in range(1,14)))
        put(dform(58,0,1,0xd8),0x7c0ff120,dform(58,0,1,0xe8),0x7c0903a6)
    put(dform(62,1,1,-0x1c0)|1,0x7c0802a6,dform(62,0,1,0xd0),
        0x7c000026,dform(62,0,1,0xd8),dform(62,2,1,0xe0),
        0x7c0902a6,dform(62,0,1,0xe8))
    put(*(dform(62,r,1,0x80+8*(r-3)) for r in range(3,13)))
    put(*(dform(54,r,1,0x130+8*(r-1)) for r in range(1,14)))
    put(dform(32,12,2,-0x59f4),dform(15,12,12,3),dform(62,12,1,0x100),
        dform(32,11,12,-0x7c04),dform(62,11,1,0xf0),
        dform(32,11,12,-0x7c00),dform(62,11,1,0xf8))
    for x,label in HEADERS:
        put(dform(14,3,0,20),dform(14,4,0,24));call(0xd0794)
        state()
        put(*(dform(58,r,1,0x80+8*(r-3)) for r in range(3,13)))
        put(dform(14,3,3,x-12))
        relocations.append(len(w));strings.append(label.encode('ascii')+b'\0');put(0,0)
        call(0xd15ac)
    put(dform(62,3,1,0x108),dform(58,12,1,0x100),
        dform(58,11,1,0xf0),dform(36,11,12,-0x7c04),
        dform(58,11,1,0xf8),dform(36,11,12,-0x7c00))
    state()
    put(*(dform(58,r,1,0x80+8*(r-3)) for r in range(4,13)))
    put(dform(58,0,1,0xd0),0x7c0803a6,dform(58,3,1,0x108),
        dform(14,1,1,0x1c0),0x4e800020)
    text=bytearray();base=address+len(w)*4
    for index,label in zip(relocations,strings):
        w[index:index+2]=load_address(5,base+len(text));text.extend(label)
    return b''.join(instruction(v) for v in w)+text


def append_code(original,code):
    for a,h in GUARDS:
        expected=bytes.fromhex(h)
        if original[a-0x10000:a-0x10000+len(expected)]!=expected:
            raise ValueError('Treatment roster context mismatch at '+hex(a))
    for a,before,after in CHANGES:
        if original[a-0x10000:a-0x10000+4]!=instruction(before):
            raise ValueError('Treatment coordinate mismatch at '+hex(a))
    additions=bytearray(b'\0'*(-len(code)%16));rows=[];patches=[]
    def install(site,payload,kind,cap=None):
        entry=CODE_BASE+len(code)+len(additions)
        additions.extend(payload(entry));additions.extend(b'\0'*(-len(additions)%16))
        patches.append((site-0x10000,instruction(branch(site,entry,True))))
        rows.append(dict(site=hex(site),entry=hex(entry),kind=kind,cap=cap))
    install(HEADER_SITE,header_image,'header')
    for site,cap in DRAW_CELLS:
        install(site,lambda a:draw_bridge(a,fixed_cap=cap),'draw',cap)
    for site,cap in MEASURE_CELLS:
        install(site,lambda a:measure_bridge(a,cap,WIDTH_SLOT),'measure',cap)
    if CODE_BASE+len(code)+len(additions)>CODE_LIMIT:raise ValueError('Treatment code gap exhausted')
    off=CODE_BASE+len(code)-0x10000
    if any(original[off:off+len(additions)]):raise ValueError('Treatment code destination is not zero-filled')
    code.extend(additions)
    patches.extend((a-0x10000,instruction(after)) for a,before,after in CHANGES)
    return patches,dict(bridges=rows,headers=[dict(x=x,text=s) for x,s in HEADERS],
        header_font=[20,24],row_height=24,panel_width=640,fee_right=624,
        fee_width=72,status_left=440,status_width=96,fee_gap=16,
        includes_recovery_roster=True,fee_calculation_and_selection_unchanged=True,
        updated_ingame_verification=False)
