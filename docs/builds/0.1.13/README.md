# Local test build 0.1.13

Source revision: `b40de0ba172f86f9a4351ac6d712abae4e69bffe`.
This build has not been published. It contains the context-label corrections
and retains the 0.1.12 portrait-dialogue fix.

| Output | Bytes | SHA-256 |
| --- | ---: | --- |
| NPJB00162 package | 1,114,929,072 | `d0cc801d65e81074cf53aaa210149fe36b96c7ca68bbd9adaa278238edb30187` |
| Perfect Pack ISO | 2,123,663,360 | `06bd962c96d607ec4b04a32c2e7343f2b6b3fe6e314f5a956a9f17093a9e6cbc` |

The overlay passes all 77 regressions, including eight context-specific tests,
all 17 native dialogue cases and 5,222 complete event paragraph groups. The
independent verifier checks 2,976 executable text references, all three
context exceptions and all 636 overlay files. Package verification checks
1,513 payloads. ISO9660, Joliet and all four UDF views agree; the other game's
package and all unselected disc files remain unchanged.

The project-local test executable matches this build. Save progress, close the
test session and start `work/output/Play-English-Test.cmd`; confirm v0.1.13.
For another RPCS3 profile, apply the matching local ISO patch, extract PKG01
and install its package normally. See [testing instructions](../../testing.md).

Retro Trans Tools verifies all three local patch round trips: original ISO,
English 0.1.11 and English 0.1.12 to 0.1.13. BUILD-MANIFEST.json identifies
each exact input/output and VALIDATION.json records the completed checks.
The local assets are under `work/output/release-0.1.13-local/`.

Updated visual fit, new package installation/boot and a complete playthrough
remain unverified. [Context evidence](CONTEXT-VALIDATION.json) records the
bounded 295-row audit and remaining ambiguous labels. Static checks cannot
establish every label's runtime reachability.
