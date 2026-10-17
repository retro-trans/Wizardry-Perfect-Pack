"""Small independently constructed retail-format fixtures; no game data needed."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import pkg_overlay as layout
from pkg_read import Package, PKG_KEY


def elf_bytes(size=80):
    data = bytearray(b'\x7fELF\x02\x02' + b'\0' * (size - 6))
    struct.pack_into('>H', data, 18, 21)
    return bytes(data)


class PackageOverlayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original = self.root / 'original.pkg'
        self.build = self.root / 'build'
        self.overlay = self.build / 'overlay'
        self.overlay.mkdir(parents=True)
        self.payloads = {
            'USRDIR/EBOOT.BIN': b'SCE\0' + b'boot' * 10,
            'USRDIR/data/same.enc': b'original-original',
            'USRDIR/data/shrink.enc': b'abcdefghij',
            'USRDIR/data/untouched.edat': b'keep authentic encrypted bytes' * 50,
            'USRDIR/movie/opening.pam': bytes(range(256)) * 32,
        }
        names = ['USRDIR', 'USRDIR/data', 'USRDIR/movie'] + list(self.payloads)
        size = 0x5000
        data = bytearray(b'\xa7' * size)
        name_at, payload_at = len(names) * 32, 0x800
        for i, name in enumerate(names):
            name_at = layout.align16(name_at)
            encoded = name.encode()
            data[name_at:name_at + len(encoded)] = encoded
            directory = name not in self.payloads
            payload = self.payloads.get(name, b'')
            offset = 0 if directory else payload_at
            struct.pack_into('>IIQQII', data, i * 32, name_at, len(encoded), offset, len(payload), 0x80000004 if directory else 0x80000003, 0)
            name_at += len(encoded)
            if not directory:
                data[offset:offset + len(payload)] = payload
                payload_at = layout.align16(offset + len(payload))
        header = bytearray(0x180)
        header[:8] = bytes.fromhex('7f504b4780000001')
        struct.pack_into('>III', header, 8, 0xc0, 1, 16)
        struct.pack_into('>IQQQ', header, 0x14, len(names), 0x180 + size + 96, 0x180, size)
        header[0x30:0x30 + len(layout.CONTENT_ID)] = layout.CONTENT_ID.encode()
        header[0x70:0x80] = bytes(range(16))
        struct.pack_into('>IIQ', header, 0xc0, 4, 8, size)
        cipher = Cipher(algorithms.AES(PKG_KEY), modes.CTR(bytes(range(16)))).encryptor()
        self.original.write_bytes(header + cipher.update(bytes(data)) + cipher.finalize() + b'opaque signature' * 6)
        # Six copies of this 16-byte string form the 96-byte opaque trailer.
        assert len(b'opaque signature') == 16
        self.targets = {
            'USRDIR/EBOOT.elf': elf_bytes(),
            'USRDIR/data/same.enc': b'translated-text!!',
            'USRDIR/data/shrink.enc': b'tiny',
            'USRDIR/data/new.enc': b'new plaintext dungeon',
            'USRDIR/movie/opening.pam': bytes(reversed(range(256))) * 32,
        }
        self.write_manifest()
        self.output = self.root / 'output' / 'english.pkg'

    def write_manifest(self):
        files = []
        for name, payload in self.targets.items():
            path = self.overlay / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            files.append(dict(file=name, bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest()))
        self.manifest = dict(version='0.1.10', target='NPJB00162', files=files)
        (self.build / 'manifest.json').write_text(json.dumps(self.manifest), encoding='utf8')

    def test_plan_is_read_only_and_classifies_slots(self):
        before = self.original.read_bytes()
        p = layout.plan(self.original, self.build)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.original.read_bytes(), before)
        rows = {r['path']: r for r in p['changed']}
        self.assertEqual(rows['USRDIR/EBOOT.BIN']['placement'], 'append')
        self.assertEqual(rows['USRDIR/data/new.enc']['placement'], 'append')
        self.assertEqual(rows['USRDIR/movie/opening.pam']['placement'], 'original slot')
        self.assertEqual(rows['USRDIR/data/shrink.enc']['placement'], 'original slot')
        self.assertGreaterEqual(p['name_start'], p['old_size'])
        self.assertLess(p['total'], self.original.stat().st_size + 1000)

    def test_round_trip_all_payloads_ciphertext_and_boot_mapping(self):
        p = layout.plan(self.original, self.build)
        before = self.original.read_bytes()
        audit = layout.write_package(p, self.output)
        self.assertEqual(audit['result'], 'verified')
        self.assertFalse(audit['retail_authentication_valid'])
        self.assertTrue(audit['source_unchanged'])
        self.assertTrue(audit['rpcs3_aligned_table_and_names_verified'])
        self.assertGreater(audit['unchanged_ciphertext_bytes'], 10000)
        self.assertEqual(self.original.read_bytes(), before)
        pkg = Package(self.output)
        try:
            entries = {e['path']: e for e in pkg.entries}
            self.assertNotIn('USRDIR/EBOOT.elf', entries)
            for name, payload in self.targets.items():
                target = name.replace('EBOOT.elf', 'EBOOT.BIN')
                e = entries[target]
                self.assertEqual(pkg.read(e['offset'], e['size']), payload)
            e = entries['USRDIR/data/untouched.edat']
            self.assertEqual(pkg.read(e['offset'], e['size']), self.payloads[e['path']])
        finally:
            pkg.close()
        self.assertTrue(self.output.with_suffix('.verification.json').exists())
        self.assertTrue(self.output.with_suffix('.audit.txt').exists())

    def test_rebuild_deterministic_and_refuses_existing_output(self):
        p = layout.plan(self.original, self.build)
        layout.write_package(p, self.output)
        second = self.root / 'second.pkg'
        layout.write_package(p, second)
        self.assertEqual(self.output.read_bytes(), second.read_bytes())
        with self.assertRaisesRegex(ValueError, 'already exists'):
            layout.write_package(p, self.output)

    def test_independent_verifier_detects_payload_padding_header_names_and_trailer(self):
        p = layout.plan(self.original, self.build)
        layout.write_package(p, self.output)
        correct = self.output.read_bytes()
        rows = {e['path']: e for e in p['entries']}
        offsets = [p['start'] + rows['USRDIR/movie/opening.pam']['offset'],
                   p['start'] + rows['USRDIR/data/new.enc']['offset'],
                   p['start'] + rows['USRDIR/data/untouched.edat']['offset'],
                   p['start'] + 0x700, 0x90,
                   p['start'] + p['name_start'], len(correct) - 1]
        for offset in offsets:
            with self.subTest(offset=offset):
                bad = bytearray(correct)
                bad[offset] ^= 0x20
                self.output.write_bytes(bad)
                with self.assertRaises((ValueError, UnicodeDecodeError)):
                    layout.verify(p, self.output)
        self.output.write_bytes(correct)

    def test_manifest_path_and_identity_guards(self):
        path = self.build / 'manifest.json'
        original = path.read_text(encoding='utf8')
        variants = [dict(self.manifest, target='NPJB00163'),
                    dict(self.manifest, version='release'),
                    dict(self.manifest, files=self.manifest['files'] + [self.manifest['files'][0]])]
        for manifest in variants:
            path.write_text(json.dumps(manifest), encoding='utf8')
            with self.assertRaises(ValueError):
                layout.plan(self.original, self.build)
        path.write_text(original, encoding='utf8')
        for name in ('../escape', '/absolute', 'USRDIR//double', 'USRDIR/./dot', 'C:/drive', 'USRDIR\\back'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                layout.safe_name(name)
        (self.overlay / 'unmanifested.bin').write_bytes(b'bad')
        with self.assertRaisesRegex(ValueError, 'Unmanifested'):
            layout.plan(self.original, self.build)

    def test_source_and_overlay_change_after_plan_refused_before_creation(self):
        p = layout.plan(self.original, self.build)
        name = self.overlay / 'USRDIR/data/new.enc'
        name.write_bytes(b'different')
        with self.assertRaisesRegex(ValueError, 'Overlay changed'):
            layout.write_package(p, self.output)
        self.assertFalse(self.output.exists())
        self.write_manifest()
        p = layout.plan(self.original, self.build)
        data = bytearray(self.original.read_bytes())
        data[-1] ^= 1
        self.original.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'changed after planning'):
            layout.write_package(p, self.output)
        self.assertFalse(self.output.exists())

    def test_unaligned_ctr_stream_writes_and_chunk_boundary(self):
        p = layout.plan(self.original, self.build)
        # Small test chunks deliberately break AES block boundaries too.
        previous = layout.CHUNK
        layout.CHUNK = 31
        try:
            with (self.root / 'raw').open('wb') as out:
                raw_path = Path(out.name)
                import io
                layout.encrypt_to(out, p, 7, io.BytesIO(bytes(range(251))))
            encrypted = raw_path.read_bytes()[p['start'] + 7:]
            cipher = Cipher(algorithms.AES(PKG_KEY), modes.CTR(p['iv'].to_bytes(16, 'big'))).decryptor()
            decoded = cipher.update(b'\0' * 7 + encrypted)[7:]
            self.assertEqual(decoded, bytes(range(251)))
        finally:
            layout.CHUNK = previous

    def test_expanded_table_cannot_overwrite_first_file(self):
        for i in range(60):
            self.targets['USRDIR/data/new%02d.enc' % i] = b'x'
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, 'table overlaps'):
            layout.plan(self.original, self.build)
        self.assertFalse(self.output.exists())

    def test_wrong_source_identity_and_bad_boot_architecture_refused(self):
        source = self.original.read_bytes()
        bad = bytearray(source)
        bad[0x30 + 16] ^= 1
        self.original.write_bytes(bad)
        with self.assertRaisesRegex(ValueError, 'content ID'):
            layout.plan(self.original, self.build)
        self.original.write_bytes(source)
        self.targets['USRDIR/EBOOT.elf'] = b'wrong executable' * 5
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, 'PPC64 ELF'):
            layout.plan(self.original, self.build)

    def test_names_match_retail_alignment_and_native_ecb_counter_decryption(self):
        source_rows = layout.rpcs3_metadata(self.original)
        self.assertEqual({r['path'] for r in source_rows},
                         {'USRDIR', 'USRDIR/data', 'USRDIR/movie'} | set(self.payloads))
        p = layout.plan(self.original, self.build)
        layout.write_package(p, self.output)
        with self.output.open('rb') as stream:
            # Independent implementation: RPCS3 AES-ECB counter blocks XORed
            # with ciphertext at the requested offset; no intra-block skip.
            def native_read(offset, size):
                stream.seek(p['start'] + offset)
                encrypted = stream.read(size)
                blocks = (size + 15) // 16
                counters = b''.join((p['iv'] + offset // 16 + i).to_bytes(16, 'big') for i in range(blocks))
                aes = Cipher(algorithms.AES(PKG_KEY), modes.ECB()).encryptor()
                keystream = aes.update(counters) + aes.finalize()
                return bytes(a ^ b for a, b in zip(encrypted, keystream))
            table = native_read(0, len(p['table']))
            for i, entry in enumerate(p['entries']):
                no, ns = struct.unpack_from('>II', table, i * 32)
                self.assertEqual(no % 16, 0)
                self.assertEqual(ns, len(entry['path'].encode()))
                self.assertEqual(native_read(no, ns), entry['path'].encode())
            # Demonstrate why Package.read alone missed the original bug.
            first = p['entries'][0]
            no, ns = first['name_offset'], first['name_size']
            pkg = Package(self.output)
            try:
                self.assertNotEqual(native_read(no + 1, ns - 1), pkg.read(no + 1, ns - 1))
            finally:
                pkg.close()


if __name__ == '__main__':
    unittest.main()
