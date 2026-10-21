"""Quest-panel bounds, text preservation and relocated display integration."""
import unittest
from check_translation import ROOT,read_sources,read_english
from quest_description_layout import is_description,render,width,MAX_LINES,LINE_PITCH,FONT_SIZE
from table_text import collect_all,relocation_plan


class QuestLayoutTests(unittest.TestCase):
    def test_native_request_and_objective_panel_contract(self):
        original=(ROOT/'work/source/NPJB00162/USRDIR/EBOOT.elf').read_bytes()
        guards={0x998ec:'3860001838800018',0x99960:'48036e35',
                0x99970:'3929000c38630028',0x99984:'38bf022a',0x9999c:'48037c11',
                0x999c4:'3860001838800018',0x999dc:'3929000c38630028',0x999f0:'38bf00d8'}
        for address,expected in guards.items():
            raw=bytes.fromhex(expected)
            self.assertEqual(original[address-0x10000:address-0x10000+len(raw)],raw,hex(address))

    def test_entire_quest_corpus_fits_without_losing_words(self):
        sources,english=read_sources(),read_english();count=0
        for key,row in sources.items():
            if not is_description(row):continue
            text=english[key]['en'];display=render(text);count+=1
            with self.subTest(id=key):
                self.assertEqual(display.split(),text.split())
                self.assertLessEqual(len(display.splitlines()),MAX_LINES)
                self.assertTrue(all(width(line)<=640 for line in display.splitlines()))
                self.assertLessEqual((len(display.splitlines())-1)*LINE_PITCH+FONT_SIZE,74)
        self.assertEqual(count,108)

    def test_reported_objective_and_overflow_guards(self):
        text=read_english()['DQ0003']['en'];display=render(text)
        self.assertIn('grizzlies',display);self.assertIn('Fiore',display)
        self.assertEqual(text.split(),display.split())
        self.assertLessEqual(len(display.splitlines()),3)
        for text in ('W'*100,'A long quest request. '*100):
            with self.assertRaises(ValueError):render(text)

    def test_pool_uses_display_copy_and_keeps_title_and_client(self):
        english=read_english();groups,_=collect_all();plan,_,_=relocation_plan(groups)
        rows={r['id']:r for r in plan['entries']}
        self.assertEqual(rows['DQ0003']['text'],render(english['DQ0003']['en']))
        for key in ('DQ0000','DQ0001'):
            self.assertEqual(rows[key]['text'],english[key]['en'])


if __name__=='__main__':unittest.main()
