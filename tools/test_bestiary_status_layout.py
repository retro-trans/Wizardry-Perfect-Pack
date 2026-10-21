"""Bestiary status copy boundaries, column bounds and native scope guards."""
import unittest
from bestiary_status_layout import (CHANGES, COPIES, FONT_SIZE, INSET, LABEL_RIGHT,
                                    PANEL_WIDTH, VALUE_LEFT, VALUE_SITES, patches)
from build import DEFERRED_UI_IDS
from check_translation import ROOT, read_english, read_sources
from spell_description_layout import width


class BestiaryStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = (ROOT/'work/source/NPJB00162/USRDIR/EBOOT.elf').read_bytes()

    def test_shared_label_anchor_and_all_nine_values_have_a_gap(self):
        changes, audit = patches(self.original)
        self.assertEqual(len(changes), 10)
        self.assertEqual(len(VALUE_SITES), 9)
        self.assertEqual(audit['column_gap'], 12)
        changed = bytearray(self.original)
        for offset, data in changes:
            changed[offset:offset+len(data)] = data
        # Only inspected horizontal instructions may change in this draw path.
        expected = bytearray(self.original)
        for address, _, after in CHANGES:
            expected[address-0x10000:address-0x10000+4] = after.to_bytes(4, 'big')
        self.assertEqual(changed, expected)

    def test_coordinate_and_copy_guards_reject_mismatched_code(self):
        sites = [row[0] for row in CHANGES]
        for row in COPIES:
            sites.extend(row[2::2])
        for address in sites:
            bad = bytearray(self.original)
            bad[address-0x10000] ^= 1
            with self.subTest(address=hex(address)), self.assertRaises(ValueError):
                patches(bad)

    def test_copied_labels_keep_original_terminators_and_deferred_aliases(self):
        sources, english = read_sources(), read_english()
        expected = {'X2443': 'Gold:', 'X2444': 'EXP:', 'X2438': 'Spell Res:'}
        prior = {'X2443': 'Gold Obtained:', 'X2444': 'Experience Gained:',
                 'X2438': 'Spell Resistance:'}
        for key, size, *_ in COPIES:
            self.assertIn(key, DEFERRED_UI_IDS)
            self.assertEqual(english[key]['en'], expected[key])
            source = sources[key]['ja'].encode('utf8')+b'\0'
            self.assertEqual(len(source), size)
            occurrence = sources[key]['occurrences'][0]
            start = occurrence['offset']
            self.assertEqual(self.original[start:start+size], source)
            self.assertEqual(source[-1], 0)
            self.assertNotIn(b'\0', (prior[key].encode('utf8')+b'\0')[:size])

    def test_all_labels_and_wide_values_fit_native_panel(self):
        english = read_english()
        labels = [english[key]['en'] for key in ('X2439', 'X2440', 'X2441',
                  'X2442', 'X2443', 'X2444', 'X2438')]+['Element:', 'HP:']
        for label in labels:
            with self.subTest(label=label):
                self.assertGreaterEqual(LABEL_RIGHT-width(label, FONT_SIZE), INSET)
        # Includes long numeric rewards/kill counts and signed printf output.
        for value in ('1', '17', 'Earth', 'Thunder', '9999~9999', '500~500',
                      '255', '6', '36', '4294967295', '-2147483648'):
            with self.subTest(value=value):
                self.assertLessEqual(VALUE_LEFT+width(value, FONT_SIZE), PANEL_WIDTH-INSET)


if __name__ == '__main__':
    unittest.main()
