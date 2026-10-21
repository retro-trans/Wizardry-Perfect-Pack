# Changelog

## 0.1.20 — 2026-10-22 (local test build)

- Fix garbage after the bestiary Gold label by resolving Gold, EXP and Spell Resistance after their original fixed-length native copies. Use Gold:, EXP: and Spell Res: in this status pane.
- Align all nine stat label/value pairs to fixed columns with a 12px gap. Preserve the 24px font, colors, row positions and separate immunity/special-attack layout. Guard all ten coordinate instructions and the three native copy boundaries.
- Pass four bestiary status tests, eleven runtime tests and host resolver cases including reused buffers containing stale suffixes. Independently verify all 636 overlay files, the ten new status instructions and deferred labels; only the executable differs from 0.1.19.
- Stage the executable atomically and update the test launcher, retaining earlier fixes, saves and controller settings. Updated in-game appearance remains pending; no release is published.

## 0.1.19 — 2026-10-22 (local test build)

- Wrap ordinary item preview descriptions to 224px at a 20px body font, preserving the complete wording and canonical translations. The reported Healing Salve Concentrate description fits in four lines.
- Cover 76 descriptions across 264 item fields; all fit within five lines and 104px of the 105px height budget. Guard both native font constants. Keep item names, quantities, special-power text and equipment stat fonts unchanged.
- Pass four item-description, two preview guard and four bestiary layout tests. Independently verify all 636 overlay files and 264 item description fields. Only the executable differs from 0.1.18; stage it atomically and update the test launcher, preserving saves and controller settings.
- Retain bestiary and quest wrapping, full class headings, compact stats and previous fixes. Updated in-game appearance remains pending; no release is published.

## 0.1.18 — 2026-10-22 (local test build)

- Wrap all 200 bestiary lore display copies to a conservative 288px width, preserving every word and paragraph break between text blocks. Leave canonical translations, names, abilities and monster data unchanged.
- Change only the bestiary lore font from 28px to 22px with two guarded native constants. All entries fit within 20 lines and 459px of the 480px height budget; overflows block output rather than cutting text.
- Pass four lore, four quest and eleven runtime-wrapper tests. Independently verify all 636 overlay files, including 200 lore fields, 112 quest fields and the two lore font instructions. Only the executable differs from 0.1.17; stage it atomically and update the test launcher, preserving saves and controller settings.
- Retain quest wrapping, full class headings, compact item stats and previous fixes. Updated in-game appearance remains pending; no release is published.

## 0.1.17 — 2026-10-22 (local test build)

- Wrap quest request and objective display copies to 640px at the native 24px font. Preserve the full wording, item names, original client line and canonical translations.
- Cover 108 descriptions across 112 quest fields, including the reported Healing Salve Concentrate objective. All fit within three lines (74px high); reject overflows rather than cutting text. Independently verify relocated text and unchanged quest data.
- Pass four quest, three spell and four skill layout tests. Verify all 636 overlay files and all 112 installed quest display fields; only the executable differs from 0.1.16. Stage it atomically and update the test launcher while preserving saves and controller settings.
- Retain the class-heading, item abbreviation, name-entry and earlier layout fixes. Updated in-game appearance remains pending; no release is published.

## 0.1.16 — 2026-10-21 (local test build)

- Translate Samurai in the assembled name/class heading on Confirm Class. The existing deferred translation handled a standalone label but missed the class after a character name and slash.
- Give only this heading call an immutable full-English lookup for all thirteen classes. Preserve the native lookup, class-grid fixed copies, player names, format string and save data. Guard the original caller, lookup, class table and formatter before patching.
- Pass three heading guard/scope/ABI tests and eleven runtime-wrapper tests. Independently verify all 636 overlay files, including the installed hook and thirteen English names. Only the executable differs from 0.1.15; stage it atomically and update the test launcher.
- Retain 0.1.15 compact item stats and all previous fixes. Updated in-game appearance remains pending; no release is published.

## 0.1.15 — 2026-10-21 (local test build)

