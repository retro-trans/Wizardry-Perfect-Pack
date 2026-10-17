"""Fit complete inventory names in their existing column, horizontally only.

Only the name draw at 0x26148 is redirected. The bridge measures through the
existing English resolver, retains the native 25x32 maximum font, reserves a
quantity column on stackable rows, and restores the original font dimensions.
The CLI is read-only and can also audit every source item-name field.
"""
import argparse
import json
from pathlib import Path

from runtime_text import CODE_BASE, CODE_LIMIT, branch, dform, instruction


DRAW_SITE = 0x26148
DRAW = 0xd15ac
MEASURE = 0x164adc
FONT_SETTER = 0xd0794
STACKABLE = 0x57f74
FONT_OBJECT_TOC = -0x7c58
UI_STATE_TOC = -0x59f4
NAME_CAP = 288
STACK_CAP = 252
FRAME = 0x1c0

# Every changed/inferred call context is checked against the original ELF.
GUARDS = (
    (0x25ef0, 'f821ff017c0802a6'),
    (0x260fc, '3880002038600019480aa691'),
    (0x26114, '3929001c'),  # name x = window x + 28
    (0x26124, '7d29e3787fe3fb787fbd4b7848032939'),  # selected color/name getter
    (0x26138, '3c80006478650020608400807ba30020480ab465'),
    (0x26150, '7fe3fb7848031e21'),  # same pure stack predicate after the draw
    (0x2618c, '812283a838a0001938c000207e84a37880690000'),
    (0x261a8, '388000207c7d1b7838600019480aa5e1'),
    (0x261cc, '39290140'),  # quantity right edge = window x + 320
    (0x261f0, '480ab3bd'),  # separate quantity draw must remain untouched
    (0x57f74, 'f821ff917c0802a6f80100804bfff7c5786300204bffe9d9'),
    (0x56960, '886300a77863f7e24e800020'),  # read-only stack flag getter
    (0x58014, '2b9e00637fc0f378409dffc4380000634bffffbc'),  # stacks <= 99
    (0xd0794, '8122a60c380000013d29000390898400980983f8906983fc4e800020'),
    (0xd106c, '38000000980983f8'),  # native draw consumes the size override
)


def _xform(xo, rt, ra, rb):
    return (31 << 26) | (rt << 21) | (ra << 16) | (rb << 11) | (xo << 1)


def _mr(destination, source):
    return _xform(444, source, destination, source)


