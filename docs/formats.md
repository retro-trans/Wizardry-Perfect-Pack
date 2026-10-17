# Edition-specific format notes

## Disc and package

The install disc has an ISO9660 tree even though common UDF readers reject its metadata. PKG01 is a split-extent file: 1,073,739,776 bytes followed by 3,407,136 bytes, totaling 1,077,146,912. `disc_read.py` joins both extents with bounds checks. The selected retail package content ID is `JP0048-NPJB00162_00-WIZDL0000000BLUR`.

Only the Prisoners package is extracted. Encryption material is neither printed in reports nor saved as a license file. The protected station event is authenticated before decoding, and its English counterpart is an ordinary EVT file selected by the game's existing loader.

## Text and archives

Event files are opcode/length/payload records. The build changes selected text payloads, updates their lengths and retains opcodes, record ordering and all unselected bytes. Longer English may increase the event file length. It does not alter branches, accepted inputs or puzzle solution indexes.

ENC archives use LZO. All members round-trip before modification. Base and added tables have distinct layouts: added item records are 436 bytes, monster records 1,932 bytes and quest records 892 bytes. Perfect Pack bonus items use the added item layout. Collection/export code records field offsets and capacities rather than guessing from adjacent strings.

Database fields receive an 11-byte ASCII relocation token plus NUL. Full English strings live in an immutable appended executable segment. Three traced text-renderer entry points expand tokens into a private 12 KiB buffer in a 16 KiB stack frame. The native resolver checks token syntax, index bounds, output capacity and malformed/partial tokens. Stack, branch and link-register invariants have dedicated tests. Runtime behavior across every caller remains an acceptance requirement.

| Renderer entry | Text argument |
|---|---|
| `0x164adc`, string measurement | r4 |
| `0x164ea4`, positioned drawing | r6 |
| `0x1654a0`, queued drawing | r6 |

Positioned drawing receives x/y coordinates in r4/r5. Version 0.1.0 incorrectly treated r4 as text and crashed on New Game's first positioned labels. The 0.1.1 regression follows the original call at `0xd122c` and the callee's r6 → r23 → r30 → UTF-8 byte-read chain, rather than assuming all font functions share an argument layout.

Executable text is relocated through inspected data/TOC pointer ranges. The patch accepts only the known NPJB00162 ELF hash. It does not scan instructions or shader words for coincidental integer matches. Source addresses, hook prologues and insertion space are guarded. The neighboring NPJB00099 binary is incompatible.

Nine short executable labels have native compiler-sized copies that cannot safely accept early relocation to longer strings. Their original terminated bytes remain available through those copies; an immutable byte-content alias table expands them at the font measure/draw boundary. Prefix matching is limited to the two weapon-hand labels. See `docs/menu_layout.md` for the equipment-buffer trace and regression coverage.

Dungeon-scene EDATs use NPD v2/license 3/flags 0x0c. The decoder authenticates the title/developer hashes and every ciphertext block before parsing their four-member ENC payloads. Member 0 has a 53-byte name field and nine binary metadata bytes. Member 1 contains 18-byte floor records, member 2 contains four bytes and member 3 is the background TGA. The build changes only the name field.

The guarded pathname at ELF file offset `0x3fb798` changes from the protected dungeon pattern to `/obj/Scenes/dun%02d.enc`. Both callers at `0x132dd4` and `0x13331c` use that shared pointer. Size (`0xc22f0`), full-read (`0x1463c`) and partial-read (`0x1495c`) paths test for the protected extension; the ordinary extension selects normal `cellFsOpen` and the unchanged archive parser. All 14 plain counterparts are included, including the unchanged dummy scene. Original protected assets remain intact. Native instruction checks support this routing; actual updated dungeon entry remains a gameplay acceptance check.

Trophy XML replacement rebuilds the archive entry table and SHA-1 field. Console signature acceptance and trophy installation are not established by that checksum.

## Images and movie

English title, ending and help assets are regenerated from measured regions. Help-page compression preserves untouched BC3 blocks; package graphics preserve pixels outside their edit rectangles. Original source artwork stays local. The UI folder distinguishes generated previews from actual emulator captures.

The opening PAMF contains H.264 video and private ATRACX audio. Generic remuxing can discard audio or alter random-access metadata. Its translation tool therefore gates output on exact original stream/container structure, frame-slot sizes and separate decode checks. A successful general-purpose video decode alone does not establish game playback compatibility.