- Abbreviate compact item stat labels to Atk, Acc, Eva, Def, Rng and Elem. Keep the separate full-word labels and the existing deferred renderer aliases.
- Move the weapon preview's left label/value pairs 32px right so Elem fits inside the frame, and move the attack count 24px right to preserve its gap after the damage range. Keep the right column and all row positions.
- Pass 66 native-font layout cases and 13 targeted guard/runtime tests. Independently verify all 636 overlay files; only the executable differs from 0.1.14. Stage it atomically and update the test launcher, preserving saves and controller settings.
- Retain the previous name-entry, dialogue, subtitle and context-label fixes. Updated in-game appearance remains pending; no release is published.

## 0.1.14 — 2026-10-19

- Expand character name entry from six to twelve characters. Replace the separate eight-character name setter with a UTF-8-aware copy limited to twelve characters and the native 32-byte payload. Preserve the 33-byte name field, neighboring character data and save layout.
- Give the asynchronous PS3 keyboard dedicated writable state and larger initial/result buffers; guard each original instruction and pointer. Bound UTF-16-to-UTF-8 conversion before the saved-name copy.
- Add boundary/canary checks for full-length names, mixed Unicode, malformed input and 200 randomized cases. Updated in-game registration, display and save/load acceptance remain pending.
- Pass all 84 regressions and independent verification of the 636-file overlay. Stage only the matching executable and observe RPCS3 booting the game at about 60 FPS; retain the narrower scope of this startup observation.
- Prefer the project's local Python environment in the test launcher, preserving its dependencies across bundled-runtime updates. Retain all previous translation, layout and context-label fixes.

- Publish ISO patches from the original Japanese disc and the exact public English 0.1.11 image, using Retro Trans Tools build manifests and complete encode/decode verification. Retain the Prisoners-only scope notice and Macross release format.
- Verify all 1,513 package entries, all 1,483 installed files, every unselected disc payload, and independent ISO9660/UDF extraction of the exact installed package. Observe installed-game title-asset loading and continuing execution in a 300-second isolated startup probe without a logged fatal error or access violation. Retain nonfatal diagnostics and the unverified visual/gameplay scope separately.

- Confirm all five uploaded asset hashes, publish v0.1.14 as latest, and register the targeted Retro Trans catalog update. Recognition through the public application catalog verifies direct routes from the original Japanese ISO and public English 0.1.11 ISO to 0.1.14.

## Documentation — 2026-10-18

- Reformat the public 0.1.11 release description to follow Macross Triangle Frontier's section order, patch table and user-facing layout. Retain the Prisoners-only notice, Steam link, installation steps and verification limits.
- Clarify prominently in the README and the 0.1.11 release description that only Prisoners of the Lost City is translated. Link the official English Steam version of the first game, Labyrinth of Lost Souls, and retain this requirement in the release guide and project instructions.

## 0.1.13 — 2026-10-18 (local test build)

- Fix the local launcher stopping when RPCS3 is closed: the process lookup returned failure for an empty result. Explicitly return success when no matching emulator is active. Keep the active-session guard, saves, controllers and game binaries unchanged. Track the launcher template and add a read-only preflight option.
- Change sword weapon categories and preferred weapons from Kns to Swords at 13 references. Keep Kns only for the compact Kensei class label.
- Audit 295 short/shared source rows. Separate compact Mage (Mag) and Felpurr race labels from Magic and Beast monster categories. Flag the unresolved Light speaker-name occurrence for review; retain uncertain Evil category wording pending stronger evidence.
- Add guarded per-reference translations, independent pointer/string verification and eight regressions. Prevent exact-text reuse from importing contextual rows or their edition-specific addresses. Preserve the 0.1.12 portrait-dialogue fix.
- Pass all 77 regressions, 17 native dialogue cases and 5,222 event paragraph groups. Verify 2,976 executable text references, all 636 overlay files, all 1,513 package payloads and every ISO filesystem view. Preserve the other game and all unselected disc files.
- Stage the matching executable and update the launcher. Build full original-ISO and 0.1.11/0.1.12 upgrade patches through Retro Trans Tools; all three encode/decode round trips reproduce the exact new ISO. Record manifests and evidence under docs/builds/0.1.13.
- Keep this build local; updated in-game appearance remains pending.

