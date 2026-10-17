# Text inventory — NPJB00162

The supplied BLJM61008 Perfect Pack disc installs two separate games. Only PKG01, **NPJB00162 / Prisoners of the Lost City**, was extracted for translation. PKG00, **NPJB00163 / Labyrinth of Lost Souls**, is outside this build.

| Source | Exported rows | Stored occurrences |
|---|---:|---:|
| Event dialogue, narration, speakers and choices | 7,056 | 11,112 |
| Executable candidates | 2,756 | 2,987 |
| Trophy names and descriptions | 106 | 106 |
| Base items, monsters, quests, spells, skills and credits | 1,071 | 1,860 |
| Added scenario 1 databases | 196 | 292 |
| Added scenario 2 databases | 179 | 253 |
| Perfect Pack bonus items | 7 | 12 |
| Protected dungeon names | 13 | 13 |
| Equipment-slot immediate literals | 3 | 3 |
| **Total** | **11,387** | **16,638** |

Rows are deduplicated within their source group. Across all groups there are **11,231 distinct source strings**. Occurrences count stored uses, not visible screen lines. The executable inventory includes **591 internal/parser candidates excluded from translation** with recorded reasons.

The event pass read and round-tripped all **613 event files**; **607** contain Japanese text. The protected station event was authenticated using its own executable's embedded data and added to the inventory. No external license files were used for that recovery. All 87 ENC archives were unpacked into 1,019 members. A further bounded text scan of non-table members found the Perfect Pack item table; other candidates were model/shader fragments rather than additional identified player-facing prose. Binary string scanning cannot establish that every reachable text source has been discovered.

The five reported menu/dungeon screenshots exposed another source: 14 protected dungeon-scene archives outside the original ENC inventory. All were authenticated using embedded game data and decoded into four-member archives. Thirteen contain Japanese location names; these are now exported separately. Their floors, metadata and background images are preserved by the translation build.

Three additional equipment-slot values are assembled from immediate UTF-8 bytes in executable instructions. They are exported separately with instruction guards; ordinary string scanning could not find them.

The neighboring download edition supplied **6,092 exact-source decisions**. There are **5,295 new decisions** in this edition. IDs, addresses, executable instructions and record layouts were traced in this edition; the neighboring executable patch was not copied into the game.

Graphics are separate from the row total: eight help pages contain 116 replaced regions, title/ending/package logos have English assets, and the opening movie has seven caption/title cues. Tiny decorative or unreadable texture fragments still require visual examination.

Regenerate the English-only machine-readable summary with `tools/corpus_report.py --write`. Detailed Japanese exports stay under ignored `work/translation/ja/` and `work/output/`; do not commit them.
