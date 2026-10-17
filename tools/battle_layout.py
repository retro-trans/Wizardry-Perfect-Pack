"""Bridge only the assembled battle-reward message to a paged presenter.

The presenter owns wrapping and calls native Show with flags 0xd1. It waits
only between pages; the unchanged caller waits for the final page. Its ABI is
``int present_battle(unsigned window, const char *text, uintptr_t font)``.
Zero requests the original native call. A nonzero result means it has shown
the final page. No global message API or other battle caller is intercepted.
"""
from runtime_text import CODE_BASE, branch, dform, instruction, load_address

SITE = 0x21860
NATIVE_SHOW_WRAPPER = 0xde6d8
EXPECTED_CONTEXT = bytes.fromhex(
    '7fa3eb78'  # 2185c: mr r3,r29, the complete formatted reward buffer
    '480bce79'  # 21860: bl de6d8
    '60000000'  # 21864: nop
    '38600001'  # 21868: li r3,1
    '480bc5d5'  # 2186c: bl dde40, original final-page acceptance
    '60000000'  # 21870: nop
)


def _mr(dst, src):
    return (31 << 26) | (src << 21) | (dst << 16) | (src << 11) | (444 << 1)


def append_code(original, code, presenter_entry, resolver_entry, table_address, count,
                alias_address, alias_count):
    """Append a guarded bridge; return file-offset patches and audit metadata.

    ``code`` is the shared code-gap bytearray. Main must append the compiled
    presenter first and pass its absolute ELFv2 local entry (not its TOC setup).
    The bridge invokes it through CTR, preserving the game's r2 and all input
    argument registers. The original native wrapper remains callable directly.
    """
    start = SITE - 4 - 0x10000
    if original[start:start + len(EXPECTED_CONTEXT)] != EXPECTED_CONTEXT:
        raise ValueError('Battle reward Show/Wait boundary mismatch')
    if not CODE_BASE <= presenter_entry < CODE_BASE + len(code) or presenter_entry % 4:
        raise ValueError('Battle presenter local entry is outside appended payload')
    code.extend(b'\0' * (-len(code) % 16))
    bridge = CODE_BASE + len(code)

    # The 0x4000 frame also owns a 12KiB expanded reward buffer. Resolve item
    # tokens before wrapping so word boundaries inside full names remain real.
    # In particular callees may overwrite +0x70..+0xd8 in this frame.
    words = [0xf821c001, dform(62, 0, 1, 0x1d8), 0x7c0802a6,
             dform(62, 0, 1, 0x1c0), 0x7c000026,
             dform(62, 0, 1, 0x1c8), dform(62, 2, 1, 0x1b8),
             0x7c0902a6, dform(62, 0, 1, 0x1e0)]
    words += [dform(62, r, 1, 0x100 + 8 * (r - 3)) for r in range(3, 13)]
    words += [dform(54, r, 1, 0x150 + 8 * (r - 1)) for r in range(1, 14)]
    words += [dform(14,4,1,0x200),dform(14,5,0,0x3000)]
    words += load_address(6,table_address)+[dform(14,7,0,count)]
    words += load_address(8,alias_address)+[dform(14,9,0,alias_count)]
    words += load_address(12,resolver_entry)+[0x7d8903a6,0x4e800421,dform(58,2,1,0x1b8)]
    words += [_mr(4, 3), dform(14, 3, 0, 0),
              dform(32, 5, 2, -0x588c), dform(32, 5, 5, 0)]
    words += load_address(12, presenter_entry)
    words += [0x7d8903a6, 0x4e800421, dform(62, 3, 1, 0x1d0)]
    words += [dform(58, 2, 1, 0x1b8), dform(58, 0, 1, 0x1e0), 0x7c0903a6,
              dform(58, 0, 1, 0x1c0), 0x7c0803a6]
    words += [dform(50, r, 1, 0x150 + 8 * (r - 1)) for r in range(1, 14)]
    words += [dform(58, r, 1, 0x100 + 8 * (r - 3)) for r in range(3, 13)]
    words += [dform(58, 0, 1, 0x1d0), 0x2f800000]  # cmpwi cr7,r0,0
    choose = len(words)
    words += [0]
    restore = [dform(58, 0, 1, 0x1c8), 0x7c0ff120,
               dform(58, 0, 1, 0x1d8), dform(14, 1, 1, 0x4000)]
    words += restore + [0x4e800020]  # handled: return to 21864 and outer wait
    passthrough = len(words)
    words += restore
    words += [branch(bridge + len(words) * 4, NATIVE_SHOW_WRAPPER)]
    words[choose] = 0x419e0000 | ((passthrough - choose) * 4)
    code.extend(b''.join(instruction(word) for word in words))
    code.extend(b'\0' * (-len(code) % 16))
    patches = [(SITE - 0x10000, instruction(branch(SITE, bridge, True)))]
    audit = dict(site=hex(SITE), bridge=hex(bridge), presenter=hex(presenter_entry),
                 original_show_wrapper=hex(NATIVE_SHOW_WRAPPER),
                 continuation=hex(SITE + 4), outer_wait='0x2186c -> 0xdde40',
                 inner_width=640, font_size=32, lines_per_page=3,
                 native_show_flags='0xd1', native_show='0xde018',
                 intermediate_wait='0xdddc0(window,1)',
                 complete_reward_buffer=True, global_message_api_unchanged=True,
                 stack_frame_bytes=0x4000,expansion_capacity=0x3000,
                 expands_item_names_before_layout=True)
    return patches, audit
