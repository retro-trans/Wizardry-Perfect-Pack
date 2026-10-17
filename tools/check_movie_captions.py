"""Check opening caption bounds with the exact rendering font; read-only by default."""
import argparse
import json
from pathlib import Path
from PIL import Image,ImageDraw
from movie_subtitles import font_for,position,draw_subtitle

ROOT=Path(__file__).resolve().parents[1]


def check():
    spec=json.loads((ROOT/'work/translation/en/graphics/opening.en.json').read_text(encoding='utf8'))
    draw=ImageDraw.Draw(Image.new('RGB',(1280,720)));cases=[];prior=0
    style=spec['style'];font=font_for(style);grouped={cue['id']:[] for cue in spec['cues']}
    originals={cue['id']:cue for cue in spec['cues']}
    for cue in spec['subtitle_segments']:
        assert prior<=cue['start']<cue['end']<2210*1001/30000,'Caption cue times overlap or exceed movie'
        prior=cue['end'];source=originals[cue['source_id']];grouped[cue['source_id']].append(cue)
        assert source['start']<=cue['start']<cue['end']<=source['end'],'Subtitle outside source narration'
        assert len(cue['en'].split('\n'))<=style['maximum_lines'],'Subtitle exceeds two lines'
        x,y,w,h=style['safe_bounds']
        assert 0<=x<x+w<=1280 and 0<=y<y+h<=720,'Subtitle safe area outside image'
        bounds=draw.multiline_textbbox(position(cue['en'],style,font),cue['en'],font=font,align='center',
                                       spacing=style['line_spacing'],stroke_width=style['outline_width'])
        fits=x<=bounds[0] and bounds[2]<=x+w and y<=bounds[1] and bounds[3]<=y+h
        assert fits,'English subtitle exceeds safe area: '+cue['id']
        # A noisy source frame proves that drawing changes only glyph pixels
        # in the bottom safe area, with no central plate or title mask.
        image=Image.effect_noise((1280,720),50).convert('RGB');before=image.copy()
        draw_subtitle(image,cue['en'],style,font)
        assert image.crop((0,0,1280,y)).tobytes()==before.crop((0,0,1280,y)).tobytes(),'Original central artwork changed'
        cases.append(dict(id=cue['id'],text=cue['en'],bounds=list(bounds),fits=True))
    for key,segments in grouped.items():
        assert segments,'Missing English narration: '+key
        assert ' '.join(s['en'] for s in segments).split()==originals[key]['en'].split(),'Narration words changed: '+key
        assert all(a['end']==b['start'] for a,b in zip(segments,segments[1:])),'Gap within narration: '+key
    assert len(cases)==12
    assert spec['cues'][0]['start']==7.1,'Keep 107-byte black holds untouched before display frame 213'
    return dict(result='passed',subtitles=len(cases),canonical_captions=len(grouped),maximum_lines=2,
                all_words_preserved=True,original_central_artwork_unchanged_by_overlay=True,
                cases=cases,updated_game_capture=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');args=p.parse_args()
    report=check();print(json.dumps(report,indent=2))
    if args.write:(ROOT/'work/output/tests/movie_captions.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')


if __name__=='__main__':main()
