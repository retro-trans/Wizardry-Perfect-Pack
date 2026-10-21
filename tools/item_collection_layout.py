"""Compact category groups at the two Item Collection format calls only."""
import json
from pathlib import Path
import struct
from runtime_text import CODE_BASE, branch, dform, instruction, load_address

ROOT = Path(__file__).resolve().parents[1]
SITES = (0x100fbc, 0x1019bc)
GROUP_ADDRESS = 0x5179c7
GROUPS = bytes.fromhex('0f00000102030405000600000800000700000900000b00000a00000c00000d00000e0000')
GUARDS = ((0x100fb0, bytes.fromhex('7b6400207fe3fb783b7b00034bfeaf9160000000')),
          (0x10198c, bytes.fromhex('813a000c3bbf015c7f83e3787d2902147bbd00205524083c7c844a14813b00007c845a143929001c78840020913b00004bfea59160000000')),
          (GROUP_ADDRESS, GROUPS))


def labels():
    rows = json.loads((ROOT/'work/translation/en/item_collection.en.json').read_text(encoding='utf8'))['labels']
    if len(rows) != 12 or any(not isinstance(t, str) or not t or len(t)>=16 or
                             any(ord(c)<32 or ord(c)>126 for c in t) for t in rows):
        raise ValueError('Invalid compact collection labels')
    return rows


def image(stub, rows):
    # Table indexed by the first type byte. Unused group heads use a safe name.
    first_types = GROUPS[::3]
    names = dict(zip(first_types, rows))
    names.update({0: rows[-1], 2: rows[1], 3: rows[1], 5: rows[2]})
    # Leaf: preserve LR, TOC, stack and all nonvolatile registers. Copy the
    # complete short label including NUL into the caller's existing buffer.
    words = [0x78630020, dform(34,9,4,0), 0x2b89000f, 0x409d0008,
             dform(14,9,0,15), 0x5529103a]
    table = stub+80
    words += load_address(10,table)
    words += [0x7d4a482e, 0x7c6b1b78, dform(34,0,10,0), dform(38,0,11,0),
              dform(14,10,10,1), dform(14,11,11,1), 0x2f800000, 0x409effec]
    # Loop branch at byte60 returns to byte40. blr follows, table aligned.
    words.append(0x4e800020)
    body = bytearray(b''.join(instruction(w) for w in words))
    body.extend(b'\0'*(80-len(body)))
    strings = bytearray(); pointers = []
    for i in range(16):
        pointers.append(table+64+len(strings))
        strings.extend(names[i].encode('ascii')+b'\0')
    body.extend(struct.pack('>16I',*pointers));body.extend(strings)
    body.extend(b'\0'*(-len(body)%16))
    return bytes(body), dict(stub=hex(stub),table=hex(table),code_bytes=68,
                             labels=rows,first_types=list(first_types),copy_budget=16,
                             maximum_copy_bytes=max(len(t)+1 for t in rows))


def append_code(original, code):
    for address, expected in GUARDS:
        if original[address-0x10000:address-0x10000+len(expected)] != expected:
            raise ValueError('Item Collection context mismatch at '+hex(address))
    stub = CODE_BASE+len(code)
    body, audit = image(stub, labels())
    code.extend(body)
    audit.update(sites=[hex(a) for a in SITES],shared_type_names_unchanged=True,
                 native_formatter_unchanged=True,updated_ingame_verification=False)
    return [(a-0x10000,instruction(branch(a,stub,True))) for a in SITES],audit
