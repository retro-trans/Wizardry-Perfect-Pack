# Menu corrections in 0.1.3

The five supplied screenshots are saved unchanged under `work/ui/menus-before-0.1.2-*.png`. Their measured panel coordinates and font budgets are in `work/ui/menus.en.json`. Updated in-game captures remain pending.

The registration labels now use “Align.” and “Look”. Class details use “Weapons”, “Style” and “Skills”, with concise descriptions checked against the value column. Party controls use “Party” and “Order”; row headings use “Front” and “Rear”. The narrow weapon-hand labels use “M:” and “S:”. The roster uses “Adventurers” and “Neut.”. The latter corrects an inherited meaning error: both occurrences of X2363 are the Neutral entry in Good/Neutral/Evil alignment arrays at `0x456a38` and `0x456bcc`.

Several cut-off strings have a different cause from ordinary width overflow. The compiler inlined copies of the original short labels, including their original terminators. Early relocation of a longer English label caused these copies to omit the new terminator. Increasing unknown stack slots would risk corrupting neighboring data.

Nine label IDs therefore retain their original source bytes through those native copies. An immutable table maps the byte contents to the full English labels at the existing font measure/draw boundary. Matching uses copied bytes, not pointer identity. Whole-label matches cannot change longer words; the two hand labels also allow a prefix match before an item name. Database token expansion still runs on the remaining text. Each renderer call owns its expansion buffer; no shared temporary string is introduced.

The equipment marker is the same missing-terminator bug. At `0xb66a8`–`0xb66b4`, the game copies the complete previous item name into `sp+0x90`. At `0xb6718`–`0xb6760`, it overwrites just seven bytes with the Equipment header. Seven bytes include the original label's NUL but only “Equipme” from the relocated English label. The old item's final token bytes then remain visible, matching the reported `030~` suffix. Keeping the original terminated label until rendering removes that suffix without truncating item names.

Validation includes the host-native resolver cases, all nine original-sized copy cases, a reused equipment-buffer regression, PPU wrapper argument-preservation checks, and original-font width checks for 45 labels and class-description values. These are static/host checks; they do not claim updated PPU gameplay or complete UI coverage.
