# Item-screen corrections

## Compact item stats in local 0.1.15

The compact stat labels use Atk, Acc, Rng, Elem, Def and Eva (X1416–X1421). Their existing late renderer aliases remain in place. Separate full-word labels are unchanged.

The weapon preview has the same original 740px left anchor as the armor preview: even abbreviated Elem is wider than the 34px available before the frame edge. Eight guarded constants move the four weapon label/value pairs 32px right to 772px. Elem then starts at 711px, inside the 706–957px panel. Two further constants move the attack-count prefix 24px right. Its anchor is computed from the native fixed `000\uff5e000` width sample, rather than the Attacks label. Native full-width damage ranges and the maximum byte-sized x255 count fit with a gap; the right column and row heights are unchanged.

The native-font audit covers 66 cases. Two preview guard/scope tests and eleven runtime-wrapper tests pass, and independent overlay verification checks the actual instructions and deferred labels. Updated in-game appearance remains pending.

## Inventory names and preview label in 0.1.6

The new Items screenshot is saved as `work/ui/items-before-0.1.6-unidentified.png`, with geometry in `work/ui/status-items.en.json`.

Only the inventory name draw at `0x26148` is redirected. It measures the expanded English with the native font function, keeps 32px height, and reduces horizontal size only when necessary. Ordinary names have 288px. Stackable names have 252px, reserving an 8px gap before the maximum two-digit quantity; the separate quantity draw is unchanged. The reported Protective Gear-like Object uses 22px horizontal size and measures 276px. Complete names remain available in every other context.

The bridge reads and restores the actual native font dimensions around each name draw. It forwards the original coordinates, color, flags and variadic inputs, preserves registers and condition state, and leaves the native draw's consumed size-override flag intact. Private stack storage starts beyond the native argument spill area.

The Unidentifi preview was caused by a ten-byte compiler-generated copy of the source label, which cannot hold the 13 bytes required by the English string and terminator. The `X0016` source stays terminated through that copy and expands to Unidentified at the existing font boundary. Native buffer sizes remain unchanged.

The name audit covers all 394 item records in four archives, 1,182 nonempty name fields, and 858 distinct display variants including enhancement suffixes. All 1,716 ordinary/stackable width cases fit. Updated gameplay appearance remains pending.

## Detail popup and armor preview in 0.1.4

The three user screenshots are saved unchanged as `work/ui/items-before-0.1.3-*.png`. Measured panel bounds and label cases are recorded in `work/ui/items.en.json`.

The item-detail popup contains fixed grids designed for short Japanese labels. Seven cell-drawing groups now measure complete English through the existing font hook. Short labels use 22×22px. Wider labels reduce horizontal size until native measurement fits 72px in the class grid or 104px in the right-hand grids. Vertical size remains 22px. The original centers, colors, flags, row spacing and column spacing remain intact. The 40 label cases modeled from the supplied screens require no horizontal size below 13px.

Two small bridges occupy the previously inspected code gap. They call the existing measurement entry, remeasure after estimating the size and decrement for rounding overshoot. The popup's unused stack slot at `sp+0x188` holds the chosen size until its original font-setting call. Each bridge preserves the caller's inputs, TOC, condition flags and return address; native measurement retains its ordinary floating-point clobbers. The original popup frame and all changed instructions are guarded before modification.

The armor/accessory preview has four right-aligned stat rows. Their original x anchor was 740, causing English labels to begin outside the 706–957 panel. Eight guarded constant changes move both labels and values 80px right, to an anchor of 820. The four row heights and weapon/miscellaneous branches remain unchanged. Modeled label starts are 713–728, within the frame.

Seven preview headings also suffered the fixed-copy terminator problem described in `docs/menu_layout.md`. They now retain their original terminated bytes until late font expansion. “Equipment Slot”, “Additional Effects” and “Organize Items” become “Slot”, “Effects” and “Organize” in these narrow UI labels.

Hands, Feet and Head were absent from the string inventory because the compiler constructs their three UTF-8 bytes with immediate instructions. `tools/ui_literal_text.py` guards those instructions and exports three source rows. Their English aliases expand after native construction; no adjacent stack slot is enlarged.

Verification includes seven fitting tests covering 84 instruction-executed sizing/rounding/clobber scenarios, all 52 fitting guards and code-gap boundaries, two preview-scope tests, eight previous runtime tests, 53 item-layout metric cases and the prior 58 menu cases. Resolver tests cover 16 copied labels, three immediate labels and the reused equipment-buffer case. Build verification checks the actual font/position instructions and all prior preservation checks. These checks do not replace updated gameplay screenshots.
