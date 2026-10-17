"""Read-only regression for the original named-message geometry.

Coordinates below come from original executable data and instructions, not
scaled screenshot measurements. The font-based paragraph checks reproduce the
three reported Beatrix passages and compare the old896 budget with native800.
"""
import json
from pathlib import Path
import re
import struct
import unittest

from fontTools.ttLib import TTFont
from check_vwf import cache_width, pen_positions

ROOT = Path(__file__).resolve().parents[1]
FONT_SIZE = 32
FRAME_X, FRAME_Y, FRAME_WIDTH, FRAME_HEIGHT = 160, 506, 960, 160
BODY_X, BODY_Y, RIGHT_INSET = 128, 32, 32
NAMED_WIDTH = FRAME_WIDTH-BODY_X-RIGHT_INSET
CONTROL = re.compile(r'@(?:[0-9]+r|RS)')
PARAGRAPHS = (
    (('E6858', 'E6859', 'E6860'), (855, 892, 847, 280), (769, 792, 700, 613)),
    (('E6872', 'E6873'), (861, 807, 88), (763, 717, 276)),
    (('E6875', 'E6876'), (888, 858, 292), (744, 645, 649)),
)
GUARDS = (
    # Show(window,0x22,...) sets per-window kind to low three flag bits:2.
    (0xde070, '548a0036548b077e'),
    (0xde340, '38800022'),
    (0xde98c, '801a010c2f800000419c00b82f800001419d01a4'),
    (0xdeb40, '2f800002409eff082f970000409d0074'),
    # Named text: set32x32, y=windowY+32+32*row, x=windowX+128.
    (0xdeb60, '38600020388000204bff1c2d600000008178000081390000396b002057e32834392900807c635a145529053e5463622665290a003c8000647c634b787b65002060840080786300203bff00014bff2a01'),
    # Wide-message resource lookup and draw-command x160/y506.
    (0xdee84, '8282a79438800048807400004807b0a9'),
    (0xdf1f4, '380000a0392001fab01f000cb13f000e93df0010933f0008'),
    # The setter records its exact requested horizontal/vertical overrides.
    (0xd0794, '8122a60c380000013d29000390898400980983f8906983fc4e800020'),
)


def source_data():
    return (ROOT/'work/source/NPJB00162/USRDIR/EBOOT.elf').read_bytes()


def english_rows():
    return {row['id']: row['en']
            for path in (ROOT/'work/translation/en/events').glob('*.en.json')
            for row in json.loads(path.read_text(encoding='utf8'))['translations']}


def font_advances():
    with TTFont(ROOT/'work/source/NPJB00162/USRDIR/FOT-UtrilloPro-DB.otf') as font:
        return {chr(c): cache_width(font['hmtx'][glyph][0], font['head'].unitsPerEm)
                for c, glyph in font.getBestCmap().items()}


def measured(text, advances):
    return int(pen_positions(CONTROL.sub('', text), FONT_SIZE, advances)[1])


def paragraph_lines(text, width, advances):
    """Independent greedy model for these short, ordinary-word paragraphs."""
    lines, line = [], ''
    for word in text.split():
        if measured(word, advances) > width:
            raise ValueError('Unexpected overwide individual word in regression passage')
        trial = line+' '+word if line else word
        if measured(trial, advances) > width or len(trial.encode('utf8')) > 120:
            lines.append(line); line = word
        else:
            line = trial
    if line: lines.append(line)
    return lines


class NamedDialogueGeometry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = source_data()
        cls.rows = english_rows()
        cls.advances = font_advances()

    def test_original_named_callback_instructions_are_exact(self):
        for address, expected in GUARDS:
            with self.subTest(address=hex(address)):
                expected = bytes.fromhex(expected)
                self.assertEqual(self.original[address-0x10000:address-0x10000+len(expected)], expected)
        self.assertEqual(0x22 & 7, 2)

    def test_resource72_dimensions_and_callback_match_the_draw_path(self):
        # Descriptor FILE0x52D090 / VA0x53D090, native records88bytes each.
        descriptor = self.original[0x52d090:0x52d0b4]
        self.assertEqual(descriptor.hex(), '0040dab000000000000003c0000000a00040dab8000003c0000000a00046909800000000')
        words = struct.unpack('>9I', descriptor)
        self.assertEqual(words[2:4], (FRAME_WIDTH, FRAME_HEIGHT))
        self.assertEqual(words[5:7], (FRAME_WIDTH, FRAME_HEIGHT))
        self.assertEqual(words[7], 0x469098)
        self.assertEqual(struct.unpack_from('>II', self.original, words[7]-0x10000), (0xde91c, 0x488530))
        for address, expected in ((words[0], b'ui72\0'), (words[4], b'win_black53_1\0')):
            self.assertEqual(self.original[address-0x10000:address-0x10000+len(expected)], expected)
        self.assertEqual((FRAME_X+BODY_X, FRAME_Y+BODY_Y), (288, 538))
        self.assertEqual(NAMED_WIDTH, 800)
        self.assertEqual(FRAME_X+BODY_X+NAMED_WIDTH, FRAME_X+FRAME_WIDTH-RIGHT_INSET)

    def test_measurement_and_native_font_draw_use_the_same_font_object(self):
        # Presenter/de9d8 font TOC-588c and D15AC real-font TOC-59d0.
        font_for_measure = struct.unpack_from('>I', self.original, 0x472ca4)[0]
        font_for_draw = struct.unpack_from('>I', self.original, 0x472b60)[0]
        self.assertEqual(font_for_measure, 0x5482210)
        self.assertEqual(font_for_draw, font_for_measure)

    def test_old896_lines_overflow_the_named_window_with_all_words_preserved(self):
        for ids, old_widths, new_widths in PARAGRAPHS:
            with self.subTest(ids=ids):
                text = ' '.join(self.rows[key] for key in ids)
                old = paragraph_lines(text, 896, self.advances)
                new = paragraph_lines(text, NAMED_WIDTH, self.advances)
                self.assertEqual(tuple(measured(line, self.advances) for line in old), old_widths)
                self.assertEqual(tuple(measured(line, self.advances) for line in new), new_widths)
                self.assertTrue(any(measured(line, self.advances) > NAMED_WIDTH for line in old))
                self.assertTrue(any(measured(line, self.advances) > FRAME_WIDTH-BODY_X for line in old))
                self.assertTrue(all(measured(line, self.advances) <= NAMED_WIDTH for line in new))
                normalize = lambda value: ''.join(CONTROL.sub('', value).split())
                self.assertEqual(normalize(' '.join(new)), normalize(text))
                self.assertTrue(all(len(line.encode('utf8')) <= 120 for line in new))
                # Native three-line pages remain96px high inside160px frame.
                for index in range(0, len(new), 3):
                    page = new[index:index+3]
                    self.assertLessEqual(BODY_Y+len(page)*FONT_SIZE, FRAME_HEIGHT)

    def test_ordinary_presenter_budget_matches_named_geometry(self):
        source = (ROOT/'tools/dialogue_layout.c').read_text(encoding='utf8')
        ordinary = source.split('EXPORT int present_dialogue(', 1)[1].split('EXPORT int present_battle(', 1)[0]
        match = re.search(r'present_message\([^;]*?,\s*(\d+)\s*,\s*0x22\s*,\s*0\)', ordinary)
        self.assertIsNotNone(match)
        self.assertEqual(int(match[1]), NAMED_WIDTH)


if __name__ == '__main__': unittest.main()
