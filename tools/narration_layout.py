"""Guarded reflow bridge for anonymous event narration's separate Show path.

The original handler skips the ordinary/typewriter hook when its speaker state
is empty. This call boundary already has the complete paragraph in r4 and its
window in r3. The presenter shows pages with native flags 0xf0, waiting only
between pages. Event opcode 0x50 retains ownership of the final acceptance.
"""
from runtime_text import CODE_BASE, branch, dform, instruction, load_address

SITE = 0xa6084
NATIVE_SHOW_WRAPPER = 0xde474
EXPECTED_CONTEXT = bytes.fromhex('7ee3bb787fe4fb78480383f1600000004bffff44')
FINAL_WAIT_SITE = 0xa5b40
EXPECTED_FINAL_WAIT = bytes.fromhex('8bfd2a187fe3fb784803827960000000')
FRAME_BYTES = 0x500
GPR_BASE = 0x100
FPR_BASE = 0x200
R0_SAVE, LR_SAVE, CR_SAVE, CTR_SAVE, RESULT = 0x440, 0x448, 0x450, 0x458, 0x460


def append_code(original, code, presenter_entry):
    """Append a bridge to the supplied absolute ELFv2 local presenter entry.

    C ABI: int present_narration(unsigned window, const char *text,
                                 uintptr_t font).
    Zero requests the original variadic native wrapper. Nonzero leaves the
    final page visible and returns to its caller's original continuation.
    """
    for address, expected in ((SITE - 8, EXPECTED_CONTEXT),
                              (FINAL_WAIT_SITE, EXPECTED_FINAL_WAIT)):
        offset = address - 0x10000
        if original[offset:offset + len(expected)] != expected:
            raise ValueError('Anonymous narration boundary mismatch at ' + hex(address))
    if presenter_entry % 4 or not CODE_BASE <= presenter_entry < CODE_BASE + len(code):
        raise ValueError('Narration presenter local entry is outside appended payload')
    code.extend(b'\0' * (-len(code) % 16))
    bridge = CODE_BASE + len(code)
    # Native ELFv1 callees may use their caller's argument home area through
    # +0xd8. All saves and local values begin beyond that area.
    words = [dform(62, 1, 1, -FRAME_BYTES | 1),
             dform(62, 0, 1, R0_SAVE), 0x7c0802a6,
             dform(62, 0, 1, LR_SAVE), 0x7c000026,
             dform(62, 0, 1, CR_SAVE), 0x7c0902a6,
             dform(62, 0, 1, CTR_SAVE)]
    words += [dform(62, r, 1, GPR_BASE + 8 * (r - 2)) for r in range(2, 32)]
    words += [dform(54, r, 1, FPR_BASE + 8 * r) for r in range(32)]
    words += [dform(32, 5, 2, -0x588c), dform(32, 5, 5, 0)]
    words += load_address(12, presenter_entry)
    words += [0x7d8903a6, 0x4e800421, dform(62, 3, 1, RESULT)]
    words += [dform(50, r, 1, FPR_BASE + 8 * r) for r in range(32)]
    words += [dform(58, r, 1, GPR_BASE + 8 * (r - 2)) for r in range(2, 32)]
    words += [dform(58, 0, 1, CTR_SAVE), 0x7c0903a6,
              dform(58, 0, 1, LR_SAVE), 0x7c0803a6,
              dform(58, 0, 1, RESULT), 0x2f800000]
    choose = len(words)
    words += [0]
    restore = [dform(58, 0, 1, CR_SAVE), 0x7c0ff120,
               dform(58, 0, 1, R0_SAVE), dform(14, 1, 1, FRAME_BYTES)]
    words += restore + [0x4e800020]
    passthrough = len(words)
    words += restore
    words += [branch(bridge + len(words) * 4, NATIVE_SHOW_WRAPPER)]
    words[choose] = 0x419e0000 | ((passthrough - choose) * 4)
    code.extend(b''.join(instruction(word) for word in words))
    code.extend(b'\0' * (-len(code) % 16))
    return [(SITE - 0x10000, instruction(branch(SITE, bridge, True)))], dict(
        site=hex(SITE), bridge=hex(bridge), presenter=hex(presenter_entry),
        continuation=hex(SITE + 4), original_show_wrapper=hex(NATIVE_SHOW_WRAPPER),
        inner_width=896, font_size=32, lines_per_page=3, native_show_flags='0xf0',
        intermediate_wait='0xdddc0(window,1)', final_wait='event opcode 0x50 -> 0xa5b48',
        complete_event_paragraph=True, ordinary_typewriter_hook_unchanged=True,
        stack_frame_bytes=FRAME_BYTES, all_gprs_and_fprs_preserved=True,
        cr_ctr_lr_toc_preserved=True, global_message_api_unchanged=True)