## 0.1.12 — 2026-10-18 (local test build)

- Fix named portrait dialogue clipping beyond the right edge. Resource72 is 960px wide, and its native body begins 128px inside the frame; use an 800px text budget with 32px right padding. The old 896px budget did not account for the portrait inset. Keep the original 32px font, wording, colors, typewriter behavior and three-line pagination.
- Trace the original resource descriptor, renderer instructions and font pointers. Add regressions for all three reported Beatrix passages: the curse, the adventurer introduction and the Adventurers' Guild explanation. Preserve anonymous narration and battle layout budgets.
- Pass 69 regression tests, 17 host-native dialogue cases and all 5,222 event paragraph groups with complete text preserved. The curse passage now uses two pages; the other two reports fit one page each. Updated in-game visual confirmation remains pending.
- Build and independently verify the local PKG/ISO, preserving the other game. Prepare full original-ISO and small 0.1.11-to-0.1.12 upgrade xdelta candidates through Retro Trans Tools; both complete encode/decode round trips. Stage the new executable atomically and update the local launcher without interrupting active sessions or changing saves/controllers. This build remains local.

## 0.1.11 — 2026-10-17

- Register the ISO release in the public Retro Trans Tools catalog after the scheduled full-catalog update failed on an unrelated Vita entry. Verify that an actual public catalog refresh recognizes the original Perfect Pack ISO and selects `original → 0.1.11` through the same recognition code as app 0.5.17. Add catalog registration and live detection as required release-publication checks.
- Withdraw the public 0.1.10 package release to a private draft at the user's request. Switch distribution to an original-ISO-to-English-ISO xdelta patch, compatible with Retro Trans Tools.
- Rebuild Prisoners of the Lost City with `v0.1.11` in the title footer. Preserve the other game's package and all unrelated disc files.
- Update patching and installation instructions: select the original Perfect Pack ISO as the patch source, then extract and install its translated PKG01 package in RPCS3. Direct ISO boot and stock-console authentication are unsupported.
- Verify ISO9660, Joliet and four UDF reading paths, affected descriptor checksums, all 11 unselected file hashes and unchanged physical regions. Independently extract PKG01 with both 7-Zip ISO9660 and UDF readers; both exit successfully and match the exact new package installed in RPCS3.
- Pass all 64 regression tests, all 1,483 installed-file checks and a new 90-second startup probe. Verify the complete ISO-to-ISO xdelta encode/decode round trip with Retro Trans Tools. Keep visual/footer/playthrough limits and nonfatal emulator diagnostics explicit in the release evidence.

## 0.1.10 — 2026-10-17

- Add `v0.1.10` and `github.com/retro-trans` at the title screen's bottom right, using native text measurement, gray text and a black shadow. Preserve the copyright, title atlas and other menus.
- Prepare the first public English patch for the Perfect Pack NPJB00162 install package. Map the translated executable to normal EBOOT.BIN for RPCS3 installation; preserve the separate game and all unselected package payloads.
- Adopt the Macross Triangle Frontier repository/release layout: English-only sources, glossary, tools, MIT licence, contribution guide, release manifests, xdelta and full patch-round-trip verification through Retro Trans Tools.
- Retain the subtitle opening, anonymous-narration wrapping and all prior UI fixes. This remains an early translation build with review flags and incomplete playthrough coverage; stock PS3 firmware is unsupported.
- Correct package-name alignment and lengths against RPCS3's own decryption behavior. Install the package into a fresh isolated RPCS3 profile and verify all 1,483 installed files. Observe main-thread execution and translated asset loading in a 90-second headless startup probe; retain nonfatal diagnostics and the unverified visual/gameplay scope in the release evidence.
- Pass 57 regression tests, the translation/control/font checks and the Retro Trans Tools encode/decode round trip for the complete 1,114,929,056-byte target. Publish only xdelta, build/validation manifests and checksums. Record exact identities and source revision in `docs/releases/0.1.10/`.
- Stage the new executable atomically for the existing local test launcher; all other overlay files match. Preserve active emulator sessions, controller settings and saves. Restart is required to load the new footer.

