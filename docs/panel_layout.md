# Status, spell, quest, settings and battle corrections

## Status descriptions in 0.1.6

The two new captures are saved as `work/ui/status-before-0.1.6-identify.png` and `work/ui/items-before-0.1.6-unidentified.png`. Coordinates are recorded in `work/ui/status-items.en.json`.

The status skill-description resource has ID 16 and native dimensions 288 by 256px. Its callback at `0xb7528` selects 22 by 22px text, gets the skill description through `0x65aa8` at `0xb76ac`, and draws at `0xb76c8` with offsets 12px horizontally and 46px vertically. A 264px inner width leaves a 12px inset on either side. All 20 description display copies are wrapped using the original font metrics; every word survives, and the longest requires only five lines. Eight lines are permitted within the vertical budget. Canonical translation rows remain unchanged, and the independent overlay verifier checks the resolved skill-description fields.

## Previous panel corrections in 0.1.5

The four supplied screenshots are saved unchanged as `work/ui/panels-before-0.1.4-*.png`; measured bounds are in `work/ui/panels.en.json`.

The spell-school labels have 116px before the first MP number. A guarded horizontal font change at `0x264d8` fits the complete Summoner label at width 105px, with a safety margin. Vertical size and the separately reset MP-number font remain 32px.

Spell descriptions have only one direct drawing caller, at `0x26784`. Their display copies now wrap at 352px using the original font's advance model. All 89 unique descriptions fit in six lines, with every word preserved; 87 change their display line breaks. The canonical English rows and source newlines stay intact. The native style adds one pixel to the vertical size, so a guarded change at `0x26728` uses 22px height with the original 24px width. Six lines occupy at most 137px within the 158px frame and its 12px top inset. Build verification resolves and checks all 94 stored description fields against those display copies.

The quest header is a single padded string. “Level” removes redundant wording and aligns Status at x854–924 over the centered body status. The apparent doubled Accepted letters came from a separate six-space bracket string drawn at the same center; its draw call at `0x9ac90` is removed. Complete and Not Accepted also lost terminators in compiler-sized copies, so their original source bytes now expand at the font boundary. All three status forms fit inside the row.

The settings options remain Fast, Normal and Slow at their original font size. Only Slow moves, from x840 to x864, in all three selection paths. The modeled gap after Normal is 17px and Slow ends at x935 inside the panel.

Battle rewards use a narrower box than event dialogue and bypass the event wrapping hook. The new guarded bridge changes only the assembled reward Show call at `0x21860`. Its private 16KiB frame owns a 12KiB token-expansion buffer, so full item names are available before word wrapping. The compiled presenter uses a 640px inner width, 32px font and three lines per page. It preserves authored line breaks, numeric color controls, UTF-8 boundaries and the original `0xd1` window flags. It avoids orphaning the final word where the last two words fit together. Intermediate pages use the native wait; the original caller at `0x2186c` still owns the final acceptance. Short fitting messages follow the original path.

The dialogue compiler validates both exported local entries and permits only their skipped ELFv2 TOC setup relocations. Neither presenter requires runtime data sections. The existing event paragraph behavior is unchanged by the battle-specific options.

Verification includes nine host-native battle cases covering the screenshot, maximum integer rewards, hard breaks, long treasure lists, color carry, UTF-8, long words and final-wait ownership; ten wrapper regressions include the battle boundary and its 24-byte guard. The previous eleven dialogue cases and all 5,222 event paragraphs still pass. Spell corpus checks, measured panel budgets and independent overlay verification also pass. These checks do not establish updated in-game visual acceptance.
