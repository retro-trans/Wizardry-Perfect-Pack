# Local build and testing

## Play the existing test build

The test build is **0.1.10**. Save your progress and close any previous test session, then double-click `work/output/Play-English-Test.cmd` in File Explorer. The launcher applies the new executable and any pending subtitled-movie update before starting the game. Controller settings and saves are preserved. Check that the title screen shows `v0.1.10` above `github.com/retro-trans` at the bottom right. Native text measurement aligns both lines to the same right edge.

Recheck the intro narration about Chu Lu Gah's despair and the mist surrounding the city. These anonymous passages previously skipped the wrapping hook. The despair paragraph should fit one page of at most three lines; the labyrinth paragraph should have two readable pages, with an advance between them and the original final acceptance afterward. The new tests follow the actual intro branch as well as checking full text and colors. See `docs/dialogue_layout.md`.

Watch the full opening: outlined English subtitles should appear at the bottom in one or two lines. The original Japanese lettering and artwork should remain visible, with no black cards. Check subtitle changes through the longer passages, the title subtitle at the end, normal music playback, smooth scene transitions and return to the title. All 2,210 pictures pass software decode and timing comparisons, and audio packets match the original; playback inside RPCS3 is still awaiting your test. See `docs/opening_movie.md` for the format and preservation checks.

Revisit Status with Gibson's Identify skill. Its full description should fit within the left panel. In Items, select Protective Gear-like Object and check that its full name fits the list and the right-hand panel shows Unidentified. Check a stacked item too: its name should leave a gap before the quantity.

Revisit Spells, Quests, Settings and a battle reward. Check Summoner against the first MP number, the full spell description, quest header/status spacing, Normal versus Slow, and reward text on three-line pages. Long rewards should require an advance between pages, followed by the original final acceptance. Then revisit the Items list and View Details for Gloves and Adventurer's Ring. Check that the four preview stat rows sit inside their box, the popup grids have gaps between labels, the headings show Slot and Effects, and the slot value shows Hands. Also revisit character registration, party formation, class confirmation, the travel menu and Bofonkerk's dungeon header. Check the Equipment heading and main/sub-hand names, Register, Samurai, the alignment column and the class-detail columns. The travel label for Labyrinth of Lingering Souls is shortened to “Lingering Souls” so it also fits the shared dungeon header with an area number. These changes have static and host-native checks; updated in-game screenshots remain pending.

This build includes the review corrections, seven bonus-item translations and the English opening movie. Check dialogue, menus and item descriptions for clipped text, visible `~T...~` tokens, untranslated text or crashes; report the location and exact wording.

## Rebuild from current sources

Use 64-bit Python and the dependencies in `tools/requirements.txt`. Original files stay under ignored `work/source/NPJB00162/`. The source executable must have SHA-256 `2e23b466028ac0a18f7f46522fe1847d5c918a129605a2bdc1c56ca31da82bba`.

1. Run `tools/check_translation.py --complete`, `tools/strip_jp.py`, `tools/check_vwf.py`, `tools/test_runtime_text.py` and the native resolver edge-case checks. Inspect the output before using write modes.
2. Generate and inspect the English graphics, then run `tools/compile_resolver.py` and `tools/compile_dialogue.py`. Run `tools/test_dialogue.py --write --corpus` for native C layout and corpus checks.
3. Dry-run `tools/build.py --runtime-tables --graphics --version 0.x.y` with a new version. Write only to a fresh output directory with `--write`; existing snapshots are never overwritten.
4. Run `tools/verify_build.py work/output/0.x.y --write` to independently check manifest hashes, event payloads, database tokens and unchanged non-text fields.
5. Close this project's test emulator. Dry-run `tools/stage_test.py work/output/0.x.y --changed-files`, then use `--write` to update differing overlay files while preserving controller settings and saves. This mode checks the running emulator path before writing. A complete refresh is available with `--update-existing`. For an executable-only update, `--executable-only` requires all other overlay files to match and atomically swaps only the ELF; restart the game to load it. These modes do not edit the original extraction or a regular emulator installation.
6. Boot `work/source/rpcs3_reader/dev_hdd0/game/NPJB00162/USRDIR/EBOOT.elf` in the isolated emulator. The untouched retail EBOOT.BIN is not the translated executable. Firmware is required by the emulator.

The user has configured an XInput controller and reached character creation and dungeon exploration. If selecting the optional Keyboard profile, its mappings are Return for Start, C for Circle/confirm, X for Cross/back and arrow keys for the D-pad. Confirm the active profile in Pads before testing.

The overlay is a local developer test output. The public release instead patches the original Perfect Pack PKG01 `INSTALL.PKG` into an RPCS3-installable package through Retro Trans Tools. Install that patched package normally in RPCS3 and boot its normal game entry; do not use the overlay-only EBOOT.elf instructions for the release. See the README and release guide for the exact source hash, patching and installation instructions.

Rollback by discarding the isolated test game or overlay and restoring files from the untouched original extraction. Keep save data separately if a later test creates progress worth retaining.
