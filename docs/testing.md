# Local build and testing

## Test local 0.1.21 collection categories

Save and close the project test session, run `work/output/Play-English-Test.cmd` and confirm **v0.1.21**. Open Item Collection: the long weapon groups should read **Blades**, **Staff/Blunt** and **Thrown**. Check both the percentage list and the category heading, then cycle through every category. Percentages should remain separate from labels and the heading should fit between L1/R1. Individual item names and other type labels keep their existing wording. All twelve group labels have complete-string and width checks; updated in-game appearance is pending. The public release remains 0.1.14.

## Test local 0.1.20 bestiary status labels

Save and close the project test session, run `work/output/Play-English-Test.cmd` and confirm **v0.1.21**. Open Magic Tree's status in the bestiary: the rewards should read **Gold: 6** and **EXP: 36**, without garbage characters. All stat labels should end at the same column, with a 12px gap before the aligned values. Check larger rewards and the additional statistics unlocked after more kills, including **Spell Res:**. Recheck lore wrapping by switching views. Native copy guards, renderer tests and all nine pairs' dimension checks pass; updated in-game appearance is pending. See [the layout notes](bestiary_status_layout.md). The public release remains 0.1.14.

## Test local 0.1.19 item descriptions

Save and close the project test session, run `work/output/Play-English-Test.cmd` and confirm **v0.1.21**. Select Healing Salve Concentrate and check that its complete description, through “fully concentrated,” fits inside the preview box. Ordinary descriptions use a 20px body font and up to five lines. Check a long item description, then a weapon and armor preview to confirm their stat labels retain their existing font. All 76 descriptions have word and dimension checks; updated in-game appearance is pending. The public release remains 0.1.14.

## Test local 0.1.18 bestiary wrapping

Save and close the project test session, run `work/output/Play-English-Test.cmd` and confirm **v0.1.21**. In the bestiary, open Undead Goblin and read through the final sentence about its stench in the labyrinth. The complete description should remain inside the right frame, with paragraph breaks. Lore uses a 22px font; the monster list and names retain their own fonts. Recheck long entries and the status/hide controls. All 200 descriptions have word and dimension checks; updated in-game appearance is pending. The public release remains 0.1.14.

## Test local 0.1.17 quest descriptions

Save and close the project test session, run `work/output/Play-English-Test.cmd` and confirm **v0.1.21**. Open The Mysterious Female Thief and check that the objective includes the complete phrase about recovering Healing Salve Concentrate from the grizzlies and giving it to Fiore, with a clear right margin. Check requests before acceptance and longer objectives, including multi-item collection quests. The client line stays above the body; the body fits within three lines. All 108 descriptions have metric/word-preservation checks; updated in-game appearance is pending. The public release remains 0.1.14.

## Test local 0.1.16 class heading

Save and close the project test session, then run `work/output/Play-English-Test.cmd` and confirm **v0.1.21**. On Confirm Class, the reported heading should read **Seraphine / Samurai**. Recheck other characters/classes and the Samurai entry in the selection grid. All thirteen full class names in this heading have independent file checks; updated in-game appearance is pending. This build includes the 0.1.15 item abbreviations. The public release remains 0.1.14.

## Test local 0.1.15 item abbreviations

Save and close the project test session, then run `work/output/Play-English-Test.cmd` and confirm **v0.1.21**. Inspect the reported sword: Atk:52~170, Acc:2, Rng:M, Eva:0, Def:1 and Elem:None should fit inside the preview, with a gap before x2. Check an armor/accessory preview as well. The source labels retain their renderer aliases. This is a local build; the public release remains 0.1.14.

## Test the local 0.1.14 name-entry fix

Save progress, close the project test session and run
`work/output/Play-English-Test.cmd`. Confirm **v0.1.21**. The keyboard should
accept `Vedette` and up to twelve English characters. Complete registration,
check the name in the roster/status screens, then save and restart to check
that it persists. [Name-entry notes](name_entry.md) describe the unchanged
save layout, byte limit for multibyte names and outstanding visual checks.
This build also includes the earlier dialogue-width and context-label fixes.

