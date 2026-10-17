"""Synthetic hybrid ISO/Joliet/UDF fixtures, independent of game assets."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest

import iso_overlay as layout


B = 2048


def crc16(data):
    value = 0
    for byte in data:
        value ^= byte << 8
        for _ in range(8):
            value = ((value << 1) ^ (0x1021 if value & 0x8000 else 0)) & 0xffff
    return value


def tag(data, kind, location, length=None):
    if length is None:
        length = len(data) - 16
    struct.pack_into('<HHBBHHHI', data, 0, kind, 3, 0, 0, 0, crc16(data[16:16 + length]), length, location)
    data[4] = sum(data[:4] + data[5:16]) & 255
    return bytes(data)


def record(name, sector, size, flags=0, joliet=False):
    rawname = name if isinstance(name, bytes) else (name + ('' if flags & 2 else ';1')).encode('utf-16-be' if joliet else 'ascii')
    data = bytearray((33 + len(rawname) + 1) & ~1)
    data[0] = len(data)
    struct.pack_into('<I', data, 2, sector)
    struct.pack_into('>I', data, 6, sector)
    struct.pack_into('<I', data, 10, size)
    struct.pack_into('>I', data, 14, size)
    data[25] = flags
    struct.pack_into('<H', data, 28, 1)
    struct.pack_into('>H', data, 30, 1)
    data[32] = len(rawname)
    data[33:33 + len(rawname)] = rawname
    return data


def fixture(root):
    original, package = root / 'original.iso', root / 'english.pkg'
    image = bytearray(800 * B)
    dirs = ['', '/PS3_GAME', '/PS3_GAME/PKGDIR', '/PS3_GAME/PKGDIR/PKG00',
            '/PS3_GAME/PKGDIR/PKG01', '/PS3_UPDATE']
    payloads = {'/PS3_GAME/PKGDIR/PKG00/INSTALL.PKG': b'other game' * 60,
                layout.TARGET: bytes(range(251)) * 24,
                '/PS3_UPDATE/PS3UPDAT.PUP': b'unchanged update' * 300}
    extents = {dirs[3] + '/INSTALL.PKG': [(544 * B, len(payloads[dirs[3] + '/INSTALL.PKG']))],
               layout.TARGET: [(548 * B, 4096), (552 * B, len(payloads[layout.TARGET]) - 4096)],
               '/PS3_UPDATE/PS3UPDAT.PUP': [(556 * B, len(payloads['/PS3_UPDATE/PS3UPDAT.PUP']))]}
    for name, payload in payloads.items():
        cursor = 0
        for offset, length in extents[name]:
            image[offset:offset + length] = payload[cursor:cursor + length]
            cursor += length
    nodes = dirs + list(payloads)
    children = lambda path: [n for n in nodes if n and str(Path(n).parent).replace('\\', '/') == (path or '/')]
    for descriptor, start, joliet in [(16, 300, False), (17, 330, True)]:
        vd = bytearray(B)
        vd[:7] = bytes([2 if joliet else 1]) + b'CD001\1'
        struct.pack_into('<I', vd, 80, 800)
        struct.pack_into('>I', vd, 84, 800)
        struct.pack_into('<H', vd, 128, B)
        struct.pack_into('>H', vd, 130, B)
        if joliet:
            vd[88:91] = b'%/E'
        rr = record(b'\0', start, B, 2)
        vd[156:156 + len(rr)] = rr
        image[descriptor * B:(descriptor + 1) * B] = vd
        for i, directory in enumerate(dirs):
            parent = str(Path(directory).parent).replace('\\', '/') if directory else ''
            if parent == '/':
                parent = ''
            raw = record(b'\0', start + i, B, 2) + record(b'\1', start + dirs.index(parent), B, 2)
            for child in children(directory):
                name = child.rsplit('/', 1)[-1]
                if child in dirs:
                    raw += record(name, start + dirs.index(child), B, 2, joliet)
                else:
                    for j, (offset, length) in enumerate(extents[child]):
                        raw += record(name, offset // B, length, 128 if j + 1 < len(extents[child]) else 0, joliet)
            image[(start + i) * B:(start + i) * B + len(raw)] = raw
    for sector, ident in [(18, b'CD001'), (19, b'BEA01'), (20, b'NSR03'), (21, b'TEA01')]:
        image[sector * B:sector * B + 7] = bytes([255 if sector == 18 else 0]) + ident + b'\1'
    struct.pack_into('>IIIIII', image, 0, 2, 0, 0, 511, 544, 799)
    image[B:B + 12] = b'PlayStation3'
    # UDF physical partition0 starts352; map1 metadata file starts384.
    def put(sector, data):
        image[sector * B:sector * B + len(data)] = data
    pd = bytearray(B)
    struct.pack_into('<II', pd, 188, 352, 447)
    lvd = bytearray(B)
    struct.pack_into('<I', lvd, 212, B)
    struct.pack_into('<IIH', lvd, 248, B, 0, 1)
    struct.pack_into('<II', lvd, 264, 70, 2)
    struct.pack_into('<II', lvd, 432, 4096, 96)
    maps = bytearray(70)
    maps[:2] = b'\1\6'
    maps[6:8] = b'\2\x40'
    maps[11:11 + len(b'*UDF Metadata Partition')] = b'*UDF Metadata Partition'
    struct.pack_into('<II', maps, 46, 0, 416)
    lvd[440:510] = maps
    for base in (32, 64):
        for i, kind in enumerate([1, 4, 5, 6, 7, 8]):
            data = bytearray(pd if kind == 5 else lvd if kind == 6 else bytearray(B))
            put(base + i, tag(data, kind, base + i, 494 if kind == 6 else 496))
    lvid = bytearray(B)
    struct.pack_into('<I', lvid, 28, 1)
    struct.pack_into('<II', lvid, 72, 2, 46)
    struct.pack_into('<II', lvid, 88, 447, 32)
    put(96, tag(lvid, 9, 96, 126))
    put(97, tag(bytearray(B), 8, 97, 496))
    anchor = bytearray(B)
    struct.pack_into('<IIII', anchor, 16, 16 * B, 32, 16 * B, 64)
    put(256, tag(anchor, 2, 256, 496))
    put(799, tag(bytearray(anchor), 2, 799, 496))
    for physical, loc, kind in [(352, 0, 250), (768, 416, 251)]:
        data = bytearray(B)
        data[27] = kind
        struct.pack_into('<QQ', data, 56, 65536, 32)
        struct.pack_into('<II', data, 168, 0, 8)
        struct.pack_into('<II', data, 176, 65536, 32)
        put(physical, tag(data, 261, loc, 168))
    assigned, nextblock = {}, 2
    for node in nodes:
        assigned[node] = (nextblock, nextblock + 1 if node in dirs else None)
        nextblock += 2 if node in dirs else 1
    fsd = bytearray(B)
    struct.pack_into('<IIH', fsd, 400, B, assigned[''][0], 1)
    put(384, tag(fsd, 256, 0, 496))
    for node in nodes:
        block, dataloc = assigned[node]
        data = bytearray(B)
        data[27] = 4 if node in dirs else 5
        if node in dirs:
            def fid(name, child, parent=False):
                encoded = b'' if parent else b'\x08' + name.encode()
                raw = bytearray((38 + len(encoded) + 3) & ~3)
                struct.pack_into('<H', raw, 16, 1)
                raw[18] = (10 if parent else 2 if child in dirs else 0)
                raw[19] = len(encoded)
                struct.pack_into('<IIH', raw, 20, B, assigned[child][0], 1)
                raw[38:38 + len(encoded)] = encoded
                return tag(raw, 257, dataloc)
            directory = fid('', node, True)
            for child in children(node):
                directory += fid(child.rsplit('/', 1)[-1], child)
            put(384 + dataloc, directory)
            struct.pack_into('<QQ', data, 56, len(directory), 1)
            struct.pack_into('<II', data, 168, 0, 8)
            struct.pack_into('<II', data, 176, len(directory), dataloc)
            adlen = 8
        else:
            struct.pack_into('<H', data, 34, 1)
            struct.pack_into('<QQ', data, 56, len(payloads[node]), (len(payloads[node]) + B - 1) // B)
            adlen = len(extents[node]) * 16
            struct.pack_into('<II', data, 168, 0, adlen)
            for i, (offset, length) in enumerate(extents[node]):
                struct.pack_into('<IIH', data, 176 + i * 16, length, offset // B - 352, 0)
        put(384 + block, tag(data, 261, block, 160 + adlen))
    original.write_bytes(image)
    replacement = bytearray(payloads[layout.TARGET] + b'appended translation' * 100)
    replacement[100:110] = b'ENGLISH!!!'
    package.write_bytes(replacement)
    package.with_suffix('.verification.json').write_text(json.dumps(dict(
        result='verified', version='0.1.11', output_sha256=hashlib.sha256(replacement).hexdigest(),
        source_sha256=hashlib.sha256(payloads[layout.TARGET]).hexdigest(),
        rpcs3_aligned_table_and_names_verified=True)), encoding='utf8')
    return original, package


class IsoOverlayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original, self.package = fixture(self.root)
        self.original_bytes = self.original.read_bytes()
        self.source_hash = hashlib.sha256(self.original_bytes).hexdigest()
        self.output = self.root / 'out' / 'english.iso'

    def plan(self):
        return layout.plan(self.original, self.package, self.source_hash)

    def test_source_all_six_filesystem_routes_agree_and_plan_read_only(self):
        p = self.plan()
        self.assertFalse(self.output.exists())
        self.assertEqual(self.original.read_bytes(), self.original_bytes)
        self.assertEqual(p['first_extent'], (548 * B, 4096))
        self.assertEqual(p['tail_extent'][0], len(self.original_bytes))
        self.assertGreater(p['size'], len(self.original_bytes))
        self.assertEqual(len(p['anchors']), 2)

    def test_round_trip_preserves_all_other_files_and_original_bytes(self):
        p = self.plan()
        audit = layout.write_iso(p, self.output)
        self.assertEqual(audit['result'], 'verified')
        self.assertTrue(audit['iso9660_joliet_udf_main_mirror_reserve_agree'])
        self.assertTrue(audit['source_unchanged'])
        self.assertEqual(len(audit['files']), 3)
        self.assertEqual(sum(r['selected'] for r in audit['files']), 1)
        self.assertEqual(self.original.read_bytes(), self.original_bytes)
        self.assertTrue(self.output.with_suffix('.verification.json').exists())
        self.assertTrue(self.output.with_suffix('.audit.txt').exists())

    def test_independent_crc_reference_and_both_endian_updates(self):
        p = self.plan()
        for change in p['patches'].values():
            b = change['after']
            if layout.u16(b, 0) in (5, 9, 261):
                self.assertEqual(layout.u16(b, 8), crc16(b[16:16 + layout.u16(b, 10)]))
                self.assertEqual(b[4], sum(b[:4] + b[5:16]) & 255)
        for n in (16, 17):
            b = p['patches'][n]['after']
            self.assertEqual(struct.unpack_from('<I', b, 80)[0], p['size'] // B)
            self.assertEqual(struct.unpack_from('>I', b, 84)[0], p['size'] // B)

    def test_corruption_of_other_file_outside_payload_udf_joliet_anchor_detected(self):
        p = self.plan()
        layout.write_iso(p, self.output)
        correct = self.output.read_bytes()
        offsets = [556 * B + 2, 200 * B + 1, 17 * B + 80,
                   next(c['sector'] for c in p['patches'].values() if c['label'].startswith('UDF PKG01')) * B + 56,
                   max(p['anchors']) * B + 12, p['tail_extent'][0] + 6]
        for offset in offsets:
            with self.subTest(offset=offset):
                bad = bytearray(correct)
                bad[offset] ^= 1
                self.output.write_bytes(bad)
                with self.assertRaises(ValueError):
                    layout.verify(p, self.output)

    def test_manifest_identity_sourcehash_and_changed_input_guards(self):
        with self.assertRaisesRegex(ValueError, 'source ISO hash'):
            layout.plan(self.original, self.package)
        p = self.plan()
        self.package.write_bytes(self.package.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'Input changed'):
            layout.write_iso(p, self.output)
        self.assertFalse(self.output.exists())

    def test_existing_output_and_determinism(self):
        p = self.plan()
        layout.write_iso(p, self.output)
        with self.assertRaisesRegex(ValueError, 'already exists'):
            layout.write_iso(p, self.output)
        second = self.root / 'second.iso'
        layout.write_iso(p, second)
        self.assertEqual(self.output.read_bytes(), second.read_bytes())

    def test_source_udf_mirror_and_reserve_metadata_are_required(self):
        for offset in (768 * B + 56, 67 * B + 264, 66 * B + 192):
            with self.subTest(offset=offset):
                bad = bytearray(self.original_bytes)
                bad[offset] ^= 1
                self.original.write_bytes(bad)
                with self.assertRaisesRegex(ValueError, 'UDF'):
                    layout.plan(self.original, self.package, hashlib.sha256(bad).hexdigest())
        self.original.write_bytes(self.original_bytes)


if __name__ == '__main__':
    unittest.main()
