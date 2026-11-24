# Paris on the Delaware: public release checklist

Started 2026-11-09. This is the list of what stands between the set on the author's PC and a public upload.

## Done

| Item | State |
| --- | --- |
| Growable buildings | 730 in game across Z1 to Z8. R7 (48 department stores, 48 towers) is staged and waiting for import, which makes 826. |
| Civic services | 11 in game, all wired to real service behaviour. |
| Park monuments | 5 built by Claude, staged in `generator\imports\1_READY_M1_monuments_5`. |
| Service names and descriptions | Written for all 11 services and the 5 monuments. The list is `tools\newfrance_services.json`. |
| Asset-bar thumbnails | 16 rendered, in `thumbnails\`. See `thumbnails\_sheet.jpg`. |
| No third-party pack needed | Every service now uses only base-game parts. The borrowed Chicago library icon is gone. |
| Textures safe to publish | All from ambientCG, which is CC0 (public domain). No credit is required, but one is polite. |
| No benches | Rule since 2026-11-09. None in any service, monument or R7 building. |
| Fictional names only | Checked on every service, monument and poster. |

## Still to do

| # | Item | Who | Note |
| --- | --- | --- | --- |
| 1 | ~~Check names and thumbnails show in game~~ | the author | **Confirmed 2026-11-09:** all show, with descriptions. |
| 2 | Import R7 and M1, then run the setup | the author, then Claude | Growables for R7, "Building" for M1. |
| 3 | Check the five monuments in game | the author | Tourist Attractions tab. Check size, that they place without "no pedestrian access", and the price. |
| 4 | Names for growables | Claude | A clicked rowhouse still shows its file name. Claude can generate a name per family (for example "Maison du Quai") from the design sheets. About 30 family names, not 826. |
| 5 | Zone names and icons | Claude | The 11 "Napoleon …" zones must ship with the set, since every growable points at them. They need the same name and icon treatment. |
| 6 | Hôpital des Invalides ghost windows | GPT, then the author | The wing ends overlap, so frames show through a wall. GPT re-bakes it as a re-import with R8. The Opéra and the Usine had the same fault, caught before import. |
| 7 | Clean-profile test | the author | Turn off every other mod and asset pack, load a new map, and confirm the set works alone. This catches hidden dependencies. |
| 8 | Size on disk | Claude | Measure the full ImportedData size and report it. Players care about download size. |
| 9 | R8 big services (Opéra, cathedral, power, water, radio) | GPT | Optional for a first release. Could be version 1.1. |
| 10 | Upload page | the author, Claude drafts | Title, short description, long description, 5 to 8 screenshots, tags, credits. `images for public upload\` has one screenshot so far. |
| 11 | Upload | the author | Done from the in-game editor to Paradox Mods. Claude never uploads. |

## If the names or thumbnails do not show (item 1)

The files Claude wrote match the format of a published pack byte for byte. The open question is only whether the game reads them from the local import folder or only from a packaged upload. If they do not show locally, they will most likely appear once packaged. Claude can test that with a small local package before the real upload.

## Suggested release order

1. Items 1 to 3 (one play session).
2. Items 4 to 6 and 8 (Claude, one sitting).
3. Item 7.
4. Items 10 and 11. Ship version 1.0. R8 follows as 1.1.
