# Shared text and short labels

Local build 0.1.13 fixes the reported `Weapons: Kns` label to `Weapons: Swords`.
The source term was shared by sword categories and the compact Kensei class
label. Matching Japanese text alone had assigned the class abbreviation to
weapon descriptions. Thirteen weapon references now use Swords; only the
compact Kensei class reference retains Kns.

The follow-up audit also found Mage sharing a source string with the Magic
monster category, and Felpurr sharing one with the Beast monster category.
The compact class reference now uses Mag and the race reference uses Felpurr.
The monster categories remain Magic and Beast. Native race lookup returns a
string pointer; no three-letter copy restriction was found. Updated visual
fit and reachability of the compact race label still need in-game testing.

## Audit scope and limits

The static audit reviewed 202 English labels of one to five trimmed characters
(290 source locations), including 56 rows with multiple locations. It expanded
to 158 source labels of one to three characters with multiple aligned raw
pointer values (321 locations and 633 candidate pointer sites). Their union
contains 295 rows. Detailed native tracing targeted class, race, monster-family,
alignment and element tables. No further proven meaning collision was found in
this bounded review. Candidate raw pointers are not proof of active callers;
this is not complete-game visual acceptance.

Two uncertainties remain explicit. X0112 Evil serves alignment and a compact
monster-family label. The compact and full family tables have different
taxonomies, so matching their indices cannot establish a replacement. X0217
Light is correct for an element, but another occurrence is in a speaker-name
table with Harun, Rin and NPC portraits. Its reading and active reachability
are unproved; that row is now flagged for review instead of inventing a name.

## Context-specific decisions

Addresses below apply only to the original Perfect Pack NPJB00162 ELF,
SHA-256 `2e23b466028ac0a18f7f46522fe1847d5c918a129605a2bdc1c56ca31da82bba`.
Pointer offsets are file offsets; source addresses are virtual addresses.

| Row | Default meaning | Exception pointer | Expected source | Exception |
| --- | --- | --- | --- | --- |
| X0179 | Sword weapons: Swords | 0x440e1c | 0x3ec808 | Compact Kensei: Kns |
| X0110 | Monster category: Magic | 0x440e00 | 0x3ec430 | Compact Mage: Mag |
| X0103 | Monster category: Beast | 0x440f00 | 0x3ec3f8 | Race: Felpurr |

Fighter and Lord preferred weapons use pointers 0x446d50 and 0x446db0.
The sword category uses 0x441194; ten item-category references use Swords too.
Compact class lookup is at VA0x51c3c, compact race lookup at VA0x51bec,
and preferred-weapon rendering at VA0x109f20.

English rows store `reference_overrides` with `pointer_offset`, `source_address`,
`en` and a semantic `context`. The builder checks the original ELF identity,
selected pointer ranges, expected old pointer, row identity and complete
installation of all overrides. Strings remain in the English read-only pool.
Labels copied through fixed byte buffers reject this mechanism because those
need caller-specific renderer hooks. The independent verifier reads each
patched pointer and its actual translated bytes, including ordinary references.
Eight focused regressions cover these semantics and the guard failures.

Reuse must not transfer these addresses to another edition. Exact-text import
now refuses a contextual row altogether, requiring its meanings to be traced
in the destination game before reuse. The glossary records the distinctions.

## Assembled class heading in local 0.1.16

The Confirm Class heading at call 0x107a54 obtains a full class name from 0x51c2c, then formats the character name and class using `%s / %s`. Samurai (X0176) remains in original bytes for a fixed-copy class-grid path. Its late renderer alias only matches a standalone label, so it did not match the class embedded after the name and slash.

A heading-specific leaf lookup uses thirteen immutable English pointers in the native class order. Only the call at 0x107a54 changes. The shared getter, original class arrays, fixed-copy labels and player-name bytes stay intact. The leaf keeps the original r3/r9 clobbers and preserves CR, LR, TOC and stack state. The builder guards the source table, getter, caller and formatter; independent verification checks the installed call, leaf and all thirteen English strings.
