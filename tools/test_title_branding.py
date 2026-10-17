"""Execute the emitted title footer against hostile native font callees."""
from pathlib import Path
import re
import unittest

from capstone import Cs, CS_ARCH_PPC, CS_MODE_64, CS_MODE_BIG_ENDIAN
import title_branding as branding

ROOT = Path(__file__).resolve().parents[1]
MASK = (1 << 64)-1


class FooterMachine:
    def __init__(self, original, widths, prefix=0, version='0.1.10'):
        self.code = bytearray(b'\x60\0\0\0'*(prefix//4))
        self.patches, self.audit = branding.append_code(original, self.code, version)
        self.start = int(self.audit['bridge'], 16)
        bridge = bytes(self.code[self.start-branding.CODE_BASE:])[:self.audit['bridge_bytes']]
        md = Cs(CS_ARCH_PPC, CS_MODE_64 | CS_MODE_BIG_ENDIAN)
        decoded = list(md.disasm(bridge, self.start))
        assert len(decoded)*4 == len(bridge)
        self.instructions = {i.address: (i.mnemonic, i.op_str) for i in decoded}
        self.regs = [0x112200000+i*0x100 for i in range(32)]
        self.regs[1], self.regs[2], self.regs[26] = 0x800000, 0x488530, 0x71000000
        self.fprs = [0x4001234500000000+i for i in range(32)]
        self.lr, self.ctr, self.cr, self.xer, self.fpscr = 0x12345678, 0x23456789, 0xa5a5a5a5, 0x76543210, 0x87654321
        self.initial_regs, self.initial_fprs = self.regs[:], self.fprs[:]
        self.initial_control = self.lr, self.ctr, self.cr, self.xer, self.fpscr
        self.memory = dict(enumerate(self.code, branding.CODE_BASE))
        self.caller = bytes((i*37+9)%256 for i in range(0x200))
        self.memory.update(enumerate(self.caller, self.regs[1]))
        self.font = 0x72000000
        self.memory.update(enumerate(self.font.to_bytes(4, 'big'), self.regs[26]))
        self.widths, self.draws, self.calls, self.measures = widths, [], [], []

    @staticmethod
    def reg(value): return int(value[1:])

    def addr(self, operand):
        match = re.fullmatch(r'(-?(?:0x[0-9a-f]+|\d+))\(r(\d+)\)', operand)
        assert match is not None, operand
        return (self.regs[int(match[2])]+int(match[1], 0)) & MASK

    def store(self, address, value, size=8):
        assert self.initial_regs[1]-branding.FRAME <= address <= self.initial_regs[1]-size
        self.memory.update(enumerate((value & ((1 << (size*8))-1)).to_bytes(size, 'big'), address))

    def load(self, address, size=8):
        return int.from_bytes(bytes(self.memory[address+i] for i in range(size)), 'big')

    def text(self, address):
        result = bytearray()
        while self.memory[address]:
            result.append(self.memory[address]); address += 1
        return result.decode('ascii')

    def native(self, target, return_address):
        assert self.regs[2] == self.initial_regs[2], 'Native call lost TOC'
        assert self.regs[3] == self.font, 'Wrong title font object'
        self.calls.append(target)
        if target == branding.MEASURE:
            index = len(self.measures)
            text, (y, size) = self.audit['labels'][index]['text'], branding.LINES[index]
            assert self.text(self.regs[4]) == text
            assert self.regs[5:7] == [size, size]
            self.measures.append(text)
            result = self.widths[index]
        elif target == branding.DRAW:
            index, shadow = len(self.draws)//2, not len(self.draws)%2
            y, size = branding.LINES[index]
            assert self.regs[4:11] == [branding.RIGHT-self.widths[index]+int(shadow),
                y+int(shadow), int(self.audit['string_addresses'][index], 16),
                branding.SHADOW if shadow else branding.FOREGROUND, size, size, 0]
            assert self.text(self.regs[6]) == self.audit['labels'][index]['text']
            self.draws.append(tuple(self.regs[4:11]))
            result = 0x12340000+len(self.draws)
        else:
            raise AssertionError('Unexpected callee')
        # Real callees may use their caller's entire outgoing parameter area.
        for offset in range(0x10, 0x80, 8): self.store(self.regs[1]+offset, 0xbad000+offset)
        for reg in [0, 2]+list(range(3, 13)): self.regs[reg] = 0xdead0000+reg
        for reg in range(14): self.fprs[reg] = 0xbadf000000000000+reg
        self.lr, self.ctr, self.cr, self.xer, self.fpscr = return_address, 0xbad1, 0xbad2, 0xbad3, 0xbad4
        self.regs[3] = result

    def run(self):
        pc = self.start
        for _ in range(1000):
            name, operands = self.instructions[pc]
            args = operands.split(', ') if operands else []
            nxt, reg = pc+4, self.reg
            if name == 'stdu':
                address = self.addr(args[1]); self.store(address, self.regs[reg(args[0])]); self.regs[1] = address
            elif name in ('std', 'stfd'):
                self.store(self.addr(args[1]), (self.fprs if name == 'stfd' else self.regs)[reg(args[0])])
            elif name in ('ld', 'lwz', 'lfd'):
                (self.fprs if name == 'lfd' else self.regs)[reg(args[0])] = self.load(self.addr(args[1]), 4 if name == 'lwz' else 8)
            elif name in ('mflr', 'mfctr', 'mfcr', 'mfxer'):
                self.regs[reg(args[0])] = getattr(self, name[2:])
            elif name in ('mtlr', 'mtctr', 'mtxer'):
                setattr(self, name[2:], self.regs[reg(args[0])])
            elif name == 'mtcrf':
                assert args[0] == '0xff'; self.cr = self.regs[reg(args[1])]
            elif name == 'mffs': self.fprs[reg(args[0])] = self.fpscr
            elif name == 'mtfsf':
                assert args[0] == '0xff'; self.fpscr = self.fprs[reg(args[1])]
            elif name == 'li': self.regs[reg(args[0])] = int(args[1], 0) & MASK
            elif name == 'lis': self.regs[reg(args[0])] = (int(args[1], 0) << 16) & MASK
            elif name == 'ori': self.regs[reg(args[0])] = self.regs[reg(args[1])] | int(args[2], 0)
            elif name == 'addi': self.regs[reg(args[0])] = (self.regs[reg(args[1])]+int(args[2], 0)) & MASK
            elif name == 'subfic':
                self.regs[reg(args[0])] = (int(args[2], 0)-self.regs[reg(args[1])]) & MASK
                self.xer ^= 0x20000000
            elif name == 'clrldi':
                self.regs[reg(args[0])] = self.regs[reg(args[1])] & ((1 << (64-int(args[2], 0)))-1)
            elif name == 'bl': self.native(int(args[0], 0), nxt)
            elif name == 'b':
                assert int(args[0], 0) == branding.CONTINUE
                return
            else: raise AssertionError('Unexpected instruction: '+name+' '+operands)
            pc = nxt
        raise AssertionError('Footer bridge failed to terminate')


class FooterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = (ROOT/'work/source/NPJB00162/USRDIR/EBOOT.elf').read_bytes()

    def test_native_alignment_and_hostile_callees_preserve_state(self):
        for widths in [(65, 199), (66, 201), (0, 0), (120, 700)]:
            for prefix in (0, 4, 20):
                with self.subTest(widths=widths, prefix=prefix):
                    machine = FooterMachine(self.original, widths, prefix)
                    machine.run()
                    expected = machine.initial_regs[:]; expected[3] = machine.font
                    self.assertEqual(machine.regs, expected)
                    self.assertEqual(machine.fprs, machine.initial_fprs)
                    self.assertEqual((machine.lr, machine.ctr, machine.cr, machine.xer, machine.fpscr), machine.initial_control)
                    self.assertEqual(bytes(machine.memory[machine.regs[1]+i] for i in range(len(machine.caller))), machine.caller)
                    self.assertEqual(len(machine.measures), 2)
                    self.assertEqual(len(machine.draws), 4)
                    self.assertEqual(machine.calls, [branding.MEASURE, branding.DRAW, branding.DRAW]*2)

    def test_each_source_guard_fails_without_mutating_code(self):
        for address, _ in branding.GUARDS:
            with self.subTest(address=hex(address)):
                changed = bytearray(self.original); changed[address-0x10000] ^= 1
                code = bytearray(b'abcd')
                with self.assertRaisesRegex(ValueError, 'context mismatch'):
                    branding.append_code(changed, code)
                self.assertEqual(code, b'abcd')

    def test_patch_is_one_title_only_branch_and_original_is_untouched(self):
        code = bytearray(); snapshot = bytes(self.original)
        patches, audit = branding.append_code(self.original, code)
        self.assertEqual(self.original, snapshot)
        self.assertEqual(len(patches), 1)
        self.assertEqual(patches[0][0], branding.SITE-0x10000)
        md = Cs(CS_ARCH_PPC, CS_MODE_64 | CS_MODE_BIG_ENDIAN)
        ins = list(md.disasm(patches[0][1], branding.SITE))
        self.assertEqual([(i.mnemonic, i.op_str) for i in ins], [('b', audit['bridge'])])
        self.assertTrue(audit['no_global_font_override_changes'])

    def test_label_pool_tracks_requested_version(self):
        machine = FooterMachine(self.original, (72, 199), version='0.1.123')
        machine.run()
        self.assertEqual(machine.measures, ['v0.1.123', 'github.com/retro-trans'])

    def test_font_bounds_leave_copyright_and_screen_edges_clear(self):
        rows = branding.layout_audit()
        self.assertEqual([r['modeled_bounds'] for r in rows], [[1191,646,65,18], [1057,670,199,20]])
        for row in rows:
            x,y,w,h = row['modeled_bounds']
            self.assertGreaterEqual(y, 646)
            self.assertLessEqual(x+w+1, 1280-23)
            self.assertLessEqual(y+h+1, 720-29)

    def test_nonzero_or_overfull_code_gap_is_rejected(self):
        changed = bytearray(self.original); changed[branding.CODE_BASE-0x10000] = 1
        with self.assertRaisesRegex(ValueError, 'zero-filled'):
            branding.append_code(changed, bytearray())
        with self.assertRaisesRegex(ValueError, 'exceeds'):
            branding.append_code(self.original, bytearray(b'\0'*(branding.CODE_LIMIT-branding.CODE_BASE-16)))

    def test_unsafe_or_oversized_labels_are_rejected(self):
        for version in ['1.0.0', '0.1.10\n', '', 'v0.1.10']:
            with self.assertRaises(ValueError): branding.texts(version)
        for project in ['', 'a\nb', 'x%08x', 'x'*65]:
            with self.assertRaises(ValueError): branding.texts(project=project)


if __name__ == '__main__': unittest.main()
