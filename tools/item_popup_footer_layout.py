"""Compact race columns and bounded notes in the equipment-detail popup."""
from runtime_text import CODE_BASE,CODE_LIMIT,branch,instruction,dform
from inventory_layout import _bridge

NOTE_SITE=0x60874
NOTE_WIDTH=416
CHANGES=(
    (0x5fedc,0x3be00090,0x3be00088), # first race row center136
    (0x6001c,0x3bff0080,0x3bff0060), # row0 column stride96
    (0x6003c,0x3b600090,0x3b600088), # second race row center136
    (0x600fc,0x3b7b0080,0x3b7b0060), # row1 column stride96
    (0x60834,0x38600018,0x38600014), # notes20x20; other fonts keep their resets
    (0x60838,0x38800018,0x38800014),
)
GUARDS=(
    (0x60028,'2f9b00023b7b0001409eff34'),
    (0x60108,'57e0063e2f800007409eff34'),
    (0x60818,'419e01207f83e378e881017838a0000038c0000038e001b84bffb821'),
    (0x60938,'7f83e378e881017838a0000138c0000038e001b84bffb7054bfffee4'),
    (0x60844,'8131000080700000392901f0386301b45529053e5463622665290a003c8000647c634b786084008038a100707863002048070d39'),
)


def multiline_measure(address):
    """Same measure ABI; return max(line widths), including an empty last line.

    The popup owns a bounded 256-byte formatted note. The private line buffer
    has 4096 bytes; no source or shared native buffers are modified.
    """
    w=[];labels={};pending=[]
    def put(*v):w.extend(v)
    def mark(name):labels[name]=len(w)
    def jump(name,condition=None):pending.append((len(w),name,condition));put(0)
    def mr(dst,src):return (31<<26)|(src<<21)|(dst<<16)|(src<<11)|(444<<1)
    put(dform(62,1,1,-0x1400)|1,0x7c0802a6,dform(62,0,1,0xd0),
        0x7c000026,dform(62,0,1,0xd8),dform(62,2,1,0xe0),
        0x7c0902a6,dform(62,0,1,0xe8))
    put(*(dform(62,r,1,0x80+8*(r-3)) for r in range(3,13)))
    put(*(dform(62,r,1,0x100+8*(r-14)) for r in range(14,22)))
    put(mr(14,4),dform(14,15,1,0x300),mr(16,15),mr(17,3),mr(18,5),mr(19,6),dform(14,20,0,0))
    mark('scan')
    put(dform(34,21,14,0),dform(14,14,14,1),0x2f950000)
    jump('line',0x419e0000)
    put(0x2f95000a);jump('line',0x419e0000)
    put(dform(38,21,16,0),dform(14,16,16,1));jump('scan')
    mark('line')
    put(dform(14,9,0,0),dform(38,9,16,0),mr(3,17),mr(4,15),mr(5,18),mr(6,19))
    put(branch(address+len(w)*4,0x164adc,True),dform(58,2,1,0xe0),0x7f83a040)
    jump('max',0x409d0000);put(mr(20,3))
    mark('max')
    put(0x2f950000);jump('done',0x419e0000)
    put(mr(16,15));jump('scan')
    mark('done')
    put(mr(3,20))
    put(*(dform(58,r,1,0x100+8*(r-14)) for r in range(14,22)))
    put(*(dform(58,r,1,0x80+8*(r-3)) for r in range(4,13)))
    put(dform(58,0,1,0xd8),0x7c0ff120,dform(58,0,1,0xe8),0x7c0903a6,
        dform(58,0,1,0xd0),0x7c0803a6,dform(58,2,1,0xe0),dform(14,1,1,0x1400),0x4e800020)
    for index,name,condition in pending:
        delta=(labels[name]-index)*4
        w[index]=branch(address+index*4,address+labels[name]*4) if condition is None else condition|(delta&0xfffc)
    return b''.join(instruction(v) for v in w)


def append_code(original,code):
    for a,h in GUARDS:
        expected=bytes.fromhex(h)
        if original[a-0x10000:a-0x10000+len(expected)]!=expected:
            raise ValueError('Popup footer context mismatch at '+hex(a))
    for a,before,after in CHANGES:
        if original[a-0x10000:a-0x10000+4]!=instruction(before):
            raise ValueError('Popup footer instruction mismatch at '+hex(a))
    padding=-len(code)%16;measure=CODE_BASE+len(code)+padding
    addition=bytearray(b'\0'*padding+multiline_measure(measure))
    addition.extend(b'\0'*(-len(addition)%16))
    entry=CODE_BASE+len(code)+len(addition)
    addition.extend(_bridge(entry,fixed_cap=NOTE_WIDTH,measure_target=measure))
    addition.extend(b'\0'*(-len(addition)%16))
    if CODE_BASE+len(code)+len(addition)>CODE_LIMIT:raise ValueError('Popup footer exceeds code gap')
    offset=CODE_BASE+len(code)-0x10000
    if any(original[offset:offset+len(addition)]):raise ValueError('Popup footer gap is not zero-filled')
    code.extend(addition)
    changes=[(a-0x10000,instruction(after)) for a,before,after in CHANGES]
    changes.append((NOTE_SITE-0x10000,instruction(branch(NOTE_SITE,entry,True))))
    return changes,dict(note_site=hex(NOTE_SITE),note_bridge=hex(entry),multiline_measure=hex(measure),
        note_width=NOTE_WIDTH,note_font=[20,20],race_first_center=136,
        race_column_stride=96,race_cell_width=80,race_font=[22,22],
        race_row_counts=[3,4],native_race_order_and_permissions_preserved=True,
        bonus_flags_colors_and_values_preserved=True,updated_ingame_verification=False)
