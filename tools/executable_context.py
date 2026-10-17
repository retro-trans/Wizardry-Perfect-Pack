"""Resolve edition-specific translations for individual executable pointers.

Identical source strings may represent unrelated meanings. Overrides select a
guarded data-pointer reference, not every occurrence of the source text. Their
addresses belong to this edition and must never be imported into another one.
"""
import re


def hexadecimal(value, label):
    if not isinstance(value, str) or not re.fullmatch(r'0x[0-9a-fA-F]+', value):
        raise ValueError(label+' must be a hexadecimal address string')
    return int(value, 16)


def reference_overrides(source, decision):
    rows = decision.get('reference_overrides', [])
    if not isinstance(rows, list):
        raise ValueError('reference_overrides must be a list')
    if rows and (source.get('source') != 'executable' or decision.get('en') is None):
        raise ValueError('Reference translations require a translated executable row')
    addresses = {o['address'] for o in source['occurrences'] if 'address' in o}
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Invalid executable reference translation')
        pointer = hexadecimal(row.get('pointer_offset'), 'pointer_offset')
        address = hexadecimal(row.get('source_address'), 'source_address')
        text, context = row.get('en'), row.get('context')
        if pointer % 4 or pointer in result:
            raise ValueError('Duplicate or unaligned executable reference')
        if address not in addresses:
            raise ValueError('Reference source address is not an occurrence of this row')
        if not isinstance(text, str) or not text or '\0' in text:
            raise ValueError('Reference translation must be nonempty text without NUL')
        if not isinstance(context, str) or not context.strip() or '\0' in context:
            raise ValueError('Reference translation requires its semantic context')
        result[pointer] = dict(id=source['id'], pointer_offset=pointer,
                               source_address=address, en=text, context=context)
    return result


def collect_reference_overrides(sources, english):
    result = {}
    for key, decision in english.items():
        if key not in sources:
            continue
        for pointer, row in reference_overrides(sources[key], decision).items():
            if pointer in result:
                raise ValueError('Executable reference has more than one translation')
            result[pointer] = row
    return result
