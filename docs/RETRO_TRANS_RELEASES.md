# Retro Trans release guide

This repository follows the documentation and release layout of
[Macross Triangle Frontier](https://github.com/retro-trans/Macross-Triangle-Frontier).
Its game-specific source and translations are not copied into this project.

The stable game identity is `wizardry-perfect-pack`, edition
`perfect-pack-npjb00162`, language `en`, platform `PS3`. The release patches the
original Perfect Pack PKG01 `INSTALL.PKG` to an RPCS3 package. It does not patch
the whole install disc or the separate NPJB00163 / PKG00 game.

## Build and verify

1. Use your own original disc and extract only PKG01 with `tools/disc_read.py`.
   Extract/export local source data as described in the format documentation.
2. Translate and validate the English decisions, compile the resolver and
   dialogue presenters, generate English graphics and prepare the verified
   subtitled opening. Run `tools/strip_jp.py --write` before committing.
3. Build a fresh `work/output/0.x.y` overlay with runtime tables, graphics and
   the verified movie. `build.py` embeds that exact version in the title footer.
   Independently verify the overlay and the relevant runtime/layout tests.
4. Dry-run `tools/pkg_overlay.py ORIGINAL.PKG work/output/0.x.y OUTPUT.PKG`.
   Review the plan, then repeat with `--write` and a fresh output path. It maps
   the translated ELF to normal `USRDIR/EBOOT.BIN`, retains unchanged encrypted
   payloads and checks all file hashes. The rebuilt authentication is not valid
   for stock PS3 firmware; this release targets RPCS3 only.
5. Install the package into an isolated RPCS3 data directory and verify the
   installed files, installation log and boot. Do not use a player's active
   profile for release probes. Verify title/footer and gameplay separately
   from the package and patch checks; report limitations honestly.
6. Commit the translation/tool revision. Prepare a private JSON configuration
   from Retro Trans Tools' `examples/release-config.json`, with the real full
   commit SHA, exact original PKG and verified output PKG. Keep local paths
   and the complete input/output packages under ignored working storage.

The patch row uses `source_version: original`, `source_format: pkg` and
`target_format: pkg`. Use a numeric version and a matching `v0.x.y` tag. A single
full patch is enough for the first release; add upgrade routes only for exact
previously published target bytes.

Run the current [Retro Trans Tools](https://github.com/retro-trans/retro-trans-tools)
builder and validator:

```text
python -m retro_trans.release build release-local.json --out release-0.x.y
python -m retro_trans.release validate release-0.x.y
```

The builder hashes its inputs, creates xdelta, decodes the patch again, compares
the complete target, and rechecks that the inputs did not change. Retain that
round-trip evidence. Do not hand-author a successful `VALIDATION.json`.

## Publish

Publish the bare `.xdelta`, exactly one `BUILD-MANIFEST.json`, the builder's
`VALIDATION.json`, and `SHA256SUMS.txt`. Never publish complete game packages or
disc images. Copy the small manifests/checksums and scoped installation evidence
to `docs/releases/<version>/`. Tag the source repository and publish release
notes describing the exact input, output, install steps, coverage and limits.

Retro Trans's catalog discovers stable releases in the organization and verifies
these assets. The automatic catalog may update after publication; Manual Apply
xdelta works with the same patch while discovery catches up. PKG support here
means exact-file patching; installation is performed by RPCS3 afterward.

Do not overwrite a published patch, tag or output identity. A corrected build
must receive a new version and updated title footer.
