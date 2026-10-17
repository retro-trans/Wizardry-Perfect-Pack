"""Exercise native-compiled wrapping with actual font advances and UI callbacks.

Default dry run. --write compiles the host test library and saves the report.
This checks the C layout logic, not PowerPC execution or an in-game screenshot.
"""
import argparse
import ctypes as C
import json
from pathlib import Path
import re
import subprocess
import sys
from fontTools.ttLib import TTFont
from check_vwf import cache_width
ROOT=Path(__file__).resolve().parents[1]
CONTROL=re.compile(r'@(?:[0-9]+r|RS)')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');p.add_argument('--corpus',action='store_true');args=p.parse_args()
    output=ROOT/'work/output/tests/dialogue.dll'
    command=[sys.executable,'-m','ziglang','cc','-shared','-O2','-fno-builtin',str(ROOT/'tools/dialogue_layout.c'),'-o',str(output)]
    print(json.dumps(dict(command=command),indent=2))
    if not args.write:print('Dry run: no compiler invoked.');return
    output.parent.mkdir(parents=True,exist_ok=True);subprocess.run(command,check=True)
    lib=C.CDLL(str(output))
    with TTFont(str(ROOT/'work/source/NPJB00162/USRDIR/FOT-UtrilloPro-DB.otf')) as font:
        cmap=font.getBestCmap();em=font['head'].unitsPerEm
        widths={chr(c):cache_width(font['hmtx'][g][0],em) for c,g in cmap.items()}
    def width(s):return sum(16 if c==' ' else widths[c] for c in CONTROL.sub('',s))
    Measure=C.CFUNCTYPE(C.c_int,C.c_void_p,C.c_char_p,C.c_int,C.c_int)
    Show=C.CFUNCTYPE(C.c_int,C.c_uint,C.c_uint,C.c_char_p,C.POINTER(C.c_void_p))
    Wait=C.CFUNCTYPE(C.c_int,C.c_uint,C.c_uint)
    Yield=C.CFUNCTYPE(None,C.c_uint);Keys=C.CFUNCTYPE(C.c_uint)
    drawn=[];waited=[];ticks=[];expected_flags=0x22
    @Measure
    def measure(font,text,sx,sy):return width(text.decode('utf8'))
    @Show
    def show(window,kind,fmt,values):
        assert kind==expected_flags and fmt==b'%s'
        drawn.append(C.string_at(values[0]).decode('utf8'));return 1
    @Wait
    def wait(window,enable):waited.append(drawn[-1]);return 1
    @Yield
    def tick(count):ticks.append(count)
    @Keys
    def keys():return 0
    lib.set_dialogue_callbacks.argtypes=[Measure,Show,Wait,Yield,Keys,Keys]
    lib.set_dialogue_callbacks(measure,show,wait,tick,keys,keys)
    present=lib.present_dialogue
    present.argtypes=[C.c_uint,C.c_char_p,C.c_void_p,C.c_uint,C.c_uint,C.c_uint];present.restype=C.c_int
    narration=lib.present_narration
    narration.argtypes=[C.c_uint,C.c_char_p,C.c_void_p];narration.restype=C.c_int
    from check_translation import read_english
    english=read_english()
    cases=[
        ('screenshot_forest','Having lost your way in the forest, you find a city spread before you\nthat seems to be the very one described in the legend...',False),
        ('screenshot_city','Gloomy though it is, the city is clearly inhabited,\nand you can see its residents going about their lives here and there.',False),
        ('long_pages','This whole passage must remain readable, including its final words. '*30,False),
        ('long_token','W'*200,False),
        ('color_pages','@7r'+('Anselm has a warning for the party. '*18)+'@0r',False),
        ('unicode_pages',('“The city’s curse,” Beatrix said, “has not faded…” '*15),False),
        ('typing_pages',('Wait for the whole sentence. '*15),True),
        ('paragraph_boundary','This introduction is long enough to need proper word wrapping within the narrow message box.\n\nThis is the second paragraph, which must start on a new page.',False),
        ('two_digit_color','@14r'+('The active color continues across every page. '*12)+'@0r',False),
        ('bracket_storage',('[a] (b) <c> '*50),False),
        ('screenshot_narration_despair','\n'.join(english[k]['en'] for k in ('E6534','E6535')),False),
        ('screenshot_narration_labyrinth','\n'.join(english[k]['en'] for k in ('E6537','E6538','E6539')),False),
    ]
    reports=[];samples={}
    for name,text,typing in cases:
        drawn.clear();waited.clear();ticks.clear()
        anonymous=name.startswith('screenshot_narration_')
        expected_flags=0xf0 if anonymous else 0x22
        assert (narration(0,text.encode(),1) if anonymous else present(0,text.encode(),1,0 if typing else 0x2000,1,0x20))==1,name
        pages=waited+[drawn[-1]]
        actual=''.join(CONTROL.sub('',x) for x in pages)
        clean=lambda s:re.sub(r'\s+','',CONTROL.sub('',s))
        assert clean(actual)==clean(text),('Lost/reordered text',name)
        for page in pages:
            assert len(page.encode())<510
            lines=page.split('\n');assert len(lines)<=3
            assert all(width(line)<=896 and len(line.encode())<=120 for line in lines),(name,page)
            assert all(len(line.encode())+2*sum(c in '[]()<>' for c in line)<=127 for line in lines)
        assert len(waited)==len(pages)-1
        if name=='paragraph_boundary':assert len(pages)>=2 and pages[1].startswith('This is the second paragraph')
        if typing:assert ticks and len(drawn)>len(pages)
        reports.append(dict(case=name,pages=len(pages),max_width=max(width(line) for page in pages for line in page.split('\n')),text_preserved=True))
        if name.startswith('screenshot_'):samples[name]=pages
    drawn.clear();assert present(0,b'Short line.',1,0x2000,1,0x20)==0 and not drawn
    drawn.clear();assert narration(0,b'Short line.',1)==0 and not drawn
    expected_flags=0x22
    corpus=None
    if args.corpus:
        from build import parse_events,event_patches
        from check_translation import read_sources,read_english
        files,_=event_patches(ROOT/'work/source/NPJB00162',read_sources(),read_english())
        paragraphs=wrapped=largest=0
        for name,payload in files.items():
            rows=parse_events(payload);i=0
            while i<len(rows):
                if rows[i][0] not in (0x46,0x49):i+=1;continue
                op=rows[i][0];parts=[]
                while i<len(rows) and rows[i][0]==op and len(parts)<8:
                    parts.append(rows[i][1].rstrip(b'\0').decode('utf8'));i+=1
                text='\n'.join(parts);paragraphs+=1;largest=max(largest,len(text.encode()))
                drawn.clear();waited.clear()
                if not present(0,text.encode(),1,0x2000,1,0x20):continue
                wrapped+=1;pages=waited+[drawn[-1]]
                assert clean(''.join(pages))==clean(text),('Corpus text mismatch',name,i)
                for page in pages:
                    assert len(page.split('\n'))<=3
                    assert all(width(line)<=896 for line in page.split('\n'))
        corpus=dict(paragraphs=paragraphs,reflowed=wrapped,max_input_bytes=largest,text_preserved=True)
    result=dict(result='passed',native_cases=len(cases)+2,cases=reports,screenshot_pages=samples,corpus=corpus,
                anonymous_narration_flags='0xf0',final_script_wait_unchanged=True,powerpc_execution=False)
    print(json.dumps(result,indent=2))
    (ROOT/'work/output/tests/dialogue.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')


if __name__=='__main__':main()
