"""Read-only regression tests for original PPU linkage-area compatibility."""
import struct
import unittest
from pathlib import Path

from capstone import Cs, CS_ARCH_PPC, CS_MODE_64, CS_MODE_BIG_ENDIAN
from runtime_text import CODE_BASE, HOOKS, branch, make_code, resolver_code

ROOT=Path(__file__).resolve().parents[1]


class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=(ROOT/'work/source/NPJB00162/USRDIR/EBOOT.elf').read_bytes()
        cls.resolver,cls.entry=resolver_code(ROOT/'work/output/text_resolver.o')
        cls.code,cls.patches,cls.audit=make_code(cls.original,cls.resolver,cls.entry,0x55c0000,1065)
        cls.md=Cs(CS_ARCH_PPC,CS_MODE_64|CS_MODE_BIG_ENDIAN)

    def test_original_renderer_linkage_area_cannot_overwrite_wrapper_return(self):
        for (target,register,expected),hook in zip(HOOKS,self.audit['hooks']):
            native=list(self.md.disasm(expected,target))
            # Original stdu allocates a frame; std r0 saves its LR at caller+16.
            frame=struct.unpack_from('>I',expected)[0]&0xfffc
            frame=frame-65536 if frame&0x8000 else frame
            native_lr_displacement=struct.unpack_from('>I',expected,12)[0]&0xfffc
            self.assertEqual(frame+native_lr_displacement,16)
            wrapper=int(hook['wrapper'],16)-CODE_BASE
            code=self.code[wrapper:wrapper+0x100]
            instructions=[(i.mnemonic,i.op_str) for i in self.md.disasm(code,int(hook['wrapper'],16))]
            self.assertIn(('std','r0, 0x100(r1)'),instructions)
            self.assertIn(('ld','r0, 0x100(r1)'),instructions)
            self.assertNotIn(('std','r0, 0x10(r1)'),instructions)

    def test_direct_branch_targets(self):
        for (offset,payload),hook in zip(self.patches,self.audit['hooks']):
            ins=list(self.md.disasm(payload,offset+0x10000))
            self.assertEqual(ins[0].mnemonic,'b')
            self.assertEqual(int(ins[0].op_str,16),int(hook['wrapper'],16))
            self.assertTrue(all(i.mnemonic=='nop' for i in ins[1:]))

    def test_unreachable_branches_are_rejected(self):
        with self.assertRaises(ValueError):branch(0x164510,0x55b0000)

    def test_no_shared_expansion_storage(self):
        self.assertFalse(self.audit['shared_mutable_buffer'])
        self.assertLess(0x200+self.audit['expansion_capacity'],self.audit['stack_frame_bytes'])

    def test_alias_arguments_preserve_original_draw_arguments(self):
        code,patches,audit=make_code(self.original,self.resolver,self.entry,0x55c0000,1453,
                                    alias_address=0x55d1230,alias_count=9)
        for hook in audit['hooks']:
            start=int(hook['wrapper'],16)
            decoded=[(i.mnemonic,i.op_str) for i in self.md.disasm(code[start-CODE_BASE:start-CODE_BASE+0x1c0],start)]
            self.assertIn(('lis','r8, 0x55d'),decoded)
            self.assertIn(('ori','r8, r8, 0x1230'),decoded)
            self.assertIn(('li','r9, 9'),decoded)
            self.assertIn(('std','r8, 0x48(r1)'),decoded)
            self.assertIn(('ld','r8, 0x48(r1)'),decoded)
            self.assertIn(('std','r9, 0x50(r1)'),decoded)
            self.assertIn(('ld','r9, 0x50(r1)'),decoded)

    def test_new_game_draw_uses_string_argument_not_x_coordinate(self):
        # Actual caller at 0xd122c sets r4=x (107 in the crash), r5=y,
        # and r6=the "Front R" label. Trace this against the original bytes,
        # independently of the generated hook's chosen register.
        caller=list(self.md.disasm(self.original[0xd120c-0x10000:0xd1230-0x10000],0xd120c))
        self.assertEqual((caller[0].mnemonic,caller[0].op_str),('mr','r4, r27'))
        self.assertEqual((caller[2].mnemonic,caller[2].op_str),('mr','r6, r28'))
        self.assertEqual((caller[-1].mnemonic,caller[-1].op_str),('bl','0x164ea4'))
        # Callee saves r6 in r23, then r30, and dereferences r30 as UTF-8.
        for at,expected in [(0x164f00,('mr','r23, r6')),
                            (0x165084,('mr','r30, r23')),
                            (0x165098,('clrldi','r3, r30, 0x20')),
                            (0x16509c,('lbz','r0, 0(r3)'))]:
            ins=next(self.md.disasm(self.original[at-0x10000:at-0x10000+4],at))
            self.assertEqual((ins.mnemonic,ins.op_str),expected)
        hook=next(h for h in self.audit['hooks'] if h['function']=='0x164ea4')
        start=int(hook['wrapper'],16)
        instructions=[(i.mnemonic,i.op_str) for i in self.md.disasm(self.code[start-CODE_BASE:start-CODE_BASE+0x100],start)]
        self.assertIn(('mr','r3, r6'),instructions)
        self.assertNotIn(('mr','r3, r4'),instructions)
        self.assertIn(('std','r3, 0x38(r1)'),instructions)  # resolved r6 slot

    def test_dialogue_bridge_preserves_native_continuations_and_condition(self):
        from compile_dialogue import dialogue_code
        code,patches,audit=make_code(self.original,self.resolver,self.entry,0x55c0000,1453,
                                    dialogue_code(ROOT/'work/output/dialogue_layout.o'))
        bridge=int(audit['dialogue']['bridge'],16)
        decoded=[(i.mnemonic,i.op_str) for i in self.md.disasm(code[bridge-CODE_BASE:],bridge)]
        for target in ('0xa5fd0','0xa5e98','0xa5fc0'):
            self.assertIn(('b',target),decoded)
        self.assertEqual(sum(m=='mtcrf' and op=='0xff, r0' for m,op in decoded),2)
        for expected in [('mr','r3, r23'),('mr','r4, r31'),('ld','r6, 0x1c8(r1)'),
                         ('lwz','r5, -0x588c(r2)'),('lwz','r5, 0(r5)'),
                         ('std','r0, 0x1c0(r1)'),('ld','r0, 0x1c0(r1)')]:
            self.assertIn(expected,decoded)
        # Native event setup establishes the CR4 mode and the complete buffer;
        # the hook runs after actor substitutions, not on isolated source rows.
        at=0xa5c50
        ins=next(self.md.disasm(self.original[at-0x10000:at-0x10000+4],at))
        self.assertEqual((ins.mnemonic,ins.op_str),('cmpwi','cr4, r28, 0'))
        at=0xa5e94
        patched=next(p for off,p in patches if off==at-0x10000)
        ins=next(self.md.disasm(patched,at))
        self.assertEqual((ins.mnemonic,ins.op_str),('b',hex(bridge)))

    def test_dialogue_hook_rejects_different_original_branch(self):
        from compile_dialogue import dialogue_code
        changed=bytearray(self.original);changed[0xa5e94-0x10000]^=1
        with self.assertRaisesRegex(ValueError,'Dialogue continuation'):
            make_code(changed,self.resolver,self.entry,0x55c0000,1453,
                      dialogue_code(ROOT/'work/output/dialogue_layout.o'))

    def test_battle_bridge_expands_before_layout_and_keeps_original_final_wait(self):
        from compile_dialogue import message_code
        code,patches,audit=make_code(self.original,self.resolver,self.entry,0x55c0000,1453,
                                    message_code(ROOT/'work/output/dialogue_layout.o'),0x55d0000,21)
        battle=audit['battle'];start=int(battle['bridge'],16)
        decoded=[(i.mnemonic,i.op_str) for i in self.md.disasm(code[start-CODE_BASE:],start)]
        self.assertEqual(battle['stack_frame_bytes'],0x4000)
        self.assertTrue(battle['expands_item_names_before_layout'])
        for expected in [('addi','r4, r1, 0x200'),('li','r5, 0x3000'),('mr','r4, r3'),
                         ('li','r3, 0'),('lwz','r5, -0x588c(r2)'),('lwz','r5, 0(r5)'),
                         ('b','0xde6d8'),('std','r0, 0x1c0(r1)'),('ld','r0, 0x1c0(r1)')]:
            self.assertIn(expected,decoded)
        self.assertEqual(sum(m=='bctrl' for m,op in decoded[:decoded.index(('b','0xde6d8'))]),2)
        # Only the Show call changes in the caller; its final native wait and
        # continuation still execute after the helper's final displayed page.
        changed=bytearray(self.original)
        for offset,value in patches:changed[offset:offset+len(value)]=value
        self.assertEqual(changed[0x21864-0x10000:0x21874-0x10000],self.original[0x21864-0x10000:0x21874-0x10000])

    def test_battle_caller_guard_rejects_each_context_byte_before_mutation(self):
        from battle_layout import append_code,EXPECTED_CONTEXT,SITE
        for delta in range(len(EXPECTED_CONTEXT)):
            changed=bytearray(self.original);changed[SITE-4-0x10000+delta]^=1
            code=bytearray(64)
            with self.subTest(byte=delta),self.assertRaises(ValueError):
                append_code(changed,code,CODE_BASE+8,CODE_BASE+16,0x55c0000,1453,0x55d0000,21)
            self.assertEqual(code,bytearray(64))

    def test_anonymous_narration_bridge_covers_the_early_branch_and_keeps_final_wait(self):
        from compile_dialogue import message_code
        from narration_layout import SITE,FINAL_WAIT_SITE,EXPECTED_FINAL_WAIT
        code,patches,audit=make_code(self.original,self.resolver,self.entry,0x55c0000,1453,
                                    message_code(ROOT/'work/output/dialogue_layout.o'),0x55d0000,22)
        narration=audit['narration'];self.assertEqual(narration['native_show_flags'],'0xf0')
        self.assertEqual(narration['inner_width'],896)
        target=int(narration['bridge'],16)
        payload=next(value for off,value in patches if off==SITE-0x10000)
        ins=next(self.md.disasm(payload,SITE))
        self.assertEqual((ins.mnemonic,ins.op_str),('bl',hex(target)))
        # The original branch lands at the argument setup, then reaches the
        # new hook. It previously skipped the ordinary hook at a5e94 entirely.
        ins=next(self.md.disasm(self.original[0xa5e58-0x10000:0xa5e58-0x10000+4],0xa5e58))
        self.assertEqual((ins.mnemonic,ins.op_str),('beq','cr7, 0xa607c'))
        changed=bytearray(self.original)
        for off,value in patches:changed[off:off+len(value)]=value
        self.assertEqual(changed[FINAL_WAIT_SITE-0x10000:FINAL_WAIT_SITE-0x10000+len(EXPECTED_FINAL_WAIT)],EXPECTED_FINAL_WAIT)
        self.assertEqual(changed[0xa6088-0x10000:0xa6090-0x10000],self.original[0xa6088-0x10000:0xa6090-0x10000])


if __name__=='__main__':unittest.main()