## 0.1.9 — 2026-10-17 (local draft)

- Fix intro narration still clipping after the previous dialogue changes. Empty/anonymous speaker commands branch to a separate Show call before the ordinary/typewriter wrapping hook, so the earlier helper never ran for these passages.
- Hook the assembled anonymous-narration call at `0xa6084`. Reflow complete text within 896px and three lines per page, preserving its original centered `0xf0` flags, color controls and event-owned final acceptance. Wait only between extra pages; fitting passages retain the original native call.
- Add regressions for the exact despair and labyrinth paragraphs and prove that the actual intro commands select the formerly unhooked branch. Execute the emitted bridge with hostile register/stack clobbers and check every guarded byte, the original fallback and final script wait.
- Pass 14 host-native dialogue/narration cases, the 5,222-paragraph corpus audit, nine battle cases, eleven runtime regressions and three focused narration tests. Keep the subtitle opening and all previous UI fixes. Updated in-game wrapping remains pending.
- Independently verify all 636 overlay files, the anonymous Show hook and unchanged final script wait. Atomically stage only the executable; all other test files match. Update the launcher without interrupting the active game, saves or controller settings. Restart is required to load the fix.

## 0.1.8 — 2026-10-17 (local draft)

- Replace the opening's black narration cards with bottom-aligned English subtitles at the user's request. Use white 36px text with a black outline and at most two lines; remove every narration plate and title mask so the original imagery, Japanese lettering and logo remain visible.
- Split display text into 12 timed subtitle segments while preserving every word of the seven canonical narration/title translations. Export an SRT sidecar for inspection.
- Check timing, safe bounds, full wording and that the subtitle painter changes no central artwork. Rebuild and independently verify the movie's complete decode, packet/frame timing and original audio/container preservation.
- Keep all prior game text and layout fixes. Update the local test launcher after verifying the new overlay; in-game playback remains pending.
- Independently verify the 636-file overlay and all 2,210 decoded video frames. Only the opening movie differs in the existing test copy; the launcher applies it after the current emulator session closes, preserving progress and controller settings.

## 0.1.7 — 2026-10-17 (local draft)

- Replace six burned-in Japanese opening narration cards with English cards and replace the subtitle beneath the Wizardry logo. Follow the existing name glossary; preserve the complete narration.
- Preserve every original audio packet, container header, timestamp, access map, and video access-unit allocation. Restore compatible source VUI/HRD and timing SEI after encoding; use single-slice video to fit the smallest held pictures.
- Check all seven English text bounds and visually inspect decoded narration/title frames. Independently decode all 2,210 pictures and require identical packet/frame timing, picture types and geometry, with no decode errors.
- Include the verified movie in the local overlay and update the test launcher. Preserve the active emulator session, saves and controller settings; the movie applies when the previous test session closes. Updated in-game playback and listening remain pending.
- Independently verify all 636 overlay files. The staging dry run finds only `USRDIR/movie/opening.pam` differs; all 635 existing overlay files already match, so the launcher will apply only the movie.

## 0.1.6 — 2026-10-17 (local draft)

- Wrap all 20 skill-description display copies within the 264px status panel at the existing 22px text size. Preserve every word and canonical translation; the longest needs five lines.
- Fit complete inventory names within their list rows using native font measurements. Keep the original text height and reserve space for stacked-item quantities.
- Restore the complete Unidentified label through late expansion after the native ten-byte source copy. Avoid changing the native buffer sizes or truncating English.
- Save the two actual user screenshots and status/item geometry. Pass seven inventory tests including 84 instruction-executed cases and 1,716 corpus width cases, four skill tests, three spell regressions, ten runtime regressions and resolver checks for 19 copied labels plus three immediate labels.
- Independently verify the 635-file overlay, all 20 stored skill descriptions and the guarded inventory call. Atomically stage only the executable and update the launcher while preserving saves and controller settings. Updated in-game visual acceptance remains pending.