def _bridge(address):
    """Original draw ABI in/out; preserve CR/CTR/LR/GPR4..12/FPR1..13.

    Caller r31 identifies the item, as guarded immediately before/after the
    redirected call. r3 holds packed coordinates/color, r4 formatting flags,
    r5 the complete item-name token/string, r6..r10 any original varargs.
    """
    words, labels, pending = [], {}, []

    def put(*values):
        words.extend(values)

    def label(name):
        labels[name] = len(words)

    def jump(name, conditional=None):
        pending.append((len(words), name, conditional))
        put(0)

    def call(target):
        put(branch(address + len(words) * 4, target, True), dform(58, 2, 1, 0xe0))

    def measure():
        put(dform(32, 3, 2, FONT_OBJECT_TOC), dform(32, 3, 3, 0),
            dform(58, 4, 1, 0x90), dform(58, 5, 1, 0x100), dform(58, 6, 1, 0xf8))
        call(MEASURE)

    def restore_float_condition_counter():
        put(*(dform(50, r, 1, 0x130 + 8 * (r - 1)) for r in range(1, 14)))
        put(dform(58, 0, 1, 0xd8), 0x7c0ff120,
            dform(58, 0, 1, 0x118), 0x7c0903a6)

    put(dform(62, 1, 1, -FRAME) | 1,
        0x7c0802a6, dform(62, 0, 1, 0xd0),
        0x7c000026, dform(62, 0, 1, 0xd8),
        dform(62, 2, 1, 0xe0), 0x7c0902a6, dform(62, 0, 1, 0x118))
    put(*(dform(62, r, 1, 0x80 + 8 * (r - 3)) for r in range(3, 13)))
    put(*(dform(54, r, 1, 0x130 + 8 * (r - 1)) for r in range(1, 14)))
    # Read actual current dimensions rather than assuming the original 25x32.
    put(dform(32, 12, 2, UI_STATE_TOC), dform(15, 12, 12, 3),
        dform(62, 12, 1, 0xe8), dform(32, 11, 12, -0x7c04),
        dform(62, 11, 1, 0xf0), dform(62, 11, 1, 0x100),
        dform(32, 11, 12, -0x7c00), dform(62, 11, 1, 0xf8),
        dform(14, 8, 0, NAME_CAP), dform(62, 8, 1, 0x108), _mr(3, 31))
    call(STACKABLE)
    put(0x2f830000)
    jump('fit', 0x419e0000)
    put(dform(14, 8, 0, STACK_CAP), dform(62, 8, 1, 0x108))
    label('fit')
    measure()
    put(0x2f830000)
    jump('draw', 0x409d0000)
    put(dform(58, 9, 1, 0x108), 0x7f834840)  # cmplw cr7,r3,r9
    jump('draw', 0x409d0000)
    put(dform(58, 8, 1, 0xf0), _xform(235, 8, 8, 9), _xform(459, 8, 8, 3), 0x2f880001)
    jump('save_size', 0x409c0000)
    put(dform(14, 8, 0, 1))
    label('save_size')
    put(dform(62, 8, 1, 0x100))
    label('remeasure')
    measure()
    put(dform(58, 9, 1, 0x108), 0x7f834840)
    jump('draw', 0x409d0000)
    put(dform(58, 8, 1, 0x100), 0x2f880001)
    jump('draw', 0x409d0000)
    put(dform(14, 8, 8, -1), dform(62, 8, 1, 0x100))
    jump('remeasure')
    label('draw')
    put(dform(58, 3, 1, 0x100), dform(58, 4, 1, 0xf8))
    call(FONT_SETTER)
    # The original variadic draw sees exactly its original register inputs,
    # including floating-point arguments and condition-register vararg flags.
    restore_float_condition_counter()
    put(*(dform(58, r, 1, 0x80 + 8 * (r - 3)) for r in range(3, 13)))
    call(DRAW)
    put(dform(62, 3, 1, 0x110), dform(58, 12, 1, 0xe8),
        dform(58, 11, 1, 0xf0), dform(36, 11, 12, -0x7c04),
        dform(58, 11, 1, 0xf8), dform(36, 11, 12, -0x7c00))
    # Keep the native draw's consumed override flag. Restore dimensions only;
    # calling the setter again would accidentally re-enable that flag.
    restore_float_condition_counter()
    put(dform(58, 0, 1, 0xd0), 0x7c0803a6, dform(58, 2, 1, 0xe0))
    put(*(dform(58, r, 1, 0x80 + 8 * (r - 3)) for r in range(4, 13)))
    put(dform(58, 3, 1, 0x110), dform(14, 1, 1, FRAME), 0x4e800020)
    for index, name, conditional in pending:
        origin, target = address + index * 4, address + labels[name] * 4
        if conditional is None:
            words[index] = branch(origin, target)
        else:
            delta = target - origin
            if delta % 4 or not -0x8000 <= delta < 0x8000:
                raise ValueError('Inventory conditional branch out of range')
            words[index] = conditional | (delta & 0xfffc)
    return b''.join(instruction(word) for word in words)


def append_code(original, code):
    """Append one bridge and return (ELF-file-offset patches, English audit)."""
    if not isinstance(code, bytearray):
        raise TypeError('Runtime code must be a mutable bytearray')
    checks = []
    for address, expected in GUARDS:
        expected = bytes.fromhex(expected)
        actual = original[address - 0x10000:address - 0x10000 + len(expected)]
        if actual != expected:
            raise ValueError(f'Inventory context mismatch at {address:#x}: '
                             f'expected {expected.hex()}, got {actual.hex()}')
        checks.append(dict(address=hex(address), expected=expected.hex()))
    padding = -len(code) % 16
    address = CODE_BASE + len(code) + padding
    addition = bytearray(b'\0' * padding + _bridge(address))
    addition.extend(b'\0' * (-(len(code) + len(addition)) % 16))
    if CODE_BASE + len(code) + len(addition) > CODE_LIMIT:
        raise ValueError('Inventory fitting exceeds inspected code gap')
    offset = CODE_BASE + len(code) - 0x10000
    if any(original[offset:offset + len(addition)]):
        raise ValueError('Inventory bridge destination is not zero-filled')
    code.extend(addition)
    return [(DRAW_SITE - 0x10000, instruction(branch(DRAW_SITE, address, True)))], dict(
        draw_site=hex(DRAW_SITE), bridge=hex(address), code_bytes=len(addition),
        frame_bytes=FRAME, ordinary_name_width=NAME_CAP, stackable_name_width=STACK_CAP,
        original_maximum_horizontal_size=25, original_vertical_size=32,
        dimensions_read_from_native_state=True, restores_native_font_dimensions=True,
        preserves_original_draw_result=True, preserves_varargs=True,
        preserves_fpr_1_through_13=True, preserves_cr_ctr_lr=True,
        preserves_selected_colors=True, quantity_draw_unchanged=True,
        name_relative_x=28, quantity_relative_right=320, maximum_stack_quantity=99,
        maximum_quantity_width=32, stack_quantity_gap=8,
        minimum_horizontal_size=1, uses_existing_english_measurement_hook=True,
        no_shared_mutable_storage=True, deferred_preview_id='X0016',
        guarded_instructions=checks,
    )


