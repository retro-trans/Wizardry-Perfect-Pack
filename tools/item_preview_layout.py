"""Guarded position correction for armor/accessory preview stat rows only."""
from runtime_text import instruction

LABEL_SITES=(0xf8e18,0xf8f68,0xf90b4,0xf9200)
VALUE_SITES=(0xf8ecc,0xf9018,0xf9164,0xf9298)


def patches(original):
    changes=[]
    for sites,expected,replacement in ((LABEL_SITES,0x23bd003c,0x23bd008c),
                                       (VALUE_SITES,0x3929003c,0x3929008c)):
        for address in sites:
            offset=address-0x10000
            if original[offset:offset+4]!=instruction(expected):
                raise ValueError('Armor preview coordinate mismatch at '+hex(address))
            changes.append((offset,instruction(replacement)))
    return changes,dict(branch='armor/accessory categories 9 through 16',
                        horizontal_shift=80,old_relative_anchor=60,new_relative_anchor=140,
                        label_sites=[hex(a) for a in LABEL_SITES],value_sites=[hex(a) for a in VALUE_SITES],
                        row_positions_unchanged=True,weapon_and_misc_branches_unchanged=True)
