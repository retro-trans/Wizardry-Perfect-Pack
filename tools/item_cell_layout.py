"""Guarded, popup-only native font fitting for item-detail grid cells.

The bridge uses the already hooked 0x164adc measurement entry, so tokens and
late aliases are expanded before sizing. Each cell retains its original text,
center, selected color and flags. The caller's unused sp+0x188 padding stores
the fitted horizontal font size until its existing font-setting call.

Run this module to inspect the proposed patches; it never writes an ELF.
"""
from pathlib import Path
import argparse
import json

from runtime_text import CODE_BASE, CODE_LIMIT, branch, dform, instruction


MEASURE = 0x164adc
FONT_SETTER = 0xd0794
POPUP_ENTRY = 0x5eadc
CALLER_WIDTH_SLOT = 0x188
FONT_SIZE = 22
BRIDGE_FRAME = 0x120

# name, measure BL/expected bytes, width/height arguments to measurement,
# width/height arguments to the later font setter, font-set BL, draw BL, cap.
CELLS = (
    ('class_row_0', 0x5f878, '48105265', 0x5f868, 0x5f86c,
     0x5f890, 0x5f898, 0x5f8ac, 0x5f900, 72),
    ('class_row_1', 0x5f954, '48105189', 0x5f944, 0x5f948,
     0x5f96c, 0x5f974, 0x5f988, 0x5f9dc, 72),
    ('class_row_2', 0x5fa40, '4810509d', 0x5fa34, 0x5fa38,
     0x5fa68, 0x5fa6c, 0x5fa70, 0x5fab8, 72),
    ('effect_row_0', 0x6021c, '481048c1', 0x6020c, 0x60210,
     0x60248, 0x60240, 0x6025c, 0x602a4, 104),
    ('effect_row_1', 0x60300, '481047dd', 0x602f4, 0x602f8,
     0x60330, 0x60334, 0x6033c, 0x60384, 104),
    ('monster_affinity', 0x60518, '481045c5', 0x60508, 0x6050c,
     0x60528, 0x60520, 0x60534, 0x605a0, 104),
    ('status_affinity', 0x60774, '48104369', 0x60764, 0x60768,
     0x60784, 0x6077c, 0x60790, 0x607fc, 104),
)


def _xform(xo, rt, ra, rb):
    return (31 << 26) | (rt << 21) | (ra << 16) | (rb << 11) | (xo << 1)


def _bridge(address, cap):
    """Return an ABI-compatible wrapper that calls native measurement.

    Input: r3 font, r4 text, r5 maximum horizontal size, r6 height.
    Output: r3 actual measured pixel width; caller sp+0x188 fitted size.
    Preserve r2, r4..r12, CR, LR and all nonvolatile registers. The normal
    measurement function owns its usual volatile floating-point clobbers.
    """
    words, labels, pending = [], {}, []

    def put(*values):
        words.extend(values)

    def mark(name):
        labels[name] = len(words)

    def jump(name, conditional=None):
        pending.append((len(words), name, conditional))
        put(0)

    def call_native():
        # Reload original inputs for every measurement, except fitted width.
        put(dform(58, 3, 1, 0x80), dform(58, 4, 1, 0x88),
            dform(58, 5, 1, 0xf0), dform(58, 6, 1, 0x98))
        put(branch(address + len(words) * 4, MEASURE, True),
            dform(58, 2, 1, 0xe0))

    put(dform(62, 1, 1, -BRIDGE_FRAME) | 1,  # stdu r1,-frame(r1)
        0x7c0802a6, dform(62, 0, 1, 0xd0),  # LR beyond callee linkage area
        0x7c000026, dform(62, 0, 1, 0xd8),  # complete CR
        dform(62, 2, 1, 0xe0))
    put(*(dform(62, r, 1, 0x80 + 8 * (r - 3)) for r in range(3, 13)))
    put(dform(62, 5, 1, 0xf0))
    call_native()
    put(0x2f830000)  # cmpwi cr7,r3,0: a failed/empty measure needs no divide.
    jump('done', 0x409d0000)  # ble cr7
    put(0x2b830000 | cap)  # cmplwi cr7,r3,cap
    jump('done', 0x409d0000)
    put(dform(58, 8, 1, 0x90), dform(14, 9, 0, cap),
        _xform(235, 8, 8, 9),  # mullw r8,r8,r9
        _xform(459, 8, 8, 3),  # divwu r8,r8,r3
        0x2f880001)  # cmpwi cr7,r8,1
    jump('store_size', 0x409c0000)  # bge cr7
    put(dform(14, 8, 0, 1))
    mark('store_size')
    put(dform(62, 8, 1, 0xf0))
    mark('remeasure')
    call_native()
    put(0x2b830000 | cap)
    jump('done', 0x409d0000)
    # Font hinting/rounding can defeat a single ratio. Check the actual native
    # width and decrement until it fits, with one as the terminating minimum.
    put(dform(58, 8, 1, 0xf0), 0x2f880001)
    jump('done', 0x409d0000)
    put(dform(14, 8, 8, -1), dform(62, 8, 1, 0xf0))
    jump('remeasure')
    mark('done')
    put(dform(58, 12, 1, 0), dform(58, 11, 1, 0xf0),
        dform(36, 11, 12, CALLER_WIDTH_SLOT))
    put(dform(58, 0, 1, 0xd8), 0x7c0ff120,  # mtcrf 255,r0
        dform(58, 0, 1, 0xd0), 0x7c0803a6,
        dform(58, 2, 1, 0xe0))
    put(*(dform(58, r, 1, 0x80 + 8 * (r - 3)) for r in range(4, 13)))
    put(dform(14, 1, 1, BRIDGE_FRAME), 0x4e800020)
    for index, name, conditional in pending:
        origin = address + index * 4
        target = address + labels[name] * 4
        delta = target - origin
        if conditional is None:
            words[index] = branch(origin, target)
        else:
            if delta % 4 or not -0x8000 <= delta < 0x8000:
                raise ValueError('Item cell conditional branch out of range')
            words[index] = conditional | (delta & 0xfffc)
    return b''.join(instruction(word) for word in words)


