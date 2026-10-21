"""Bounded display lines for the chest prompt beside its illustration."""
from spell_description_layout import width

PROMPT_ID = 'X1801'
WIDTH = 560
FONT_SIZE = 32
MAX_LINES = 3


def display_text(key, decision):
    if key != PROMPT_ID:
        return decision['en']
    lines = decision.get('display_lines')
    if (not isinstance(lines, list) or not 1 <= len(lines) <= MAX_LINES or
            any(not isinstance(line, str) or not line or '\n' in line or '\0' in line for line in lines)):
        raise ValueError('Invalid chest prompt display lines')
    result = '\n'.join(lines)
    if result.split() != decision['en'].split():
        raise ValueError('Chest prompt display words changed')
    if any(width(line, FONT_SIZE) > WIDTH for line in lines):
        raise ValueError('Chest prompt exceeds illustrated panel width')
    return result