## 0.1.5 — 2026-10-17 (local draft)

- Fit the full Summoner school label before the first MP number while keeping MP digits at their original size.
- Reflow spell-description display copies to a 352px width. All 89 descriptions fit within six lines; 87 display copies change their line breaks. Use 24px horizontal / 22px vertical size and a 23px line pitch. Preserve every word and the canonical translations' authored newlines.
- Align the quest header using “Level” and center Status over its column. Remove decorative brackets that overlap Accepted and restore complete status strings through late aliases for Complete and Not Accepted.
- Move Slow 24px right in every selected/unselected settings path, preserving option text and colors.
- Wrap the complete formatted battle reward inside the narrow message box. Expand item-name tokens before layout, preserve hard line breaks and colors, show at most three lines per page, and retain the original final-page wait. Use native waits only between additional pages; keep the final two words together where possible.
- Pass ten runtime regressions, nine host-native battle cases, the eleven dialogue cases and 5,222-paragraph regression audit, three spell corpus/preservation tests, ten measured panel cases, and resolver checks for 18 copied labels plus three immediate labels.
- Independently verify the 635-file overlay, all 94 stored spell-description fields, six panel instruction changes and the battle Show/Wait boundary. Atomically stage only the executable and update the launcher. Updated gameplay appearance remains pending.

## 0.1.4 — 2026-10-17 (local draft)

- Fix the reported item-screen overlaps. Fit full class, status, monster-type and bonus labels inside their existing cells using native measurement; retain cell centers, row spacing and selected colors. Use 22px height and reduce horizontal size only when required.
- Move all four armor/accessory preview stat label/value pairs 80px right into their panel; preserve their vertical positions and the separate weapon/miscellaneous branches.
- Extend late expansion to seven preview labels whose native byte copies omitted English terminators. Replace narrow item headings with “Slot” and “Effects” and the footer with “Organize”.
- Recover and translate Hands, Feet and Head slot labels assembled from immediate UTF-8 bytes in code. Add three source rows, bringing the inventory to 11,387 rows / 16,638 occurrences and 10,796 English drafts.
- Save the three actual screenshots and measured item UI geometry. Pass 53 item-layout checks, 58 previous menu checks, 17 runtime/guard unit tests including 84 instruction-executed sizing scenarios, and resolver checks for 16 copied labels plus three immediate labels.
- Independently verify the 635-file overlay, seven fitting groups and four preview rows. Atomically stage only the changed executable and update the launcher; saves and controller settings are preserved. Updated in-game appearance remains pending.

## 0.1.3 — 2026-10-17 (local draft)

- Fix the reported registration, party and class overlaps with measured compact labels and class descriptions. Restore the full Samurai and Register labels. Correct the roster's inherited “Medium” alignment to “Neut.”.
- Preserve original terminated bytes for nine labels copied by native fixed-size instructions; expand their English text at the final font boundary. This also fixes the equipment header reading the previous item's `030~` token suffix.
- Authenticate and inventory all 14 protected dungeon archives. Translate 13 newly recovered location names, including Bofonkerk and Labyrinth of Lingering Souls. Use compact shared display names where the dungeon header must also fit an area number.
- Redirect the verified dungeon pathname to ordinary ENC files. Preserve all floor records, binary metadata and background members; leave the original EDAT files intact.
- Expand the inventory to 11,384 rows / 16,635 occurrences: 10,793 English drafts and 591 internal/parser exclusions, with 448 review-status entries.
- Pass eight runtime-wrapper regressions, three dungeon authentication/loader regressions, 17 native resolver edge cases, nine original-sized label-copy cases, the reused equipment-buffer regression, and 58 font-width checks. Independently verify the 635-file overlay and unchanged non-text content.
- Save the five actual user screenshots and measured UI geometry. Prepare the launcher to apply the 15 differing files after this project's emulator closes, preserving saves and controller settings. Updated in-game visual confirmation remains pending.

