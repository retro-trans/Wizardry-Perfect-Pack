# Wizardry Perfect Pack — English patch 0.1.10

**Target:** Perfect Pack **PKG01 / NPJB00162 — Prisoners of the Lost City**. **Platform:** RPCS3. This is a package-to-package xdelta patch, not a patch for the install ISO. **NPJB00163 / PKG00 — Labyrinth of Lost Souls** is outside scope.

## Status

This is an early English release for RPCS3. The rebuilt package installs successfully in an isolated profile; all 1,483 installed files match their expected hashes. A 90-second headless startup test reaches the game's main thread with no fatal crash. This does not establish that the title footer looks correct or that gameplay completes. Full-playthrough verification is incomplete. No physical-console or stock-firmware compatibility is claimed.

## Changes

- Prepare the English translation as a normally installable RPCS3 package, with the translated executable at `USRDIR/EBOOT.BIN`.
- Preserve the 636 selected overlay files and 847 unselected file payloads, checking their identities independently. Preserve 891,594,388 bytes of untouched source ciphertext. The corrected package validates native 16-byte-aligned name offsets and name lengths without NUL terminators.
- Add `v0.1.10` and `github.com/retro-trans` in a small gray title-screen footer with a black shadow.
- Retain the anonymous intro-narration wrapping fix, three-line pagination, item/inventory layout, skill and spell description reflow, quest/settings spacing and battle-reward fixes.
- Retain bottom-aligned English opening subtitles with the original Japanese lettering, imagery, logo and audio. No black narration cards or masks are used.

## Supported input and output

Extract `/PS3_GAME/PKGDIR/PKG01/INSTALL.PKG` from your own Japanese **BLJM61008** disc. The included `tools/disc_read.py` joins its two ISO9660 extents. Instructions are in [the README](../../../README.md#getting-the-correct-original-package).

| Identity | Bytes | SHA-256 |
|---|---:|---|
| Original PKG01 `INSTALL.PKG` | 1,077,146,912 | `beeaa26163cb39314ef0d82748af7afd865e0acd3ca006b1226755cb1b1e72b8` |
| English 0.1.10 PKG | 1,114,929,056 | `7cb285c8abae4f80df288c34dc7118c55b77f4bc9f3b5f83be0e76571bdd8659` |

Source and target filenames may differ; their complete size and hash must match.

## Applying and installing

Use [Retro Trans Tools](https://github.com/retro-trans/retro-trans-tools/releases/latest): **Automatic → Refresh catalog**, select the original PKG, select this English patch and save a new `.pkg`. Alternatively, download `Wizardry-Perfect-Pack-Prisoners-English-v0.1.10.xdelta` and apply it with xdelta3 or the manual **Apply xdelta** tab. [Full instructions](../../../README.md#applying-the-patch).

In RPCS3 choose **File → Install Packages/Raps/Edats**, install the English PKG, and boot the installed Prisoners of the Lost City entry. Keep existing saves backed up and retain the untouched original package. A clean restart loads the updated executable; this release does not require starting a loose overlay ELF.

## Verification and remaining work

The package reconstruction checks all selected and unselected file payloads, native name alignment, entry bounds, unique paths and unchanged ciphertext regions. The event/database overlay has separate hash and non-text preservation checks. All 57 regression tests pass. Native-host and emitted-instruction tests cover the layout changes and final message-wait ownership.

The limited startup probe records loader/analyzer and headless-environment warnings, including branch-analysis diagnostics for added runtime code. It does not establish a clean title display or trophy behavior. The installer also reports non-file payload space in its progress accounting and a headless teardown error after success; all installed file sizes and hashes were independently verified. See [RPCS3 validation](RPCS3-VALIDATION.json) for the exact scope and diagnostics.

The opening passes independent software decoding of all 2,210 pictures, with matching packet and frame timing, picture types, geometry and pixel format. Original audio packets, container headers and access maps are preserved. In-game playback and audible-audio confirmation remain pending.

Retro Trans Tools' `BUILD-MANIFEST.json`, `VALIDATION.json` and `SHA256SUMS.txt` provide the release identities and patch round-trip evidence. The builder encodes and decodes the patch and checks the complete target package. That binary check is separate from installation, boot and gameplay testing.

There are **448 review-status translation entries**. Some names, source ambiguities and adapted riddles remain provisional; broad UI testing, save/load, scenario progression, trophy behavior and a complete playthrough remain unfinished. Original Japanese lettering remains in the opening by design beneath or alongside the added English subtitles. See [translation status](../../translation_status.md) for detail.

## How this was translated

LLM-assisted drafts were checked against scene context and the researched glossary. Exact-source translations and terminology were reused from the neighboring Wizardry project; edition-specific binary hooks were traced again. Some lines retain review flags, and complete human proofreading is outstanding.

## Acknowledgements and source

The repository and release layout follow [Macross Triangle Frontier](https://github.com/retro-trans/Macross-Triangle-Frontier), with patch generation and validation by [Retro Trans Tools](https://github.com/retro-trans/retro-trans-tools).

Translation text and project tools are available in the [source repository](https://github.com/retro-trans/Wizardry-Perfect-Pack) under the [MIT license](https://github.com/retro-trans/Wizardry-Perfect-Pack/blob/main/LICENSE). Original game assets are not included in the source repository and are not covered by that license. Supply your own game files.

Report issues in the repository or join the [Retro Trans Discord](https://discord.gg/MssepShjmB) to contribute.
