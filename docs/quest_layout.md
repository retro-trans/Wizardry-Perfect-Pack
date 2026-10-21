# Quest description wrapping

Local build 0.1.17 wraps the lower quest panel using display copies in the relocated text pool. Canonical translations and quest titles, clients, identifiers, flags and numeric fields remain unchanged. Both request and objective fields in member 8 of the quest archives are covered.

The native draw uses a 24px font. The client line starts at panel x+12, y+8; the body starts at x+12, y+40. Accepted objectives select record offset 554 at VA0x99984; requests select offset 216 at VA0x999f0, then share the draw at VA0x9999c. The panel is 671px wide and 123px high. A 640px text budget leaves a right margin; at most three body lines, with 25px pitch, occupy 74px and fit below the client line.

The audit covers 108 distinct descriptions and 112 field occurrences. It reflows 89 descriptions and preserves every word, including the grizzlies and Fiore in the reported objective. Excessively wide words or over-height descriptions stop the build instead of being truncated. The independent overlay verifier resolves every quest token and compares its actual display text, while retaining all non-text database checks.

Quest, spell and skill layout tests pass. Updated in-game appearance still needs confirmation through the local launcher. The previous class-heading, item abbreviation and other translation fixes are retained. This is a local build, not a public release.
