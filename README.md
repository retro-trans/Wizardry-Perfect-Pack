# Wizardry Perfect Pack — Prisoners of the Lost City English patch

**This patch translates only Wizardry: Prisoners of the Lost City, the second game in Wizardry Perfect Pack.** The first game, **Wizardry: Labyrinth of Lost Souls**, is not translated by this patch. Its official English PC version is available on [Steam](https://store.steampowered.com/app/948640/Wizardry_Labyrinth_of_Lost_Souls/).

The patch targets **NPJB00162 / PKG01** from the Japanese **Wizardry Perfect Pack** install disc (**BLJM61008**), changing that package and the disc metadata needed to store it. **Labyrinth of Lost Souls, NPJB00163 / PKG00**, remains unchanged.

Version **0.1.11** is an early **RPCS3-only ISO patch**. Apply the xdelta to your own original Japanese ISO. After patching, extract PKG01 from the English ISO and install that package in RPCS3. Independent ISO9660 and UDF extraction checks reproduce the exact package tested in RPCS3: installation, all 1,483 installed-file hashes and a 90-second startup probe pass. A complete playthrough and the updated footer's appearance remain unverified; physical-console and stock-firmware compatibility are unsupported.

The previous **0.1.10 PKG patch was withdrawn and its release is now a private draft**. Use the 0.1.11 ISO patch described here.

This repository contains English translation decisions, glossaries, layout metadata and tools. Original game files, rebuilt packages/discs and Japanese working scripts are excluded.

## Applying the patch

Use [Retro Trans Tools](https://github.com/retro-trans/retro-trans-tools/releases/latest) for automatic patching:

1. In **Automatic**, click **Refresh catalog** and select your original `Wizardry - Perfect Pack (Japan).iso`.
2. Select **Wizardry Perfect Pack: Prisoners of the Lost City**, leave **Target** on **Latest**, and choose a new `.iso` output filename.
3. Apply the patch. Retro Trans Tools downloads the matching xdelta and verifies the complete resulting ISO.
4. [Extract PKG01 from the patched ISO](#extracting-the-english-install-package), then in RPCS3 choose **File → Install Packages/Raps/Edats** and install the extracted English package.
5. Boot the installed **Prisoners of the Lost City** entry normally. This workflow does not require manually launching an overlay ELF.

See the [release notes](docs/releases/0.1.11/RELEASE-NOTES.md) for verification status and limitations, and [Releases](https://github.com/retro-trans/Wizardry-Perfect-Pack/releases) for downloads. Back up existing saves before replacing an installation. Keep your untouched original ISO.

### Supported ISO

The patch accepts the complete original **BLJM61008** Japanese disc image:

| Identity | Bytes | SHA-256 |
|---|---:|---|
| Original `Wizardry - Perfect Pack (Japan).iso` | 2,081,947,648 | `25dc1f842f42dbd9e24ee1a23e23e51e339fc406bed997c8fbdb9815d41a42a7` |
| English 0.1.11 ISO | `2,123,663,360` | `1e92be73fa5456f04245705e880f64a9464e881e418fb4828b2fd334f2fa8877` |

Filenames may differ; the complete size and hash must match. Select the original ISO as the patch input.

### Manual xdelta patching

1. Download `Wizardry-Perfect-Pack-Prisoners-English-v0.1.11.xdelta` from [the release](https://github.com/retro-trans/Wizardry-Perfect-Pack/releases/tag/v0.1.11).
2. Use xdelta3, Delta Patcher, or Retro Trans Tools' **Apply xdelta** tab with the original ISO as the source and a new ISO as the output. For xdelta3:

   ```powershell
   xdelta3 -d -s "Wizardry - Perfect Pack (Japan).iso" "Wizardry-Perfect-Pack-Prisoners-English-v0.1.11.xdelta" "Wizardry-Perfect-Pack-Prisoners-English-0.1.11.iso"
   ```

3. Verify the resulting ISO against the target identity in the release notes or `BUILD-MANIFEST.json`, then extract and install PKG01 as below.

### Extracting the English install package

The English package is `/PS3_GAME/PKGDIR/PKG01/INSTALL.PKG` **inside the patched ISO**. The disc uses multiple extents for this file; all extents must be joined. Use the included reader or another extractor that produces the complete verified package. Do not extract PKG00.

With Python and this repository, inspect the patched ISO first, then extract into a fresh local destination:

```powershell
python tools/disc_read.py "Wizardry-Perfect-Pack-Prisoners-English-0.1.11.iso"
python tools/disc_read.py "Wizardry-Perfect-Pack-Prisoners-English-0.1.11.iso" --path /PS3_GAME/PKGDIR/PKG01/INSTALL.PKG --extract work/local/iso-0.1.11
```

Install `work/local/iso-0.1.11/PS3_GAME/PKGDIR/PKG01/INSTALL.PKG` through RPCS3's **File → Install Packages/Raps/Edats** menu, then boot its installed game entry. The extraction command refuses to overwrite an existing file. RPCS3 does not boot this install ISO directly. Independent 7-Zip ISO9660 and UDF extraction checks both complete without errors and produce the same 1,114,929,056-byte package, SHA-256 `a39cfd853316d2532cdc1821c3d21cc12e6b46456f70e3b2ff96edc74a11779f`.

## What is translated

- Exported event dialogue and narration, including the additional scenarios, with contextual review of newly drafted event text.
- Menus, system messages, items, skills, spells, quests, monster text, dungeon names and trophy text identified by the project's extraction tools.
- Selected title/help graphics and **English subtitles along the bottom of the opening movie**. The original Japanese lettering, artwork, logo and audio are retained.
- Runtime layout changes for full English dialogue, narration, battle rewards and several narrow UI panels. Long text is relocated rather than truncated to Japanese byte capacities.
- A small title-screen footer showing `v0.1.11` and `github.com/retro-trans`.

There are **11,387 exported rows with decisions**: **10,796 English drafts** and **591 documented internal/parser exclusions**. **448 entries retain review status**. These counts describe the extracted corpus; they do not establish complete game coverage or a successful playthrough. Image and movie captions are tracked separately.

## Known limitations

This is an early translation build. Some names, wordplay and ambiguous source lines remain provisional. Functional puzzle choices preserve their order and game logic, but adapted English riddles need playthrough testing. Exact-source imports retain inherited uncertainty. Broader checks of wrapping, save/load, scenario access and trophy behavior remain incomplete.

The subtitled opening preserves the original Japanese text on screen by design. Full software decoding and timing/audio/container comparisons pass; updated in-game playback and listening still require confirmation. The anonymous intro-narration fix has source-path and instruction-execution tests; updated in-game visual confirmation remains pending.

Report problems with the version, screen or scene, exact text and a screenshot when possible. See [translation status](docs/translation_status.md), [the text census](docs/text_census.md) and [the changelog](CHANGELOG.md) for the evidence and outstanding work.

## Repository layout

- `docs/` — format notes, translation status, layout findings and versioned release notes.
- `tools/` — extraction, validation, relocation, graphics, movie, package and build tools.
- `work/glossary/` — researched names and terminology.
- `work/translation/en/` — English-only `.en.json` decisions and provenance.
- `work/ui/` — screen geometry and layout metadata; actual captures remain local.
- `work/source/`, `work/output/` — ignored original files, decoded working data, test builds and verification reports.

## Build it

Use 64-bit Python and the dependencies in `tools/requirements.txt`. Original files remain local under ignored `work/source/`. The [format notes](docs/formats.md), [local testing guide](docs/testing.md), and tool help describe extraction and the overlay build. Inspection tools default to dry runs unless their help states otherwise; inspect the plan before using extraction or write modes.

Build and independently verify a fresh versioned overlay, then use `tools/pkg_overlay.py` to rebuild PKG01 for RPCS3. It maps the translated ELF to `USRDIR/EBOOT.BIN`, preserves unselected package payloads, and independently checks native package-name alignment and file contents. Package reconstruction does not create valid retail-console authentication. Keep package installation/boot testing separate from static validation and xdelta round-trip checks.

For the ISO release, run `tools/iso_overlay.py` to place the rebuilt package into a fresh disc copy. It updates ISO9660, Joliet, UDF and required disc metadata, verifies all views and checks every unselected file plus unchanged physical regions. Independently extract the package and match it to the exact package tested in RPCS3. See [the release guide](docs/RETRO_TRANS_RELEASES.md) for ISO packaging and Retro Trans Tools release checks.

Before committing, run `tools/strip_jp.py --write` and commit only the English `.en.json` translation copies. See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution rules.

## Credits and license

The neighboring *Wizardry Prisoners of the Lost City* translation project supplied exact-source matches, researched terminology and reference tooling. Its edition-specific executable patches were not reused; Perfect Pack's binary paths and hooks were traced separately.

The translation uses LLM-assisted drafts, glossary research and contextual review. It is not an official localization and has not received complete human proofreading. Repository and release organization follow [Macross Triangle Frontier](https://github.com/retro-trans/Macross-Triangle-Frontier). Join the [Retro Trans Discord](https://discord.gg/MssepShjmB) to contribute or share test results.

Translation text and project tools are available under the [MIT license](LICENSE). Wizardry and its original game assets belong to their respective rights holders. This license does not cover the game, its bundled font, artwork, audio or other original assets. Supply your own original game files.
