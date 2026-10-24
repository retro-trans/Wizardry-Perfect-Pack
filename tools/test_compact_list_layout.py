"""Execute the new native fitting paths; check scope, guards and full names."""
import json
import unittest
from capstone import Cs,CS_ARCH_PPC,CS_MODE_64,CS_MODE_BIG_ENDIAN
import compact_list_layout as layout
from check_translation import ROOT
from test_inventory_layout import InventoryMachine
from spell_description_layout import width
from runtime_text import branch,instruction


class CompactListTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=(ROOT/'work/source/NPJB00162/USRDIR/EBOOT.elf').read_bytes()

    def test_skill_fit_executes_and_preserves_full_name_and_native_state(self):
        rows=json.loads((ROOT/'work/translation/en/databases/skills/0000.en.json').read_text('utf8'))['translations']
        names=[r['en'] for r in rows if r.get('en') and '\n' not in r['en'] and len(r['en'])<40]
        self.assertIn('Thunderblade Formation',names)
        for name in names:
            measure=lambda size: width(name,size)
            machine=InventoryMachine(measure,horizontal=22,vertical=22,
                                     bridge_options=dict(fixed_cap=164))
            chosen=machine.run()
            self.assertLessEqual(measure(chosen),164,name)
            if measure(22)<=164:self.assertEqual(chosen,22)

    def test_reported_inventory_names_leave_quantity_and_price_gap(self):
        for name in ('Healing Salve Concentrate','Burial Scripture Scroll',
                     'Cremation Scripture Scroll','Dagger','Protective Gear-like Object+15'):
            for window in (288,320,400):
                for mode in (0,1,2):
                    measure=lambda size: width(name,size)
                    machine=InventoryMachine(measure,horizontal=24,vertical=24,
                        bridge_options=dict(cap_words=layout.ITEM_CAP_WORDS),
                        window_width=window,mode=mode)
                    chosen=machine.run()
                    reserve=128 if mode==1 else 64
                    self.assertLessEqual(24+measure(chosen)+8+reserve,window-16)

    def test_guards_reject_context_drift_before_mutation(self):
        for a,h in layout.GUARDS:
            changed=bytearray(self.original);changed[a-0x10000]^=1
            code=bytearray(b'\0'*16)
            with self.subTest(address=hex(a)),self.assertRaises(ValueError):
                layout.append_code(changed,code)
            self.assertEqual(code,bytearray(b'\0'*16))

    def test_only_reported_row_paths_and_shop_formatters_are_patched(self):
        code=bytearray();changes,audit=layout.append_code(self.original,code)
        self.assertEqual([a+0x10000 for a,_ in changes],
                         [layout.SKILL_SITE,*layout.ITEM_SITES,*layout.SHOP_SITES])
        for row in audit['bridges']:
            entry=int(row['entry'],16)
            for site in row['sites']:
                a=int(site,16)
                self.assertIn((a-0x10000,instruction(branch(a,entry,True))),changes)
        self.assertTrue(audit['skill_description_heading_unchanged'])
        self.assertTrue(audit['full_names_preserved'])
        self.assertFalse(audit['updated_ingame_verification'])

    def test_shop_label_table_preserves_combined_category_membership(self):
        code=bytearray();_,audit=layout.append_code(self.original,code)
        table=int(audit['shop_categories']['table'],16)-layout.CODE_BASE
        expected={15:'All',1:'Blades',4:'Other Weapons',8:'Armor',7:'Robe',
                  9:'Shield/Gloves',10:'Helm/Boots',13:'Accessory',14:'Items'}
        for first,label in expected.items():
            pointer=int.from_bytes(code[table+first*4:table+first*4+4],'big')-layout.CODE_BASE
            self.assertEqual(code[pointer:].split(b'\0')[0].decode(),label)
            self.assertLessEqual(width(label,32),256)
        self.assertEqual(layout.SHOP_GROUPS[6:9],bytes((4,5,6)))


if __name__=='__main__':unittest.main()
