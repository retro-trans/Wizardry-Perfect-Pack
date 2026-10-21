# Bestiary lore layout

Local build 0.1.18 reflows the lore field in monster member 2 of the table archives. Canonical English decisions, monster names, abilities and numeric data remain unchanged. Single source line breaks become soft breaks; blank lines between paragraphs are retained, while empty trailing space is removed from the display copy.

The native lore branch sets a 28px font at VA0x100560/0x100564, reads the lore at record offset 1305, and draws it at the panel origin plus 16px in each direction through VA0x1005b0. Two guarded font constants select 22px only for this branch. The display model reserves a conservative 288px by 480px text rectangle. At 23px line pitch, all 200 entries fit within twenty lines and at most 459px; paragraph breaks and every word remain intact. Excess width or height blocks the build.

The reported Undead Goblin entry is DM0041. Tests check it through the final labyrinth sentence, both font guards, all lore entries, and unchanged monster names and abilities in the relocated pool. Independent overlay verification checks every lore token and the actual installed font instructions, with existing non-text database preservation checks retained. The list, names and status views keep their separate native font settings.

The source screenshot and modeled bounds are recorded in work/ui/bestiary.en.json. The capture bounds are approximate; updated in-game appearance still needs confirmation using the local launcher. The public release remains 0.1.14.
