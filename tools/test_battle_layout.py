"""Host-native reward wrapping checks; default dry run, --write runs cases."""
import argparse
import ctypes as C
import json
import re
import subprocess
import sys
from check_translation import ROOT
from spell_description_layout import advances

CONTROL=re.compile(r'@(?:[0-9]+r|RS)')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');args=p.parse_args()
    target=ROOT/'work/output/tests/battle.dll'
    command=[sys.executable,'-m','ziglang','cc','-shared','-O2','-fno-builtin',str(ROOT/'tools/dialogue_layout.c'),'-o',str(target)]
    if not args.write:print('Dry run: compile the shared message presenter and check reward width, pages, colors and final-wait ownership.');return
    subprocess.run(command,check=True);lib=C.CDLL(str(target));metrics=advances()
    def width(text):return sum(16 if ch==' ' else metrics[ch] for ch in CONTROL.sub('',text))
    Measure=C.CFUNCTYPE(C.c_int,C.c_void_p,C.c_char_p,C.c_int,C.c_int)
    Show=C.CFUNCTYPE(C.c_int,C.c_uint,C.c_uint,C.c_char_p,C.POINTER(C.c_void_p))
    Wait=C.CFUNCTYPE(C.c_int,C.c_uint,C.c_uint);Yield=C.CFUNCTYPE(None,C.c_uint);Keys=C.CFUNCTYPE(C.c_uint)
    pages=[];waits=[]
    @Measure
    def measure(font,text,sx,sy):
        assert sx==sy==32
        return width(text.decode('utf8'))
    @Show
    def show(window,flags,fmt,values):
        assert window==0 and flags==0xd1 and fmt==b'%s'
        pages.append(C.string_at(values[0]).decode('utf8'));return 1
    @Wait
    def wait(window,enabled):
        assert window==0 and enabled==1
        waits.append(len(pages));return 1
    @Yield
    def tick(count):raise AssertionError('Rewards must not acquire typewriter delays')
    @Keys
    def keys():return 0
    lib.set_dialogue_callbacks.argtypes=[Measure,Show,Wait,Yield,Keys,Keys]
    lib.set_dialogue_callbacks(measure,show,wait,tick,keys,keys)
    present=lib.present_battle;present.argtypes=[C.c_uint,C.c_char_p,C.c_void_p];present.restype=C.c_int
    cases=[('screenshot','Each adventurer gained @7r108@0r experience points!\nObtained @7r15@0r Gold!'),
           ('large_numbers','Each adventurer gained @7r2147483647@0r experience points!\nObtained @7r4294967295@0r Gold!'),
           ('hard_lines','First reward line.\nSecond reward line.\nThird reward line.\nFourth reward line.'),
           ('treasure_pages',('The party obtained an Ancient Enchanted Golden Sword of the Forgotten Kings!\n'*12).rstrip()),
           ('color_carry','@14r'+('This whole long colored reward must stay readable. '*20)+'@0r'),
           ('paragraphs','An unusually long reward message needs wrapping before the next authored paragraph.\n\nThis second paragraph must start on a fresh page.'),
           ('long_word','W'*200),
           ('unicode','“A legendary reward,” the record says. '*20)]
    report=[]
    clean=lambda text:re.sub(r'\s+','',CONTROL.sub('',text))
    for name,text in cases:
        pages.clear();waits.clear();assert present(0,text.encode('utf8'),1)==1,name
        assert clean(''.join(pages))==clean(text),name
        assert len(waits)==len(pages)-1,(name,'final acceptance must belong to the original caller')
        assert waits==list(range(1,len(pages))),name
        for page in pages:
            assert len(page.split('\n'))<=3
            assert all(width(line)<=640 and len(line.encode('utf8'))<=120 for line in page.split('\n'))
        if name=='hard_lines':assert pages==['First reward line.\nSecond reward line.\nThird reward line.','Fourth reward line.']
        if name=='color_carry':assert all(page.startswith('@14r') for page in pages)
        if name=='paragraphs':assert len(pages)>=2 and pages[1].startswith('This second paragraph')
        report.append(dict(case=name,pages=len(pages),maximum_width=max(width(line) for page in pages for line in page.split('\n')),text_preserved=True))
        if name=='screenshot':screenshot=list(pages)
    pages.clear();assert present(0,b'Short reward.',1)==0 and not pages
    result=dict(result='passed',native_cases=len(cases)+1,cases=report,screenshot_pages=screenshot,
                flags_preserved='0xd1',last_page_wait_preserved=True,powerpc_game_execution=False)
    (ROOT/'work/output/tests/battle_layout.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
