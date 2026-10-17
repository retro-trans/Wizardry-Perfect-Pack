"""Read-only regressions for protected source authentication and loader routing."""
import unittest
from check_vwf import Audit
from dungeon_scene import SOURCE, decrypt_scene
from dungeon_patch import PATH_OFFSET,OLD_PATH,NEW_PATH,redirect_loader


class DungeonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.executable=(SOURCE/'EBOOT.elf').read_bytes()
        cls.protected=(SOURCE/'data/obj/Scenes/dun00.edat').read_bytes()

    def test_authentication_rejects_title_metadata_and_ciphertext_changes(self):
        # First establish a known valid tiny archive, then alter each protected
        # component independently. No external licenses or key files are used.
        self.assertTrue(decrypt_scene(self.protected,self.executable,'dun00.edat'))
        for offset in (0x50,0x100,0x110):
            corrupted=bytearray(self.protected);corrupted[offset]^=1
            with self.assertRaises(ValueError):decrypt_scene(bytes(corrupted),self.executable,'dun00.edat')

    def test_loader_literal_is_bounded_and_source_guarded(self):
        result=bytearray(self.executable)
        redirect_loader(self.executable,result)
        self.assertEqual(result[:PATH_OFFSET],self.executable[:PATH_OFFSET])
        self.assertEqual(result[PATH_OFFSET+len(OLD_PATH):],self.executable[PATH_OFFSET+len(OLD_PATH):])
        self.assertEqual(result[PATH_OFFSET:PATH_OFFSET+len(OLD_PATH)],NEW_PATH+b'\0')
        changed=bytearray(self.executable);changed[PATH_OFFSET]^=1
        with self.assertRaises(ValueError):redirect_loader(changed,bytearray(changed))

    def test_plain_extension_uses_normal_size_full_and_partial_reads(self):
        audit=Audit(SOURCE/'EBOOT.elf')
        for address in (0x132dd4,0x13331c):audit.insn(address,'lwz','r4, -0x4868(r2)')
        self.assertEqual(audit.u32(0x488530-0x4868),PATH_OFFSET+0x10000)
        for toc_offset in (-0x5c4c,-0x7edc):
            self.assertEqual(audit.read(audit.u32(0x488530+toc_offset),6),b'.edat\0')
        for address in (0xc22f0,0x1463c,0x1495c):audit.insn(address,'bl','0x27d1bc')
        for address,target in ((0xc22fc,0xc2414),(0x14648,0x147c0),(0x1497c,0x14b04)):
            audit.insn(address,'beq','cr7, '+hex(target))
        for address in (0xc2428,0x147d4):audit.insn(address,'bl','0x3de2c0')


if __name__=='__main__':unittest.main()
