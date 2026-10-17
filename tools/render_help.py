"""Render the eight title2.enc English help textures; read-only unless --write.

Uses the supplied game font and English coordinate manifest. Original compressed
DDS blocks outside edits are copied verbatim, preserving the controller diagram,
button glyphs, connecting lines, artwork and existing English legal notices.
Run with the bundled 64-bit Python, Pillow >=12 and lzokay available.
"""
import argparse
from collections import Counter
from functools import lru_cache
import hashlib
import io
import json
from pathlib import Path
import struct

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from enc_archive import pack, unpack

ROOT = Path(__file__).resolve().parents[1]
COLORS = dict(white=(255,255,255,255), cyan=(106,223,255,255),
              gold=(255,222,0,255), red=(255,80,80,255), gray=(145,145,145,255))
# All coordinates below are measured from the decoded 1280x720 originals.
CONTROLLER = (480,256,800,480)  # DXT-block aligned, includes the full silhouette.
CONTROLLER_POLYGON = [(531,260),(575,260),(582,294),(628,299),(672,299),
    (697,294),(701,261),(747,261),(752,284),(761,306),(777,350),
    (792,394),(800,445),(794,463),(775,477),(749,474),(719,451),
    (706,440),(694,462),(676,466),(654,451),(640,439),(621,462),
    (601,468),(578,453),(570,440),(548,465),(527,476),(507,476),
    (490,464),(480,445),(483,412),(489,374),(499,339),(515,300),(522,278)]
FRONT_PANELS = {5:[(76,148,464,308),(76,404,388,528)],
                6:[(152,476,468,604),(884,360,1156,604)]}
