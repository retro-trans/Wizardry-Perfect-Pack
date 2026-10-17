"""Read-only instruction-execution regressions for the item-popup bridges.

Capstone decodes the emitted big-endian PPC instructions. The small interpreter
below executes those instructions independently of the generator, replacing
only the native font call with a configurable measurement and ABI clobbers.
No emulator installation, game boot or output file is needed.
"""
import math
import re
import unittest
from pathlib import Path

from capstone import Cs, CS_ARCH_PPC, CS_MODE_64, CS_MODE_BIG_ENDIAN

import item_cell_layout as layout


ROOT = Path(__file__).resolve().parents[1]
MASK64 = (1 << 64) - 1


class BridgeMachine:
    """Interpret only the emitted bridge's integer/branch instruction subset."""

    def __init__(self, cap, measure):
        self.start = 0x448090
        decoder = Cs(CS_ARCH_PPC, CS_MODE_64 | CS_MODE_BIG_ENDIAN)
        payload = layout._bridge(self.start, cap)
        decoded = list(decoder.disasm(payload, self.start))
        if len(decoded) * 4 != len(payload):
            raise AssertionError('Bridge contains an undecodable instruction')
        self.instructions = {i.address: (i.mnemonic, i.op_str) for i in decoded}
        self.regs = [0x100000 + 0x100 * i for i in range(32)]
        self.regs[1] = 0x800000
        self.regs[3:7] = [0x555000, 0x123400, 22, 22]
        self.initial_regs = self.regs[:]
        self.lr = self.initial_lr = 0x600001
        self.cr = self.initial_cr = 0xa5a5a5a5
        self.measure = measure
        self.calls = []
        self.memory = {}
        # The surrounding caller frame must remain intact except its declared
        # four-byte fitted-width slot. Use byte-addressed memory to catch any
        # accidental overlapping or incorrectly sized stores.
        self.caller_start = self.regs[1]
        self.caller_before = bytes((i * 37 + 11) % 256 for i in range(0x240))
        for i, value in enumerate(self.caller_before):
            self.memory[self.caller_start + i] = value

    @staticmethod
    def _register(operand):
        return int(operand[1:])

    @staticmethod
    def _signed32(value):
        return (value & 0x7fffffff) - (value & 0x80000000)

    def _address(self, operand):
        match = re.fullmatch(r'(-?(?:0x[0-9a-f]+|\d+))\(r(\d+)\)', operand)
        if match is None:
            raise AssertionError(f'Unrecognized memory operand: {operand}')
        return (int(match[1], 0) + self.regs[int(match[2])]) & MASK64

    def _store(self, address, value, size=8):
        if not self.caller_start - 0x120 <= address < self.caller_start + 0x240:
            raise AssertionError(f'Store outside inspected stack frames: {address:#x}')
        for i, byte in enumerate((value & ((1 << (size * 8)) - 1)).to_bytes(size, 'big')):
            self.memory[address + i] = byte

    def _load(self, address, size=8):
        return int.from_bytes(bytes(self.memory[address + i] for i in range(size)), 'big')

    def _compare(self, left, right):
        # All comparisons in the bridge address CR7 (the low CR nibble).
        self.cr = (self.cr & ~15) | (8 if left < right else 4 if left > right else 2)

    def _native_call(self, return_address):
        if self.regs[3] != self.initial_regs[3] or self.regs[4] != self.initial_regs[4]:
            raise AssertionError('Native font or text input was lost between measurements')
        if self.regs[6] != 22:
            raise AssertionError('Native measurement height changed')
        chosen = self.regs[5]
        self.calls.append(chosen)
        width = self.measure(chosen)
        # The real renderer saves its return at its caller's sp+16. Its
        # resolver wrapper may also use the normal argument/linkage area.
        for offset in range(0x10, 0x78, 8):
            self._store(self.regs[1] + offset, 0xbad00 + offset)
        # Deliberately clobber more than the native routine is required to:
        # every volatile GPR, TOC and all CR fields. The bridge promises to
        # restore the caller's argument registers/TOC/CR itself.
        for register in [0, 2] + list(range(3, 13)):
            self.regs[register] = 0xdead000 + register
        self.regs[3] = width
        self.cr = 0x12345678
        self.lr = return_address

    def run(self):
        pc = self.start
        for _ in range(4000):
            name, operands = self.instructions[pc]
            args = [part.strip() for part in operands.split(',')]
            reg = self._register
            next_pc = pc + 4
            if name == 'stdu':
                address = self._address(args[1])
                self._store(address, self.regs[reg(args[0])])
                self.regs[1] = address
            elif name in ('std', 'stw'):
                self._store(self._address(args[1]), self.regs[reg(args[0])],
                            8 if name == 'std' else 4)
            elif name == 'ld':
                self.regs[reg(args[0])] = self._load(self._address(args[1]))
            elif name == 'mflr':
                self.regs[reg(args[0])] = self.lr
            elif name == 'mtlr':
                self.lr = self.regs[reg(args[0])]
            elif name == 'mfcr':
                self.regs[reg(args[0])] = self.cr
            elif name == 'mtcrf':
                if args[0] != '0xff':
                    raise AssertionError('Bridge no longer restores the entire CR')
                self.cr = self.regs[reg(args[1])]
            elif name == 'li':
                self.regs[reg(args[0])] = int(args[1], 0)
            elif name == 'addi':
                self.regs[reg(args[0])] = (self.regs[reg(args[1])] + int(args[2], 0)) & MASK64
            elif name in ('cmpwi', 'cmplwi'):
                if args[0] != 'cr7':
                    raise AssertionError('Unexpected condition-register field')
                value = self.regs[reg(args[1])]
                self._compare(self._signed32(value) if name == 'cmpwi' else value & 0xffffffff,
                              int(args[2], 0))
            elif name == 'mullw':
                self.regs[reg(args[0])] = (self.regs[reg(args[1])] * self.regs[reg(args[2])]) & 0xffffffff
            elif name == 'divwu':
                self.regs[reg(args[0])] = ((self.regs[reg(args[1])] & 0xffffffff)
                                          // (self.regs[reg(args[2])] & 0xffffffff))
            elif name in ('ble', 'bge'):
                if ((name == 'ble' and not self.cr & 4)
                        or (name == 'bge' and not self.cr & 8)):
                    next_pc = int(args[1], 0)
            elif name == 'b':
                next_pc = int(args[0], 0)
            elif name == 'bl':
                if int(args[0], 0) != 0x164adc:
                    raise AssertionError('Bridge bypassed the existing native measurement hook')
                self._native_call(next_pc)
            elif name == 'blr':
                return self._result()
            else:
                raise AssertionError(f'Unhandled instruction: {name} {operands}')
            pc = next_pc
        raise AssertionError('Bridge did not terminate')

    def _result(self):
        if (self.lr != self.initial_lr or self.cr != self.initial_cr
                or self.regs[1] != self.initial_regs[1]
                or self.regs[2] != self.initial_regs[2]
                or self.regs[4:] != self.initial_regs[4:]):
            raise AssertionError('Bridge violated register, stack, TOC, CR or LR preservation')
        after = bytes(self.memory[self.caller_start + i] for i in range(0x240))
        if after[:0x188] != self.caller_before[:0x188] or after[0x18c:] != self.caller_before[0x18c:]:
            raise AssertionError('Bridge overwrote caller storage outside sp+0x188')
        chosen = self._load(self.caller_start + 0x188, 4)
        return chosen, self.regs[3], self.calls


class ItemCellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = (ROOT / 'work/source/NPJB00162/USRDIR/EBOOT.elf').read_bytes()

    def test_native_clobbers_and_rounding_84_cases(self):
        cases = 0
        for cap in (72, 104):
            for full_width in (0, 1, 25, 71, 72, 73, 103, 104, 105, 166, 193, 251, 500, 5000):
                for rounding in (0, 1, 3):
                    with self.subTest(cap=cap, full_width=full_width, rounding=rounding):
                        def measure(size):
                            return math.ceil(full_width * size / 22) + (rounding if size < 22 else 0)
                        chosen, width, calls = BridgeMachine(cap, measure).run()
                        self.assertEqual(width, measure(chosen))
                        self.assertGreaterEqual(chosen, 1)
                        self.assertLessEqual(chosen, 22)
                        self.assertTrue(width <= cap or chosen == 1)
                        self.assertEqual(calls[0], 22)
                        if full_width <= cap:
                            self.assertEqual(chosen, 22)
                            self.assertEqual(calls, [22])
                        cases += 1
        self.assertEqual(cases, 84)

    def test_hinting_overshoot_is_remeasured_and_decremented(self):
        chosen, width, calls = BridgeMachine(72, lambda size: math.ceil(193 * size / 22)
                                           + (3 if size < 22 else 0)).run()
        self.assertEqual(calls, [22, 8, 7])
        self.assertEqual((chosen, width), (7, 65))

    def test_guard_failures_do_not_mutate_code(self):
        _, audit = layout.append_code(self.original, bytearray())
        self.assertEqual(len(audit['guarded_instructions']), 52)
        for guard in audit['guarded_instructions']:
            with self.subTest(address=guard['address']):
                changed = bytearray(self.original)
                changed[int(guard['address'], 16) - 0x10000] ^= 1
                code = bytearray(b'\xaa' * 16)
                before = bytes(code)
                with self.assertRaisesRegex(ValueError, 'instruction mismatch'):
                    layout.append_code(changed, code)
                self.assertEqual(bytes(code), before)

    def test_nonzero_code_gap_is_rejected_before_mutation(self):
        changed = bytearray(self.original)
        changed[layout.CODE_BASE - 0x10000] = 1
        code = bytearray()
        with self.assertRaisesRegex(ValueError, 'not zero-filled'):
            layout.append_code(changed, code)
        self.assertEqual(code, bytearray())

    def test_code_limit_is_rejected_before_mutation(self):
        code = bytearray(layout.CODE_LIMIT - layout.CODE_BASE - 16)
        before = bytes(code)
        with self.assertRaisesRegex(ValueError, 'code gap'):
            layout.append_code(self.original, code)
        self.assertEqual(bytes(code), before)

    def test_alignment_for_five_existing_runtime_lengths(self):
        for length in (0, 1, 5, 16, 100):
            with self.subTest(length=length):
                code = bytearray(length)
                patches, audit = layout.append_code(self.original, code)
                self.assertEqual(len(patches), 35)
                self.assertEqual(len(code) % 16, 0)
                self.assertTrue(all(int(cell['bridge'], 16) % 16 == 0 for cell in audit['cells']))
                self.assertEqual(audit['maximum_horizontal_size'], 22)
                self.assertEqual(audit['vertical_size'], 22)

    def test_patch_targets_keep_draw_and_color_logic(self):
        patches, audit = layout.append_code(self.original, bytearray())
        changed = bytearray(self.original)
        for offset, payload in patches:
            changed[offset:offset + len(payload)] = payload
        for cell in audit['cells']:
            address = int(cell['draw_call'], 16)
            self.assertEqual(changed[address - 0x10000:address - 0x10000 + 4],
                             self.original[address - 0x10000:address - 0x10000 + 4])
        # The original affinity/state selection branches are outside every
        # patch: normal, effective, ineffective and special colors survive.
        for start, end in ((0x604ac, 0x604e8), (0x60710, 0x60748), (0x60880, 0x60960)):
            self.assertEqual(changed[start - 0x10000:end - 0x10000],
                             self.original[start - 0x10000:end - 0x10000])


if __name__ == '__main__':
    unittest.main()