## Test the local 0.1.13 context-label fix

The 0.1.13 context-label fixes are included in 0.1.14. Use the current launcher
and version check above.
The launcher template is tracked at `tools/templates/Play-English-Test.cmd`.
Its `--check` option checks the emulator path and active-session guard without
staging files or opening RPCS3. A closed emulator is a successful preflight;
an active project test session still blocks a second launch.
In class confirmation, Fighter and Lord should show `Weapons: Swords`.
Sword item categories should also read Swords. Compact Kensei class labels
retain Kns; compact Mage labels use Mag. The race label uses Felpurr, while
the monster categories remain Magic and Beast. See
[the context audit](short_label_context.md) for the verified scope and remaining
uncertainties. Recheck the portrait-dialogue cases below as well.

The public 0.1.14 release includes these fixes. Apply its full patch to the original Japanese ISO or its upgrade patch to the exact public English 0.1.11 ISO. Extract PKG01 and install it in RPCS3 as described below.

## Test the local 0.1.12 portrait-dialogue fix

The 0.1.12 portrait-dialogue fix is also included in 0.1.14. Use the
current launcher and version check above. It preserves controller settings
and saves.

Revisit Beatrix's curse explanation, her adventurer introduction and the
Adventurers' Guild explanation. The curse paragraph should use two pages;
the other two should fit on one three-line page. All words, including
“reach,” “be” and “for adventurers,” must remain visible, with a right margin.
The dialogue uses an 800px budget within the portrait frame. Anonymous
narration and battle messages retain their separate layout settings.

Native-resource guards, all three reported passages, full-text pagination
and the corpus checks pass. Updated in-game appearance still needs testing.

## Test the 0.1.14 ISO release

The current build is **0.1.14**, with the footer updated to `v0.1.14`.
Independent ISO9660 and UDF extraction both produce the exact new package
verified in a fresh RPCS3 profile. Installation and all 1,483 installed-file
hashes pass. See the release evidence for the separate startup observation
and retained emulator diagnostics. Title/footer appearance and
complete gameplay remain unverified. See the versioned release evidence.

The required source is `Wizardry - Perfect Pack (Japan).iso`,
**2,081,947,648 bytes**, SHA-256
`25dc1f842f42dbd9e24ee1a23e23e51e339fc406bed997c8fbdb9815d41a42a7`.
The verified target is **2,123,663,360 bytes**, SHA-256
`736471ff2087f1f735693c7c227de377481f1ccea111d8a7fc22b6db43f94f6b`.

1. Apply `Wizardry-Perfect-Pack-Prisoners-English-v0.1.14.xdelta` to the
   original **ISO**, using Retro Trans Tools Automatic or manual xdelta.
   The patch must produce a new ISO whose whole size/hash matches the release
   manifest. It does not take an original PKG as its patch input.
2. Inspect and extract PKG01 from the patched ISO into a fresh directory:

   ```powershell
   python tools/disc_read.py "Wizardry-Perfect-Pack-Prisoners-English-0.1.14.iso"
   python tools/disc_read.py "Wizardry-Perfect-Pack-Prisoners-English-0.1.14.iso" --path /PS3_GAME/PKGDIR/PKG01/INSTALL.PKG --extract work/local/iso-0.1.14
   ```

   Join all package extents. The disc builder/independent verifier must also
   check the UDF view, identical PKG01 bytes through both views, and unchanged
   PKG00 and other unselected file payloads.
3. Use a fresh isolated RPCS3 data root for the release probe, creating its
   `log/` directory before launch. Allow cold-cache compilation to finish
   before timing runtime execution. Through
   **File → Install Packages/Raps/Edats**, install the extracted
   `work/local/iso-0.1.14/PS3_GAME/PKGDIR/PKG01/INSTALL.PKG`, then boot the
   installed Prisoners of the Lost City entry. RPCS3 does not boot this ISO
   directly. Verify the installation log and installed file hashes separately
   from startup and gameplay; an installer process exit code alone is
   insufficient.