FOOTER_ICONS=[(252,640,310,676),(548,636,588,676),(784,640,840,676)]
ICON_BOXES={
    3:[(84,208,118,232),(140,208,176,232),(188,208,236,232),(248,208,284,232),
       (228,352,264,388),(220,492,248,524),(1012,172,1076,200),
       (1048,284,1124,312),(1092,412,1120,440),(980,484,1008,516),(1012,556,1044,588)],
    4:[(84,192,116,216),(268,192,296,220),(216,288,252,312),
       (224,352,260,392),(304,396,340,432),(236,468,292,488),
       (260,540,288,568),(1052,288,1084,312),(1092,380,1120,408),
       (984,468,1012,500),(1016,556,1048,588)],
    5:[(108,440,140,480),(108,484,140,516),(1108,252,1136,284),
       (1064,344,1096,380),(1016,444,1048,476),(1116,536,1148,572)],
    6:[(184,516,216,552),(184,556,216,592)]
}
OVERRIDES = {
    # Give long translated safety paragraphs the unused vertical gap below them.
    (1,'seizure_body'):[70,190,1145,72],
    (1,'stop_body'):[70,340,1145,68],
    # Entire title-panel interiors are available, not just Japanese glyph widths.
    (3,'town_title'):[470,70,350,43],
    (4,'dungeon_title'):[470,70,350,43],
    (4,'l3_note'):[270,488,108,15],
    (4,'auto_combo_suffix'):[296,196,42,22],
    (4,'map_requirement'):[83,568,292,36],
    (5,'ranking_title'):[445,70,395,43],
    (5,'top_ten'):[914,346,145,36],
    (6,'registration_title'):[445,61,395,43],
    (6,'background_appearance'):[205,404,95,33],
    (7,'contact_title'):[480,109,344,43],
    (7,'phone'):[510,280,300,36],
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def wrap(text,font,width):
    lines=[]
    for paragraph in text.split('\n'):
        if not paragraph:
            lines.append('');continue
        line=''
        for word in paragraph.split():
            candidate=(line+' '+word).strip()
            if line and font.getlength(candidate)>width:
                lines.append(line);line=word
            else: line=candidate
        lines.append(line)
    return lines


def fit(text,font_path,size,width,height,minimum=12):
    # No translation shortening. Font size and line wrapping are the only changes.
    for px in range(size,minimum-1,-1):
        font=ImageFont.truetype(str(font_path),px)
        lines=wrap(text,font,width)
        boxes=[font.getbbox(line or 'Ag') for line in lines]
        line_height=max(box[3]-box[1] for box in boxes)+max(2,px//7)
        total=line_height*len(lines)-max(2,px//7)
        longest=max((font.getlength(line) for line in lines),default=0)
        if longest<=width and total<=height:
            return font,lines,line_height,total
    raise ValueError('Text cannot fit without shrinking below %d px: %r' % (minimum,text))


@lru_cache(maxsize=4)
def controller_mask(size):
    mask=Image.new('L',size,0)
    ImageDraw.Draw(mask).polygon(CONTROLLER_POLYGON,fill=255)
    mask=mask.filter(ImageFilter.MaxFilter(7))
    # A DXT5 block must remain intact whenever it touches controller artwork.
    out=Image.new('L',size,0);d=ImageDraw.Draw(out)
    bounds=mask.getbbox()
    for by in range(bounds[1]//4,(bounds[3]+3)//4):
        for bx in range(bounds[0]//4,(bounds[2]+3)//4):
            box=(bx*4,by*4,bx*4+4,by*4+4)
            if mask.crop(box).getbbox():d.rectangle((box[0],box[1],box[2]-1,box[3]-1),fill=255)
    return out


@lru_cache(maxsize=8)
def icon_mask(size,member):
    out=Image.new('L',size,0);d=ImageDraw.Draw(out)
    boxes=ICON_BOXES.get(member,[])+(FOOTER_ICONS if member>=3 else [])
    for left,top,right,bottom in boxes:
        box=(left//4*4,top//4*4,(right+3)//4*4,(bottom+3)//4*4)
        d.rectangle((box[0],box[1],box[2]-1,box[3]-1),fill=255)
    return out


def allowed_mask(size,box,member,background=False):
    mask=Image.new('L',size,0)
    ImageDraw.Draw(mask).rectangle((box[0],box[1],box[2]-1,box[3]-1),fill=255)
    if member in (3,4,5,6):
        mask=ImageChops.subtract(mask,controller_mask(size))
    mask=ImageChops.subtract(mask,icon_mask(size,member))
    if background:
        for protected in FRONT_PANELS.get(member,[]):
            ImageDraw.Draw(mask).rectangle((protected[0],protected[1],protected[2]-1,protected[3]-1),fill=0)
    return mask


def background_color(image,box,dimmed):
    if not dimmed:return (0,0,0,255)
    # Baked dimmed screenshot lettering needs an opaque, subdued replacement
    # patch. Recovering scene pixels beneath its Japanese glyphs is impossible.
    pixels=image.crop(box).convert('RGB').get_flattened_data()
    dark=[p for p in pixels if max(p)<100]
    color=Counter(dark).most_common(1)[0][0] if dark else (16,16,16)
    return (*color,255)


def render_region(image,asset,region,font_path,report,partial=False,source=None):
    member=asset['member'];rid=region.get('id', 'partial_%d' % len(report))
    rect=OVERRIDES.get((member,rid),region['rect'])
    x,y,w,h=rect; box=(x,y,x+w,y+h)
    background=rid.startswith('background_') or partial
    # Two pixels around the measured glyph region remove the original DDS
    # antialiasing fringe. Border/icon protection remains authoritative.
    ox,oy,ow,oh=region['rect']
    clear_box=(max(0,min(x,ox)-2),max(0,min(y,oy)-2),
               min(image.width,max(x+w,ox+ow)+2),min(image.height,max(y+h,oy+oh)+2))
    if member==5 and background and x<800:
        clear_box=(clear_box[0],clear_box[1],max(clear_box[2],560),clear_box[3])
    if (member,rid)==(4,'l3_note'):
        clear_box=(clear_box[0],clear_box[1],clear_box[2],503)
    mask=allowed_mask(image.size,clear_box,member,background)
    if background and source is not None:
        # Keep the cyan controller callout paths that cross screenshot text.
        pixels=source.convert('RGB').crop(clear_box)
        line=Image.new('L',pixels.size,0)
        line.putdata([255 if b>r+30 and g>r+30 and b>100 and g>100 else 0 for r,g,b in pixels.get_flattened_data()])
        full=Image.new('L',image.size,0);full.paste(line,clear_box[:2])
        mask=ImageChops.subtract(mask,full)
    if not mask.getbbox():
        report.append(dict(id=rid,status='fully_occluded',text=region['en']));return
    style=region.get('style',{})
    size=style.get('suggested_font_px',20 if partial else 22)
    if (member,rid)==(4,'l3_note'):size=12
    if (member,rid)==(4,'map_requirement'):size=15
    if (member,rid)==(6,'background_neutral'):size=18
    if (member,rid)==(5,'top_ten'):size=15
    text=region['en']+' +' if (member,rid)==(4,'auto_combo') else region['en']
    if (member,rid)==(5,'top_ten'):text=text.replace(' (','\n(')
    # Original tiny parenthetical stick captions remain >=12 px. Normal body
    # copy remains >=15 px, and ordinary headings/labels remain >=16 px.
    minimum=min(size,12 if h<=18 else 15 if 'body' in rid or h<25 else 16)
    if partial:minimum=16
    if partial:
        # Reconstruct the underlying full line, then reveal only the existing
        # unobscured fragment. Never write through controller or help panels.
        draw_x=299 if member==5 else x
        full_width=300 if member==5 else w
        full_height=28
        font,lines,line_h,total=fit(text,font_path,size,full_width,full_height,minimum)
        text_y=y
    else:
        font,lines,line_h,total=fit(text,font_path,size,w-2,h-2,minimum)
        draw_x=x+1
        # Center titles/contact text; ordinary labels remain left aligned.
        text_y=y+(h-total)//2
        if (member,rid)==(2,'burn_in'):text_y=y+1
        if (member,rid)==(6,'background_neutral'):text_y=370
    layer=Image.new('RGBA',image.size,(0,0,0,0))
    d=ImageDraw.Draw(layer)
    d.rectangle((clear_box[0],clear_box[1],clear_box[2]-1,clear_box[3]-1),fill=background_color(image,box,background))
    color=COLORS.get(style.get('color','gray' if background else 'white'),COLORS['white'])
    ink=Image.new('L',image.size,0); ink_draw=ImageDraw.Draw(ink)
    for line_no,line in enumerate(lines):
        bbox=font.getbbox(line or 'Ag')
        tx=draw_x
        if not partial and (member>=3 and rid in ('town_title','dungeon_title','ranking_title','registration_title','contact_title') or member==7 and rid not in ('previous','next','return_title')):
            tx=x+(w-font.getlength(line))/2
        ty=text_y+line_no*line_h-bbox[1]
        d.text((tx,ty),line,font=font,fill=color)
        ink_draw.text((tx,ty),line,font=font,fill=255)
    actual_ink=ImageChops.multiply(ink,mask)
    if not background and ImageChops.subtract(ink,actual_ink).getbbox():
        raise ValueError('Protected artwork clips English text: %d/%s' % (member,rid))
    # The allowed mask clips only known layering/protected regions, not fit.
    unclipped=ink.getbbox()
    if not partial and unclipped and not (box[0]<=unclipped[0] and box[1]<=unclipped[1] and unclipped[2]<=box[2] and unclipped[3]<=box[3]):
        raise ValueError('Ink escaped edit region: %s/%s' % (member,rid))
    image.paste(layer,(0,0),mask)
    report.append(dict(id=rid,text=region['en'],status='visible_fragment' if partial else 'rendered',
                       source_rect=region['rect'],render_rect=rect,font_px=font.size,
                       lines=lines,ink_bbox=actual_ink.getbbox(),
                       controller_mask_applied=member in (3,4,5,6),
                       background_panel_patch=background or rid in ('previous','return_title','next')))


def splice_dds(original,image):
    if original[:4]!=b'DDS ' or original[84:88]!=b'DXT5':
        raise ValueError('Expected original DXT5 DDS')
    source=Image.open(io.BytesIO(original)).convert('RGBA')
    if source.size!=image.size:raise ValueError('Image dimensions changed')
    if source.getchannel('A').getextrema()!=(255,255):
        raise ValueError('This renderer expects the supplied opaque title2 pages')
    encoded=io.BytesIO();image.save(encoded,format='DDS',pixel_format='DXT5')
    new=encoded.getvalue()
    if len(new)!=len(original):raise ValueError('DDS storage layout changed')
    # Copy only changed compressed blocks. Every untouched block remains
    # byte-identical, avoiding recompression damage to original artwork.
    diff=ImageChops.difference(source.convert('RGB'),image.convert('RGB')).convert('L')
    bbox=diff.getbbox(); result=bytearray(original);changed=[]
    if bbox:
        for by in range(bbox[1]//4,(bbox[3]+3)//4):
            for bx in range(bbox[0]//4,(bbox[2]+3)//4):
                if not diff.crop((bx*4,by*4,bx*4+4,by*4+4)).getbbox():continue
                offset=128+16*(by*(image.width//4)+bx)
                result[offset:offset+16]=new[offset:offset+16];changed.append((bx,by))
    decoded=Image.open(io.BytesIO(result)).convert('RGBA')
    if decoded.size!=source.size or decoded.getchannel('A').getextrema()!=(255,255):
        raise ValueError('DDS dimension/alpha verification failed')
    return bytes(result),decoded,changed


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,default=ROOT/'work/translation/en/graphics/title2.en.json')
    parser.add_argument('--source',type=Path,default=ROOT/'work/source/NPJB00162')
    parser.add_argument('--font',type=Path)
    parser.add_argument('--output',type=Path,default=ROOT/'work/output/graphics_english')
    parser.add_argument('--write',action='store_true')
    args=parser.parse_args()
    font=args.font or args.source/'USRDIR/FOT-UtrilloPro-DB.otf'
    manifest=json.loads(args.manifest.read_text(encoding='utf8'))
    if [a['member'] for a in manifest['assets']]!=list(range(8)):
        raise ValueError('Expected exactly the eight title2 help pages')
    if any(a['source_file']!='USRDIR/data/texture/title2.enc' for a in manifest['assets']):
        raise ValueError('This renderer only edits title2.enc help pages')
    path=args.source/'USRDIR/data/texture/title2.enc'
    members=unpack(path.read_bytes()); original_members=list(members)
    if len(members)!=8:raise ValueError('Unexpected title2 member count')
    reports=[]; previews=[]
    for asset in manifest['assets']:
        i=asset['member'];source=Image.open(io.BytesIO(members[i])).convert('RGBA')
        if source.size!=(asset['width'],asset['height']):raise ValueError('Manifest size mismatch')
        edited=source.copy();regions=[]
        if i==6:
            # The Japanese attribute names extend beyond the draft rectangles.
            # Rebuild only this black-panel interior; preserve its ornate frame.
            ImageDraw.Draw(edited).rectangle((902,404,1138,586),fill=(0,0,0,255))
        # Background screenshot text is rendered first, respecting front panels.
        ordered=sorted(asset['regions'],key=lambda r:not r['id'].startswith('background_'))
        for region in ordered:render_region(edited,asset,region,font,regions,source=source)
        for region in asset.get('partially_occluded_text',[]):
            render_region(edited,asset,region,font,regions,partial=True,source=source)
        if i==5:
            # Narrow undecipherable remnants of hidden ranking rows. Their
            # actual labels are not reconstructed or invented.
            box=(464,208,480,304);mask=allowed_mask(edited.size,box,i,True)
            patch=Image.new('RGBA',edited.size,(32,32,32,255));edited.paste(patch,(0,0),mask)
        new,decoded,changed=splice_dds(members[i],edited);members[i]=new
        if i in (3,4,5,6):
            difference=ImageChops.difference(source.convert('RGB'),decoded.convert('RGB')).convert('L')
            if ImageChops.multiply(difference,controller_mask(source.size)).getbbox():
                raise ValueError('Controller pixels changed on page %d' % i)
        difference=ImageChops.difference(source.convert('RGB'),decoded.convert('RGB')).convert('L')
        if ImageChops.multiply(difference,icon_mask(source.size,i)).getbbox():
            raise ValueError('Original button icon pixels changed on page %d' % i)
        for preserve in asset.get('preserve_regions',[]):
            x,y,w,h=preserve['rect'];box=(x,y,x+w,y+h)
            if source.crop(box).tobytes()!=decoded.crop(box).tobytes():
                raise ValueError('Preserved English notice changed')
        reports.append(dict(member=i,width=decoded.width,height=decoded.height,format='DXT5 DDS',
                            original_sha256=sha(original_members[i]),english_sha256=sha(new),
                            changed_blocks=len(changed),alpha_extrema=decoded.getchannel('A').getextrema(),
                            controller_pixels_verified=i in (3,4,5,6),
                            original_button_icons_verified=True,regions=regions))
        previews.append(decoded)
    archive=pack(members)
    if unpack(archive)!=members:raise ValueError('English archive round-trip failed')
    report=dict(format_version=1,status='rendered; static verification passed; in-game verification pending',
                manifest_sha256=sha(args.manifest.read_bytes()),font_sha256=sha(font.read_bytes()),
                source_archive_sha256=sha(path.read_bytes()),english_archive_sha256=sha(archive),
                archive_roundtrip_verified=True,assets=reports,
                unreadable_or_occluded=manifest.get('unreadable_or_occluded',[]),
                notes=['The source has baked Japanese text over art. Opaque English text-panel patches replace those regions; hidden artwork is not reconstructed.',
                       'Dimmed screenshot fragments are rendered behind controller/help masks. Completely hidden labels are not invented.',
                       'Tiny source underlay fragments touching protected controller/icon DXT blocks may remain at occlusion edges; those blocks are retained to preserve the original art exactly.',
                       'Only changed original-format DXT5 blocks are replaced; untouched compressed blocks remain byte-identical.'])
    print(json.dumps(dict(pages=8,regions=sum(len(r['regions']) for r in reports),
                          minimum_font_px=min(r['font_px'] for a in reports for r in a['regions'] if 'font_px' in r),
                          controller_pixels_verified=all(a['controller_pixels_verified'] for a in reports[3:7]),
                          archive_roundtrip_verified=True,
                          sample=reports[3]['regions'][:3]),indent=2))
    if args.write:
        args.output.mkdir(parents=True,exist_ok=True)
        for i,(data,im) in enumerate(zip(members,previews)):
            (args.output/('%04d.dds'%i)).write_bytes(data)
            im.save(args.output/('%04d.png'%i))
        (args.output/'title2.enc').write_bytes(archive)
        (args.output/'verification.en.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        print('Wrote English DDS/PNG pages, round-trip checked title2.enc and verification report to',args.output)
    else:print('Dry run: no files written. Use --write after inspecting the fit report.')


if __name__=='__main__':main()
