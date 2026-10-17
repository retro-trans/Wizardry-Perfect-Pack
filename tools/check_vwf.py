"""Audit native variable-width font support. Default: read-only dry run.

Checks the original PowerPC instructions, font imports and OTF metrics.
The layout model and preview are reconstructions, not execution of the game.
--write saves an audit, ASCII metrics and a font preview. No game patch.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from capstone import Cs, CS_ARCH_PPC, CS_MODE_64, CS_MODE_BIG_ENDIAN
from elftools.elf.elffile import ELFFile
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
EXE_HASH = '2e23b466028ac0a18f7f46522fe1847d5c918a129605a2bdc1c56ca31da82bba'
TOC = 0x488530


def f32(value):
    return struct.unpack('>f', struct.pack('>f', value))[0]


class Audit:
    def __init__(self, path):
        self.data = path.read_bytes()
        if hashlib.sha256(self.data).hexdigest() != EXE_HASH:
            raise ValueError('Unknown executable; addresses must be traced again for this version')
        with path.open('rb') as stream:
            self.segments = [(s['p_vaddr'], s['p_offset'], s['p_filesz'])
                             for s in ELFFile(stream).iter_segments() if s['p_type']=='PT_LOAD']
        self.md = Cs(CS_ARCH_PPC, CS_MODE_64 | CS_MODE_BIG_ENDIAN)
        self.checks = []

    def read(self, address, size):
        for va, off, length in self.segments:
            if va <= address and address+size <= va+length:
                return self.data[off+address-va:off+address-va+size]
        raise ValueError('Address is not in file-backed load data: %x' % address)

    def u32(self, address):
        return struct.unpack('>I', self.read(address, 4))[0]

    def insn(self, address, mnemonic, operands):
        insns = list(self.md.disasm(self.read(address, 4), address))
        if len(insns)!=1 or (insns[0].mnemonic, insns[0].op_str)!=(mnemonic, operands):
            raise ValueError('Instruction mismatch at %x' % address)
        self.checks.append(dict(address=hex(address), instruction=mnemonic+' '+operands))


def cache_width(units, em):
    # Native code truncates h_advance + 0.9999, effectively ceiling ordinary
    # positive advances. This model supplies h_advance from OTF hmtx at 32px.
    return int(f32(f32(units*32/em)+f32(0.9999)))


def pen_positions(text, size, widths, queued=False):
    """Model the observed integer and queued advance rules for plain ASCII."""
    x, y, positions = 0.0, 0, []
    for char in text:
        if char == '\n':
            x, y = 0.0, y+size+4
        elif char == ' ':
            value = f32(x + f32(size*0.5))
            x = value if queued else int(value)
        else:
            positions.append(dict(character=char, x=int(x), y=y))
            advance = f32(f32(size*widths[char])/32)
            x = f32(x+advance) if queued else int(x)+int(advance)
    return positions, x


def preview(path, font_path, widths):
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new('RGB', (1040, 360), '#121925')
    draw = ImageDraw.Draw(image)
    label = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 18)
    draw.text((28, 16), 'Existing game font: variable-width Latin', font=label, fill='#edf3ff')
    draw.text((28, 45), 'Reconstruction using the bundled font; not an in-game screenshot', font=label, fill='#a7b6ce')
    for row, (sample, size) in enumerate([('iiiiiiii', 32), ('WWWWWWWW', 32),
                                        ('Wizardry: Prisoners of the Lost City', 24),
                                        ('Illusion, magic, and forgotten memories.', 24)]):
        top = 94+row*59
        font = ImageFont.truetype(str(font_path), size)
        positions, end = pen_positions(sample, size, widths)
        draw.text((28, top+5), '%dpx' % size, font=label, fill='#a7b6ce')
        for p in positions:
            draw.text((110+p['x'], top), p['character'], font=font, fill='#f4eee0')
        draw.line((110,top+43,110+int(end),top+43), fill='#6bd4b4', width=2)
        draw.text((max(690,132+int(end)), top+7), 'model width %dpx' % end, font=label, fill='#6bd4b4')
    image.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'work/source/NPJB00162/USRDIR')
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    audit = Audit(args.source/'EBOOT.elf')
    # Resolve the imported font API from its NID and stub table, not its name alone.
    assert audit.u32(0x3e0b80+14*4) == 0x88be4799
    assert audit.u32(0x45e644+14*4) == 0x3df2e0
    assert audit.u32(TOC-0x3be8) == 0x456fcc
    assert audit.u32(0x456fcc) == 0x40ddf0
    font_name = b'/FOT-UtrilloPro-DB.otf\0'
    assert audit.read(0x40ddf0, len(font_name)) == font_name
    expected = [
        (0x1637c0,'addi','r8, r1, 0x98'),   # glyph metrics output
        (0x1637ec,'bl','0x3dd270'),           # cellFontRenderCharGlyphImage
        (0x163828,'cmplwi','cr7, r26, 0x7f'),
        (0x163834,'lfs','f0, 0xa8(r1)'),     # metrics + 0x10 = h_advance
        (0x163850,'bgt','cr7, 0x1639ac'),    # ASCII bypasses CJK bitmap adjustment
        (0x163948,'lfs','f0, 0xa8(r1)'),
        (0x16394c,'fadds','f0, f0, f30'),
        (0x163954,'fctiwz','f0, f0'),
        (0x16395c,'lwz','r3, 0xc0(r1)'),     # return individual advance
        (0x163b14,'bl','0x163724'),
        (0x163b1c,'stw','r3, 0xc(r31)'),     # cache advance
        (0x163aa0,'lwz','r3, 0xc(r31)'),     # cache hit returns advance
        (0x163e14,'lwz','r3, 0xc(r30)'),
        (0x164004,'lwz','r3, 0xc(r31)'),
        (0x16478c,'bl','0x163a50'),          # measurement uses cached advance
        (0x1647ac,'fmuls','f0, f31, f0'),
        (0x1647b0,'fmuls','f0, f0, f29'),
        (0x1647c0,'add','r29, r29, r0'),
        (0x164b60,'bl','0x163b58'),          # direct drawing uses same cache
        (0x164b80,'fmuls','f0, f31, f0'),
        (0x164b94,'add','r31, r31, r0'),
        (0x165240,'bl','0x163eb0'),          # queued drawing uses same cache
        (0x165264,'fmuls','f0, f31, f0'),
        (0x165268,'fmadds','f29, f0, f26, f29'),
        (0x1648a4,'fmadds','f0, f31, f0, f13'),  # half-em spaces
        (0x16486c,'addi','r31, r31, 1'),    # measurement skips @...r controls
        (0x164884,'b','0x164704'),
    ]
    # Each expected instruction is checked in this edition. Local font code
    # moved by 0x5cc; the imported glyph API stub has its own traced address.
    for address, mnemonic, operands in expected:
        import re
        def destination(match):
            old=int(match[0],16)
            return hex(0x3df2e0 if old==0x3dd270 else old+0x5cc)
        operands=re.sub(r'0x[0-9a-f]{5,}',destination,operands)
        audit.insn(address+0x5cc, mnemonic, operands)
    constants = {hex(d): struct.unpack('>f', audit.read(TOC+d,4))[0]
                 for d in (-0x3c34,-0x3c30,-0x3c10,-0x3c0c)}
    assert list(constants.values()) == [32.0, f32(0.9999), 0.5, 1/32]
    font_path = args.source/'FOT-UtrilloPro-DB.otf'
    with TTFont(str(font_path)) as font:
        cmap, em = font.getBestCmap(), font['head'].unitsPerEm
        assert all(code in cmap for code in range(32,127))
        from check_translation import read_english
        texts = [text for row in read_english().values()
                 for text in [row['en'] or '']+[r['en'] for r in row.get('reference_overrides',[])]]
        used = {ord(ch) for text in texts for ch in text if ord(ch) >= 32}
        unsupported = sorted(used-set(cmap))
        assert not unsupported, 'English glyphs absent from native font: '+str(unsupported)
        advances = {chr(c):font['hmtx'][cmap[c]][0] for c in range(32,127)}
        assert not font['post'].isFixedPitch and advances['i'] < advances['W']
        widths = {ch:cache_width(w,em) for ch,w in advances.items()}
        cases = 0
        for size in (16,20,24,28,32):
            for text in ('iWiWiW','Wizardry','Prisoners of the Lost City',
                         'Illusion WWW 123','.,:;!?-()[]','iii WWW iii'):
                direct, end = pen_positions(text,size,widths)
                queued, _ = pen_positions(text,size,widths,True)
                assert len(direct)==len(queued)==len(text.replace(' ',''))
                assert direct[0]['x']==queued[0]['x']==0
                assert all(a['x']<=b['x'] for a,b in zip(direct,queued))
                assert all(abs(a['x']-b['x'])<len(text) for a,b in zip(direct,queued))
                cases += 1
        report = dict(result='native_variable_width_supported_static_audit',
            executable_sha256=EXE_HASH, font_sha256=hashlib.sha256(font_path.read_bytes()).hexdigest(),
            instruction_checks=len(audit.checks), layout_model_cases=cases,
            printable_ascii_codepoints=95, english_codepoints_checked=len(used), unsupported_english_codepoints=unsupported,
            distinct_ascii_advances=len(set(advances.values())),
            units_per_em=em, fixed_pitch=bool(font['post'].isFixedPitch),
            sample_font_units={c:advances[c] for c in ('i','l','I','M','W',' ')},
            modeled_widths_at_32px={t:int(pen_positions(t,32,widths)[1]) for t in ('iiiiiiii','WWWWWWWW')},
            model_basis='OTF hmtx normalized to 32px, native rounding/scaling and half-em spaces',
            constants=constants, checks=audit.checks, game_files_changed=False,
            native_cpu_execution_verified=False, in_game_visual_check=False,
            limitations=['Static instruction/data-flow checks plus a layout model; not a full game or CPU execution test.',
                         'Pixel appearance, line wrapping, clipping and every call site remain unverified in game.',
                         'Queued drawing keeps fractional advances; integer measurement rounds per glyph.',
                         'Measurement returns final-line width, not maximum-line width.',
                         'Kerning support has not been established.'])
        print(json.dumps({k:v for k,v in report.items() if k!='checks'},indent=2))
        if not args.write:
            print('Dry run: nothing written. Use --write to save the audit, metrics and preview.')
            return
        out = ROOT/'work/output/vwf'
        out.mkdir(parents=True,exist_ok=True)
        (out/'verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        target = ROOT/'work/font'
        target.mkdir(parents=True,exist_ok=True)
        (target/'native_vwf.en.json').write_text(json.dumps(dict(font=font_path.name,
            source_sha256=report['font_sha256'], units_per_em=em, native_cache_size=32,
            space_em=0.5, advance_source='hmtx; model only until runtime measured',
            ascii={c:dict(units=advances[c],modeled_cache_advance=widths[c]) for c in advances}),indent=2)+'\n',encoding='utf-8')
        preview(out/'native_font_preview.png',font_path,widths)
        print('Saved the audit, ASCII metrics and reconstructed font preview.')


if __name__=='__main__':
    main()
