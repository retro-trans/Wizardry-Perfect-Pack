"""Native header/cell execution, long roster values and exact patch scope."""
import unittest
from capstone import Cs,CS_ARCH_PPC,CS_MODE_64,CS_MODE_BIG_ENDIAN
from check_translation import ROOT
from spell_description_layout import width
from test_inventory_layout import InventoryMachine
from test_item_cell_layout import BridgeMachine
import treatment_layout as layout


class HeaderMachine(InventoryMachine):
    def __init__(self):
        super().__init__(lambda size:0,horizontal=24,vertical=24)
        self.payload=layout.header_image(self.start)
        md=Cs(CS_ARCH_PPC,CS_MODE_64|CS_MODE_BIG_ENDIAN)
        self.instructions={i.address:(i.mnemonic,i.op_str) for i in md.disasm(self.payload,self.start)}
        self._write(self.start,self.payload);self.labels=[]

    def _native_call(self,target,return_address):
        if target==0xd15ac:
            x,label=layout.HEADERS[len(self.labels)]
            expected=self.initial_regs[3:13].copy()
            expected[0]+=x-12;expected[2]=self.regs[5]
            if self.regs[3:13]!=expected:raise AssertionError('Header coordinates/flags changed')
            p=self.regs[5];text=bytearray()
            while self.memory[p]:text.append(self.memory[p]);p+=1
            if text.decode()!=label:raise AssertionError('Wrong heading string')
            self.labels.append((x,label))
            # Base hostile-callee model checks all remaining draw/native state.
            self.regs[3:13]=self.initial_regs[3:13]
        super()._native_call(target,return_address)

    def _result(self):
        if (self.regs[1]!=self.initial_regs[1] or self.regs[2]!=self.initial_regs[2]
                or self.regs[4:]!=self.initial_regs[4:] or self.regs[3]!=self.draw_result
                or self.fprs[1:14]!=self.initial_fprs[1:14] or self.cr!=self.initial_cr
                or self.ctr!=self.initial_ctr or self.lr!=self.initial_lr):
            raise AssertionError('Header ABI preservation failed')
        if self._load(self.width_address,4)!=24 or self._load(self.height_address,4)!=24:
            raise AssertionError('Header leaked its font')
        if any(size!=(20,24) for size in self.draws):raise AssertionError('Wrong header font')
        return self.labels


class TreatmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.original=(ROOT/'work/source/NPJB00162/USRDIR/EBOOT.elf').read_bytes()

    def test_individual_headers_and_native_state_survive_hostile_callees(self):
        machine=HeaderMachine();self.assertEqual(machine.run(),list(layout.HEADERS))
        for i,(x,label) in enumerate(layout.HEADERS):
            end=layout.HEADERS[i+1][0] if i+1<len(layout.HEADERS) else 624
            self.assertLessEqual(x+width(label,20),end)

    def test_names_races_and_statuses_fit_before_next_column(self):
        cells=(('Marina',116),('Seraphine',116),('WWWWWWWWWWWW',116),
               ('Porklu',96),('Felpurr',96),('Petrification',96),('Unconscious',96))
        for text,cap in cells:
            measure=lambda size:width(text,size)
            machine=InventoryMachine(measure,horizontal=24,vertical=24,bridge_options=dict(fixed_cap=cap))
            chosen=machine.run();self.assertLessEqual(measure(chosen),cap)
        self.assertLessEqual(52+116,210-max(width(s,24) for s in ('Good','Neut.','Evil'))/2-8)
        self.assertLessEqual(210+max(width(s,24) for s in ('Good','Neut.','Evil'))/2+6,248)
        self.assertLessEqual(288+96+16,400)
        self.assertEqual(440+96+16,624-72)

    def test_levels_and_large_fees_keep_right_edge_with_private_local_slot(self):
        for cap,text in ((32,'9:'),(32,'99:'),(32,'65535:'),(72,'45G'),
                         (72,'9999999G'),(72,'2147483647G')):
            measure=lambda size:width(text,size)
            machine=BridgeMachine(cap,measure,width_slot=layout.WIDTH_SLOT,font_size=24)
            chosen,pixels,calls=machine.run()
            self.assertEqual(pixels,measure(chosen));self.assertLessEqual(pixels,cap)
            self.assertGreaterEqual((40 if cap==32 else 624)-pixels,8 if cap==32 else 552)

    def test_original_context_drift_is_rejected_before_mutation(self):
        for a,h in layout.GUARDS:
            changed=bytearray(self.original);changed[a-0x10000]^=1;code=bytearray()
            with self.assertRaises(ValueError):layout.append_code(changed,code)
            self.assertFalse(code)
        for a,before,after in layout.CHANGES:
            changed=bytearray(self.original);changed[a-0x10000]^=1
            with self.assertRaises(ValueError):layout.append_code(changed,bytearray())

    def test_only_roster_display_changes(self):
        changes,audit=layout.append_code(self.original,bytearray())
        expected={layout.HEADER_SITE,*dict(layout.DRAW_CELLS),*dict(layout.MEASURE_CELLS),
                  *(a for a,_,_ in layout.CHANGES)}
        self.assertEqual({a+0x10000 for a,_ in changes},expected)
        self.assertTrue(audit['fee_calculation_and_selection_unchanged'])
        self.assertFalse(audit['updated_ingame_verification'])


if __name__=='__main__':unittest.main()
