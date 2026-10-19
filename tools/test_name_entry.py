"""Exercise native name-copy boundaries and the original OSK buffer guards."""
import ctypes as C
import random
import struct
import subprocess
import sys
import unittest

from capstone import Cs, CS_ARCH_PPC, CS_MODE_64, CS_MODE_BIG_ENDIAN
from compile_name_entry import ROOT, name_code
import name_entry as layout


class NameEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        folder = ROOT/'work/output/tests'
        folder.mkdir(parents=True, exist_ok=True)
        library = folder/'name_entry.dll'
        subprocess.run([sys.executable, '-m', 'ziglang', 'cc', '-shared', '-O2',
                        '-fno-builtin', str(ROOT/'tools/name_entry.c'), '-o', str(library)], check=True)
        cls.library = C.CDLL(str(library))
        cls.copy = cls.library.set_character_name
        cls.copy.argtypes = [C.c_void_p, C.c_char_p]
        cls.copy.restype = C.c_void_p
        cls.original = (ROOT/'work/source/NPJB00162/USRDIR/EBOOT.elf').read_bytes()

    def check_copy(self, value, wanted):
        storage = (C.c_ubyte*0x280)(*([0xa5]*0x280))
        base = C.addressof(storage)+16
        returned = self.copy(base, value)
        raw = bytes(storage)
        start = 16+layout.NAME_OFFSET
        self.assertEqual(raw[:start], b'\xa5'*start)
        self.assertEqual(raw[start:start+33], wanted+b'\0'*(33-len(wanted)))
        self.assertEqual(raw[start+33:], b'\xa5'*(len(raw)-start-33))
        self.assertEqual(returned, base if value is None else base+layout.NAME_OFFSET)

    def test_reported_name_and_twelve_character_boundary(self):
        for text in ('Vedette', 'Christopher', 'ABCDEFGHIJKL', 'ABCDEFGHIJKLM', ''):
            with self.subTest(text=text):
                self.check_copy(text.encode(), text[:12].encode())

    def test_null_preserves_native_clear_behavior(self):
        self.check_copy(None, b'')

    def test_utf8_does_not_split_a_character_or_overrun_saved_field(self):
        for text in ('é'*13, '界'*12, 'A界'*8, '𐀀'*12):
            wanted = b''
            for char in text[:12]:
                if len(wanted)+len(char.encode())>32: break
                wanted += char.encode()
            self.check_copy(text.encode(), wanted)

    def test_malformed_utf8_stops_before_invalid_sequence(self):
        for tail in (b'\x80', b'\xc0\xaf', b'\xe0\x80\x80', b'\xed\xa0\x80',
                     b'\xf4\x90\x80\x80', b'\xe2\x82', b'\xff'):
            self.check_copy(b'Name'+tail, b'Name')

    def test_random_mixed_names_preserve_neighboring_save_fields(self):
        rng = random.Random(14)
        for _ in range(200):
            text = ''.join(rng.choice('Ab é界𐀀') for _ in range(rng.randrange(35)))
            wanted = b''
            for char in text[:12]:
                if len(wanted)+len(char.encode())>32: break
                wanted += char.encode()
            self.check_copy(text.encode(), wanted)

    def test_osk_struct_fields_and_buffers_are_separate(self):
        # cellOskDialogInputFieldInfo occupies +0xc..+0x17; parameters +0x30..+0x43.
        self.assertGreaterEqual(layout.INITIAL_OFFSET, 0x44)
        self.assertLessEqual(layout.INITIAL_OFFSET+(layout.LIMIT+1)*2, layout.RESULT_OFFSET)
        self.assertLessEqual(layout.RESULT_OFFSET+(layout.LIMIT+1)*2, layout.STATE_BYTES)
        code = bytearray()
        patches, audit = layout.append_code(self.original, code, b'\x4e\x80\x00\x20', 0, 0x5600000)
        values = dict(patches)
        self.assertEqual(struct.unpack('>I', values[0x10c698-0x10000])[0]&0xffff, 12)
        self.assertEqual(struct.unpack('>I', values[0x10c6bc-0x10000])[0]&0xffff, 13)
        self.assertFalse(audit['save_layout_changed'])
        decoded = list(Cs(CS_ARCH_PPC, CS_MODE_64|CS_MODE_BIG_ENDIAN).disasm(code[:12], 0x448090))
        self.assertEqual([(i.mnemonic, i.op_str) for i in decoded[:2]],
                         [('clrldi', 'r3, r3, 0x20'), ('clrldi', 'r4, r4, 0x20')])
        self.assertEqual(decoded[2].mnemonic, 'b')
        bad = bytearray(self.original); bad[0x10c698-0x10000+3] = 7
        with self.assertRaisesRegex(ValueError, 'instruction changed'):
            layout.append_code(bad, bytearray(), b'', 0, 0x5600000)
        bad = bytearray(self.original); bad[layout.STATE_POINTER-0x10000] ^= 1
        with self.assertRaisesRegex(ValueError, 'state pointer changed'):
            layout.append_code(bad, bytearray(), b'', 0, 0x5600000)

    def test_powerpc_object_is_self_contained_and_does_not_change_toc(self):
        code, entry = name_code(ROOT/'work/output/name_entry.o')
        decoded = list(Cs(CS_ARCH_PPC, CS_MODE_64|CS_MODE_BIG_ENDIAN).disasm(code[entry:], 0x448090))
        # LLVM may leave zero alignment padding after the function.
        self.assertFalse(any(code[entry+len(decoded)*4:]))
        self.assertGreater(len(decoded), 0)
        self.assertFalse(any(i.mnemonic in ('bl', 'bctrl', 'blrl') for i in decoded))
        self.assertFalse(any(i.mnemonic.startswith(('std', 'stw', 'sth')) for i in decoded))
        # r2 is the game's TOC; this leaf must neither establish nor overwrite it.
        self.assertFalse(any(i.op_str.split(',')[0] == 'r2' for i in decoded))


if __name__ == '__main__':
    unittest.main()
