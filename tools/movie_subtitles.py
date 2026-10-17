"""Bottom-aligned subtitle geometry, shared by rendering and the bounds audit."""
from PIL import Image,ImageDraw,ImageFont


def font_for(style):
    return ImageFont.truetype(style['font_file'],style['font_size'])


def position(text,style,font):
    draw=ImageDraw.Draw(Image.new('RGB',(1,1)))
    left,top,right,bottom=draw.multiline_textbbox((0,0),text,font=font,
        spacing=style['line_spacing'],stroke_width=style['outline_width'],align='center')
    return (640-(left+right)/2,style['bottom']-bottom)


def draw_subtitle(picture,text,style,font):
    ImageDraw.Draw(picture).multiline_text(position(text,style,font),text,font=font,
        fill=style['text_color'],align='center',spacing=style['line_spacing'],
        stroke_width=style['outline_width'],stroke_fill=style['outline_color'])


def srt_text(spec):
    def stamp(seconds):
        value=round(seconds*1000);hours,value=divmod(value,3600000)
        minutes,value=divmod(value,60000);seconds,millis=divmod(value,1000)
        return f'{hours:02}:{minutes:02}:{seconds:02},{millis:03}'
    return '\n\n'.join(f"{i}\n{stamp(c['start'])} --> {stamp(c['end'])}\n{c['en']}"
                       for i,c in enumerate(spec['subtitle_segments'],1))+'\n'


def main():
    import argparse,json
    from pathlib import Path
    from check_movie_captions import check
    p=argparse.ArgumentParser(description='Export the validated English opening subtitles as SRT. Default dry run.')
    p.add_argument('--write',action='store_true');args=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    spec=json.loads((root/'work/translation/en/graphics/opening.en.json').read_text(encoding='utf8'))
    check();text=srt_text(spec)
    print(text.split('\n\n')[0]);print('Subtitles:',len(spec['subtitle_segments']))
    if args.write:(root/'work/output/movie/opening.en.srt').write_text(text,encoding='utf8')
    else:print('Dry run: no files written.')


if __name__=='__main__':main()
