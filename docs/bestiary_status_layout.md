# Bestiary status labels (local 0.1.20)

The reported Gold label was copied into a stack buffer using the Japanese
literal's compiled length: 12 bytes, including its terminator. The English
`Gold Obtained:` needed 15 bytes including its terminator, so the copy omitted it and the
renderer consumed stale stack bytes. `Experience Gained:` had the same risk
with its 17-byte copy. The optional Spell Resistance row also has a 17-byte
copy and an English label that exceeded it.

Keep these three source pointers intact until the native copy finishes, then
resolve their text at the existing renderer's measurement and drawing hooks.
Use **Gold:**, **EXP:** and **Spell Res:**. Other occurrences of longer reward
labels retain their own translations.

All nine label/value pairs use a fixed label right edge at panel-relative
**132px** and a value left edge at **144px**. The 12px gap replaces the native
touching columns and the dynamic anchor based on the longest translated label.
The native 320px panel, 24px font, vertical positions and colors are preserved.
The ninth pair is the optional Spell Resistance row; immunity and special
attack text retain their separate positions.

`tools/bestiary_status_layout.py` guards the ten coordinate instructions and
nine instructions identifying the three native copies. Four focused tests
cover those guards, source terminators, alignment scope and native-font bounds
for every label and wide numeric values. The host resolver test checks each
copied label in a buffer containing stale `BCD@` bytes. These checks do not
execute PowerPC code or establish in-game visual acceptance.

The local overlay and staged test executable are 0.1.20. Save and close the
project test session, then run `work/output/Play-English-Test.cmd`. Confirm
**v0.1.20**, open Magic Tree's bestiary status and check **Gold: 6** and
**EXP: 36**. All label ends and value starts should align with a clear gap.
Check a monster with larger rewards and the additional statistics unlocked by
more kills. Switch to its lore view to recheck the existing wrapping fix.

Only Prisoners of the Lost City is affected. The public release remains
0.1.14; updated in-game appearance is pending.
