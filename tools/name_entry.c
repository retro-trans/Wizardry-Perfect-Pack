/* Preserve the native 33-byte saved-name field, copying whole UTF-8 characters. */
typedef unsigned char u8;
void *set_character_name(u8 *record, const u8 *text)
{
    u8 *name = record + 0x1bd;
    unsigned used = 0, chars = 0, i, width;
    /* The native field is unaligned; keep clearing as byte stores on PPU. */
    for (i = 0; i < 33; ++i) ((volatile u8 *)name)[i] = 0;
    if (!text) return record;
    while (chars < 12 && text[0]) {
        u8 c = text[0];
        if (c < 0x80) width = 1;
        else if (c >= 0xc2 && c <= 0xdf) width = 2;
        else if (c >= 0xe0 && c <= 0xef) width = 3;
        else if (c >= 0xf0 && c <= 0xf4) width = 4;
        else break;
        if (used + width > 32) break;
        for (i = 1; i < width; ++i)
            if ((text[i] & 0xc0) != 0x80) return name;
        /* Exclude overlong encodings, surrogate codepoints and values > U+10ffff. */
        if ((c == 0xe0 && text[1] < 0xa0) || (c == 0xed && text[1] >= 0xa0) ||
            (c == 0xf0 && text[1] < 0x90) || (c == 0xf4 && text[1] >= 0x90)) break;
        for (i = 0; i < width; ++i) name[used+i] = text[i];
        used += width;
        text += width;
        ++chars;
    }
    return name;
}
