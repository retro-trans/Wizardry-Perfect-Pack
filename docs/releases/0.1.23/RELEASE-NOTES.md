English fan translation of **Wizardry: Prisoners of the Lost City** for PS3 (**NPJB00162 / PKG01**), distributed as ISO patches for the Japanese **Wizardry Perfect Pack** disc (**BLJM61008**). The translated package is intended for RPCS3.

**Only Prisoners of the Lost City, the second game in Perfect Pack, is translated.** **Wizardry: Labyrinth of Lost Souls**, the first game, is unchanged. Its official English PC version is available on [Steam](https://store.steampowered.com/app/948640/Wizardry_Labyrinth_of_Lost_Souls/).

### Apply

**Recommended:** Open the latest [Retro Trans Tools](https://github.com/retro-trans/retro-trans-tools) app, click **Refresh catalog**, then use **Automatic**. Select your original Japanese ISO or an unmodified public English 0.1.11/0.1.14 ISO, choose **0.1.23** or **Latest**, and save to a new ISO filename. The app selects the matching patch and verifies the complete output.

**Manual patching:** Use [DeltaPatcher](https://github.com/marco-calautti/DeltaPatcher), [xdelta3](https://github.com/jmacd/xdelta), or the app's **Apply xdelta** tab:

| Your source image | Patch |
| --- | --- |
| Original Japanese Perfect Pack ISO (BLJM61008) | `Wizardry-Perfect-Pack-Prisoners-English-v0.1.23.xdelta` |
| Public English 0.1.14 ISO | `Wizardry-Perfect-Pack-Prisoners-English-v0.1.14-to-v0.1.23.xdelta` |
| Public English 0.1.11 ISO | `Wizardry-Perfect-Pack-Prisoners-English-v0.1.11-to-v0.1.23.xdelta` |

```text
xdelta3 -d -s "Wizardry - Perfect Pack (Japan).iso" "Wizardry-Perfect-Pack-Prisoners-English-v0.1.23.xdelta" "Wizardry-Perfect-Pack-Prisoners-English-0.1.23.iso"
```

Original Japanese ISO: **2,081,947,648 bytes**, SHA-256 `25dc1f842f42dbd9e24ee1a23e23e51e339fc406bed997c8fbdb9815d41a42a7`.

English 0.1.23 output: **2,123,665,408 bytes**, SHA-256 `5e9d937da764678bc8981ca995236f569b6e98ff7f6a14585e53e7b4ca73d1c5`.

The upgrades require exact public images. Both previous ISOs are 2,123,663,360 bytes: **0.1.14** has SHA-256 `736471ff2087f1f735693c7c227de377481f1ccea111d8a7fc22b6db43f94f6b`; **0.1.11** has SHA-256 `1e92be73fa5456f04245705e880f64a9464e881e418fb4828b2fd334f2fa8877`. For other builds, use the original Japanese ISO and the full patch.

`BUILD-MANIFEST.json` identifies all three patch routes. `VALIDATION.json` records their complete encode/decode checks; `SHA256SUMS.txt` covers the downloads. Patch the ISO itself, rather than an extracted package.

**RPCS3 installation:** This is an install disc; RPCS3 does not boot it directly. Extract `/PS3_GAME/PKGDIR/PKG01/INSTALL.PKG` from the **patched ISO**, joining every file extent. With this repository and Python:

```text
python tools/disc_read.py "Wizardry-Perfect-Pack-Prisoners-English-0.1.23.iso" --path /PS3_GAME/PKGDIR/PKG01/INSTALL.PKG --extract work/local/iso-0.1.23
```

Choose **File → Install Packages/Raps/Edats** in RPCS3, install the extracted PKG01, then boot **Prisoners of the Lost City**. The complete English package is **1,114,929,200 bytes**, SHA-256 `429964e07f996502288aa14387d989c2e37eb7347fcea7bb11077ab71b95f4cd`. Back up saves and retain your original ISO. [Detailed installation instructions](https://github.com/retro-trans/Wizardry-Perfect-Pack#applying-the-patch).

### What's included

**Changes since public 0.1.14:**

* **Descriptions:** wrap quest requests/objectives, all 200 exported bestiary lore entries and ordinary item previews inside their panels, preserving complete wording.
* **Item screens:** compact Atk/Acc/Eva/Def/Rng/Elem labels, adjusted preview spacing, and Blades, Staff/Blunt and Thrown category groups in Item Collection.
* **Class confirmation:** translate the assembled name/class heading, including Samurai, with full English class names.
* **Bestiary status:** repair truncated Gold/EXP labels and align stat labels and values in separate columns.
* **Treasure chests:** split the illustrated chest prompt into two complete lines beside the icon.
* **Battle Record:** keep all thirteen monster categories inside three fixed columns; repair Wipeouts/Chests labels and separate counters from their labels.
* **Title footer:** show `v0.1.23` and `github.com/retro-trans`.

All earlier translation work is included: exported dialogue/narration and additional scenarios; identified menu, system, item, spell, skill, quest, monster, dungeon and trophy text; selected title/help graphics; English opening subtitles; dialogue/battle pagination; and names of up to twelve English characters within the existing save field.

The extracted corpus has **11,387 decisions**: 10,796 English drafts and 591 internal/parser exclusions. This is a count of extracted text, not proof of complete coverage. The patch changes PKG01 and required disc metadata; PKG00 and every other unselected disc payload remain unchanged. [Changelog](https://github.com/retro-trans/Wizardry-Perfect-Pack/blob/main/CHANGELOG.md).

### Release status

**Early build: further proofreading and full in-game playtesting are needed.** Verification covers all 636 overlay files, 1,513 package entries, independent ISO9660/UDF package extraction, 111 project regressions, and 5,222 dialogue paragraphs. All three ISO patches reproduce the complete target image. RPCS3 logs a successful installation and all 1,483 installed files match, but its headless installer exits with a teardown error. Fresh-profile installation and limited startup observations are documented separately in the [release evidence](https://github.com/retro-trans/Wizardry-Perfect-Pack/tree/v0.1.23/docs/releases/0.1.23).

Known limitations:

* **451 entries remain marked for review.** Names, ambiguous lines and adapted riddles still need proofreading and gameplay checks.
* The latest layout changes pass file and font-width checks; their appearance throughout the game has not received full visual acceptance.
* The expanded name keyboard, registration, name display and save/load need broader testing. The keyboard's native prompt remains Japanese. Names are limited to twelve characters and 32 UTF-8 bytes; multibyte names can reach the byte limit earlier.
* Opening subtitles retain the Japanese lettering, artwork and audio. Full movie decoding/container checks pass; in-game playback/listening needs further confirmation.
* Scenario progression, trophy behavior and a complete playthrough remain unverified.
* This is an **RPCS3-only build with a decrypted executable**. Physical-console and stock-firmware compatibility are unsupported. Installation/startup reports retain emulator diagnostics and distinguish file checks from visual/gameplay testing.

**Restart the game after installing the package.** A running session keeps the executable and text already loaded in memory.

### How it was translated

This is a **machine translation**, drafted with large language models and edited using scene context and a researched glossary. Identical text and terminology were reused from the neighboring *Wizardry Prisoners of the Lost City* project, with its unresolved questions retained. Perfect Pack's executable references and layout changes were traced for this edition. Human proofreading and playtesting are welcome.

### Acknowledgements

* The neighboring **Wizardry Prisoners of the Lost City** project for reusable translation decisions, terminology and reference tools.
* **RPCS3** for emulation and package installation.
* **Retro Trans Tools** for verified patches and catalog delivery.
* **Macross Triangle Frontier** for the [release format](https://github.com/retro-trans/Macross-Triangle-Frontier/releases).

### Source code

English translation decisions, glossaries and tools are in the [project repository](https://github.com/retro-trans/Wizardry-Perfect-Pack), under its [MIT license](https://github.com/retro-trans/Wizardry-Perfect-Pack/blob/main/LICENSE). GitHub's source archives contain the tagged repository snapshot; use the `.xdelta` assets to patch the game. Original game assets are excluded from the repository and its license.

### Contribute

Share bug reports, proofreading and playtest results at **[discord.gg/MssepShjmB](https://discord.gg/MssepShjmB)** or in the [issue tracker](https://github.com/retro-trans/Wizardry-Perfect-Pack/issues). Include the patch version, screen/scene and a screenshot where possible.

No complete game images are distributed. Apply the patch to your own disc image.
