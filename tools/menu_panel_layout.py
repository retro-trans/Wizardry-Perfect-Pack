"""Guarded bestiary/spell fonts, quest status and settings positions."""
from runtime_text import instruction

CHANGES=(
    # Lore uses the narrow right bestiary panel; other list/status fonts reset.
    (0x100560,0x3860001c,0x38600016,'monster_lore_horizontal_size'),
    (0x100564,0x3880001c,0x38800016,'monster_lore_vertical_size'),
    # Full Summoner label fits before the first MP number; number font resets.
    (0x264d8,0x38600020,0x38600016,'spell_school_horizontal_size'),
    (0x26728,0x38800018,0x38800016,'spell_description_vertical_size'),
    # Native status text exceeds the decorative six-space square brackets.
    (0x9ac90,0x4803691d,0x60000000,'quest_status_bracket_draw'),
    # Every selected/unselected Slow branch: move it 24px from Normal.
    (0xe99f0,0x396b0208,0x396b0220,'settings_slow_x'),
    (0xe9a94,0x396b0208,0x396b0220,'settings_slow_x'),
    (0xea260,0x39290208,0x39290220,'settings_slow_x'),
)


def patches(original):
    result=[]
    for address,before,after,name in CHANGES:
        offset=address-0x10000
        if original[offset:offset+4]!=instruction(before):
            raise ValueError('Menu panel instruction mismatch at '+hex(address))
        result.append((offset,instruction(after)))
    return result,dict(spell_school_horizontal_size=22,spell_school_vertical_size=32,
                       monster_lore_horizontal_size=22,monster_lore_vertical_size=22,
                       spell_description_horizontal_size=24,spell_description_vertical_size=22,
                       mp_number_font_unchanged=True,quest_status_brackets_removed=True,
                       settings_slow_horizontal_shift=24,selected_colors_preserved=True,
                       changes=[dict(address=hex(a),before=hex(b),after=hex(c),purpose=n) for a,b,c,n in CHANGES])
