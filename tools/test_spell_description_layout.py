"""Read-only corpus and word-preservation checks for spell display copies."""
import unittest
from check_translation import read_sources,read_english
from spell_description_layout import is_description,render,width


class SpellLayoutTests(unittest.TestCase):
    def test_entire_spell_corpus_fits_without_losing_words(self):
        sources,english=read_sources(),read_english();count=0
        for key,row in sources.items():
            if not is_description(row):continue
            text=english[key]['en'];display=render(text);count+=1
            with self.subTest(id=key):
                self.assertEqual(text.split(),display.split())
                self.assertLessEqual(len(display.split('\n')),6)
                self.assertTrue(all(width(line)<=352 for line in display.split('\n')))
        self.assertEqual(count,89)

    def test_paragraphs_survive(self):
        self.assertEqual(render('One paragraph.\n\nAnother paragraph.'),'One paragraph.\n\nAnother paragraph.')

    def test_unbreakable_words_and_excess_height_block_output(self):
        for text in ('W'*100,'A long spell description. '*100):
            with self.assertRaises(ValueError):render(text)


if __name__=='__main__':unittest.main()
