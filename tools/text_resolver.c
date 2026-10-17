/* Freestanding PPU token expansion. No imports, static storage or heap use.
 * The caller owns output for the entire measure/draw call. Table strings are
 * immutable; eight-digit indices identify complete relocated UTF-8 strings.
 */
typedef __UINTPTR_TYPE__ uptr;
typedef unsigned int u32;

#if defined(_WIN32)
__declspec(dllexport)
#endif
const char *resolve_text(const char *input, char *output, u32 capacity,
                         const uptr *table, u32 count,
                         const uptr *aliases, u32 alias_count)
{
    const char *scan = input;
    u32 used = 0;
    int changed = 0;
    if (!input || !output || !capacity) return input;
    if (!alias_count) {
        while (*scan && !(scan[0] == '~' && scan[1] == 'T')) ++scan;
        if (!*scan) return input;
        scan = input;
    }
    while (*scan) {
        u32 index = 0;
        unsigned int i = 0;
        /* A few native menu labels are copied with compile-time byte counts.
         * Keep their original, terminated bytes until this final boundary.
         * Exact aliases cannot alter a longer word. Prefix aliases are limited
         * to the two hand labels, which precede an item name in the same row.
         */
        if (scan == input) {
            u32 a;
            for (a = 0; a < alias_count; ++a) {
                const char *key = (const char *)aliases[a * 3];
                const char *replacement = (const char *)aliases[a * 3 + 1];
                u32 length = 0;
                while (key[length] && scan[length] && key[length] == scan[length]) ++length;
                if (!key[length] && (aliases[a * 3 + 2] || !scan[length])) {
                    while (*replacement) {
                        if (used + 1 >= capacity) return input;
                        output[used++] = *replacement++;
                    }
                    scan += length;
                    changed = 1;
                    break;
                }
            }
            if (changed) continue;
        }
        if (scan[0] == '~' && scan[1] == 'T') {
            for (i = 2; i != 10; ++i) {
                unsigned char c = (unsigned char)scan[i];
                u32 digit;
                if (c >= '0' && c <= '9') digit = c - '0';
                else if (c >= 'A' && c <= 'F') digit = c - 'A' + 10;
                else break;
                index = (index << 4) | digit;
            }
            if (i == 10 && scan[10] == '~' && index < count) {
                const char *replacement = (const char *)table[index];
                while (*replacement) {
                    if (used + 1 >= capacity) return input;
                    output[used++] = *replacement++;
                }
                scan += 11;
                changed = 1;
                continue;
            }
        }
        if (used + 1 >= capacity) return input;
        output[used++] = *scan++;
    }
    output[used] = 0;
    return changed ? output : input;
}
