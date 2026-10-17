# Retro Trans release guide

This repository follows the documentation and release layout of
[Macross Triangle Frontier](https://github.com/retro-trans/Macross-Triangle-Frontier).
Its game-specific translation is separate.

Version **0.1.11** distributes an **ISO → ISO** xdelta for the Japanese Perfect
Pack disc. The patch replaces PKG01 with the English NPJB00162 package and
updates only the disc metadata needed to store it. PKG00 / NPJB00163 is
preserved. RPCS3 users patch their ISO first, extract PKG01 from that output,
then install the package normally; no original PKG is required as patch input.

The stable game identity remains `wizardry-perfect-pack`, language `en`,
platform `PS3`. Use the separate ISO edition `perfect-pack-bljm61008-iso`.
The withdrawn 0.1.10 PKG edition `perfect-pack-npjb00162` has a different
original binary identity and must not be reused for the ISO's original hash.

## Build and verify

1. Verify the original ISO: **2,081,947,648 bytes**, SHA-256
   `25dc1f842f42dbd9e24ee1a23e23e51e339fc406bed997c8fbdb9815d41a42a7`.
   Keep it read-only throughout package and disc construction.
2. Extract PKG01 locally with `tools/disc_read.py`; its reader must join every
   ISO9660 extent. Prepare local source data as described in the format notes.
3. Validate the English decisions, compile the resolver/presenters and prepare
   graphics plus the verified subtitled opening. Run
   `tools/strip_jp.py --write` before committing. Build and independently verify
   a fresh `work/output/0.1.11` overlay; its footer must show `v0.1.11`.
4. Rebuild PKG01 with `tools/pkg_overlay.py`, mapping the translated ELF to
   `USRDIR/EBOOT.BIN`. Check all selected/unselected package payloads and native
   name alignment. This package is intended for RPCS3, not retail-console
   authentication.
5. Build a fresh ISO containing that exact package. Update package extents,
   directory sizes and other required disc metadata consistently in both
   ISO9660 and UDF views. Independently extract PKG01 through both views and
   compare its entire size/hash with the package input. Verify PKG00 and all
   other unselected disc file payloads remain identical.
6. Independently extract the package from the **new ISO** and verify it is
   byte-identical to the package tested in an isolated RPCS3 data root.
   Verify installed hashes, installation logs and startup.
   Check the title/footer and gameplay separately. The earlier 0.1.10 package
   install/startup evidence is historical and does not validate this ISO build.
7. Commit the translation/tool revision and prepare an ignored private release
   config containing the real full commit SHA and exact source/target ISOs.
   Input/output disc images, packages and local paths are not release assets.

The verified ISO target is **2,123,663,360 bytes**, SHA-256
`1e92be73fa5456f04245705e880f64a9464e881e418fb4828b2fd334f2fa8877`.

## Retro Trans Tools configuration

The v1 patch row must use `source_version: original`,
`source_format: iso` and `target_format: iso`. For an ignored config at
`work/release/release-local.json`, use the following shape, replacing the
all-zero commit and target path with the actual committed revision/output:

```json
{
  "game_id": "wizardry-perfect-pack",
  "game_name": "Wizardry Perfect Pack: Prisoners of the Lost City",
  "platform": "PS3",
  "version": "0.1.11",
  "source_commit": "0000000000000000000000000000000000000000",
  "patches": [{
    "patch": "Wizardry-Perfect-Pack-Prisoners-English-v0.1.11.xdelta",
    "edition": "perfect-pack-bljm61008-iso",
    "language": "en",
    "source_version": "original",
    "source_format": "iso",
    "target_format": "iso",
    "source": "../../Wizardry - Perfect Pack (Japan).iso",
    "target": "../output/iso/Wizardry-Perfect-Pack-Prisoners-English-0.1.11.iso"
  }]
}
```

Paths resolve relative to the config file. No upgrade from a withdrawn PKG
output is implied. Add upgrade routes only for exact supported ISO identities.

Run the current [Retro Trans Tools](https://github.com/retro-trans/retro-trans-tools)
builder and validator:

```text
python -m retro_trans.release build release-local.json --out release-0.1.11
python -m retro_trans.release validate release-0.1.11
```

The builder hashes its inputs, creates xdelta, decodes it to a complete
temporary ISO, verifies the whole target and rehashes its inputs. Retain that
round-trip evidence. Do not hand-author a successful `VALIDATION.json`.
Retain the exact ISO/extracted-package identities with the installation and
limited startup reports; visual/gameplay checks have a separate scope.

## Publish

Publish the bare `Wizardry-Perfect-Pack-Prisoners-English-v0.1.11.xdelta`,
exactly one `BUILD-MANIFEST.json`, the builder's `VALIDATION.json`, and
`SHA256SUMS.txt`. Never publish complete game packages or disc images.
Copy the small manifests/checksums and scoped verification evidence to
`docs/releases/0.1.11/`. Tag the real source revision and publish notes with
the exact ISO identities, package-extraction steps, RPCS3 installation and
remaining limitations.

Register the published release in Retro Trans's catalog before declaring
Automatic detection ready. The application's Refresh catalog downloads the
prebuilt catalog; it does not scan new GitHub releases itself. A failed
scheduled catalog job leaves a valid new release undiscoverable.

During the user-authorized release publication, run the existing targeted
catalog workflow and wait for successful validation/publication:

```text
gh workflow run catalog.yml --repo retro-trans/retro-trans-tools --ref main -f repository=retro-trans/Wizardry-Perfect-Pack
```

Verify through the application's actual public catalog URL and recognition
code that the original ISO matches and has an `original → 0.1.11` route.
Preserve all prior catalog identities. This metadata registration does not
require a new application release. Record the workflow and recognition result
with the release evidence. Manual Apply xdelta uses the same ISO patch while
catalog discovery catches up.
Users must select the original ISO, then extract PKG01 from the resulting
English ISO; RPCS3 does not boot this install ISO directly.

The 0.1.10 PKG release was withdrawn and is now a private draft. Keep its
versioned notes as history; do not advertise it as a current route or silently
replace its patch bytes with ISO patch bytes. Published output identities are
immutable; corrected builds receive a new version and title footer.