4. Confirm the title footer reads `v0.1.14` above `github.com/retro-trans`.
   Record normal boot and visual results for this exact new build.

Do not replace or operate on a player's active emulator profile for release
probes. Keep its controller settings and saves. Retain the untouched original
ISO so the original installation can be restored if needed.

## Gameplay and visual checks

Recheck the intro narration about Chu Lu Gah's despair and the mist surrounding
the city. Anonymous passages previously skipped the wrapping hook. The despair
paragraph should fit one page of at most three lines; the labyrinth paragraph
should have two pages, with an advance between them and the script's original
final acceptance afterward. Tests trace the actual intro branch and check full
text and colors. See [dialogue layout](dialogue_layout.md).

Watch the full opening: outlined English subtitles should appear at the bottom
in one or two lines. Original Japanese lettering and artwork remain visible,
with no black cards. Check subtitle changes, the title subtitle at the end,
music, smooth scene transitions and return to the title. All 2,210 pictures
have software decode/timing checks and original audio-packet comparisons;
in-game playback and listening still need confirmation. See
[opening movie](opening_movie.md).

Revisit Status with Gibson's Identify skill. Its full description should fit
the left panel. In Items, check the full Protective Gear-like Object name,
Unidentified in the right panel, and a stacked item's gap before its quantity.

Revisit Spells, Quests, Settings and a battle reward. Check Summoner against the
first MP number, full spell descriptions, quest header/status spacing, Normal
versus Slow, and reward text on three-line pages. Extra reward pages should
retain the original final acceptance. Check preview stat rows, popup cell gaps,
Slot, Effects and Hands. Revisit character registration, party formation,
Samurai, alignment/class columns, travel selection and Bofonkerk's dungeon
header. These have static and host-native checks; broad visual acceptance is
incomplete.

Check save/load, scenario access, quest progression, accepted-input puzzles and
trophies with real progress. Report clipped text, visible `~T...~` tokens,
untranslated text or crashes with the version, location, exact wording and a
screenshot when possible. There are 448 translation entries retaining review
status; a successful build does not remove that uncertainty.

## Rebuild and developer overlay testing

Use 64-bit Python and `tools/requirements.txt`. Source files remain under
ignored `work/source/NPJB00162/`. The original ELF must have SHA-256
`2e23b466028ac0a18f7f46522fe1847d5c918a129605a2bdc1c56ca31da82bba`.

1. Run `tools/check_translation.py --complete`, `tools/strip_jp.py`,
   `tools/check_vwf.py` and the relevant runtime/resolver/layout tests. Inspect
   plans before write modes; use `strip_jp.py --write` before committing.
2. Generate and inspect English graphics, compile the resolver and dialogue
   presenters, and verify the subtitled opening. Run
   `tools/test_dialogue.py --write --corpus` for native-host layout/corpus checks.
3. Dry-run `tools/build.py --runtime-tables --graphics --version 0.1.14`,
   including its verified movie input. Write to a fresh build directory and
   run `tools/verify_build.py work/output/0.1.14 --write`.
4. Rebuild and verify the RPCS3 package, then construct and verify the ISO as
   described in [the release guide](RETRO_TRANS_RELEASES.md). Release acceptance
   must use a package freshly extracted from this ISO.
5. For separate developer overlay tests, close only this project's isolated
   test session, inspect `tools/stage_test.py work/output/0.1.14 --changed-files`,
   then use its write mode when the plan is correct. Boot the staged
   `USRDIR/EBOOT.elf` only for that overlay workflow. This does not validate the
   release ISO, package extraction or normal installed-game boot.

The existing local XInput profile has reached character creation and dungeon
exploration in earlier tests. Preserve that profile and saves; restart the game
to load a changed executable. Developer overlay launchers and historical
runtime observations must not be presented as fresh ISO release validation.
