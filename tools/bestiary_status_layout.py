"""Guarded columns for the bestiary status pane, in native 1280x720 pixels."""
from runtime_text import instruction

LABEL_RIGHT = 132
VALUE_LEFT = 144
PANEL_WIDTH = 320
INSET = 16
FONT_SIZE = 24
VALUE_SITES = (0xff620, 0xff784, 0xff8bc, 0xff9e8, 0xffb4c,
               0xffca4, 0xffe04, 0xfff8c, 0x10030c)
CHANGES = ((0xff4e4, 0x3bc3000c, 0x3bc00084),) + tuple(
    (address, 0x7c7e1a14, 0x38630090) for address in VALUE_SITES)
# Copy lengths include the original NUL. These labels must resolve after the
# native stack copy, at both the measure and draw boundaries.
COPIES = (
    ('X2443', 12, 0xffcd0, 0x8122aeb0, 0xffcf0, 0x8ae9000b, 0xffd44, 0x9ae1007b),
    ('X2444', 17, 0xffe30, 0x8122aeb4, 0xffe80, 0x8a690010, 0xffec8, 0x9a610080),
    ('X2438', 17, 0x1001ac, 0x8122ae94, 0x1001fc, 0x8a690010, 0x100244, 0x9a610080),
)


def patches(original):
    for _, _, *guards in COPIES:
        for address, expected in zip(guards[::2], guards[1::2]):
            if original[address-0x10000:address-0x10000+4] != instruction(expected):
                raise ValueError('Bestiary label copy mismatch at '+hex(address))
    result = []
    for address, before, after in CHANGES:
        offset = address-0x10000
        if original[offset:offset+4] != instruction(before):
            raise ValueError('Bestiary status coordinate mismatch at '+hex(address))
        result.append((offset, instruction(after)))
    return result, dict(label_right=LABEL_RIGHT, value_left=VALUE_LEFT,
                        column_gap=VALUE_LEFT-LABEL_RIGHT, panel_width=PANEL_WIDTH,
                        inset=INSET, font_size=FONT_SIZE, row_positions_unchanged=True,
                        value_sites=[hex(a) for a in VALUE_SITES],
                        deferred_labels=[dict(id=row[0], copy_bytes=row[1]) for row in COPIES],
                        changes=[dict(address=hex(a), before=hex(b), after=hex(c))
                                 for a, b, c in CHANGES])
