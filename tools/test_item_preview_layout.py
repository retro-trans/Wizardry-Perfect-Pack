"""Read-only scope and guard checks for armor/accessory coordinate fixes."""
import unittest
from check_translation import ROOT
from item_preview_layout import patches,LABEL_SITES,VALUE_SITES


class PreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.original=(ROOT/'work/source/NPJB00162/USRDIR/EBOOT.elf').read_bytes()

    def test_all_stat_pairs_move_together_and_other_branches_are_unchanged(self):
        changes,audit=patches(self.original);changed=bytearray(self.original)
        self.assertEqual(len(changes),8)
        for offset,data in changes:changed[offset:offset+len(data)]=data
        self.assertEqual(changed[0xf83b0-0x10000:0xf8da0-0x10000],self.original[0xf83b0-0x10000:0xf8da0-0x10000])
        for address in LABEL_SITES+VALUE_SITES:
            self.assertEqual(int.from_bytes(changed[address-0x10000:address-0x10000+4],'big')&65535,140)
        self.assertEqual(audit['horizontal_shift'],80)

    def test_each_changed_instruction_is_guarded(self):
        for address in LABEL_SITES+VALUE_SITES:
            changed=bytearray(self.original);changed[address-0x10000]^=1
            with self.subTest(address=hex(address)),self.assertRaises(ValueError):patches(changed)


if __name__=='__main__':unittest.main()
