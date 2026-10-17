"""Read-only instruction execution and source-path checks for narration reflow."""
from pathlib import Path
import re
import unittest

from capstone import Cs, CS_ARCH_PPC, CS_MODE_64, CS_MODE_BIG_ENDIAN

import narration_layout as layout
from runtime_text import CODE_BASE

ROOT = Path(__file__).resolve().parents[1]
MASK = (1 << 64) - 1


class BridgeMachine:
    def __init__(self, original, result):
        code = bytearray(bytes.fromhex('60000000') * 4)
        self.presenter = CODE_BASE
        _, audit = layout.append_code(original, code, self.presenter)
        self.start = int(audit['bridge'], 16)
        md = Cs(CS_ARCH_PPC, CS_MODE_64 | CS_MODE_BIG_ENDIAN)
        blob = bytes(code[self.start - CODE_BASE:])
        instructions = list(md.disasm(blob, self.start))
        # Alignment padding follows the terminating branch.
        self.instructions = {i.address: (i.mnemonic, i.op_str) for i in instructions}
        self.regs = [0x12340000 + i * 0x101 for i in range(32)]
        self.regs[1:5] = [0x800000, 0x488530, 0, 0x600000]
        self.fprs = [0x4001234500000000 + i for i in range(32)]
        self.initial_regs, self.initial_fprs = self.regs[:], self.fprs[:]
        self.lr = self.initial_lr = layout.SITE + 4
        self.ctr = self.initial_ctr = 0x13572468
        self.cr = self.initial_cr = 0x89abcdef
        self.memory = {}
        self.result = result
        self.called = 0
        self.caller = bytes((i * 19 + 3) % 256 for i in range(0x180))
        self.memory.update(enumerate(self.caller, self.regs[1]))
        self.store(self.regs[2] - 0x588c, 0x5482210, 4)
        self.store(0x5482210, 0x55667788, 4)

    def store(self, address, value, size=8):
        for i, byte in enumerate((value & ((1 << (8 * size)) - 1)).to_bytes(size, 'big')):
            self.memory[address + i] = byte

    def load(self, address, size=8):
        return int.from_bytes(bytes(self.memory[address + i] for i in range(size)), 'big')

    @staticmethod
    def reg(value):
        return int(value[1:])

    def address(self, value):
        m = re.fullmatch(r'(-?(?:0x[0-9a-f]+|\d+))\(r(\d+)\)', value)
        if m is None:
            raise AssertionError('Unexpected memory operand ' + value)
        return (self.regs[int(m[2])] + int(m[1], 0)) & MASK

    def run(self):
        pc = self.start
        for _ in range(1000):
            mnemonic, operands = self.instructions[pc]
            args = operands.split(', ') if operands else []
            next_pc = pc + 4
            if mnemonic == 'stdu':
                address = self.address(args[1])
                self.store(address, self.regs[self.reg(args[0])])
                self.regs[1] = address
            elif mnemonic in ('std', 'stfd'):
                values = self.fprs if mnemonic == 'stfd' else self.regs
                self.store(self.address(args[1]), values[self.reg(args[0])])
            elif mnemonic in ('ld', 'lfd', 'lwz'):
                values = self.fprs if mnemonic == 'lfd' else self.regs
                values[self.reg(args[0])] = self.load(self.address(args[1]), 4 if mnemonic == 'lwz' else 8)
            elif mnemonic in ('mflr', 'mfctr', 'mfcr'):
                self.regs[self.reg(args[0])] = getattr(self, mnemonic[2:])
            elif mnemonic in ('mtlr', 'mtctr'):
                setattr(self, mnemonic[2:], self.regs[self.reg(args[0])])
            elif mnemonic == 'mtcrf':
                if args[0] != '0xff':raise AssertionError('Partial CR restoration')
                self.cr = self.regs[self.reg(args[1])] & 0xffffffff
            elif mnemonic == 'lis':
                self.regs[self.reg(args[0])] = (int(args[1], 0) << 16) & MASK
            elif mnemonic == 'ori':
                self.regs[self.reg(args[0])] = self.regs[self.reg(args[1])] | int(args[2], 0)
            elif mnemonic == 'addi':
                self.regs[self.reg(args[0])] = (self.regs[self.reg(args[1])] + int(args[2], 0)) & MASK
            elif mnemonic == 'bctrl':
                if self.ctr != self.presenter:raise AssertionError('Wrong C entry')
                if self.regs[3:6] != [0, self.initial_regs[4], 0x55667788]:
                    raise AssertionError('Wrong presenter inputs')
                self.called += 1
                # Deliberately exceed ordinary ABI clobbers to prove every
                # register save, including nonvolatile inputs and f0, works.
                for r in [0] + list(range(2, 32)):self.regs[r] = 0xbad00000 + r
                self.fprs = [0xdead000000000000 + r for r in range(32)]
                self.cr, self.ctr, self.lr = 0x12345678, 0xbad, next_pc
                for offset in range(0x10, 0xe0, 8):self.store(self.regs[1] + offset, 0xbad + offset)
                self.regs[3] = self.result & MASK
            elif mnemonic == 'cmpwi':
                if args[0] != 'cr7':raise AssertionError('Unexpected CR field')
                value = self.regs[self.reg(args[1])] & 0xffffffff
                value = value - (1 << 32) if value & 0x80000000 else value
                self.cr = (self.cr & ~15) | (8 if value < 0 else 4 if value > 0 else 2)
            elif mnemonic == 'beq':
                if args[0] != 'cr7':raise AssertionError('Unexpected branch CR')
                if self.cr & 2:next_pc = int(args[1], 0)
            elif mnemonic == 'b':
                target = int(args[0], 0)
                if target != layout.NATIVE_SHOW_WRAPPER:raise AssertionError('Wrong fallback')
                return target
            elif mnemonic == 'blr':
                return self.lr
            else:
                raise AssertionError('Unexpected instruction ' + mnemonic)
            pc = next_pc
        raise AssertionError('Bridge failed to terminate')


class NarrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = (ROOT / 'work/source/NPJB00162/USRDIR/EBOOT.elf').read_bytes()

    def test_both_paths_restore_every_register_and_leave_caller_stack_intact(self):
        for result in (0, 1, -1):
            with self.subTest(result=result):
                machine = BridgeMachine(self.original, result)
                target = machine.run()
                self.assertEqual(target, layout.NATIVE_SHOW_WRAPPER if result == 0 else layout.SITE + 4)
                self.assertEqual(machine.called, 1)
                self.assertEqual(machine.regs, machine.initial_regs)
                self.assertEqual(machine.fprs, machine.initial_fprs)
                self.assertEqual((machine.cr, machine.ctr, machine.lr),
                                 (machine.initial_cr, machine.initial_ctr, machine.initial_lr))
                self.assertEqual(bytes(machine.memory[machine.regs[1] + i] for i in range(len(machine.caller))), machine.caller)

    def test_only_narration_call_is_patched_and_every_guard_byte_blocks_unknown_code(self):
        patches, _ = layout.append_code(self.original, bytearray(b'\x60\0\0\0' * 4), CODE_BASE)
        self.assertEqual([(offset, len(data)) for offset, data in patches], [(layout.SITE - 0x10000, 4)])
        for address, expected in ((layout.SITE - 8, layout.EXPECTED_CONTEXT),
                                  (layout.FINAL_WAIT_SITE, layout.EXPECTED_FINAL_WAIT)):
            for n in range(len(expected)):
                modified = bytearray(self.original)
                modified[address - 0x10000 + n] ^= 1
                with self.subTest(address=hex(address + n)), self.assertRaises(ValueError):
                    layout.append_code(modified, bytearray(b'\x60\0\0\0' * 4), CODE_BASE)

    def test_actual_intro_commands_select_the_previously_unhooked_branch(self):
        from build import parse_events
        rows = parse_events((ROOT / 'work/source/NPJB00162/USRDIR/data/event/station/S0102.evt').read_bytes())
        self.assertEqual(rows[139][0], 0x93)
        self.assertEqual(rows[140][0], 0x43)
        self.assertFalse(rows[140][1].rstrip(b'\0'))
        self.assertEqual(rows[156][0], 0x38)
        self.assertEqual([rows[i][0] for i in (171, 172, 176, 177, 178)], [0x46] * 5)
        self.assertEqual([rows[i][0] for i in (173, 179)], [0x50] * 2)
        def data(address, size):return self.original[address - 0x10000:address - 0x10000 + size]
        def word(address):return int.from_bytes(data(address, 4), 'big')
        # Dispatch table links actual script opcodes to the traced handlers.
        for op, handler in ((0x93, 0x9d4e4), (0x43, 0x9e000),
                            (0x38, 0xa6878), (0x46, 0xa60cc), (0x50, 0xa5b10)):
            self.assertEqual(word(word(0x51ecc0 + op * 4)), handler)
        # Empty speaker -> 2590=ff, anonymous speaker -> 22a8=ff. Both flags
        # select a607c before ordinary/typewriter hook a5e94 is reached.
        guards = {0x9d4e8:'3800ffff', 0x9d4f4:'980922a8',
                  0x9df54:'419e0034', 0x9df88:'7fe307b44bffff11',
                  0x9dec8:'3800ffff980a2590', 0xa68a4:'4bff75f9',
                  0xa5e40:'7d77b214880b25902f800000419e0010880b22a82f8000ff419e0224',
                  0xa5e94:'4192012c', 0xde498:'388000f0'}
        for address, expected in guards.items():
            self.assertEqual(data(address, len(expected) // 2), bytes.fromhex(expected), hex(address))


if __name__ == '__main__':
    unittest.main()
