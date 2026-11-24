# Lobstertown: how to run the whole pipeline yourself (for Gemini and GPT)

the author's town mod for Cities: Skylines II. Maine shingle style. You design, bake, review, stage and run setup. the author imports in the game editor and checks results in game. Folder: `C:\Users\<you>\CS2Planner\Lobstertown`. Python: `C:\Users\<you>\AppData\Local\Programs\Python\Python313\python.exe` (bare `python` opens the Store stub). Blender 5.2 is installed; run.py calls it.

## Folder map
- `gemini\RULEBOOK.md`: the rules. Read rules 11, 17, 20, 21, 26, 28, 29 and the "How the audit sees" section first.
- `gemini\source\lt_designs\*.py`: one design module per set (`build(lod, **variant)`). Copy the closest one.
- `gemini\lt_roster.py`: lists designs, sizes, households and writes the stubs into `gemini\scripts\`.
- `gemini\run.py`: bake, audit, preview, stage. `gemini\runs\<stamp>\`: output, REPORT.md, previews, `_REVIEW.md` per building.
- `generator\imports\1_READY_*`: staged sets waiting for the author. `2_PROCESSED`: done. `GPT_INBOX\gemini\designs.json`: zone registry (run.py --stage writes it).
- `tools\newfrance_setup.py`: setup. `ZONE_KEY` maps zone keys to the exact game zone names.
- Backups: copy any file to `<name>.pre_<reason>.py` before editing. Old game files go to `CS2Planner\backups\`.
- `_archive\`: old `*.pre_*` backups (same subfolder layout as the original, under `pre_backups\`), old logs, runs before 2026-11-17 (`old_runs\`) and stale docs. `_archive\MOVED.txt` lists every move. Nothing in the pipeline reads it.

## Steps, in order (run from `gemini\`)
1. **Design.** Edit or copy a module in `lt_designs`, add roster entries in `lt_roster.py`. Whole set at all sizes, no pilots.
2. **Dry check** (optional, no Blender): `tools\dry_harness.py`, `roster_test.py` show kit-rule failures fast.
3. **Bake the whole set in one run** (one texture set): `python run.py $(python lt_roster.py ZXX | tr ',' ' ')`. In PowerShell: `python run.py (python lt_roster.py ZXX).Split(',')`. Roster prints commas; run.py needs spaces.
4. **Read `runs\<stamp>\REPORT.md`.** Fix every FAIL at its cause and rebake the whole set.
5. **Review.** Look at the previews (front, rear, aerial). Fill each `_REVIEW.md`: 8 rows PASS and a line `Verdict: PASS`. `--stage` skips anything without PASS.
6. **Stage:** `python run.py --stage runs/<stamp>` creates `generator\imports\1_READY_GEMINI_<stamp>_<count>`.
7. **Replacing an old set?** With the game closed, move its old files out of `%USERPROFILE%\AppData\LocalLow\Colossal Order\Cities Skylines II\ImportedData` into `CS2Planner\backups\ImportedData_<reason>`. Group by base name (strip `.bak`, `.cid`). Otherwise duplicates appear.
8. **Zone key.** New zone: add it to `ZONE_KEY` in `tools\newfrance_setup.py` and a row to the RULEBOOK zone table (ask the author first). Zones that sell goods need "Mixed" in the name; names with "Commercial" get no households.
9. **the author imports** the READY folder (whole folder, game editor) and makes any new zone with the exact name. Wait for him.
10. **Setup, game closed:** `python tools\newfrance_setup.py --dry-run`, check each building lands in the right zone and lot, then run it without `--dry-run`. Spot-check one prefab: level 1, lot, access, zone, households.
11. **File it:** move the READY folder to `generator\imports\2_PROCESSED\`. Colour-only changes need only `colour_variations.json` plus step 10.

## Rules that keep failing builds
- **Rule 28:** every window opens onto enclosed space under the building's own roof (storey, gable attic, dormer, turret). No windows onto sky, roof slope or parapet. Use panels there.
- **Rule 29:** the main front wall stands within about 1 m of the lot front line. Measure to the main wall, not the verandah or porch. Porches, stoops, bays and cornices may project. Recess galleries under upper floors.
- **Coverage:** 70% or more. Rear wall 0.6 m inside the lot line. the author hates empty yards.
- **Eave heights:** three at most. A level needs 3 m of unbroken outline. Gambrel lower slope rises under 1.6 per 1. Give every front a full porch or bay. Barns ridge across the lot on party-wall lots.
- **Crowns:** a turret or pavilion under 150 m² in plan counts as crown, not an eave, only in ZC2 and ZP3.
- **Slits:** none. Keep overhang edges off grid-cell centres (use 0.5 m, not 0.45). Nothing shares a plane (parts 3 mm apart). Roofs are closed solids.
- **Palette:** blues and navies, whites and creams, driftwood and sand, muted sage and grey-green. Reds, rust brown and charcoal only on doors and shutters. No bright roofs, no pastels.
- **Corners:** LeftCorner only. The game mirrors it. Never make RightCorner. No lettering on corner pieces. Mirror whole buildings, never parts.
- **Variety:** every design differs in mass, roofline and rear from its siblings, and each zone differs from the others. Entrances at street level. Stand-alone: no props, fences, flags, loose spires.
- **Budgets:** LOD0 at most 45,000 triangles, LOD1 9,000, LOD2 1,000. Density at least 8 tri per m².

## Common failures and fixes
- "extra eave": a rake or pediment counted as a level. Add a porch or bay across it, or lower the step under 0.4 m.
- "slit": tuck the verandah roof into the tower it meets; move edges off grid centres.
- "blank wall 30 m²": add windows, or break the plane with a bay. Long fascias and cornices count too.
- Density under 8: add coursing, trim and window detail at LOD0.
- Rule engine fails 2/3: doors above ground, or glazed doors off the window rows. Use plain windows behind decks.
- Shared textures: a batch's first `NA_LT` building owns the textures. Never drop it from a staged folder.

## Do not touch
- RULEBOOK.md without the author's OK. Any `*.pre_*` backup (new ones sit beside the file until the next tidy; old ones are in `_archive\pre_backups`). `generator\imports\2_PROCESSED`. `lt_kit.py` or `nf_kit.py` (a kit fix needs the author's OK).
- the author's game files except through the steps above. Never delete: move to backups.
- Never import a READY folder that a newer run replaced. Never stage a building whose review isn't PASS.
- Report in `GPT_INBOX\<set name> - review` with a short table: size, households, coverage, front wall to main wall, colours.
