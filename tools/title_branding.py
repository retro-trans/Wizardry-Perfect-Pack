"""Add a native, title-screen-only translation footer. CLI is a dry run.

The title callback at 0xe5c18 draws PRESS START and the copyright, then restores
its native font mode. Hook only that common tail, before mode restoration.
Use its existing font object and direct measurement/draw ABI; no atlas pixels,
font overrides, copyright text, menu callbacks or source files are modified.
"""
import argparse
import json
from pathlib import Path
import re

from runtime_text import CODE_BASE, CODE_LIMIT, branch, dform, instruction, load_address

ROOT = Path(__file__).resolve().parents[1]
SITE = 0xe5d80
CONTINUE = SITE + 4
MEASURE = 0x164adc
DRAW = 0x1654a0
FRAME = 0x200
RIGHT = 1256
LINES = ((646, 18), (670, 20))
FOREGROUND = 0xffdddddd
SHADOW = 0xb0000000
GUARDS = (
    (0xe5c18, 'f821fe517c0802a6fbe1019083e2a938f80101c0dba10198'),
    (0xe5c6c, '8342a9c03b010098807a0000388000003b7f00394807e069'),
    (0xe61c4, '8122a9d4'),  # PRESS START title branch
    (0x482f04, '00407910'),
    (0x407910, '505245535320535441525420425554544f4e00'),
    # Copyright uses direct title font, x316/y580, 18x18, then mode1.
    (0xe5d54, '38e0ffff807a000080c2a9f478e700203880013c38a002443900001239200012394000004807f72960000000807a0000388000014807df6160000000'),
    (0xe5d90, 'e80101c0eaa10140eac101487c0803a6eae10150eb010158eb210160eb410168eb610170eb810178eba10180ebc10188ebe10190cba10198cbc101a0cbe101a8382101b04e800020'),
    (MEASURE, 'f821fe017c0802a6fb4101b8f8010210'),
    (DRAW, 'f821fdd17c0802a6fac101b0f8010240'),
)


def texts(version='0.1.10', project='github.com/retro-trans'):
    if not isinstance(version, str) or not re.fullmatch(r'0\.\d+\.\d+', version):
        raise ValueError('Footer version must use 0.x.y format')
    if (not isinstance(project, str) or not project or len(project) > 64
            or any(ord(c) < 33 or ord(c) > 126 or c == '%' for c in project)):
        raise ValueError('Footer project must be a short, plain ASCII label')
    return ('v'+version, project)


def _bridge(address, string_addresses):
    """Save caller state, draw two measured lines and replay displaced lwz."""
    words = []
    def put(*values): words.extend(values)
    def call(target):
        put(branch(address+len(words)*4, target, True), dform(58, 2, 1, 0xa8))
    put(dform(62, 1, 1, -FRAME) | 1, dform(62, 0, 1, 0x80),
        0x7c0802a6, dform(62, 0, 1, 0x88),
        0x7c000026, dform(62, 0, 1, 0x90),
        0x7c0902a6, dform(62, 0, 1, 0x98),
        0x7c0102a6, dform(62, 0, 1, 0xa0), dform(62, 2, 1, 0xa8))
    put(*(dform(62, r, 1, 0xb0+8*(r-3)) for r in range(3, 13)))
    put(*(dform(54, r, 1, 0x100+8*r) for r in range(14)))
    put(0xfc00048e, dform(54, 0, 1, 0x170))  # mffs f0; save FPSCR
    for string_address, (y, size) in zip(string_addresses, LINES):
        put(dform(32, 3, 26, 0), *load_address(4, string_address),
            dform(14, 5, 0, size), dform(14, 6, 0, size))
        call(MEASURE)
        put(dform(8, 4, 3, RIGHT), dform(62, 4, 1, 0x178))
        for shadow in (True, False):
            put(dform(32, 3, 26, 0), dform(58, 4, 1, 0x178))
            if shadow: put(dform(14, 4, 4, 1))
            put(dform(14, 5, 0, y+int(shadow)), *load_address(6, string_address),
                *load_address(7, SHADOW if shadow else FOREGROUND), 0x78e70020,
                dform(14, 8, 0, size), dform(14, 9, 0, size), dform(14, 10, 0, 0))
            call(DRAW)
    put(dform(50, 0, 1, 0x170), 0xfdfe058e)  # restore entire FPSCR
    put(*(dform(50, r, 1, 0x100+8*r) for r in range(14)))
    put(dform(58, 0, 1, 0x90), 0x7c0ff120,
        dform(58, 0, 1, 0x98), 0x7c0903a6,
        dform(58, 0, 1, 0xa0), 0x7c0103a6,
        dform(58, 0, 1, 0x88), 0x7c0803a6, dform(58, 2, 1, 0xa8))
    put(*(dform(58, r, 1, 0xb0+8*(r-3)) for r in range(3, 13)))
    put(dform(58, 0, 1, 0x80), dform(14, 1, 1, FRAME),
        dform(32, 3, 26, 0))  # original instruction at SITE
    put(branch(address+len(words)*4, CONTINUE))
    return b''.join(instruction(word) for word in words)


