"""Collection-only call guards, complete category strings and font bounds."""
import struct
import unittest
from capstone import Cs, CS_ARCH_PPC, CS_MODE_64, CS_MODE_BIG_ENDIAN
from check_translation import ROOT
from item_collection_layout import CODE_BASE, GROUPS, GUARDS, SITES, append_code, labels
from runtime_text import branch, instruction
from spell_description_layout import width


class CollectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=(ROOT/'work/source/NPJB00162/USRDIR/EBOOT.elf').read_bytes()

    def test_only_two_collection_calls_change(self):
        code=bytearray();changes,audit=append_code(self.original,code)
        self.assertEqual(changes,[(a-0x10000,instruction(branch(a,CODE_BASE,True))) for a in SITES])
        self.assertTrue(audit['shared_type_names_unchanged'])
        self.assertTrue(audit['native_formatter_unchanged'])

    def test_caller_and_category_membership_guards(self):
        for address,expected in GUARDS:
            for i in range(len(expected)):
                changed=bytearray(self.original);changed[address-0x10000+i]^=1;code=bytearray()
                with self.subTest(address=hex(address+i)),self.assertRaises(ValueError):
                    append_code(changed,code)
                self.assertFalse(code)

    def test_every_group_has_a_complete_label_and_leaf_keeps_native_state(self):
        code=bytearray();_,audit=append_code(self.original,code)
        table=int(audit['table'],16)-CODE_BASE
        for group,text in zip(GROUPS[::3],labels()):
            pointer=struct.unpack_from('>I',code,table+4*group)[0]-CODE_BASE
            self.assertEqual(bytes(code[pointer:]).split(b'\0')[0],text.encode('ascii'))
            self.assertLessEqual(len(text)+1,audit['copy_budget'])
        md=Cs(CS_ARCH_PPC,CS_MODE_64|CS_MODE_BIG_ENDIAN)
        decoded=[(i.mnemonic,i.op_str) for i in md.disasm(code[:68],CODE_BASE)]
        self.assertEqual(len(decoded),17)
        self.assertEqual(decoded[-1],('blr',''))
        self.assertEqual(decoded[15],('bne','cr7, '+hex(CODE_BASE+40)))
        self.assertEqual(decoded[11],('stb','r0, 0(r11)'))
        # No nested call, LR/TOC/stack change or nonvolatile register writes.
        self.assertFalse(any(op in ('bl','stdu','mflr','mtlr') for op,_ in decoded))
        self.assertTrue(all(not any('r'+str(r)+',' in arg for r in [1,2]+list(range(14,32))) for _,arg in decoded))

    def test_every_label_leaves_room_for_percentages_and_header_icons(self):
        for text in labels():
            with self.subTest(text=text):
                self.assertLessEqual(width(text,24),128)
                # Conservative 256px pane, two 16px insets and a 12px gap.
                self.assertLessEqual(32+width(text,24)+12+width('100.0%',24),256)
                self.assertLessEqual(width(text,32),256)


if __name__=='__main__':unittest.main()
