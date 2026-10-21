"""Item preview bounds, native font guards and complete relocated text."""
import unittest
from check_translation import ROOT,read_sources,read_english
from item_description_layout import is_description,render,width,MAX_LINES,LINE_PITCH,FONT_SIZE,HEIGHT
from table_text import collect_all,relocation_plan
from menu_panel_layout import patches


class ItemDescriptionTests(unittest.TestCase):
    def test_native_description_branch_and_font_are_guarded(self):
        original=(ROOT/'work/source/NPJB00162/USRDIR/EBOOT.elf').read_bytes()
        guards={0xf83b0:'7fe3fb784bf5f39160000000388000187c7d1b78386000183bbd01564bfd83c9',
                0xf83f0:'3929000c3863000c',0xf840c:'4bfd91a1'}
        for address,expected in guards.items():
            data=bytes.fromhex(expected)
            self.assertEqual(original[address-0x10000:address-0x10000+len(data)],data,hex(address))
        changes=dict(patches(original)[0])
        self.assertEqual(changes[0xf83bc-0x10000],bytes.fromhex('38800014'))
        self.assertEqual(changes[0xf83c4-0x10000],bytes.fromhex('38600014'))
        for address in (0xf83bc,0xf83c4):
            bad=bytearray(original);bad[address-0x10000]^=1
            with self.assertRaises(ValueError):patches(bad)

    def test_entire_description_corpus_preserves_words_and_fits(self):
        sources,english=read_sources(),read_english();count=0
        for key,row in sources.items():
            if not is_description(row):continue
            text=english[key]['en'];display=render(text);lines=display.split('\n');count+=1
            with self.subTest(id=key):
                self.assertEqual(display.split(),text.split())
                self.assertLessEqual(len(lines),MAX_LINES)
                self.assertTrue(all(width(line)<=224 for line in lines))
                self.assertLessEqual((len(lines)-1)*LINE_PITCH+FONT_SIZE,HEIGHT)
        self.assertEqual(count,76)

    def test_reported_healing_salve_and_overflow_guards(self):
        text=read_english()['DI0297']['en'];display=render(text)
        self.assertEqual(display.split(),text.split())
        self.assertIn('concentrated.',display)
        for text in ('W'*100,'A long item description. '*100):
            with self.assertRaises(ValueError):render(text)

    def test_pool_preserves_item_names_and_special_power_text(self):
        english=read_english();sources=read_sources();groups,_=collect_all();plan,_,_=relocation_plan(groups)
        entries={e['id']:e['text'] for e in plan['entries']}
        for key,row in sources.items():
            if not row['source'].startswith('databases/') or not row['occurrences'] or not all(o.get('member')==0 for o in row['occurrences']):continue
            if english[key]['en'] is None:continue
            expected=render(english[key]['en']) if is_description(row) else english[key]['en']
            self.assertEqual(entries[key],expected,key)


if __name__=='__main__':unittest.main()
