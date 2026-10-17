# Wizardry Perfect Pack — Prisoners of the Lost City English patch

English fan translation of **Wizardry: Prisoners of the Lost City**, **NPJB00162**, from the Japanese **Wizardry Perfect Pack** install disc (**BLJM61008**). Only **PKG01** is patched. The separately installed **Labyrinth of Lost Souls**, **NPJB00163 / PKG00**, is outside this project's scope.

Version **0.1.10** is an early **RPCS3-only** package patch. Apply the xdelta to your own original `INSTALL.PKG`, then install the resulting PKG normally in RPCS3. The package passes isolated installation, all 1,483 installed-file hash checks, and a 90-second headless startup test. The updated title footer still needs visual confirmation, and a complete playthrough has not been verified. Stock PS3 firmware and physical-console compatibility are unsupported.

This repository contains English translation decisions, glossaries, layout metadata and tools. Original game files, rebuilt packages and Japanese working scripts are excluded.

## Applying the patch

Use [Retro Trans Tools](https://github.com/retro-trans/retro-trans-tools/releases/latest) for automatic patching:

1. Extract **PKG01's `INSTALL.PKG`** from your own Perfect Pack disc image, as described below. Do not select PKG00 or the ISO itself.
2. In Retro Trans Tools, open **Automatic**, click **Refresh catalog**, and select that original PKG.
3. Select **Wizardry Perfect Pack: Prisoners of the Lost City**, leave **Target** on **Latest**, and choose a new `.pkg` output filename. Retro Trans Tools downloads the matching patch and verifies the complete output.
4. In RPCS3, choose **File → Install Packages/Raps/Edats** and install the new English PKG. Boot the installed **Prisoners of the Lost City** entry normally. This release does not require manually launching an overlay ELF.

See the [release notes](docs/releases/0.1.10/RELEASE-NOTES.md) for hashes, verification status and limitations, and [Releases](https://github.com/retro-trans/Wizardry-Perfect-Pack/releases) for downloads. Back up existing saves before replacing an installation. Keep the original package so you can reinstall it if needed.

### Getting the correct original package

The required file is `/PS3_GAME/PKGDIR/PKG01/INSTALL.PKG` inside the Japanese Perfect Pack disc image:

| File | Bytes | SHA-256 |
|---|---:|---|
| Original PKG01 `INSTALL.PKG` | 1,077,146,912 | `beeaa26163cb39314ef0d82748af7afd865e0acd3ca006b1226755cb1b1e72b8` |

This disc stores PKG01 in two ISO9660 extents. The included reader joins both with bounds checks and handles the disc's unusual directory metadata. With Python and this repository, inspect first, then extract into a fresh local destination:

```powershell
python tools/disc_read.py "Wizardry - Perfect Pack (Japan).iso"
python tools/disc_read.py "Wizardry - Perfect Pack (Japan).iso" --path /PS3_GAME/PKGDIR/PKG01/INSTALL.PKG --extract work/source/disc
```

The output is `work/source/disc/PS3_GAME/PKGDIR/PKG01/INSTALL.PKG`. Verify its size and SHA-256 before patching. The extraction command refuses to overwrite an existing file. Other extraction tools are suitable if they produce exactly the required bytes.

### Manual xdelta patching

1. Download `Wizardry-Perfect-Pack-Prisoners-English-v0.1.10.xdelta` from [the release](https://github.com/retro-trans/Wizardry-Perfect-Pack/releases/tag/v0.1.10).
2. Use xdelta3, Delta Patcher, or Retro Trans Tools' **Apply xdelta** tab with the original PKG as the source and a new PKG as the output. For xdelta3:

   ```powershell
   xdelta3 -d -s "INSTALL.PKG" "Wizardry-Perfect-Pack-Prisoners-English-v0.1.10.xdelta" "Wizardry-Prisoners-English-0.1.10.pkg"
   ```

3. Verify the resulting package against the target identity in the release notes or `BUILD-MANIFEST.json`, then install it in RPCS3 as above. The output must be **1,114,929,056 bytes**, SHA-256 `7cb285c8abae4f80df288c34dc7118c55b77f4bc9f3b5f83be0e76571bdd8659`.

## What is translated

- Exported event dialogue and narration, including the additional scenarios, with contextual review of newly drafted event text.
- Menus, system messages, items, skills, spells, quests, monster text, dungeon names and trophy text identified by the project's extraction tools.
- Selected title/help graphics and **English subtitles along the bottom of the opening movie**. The original Japanese lettering, artwork, logo and audio are retained.
- Runtime layout changes for full English dialogue, narration, battle rewards and several narrow UI panels. Long text is relocated rather than truncated to Japanese byte capacities.
- A small title-screen footer showing `v0.1.10` and `github.com/retro-trans`.

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

Before committing, run `tools/strip_jp.py --write` and commit only the English `.en.json` translation copies. See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution rules.

## Credits and license

The neighboring *Wizardry Prisoners of the Lost City* translation project supplied exact-source matches, researched terminology and reference tooling. Its edition-specific executable patches were not reused; Perfect Pack's binary paths and hooks were traced separately.

The translation uses LLM-assisted drafts, glossary research and contextual review. It is not an official localization and has not received complete human proofreading. Repository and release organization follow [Macross Triangle Frontier](https://github.com/retro-trans/Macross-Triangle-Frontier). Join the [Retro Trans Discord](https://discord.gg/MssepShjmB) to contribute or share test results.

Translation text and project tools are available under the [MIT license](LICENSE). Wizardry and its original game assets belong to their respective rights holders. This license does not cover the game, its bundled font, artwork, audio or other original assets. Supply your own original game files.
