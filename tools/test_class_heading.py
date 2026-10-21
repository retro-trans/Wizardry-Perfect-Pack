"""Heading lookup scope, native ABI and fail-closed context guards."""
import unittest
from capstone import Cs,CS_ARCH_PPC,CS_MODE_64,CS_MODE_BIG_ENDIAN
from check_translation import ROOT,read_sources,read_english
from class_heading import collect,append_code,CLASS_IDS,CONTEXT_ADDRESS,CONTEXT,GETTER,SITE,TABLE
from runtime_text import CODE_BASE,branch,instruction


class HeadingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=(ROOT/'work/source/NPJB00162/USRDIR/EBOOT.elf').read_bytes()
        cls.sources=read_sources();cls.english=read_english()

    def test_all_thirteen_full_class_names_including_samurai(self):
        rows=collect(self.original,self.sources,self.english)
        self.assertEqual([r['id'] for r in rows],list(CLASS_IDS))
        self.assertEqual([r['en'] for r in rows],['Fighter','Mage','Priest','Thief','Bishop',
            'Samurai','Lord','Ninja','Kensei','Sorcerer','Monk','Ranger','Summoner'])

    def test_only_heading_call_changes_and_leaf_preserves_condition_and_stack(self):
        code=bytearray();rows=collect(self.original,self.sources,self.english)
        changes,audit=append_code(self.original,code,0x55d0000,rows)
        self.assertEqual(changes,[(SITE-0x10000,instruction(branch(SITE,CODE_BASE,True)))])
        md=Cs(CS_ARCH_PPC,CS_MODE_64|CS_MODE_BIG_ENDIAN)
        decoded=[(i.mnemonic,i.op_str) for i in md.disasm(code[:20],CODE_BASE)]
        self.assertEqual(decoded,[('lis','r9, 0x55d'),('ori','r9, r9, 0'),
                                  ('sldi','r3, r3, 2'),('lwzx','r3, r9, r3'),('blr','')])
        self.assertTrue(audit['fixed_copy_class_labels_unchanged'])

    def test_every_caller_byte_and_class_table_entry_are_guarded(self):
        rows=collect(self.original,self.sources,self.english)
        for address,length in ((CONTEXT_ADDRESS,len(CONTEXT)),(GETTER,16),(0x409b00,8)):
            for n in range(length):
                bad=bytearray(self.original);bad[address-0x10000+n]^=1;code=bytearray()
                with self.subTest(address=hex(address+n)),self.assertRaises(ValueError):append_code(bad,code,0x55d0000,rows)
                self.assertFalse(code)
        for i in range(13):
            bad=bytearray(self.original);bad[TABLE-0x10000+4*i]^=1
            with self.subTest(index=i),self.assertRaises(ValueError):collect(bad,self.sources,self.english)


if __name__=='__main__':unittest.main()
