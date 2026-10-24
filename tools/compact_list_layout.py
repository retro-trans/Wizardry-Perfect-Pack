"""Fit status skills and ordinary/shop item rows; shorten shop groups locally."""
from runtime_text import CODE_BASE, CODE_LIMIT, branch, dform, instruction
from inventory_layout import _bridge
from item_collection_layout import image, labels

SKILL_SITE = 0xb7464
ITEM_SITES = (0xf7eb0, 0xf8020)
SHOP_SITES = (0xf5430, 0xfa8cc)
SHOP_GROUP_ADDRESS = 0x5179a5
SHOP_GROUPS = bytes.fromhex('0f0000010203040506080000070000090b000a0c000d00000e0000')
SKILL_CAP = 164
# Name starts at x+24, count ends at window width-16. Leave 72px for
# quantities, the native unit suffix and their gap; prices reserve 136px.
ITEM_CAP_WORDS = (dform(32,8,24,0xd0), dform(14,8,8,-112),
                  dform(32,9,24,0x11c), 0x2f890001, 0x409e0008,
                  dform(14,8,8,-64))
GUARDS = (
    (0xb740c, '3880001638600016480193816000000083b60000813500003bbd000c392900627bcb00205529053e7fbfea1465290a0057bd6226a06b00027fbd4b784bfae64d600000003c8000647bbd002078650020608400807fa3eb784801a149'),
    (0xb74bc, '38a000a4'),  # selected skill cell is 164px wide
    (0xf7e54, '38800018386000184bfd8939600000008322ad0483c2ad087f43d37883b90000813e00003bbd000c392900187fb6ea145529053e57bd622665290a007fbd4b784bf60bd5600000007bbd00203c80006478650020608400807fa3eb784bfd96fd600000004bfffcc4'),
    (0xf7fd0, '4bfd87c5600000008322ad0483c2ad087f43d37883b90000813e00003bbd000c392900187fb6ea145529053e57bd6226652901007fbd4b784bf60a61600000003c80006478650020608400807ba301e04bfd958d60000000'),
    (0xf7c8c, '813800d0801e00007d3d4850807900003c8000647d3c48503863000c7d2902147c63b2143929fff0'),
    (0xf7df4, '7f43d3783a4100704bf60179600000005463063e2f830000419efe0c'),
    (0xf5410, '5524083c8002ad2c3b8100707c844a147b9c00207c8402147f83e378788400204bff6b1d'),
    (0xfa8bc, '788400207bbd00207f63db78917700004bff1681'),
    (SHOP_GROUP_ADDRESS, SHOP_GROUPS.hex()),
)


def shop_labels():
    rows = labels()
    rows[2] = 'Other Weapons'  # Staff, blunt and thrown weapons share this tab.
    rows[6] = rows[7] = 'Shield/Gloves'
    rows[8] = rows[9] = 'Helm/Boots'
    return rows


def append_code(original, code):
    for a, expected in GUARDS:
        payload = bytes.fromhex(expected)
        if original[a-0x10000:a-0x10000+len(payload)] != payload:
            raise ValueError('Compact list context mismatch at '+hex(a))
    addition = bytearray(b'\0'*(-len(code)%16))
    bridges = []
    patches = []
    for sites, options in (((SKILL_SITE,), dict(fixed_cap=SKILL_CAP)),
                           (ITEM_SITES, dict(cap_words=ITEM_CAP_WORDS))):
        entry = CODE_BASE+len(code)+len(addition)
        addition.extend(_bridge(entry, **options))
        addition.extend(b'\0'*(-len(addition)%16))
        bridges.append(dict(sites=[hex(a) for a in sites], entry=hex(entry)))
        patches.extend((a-0x10000,instruction(branch(a,entry,True))) for a in sites)
    stub = CODE_BASE+len(code)+len(addition)
    body, categories = image(stub,shop_labels())
    addition.extend(body)
    patches.extend((a-0x10000,instruction(branch(a,stub,True))) for a in SHOP_SITES)
    if CODE_BASE+len(code)+len(addition)>CODE_LIMIT:
        raise ValueError('Compact lists exceed runtime code gap')
    offset=CODE_BASE+len(code)-0x10000
    if any(original[offset:offset+len(addition)]):
        raise ValueError('Compact list destination is not zero-filled')
    code.extend(addition)
    return patches, dict(bridges=bridges, shop_categories=categories,
                         skill_width=SKILL_CAP, item_width_from_window=True,
                         item_quantity_gap=8, item_quantity_reserved=64,
                         shop_price_reserved=128, full_names_preserved=True,
                         original_quantity_draws_unchanged=True,
                         skill_description_heading_unchanged=True,
                         updated_ingame_verification=False)