def append_code(original, code):
    """Append bridges to the shared runtime bytearray; return patches, audit.

    The caller must add the returned (ELF file offset, bytes) patches and keep
    its normal code-gap/segment validation. All guards run before mutation.
    """
    if not isinstance(code, bytearray):
        raise TypeError('Runtime code must be a mutable bytearray')
    patches, checks, cell_audit = [], [], []

    def guard(address, expected):
        expected = bytes.fromhex(expected) if isinstance(expected, str) else expected
        actual = original[address - 0x10000:address - 0x10000 + len(expected)]
        if actual != expected:
            raise ValueError(f'Item popup instruction mismatch at {address:#x}: '
                             f'expected {expected.hex()}, got {actual.hex()}')
        checks.append(dict(address=hex(address), expected=expected.hex()))

    # Confirm this is the inspected frame, its text-buffer pointer and saved
    # register boundary surrounding the otherwise unused eight-byte padding.
    guard(0x5eae0, 'f821fde1')
    guard(0x5eae4, 'f9c10190')
    guard(0x5eb4c, 'f8010180')
    for name, measure, expected, mw, mh, sw, sh, setter, draw, cap in CELLS:
        guard(measure, expected)
        guard(mw, '38a0001a')
        guard(mh, '38c0001a')
        guard(sw, '3860001a')
        guard(sh, '3880001a')
        guard(setter, instruction(branch(setter, FONT_SETTER, True)))
        guard(draw, instruction(branch(draw, 0xd15ac, True)))

    addition = bytearray(b'\0' * (-len(code) % 16))
    bridges = {}
    for cap in sorted({cell[-1] for cell in CELLS}):
        address = CODE_BASE + len(code) + len(addition)
        bridges[cap] = address
        addition.extend(_bridge(address, cap))
        addition.extend(b'\0' * (-(len(code) + len(addition)) % 16))
    if CODE_BASE + len(code) + len(addition) > CODE_LIMIT:
        raise ValueError('Item popup fitting exceeds the inspected code gap')
    start = CODE_BASE + len(code) - 0x10000
    if any(original[start:start + len(addition)]):
        raise ValueError('Item popup code destination is not zero-filled')

    for name, measure, expected, mw, mh, sw, sh, setter, draw, cap in CELLS:
        patches.extend((
            (measure - 0x10000, instruction(branch(measure, bridges[cap], True))),
            (mw - 0x10000, instruction(dform(14, 5, 0, FONT_SIZE))),
            (mh - 0x10000, instruction(dform(14, 6, 0, FONT_SIZE))),
            (sw - 0x10000, instruction(dform(32, 3, 1, CALLER_WIDTH_SLOT))),
            (sh - 0x10000, instruction(dform(14, 4, 0, FONT_SIZE))),
        ))
        cell_audit.append(dict(name=name, measure_call=hex(measure),
                               setter_call=hex(setter), draw_call=hex(draw),
                               bridge=hex(bridges[cap]), maximum_width=cap))
    code.extend(addition)
    return patches, dict(
        popup_entry=hex(POPUP_ENTRY), code_bytes=len(addition),
        bridge_frame_bytes=BRIDGE_FRAME, caller_width_slot=hex(CALLER_WIDTH_SLOT),
        maximum_horizontal_size=FONT_SIZE, vertical_size=FONT_SIZE,
        uses_native_measurement=True, resolves_full_english=True,
        preserves_cell_centers=True, preserves_selected_colors=True,
        preserves_row_column_spacing=True, shared_mutable_storage=False,
        minimum_horizontal_size=1,
        minimum_size_overflow='Returns actual native width; never loops forever',
        cells=cell_audit, guarded_instructions=checks,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path,
                        default=Path('work/source/NPJB00162/USRDIR/EBOOT.elf'))
    args = parser.parse_args()
    code = bytearray()
    patches, audit = append_code(args.source.read_bytes(), code)
    print(json.dumps(dict(mode='dry-run', patches=[
        dict(offset=hex(offset), replacement=value.hex()) for offset, value in patches
    ], audit=audit), indent=2))


if __name__ == '__main__':
    main()
