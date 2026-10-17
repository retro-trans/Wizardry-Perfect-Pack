# Translation status

All **11,387 extracted rows** have decisions: **10,796 English drafts** and **591 documented exclusions** for executable internals/parser data. The validation pass reports zero missing decisions and zero control-code, placeholder or newline-count errors. There are **448 entries with review status** and **450 review notices** in total, including retained Japanese clue glyph notices. Review status is not removed merely because a build succeeds.

The 4,903 newly drafted event entries received independent Japanese/context review by another translation agent. Added quest text and new item/bestiary terminology also received independent review. Corrections include actor/subject attribution, quest-item terminology, singular/plural meaning and a priest/cleric reference. Exact-source imports retain their inherited uncertainty and are not claimed as newly proofread throughout this edition.

The glossary preserves evidence and uncertainty. Character gender is recorded only when supported by the source/context; unfamiliar names are not used as gender evidence. Some additional-scenario place names, wordplay, compound attack names and staff-name readings remain provisional. Functional puzzle choices keep their ordering and game logic; English wordplay adaptations need playthrough testing.

Full English text is stored in relocated memory rather than cut to Japanese byte capacities. Database record lengths, IDs and non-text bytes are preserved. Event control data and unselected records are compared independently after building. The original font covers every codepoint used in the English drafts; variable-width behavior has static instruction and font-metric verification. Actual screen wrapping still needs broader game testing.

## Acceptance work still required

- Inspect dialogue, long item/monster descriptions, quest windows and name entry in game for wrapping, clipping and substituted runtime names.
- Exercise the three renderer hooks across all relevant screens and both extra scenarios.
- Test save/load, branch selection, accepted-input puzzles, trophy installation and scenario access with real progress.
- Resolve the review-status entries against stronger context or authoritative readings where possible.
- Complete a playthrough; retail console signing/installation is outside the present ELF overlay workflow.

Build manifests and saved UI captures report the narrower checks actually performed. Public version 0.1.10 distributes a package-to-package xdelta patch for RPCS3, with separate installed-file and startup evidence. Local overlays remain developer test outputs. Stock-console signing and full-playthrough verification remain outside the completed checks.

## Runtime observations

The user's New Game test exposed a crash in 0.1.0: the positioned drawing hook treated the x coordinate as a string pointer and tried to read address `0x6b`. Version 0.1.1 corrects the hook to use r6 for the string. The user's subsequent screenshots confirm that New Game reaches the English introductory narration. Those screenshots exposed clipping from original fixed script lines.

Version 0.1.2 adds full-paragraph runtime wrapping and three-line pagination. Seven runtime-code checks, eleven native C cases and all 5,222 extracted event paragraph groups pass the layout tests; 1,143 groups reflow. A restarted in-game visual test of wrapping remains pending. See `docs/dialogue_layout.md` for measured bounds and implementation limits.

The user's later screenshots confirm character registration, party formation, class confirmation, travel selection and Bofonkerk dungeon entry with the previous build. They expose overlapping labels, fixed-copy truncation, an inherited alignment mistranslation and untranslated protected dungeon names. Version 0.1.3 addresses those findings and adds 13 source rows. Its 635-file overlay passes independent verification, eight wrapper regressions, three dungeon authentication/loader regressions, 17 native resolver cases, nine fixed-copy label cases, a reused equipment-buffer regression and 58 measured font-budget checks. The launcher applies the update after the active test emulator closes. Updated gameplay captures remain pending; see `docs/menu_layout.md`.

The 0.1.0 overlay boots in the isolated emulator, displays English usage precautions and the English title, and returns from the original opening movie to the title. A real title capture is saved in `work/ui/`. Earlier automated Return/confirm presses did not advance the Start prompt even with the untouched original game. The user subsequently configured XInput and reached gameplay; the earlier automated-input limitation does not establish a game defect. Current testing must preserve that controller profile and the user's save data.

Version 0.1.4 addresses the subsequent Items screenshots: popup cell fitting, four preview stat rows, preview-label terminators, compact headings and three newly exported slot literals. Its 635-file overlay is independently verified and the staged executable matches. The fitting tests execute the emitted instruction subset with deliberate native-call clobbers; 84 sizing scenarios pass. The actual updated in-game appearance remains pending. See `docs/item_layout.md`.

Version 0.1.5 addresses the subsequent spell, quest, settings and battle-reward screenshots. It reflows spell display copies without changing canonical wording, corrects quest/status and settings spacing, and pages the fully formatted reward after item-name expansion. The native-host tests preserve all reward text and final-wait ownership; the event corpus still passes. The verified 635-file overlay is staged with an executable-only update. Updated in-game visual acceptance remains pending. See `docs/panel_layout.md`.

Version 0.1.6 addresses the Status and Items screenshots: skill descriptions wrap within their narrow panel, inventory names fit their row with quantity space, and the full Unidentified label expands after its native fixed-size copy. All 20 skill descriptions preserve their words and need at most five lines at the original text size. Canonical translations are unchanged. Updated in-game visual acceptance remains pending.

Version 0.1.7 replaces the opening's burned-in Japanese narration with six English cards and replaces the Japanese subtitle beneath the Wizardry logo. All seven text layouts pass font-bound checks and decoded-frame visual review. Every original audio packet and non-video container byte is preserved. The final movie independently decodes all 2,210 pictures with identical packet/frame timing, picture types and geometry. The local overlay includes the verified movie; the launcher applies it after the active test session closes. Updated in-game playback and listening remain pending. See `docs/opening_movie.md`.

Version 0.1.8 follows the user's preference for subtitles: remove all black cards and masks, retain the original Japanese lettering and imagery, and add outlined English at the bottom. Twelve timed display segments preserve every word of the seven canonical English entries, with at most two lines each. All subtitle bounds and wording checks pass; decoded frames are visually reviewed. The movie again passes complete software decoding and timing/audio/container comparisons. The launcher applies the verified movie after the active session closes; updated in-game playback remains pending.

Version 0.1.9 corrects the previously incomplete event-hook coverage. Actual intro commands select an anonymous-narration branch that jumps past the ordinary/typewriter reflow hook. A guarded additional Show bridge covers that branch, preserving native centered flags and script-owned final acceptance. Tests include the exact reported passages, actual intro command dispatch/state/branch instructions, emitted bridge execution and full wording/color preservation. This explains why the earlier helper-only layout checks passed while the user's narration still clipped. Updated in-game visual confirmation remains pending.
