"""Guarded positions for compact weapon and armor/accessory preview stats."""
from runtime_text import instruction

LABEL_SITES=(0xf8e18,0xf8f68,0xf90b4,0xf9200)
VALUE_SITES=(0xf8ecc,0xf9018,0xf9164,0xf9298)
WEAPON_LABEL_SITES=(0xf8490,0xf877c,0xf8a10,0xf8ca0)
WEAPON_VALUE_SITES=(0xf8554,0xf882c,0xf8ac0,0xf8d38)
WEAPON_CHANGES=tuple((a,0x23bd003c,0x23bd005c) for a in WEAPON_LABEL_SITES)+tuple(
    (a,0x3929003c,0x3929005c) for a in WEAPON_VALUE_SITES)+(
    (0xf863c,0x3863004c,0x38630064),(0xf8660,0x3b9c004c,0x3b9c0064))


def patches(original):
    changes=[]
    for sites,expected,replacement in ((LABEL_SITES,0x23bd003c,0x23bd008c),
                                       (VALUE_SITES,0x3929003c,0x3929008c)):
        for address in sites:
            offset=address-0x10000
            if original[offset:offset+4]!=instruction(expected):
                raise ValueError('Armor preview coordinate mismatch at '+hex(address))
            changes.append((offset,instruction(replacement)))
    for address,expected,replacement in WEAPON_CHANGES:
        offset=address-0x10000
        if original[offset:offset+4]!=instruction(expected):
            raise ValueError('Weapon preview coordinate mismatch at '+hex(address))
        changes.append((offset,instruction(replacement)))
    return changes,dict(branch='armor/accessory categories 9 through 16',
                        horizontal_shift=80,old_relative_anchor=60,new_relative_anchor=140,
                        label_sites=[hex(a) for a in LABEL_SITES],value_sites=[hex(a) for a in VALUE_SITES],
                        row_positions_unchanged=True,misc_branch_unchanged=True,
                        weapon_left_shift=32,weapon_count_shift=24,weapon_right_column_unchanged=True,
                        weapon_changes=[dict(address=hex(a),before=hex(b),after=hex(c)) for a,b,c in WEAPON_CHANGES])