## 0.1.2 — 2026-10-17 (local draft)

- Reflow event dialogue and narration inside the standard message box using native font measurements at 32px and an 896px inner width. Keep three visible lines per page and use the native advance action for overflow pages.
- Lay out the complete paragraph after actor substitutions; preserve source records, translation wording, event branches, color controls and typewriter behavior. Retain authored blank-line boundaries as page boundaries.
- Guard the native 128-byte line slots and account for brackets expanded into color tags. Support two-digit color controls and UTF-8 boundaries.
- Add a guarded event presenter bridge that preserves registers, linkage, condition flags and the original paths for fitting paragraphs.
- Pass seven runtime-code regression tests, eleven native C layout cases and a 5,222-paragraph corpus audit. The audit reflows 1,143 groups without dropping or reordering text; both reported passages fit one three-line page.
- Build and independently verify the 621-file overlay, then atomically update only the staged executable. Existing game sessions, controller settings and saves are preserved; restart is required. In-game visual confirmation remains pending.

## 0.1.1 — 2026-10-17 (local draft)

- Fix the New Game crash in the database text renderer hook. The positioned drawing function at `0x164ea4` receives its UTF-8 string in r6 and x/y coordinates in r4/r5; the old wrapper dereferenced x=107 as address `0x6b`. Correct the register mapping and add a regression against the original caller/callee instructions.
- Build and independently verify the 621-file overlay, including 2,417 relocated database fields. Refresh the isolated test game while preserving its controller profile and save data.
- Add the seven Perfect Pack bonus-item rows and their 12 stored text fields; include `ppdata.enc` in relocation and independent non-text preservation checks.
- Apply independent context-review corrections to 15 event entries, four bestiary/item entries and two quest entries; retain uncertain readings as review items.
- Complete decisions for 11,371 rows: 10,780 English drafts and 591 internal/parser exclusions. Record 448 review-status entries and 450 review notices.
- Retain exact-source provenance for all 6,092 reused decisions, including the recovered station event. Newly authored decisions total 5,279.
- Expand the source-backed database-name glossary to 524 entries. Add census, format, local-testing and translation-status documentation.
- Extend the font audit to check all 96 codepoints used by the English drafts; all are present in the original font.
- Save the actual English title screenshot and measured coordinates. Record that automated Start input also fails with the untouched original executable; menu/database runtime acceptance remains pending.
- Add versioned local overlay verification, isolated staging refresh and CRC-checked local bundle tooling.
- Add a double-click launcher for the existing staged 0.1.0 test checkpoint and separate play instructions from the unbuilt 0.1.1 workflow.

## 0.1.0 — 2026-10-17 (local checkpoint)

- Identify the supplied install disc as BLJM61008 and isolate its NPJB00162 Prisoners of the Lost City package; leave NPJB00163 unchanged.
- Add a bounded ISO9660 reader supporting the package's two extents; extract originals only under ignored local source storage.
- Inventory 613 event scripts including an authenticated protected station event, executable text, trophies, base databases and both additional-scenario databases.
- Export 11,364 contextual rows and reuse 6,092 exact-source decisions from the neighboring project, retaining provenance and uncertainty.
- Build an inherited/researched glossary with additional-scenario terms and 521 source-backed item, monster and spell name entries.
- Draft additional-scenario dialogue, narration, choices, items, bestiary lore and quest text in English; preserve functional puzzle answers and mark localizations requiring runtime checks.
- Port executable relocation and three renderer hooks to the Perfect Pack executable; support added database archives without changing IDs, record sizes or non-text fields.
- Retain full English strings in relocated storage rather than truncating to Japanese byte slots.
- Add local validation and reversible generation of graphics/metadata. Runtime layout, movie captions and full playthrough remain separate acceptance work.

The 0.1.0 snapshot contains 620 overlay files and predates the bonus-item export and final review corrections. Final contents and outstanding issues belong in each build manifest and the translation status report.
