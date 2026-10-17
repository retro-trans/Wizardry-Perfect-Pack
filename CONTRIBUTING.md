# Contributing

Bug reports, proofreading and playtesting are welcome through GitHub issues or
[Discord](https://discord.gg/MssepShjmB). Include the build version, location,
exact wording and a screenshot when reporting a visual issue. Distinguish
automated verification from checks actually performed in game.

Keep English translation decisions under `work/translation/en/`, terminology
under `work/glossary/`, layout metadata under `work/ui/`, documentation under
`docs/`, and tools under `tools/`. Preserve row IDs, control codes, placeholders,
source-record boundaries and glossary spellings. Read adjacent dialogue and
the [translation rules](BASE_RULES.md); record unresolved context in the row's
notes. Do not remove a review flag merely because a build succeeds.

Japanese script text must never be committed. Generate source exports locally
from your own game. Commit only English `*.en.json` copies prepared with
`python tools/strip_jp.py --write`. Japanese names and UI terms are allowed in
glossaries. Do not commit game files, extracted data, screenshots, saves, fonts
from the game, personal licence files or local build artifacts.

Use an unused `0.x.y` build version and add a changelog entry. Run translation
validation and checks appropriate to the change, then independently verify the
overlay. Preserve the original game and the separate Labyrinth of Lost Souls
package. Restart RPCS3 and load a normal save when testing a new executable;
an active game keeps the old executable in memory.

Public releases require an explicit request and must follow the
[Retro Trans release guide](docs/RETRO_TRANS_RELEASES.md). Published binaries
and patch assets are immutable; corrections need a new version.
