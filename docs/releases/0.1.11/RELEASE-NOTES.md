English fan translation of **Wizardry: Prisoners of the Lost City** for PS3 (**NPJB00162 / PKG01**), supplied as an ISO patch for the Japanese **Wizardry Perfect Pack** disc (**BLJM61008**). The translated package is intended for RPCS3.

**Only Prisoners of the Lost City, the second game in Perfect Pack, is translated.** The first game, **Wizardry: Labyrinth of Lost Souls**, remains unchanged. Its official English PC version is available on [Steam](https://store.steampowered.com/app/948640/Wizardry_Labyrinth_of_Lost_Souls/).

### Apply

**Recommended:** Use the latest [Retro Trans](https://github.com/retro-trans/retro-trans-tools) app. Click **Refresh catalog**, open **Automatic**, select your original Japanese Perfect Pack ISO, choose **0.1.11** (or **Latest**), and select a new output filename. The app downloads the matching patch and verifies the resulting ISO.

**Manual patching:** [DeltaPatcher](https://github.com/marco-calautti/DeltaPatcher) and [xdelta3](https://github.com/jmacd/xdelta) accept the same asset:

| Your source image | Patch |
| --- | --- |
| Original Japanese Perfect Pack ISO (BLJM61008) | `Wizardry-Perfect-Pack-Prisoners-English-v0.1.11.xdelta` |

```text
xdelta3 -d -s "Wizardry - Perfect Pack (Japan).iso" "Wizardry-Perfect-Pack-Prisoners-English-v0.1.11.xdelta" "Wizardry-Perfect-Pack-Prisoners-English-0.1.11.iso"
```

Original Japanese ISO: 2,081,947,648 bytes; SHA-256 `25dc1f842f42dbd9e24ee1a23e23e51e339fc406bed997c8fbdb9815d41a42a7`.

Release output: 2,123,663,360 bytes; SHA-256 `1e92be73fa5456f04245705e880f64a9464e881e418fb4828b2fd334f2fa8877`.

`BUILD-MANIFEST.json` identifies the source, output and patch. `VALIDATION.json` records the successful patch round trip; `SHA256SUMS.txt` covers the downloads. Supply the unpacked original ISO, rather than an extracted `INSTALL.PKG`.

**RPCS3 installation:** RPCS3 does not boot this install ISO directly. Extract `/PS3_GAME/PKGDIR/PKG01/INSTALL.PKG` from the **patched ISO**, joining all file extents. With the repository's reader:

```text
python tools/disc_read.py "Wizardry-Perfect-Pack-Prisoners-English-0.1.11.iso" --path /PS3_GAME/PKGDIR/PKG01/INSTALL.PKG --extract work/local/iso-0.1.11
```

In RPCS3, choose **File → Install Packages/Raps/Edats**, install the extracted PKG01 package, then boot **Prisoners of the Lost City**. Back up saves and retain the original ISO. [Detailed installation instructions](https://github.com/retro-trans/Wizardry-Perfect-Pack#applying-the-patch).

### What's included

This is the first public ISO release. The earlier 0.1.10 package patch was withdrawn; use this ISO patch instead.

* **Menus and system text:** identified menus, help, system messages and trophy text.
* **Story text:** exported dialogue and narration, including the additional scenarios. Newly drafted event text received contextual review.
* **Game data:** identified item, monster, spell, skill, quest and dungeon-name text.
* **Opening subtitles:** bottom-aligned English subtitles, retaining the Japanese lettering, original artwork, logo and audio.
* **Graphics:** selected title and help graphics translated into English.
* **Text layout:** English wrapping and pagination for dialogue, anonymous narration and battle rewards, plus fitting changes for several narrow menus and descriptions. Long strings use relocated storage.
* **Title screen:** `v0.1.11` and `github.com/retro-trans` at the bottom right.

The extracted corpus has 11,387 decisions: 10,796 English drafts and 591 internal/parser exclusions. These counts do not establish complete game coverage. The patch replaces only PKG01 and the disc metadata required to store it; PKG00 and the other disc files are preserved. See the [changelog](https://github.com/retro-trans/Wizardry-Perfect-Pack/blob/main/CHANGELOG.md).

### Release status

**This is an early build. Further proofreading and full in-game playtesting are needed.** The ISO patch completes an encode/decode round trip. Independent ISO9660 and UDF extraction reproduce the exact package tested in RPCS3. Installation, all 1,483 installed-file hashes, 64 regressions and a 90-second startup probe pass. This does not establish correct appearance on every screen or a successful playthrough. [Verification reports](https://github.com/retro-trans/Wizardry-Perfect-Pack/tree/v0.1.11/docs/releases/0.1.11) separate file checks from installation and startup observations.

Known limitations:

* 448 translation entries remain marked for review. Some names, ambiguous lines and adapted riddles are provisional.
* Wrapping and fitting changes need broader in-game checks. The updated title footer and opening playback/listening have not received full visual acceptance for this release.
* Save/load, scenario progression, trophy behavior and a complete playthrough remain unverified.
* The opening intentionally keeps its original Japanese lettering alongside the English subtitles.
* The rebuilt package uses a decrypted executable for RPCS3. Physical-console and stock-firmware compatibility are unsupported. The startup probe retains nonfatal emulator diagnostics, documented in the verification reports.

**Restart the game after installing the patched package.** A running session continues using the executable and text already loaded in memory.

### How it was translated

This is a **machine translation**, drafted with large language models and reviewed and edited against scene context and a researched glossary. Exact-source text and terminology were reused from the neighboring *Wizardry Prisoners of the Lost City* project. Its existing uncertainty is retained; edition-specific executable paths and hooks were traced separately for Perfect Pack. New event drafts received independent contextual review, but complete human proofreading is still needed.

### Acknowledgements

* The neighboring **Wizardry Prisoners of the Lost City** project, for translation matches, glossary research and reference tools.
* **RPCS3**, for the emulator and the package-installation behavior used during verification.
* **Retro Trans Tools**, for patch generation, complete round-trip verification and automatic patch delivery.
* **Macross Triangle Frontier**, whose [release format](https://github.com/retro-trans/Macross-Triangle-Frontier/releases) this project follows.

### Source code

Translation decisions, glossaries and tools are available in the [project repository](https://github.com/retro-trans/Wizardry-Perfect-Pack) under the [MIT license](https://github.com/retro-trans/Wizardry-Perfect-Pack/blob/main/LICENSE). GitHub's source archives correspond to the release tag; download the `.xdelta` asset to patch the game. Original game assets are excluded and are not covered by the repository license.

### Contribute

Report bugs, help proofread or share playtest results at **[discord.gg/MssepShjmB](https://discord.gg/MssepShjmB)**, or open an issue in the [project repository](https://github.com/retro-trans/Wizardry-Perfect-Pack).

No complete game images are distributed. Use the patch with your own original disc image.
