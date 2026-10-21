"""Battle Record native scope, fixed-copy safety and all counter bounds."""
import struct
import unittest
from battle_record_layout import (CHANGES,COPIES,LOOP,TYPE_IDS,STRIDE,LABEL_RIGHT,
                                   VALUE_LEFT,PANEL_WIDTH,INSET,FONT_SIZE,patches)
from build import DEFERRED_UI_IDS
from check_translation import ROOT,read_sources,read_english
from spell_description_layout import width


class RecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=(ROOT/'work/source/NPJB00162/USRDIR/EBOOT.elf').read_bytes()
        cls.sources=read_sources();cls.english=read_english()

    def test_all_thirteen_types_and_maximum_counts_fit_three_columns(self):
        for index,key in enumerate(TYPE_IDS):
            pointer=struct.unpack_from('>I',self.original,0x450c38-0x10000+4*index)[0]
            self.assertIn(pointer,{o.get('address') for o in self.sources[key]['occurrences']})
            label=self.english[key]['en']+':'
            row,col=divmod(index,3)
            left=col*STRIDE+LABEL_RIGHT-width(label,FONT_SIZE)
            value_left=col*STRIDE+VALUE_LEFT
            with self.subTest(id=key):
                self.assertGreaterEqual(left,col*STRIDE+INSET)
                self.assertEqual(value_left-(col*STRIDE+LABEL_RIGHT),12)
                self.assertLessEqual(value_left+width('999999',FONT_SIZE),min((col+1)*STRIDE,PANEL_WIDTH-INSET))
                self.assertLessEqual(64+row*32+FONT_SIZE,240)

    def test_summary_and_heading_values_keep_a_gap_at_native_caps(self):
        for key,end,start,value in [('X2435',192,204,'9999'),('X2436',528,540,'9999'),('X2437',864,876,'9999999')]:
            self.assertGreaterEqual(end-width(self.english[key]['en'],32),INSET)
            self.assertEqual(start-end,12)
            self.assertLessEqual(start+width(value,32),PANEL_WIDTH-INSET)
        for key,value in [('X2432','4294967295'),('X2434','9999:59:59')]:
            self.assertLessEqual(16+width(self.english[key]['en'],32)+12+width(value,32),PANEL_WIDTH-INSET)

    def test_copied_summary_labels_retain_source_terminators(self):
        for key,size,*_ in COPIES:
            self.assertIn(key,DEFERRED_UI_IDS)
            encoded=self.sources[key]['ja'].encode('utf8')+b'\0'
            self.assertEqual(len(encoded),size)
            start=self.sources[key]['occurrences'][0]['offset']
            self.assertEqual(self.original[start:start+size],encoded)
        self.assertEqual(self.english['X2436']['en'],'Wipeouts:')
        self.assertEqual(self.english['X2437']['en'],'Chests:')

    def test_all_positions_fonts_copies_and_loop_are_guarded(self):
        changes,audit=patches(self.original)
        self.assertEqual(len(changes),16)
        self.assertEqual(audit['monster_font_size'],24)
        self.assertEqual(audit['summary_font_size'],32)
        sites=[a for a,_,_ in CHANGES]+[LOOP[0]]
        for row in COPIES:sites.extend(row[2::2])
        for address in sites:
            bad=bytearray(self.original);bad[address-0x10000]^=1
            with self.subTest(address=hex(address)),self.assertRaises(ValueError):patches(bad)


if __name__=='__main__':unittest.main()
