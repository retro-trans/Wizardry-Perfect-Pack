/* Reflow expanded event paragraphs before the native three-line message box.
 * No heap, imports or shared mutable storage in the PPU build. Native calls
 * use non-variadic entries so ELFv1 vararg home slots cannot overwrite the
 * ELFv2 caller's locals. All complete text stays in the original event buffer.
 */
typedef __UINTPTR_TYPE__ uptr;
typedef unsigned int u32;
typedef int (*Measure)(uptr,const char *,int,int);
typedef int (*Show)(u32,u32,const char *,const uptr *);
typedef int (*Wait)(u32,u32);
typedef void (*Yield)(u32);
typedef u32 (*Keys)(void);

#ifdef _WIN32
#define EXPORT __declspec(dllexport)
static Measure measure_call;
static Show show_call;
static Wait wait_call;
static Yield yield_call;
static Keys held_call,pressed_call;
EXPORT void set_dialogue_callbacks(Measure m,Show s,Wait w,Yield y,Keys h,Keys p)
{measure_call=m;show_call=s;wait_call=w;yield_call=y;held_call=h;pressed_call=p;}
#else
#define EXPORT
#define measure_call ((Measure)(uptr)0x164adc)
#define show_call ((Show)(uptr)0xde018)
#define wait_call ((Wait)(uptr)0xdddc0)
#define yield_call ((Yield)(uptr)0xd73b0)
#define held_call ((Keys)(uptr)0xdf494)
#define pressed_call ((Keys)(uptr)0xdfb04)
#endif

#define INLINE static __attribute__((always_inline)) inline
#define LINE_BYTES 120
#define PAGE_LINES 3

INLINE unsigned length(const char *s) {unsigned n=0;while(s[n])++n;return n;}
INLINE int whitespace(unsigned char c) {return c==' '||c=='\n'||c=='\r'||c=='\t';}
INLINE unsigned unit_bytes(const char *s)
{
    unsigned char c=(unsigned char)*s;
    if(c=='@'&&s[1]) {
        if(s[1]=='R'&&s[2]=='S')return 3;
        unsigned i=1;while(s[i]>='0'&&s[i]<='9')++i;
        if(i>1&&s[i]=='r')return i+1;
        if(s[1]=='<'||s[1]=='>'||s[1]=='['||s[1]==']'||s[1]=='('||s[1]==')')return 2;
    }
    if(c<128)return 1;
    unsigned n=c<224?2:c<240?3:4;
    for(unsigned i=1;i<n;i++)if(!s[i]||((unsigned char)s[i]&192)!=128)return 1;
    return n;
}
INLINE void color_state(const char *s,unsigned n,unsigned *color)
{
    for(unsigned i=0;i<n;i++) {
        if(s[i]=='@') {
            unsigned step=unit_bytes(s+i);
            if(step==2){++i;continue;}
            if(i+step<=n&&step>=3) {
                if(s[i+1]=='R')*color=0;
                else {
                    unsigned value=0;
                    for(unsigned k=1;k+1<step;k++)value=value*10+(s[i+k]-'0');
                    *color=value<=99?value:0;
                }
                i+=step-1;
            }
        } else if(s[i]=='<')*color=4;
        else if(s[i]=='[')*color=3;
        else if(s[i]=='(')*color=2;
        else if(s[i]=='>'||s[i]==']'||s[i]==')')*color=0;
    }
}
INLINE unsigned storage_bytes(const char *s)
{
    unsigned n=0;
    for(unsigned i=0;s[i];i++,n++) {
        if(s[i]=='@'&&unit_bytes(s+i)==2){++i;continue;}
        if(s[i]=='<'||s[i]=='>'||s[i]=='['||s[i]==']'||s[i]=='('||s[i]==')')n+=2;
    }
    return n;
}
INLINE int overwide(uptr font,const char *line,int width)
{return measure_call(font,line,32,32)>width;}

INLINE int needs_layout(uptr font,const char *input,int width)
{
    char line[LINE_BYTES+1];unsigned n=0,rows=1,total=0;
    for(const char *p=input;;p++) {
        char c=*p;
        if(c=='\n'||!c) {
            line[n]=0;if(overwide(font,line,width)||storage_bytes(line)>LINE_BYTES)return 1;n=0;
            if(!c)break;
            if(++rows>PAGE_LINES)return 1;
        } else {
            if(n==LINE_BYTES)return 1;
            line[n++]=c;
        }
        if(++total>=500)return 1;
    }
    return 0;
}

INLINE void display(u32 window,const char *page,int typing,unsigned delay,u32 accept,u32 flags)
{
    char format[3];format[0]='%';format[1]='s';format[2]=0;
    uptr args[1];
    if(!typing) {args[0]=(uptr)page;show_call(window,flags,format,args);return;}
    char prefix[512];unsigned n=0;
    while(page[n]) {
        unsigned unit=unit_bytes(page+n);
        for(unsigned i=0;i<unit;i++){prefix[n]=page[n];++n;}
        prefix[n]=0;args[0]=(uptr)prefix;show_call(window,flags,format,args);
        unsigned remaining=delay;
        while(remaining--) {
            yield_call(1);
            if((held_call()|pressed_call())&accept) {
                args[0]=(uptr)page;show_call(window,flags,format,args);return;
            }
        }
    }
}

