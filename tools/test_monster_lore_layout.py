"""Bestiary lore dimensions, complete text and isolated display reflow."""
import unittest
from check_translation import ROOT,read_sources,read_english
from monster_lore_layout import is_lore,render,width,MAX_LINES,LINE_PITCH,FONT_SIZE,HEIGHT
from table_text import collect_all,relocation_plan
from menu_panel_layout import patches


class LoreLayoutTests(unittest.TestCase):
    def test_native_lore_font_and_panel_offsets_are_guarded(self):
        original=(ROOT/'work/source/NPJB00162/USRDIR/EBOOT.elf').read_bytes()
        guards={0x100560:'3860001c3880001c4bfd022d',0x100580:'38a90519',
                0x100594:'3929001038630010',0x1005b0:'4bfd0ffd'}
        for address,expected in guards.items():
            raw=bytes.fromhex(expected)
            self.assertEqual(original[address-0x10000:address-0x10000+len(raw)],raw,hex(address))
        changes=dict(patches(original)[0])
        self.assertEqual(changes[0x100560-0x10000],bytes.fromhex('38600016'))
        self.assertEqual(changes[0x100564-0x10000],bytes.fromhex('38800016'))
        for address in (0x100560,0x100564):
            bad=bytearray(original);bad[address-0x10000]^=1
            with self.assertRaises(ValueError):patches(bad)

    def test_all_lore_keeps_words_paragraphs_and_fits_both_dimensions(self):
        sources,english=read_sources(),read_english();count=0
        for key,row in sources.items():
            if not is_lore(row):continue
            text=english[key]['en'];display=render(text);lines=display.split('\n');count+=1
            with self.subTest(id=key):
                self.assertEqual(display.split(),text.split())
                self.assertEqual(display.strip().count('\n\n'),text.strip().count('\n\n'))
                self.assertLessEqual(len(lines),MAX_LINES)
                self.assertTrue(all(width(line)<=288 for line in lines))
                self.assertLessEqual((len(lines)-1)*LINE_PITCH+FONT_SIZE,HEIGHT)
        self.assertEqual(count,200)

    def test_reported_goblin_and_oversize_inputs(self):
        text=read_english()['DM0041']['en'];display=render(text)
        self.assertIn('labyrinth.',display)
        self.assertEqual(display.split(),text.split())
        for text in ('W'*100,'Long bestiary lore. '*300):
            with self.assertRaises(ValueError):render(text)

    def test_pool_reflows_lore_and_preserves_names_and_abilities(self):
        english=read_english();sources=read_sources();groups,_=collect_all();plan,_,_=relocation_plan(groups)
        entries={e['id']:e['text'] for e in plan['entries']}
        for key,row in sources.items():
            if not row['occurrences'] or not all(o.get('member')==2 for o in row['occurrences']):continue
            if english[key]['en'] is None:continue
            expected=render(english[key]['en']) if is_lore(row) else english[key]['en']
            self.assertEqual(entries[key],expected,key)


if __name__=='__main__':unittest.main()
