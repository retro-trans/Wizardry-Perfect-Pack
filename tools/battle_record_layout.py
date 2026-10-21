"""Guarded fixed columns for the Battle Record statistics panels."""
from runtime_text import instruction

PANEL_WIDTH = 1040
INSET = 16
STRIDE = 336
LABEL_RIGHT = 224
VALUE_LEFT = 236
FONT_SIZE = 24
TYPE_IDS = ('X0100', 'X0113', 'X0114', 'X0115', 'X0116', 'X0117', 'X0118',
            'X0119', 'X0120', 'X0121', 'X0122', 'X0123', 'X0124')
FONT_SITES = ((0xfea4c, 0x38c00020), (0xfea54, 0x38a00020),
              (0xfea80, 0x38600020), (0xfea84, 0x38800020),
              (0xfe9c0, 0x38600020), (0xfe9c4, 0x38800020))
CHANGES = (
    (0xfe994, 0x3aa90020, 0x3aa000ec),  # fixed numeric anchor 236
    (0xfe9a4, 0x7e83aa14, 0x3a800150),  # fixed column stride 336
    (0xfea68, 0x7c7d1b78, 0x3ba3000c),  # label measure +12 gives a gap
    (0xfee2c, 0x23bd00a0, 0x23bd00c0),  # Deaths label ends at192
    (0xfefa0, 0x23bd0200, 0x23bd0210),  # Wipeouts label ends at528
    (0xfeed4, 0x392900a0, 0x392900cc),  # Deaths value starts at204
    (0xff044, 0x39290200, 0x3929021c),  # Wipeouts value starts at540
    (0xff1c0, 0x39290360, 0x3929036c),  # Chests value starts at876
    (0xfe930, 0x396b0010, 0x396b001c),  # total kills heading gap
    (0xfed5c, 0x38630010, 0x3863001c),  # play time heading gap
) + tuple((a, before, (before & 0xffff0000) | FONT_SIZE) for a, before in FONT_SITES)
COPIES = (
    ('X2436', 14, 0xfef04, 0x8122ae8c, 0xfef30, 0x8a89000d, 0xfef84, 0x9a81007d),
    ('X2437', 14, 0xff074, 0x8122ae90, 0xff0a0, 0x8a89000d, 0xff0f4, 0x9a81007d),
)
# Native loop: divide index by3 for the row; later subtract row*3 for column.
LOOP = (0xfea14, bytes.fromhex('7f40fe707f9a90967b5b06207f80e0507f63db78578928343b090040'))


def patches(original):
    guards = [(LOOP[0], LOOP[1])]
    for _, _, *row in COPIES:
        guards.extend((a, instruction(w)) for a, w in zip(row[::2], row[1::2]))
    for address, expected in guards:
        if original[address-0x10000:address-0x10000+len(expected)] != expected:
            raise ValueError('Battle Record context mismatch at '+hex(address))
    changes = []
    for address, before, after in CHANGES:
        if original[address-0x10000:address-0x10000+4] != instruction(before):
            raise ValueError('Battle Record instruction mismatch at '+hex(address))
        changes.append((address-0x10000, instruction(after)))
    return changes, dict(panel_width=PANEL_WIDTH, columns=3, column_stride=STRIDE,
                         monster_label_right=LABEL_RIGHT, monster_value_left=VALUE_LEFT,
                         monster_font_size=FONT_SIZE, column_gap=12, row_pitch=32,
                         monster_count_cap=999999, summary_font_size=32,
                         summary_label_ends=[192,528,864], summary_value_starts=[204,540,876],
                         summary_count_caps=[9999,9999,9999999],
                         row_positions_and_colors_unchanged=True,
                         deferred_labels=[r[0] for r in COPIES],
                         changes=[dict(address=hex(a), before=hex(b), after=hex(c))
                                  for a,b,c in CHANGES])
