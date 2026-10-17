# Dialogue wrapping

## Anonymous narration coverage in 0.1.9

The user's new captures are saved as `work/ui/narration-before-0.1.9-despair.png` and `work/ui/narration-before-0.1.9-labyrinth.png`, with geometry and source IDs in `work/ui/narration.en.json`. The intended translated executable is being launched. The failure is a missing native path, rather than a movie-subtitle change or an outdated translation file.

Intro script S0102 sets anonymous-speaker state through opcode `0x93` and an empty `0x43` speaker entry. Those handlers set per-window flags `0x22a8` and `0x2590` to `0xff`. The branch at `0xa5e58` therefore jumps to `0xa607c`, which calls `de474` at `0xa6084`. It skips the ordinary/typewriter hook at `0xa5e94` entirely. The earlier host tests proved the layout helper's output, but did not prove this narration branch would call it.

A separate guarded bridge now intercepts that anonymous Show call after the full paragraph and actor references have been assembled. It passes window/text/font to the narration presenter, retaining the original centered `0xf0` flags and wide-box 896px budget. The bridge preserves registers, floating-point inputs, condition state, TOC and linkage. Its private saves remain beyond the native argument area. A fitting paragraph tail-calls the original variadic wrapper; a handled one returns to the original continuation and epilogue.

The presenter leaves its final page visible. Script opcode `0x50` still calls `dddc0(window,1)` at `0xa5b48` for final acceptance. Only extra pages add intermediate waits. The exact despair paragraph fits one three-line page; the labyrinth paragraph requires two pages. Full wording and colors survive.

Three focused tests execute the emitted instruction bridge for handled/fallback results with deliberately clobbered registers and argument slots, reject every altered byte in both native boundary guards, and trace the actual S0102 commands through the relevant dispatch/state/branch instructions. Eleven runtime regressions and 14 host-native dialogue/narration cases pass, as do all 5,222 corpus paragraphs and the nine battle cases. Updated in-game appearance still requires a restarted test session.

## Ordinary dialogue hook introduced in 0.1.2

The user's 1280×720 captures show a message frame at x=160, y=507, width=960, height=158. The original renderer centers each supplied line independently at 32px. English rows E6543 and E6546 exceeded that frame and were clipped. Reducing the string's stored byte length would not fix this geometry.

The event handler at `0xa5c04` gathers adjacent MES/MESONE records and expands actor references before choosing ordinary or typewriter presentation. The guarded bridge at `0xa5e94` passes that complete buffer to the new presenter. Paragraphs that already fit continue through the original code. The new path measures words with the native font function, uses **896px** of the frame, and limits a page to **three lines**. Extra pages use the native advance/wait routine. It copies text through the native non-variadic message entry, preserving titles and avoiding incompatible variadic stack home areas.

The source scripts and canonical translation files remain unchanged. Runtime reflow replaces physical source line divisions with word boundaries; blank lines remain paragraph/page boundaries. Full words and UTF-8 codepoints are preserved. Color state carries across new lines and pages, including `@14r`. Each row is capped conservatively at 120 bytes after native bracket-to-color expansion, below the native 128-byte row slot. Actor names are measured after substitution rather than budgeted as short placeholders.

The two reported paragraphs now produce these layouts in the native C/font-metric tests:

```text
Having lost your way in the forest, you find a city
spread before you that seems to be the very one
described in the legend...

Gloomy though it is, the city is clearly inhabited, and
you can see its residents going about their lives here
and there.
```

Seven code/linkage regression tests and eleven host-native C layout cases pass. A corpus pass tested 5,222 event groups, reflowing 1,143 while preserving text order and content. No collected input group exceeded the original event buffer: the largest was 215 bytes before runtime name substitution. The tests cover pagination, long tokens, UTF-8, colors, paragraph boundaries, row capacities and typewriter updates. They model font advances and execute the C helper on the host; they do not establish PowerPC execution or in-game visual acceptance.

The patch applies to the event dialogue/narration path. Other database and menu panels still require their own measured layout acceptance. The current running emulator retains its old loaded executable until restarted.