/* CR4.EQ describes ordinary MES (no typewriter); the event handler has already
 * expanded actor names and collected the entire paragraph into its buffer.
 * Return zero to leave a fitting paragraph on the original path unchanged.
 */
INLINE int present_message(u32 window,const char *input,uptr font,u32 condition,
                           unsigned delay,u32 accept,int width,u32 flags,int hard_breaks)
{
    if(window>2||!input||!font||!needs_layout(font,input,width))return 0;
    int typing=(condition&0x2000)==0;
    char line[LINE_BYTES+8],page[512];
    unsigned used=0,line_count=0,n=0,color=0;
    const char *p=input;
    while(*p) {
        unsigned breaks=0;
        while(whitespace((unsigned char)*p)){if(*p=='\n')++breaks;++p;}
        /* A blank line is an authored paragraph boundary. Keep it as a page
         * boundary rather than folding it into the preceding sentence. */
        if(breaks>=2 && (n||line_count)) {
            if(n) {
                if(line_count)page[used++]='\n';
                for(unsigned i=0;i<n;i++)page[used++]=line[i];
            }
            page[used]=0;display(window,page,typing,delay,accept,flags);
            if(*p)wait_call(window,1);
            used=0;line_count=0;n=0;
        } else if(hard_breaks&&breaks&&n) {
            if(line_count)page[used++]='\n';
            for(unsigned i=0;i<n;i++)page[used++]=line[i];
            page[used]=0;n=0;++line_count;
            if(line_count==PAGE_LINES) {
                display(window,page,typing,delay,accept,flags);
                if(*p)wait_call(window,1);
                used=0;line_count=0;
            }
        }
        if(!*p)break;
        if(!n&&color) {
            line[n++]='@';if(color>=10)line[n++]=(char)('0'+color/10);
            line[n++]=(char)('0'+color%10);line[n++]='r';line[n]=0;
        }
        unsigned prefix_n=n&&line[0]=='@'?unit_bytes(line):0;
        const char *word=p;unsigned word_n=0;
        while(word[word_n]&&!whitespace((unsigned char)word[word_n]))++word_n;
        unsigned old=n;
        if(n && n!=prefix_n)line[n++]=' ';
        int fits=n+word_n<=LINE_BYTES;
        if(fits) {
            for(unsigned i=0;i<word_n;i++)line[n+i]=word[i];
            line[n+word_n]=0;fits=!overwide(font,line,width)&&storage_bytes(line)<=LINE_BYTES;
        }
        /* Keep a reward line's final two words together when they fit as a
         * pair. This avoids an orphaned "points!" after a long experience row.
         * Event paragraphs retain their established greedy layout. */
        if(hard_breaks&&fits&&old>prefix_n) {
            const char *last=word+word_n;
            while(*last==' '||*last=='\t'||*last=='\r')++last;
            unsigned last_n=0;
            while(last[last_n]&&!whitespace((unsigned char)last[last_n]))++last_n;
            const char *tail=last+last_n;
            while(*tail==' '||*tail=='\t'||*tail=='\r')++tail;
            unsigned end=n+word_n;
            if(last_n&&(!*tail||*tail=='\n')&&end+1+last_n<=LINE_BYTES) {
                line[end]=' ';
                for(unsigned i=0;i<last_n;i++)line[end+1+i]=last[i];
                line[end+1+last_n]=0;
                if(!overwide(font,line+n,width)&&overwide(font,line,width))fits=0;
                line[end]=0;
            }
        }
        if(fits) {n+=word_n;p+=word_n;color_state(word,word_n,&color);}
        else {
            n=old;
            if(!n || n==prefix_n) {
                /* A single long token is split only at complete UTF-8/control
                 * units. This also enforces the native 128-byte row capacity. */
                while(*p&&!whitespace((unsigned char)*p)) {
                    unsigned step=unit_bytes(p);
                    if(n+step>LINE_BYTES)break;
                    for(unsigned i=0;i<step;i++)line[n+i]=p[i];
                    line[n+step]=0;
                    if(overwide(font,line,width)||storage_bytes(line)>LINE_BYTES)break;
                    color_state(p,step,&color);n+=step;p+=step;
                }
            }
        }
        const char *next=p;while(whitespace((unsigned char)*next))++next;
        if(!fits||!*next) {
            line[n]=0;
            if(line_count)page[used++]='\n';
            for(unsigned i=0;i<n;i++)page[used++]=line[i];
            page[used]=0;n=0;++line_count;
            if(line_count==PAGE_LINES||!*next) {
                display(window,page,typing,delay,accept,flags);
                if(*next)wait_call(window,1);
                used=0;line_count=0;
            }
        }
    }
    return 1;
}

EXPORT int present_dialogue(u32 window,const char *input,uptr font,u32 condition,
                           unsigned delay,u32 accept)
{return present_message(window,input,font,condition,delay,accept,896,0x22,0);}

EXPORT int present_battle(u32 window,const char *input,uptr font)
{return present_message(window,input,font,0x2000,0,0,640,0xd1,1);}

/* Anonymous narration takes a separate native branch before the ordinary
 * event hook. Retain its original centered 0xf0 flags and final script wait. */
EXPORT int present_narration(u32 window,const char *input,uptr font)
{return present_message(window,input,font,0x2000,0,0,896,0xf0,0);}
