"""PPU wrappers for complete database strings; no shared mutable text buffers.

The small resolver and wrappers occupy a verified zero-filled gap between the
first two original load segments. Each call owns a 16KiB stack frame and a
12KiB expansion buffer. Full English lives in an immutable appended segment.
"""
import io
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile

CODE_BASE = 0x448090
CODE_LIMIT = 0x450000
HOOKS = [
    (0x164adc, 4, bytes.fromhex('f821fe017c0802a6fb4101b8f8010210')),
    # Draw receives x/y in r4/r5 and its string in r6. Treating r4 as a
    # pointer crashes when a positioned label is drawn (e.g. New Game).
    (0x164ea4, 6, bytes.fromhex('f821fdd17c0802a6fb4101e8f8010240')),
    (0x1654a0, 6, bytes.fromhex('f821fdd17c0802a6fac101b0f8010240')),
]


def instruction(word):
    return struct.pack('>I', word)


def dform(op, rt, ra, immediate):
    return (op << 26) | (rt << 21) | (ra << 16) | (immediate & 0xffff)


def branch(origin, destination, link=False):
    delta = destination-origin
    if delta%4 or not -0x2000000 <= delta < 0x2000000:
        raise ValueError('PPU branch cannot reach destination')
    return 0x48000000 | (delta & 0x3fffffc) | int(link)


def load_address(register, value):
    if not 0 <= value <= 0xffffffff:
        raise ValueError('Address exceeds PPU game pointer range')
    return [dform(15, register, 0, value >> 16),
            dform(24, register, register, value & 0xffff)]


def resolver_code(path):
    elf = ELFFile(io.BytesIO(Path(path).read_bytes()))
    if elf.header['e_machine'] != 'EM_PPC64' or elf.little_endian:
        raise ValueError('Resolver must be big-endian PPC64')
    text = elf.get_section_by_name('.text')
    data = text.data()
    # LLVM ELFv2 global entry establishes a TOC. This leaf has no TOC data;
    # call its local entry (+8), preserving the game's r2 instead.
    if data[:8] != bytes.fromhex('3c4c000038420000'):
        raise ValueError('Unexpected resolver entry; inspect compiler output')
    rela = elf.get_section_by_name('.rela.text')
    if rela is not None and any(r['r_offset'] >= 8 for r in rela.iter_relocations()):
        raise ValueError('Resolver contains unresolved runtime relocations')
    return data, 8


