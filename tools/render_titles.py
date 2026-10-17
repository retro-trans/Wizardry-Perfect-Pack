"""Build English logo subtitles from the game's font and existing logo layers.

Default dry run. Only local output is written with --write. The title wordmark,
sword and independent fog strips are retained. The ending reuses the original
clean title wordmark to avoid erasing overlapping lettering. DDS edits replace
only affected BC3 blocks, leaving every other compressed block byte-exact.
"""
import argparse
import io
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from enc_archive import ROOT, unpack, pack


def label(size, text, color='white', glow=False):
    font=ImageFont.truetype(str(ROOT/'work/source/NPJB00162/USRDIR/FOT-UtrilloPro-DB.otf'),size)
    box=font.getbbox(text);width=box[2]-box[0]+24;height=box[3]-box[1]+24
    layer=Image.new('RGBA',(width,height))
    draw=ImageDraw.Draw(layer)
    draw.text((12-box[0],12-box[1]),text,font=font,fill=color,
              stroke_width=1 if glow else 0,stroke_fill='white')
    if glow:
        halo=Image.new('RGBA',layer.size,(50,90,255,0))
        halo.putalpha(layer.getchannel('A').filter(ImageFilter.GaussianBlur(5)))
        halo.alpha_composite(layer)
        return halo
    return layer


def encode_tga(im):
    out=io.BytesIO();im.save(out,format='TGA',compression=None);return out.getvalue()


def bc3_region(original, image, rect):
    out=io.BytesIO();image.save(out,format='DDS',pixel_format='DXT5')
    encoded=out.getvalue()
    if original[84:88]!=b'DXT5' or encoded[84:88]!=b'DXT5' or len(original)!=len(encoded):
        raise ValueError('Unexpected DDS layout')
    result=bytearray(original);x,y,w,h=rect;stride=(image.width+3)//4
    for by in range(y//4,(y+h+3)//4):
        for bx in range(x//4,(x+w+3)//4):
            off=128+(by*stride+bx)*16
            result[off:off+16]=encoded[off:off+16]
    return bytes(result)


def generate():
    source=ROOT/'work/source/NPJB00162/USRDIR/data/texture'
    title=unpack((source/'title.enc').read_bytes())
    ending=unpack((source/'ending.enc').read_bytes())
    title_image=Image.open(io.BytesIO(title[3])).convert('RGBA')
    clean_logo=title_image.crop((0,0,1280,220))
    fog=title_image.crop((350,330,950,405))
    title_en=title_image.copy()
    title_en.paste((0,0,0,0),(340,220,960,325))
    title_en.alpha_composite(fog.resize((600,75)),(340,235))
    subtitle=label(40,'Prisoners of the Lost City',(90,110,255,255),True)
    title_en.alpha_composite(subtitle,((1280-subtitle.width)//2,238))
    # Clean original wordmark avoids destructive guessing where the Japanese
    # ending subtitle overlaps the wordmark's descending strokes.
    ending_en=Image.new('RGBA',(1280,720),(0,0,0,255))
    ending_en.alpha_composite(clean_logo,(0,104))
    ending_en.alpha_composite(fog.resize((600,75)),(340,300))
    ending_en.alpha_composite(subtitle,((1280-subtitle.width)//2,303))
    company=Image.open(io.BytesIO(title[0])).convert('RGBA')
    company.paste((0,0,0,255),(464,408,784,448))
    corporate=label(28,'ACQUIRE Corp.')
    company.alpha_composite(corporate,((1280-corporate.width)//2,407))
    original_title=list(title);original_ending=list(ending)
    title[0]=bc3_region(title[0],company,(464,408,320,40))
    title[3]=encode_tga(title_en)
    ending[0]=encode_tga(ending_en)
    for index,(a,b) in enumerate(zip(original_title,title)):
        if index not in (0,3) and a!=b:raise ValueError('Unrelated title member changed')
    if any(a!=b for a,b in zip(original_ending[1:],ending[1:])):
        raise ValueError('Unrelated ending member changed')
    return {'title.enc':pack(title),'ending.enc':pack(ending)},[
        ('title-subtitle.png',title_en),('ending-subtitle.png',ending_en),('company.png',company)]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write',action='store_true');args=parser.parse_args()
    archives,previews=generate()
    print(json.dumps(dict(archives={name:len(data) for name,data in archives.items()},
                          previews=[name for name,_ in previews],size=[1280,720],
                          subtitle='Prisoners of the Lost City',company='ACQUIRE Corp.'),indent=2))
    if args.write:
        out=ROOT/'work/output/graphics_english'
        out.mkdir(parents=True,exist_ok=True)
        for name,data in archives.items():(out/name).write_bytes(data)
        for name,im in previews:im.save(out/name)
        print('Wrote isolated font-generated title/ending assets.')
    else:print('Dry run: no files written.')


if __name__=='__main__':main()
