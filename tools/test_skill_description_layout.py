"""Read-only full-corpus checks for the narrow status skill-description panel."""
import unittest
from check_translation import ROOT,read_sources,read_english
from skill_description_layout import is_description,render,width,MAX_LINES,LINE_PITCH,VERTICAL_SIZE
from table_text import collect_all,relocation_plan


class SkillLayoutTests(unittest.TestCase):
    def test_native_panel_contract(self):
        original=(ROOT/'work/source/NPJB00162/USRDIR/EBOOT.elf').read_bytes()
        guards={0x65aa8:'80028b201c6304637c63021438630051786300204e800020',
                0xb76ac:'4bfae3fd',0xb7678:'38800016',0xb767c:'38600016',
                0xb7690:'3929000c',0xb7698:'3bbd002e',0xb76c8:'48019ee5',
                0x53c1d0:'0000012000000100'}
        for address,expected in guards.items():
            value=bytes.fromhex(expected)
            self.assertEqual(original[address-0x10000:address-0x10000+len(value)],value,hex(address))

    def test_all_descriptions_preserve_words_and_fit(self):
        sources,english=read_sources(),read_english();count=0
        for key,row in sources.items():
            if not is_description(row):continue
            text=english[key]['en'];display=render(text);lines=display.split('\n');count+=1
            with self.subTest(id=key):
                self.assertEqual(text.split(),display.split())
                self.assertLessEqual(len(lines),MAX_LINES)
                self.assertLessEqual((len(lines)-1)*LINE_PITCH+VERTICAL_SIZE,190)
                self.assertTrue(all(width(line)<=264 for line in lines))
        self.assertEqual(count,20)

    def test_identify_and_paragraphs(self):
        text=read_english()['DS0023']['en']
        self.assertEqual(render(text),'Identify an unidentified\nitem. Items above the\nuser\'s level are more\nlikely to resist\nidentification.')
        self.assertEqual(render('First paragraph.\n\nSecond paragraph.'),'First paragraph.\n\nSecond paragraph.')
        for text in ('W'*100,'A long description. '*100):
            with self.assertRaises(ValueError):render(text)

    def test_pool_uses_display_copy_and_preserves_other_fields(self):
        english=read_english();groups,_=collect_all();plan,_,_=relocation_plan(groups)
        entries={r['id']:r for r in plan['entries']}
        self.assertEqual(entries['DS0023']['text'],render(english['DS0023']['en']))
        self.assertEqual(entries['DS0022']['text'],english['DS0022']['en'])
        self.assertEqual(entries['DI0000']['text'],english['DI0000']['en'])


if __name__=='__main__':unittest.main()