def make_code(original, resolver, resolver_entry_offset, table_address, count, dialogue=None,
              alias_address=0, alias_count=0,branding_version=None):
    code = bytearray(resolver)
    code.extend(b'\0'*(-len(code)%16))
    patches, details = [], []
    resolver_entry = CODE_BASE+resolver_entry_offset
    for target, text_register, expected in HOOKS:
        if original[target-0x10000:target-0x10000+16] != expected:
            raise ValueError('Renderer prologue mismatch')
        wrapper = CODE_BASE+len(code)
        # Callees save their LR in their caller's linkage area (+16). Keep
        # our own return address beyond that area so the original renderer
        # trampoline cannot overwrite it when its prologue runs.
        words = [0xf821c001, 0x7c0802a6, dform(62,0,1,0x100), dform(62,2,1,208)]
        words += [dform(62,r,1,32+8*(r-3)) for r in range(3,11)]
        words += [dform(54,r,1,96+8*(r-1)) for r in range(1,14)]
        # mr r3, text_register
        words += [(31<<26)|(text_register<<21)|(3<<16)|(text_register<<11)|(444<<1),
                  dform(14,4,1,0x200), dform(14,5,0,0x3000)]
        words += load_address(6,table_address)+[dform(14,7,0,count)]
        words += load_address(8,alias_address)+[dform(14,9,0,alias_count)]
        words += load_address(12,resolver_entry)+[0x7d8903a6,0x4e800421]
        words += [dform(62,3,1,32+8*(text_register-3)),dform(58,2,1,208)]
        words += [dform(50,r,1,96+8*(r-1)) for r in range(1,14)]
        words += [dform(58,r,1,32+8*(r-3)) for r in range(3,11)]
        call_index = len(words)
        words += [0,dform(58,0,1,0x100),0x7c0803a6,dform(14,1,1,0x4000),0x4e800020]
        trampoline = (wrapper+len(words)*4+15)//16*16
        words[call_index] = branch(wrapper+call_index*4,trampoline,True)
        code.extend(b''.join(instruction(w) for w in words))
        code.extend(b'\0'*(-len(code)%16))
        if CODE_BASE+len(code) != trampoline:
            raise ValueError('Trampoline alignment mismatch')
        code.extend(expected)
        code.extend(instruction(branch(trampoline+16,target+16)))
        code.extend(b'\0'*(-len(code)%16))
        patch = instruction(branch(target,wrapper))+instruction(0x60000000)*3
        patches.append((target-0x10000,patch))
        details.append(dict(function=hex(target),text_register=text_register,
                            wrapper=hex(wrapper),trampoline=hex(trampoline)))
    dialogue_audit=None
    battle_audit=None
    narration_audit=None
    if dialogue is not None:
        # This boundary is after event lines and runtime actor names have been
        # assembled, before the ordinary/typewriter paths diverge. A fitting
        # paragraph follows the original conditional branch unchanged.
        site=0xa5e94
        expected=bytes.fromhex('4192012c')
        if original[site-0x10000:site-0x10000+4]!=expected:
            raise ValueError('Dialogue continuation branch mismatch')
        payload,entry=dialogue[:2]
        presenter=CODE_BASE+len(code)
        code.extend(payload);code.extend(b'\0'*(-len(code)%16))
        bridge=CODE_BASE+len(code)
        words=[0xf821fd01,dform(62,0,1,0x1d8),0x7c0802a6,dform(62,0,1,0x1c0),
               0x7c000026,dform(62,0,1,0x1c8),dform(62,2,1,0x1b8),
               0x7c0902a6,dform(62,0,1,0x1e0)]
        words += [dform(62,r,1,0x100+8*(r-3)) for r in range(3,13)]
        words += [dform(54,r,1,0x150+8*(r-1)) for r in range(1,14)]
        def mr(dst,src):return (31<<26)|(src<<21)|(dst<<16)|(src<<11)|(444<<1)
        words += [mr(3,23),mr(4,31),dform(32,5,2,-0x588c),dform(32,5,5,0),
                  dform(58,6,1,0x1c8),dform(32,7,2,-0x6324),dform(15,7,7,3),
                  (31<<26)|(7<<21)|(7<<16)|(23<<11)|(266<<1),dform(34,7,7,0x2278),
                  dform(32,8,2,-0x62b4),dform(40,8,8,12)]
        words += load_address(12,presenter+entry)+[0x7d8903a6,0x4e800421,dform(62,3,1,0x1d0)]
        words += [dform(58,2,1,0x1b8),dform(58,0,1,0x1e0),0x7c0903a6,
                  dform(58,0,1,0x1c0),0x7c0803a6]
        words += [dform(50,r,1,0x150+8*(r-1)) for r in range(1,14)]
        words += [dform(58,r,1,0x100+8*(r-3)) for r in range(3,13)]
        words += [dform(58,0,1,0x1d0),0x2f800000]
        choose=len(words);words += [0]
        restore=[dform(58,0,1,0x1c8),0x7c0ff120,dform(58,0,1,0x1d8),dform(14,1,1,0x300)]
        words += restore
        words += [branch(bridge+len(words)*4,0xa5fd0)]
        passthrough=len(words)
        words += restore
        words += [0x41920008,branch(bridge+(len(words)+1)*4,0xa5e98),
                  branch(bridge+(len(words)+2)*4,0xa5fc0)]
        words[choose]=0x419e0000|((passthrough-choose)*4)
        code.extend(b''.join(instruction(w) for w in words));code.extend(b'\0'*(-len(code)%16))
        patches.append((site-0x10000,instruction(branch(site,bridge))))
        dialogue_audit=dict(site=hex(site),presenter=hex(presenter+entry),bridge=hex(bridge),
            inner_width=800,font_size=32,lines_per_page=3,native_line_bytes=120,
            frame_width=960,portrait_text_inset=128,right_padding=32,
            preserves_event_records=True,preserves_actor_substitutions=True,
            preserves_typewriter=True,uses_native_font_measurement=True,
            native_show='0xde018',native_wait='0xdddc0')
        if len(dialogue)>2:
            from battle_layout import append_code as battle_code
            battle_patches,battle_audit=battle_code(original,code,presenter+dialogue[2],resolver_entry,
                                                   table_address,count,alias_address,alias_count)
            patches.extend(battle_patches)
        if len(dialogue)>3:
            from narration_layout import append_code as narration_code
            narration_patches,narration_audit=narration_code(original,code,presenter+dialogue[3])
            patches.extend(narration_patches)
    from item_cell_layout import append_code as item_cell_code
    item_patches,item_audit=item_cell_code(original,code)
    patches.extend(item_patches)
    from item_preview_layout import patches as item_preview_patches
    preview_patches,preview_audit=item_preview_patches(original)
    patches.extend(preview_patches)
    from menu_panel_layout import patches as panel_patches
    panel_changes,panel_audit=panel_patches(original)
    patches.extend(panel_changes)
    from inventory_layout import append_code as append_inventory_code
    inventory_patches,inventory_audit=append_inventory_code(original,code)
    patches.extend(inventory_patches)
    branding_audit=None
    if branding_version is not None:
        from title_branding import append_code as title_footer
        branding_patches,branding_audit=title_footer(original,code,branding_version)
        patches.extend(branding_patches)
    if CODE_BASE+len(code) > CODE_LIMIT:
        raise ValueError('Runtime code exceeds inspected gap')
    start = CODE_BASE-0x10000
    if any(original[start:start+len(code)]):
        raise ValueError('Code gap is not empty')
    return bytes(code),patches,dict(resolver=hex(resolver_entry),code_bytes=len(code),
                                    stack_frame_bytes=0x4000,expansion_capacity=0x3000,
                                    shared_mutable_buffer=False,hooks=details,dialogue=dialogue_audit,
                                    alias_address=hex(alias_address),alias_count=alias_count,
                                    item_cells=item_audit,item_preview=preview_audit,menu_panels=panel_audit,battle=battle_audit,
                                    inventory_names=inventory_audit,narration=narration_audit,title_branding=branding_audit)
