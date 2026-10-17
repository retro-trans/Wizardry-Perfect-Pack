"""Guard context-specific labels against shared-source translation collisions."""
import copy
import io
import struct
import unittest
from unittest.mock import patch

from elftools.elf.elffile import ELFFile
from build import executable_patch
from check_translation import ROOT, read_sources, read_english, validate
from executable_context import reference_overrides, collect_reference_overrides
from reuse_translation import reusable_exact_match


class ContextMetadataTests(unittest.TestCase):
    def setUp(self):
        self.source = dict(id='T', source='executable', ja='Label',
                           occurrences=[dict(address=0x2000)])
        self.decision = dict(en='Default', status='translated', output_file='fixture',
                             reference_overrides=[dict(pointer_offset='0x1000',
                             source_address='0x2000', en='Context', context='Other meaning')])

    def test_metadata_requires_guarded_reference_and_meaning(self):
        self.assertEqual(reference_overrides(self.source, self.decision)[0x1000]['en'], 'Context')
        for field, value in (('pointer_offset', '0x1001'), ('pointer_offset', 4096),
                             ('source_address', '0x2004'), ('en', ''), ('en', 'x\0'),
                             ('context', ' ')):
            with self.subTest(field=field, value=value):
                bad = copy.deepcopy(self.decision)
                bad['reference_overrides'][0][field] = value
                with self.assertRaises(ValueError):
                    reference_overrides(self.source, bad)

    def test_overrides_cannot_target_other_source_types_or_exclusions(self):
        with self.assertRaises(ValueError):
            reference_overrides(dict(self.source, source='events'), self.decision)
        with self.assertRaises(ValueError):
            reference_overrides(self.source, dict(self.decision, en=None))

    def test_duplicate_reference_rejected_within_and_across_rows(self):
        bad = copy.deepcopy(self.decision)
        bad['reference_overrides'] *= 2
        with self.assertRaises(ValueError):
            reference_overrides(self.source, bad)
        with self.assertRaises(ValueError):
            collect_reference_overrides({'T': self.source, 'U': dict(self.source, id='U')},
                                        {'T': self.decision, 'U': self.decision})

    def test_reference_text_preserves_controls_and_line_count(self):
        source = dict(self.source, ja='@1rLabel@RS\n%d')
        decision = copy.deepcopy(self.decision)
        decision['en'] = '@1rDefault@RS\n%d'
        errors = validate({'T': source}, {'T': decision})['errors']
        self.assertEqual({e['error'] for e in errors}, {
            'controls changed in reference translation',
            'printf changed in reference translation',
            'Newline count changed in reference translation'})

    def test_reuse_rejects_contextual_or_conflicting_matches(self):
        plain = dict(en='Default', status='translated')
        self.assertTrue(reusable_exact_match([plain, plain]))
        self.assertFalse(reusable_exact_match([plain, self.decision]))
        self.assertFalse(reusable_exact_match([plain, dict(plain, en='Other')]))
        self.assertFalse(reusable_exact_match([]))


class OriginalExecutableContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = (ROOT/'work/source/NPJB00162/USRDIR/EBOOT.elf').read_bytes()
        keys = {'X0179', 'X0110', 'X0103'}
        cls.sources = {k: v for k, v in read_sources().items() if k in keys}
        cls.english = {k: v for k, v in read_english().items() if k in keys}

    def build_subset(self, english=None):
        # Literal-label renderer hooks are unrelated to this pointer regression.
        with patch('ui_literal_text.collect', return_value=[]):
            return executable_patch(self.data, self.sources, english or self.english)

    def test_actual_weapon_class_race_and_monster_references_are_separated(self):
        patched, audit = self.build_subset()
        segments = list(ELFFile(io.BytesIO(patched)).iter_segments())

        def text_at_reference(offset):
            address = struct.unpack_from('>I', patched, offset)[0]
            for segment in segments:
                if segment['p_vaddr'] <= address < segment['p_vaddr']+segment['p_filesz']:
                    pos = segment['p_offset']+address-segment['p_vaddr']
                    return patched[pos:patched.index(b'\0', pos)].decode('utf8')
            self.fail('Reference points outside loaded data')

        weapons = [0x441194, 0x44165c, 0x44166c, 0x44167c, 0x44168c,
                   0x44169c, 0x4416ac, 0x4416bc, 0x4416cc, 0x4416dc,
                   0x441ffc, 0x446d50, 0x446db0]
        for offset in weapons:
            self.assertEqual(text_at_reference(offset), 'Swords', hex(offset))
        expected = {0x440e1c: 'Kns', 0x440e00: 'Mag', 0x440c2c: 'Magic',
                    0x446458: 'Magic', 0x440f00: 'Felpurr',
                    0x440c10: 'Beast', 0x446464: 'Beast'}
        for offset, text in expected.items():
            self.assertEqual(text_at_reference(offset), text, hex(offset))
        self.assertEqual(len(audit['reference_overrides']), 3)

    def test_expected_old_pointer_must_match(self):
        bad = copy.deepcopy(self.english)
        bad['X0179']['reference_overrides'][0]['source_address'] = '0x3ed030'
        with self.assertRaisesRegex(ValueError, 'context guard mismatch'):
            self.build_subset(bad)

    def test_outside_verified_pointer_ranges_rejected(self):
        bad = copy.deepcopy(self.english)
        bad['X0179']['reference_overrides'][0]['pointer_offset'] = '0x1000'
        with self.assertRaisesRegex(ValueError, 'outside the verified pointer ranges'):
            self.build_subset(bad)


if __name__ == '__main__':
    unittest.main()
