"""Race-grid containment and bonus-note/font/permission regressions."""
import json
import unittest
from capstone import Cs,CS_ARCH_PPC,CS_MODE_64,CS_MODE_BIG_ENDIAN
from check_translation import ROOT
from spell_description_layout import width
from test_item_cell_layout import BridgeMachine
from test_inventory_layout import InventoryMachine
import item_popup_footer_layout as layout


class MultilineMachine(InventoryMachine):
    def __init__(self,text):
        super().__init__(None,horizontal=20,vertical=20)
        self.source=text.encode()+b'\0'
        self.source_address=0x123400
        self._write(self.source_address,self.source)
        self.regs[3:7]=[self.font_object,self.source_address,20,20]
        self.initial_regs=self.regs[:]
        decoder=Cs(CS_ARCH_PPC,CS_MODE_64|CS_MODE_BIG_ENDIAN)
        payload=layout.multiline_measure(self.start)
        decoded=list(decoder.disasm(payload,self.start))
        assert len(decoded)*4==len(payload)
        self.instructions={i.address:(i.mnemonic,i.op_str) for i in decoded}
        self.lines=[]

    def _store(self,address,value,size=8):
        if not self.stack_start-0x1400<=address<=self.stack_start-size:
            raise AssertionError('Measurement wrote outside private frame')
        self._write(address,(value&((1<<(size*8))-1)).to_bytes(size,'big'))

    def _native_call(self,target,return_address):
        assert target==0x164adc
        assert self.regs[3]==self.font_object and self.regs[5:7]==[20,20]
        address=self.regs[4];data=bytearray()
        while self.memory[address]:
            data.append(self.memory[address]);address+=1
        self.lines.append(data.decode())
        result=int(width(self.lines[-1],20))
        for offset in range(0x10,0x78,8):self._store(self.regs[1]+offset,0xbad00+offset)
        for register in [0,2,*range(3,13)]:self.regs[register]=0xdead000+register
        self.regs[3]=result
        self.cr,self.ctr,self.lr=0x12345678,0xbadc0ffee,return_address

    def _result(self):
        assert self.regs[1:3]==self.initial_regs[1:3]
        assert self.regs[4:]==self.initial_regs[4:]
        assert (self.cr,self.ctr,self.lr)==(self.initial_cr,self.initial_ctr,self.initial_lr)
        assert bytes(self.memory[self.source_address+i] for i in range(len(self.source)))==self.source
        assert bytes(self.memory[self.stack_start+i] for i in range(len(self.caller_before)))==self.caller_before
        return self.regs[3]


class PopupFooterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.original=(ROOT/'work/source/NPJB00162/USRDIR/EBOOT.elf').read_bytes()

    def test_all_seven_races_fit_left_of_bonus_notes(self):
        rows=(('Human','Elf','Dwarf'),('Gnome','Porklu','Fairy','Felpurr'))
        for row in rows:
            previous=80
            for col,text in enumerate(row):
                size,pixels,_=BridgeMachine(80,lambda size:width(text,size)).run()
                center=136+96*col
                self.assertLessEqual(pixels,80)
                self.assertGreaterEqual(center-pixels/2-previous,8)
                self.assertLessEqual(center+pixels/2,464)
                previous=center+pixels/2
        self.assertEqual(496-464,32)

    def test_reported_bonus_text_retains_words_and_fits_native_font(self):
        samples=('Spell Pwr+ Spell Res+\nSpecial Res+',
                 'Spell Pwr+ Thief+ Spell Res+ Special Res+\nLevitate Enc.+ Enc.-',
                 'Spell/Special Resistance+ 32768\nSpecial Res+',
                 'A longer line '*8+'\nSecond line')
        for text in samples:
            # The helper supplies the widest line to the emitted fitter.
            measure=lambda size:max(width(line,size) for line in text.split('\n'))
            machine=InventoryMachine(measure,horizontal=20,vertical=20,
                                     bridge_options=dict(fixed_cap=416))
            chosen=machine.run();self.assertLessEqual(measure(chosen),416)

    def test_emitted_multiline_helper_measures_every_line_and_preserves_caller(self):
        samples=('A long first line with several words\nX',
                 'X\nA long second line with several words','Longest line\n',
                 'A\n\nB','@0rSpell Pwr+ @0rSpell Res+\nSpecial Res+','Single line','')
        for text in samples:
            with self.subTest(text=text):
                machine=MultilineMachine(text)
                self.assertEqual(machine.run(),max(width(line,20) for line in text.split('\n')))
                self.assertEqual(machine.lines,text.split('\n'))

    def test_bonus_abbreviations_are_pointer_scoped(self):
        doc=json.loads((ROOT/'work/translation/en/executable/0240.en.json').read_text('utf8'))
        expected={'X0252':(0x451144,'Spell Pwr+'),'X0253':(0x45114c,'Thief+'),
                  'X0254':(0x451154,'Spell Res+'),'X0255':(0x45115c,'Special Res+'),
                  'X0256':(0x451164,'Levitate'),'X0257':(0x451174,'Enc.+'),
                  'X0258':(0x45117c,'Enc.-')}
        for row in doc['translations']:
            if row['id'] in expected:
                pointer,text=expected[row['id']];override=row['reference_overrides'][0]
                self.assertEqual(int(override['pointer_offset'],16),pointer-0x10000)
                self.assertEqual(override['en'],text)
                self.assertNotEqual(row['en'],text)
                self.assertEqual(int.from_bytes(self.original[pointer-0x10000:pointer-0x10000+4],'big'),int(override['source_address'],16))
        # All three reported positive traits fit the formatter's 64-byte
        # temporary line, including native color prefixes, spaces and NUL.
        reported='@0rSpell Pwr+ @0rSpell Res+ @0rSpecial Res+ '
        self.assertLessEqual(len(reported.encode())+1,64)

    def test_guards_fail_atomically_and_changes_are_display_only(self):
        for a,h in layout.GUARDS:
            changed=bytearray(self.original);changed[a-0x10000]^=1;code=bytearray()
            with self.assertRaises(ValueError):layout.append_code(changed,code)
            self.assertFalse(code)
        for a,before,after in layout.CHANGES:
            changed=bytearray(self.original);changed[a-0x10000]^=1
            with self.assertRaises(ValueError):layout.append_code(changed,bytearray())
        changes,audit=layout.append_code(self.original,bytearray())
        self.assertEqual({a+0x10000 for a,_ in changes},{layout.NOTE_SITE,*(a for a,_,_ in layout.CHANGES)})
        self.assertTrue(audit['native_race_order_and_permissions_preserved'])
        self.assertTrue(audit['bonus_flags_colors_and_values_preserved'])
        self.assertFalse(audit['updated_ingame_verification'])


if __name__=='__main__':unittest.main()
