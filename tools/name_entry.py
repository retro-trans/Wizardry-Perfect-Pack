"""Guard the name-entry buffers and retain the native character/save layout."""
import hashlib
import struct
from runtime_text import CODE_BASE, branch, dform, instruction

LIMIT = 12
NAME_OFFSET, NAME_BYTES = 0x1bd, 33
STATE_BYTES, INITIAL_OFFSET, RESULT_OFFSET = 0x90, 0x54, 0x70
STATE_POINTER = 0x48366c
ORIGINAL_STATE = 0x51ecfa0
SETTER = 0x50bc0
# Exact original instructions, all virtual addresses in Perfect Pack NPJB00162.
CHANGES = (
    (0x10c674, '387d0018', dform(14, 3, 29, INITIAL_OFFSET)),
    (0x10c684, '381d0044', dform(14, 0, 29, RESULT_OFFSET)),
    (0x10c698, '38000006', dform(14, 0, 0, LIMIT)),
    (0x10c6b0, '38dd0018', dform(14, 6, 29, INITIAL_OFFSET)),
    (0x10c6bc, '38000020', dform(14, 0, 0, LIMIT+1)),
    (0x10c73c, '393d0018', dform(14, 9, 29, INITIAL_OFFSET)),
    (0x10c530, '38800024', dform(14, 4, 0, NAME_BYTES)),
)


def append_code(original, code, payload, entry, state_address):
    if struct.unpack_from('>I', original, STATE_POINTER-0x10000)[0] != ORIGINAL_STATE:
        raise ValueError('Name-entry state pointer changed')
    if original[SETTER-0x10000:SETTER-0x10000+4] != bytes.fromhex('2f840000'):
        raise ValueError('Name setter entry changed')
    patches, changed = [], []
    for address, before, word in CHANGES:
        if original[address-0x10000:address-0x10000+4] != bytes.fromhex(before):
            raise ValueError('Name-entry instruction changed at '+hex(address))
        patches.append((address-0x10000, instruction(word)))
        changed.append(dict(address=hex(address), before=before, after=instruction(word).hex()))
    code.extend(b'\0'*(-len(code)%16))
    helper = CODE_BASE+len(code)
    # Native PS3 pointers are 32-bit values in 64-bit argument registers.
    # Clear their upper halves before entering the freestanding LP64 leaf.
    code.extend(instruction(0x78630020)+instruction(0x78840020)+
                instruction(branch(helper+8,helper+16+entry))+b'\0'*4)
    payload_start=helper+16
    code.extend(payload)
    code.extend(b'\0'*(-len(code)%16))
    patches.extend(((SETTER-0x10000, instruction(branch(SETTER, helper+entry))),
                    (STATE_POINTER-0x10000, struct.pack('>I', state_address))))
    return patches, dict(character_limit=LIMIT, saved_name_bytes=NAME_BYTES,
                         saved_name_offset=hex(NAME_OFFSET), save_layout_changed=False,
                         state_address=hex(state_address), state_bytes=STATE_BYTES,
                         initial_text_offset=hex(INITIAL_OFFSET), result_text_offset=hex(RESULT_OFFSET),
                         setter=hex(SETTER), helper=hex(helper), helper_start=hex(payload_start),
                         pointer_arguments_truncated_to_32_bits=True,
                         helper_bytes=len(payload), helper_sha256=hashlib.sha256(payload).hexdigest(),
                         instructions=changed, updated_ingame_verification=False)