def layout_audit(version='0.1.10', project='github.com/retro-trans'):
    """Font-metric reconstruction; runtime aligns using native measurement."""
    from fontTools.ttLib import TTFont
    from check_vwf import cache_width, pen_positions
    font = TTFont(ROOT/'work/source/NPJB00162/USRDIR/FOT-UtrilloPro-DB.otf')
    widths = {chr(c): cache_width(font['hmtx'][g][0], font['head'].unitsPerEm)
              for c, g in font.getBestCmap().items()}
    result = []
    for text, (y, size) in zip(texts(version, project), LINES):
        width = int(pen_positions(text, size, widths)[1])
        if width > RIGHT-24:
            raise ValueError('Footer label exceeds title screen width')
        result.append(dict(text=text, font_size=size, modeled_width=width,
                           modeled_bounds=[RIGHT-width, y, width, size],
                           right_margin=1280-RIGHT, bottom_margin=720-y-size,
                           shadow_offset=[1, 1]))
    return result


def append_code(original, code, version='0.1.10', project='github.com/retro-trans'):
    """Append code plus immutable labels; return guarded file patches/audit.

    Input must be the untouched source executable, with the shared runtime code
    bytearray to which other render bridges have already been appended. This
    function never writes a file or changes the source bytes.
    """
    labels = texts(version, project)
    measured = layout_audit(version, project)
    if not isinstance(code, bytearray):
        raise TypeError('Runtime code must be a mutable bytearray')
    for address, expected in GUARDS:
        expected = bytes.fromhex(expected)
        if original[address-0x10000:address-0x10000+len(expected)] != expected:
            raise ValueError('Title callback context mismatch at %#x' % address)
    padding = -len(code) % 16
    address = CODE_BASE+len(code)+padding
    skeleton = _bridge(address, (0, 0))
    pool_offset = (len(skeleton)+15)//16*16
    encoded = [text.encode('ascii')+b'\0' for text in labels]
    string_addresses = (address+pool_offset, address+pool_offset+len(encoded[0]))
    addition = bytearray(b'\0'*padding+_bridge(address, string_addresses))
    addition.extend(b'\0'*(padding+pool_offset-len(addition)))
    addition.extend(b''.join(encoded))
    addition.extend(b'\0'*(-(len(code)+len(addition)) % 16))
    if CODE_BASE+len(code)+len(addition) > CODE_LIMIT:
        raise ValueError('Title footer exceeds inspected runtime code gap')
    offset = CODE_BASE+len(code)-0x10000
    if len(original[offset:offset+len(addition)]) != len(addition) or any(original[offset:offset+len(addition)]):
        raise ValueError('Title footer destination is not an existing zero-filled gap')
    code.extend(addition)
    return [(SITE-0x10000, instruction(branch(SITE, address)))], dict(
        callback='0xe5c18', site=hex(SITE), continuation=hex(CONTINUE),
        bridge=hex(address), bridge_bytes=len(skeleton), code_bytes=len(addition),
        string_addresses=[hex(value) for value in string_addresses], labels=measured,
        title_only=True, native_measure=hex(MEASURE), native_draw=hex(DRAW),
        frame_bytes=FRAME, right_edge=RIGHT, preserves_copyright=True,
        no_texture_atlas_changes=True, no_global_font_override_changes=True,
        preserves_gpr_0_2_through_12=True, preserves_fpr_0_through_13=True,
        preserves_lr_cr_ctr_xer_fpscr=True, replays_displaced_instruction=True,
        guarded_addresses=[hex(address) for address, _ in GUARDS],
        validation='Static trace and instruction tests; in-game visual verification pending.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='0.1.10')
    parser.add_argument('--project', default='github.com/retro-trans')
    args = parser.parse_args()
    original = (ROOT/'work/source/NPJB00162/USRDIR/EBOOT.elf').read_bytes()
    code = bytearray()
    _, audit = append_code(original, code, args.version, args.project)
    print(json.dumps(audit, indent=2))
    print('Dry run: footer generated in memory; no files written.')


if __name__ == '__main__':
    main()