def corpus_audit():
    """Measure every nonempty item-name field, including original ASCII names.

    Japanese is read only from ignored source data and never enters the report.
    Identified names also test the native signed five-bit enhancement suffixes.
    """
    from fontTools.ttLib import TTFont
    from check_translation import ROOT, read_sources, read_english, JAPANESE_PROSE
    from check_vwf import cache_width, pen_positions
    sources, english = read_sources(), read_english()
    replacements = {}
    kinds = {'name', 'alternate_name', 'unidentified_name'}
    for key, row in sources.items():
        if not row['source'].startswith('databases/') or not row['source'].endswith('items'):
            continue
        for occurrence in row['occurrences']:
            if occurrence['kind'] in kinds:
                decision = english.get(key, {})
                if not decision.get('en'):
                    raise ValueError('Missing inventory name translation: ' + key)
                replacements[(occurrence['archive'], occurrence['record'], occurrence['field_offset'])] = (key, decision['en'])
    font = TTFont(ROOT / 'work/source/NPJB00162/USRDIR/FOT-UtrilloPro-DB.otf')
    widths = {chr(c): cache_width(font['hmtx'][g][0], font['head'].unitsPerEm)
              for c, g in font.getBestCmap().items()}
    fields, variants, cases, archives = 0, {}, [], []
    for archive in ('table.enc', 'addtable01.enc', 'addtable02.enc', 'ppdata.enc'):
        path = ROOT / 'work/source/decoded/USRDIR/data' / archive / '0000.dat'
        if not path.exists():
            continue
        data = path.read_bytes()
        extra = 0 if archive == 'table.enc' else 4
        stride = 432 + extra
        if len(data) % stride:
            raise ValueError('Invalid item-name corpus stride: ' + archive)
        archives.append(dict(archive=archive, records=len(data) // stride))
        for record in range(len(data) // stride):
            for base, kind in ((0, 'name'), (42, 'alternate_name'), (96, 'unidentified_name')):
                offset = base + extra
                raw = data[record * stride + offset:record * stride + offset + 42].split(b'\0', 1)[0]
                if not raw:
                    continue
                key, text = replacements.get((archive, record, offset),
                                             (f'{archive}:{record}:{kind}', raw.decode('utf8')))
                if JAPANESE_PROSE.search(text):
                    raise ValueError('Untranslated inventory name remains at ' + key)
                fields += 1
                suffixes = ('', '+15', '-16') if kind != 'unidentified_name' else ('',)
                for suffix in suffixes:
                    variants.setdefault(text + suffix, dict(id=key, kind=kind, suffix=suffix))
    for text, provenance in sorted(variants.items()):
        for cap in (NAME_CAP, STACK_CAP):
            size = 25
            full = pen_positions(text, size, widths)[1]
            if full > cap:
                size = max(1, size * cap // int(full))
                while size > 1 and pen_positions(text, size, widths)[1] > cap:
                    size -= 1
            actual = pen_positions(text, size, widths)[1]
            cases.append(dict(**provenance, text=text, maximum_width=cap,
                              original_width=full, fitted_horizontal_size=size,
                              fitted_width=actual, fits=actual <= cap))
    if not cases:
        raise ValueError('Inventory name corpus is empty')
    return dict(result='passed' if all(row['fits'] for row in cases) else 'failed',
                archives=archives, nonempty_name_fields=fields, unique_display_variants=len(variants),
                cases=len(cases), minimum_horizontal_size=min(row['fitted_horizontal_size'] for row in cases),
                maximum_original_width=max(row['original_width'] for row in cases),
                failures=[row for row in cases if not row['fits']],
                long_name_samples=[row for row in cases if row['text'] == 'Protective Gear-like Object'],
                all_cases=cases, updated_game_capture=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path,
                        default=Path('work/source/NPJB00162/USRDIR/EBOOT.elf'))
    parser.add_argument('--corpus', action='store_true')
    args = parser.parse_args()
    code = bytearray()
    patches, audit = append_code(args.source.read_bytes(), code)
    result = dict(mode='dry-run', patches=[dict(offset=hex(o), replacement=p.hex()) for o, p in patches], audit=audit)
    if args.corpus:
        result['corpus'] = {k: v for k, v in corpus_audit().items() if k != 'all_cases'}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
