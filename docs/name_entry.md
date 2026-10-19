# Character name entry — local 0.1.14

The reported six-character stop comes from the game's PS3 keyboard request,
not a controller or RPCS3 preference. The game also has a separate eight-character
setter. Local 0.1.14 raises entry to **12 characters** and replaces the setter
with a bounded copy. ASCII names can use all twelve; multibyte names must also
fit the existing 32-byte UTF-8 payload plus its terminator.

The existing character and save layout is unchanged. The getter at VA0x4c7c8
returns record+0x1bd; the native setter at VA0x50bc0 clears 0x21 bytes there.
Registration already copies the entire 33-byte field. The replacement clears
that same field, accepts at most twelve complete UTF-8 characters and 32 bytes,
and preserves the following record fields. Empty and null input retain the
native clearing behavior. Existing names remain readable.

## Keyboard storage

`cellOskDialogLoadAsync` receives the input-field structure at state+0xc;
its limit field at state+0x14 is initialized by `li r0,6` at VA0x10c698.
The load call is VA0x10c814. Return data is processed after the unload call at
VA0x10c50c. The previous temporary UTF-16 arrays were sized around short names;
raising only the limit would overwrite neighboring state.

The original state pointer at VA0x48366c is redirected to a dedicated,
zero-initialized 144-byte writable load segment. Header/control fields keep
their native offsets. Initial text moves to +0x54 and returned text to +0x70,
each with room for twelve UTF-16 units and a terminator. The result length is
13, and conversion to the UTF-8 stack buffer is bounded to 33 bytes before
calling the setter. The original character record is never enlarged.

RPCS3's [ELF loader](https://github.com/RPCS3/rpcs3/blob/master/rpcs3/Emu/Cell/PPUModule.cpp)
allocates LOAD segments according to memory size, including zero-file-size
segments. The independent verifier checks that the new state does not overlap
another segment and that existing writable, TLS and process segments are intact.

The layout and callback interpretation were checked against RPCS3's
[keyboard structures](https://github.com/RPCS3/rpcs3/blob/master/rpcs3/Emu/Cell/Modules/cellOskDialog.h)
and [load/unload implementation](https://github.com/RPCS3/rpcs3/blob/master/rpcs3/Emu/Cell/Modules/cellOskDialog.cpp).
Every changed instruction and the original state pointer are guarded against
the original Perfect Pack executable. Other editions require tracing again.

Build the new helper with `python tools/compile_name_entry.py --write` before
running `tools/build.py --runtime-tables`. The helper has no external data or
calls. Its entry bridge clears the upper halves of both pointer arguments to
match the native PS3 ABI, and it uses byte stores for the unaligned name field.

## Testing

Save progress, close the project test session and run
`work/output/Play-English-Test.cmd`. Confirm **v0.1.14** on the title screen.
Create a character named `Vedette` (seven characters), then test a twelve-letter
name such as `ABCDEFGHIJKL`. The thirteenth character should be refused. Check
the completed registration, roster and status screens, save, restart the game
and confirm that the complete name returns. Existing saves and controller
settings are retained by the local staging workflow.

Boundary tests exercise ASCII, empty/null input, multibyte text, invalid
encodings and 200 reproducible mixed names, with canaries around the native
name field. Static checks inspect the PowerPC object, keyword limit, temporary
buffer separation, writable segment and setter branch. These checks do not
replace an in-game registration/save/load test. Appearance of unusually wide
twelve-letter names on every panel remains unverified.
