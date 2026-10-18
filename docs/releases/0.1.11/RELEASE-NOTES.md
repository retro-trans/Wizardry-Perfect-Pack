# Wizardry Perfect Pack — English ISO patch 0.1.11

**This patch translates only Wizardry: Prisoners of the Lost City, the second game in Wizardry Perfect Pack.** The first game, **Wizardry: Labyrinth of Lost Souls**, is not translated by this patch. Its official English PC version is available on [Steam](https://store.steampowered.com/app/948640/Wizardry_Labyrinth_of_Lost_Souls/).

**Input/output:** Japanese Perfect Pack **BLJM61008 ISO → English ISO**.
**Translated game:** **PKG01 / NPJB00162 — Prisoners of the Lost City**.
**Runtime target:** RPCS3. **PKG00 / NPJB00163 — Labyrinth of Lost Souls** is
preserved.

## Status

This is an early English ISO release for RPCS3. Independent ISO9660 and UDF
extraction reproduce the exact 0.1.11 package tested in a fresh emulator
profile. Installation succeeds, all 1,483 installed files match their hashes,
and a 90-second headless probe executes the game's main thread and opens
translated assets without a fatal error. Title/footer appearance and complete
playthrough coverage remain unverified. Physical-console and stock-firmware
compatibility are unsupported.

The previous 0.1.10 PKG patch was withdrawn and its release is now a private
draft. Version 0.1.11 uses the original ISO as patch input.

## Changes

- Distribute an ISO-to-ISO xdelta; users do not need an extracted original PKG
  to apply the patch.
- Replace only PKG01 with the English package and update the disc metadata
  needed to store it. Preserve PKG00 and all other unselected disc file payloads.
  ISO9660, Joliet and main/reserve UDF with main/mirror metadata agree.
- Update the title footer to `v0.1.11` above `github.com/retro-trans`.
  Translation content is otherwise unchanged from 0.1.10.
- Retain anonymous narration wrapping, three-line pagination, UI fitting,
  skill/spell description reflow and battle reward handling.
- Retain bottom English opening subtitles. Original Japanese lettering,
  artwork, logo and audio remain; no black cards or masks are used.

## Supported input and output

| Identity | Bytes | SHA-256 |
|---|---:|---|
| Original `Wizardry - Perfect Pack (Japan).iso` | 2,081,947,648 | `25dc1f842f42dbd9e24ee1a23e23e51e339fc406bed997c8fbdb9815d41a42a7` |
| English 0.1.11 ISO | `2,123,663,360` | `1e92be73fa5456f04245705e880f64a9464e881e418fb4828b2fd334f2fa8877` |

The release patch is
`Wizardry-Perfect-Pack-Prisoners-English-v0.1.11.xdelta`.
Filenames can differ; complete binary sizes and hashes must match.
An original or translated `INSTALL.PKG` is not a supported input for this
ISO patch.

## Apply the patch, then install

Use [Retro Trans Tools](https://github.com/retro-trans/retro-trans-tools/releases/latest):
**Automatic → Refresh catalog**, select your original ISO, select this English
patch and save a new ISO. Manual **Apply xdelta** or xdelta3 uses the same
original ISO and patch. See [the README](../../../README.md#applying-the-patch).

RPCS3 does not boot this install ISO directly. Extract
`/PS3_GAME/PKGDIR/PKG01/INSTALL.PKG` from the **patched** ISO, joining all its
extents. With the repository's reader:

```powershell
python tools/disc_read.py "Wizardry-Perfect-Pack-Prisoners-English-0.1.11.iso"
python tools/disc_read.py "Wizardry-Perfect-Pack-Prisoners-English-0.1.11.iso" --path /PS3_GAME/PKGDIR/PKG01/INSTALL.PKG --extract work/local/iso-0.1.11
```

In RPCS3 choose **File → Install Packages/Raps/Edats** and install
`work/local/iso-0.1.11/PS3_GAME/PKGDIR/PKG01/INSTALL.PKG`. Boot the installed
Prisoners of the Lost City entry normally. Keep saves backed up and retain the
untouched original ISO. This workflow does not require a loose overlay ELF.

## Verification scope and remaining work

The ISO's six filesystem reading paths agree, all affected UDF descriptor
checksums pass, and all 11 unselected disc files match the original. PKG00 and
the update PUP are unchanged. Physical byte comparisons preserve 1,008,189,440
original bytes outside the selected payload and explicit metadata sectors.

Independent 7-Zip 26.02 ISO9660 and UDF extraction both exit successfully,
producing the 1,114,929,056-byte package with SHA-256
`a39cfd853316d2532cdc1821c3d21cc12e6b46456f70e3b2ff96edc74a11779f`.
That exact package passes the new isolated installation and startup checks.
The startup probe retains nonfatal loader/analyzer and headless-environment
warnings. The installer logs success and all payloads verify despite a
headless teardown error afterward. Visual/gameplay checks have a separate
scope; see the accompanying validation reports.

Retro Trans Tools builds the ISO-to-ISO xdelta, decodes it again, verifies the
whole target ISO and rechecks the inputs. Its release manifests and checksums
record the complete identities and round-trip evidence.

All 64 regression tests pass. [ISO validation](ISO-VALIDATION.json),
[independent extraction](EXTRACTION-VALIDATION.json) and
[RPCS3 validation](RPCS3-VALIDATION.json) record their respective scopes.

The carried-over translation/layout code has native-host and emitted-instruction
tests. The opening has independent software decoding of all 2,210 pictures,
matching packet/frame timing, picture types, geometry and pixel format, with
original audio/container bytes preserved. Updated in-game playback and listening
remain to be confirmed.

There are **448 review-status translation entries**. Some names, source
ambiguities and adapted riddles remain provisional. Broad UI testing,
save/load, scenario progression, trophy behavior and a complete playthrough
remain incomplete. Original Japanese opening lettering remains by design
alongside the English subtitles. See [translation status](../../translation_status.md).

## Source and credits

LLM-assisted drafts were checked against scene context and the researched
glossary. Exact-source terminology/text came from the neighboring Wizardry
project; edition-specific binary hooks were traced separately. Complete human
proofreading is outstanding.

Repository/release organization follows
[Macross Triangle Frontier](https://github.com/retro-trans/Macross-Triangle-Frontier);
patch generation and verification use
[Retro Trans Tools](https://github.com/retro-trans/retro-trans-tools).

Translation text and project tools use the [MIT license](../../../LICENSE).
Original game assets are excluded from the source repository and are not
covered by that license. Supply your own game files. Report issues in the
[source repository](https://github.com/retro-trans/Wizardry-Perfect-Pack)
or join [Retro Trans Discord](https://discord.gg/MssepShjmB).
