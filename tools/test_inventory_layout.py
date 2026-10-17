"""Execute emitted inventory bridge instructions with hostile native callees.

This is an independent integer/stack/branch interpreter over Capstone's actual
decoded PPC code, with native font, predicate, setter and draw calls modeled.
It also audits all item-name fields and the deferred preview-label fix.
"""
import json
import math
import re
import unittest
from pathlib import Path

from capstone import Cs, CS_ARCH_PPC, CS_MODE_64, CS_MODE_BIG_ENDIAN

import inventory_layout as layout


ROOT = Path(__file__).resolve().parents[1]
MASK64 = (1 << 64) - 1


class InventoryMachine:
    def __init__(self, measure, stackable=False, horizontal=25, vertical=32):
        self.start = 0x448090
        payload = layout._bridge(self.start)
        decoder = Cs(CS_ARCH_PPC, CS_MODE_64 | CS_MODE_BIG_ENDIAN)
        decoded = list(decoder.disasm(payload, self.start))
        if len(decoded) * 4 != len(payload):
            raise AssertionError('Undecodable inventory bridge')
        self.instructions = {i.address: (i.mnemonic, i.op_str) for i in decoded}
        self.regs = [0x100000 + 0x100 * i for i in range(32)]
        self.regs[1] = 0x800000
        self.regs[2] = 0x488530
        self.regs[3] = 0x090ab15c  # selected color plus packed screen position
        self.regs[4] = 0x00640080
        self.regs[5] = 0x123400
        self.initial_regs = self.regs[:]
        self.fprs = [0x3ff1000000000000 + i for i in range(32)]
        self.initial_fprs = self.fprs[:]
        self.lr = self.initial_lr = 0x600001
        self.cr = self.initial_cr = 0xa5a5a5a5
        self.ctr = self.initial_ctr = 0xabcdef0198765432
        self.initial_horizontal, self.initial_vertical = horizontal, vertical
        self.measure, self.stackable = measure, stackable
        self.calls, self.measurements, self.draws = [], [], []
        self.memory = {}
        self.stack_start = self.regs[1]
        self.caller_before = bytes((i * 37 + 11) % 256 for i in range(0x140))
        self._write(self.stack_start, self.caller_before)
        self.state = 0x70000000 + 0x30000
        self.width_address = self.state - 0x7c04
        self.height_address = self.state - 0x7c00
        self.flag_address = self.state - 0x7c08
        self.font_pointer = 0x71000000
        self.font_object = 0x72000000
        self._write(self.regs[2] - 0x59f4, (self.state - 0x30000).to_bytes(4, 'big'))
        self._write(self.regs[2] - 0x7c58, self.font_pointer.to_bytes(4, 'big'))
        self._write(self.font_pointer, self.font_object.to_bytes(4, 'big'))
        self._write(self.width_address, horizontal.to_bytes(4, 'big'))
        self._write(self.height_address, vertical.to_bytes(4, 'big'))
        self._write(self.flag_address, b'\x01')
        self.draw_result = 0x1234567

    def _write(self, address, value):
        for i, byte in enumerate(value):
            self.memory[address + i] = byte

    def _store(self, address, value, size=8):
        if not (self.stack_start - 0x1c0 <= address < self.stack_start
                or (address, size) in ((self.width_address, 4), (self.height_address, 4))):
            raise AssertionError(f'Unexpected bridge write at {address:#x}, size {size}')
        self._write(address, (value & ((1 << (size * 8)) - 1)).to_bytes(size, 'big'))

    def _load(self, address, size=8):
        return int.from_bytes(bytes(self.memory[address + i] for i in range(size)), 'big')

    @staticmethod
    def _register(operand):
        return int(operand[1:])

    def _address(self, operand):
        match = re.fullmatch(r'(-?(?:0x[0-9a-f]+|\d+))\(r(\d+)\)', operand)
        if match is None:
            raise AssertionError('Unexpected memory operand: ' + operand)
        return (self.regs[int(match[2])] + int(match[1], 0)) & MASK64

    def _compare(self, left, right):
        self.cr = (self.cr & ~15) | (8 if left < right else 4 if left > right else 2)

    def _native_call(self, target, return_address):
        self.calls.append(target)
        if target == 0x57f74:
            if self.regs[3] != self.initial_regs[31]:
                raise AssertionError('Stack predicate received the wrong item')
            result = int(self.stackable)
        elif target == 0x164adc:
            if (self.regs[3] != self.font_object or self.regs[4] != self.initial_regs[5]
                    or self.regs[6] != self.initial_vertical):
                raise AssertionError('Font, name token or vertical size lost during native measurement')
            self.measurements.append(self.regs[5])
            result = self.measure(self.regs[5])
        elif target == 0xd0794:
            self._write(self.width_address, self.regs[3].to_bytes(4, 'big'))
            self._write(self.height_address, self.regs[4].to_bytes(4, 'big'))
            self._write(self.flag_address, b'\x01')
            result = 0
        elif target == 0xd15ac:
            if self.regs[3:13] != self.initial_regs[3:13]:
                raise AssertionError('Original variadic draw integer arguments or packed colors changed')
            if (self.fprs[1:14] != self.initial_fprs[1:14]
                    or self.cr != self.initial_cr or self.ctr != self.initial_ctr):
                raise AssertionError('Original variadic draw FPR, CR or CTR inputs changed')
            chosen = self._load(self.width_address, 4)
            height = self._load(self.height_address, 4)
            if height != self.initial_vertical:
                raise AssertionError('Drawing changed the native vertical size')
            self.draws.append((chosen, height))
            self._write(self.flag_address, b'\x00')  # real native draw consumes the override
            result = self.draw_result
        else:
            raise AssertionError(f'Unexpected native call: {target:#x}')
        # Native d15ac's LR and integer-vararg spills live here. Other callees
        # may also use the standard linkage/parameter area below private0x80.
        for offset in range(0x10, 0x78, 8):
            self._store(self.regs[1] + offset, 0xbad00 + offset)
        for register in [0, 2] + list(range(3, 13)):
            self.regs[register] = 0xdead000 + register
        for register in range(14):
            self.fprs[register] = 0xbadf0000 + register
        self.regs[3] = result
        self.cr, self.ctr, self.lr = 0x12345678, 0xbadc0ffee, return_address

    def run(self):
        pc = self.start
        for _ in range(6000):
            name, operands = self.instructions[pc]
            args = [part.strip() for part in operands.split(',')]
            reg = self._register
            next_pc = pc + 4
            if name == 'stdu':
                address = self._address(args[1])
                self._store(address, self.regs[reg(args[0])])
                self.regs[1] = address
            elif name in ('std', 'stw'):
                self._store(self._address(args[1]), self.regs[reg(args[0])], 8 if name == 'std' else 4)
            elif name in ('ld', 'lwz'):
                self.regs[reg(args[0])] = self._load(self._address(args[1]), 8 if name == 'ld' else 4)
            elif name == 'stfd':
                self._store(self._address(args[1]), self.fprs[reg(args[0])])
            elif name == 'lfd':
                self.fprs[reg(args[0])] = self._load(self._address(args[1]))
            elif name in ('mflr', 'mfctr', 'mfcr'):
                self.regs[reg(args[0])] = {'mflr': self.lr, 'mfctr': self.ctr, 'mfcr': self.cr}[name]
            elif name in ('mtlr', 'mtctr'):
                if name == 'mtlr':
                    self.lr = self.regs[reg(args[0])]
                else:
                    self.ctr = self.regs[reg(args[0])]
            elif name == 'mtcrf':
                if args[0] != '0xff':
                    raise AssertionError('Incomplete CR restoration')
                self.cr = self.regs[reg(args[1])]
            elif name == 'mr':
                self.regs[reg(args[0])] = self.regs[reg(args[1])]
            elif name == 'li':
                self.regs[reg(args[0])] = int(args[1], 0)
            elif name in ('addi', 'addis'):
                immediate = int(args[2], 0) * (0x10000 if name == 'addis' else 1)
                self.regs[reg(args[0])] = (self.regs[reg(args[1])] + immediate) & MASK64
            elif name == 'cmpwi':
                value = self.regs[reg(args[1])]
                self._compare((value & 0x7fffffff) - (value & 0x80000000), int(args[2], 0))
            elif name == 'cmplw':
                self._compare(self.regs[reg(args[1])] & 0xffffffff, self.regs[reg(args[2])] & 0xffffffff)
            elif name == 'mullw':
                self.regs[reg(args[0])] = (self.regs[reg(args[1])] * self.regs[reg(args[2])]) & 0xffffffff
            elif name == 'divwu':
                self.regs[reg(args[0])] = ((self.regs[reg(args[1])] & 0xffffffff)
                                          // (self.regs[reg(args[2])] & 0xffffffff))
            elif name in ('ble', 'bge', 'beq'):
                if ((name == 'ble' and not self.cr & 4) or (name == 'bge' and not self.cr & 8)
                        or (name == 'beq' and self.cr & 2)):
                    next_pc = int(args[1], 0)
            elif name == 'b':
                next_pc = int(args[0], 0)
            elif name == 'bl':
                self._native_call(int(args[0], 0), next_pc)
            elif name == 'blr':
                return self._result()
            else:
                raise AssertionError(f'Unhandled instruction: {name} {operands}')
            pc = next_pc
        raise AssertionError('Inventory bridge did not terminate')

    def _result(self):
        if (self.regs[1] != self.initial_regs[1] or self.regs[2] != self.initial_regs[2]
                or self.regs[4:] != self.initial_regs[4:] or self.regs[3] != self.draw_result
                or self.fprs[1:14] != self.initial_fprs[1:14] or self.cr != self.initial_cr
                or self.ctr != self.initial_ctr or self.lr != self.initial_lr):
            raise AssertionError('Inventory bridge violated caller register preservation')
        after = bytes(self.memory[self.stack_start + i] for i in range(len(self.caller_before)))
        if after != self.caller_before:
            raise AssertionError('Inventory bridge overwrote caller frame')
        if (self._load(self.width_address, 4) != self.initial_horizontal
                or self._load(self.height_address, 4) != self.initial_vertical
                or self._load(self.flag_address, 1) != 0):
            raise AssertionError('Native font state was not restored correctly')
        if len(self.draws) != 1 or self.calls.count(0x57f74) != 1:
            raise AssertionError('Wrong number of draws or stack-predicate calls')
        return self.draws[0][0]


class InventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = (ROOT / 'work/source/NPJB00162/USRDIR/EBOOT.elf').read_bytes()

    def test_84_sizing_vararg_clobber_and_rounding_cases(self):
        cases = 0
        for stackable in (False, True):
            cap = 252 if stackable else 288
            for width in (0, 1, 100, 251, 252, 253, 287, 288, 289, 315, 400, 501, 1000, 10000):
                for rounding in (0, 1, 3):
                    with self.subTest(stackable=stackable, width=width, rounding=rounding):
                        def measure(size):
                            return math.ceil(width * size / 25) + (rounding if size < 25 else 0)
                        machine = InventoryMachine(measure, stackable)
                        size = machine.run()
                        self.assertTrue(measure(size) <= cap or size == 1)
                        self.assertGreaterEqual(size, 1)
                        self.assertLessEqual(size, 25)
                        self.assertEqual(machine.measurements[0], 25)
                        if width <= cap:
                            self.assertEqual(size, 25)
                            self.assertEqual(machine.measurements, [25])
                        cases += 1
        self.assertEqual(cases, 84)

    def test_long_name_and_stack_quantity_gap(self):
        from fontTools.ttLib import TTFont
        from check_vwf import cache_width, pen_positions
        font = TTFont(ROOT / 'work/source/NPJB00162/USRDIR/FOT-UtrilloPro-DB.otf')
        widths = {chr(c): cache_width(font['hmtx'][g][0], font['head'].unitsPerEm)
                  for c, g in font.getBestCmap().items()}
        text = 'Protective Gear-like Object'
        measure = lambda size: pen_positions(text, size, widths)[1]
        self.assertEqual(measure(25), 315)
        ordinary = InventoryMachine(measure)
        stack = InventoryMachine(measure, True)
        self.assertEqual(ordinary.run(), 22)
        self.assertEqual(stack.run(), 20)
        self.assertEqual(measure(22), 276)
        self.assertEqual(measure(20), 251)
        quantity_width = pen_positions('99', 25, widths)[1]
        self.assertEqual(quantity_width, 32)
        self.assertGreaterEqual(320 - quantity_width - (28 + measure(20)), 8)

    def test_actual_native_font_dimensions_are_used_and_restored(self):
        for horizontal, vertical in ((22, 26), (30, 40), (25, 32)):
            with self.subTest(horizontal=horizontal, vertical=vertical):
                machine = InventoryMachine(lambda size: math.ceil(500 * size / horizontal),
                                           horizontal=horizontal, vertical=vertical)
                size = machine.run()
                self.assertEqual(machine.measurements[0], horizontal)
                self.assertEqual(machine.draws, [(size, vertical)])

    def test_all_item_name_fields_and_enhancement_variants_fit(self):
        audit = layout.corpus_audit()
        self.assertEqual(audit['result'], 'passed')
        self.assertGreaterEqual(audit['nonempty_name_fields'], 1182)
        self.assertGreaterEqual(audit['cases'], 1716)
        self.assertEqual(audit['failures'], [])
        self.assertGreaterEqual(audit['minimum_horizontal_size'], 12)
        self.assertEqual(len(audit['archives']), 4)
        self.assertFalse(audit['updated_game_capture'])

    def test_guard_alignment_and_capacity_failures_are_atomic(self):
        for address, expected in layout.GUARDS:
            for displacement in range(0, len(bytes.fromhex(expected)), 4):
                with self.subTest(guard=hex(address), displacement=displacement):
                    changed = bytearray(self.original)
                    changed[address - 0x10000 + displacement] ^= 1
                    code = bytearray(b'\xaa' * 16)
                    with self.assertRaisesRegex(ValueError, 'context mismatch'):
                        layout.append_code(changed, code)
                    self.assertEqual(code, bytearray(b'\xaa' * 16))
        for length in (0, 1, 5, 16, 100):
            code = bytearray(length)
            patches, audit = layout.append_code(self.original, code)
            self.assertEqual(len(patches), 1)
            self.assertEqual(int(audit['bridge'], 16) % 16, 0)
            self.assertEqual(len(code) % 16, 0)
        changed = bytearray(self.original)
        changed[layout.CODE_BASE - 0x10000] = 1
        with self.assertRaisesRegex(ValueError, 'zero-filled'):
            layout.append_code(changed, bytearray())
        code = bytearray(layout.CODE_LIMIT - layout.CODE_BASE - 16)
        before = bytes(code)
        with self.assertRaisesRegex(ValueError, 'code gap'):
            layout.append_code(self.original, code)
        self.assertEqual(bytes(code), before)

    def test_scoped_patch_keeps_quantity_and_selection_code(self):
        patches, audit = layout.append_code(self.original, bytearray())
        self.assertEqual([offset for offset, value in patches], [0x16148])
        changed = bytearray(self.original)
        offset, payload = patches[0]
        changed[offset:offset + len(payload)] = payload
        for start, end in ((0x2609c, 0x26148), (0x2614c, 0x26200)):
            self.assertEqual(changed[start - 0x10000:end - 0x10000],
                             self.original[start - 0x10000:end - 0x10000])
        self.assertTrue(audit['preserves_selected_colors'])
        self.assertTrue(audit['quantity_draw_unchanged'])

    def test_deferred_unidentified_preview_restores_original_terminator(self):
        from build import DEFERRED_UI_IDS
        self.assertIn('X0016', DEFERRED_UI_IDS)
        rows = json.loads((ROOT / 'work/translation/en/executable/0000.en.json').read_text('utf8'))['translations']
        english = next(row['en'] for row in rows if row['id'] == 'X0016')
        encoded = english.encode('utf8') + b'\0'
        self.assertEqual(encoded[:10], b'Unidentifi')
        self.assertNotIn(0, encoded[:10])
        for address in (0x3eb4b0, 0x3faa98, 0x408e48, 0x40a718):
            copied = self.original[address - 0x10000:address - 0x10000 + 10]
            self.assertEqual(copied[-1], 0)
            self.assertNotIn(0, copied[:-1])
            # The existing byte-content late alias now receives the complete,
            # correctly terminated original label rather than a truncated EN.
            aliases = {copied[:-1]: english}
            self.assertEqual(aliases[copied.split(b'\0', 1)[0]], 'Unidentified')


if __name__ == '__main__':
    unittest.main()
