# Lobstertown: zone handoff

*Written 2026-11-17 by Claude for the author. Each zone section stands on its own, so it can start that zone's own thread (paste the Common section plus the zone's section). One section per zone, after what is common to all of them. `HANDOFF.md` keeps the full history; this file is the quick map. Paths are relative to `C:\Users\<you>\CS2Planner\Lobstertown\` unless they start with `CS2Planner\`.*

## Common to every zone

**Pipeline (all on the PC, from `gemini\`, using the full Python path `C:\Users\<you>\AppData\Local\Programs\Python\Python313\python.exe`):**

1. **Design:** edit the zone's module in `gemini\source\lt_designs\` and its entries in `gemini\lt_roster.py`.
2. **Bake:** `python run.py $(python lt_roster.py ZXX | tr ',' ' ')`. Bake the whole set in one run (no pilots). Output goes to `gemini\runs\<stamp>\`.
3. **Review:** look at the contact sheets, then fill every `_REVIEW.md` (8 PASS rows, `Verdict: PASS`).
4. **Stage:** `python run.py --stage runs/<stamp>` creates `generator\imports\1_READY_GEMINI_<stamp>_<count>`.
5. **Clear the old copies:** with the game closed, move the old files of a replaced set out of `%USERPROFILE%\AppData\LocalLow\Colossal Order\Cities Skylines II\ImportedData` into `CS2Planner\backups\ImportedData_<reason>`. Group them by base name (strip `.bak` / `.cid`).
6. **the author imports:** he makes the zone in the editor (a new zone only) and imports the READY folder.
7. **Setup:** with the game closed, run `python tools\newfrance_setup.py --dry-run`, then run it for real. Spot-check one building's level, lot, access, zone and households.
8. **File it:** move the READY folder to `generator\imports\2_PROCESSED\`. An import it replaced becomes `0_SUPERSEDED_*`.

**Palette-only changes** need no re-bake and no re-import. Colours live in `gemini\colour_variations.json`, which `lt_roster.py` writes. The setup script rewrites each main mesh's ColorProperties, so just regenerate the file and re-run setup with the game closed. This is how the historic-district colours went in on 2026-11-17.

**Backups and files:**
- **Before a change:** copy the file to `<name>.pre_<change>.<ext>`, for example `lt_roster.pre_hdc.py`.
- **ImportedData copies:** they go to `CS2Planner\backups\ImportedData_<reason>`.
- **Line endings:** the Python sources and `HANDOFF.md` are CRLF. To patch them from Python, read and write bytes, because `write_text` on Windows doubles the `\r`. Don't put a `#` comment mid-line in `gemini_specs.py`.

**Rulebook (`gemini\RULEBOOK.md`):** an edit needs the author's direct approval, typed on the PC. Otherwise, propose the wording only.

**the author's preferences (his eye in game outranks every rule):**
- **Each district distinct:** every district has its own architecture and material family (rule 20), never a recolour of another.
- **Muted colours:** the historic district commission's palette. Greyed period colours, nothing candy or "laffy taffy".
- **Entrances at grade:** doors open off the sidewalk, with no raised stoops.
- **Rule 28:** every window needs a room behind it, never sky or a roof slope.
- **Fill the lot:** build to 0.6 m off the rear line (rule 17). No props or loose objects in the mesh (rule 19); he dresses lots with Placemaker.
- **Level 1 only:** a bigger or denser version is a new zone.
- **Reports:** short updates with a table and a contact sheet. No paid API calls unless he asks.

**Budgets:** LOD0 / LOD1 / LOD2 at most 45,000 / 9,000 / 1,000 triangles (160,000 / 24,000 / 3,000 for ZP3 and ZC2). The bake also needs at least 8 triangles per m² of skin.

## ZL1: Shore Rows

- **Game zone:** Lobstertown Low Residential (a Residential Low clone). 100 buildings, 20 designs at 1x2–1x6, 2–4 households.
- **Module:** `shorerows.py`.
- **Architecture:** late-Victorian painted ladies (Carpenter Gothic, Queen Anne, Stick, painted triple-deckers). Fishscale, diamond and board-and-batten accents. Each rear is its own run of wings ending in a carriage house.
- **Palette:** `victorian`, the historic district edition (2026-11-17). 12 greyed sets: sage, putty, stone grey, olive drab, slate blue-grey, oxblood, spruce, buff, warm grey, cream, lichen and umber. The accent shingles are a shade off the body; trim is cream, off-white, spruce or black. Swatches: `research\hdc\hdc_swatches.png`.
- **Last run:** `2026-11-16_183227`, filed as `generator\imports\2_PROCESSED\1_READY_GEMINI_2026-11-16_183227_100`. In game and set up; the new colours were applied by setup on 2026-11-17.
- **Backups:** the old ZL1 import is in `CS2Planner\backups\ImportedData_pre_shorerows`. The meshes before the colour change are in `ImportedData_pre_hdc_colours`. Sources: `*.pre_shorerows.*`, `lt_roster.pre_hdc.py`, `colour_variations.pre_hdc.json`.
- **Watch in game:** whether the new muted colours read well as a street.
- **Rules that bite:**
  - Rule 11, eave levels: a ridge cap off the 0.25 m grid breaks a run; corner houses use `ci=.5`.
  - Rule 21, rear variety.
  - Rule 20, the ZL1 exception for painted colour.

## ZM1: Main Street

- **Game zone:** Lobstertown Mixed Main Street (a Mixed Housing clone; keep "Mixed" in the name so the shops get goods). 50 buildings, 10 designs at 1x2–1x6.
- **Module:** `mainst.py`.
- **Architecture:** a New England brick downtown of 3–4 storey masonry blocks with iron or granite shopfronts. Stone lintels, Italianate hoods or pediments, oriels and canted bays, mansards, brick gables. Corner towers (square or octagonal). Backs step down in brick, with fire escapes.
- **Palette:** `brick` (only the trim varies).
- **Last run:** `2026-11-16_103204`, filed as `2_PROCESSED\1_READY_GEMINI_2026-11-16_103204_50`.
- **Backups:** `CS2Planner\backups\ImportedData_pre_mainst_rework`; sources `*.pre_mainst.*`.
- **Watch in game:**
  - ProvisionsMansard's Greystone reads as rubble rather than ashlar.
  - The square corner tower counts as a roof level.
- **Rules that bite:**
  - Rule 8, clearance: the shop fascias.
  - Rule 26, signs must sit on the 3 m atlas grid.
  - Rule 11, eave levels: a corner tower limits the back range.

## ZP1: Prestige Cottages

- **Game zone:** Lobstertown Prestige Cottages (a Residential Low clone). 48 buildings, 8 designs at 2x4–3x6, 1 household each.
- **Module:** `federal.py`.
- **Architecture:** Federal and Greek Revival captains' houses: hipped roofs with widow's walks, brick ends, gambrels, capes, temple fronts. An ell runs back to a carriage barn round a court.
- **Palette:** `federal`, calmed 2026-11-17. Barn red is greyed to (.52, .30, .26), and the straw walls are now a pale buff. White, cream, pale grey and grey-blue walls stay as they were.
- **Last run:** `2026-11-16_191827` (shared with ZP2), filed as `2_PROCESSED\1_READY_GEMINI_2026-11-16_191827_80`.
- **Backups:** `CS2Planner\backups\ImportedData_pre_federal` and `ImportedData_pre_hdc_colours`; sources `lt_roster.pre_federal.py` and `lt_roster.pre_hdc.py`.
- **Rules that bite:**
  - Rule 17, fill the lot: there are no fenced front yards, only a lawn strip.
  - Open shutters reach about 1.04 m from a window's centre.
  - Baked LOD1 counts run about 1.26× the build count.

## ZP2: Cottage Flats

- **Game zone:** Lobstertown Cottage Flats (a Residential Medium clone). 32 buildings, 8 designs at 3x5–4x6, 6–10 households.
- **Module:** `federal.py`.
- **Architecture:** Federal doubles, brick rows, twin Greek fronts and double capes.
- **Palette:** `federal` (as ZP1).
- **Last run:** `2026-11-16_191827`, with ZP1.
- **Backups:** as ZP1.
- **Rules that bite:**
  - Density floor: the doubles needed dentils at LOD0 to reach it.
  - Rule 22, flush faces: a rear frieze level with an ell's eave was dropped there.

## ZP3: Grand Hotels

- **Game zone:** Lobstertown Grand Hotels (a Residential High clone). 24 buildings at 4x6–6x6, 40–70 households.
- **Module:** `cottage.py` (`hotel=True`).
- **Architecture:** 12–20 storey shingle towers with château crowns (pavilions, domes, spires).
- **Palette:** `shingle` / `clapboard`.
- **Last run:** `2026-11-16_053613`, filed as `2_PROCESSED\1_READY_GEMINI_2026-11-16_053613_24`.
- **Backups:** `CS2Planner\backups\ImportedData_ZC2_ZP3_old_2026-11-15`; sources `*.pre_chateau.*`.
- **Watch in game (not reported yet):** slim turret cones at 60 m, and the far-view shingle reads dark.
- **Rules that bite:**
  - Rules 25a and 25b: the tower budget and balconies.
  - Rule 11b, château crowns (crown blocks under 150 m²).

## ZC1: Boardwalk Shops

- **Game zone:** Lobstertown Commercial Waterfront (the author's Commercial Low Waterfront clone; no households). 48 buildings: 8 mid-block designs plus 4 LeftCorner designs, each at 1x2, 2x2, 2x3 and 3x3.
- **Module:** `shops.py`.
- **Architecture:** "built up over time". Half are brick blocks with an iron or granite shop storey; half are painted clapboard false fronts. 1–3 storeys, with stockrooms filling the deep lots.
- **Palette:** `shopfront`. The historic-commission colour pass has been applied to Shops (the author, 2026-11-17).
- **Last run:** `2026-11-17_182603` (48 of 48 pass), filed as `2_PROCESSED\1_READY_GEMINI_2026-11-17_182603_48`. Set up in game 2026-11-17.
- **Corner pieces (done 2026-11-17):** `corner=True` in `shops.py` builds a LeftCorner: street side inset 0.4 m, shop glass to a corner pier plus a corner entry door, windows on every floor down the side street, cornice carried round, no lettering (the game mirrors it). Designs: ChandleryLeftCorner and SailLoftLeftCorner (brick), BaitTackleLeftCorner and IceCreamLeftCorner (clapboard). Ice Cream is `top="flat"`, because a stepped front plus a stockroom gave four eave heights on 2x3 and 3x3 (the audit allows three). Backups: `shops.pre_corners.py`, `lt_roster.pre_zc1corners.py`, `lt_roster.pre_zc1icecream.py`.
- **Backups:** `CS2Planner\backups\ImportedData_ZC1_BoardwalkShops_*` and `ImportedData_ZC1_leftover` (the old set, found sitting beside the new import); sources `*.pre_windows.*`.
- **Open items:** the author's in-game check of the corners. Corner glass is front glazing plus a door, not wrapped round the corner; true wrap-around glass would be a new change.
- **Lesson:** before the author imports a replacement set, make sure the old files are out of ImportedData, or the import leaves two copies of each prefab.
- **Rules that bite:**
  - Rule 28, born here: false-front windows only where the attic stands behind them.
  - The blank-wall band check: long fascias.
  - Rule 26, signs on the atlas grid.

## ZC2: Boardwalk Palaces

- **Game zone:** Lobstertown Commercial Boardwalk (a Commercial High clone; no households). 32 buildings, 8 designs at 4x4–6x6.
- **Module:** `boardwalk.py`.
- **Architecture:** 4–6 storey shingle palaces behind a two-deck promenade arcade, with château towers and domes.
- **Palette:** `shingle` / `clapboard`.
- **Last run:** `2026-11-16_053203`, filed as `2_PROCESSED\1_READY_GEMINI_2026-11-16_053203_32`.
- **Backups:** `CS2Planner\backups\ImportedData_ZC2_ZP3_old_2026-11-15`.
- **Watch in game (not reported yet):** the turret cones and the dark LOD2 shingle.
- **Open item:** corner pieces.
- **Rules that bite:**
  - Rule 11b, crowns.
  - Turret cones overhang 0.32 m.
  - The blank-wall band check on a 6-wide lot.

## ZI1: Cannery Row

- **Game zone:** Lobstertown Industrial Cannery Row (an Industrial Manufacturing clone; green industry, one clean product each). 32 buildings, 8 designs at 2x4–4x6.
- **Module:** `cannery.py`.
- **Architecture:** six brick-and-granite works (side-ridge piles, mansards, gambrels, stair towers, stacks) behind a granite quay, plus two weathered board sheds.
- **Palette:** `brick` / `shingle`.
- **Last run:** `2026-11-15_213023`, filed as `2_PROCESSED\1_READY_GEMINI_2026-11-15_213023_32`.
- **Backups:** `CS2Planner\backups\ImportedData_stray_CanneryRow_label_2026-11-15`.
- **Watch in game:** the LOD2 brick tile reads coarse at a distance.
- **Rules that bite:**
  - Rule 20: no white trim in this family.
  - Entrances at grade: one sidewalk step at most.
  - The `PRODUCT` line for every design.

## ZO1: Exchange Row (new 2026-11-17, not staged)

- **Game zone:** none yet. Proposed name "Lobstertown Office Exchange Row", made as an **Office Low** clone; offices have no households. 32 buildings, 8 designs at 2x3, 3x3, 3x4 and 4x4.
- **Module:** `exchange.py`; roster `EXCHANGE_ROW`, `MODULE['ZO1'] = 'exchange'`.
- **Architecture:** the town's office district, Beaux-Arts and Classical Revival, c. 1900–1915.
  - **Fronts:** a grey granite banking storey (often rusticated, with tall glazed arched windows), pale limestone ashlar above, stone lintels and hoods, a frieze with dentils and modillions, a deep stone cornice, balustrades.
  - **Roofs:** green copper (a mansard, a hip, a dome, a clock-tower pyramid). Bronze six-over-six sashes and bronze doors at grade; no white trim.
  - **Backs:** ashlar or buff common brick, with a skylit banking hall, stepped back blocks, or wings round a light court; ventilators on the back roofs.
- **Designs:**

  | Design | Front | Roof and crown | Back |
  | --- | --- | --- | --- |
  | SeamensSavings | 3 storeys, columns, quoins, cap hoods | stone pediment | skylit hall |
  | CustomHouse | 3 storeys, pediment hoods, quoins | copper dome | stepped |
  | MerchantsExchange | 4 storeys, pilasters | copper mansard | full depth |
  | MarineInsurance | 4 storeys | attic storey | brick wings round a light court |
  | CableOffice | 3 storeys, quoins | copper hip | brick back block |
  | SteamshipAgency | 4 storeys, bronze oriels | balustrade | hall with a clerestory |
  | TrustCompany | 3 storeys, columns | attic storey | stepped |
  | GazetteBuilding | 4 storeys, pilasters | clock tower | brick back block |

- **Palette:** `exchange`. Stone and copper aren't tinted; colour 2 tints the few TrimWhite faces to limestone, warm stone or granite.
- **Last run:** `gemini\runs\2026-11-17_061902`: 32/32 PASS, reviews filled. Sheets in `runs\2026-11-17_061902\sheets\`:
  - `_front`, `_frontleft`, `_rear`, `_aerial`: one row of designs at 3x4.
  - `_allsizes`: every design at every lot.
  - `_districts`: rule 20, side by side with Main Street, Federal, Boardwalk Shops and Cannery Row.
- **Kit change:** `lt_kit.loading_bay` has a new opt-in key, `glazed` (a glazed arched window). Backups: `lt_kit.pre_exchange.py`, `lt_roster.pre_exchange.py`.
- **To put it in the game:**
  1. the author OKs the sheets.
  2. `run.py --stage runs/2026-11-17_061902`.
  3. In `tools\newfrance_setup.py`, add `"ZO1": "Lobstertown Office Exchange Row"` to `ZONE_KEY` and add `"ZO1"` to the `nonres` tuple, so offices get no flats.
  4. the author makes the Office Low clone and imports.
  5. Run setup.

  New names, so there is nothing to clear out of ImportedData.
- **Proposed rulebook wording (needs the author's typed OK on the PC):**
  - **Zones row:** `| ZO1 | Lobstertown Office Exchange Row | Office Low | Exchange Row (exchange.py): Beaux-Arts banks and offices, granite banking storey, limestone ashlar, stone cornices and balustrades, green copper mansards, hips, dome and clock tower, bronze sashes; backs in ashlar or buff brick with banking halls, stepped blocks or a light court | 2x3, 3x3, 3x4, 4x4 | 32 |`
  - **Rule 20, add a family:** "**offices** (ZO1 Exchange Row) grey granite base, pale limestone ashlar, stone trim and cornices, green copper roofs, dark bronze sashes, no white trim."
- **Watch in game:**
  - The MerchantsExchange mansard runs the full lot depth (a long copper-and-tin deck on 3x4 and 4x4).
  - The buff brick LOD2 tile reads coarse.
  - Heights run 15–29 m (the Gazette tower is the tallest), probably more than a vanilla Office Low.
- **Rules that bite:**
  - **Density floor (8 triangles per m²):** ashlar's 9.45 m tile and big flat roofs carry little geometry. Six-over-six sashes, balustrades, rear hoods, roof ventilators and rear rustication were all needed.
  - **Rule 22:** dentils sit on the frieze, clear of lintels and pilaster caps.
  - **Rule 2:** attic windows are sized to the bay spacing (`s/3.3`).
  - **Rule 4:** attic windows at least 1.4:1.

## ZS1: Civic and service buildings (new 2026-11-17, not baked)

- **Not a game zone.** 11 ploppable services, one lot each. `tools\newfrance_services.json` (entries `NA_LT<Design>_L1_WxD`) turns each into a service at setup.
- **Module:** `civic.py`; roster `CIVIC` (each design carries its `lot`), `MODULE['ZS1'] = 'civic'`, palette `COASTAL['ZS1']` (shingle tints, white/cream trim).
- **Architecture (the author's pick, "fieldstone and shingle"):** Richardson manner. Rough fieldstone (`Greystone`) ground storey with round-arched windows on dressed voussoirs, weathered shingle above, deep slate hips (or a big shingled front gable), octagonal stair turrets, a hose tower, belfry or clock stage, a fieldstone back wing to the rear line.
- **Designs:**

  | Design | Lot | Service | Notes |
  | --- | --- | --- | --- |
  | FireStation | 4x4 | fire | 3 open engine bays, hose tower |
  | Constabulary | 4x4 | police | steep hip, turret, 2 carriage doors |
  | CottageHospital | 4x4 | hospital (clinic numbers) | verandah, twin ward wings, 2 ambulance doors |
  | GrammarSchool | 4x5 | elementary | cupola |
  | Academy | 5x6 | school | 3 storeys, clock stage, twin wings |
  | PostOffice | 3x3 | post | front gable, turret, van door |
  | TownHall | 4x5 | landmark | front gable, belfry, turret, 2-storey wing |
  | Library | 4x4 | landmark | steep hip, lookout turret |
  | Waterworks | 3x3 | water (groundwater) | steep hip, stack, cupola |
  | Powerhouse | 4x5 | power | two stacks |
  | TransferBarn | 3x3 | park (decorative) | front gable, wagon doors; no garbage template exists |

- **Templates:** water = Chicago pack `NA_DeverCribWaterIntake` (`m_AllowedWaterTypes` set to 1, groundwater; its FloatingObject is not copied); power = Battersea mod `154430_5\battersea_*.cok` (`PowerPlant`; the path names mod version 5, fix it if the mod updates). `TEMPLATES` takes an optional third item, the pack.
- **Previews (dry run, no Blender):** `research\civic\`. All 11 pass the kit rules at LOD 0/1/2.
- **Backups:** `*.pre_civic.*` (lt_roster, newfrance_setup, newfrance_services, ZONE_HANDOFF).
- **Watch at the bake:** the 8 triangles per m2 density floor (stone walls carry little geometry); the front gable rake and towers against the 3 eave levels; the power plant's output (template value 5,030,000) and whether it needs a power line connection the setup does not add.
- **To put it in the game:** bake `run.py` with the ZS1 list, review, stage, the author imports, run setup. Each step waits for the author's go in the project chat.
- **Street line (2026-11-18, the author: services sat back from the sidewalk):** the first ZS1 bake used a 3.0 m `set` plus turret fronts 2.6 m proud, so fronts stood 3 m in. `civic.py` now sets the street wall 1.0 m in (Main Street / Exchange Row standard), turret fronts .3 m proud, hospital `set=2.1` with its verandah to lot y .3; pedestrian points y .6, vehicle points recomputed in `newfrance_services.json`. Backups `*.pre_setback.*`. Needs a re-bake, re-stage, re-import (same names: clear the old ZS1 files from ImportedData first) and a setup re-run. Landmarks (`landmarks.py`) have their own `yF = -4D + 2.0/2.5`; it is a per-module value, not a shared setting.

## ZH1: Harbour Hill (new 2026-11-18, staged, not imported)

- **Game zone:** Lobstertown Harbour Hill (a Residential Medium clone; make it in the editor). 26 buildings: 6 designs at 1x4, 1x6, 2x4, 2x6, plus HarbourLeftCorner at 2x4 and 2x6 only (RightCorner dropped on purpose).
- **Module:** `harbourhill.py`; roster `HARBOUR_HILL`, `ZH_HH` (households 8, 10, 12, 16). Setup name added in `ZONE_KEY`.
- **Rename:** the roster design is `HillQuadDecker`, because `QuadDecker` already exists in ZL1 and would have overwritten it at 1x4 and 1x6.
- **Run:** `2026-11-17_215101` (26 of 26), staged as `1_READY_GEMINI_2026-11-17_215101_26`. Fixes: CorniceBlock quoins stop at `top - .7`; the corner belfry tower starts at `top + DEEP - .1` and ends at `top + 5.35`. Backup `harbourhill.pre_zh1fix.py`.

## ZP4: Motor Courts (new 2026-11-18, staged, not imported)

- **Game zone:** Lobstertown Motor Courts (a Residential Medium clone). Designed for 18 buildings; 15 pass.
- **Modules:** `motorcourt.py` and `courtplan.py`. Cabins stand in rows that touch (windowless on the shared wall) and are tied together by covered walks (`links()`), because the audit needs one building.
- **Run:** `2026-11-17_221746` (15 of 18), staged as `1_READY_GEMINI_2026-11-17_221746_15`.
- **Not staged (fail the audit):** UCourt 3x5 and 4x6 (1 m² slit); GambrelCourt 3x5 (4 eave levels). Roster changes: GambrelCourt is layout R, OfficeCourt is gable (was gambrel). The first building in a run owns the textures, so a failing first building blocks staging; bake a passing one first.
- **Backups:** `motorcourt.pre_zp4.py`, `lt_roster.pre_zp4.py`, `lt_roster.pre_zp4b.py`.

## ZC2 extras (2026-11-18)

- 4 new Palaces (TidewaterCasino, SeaBathhouse, DancePavilion, BathingHotel) at 4x4, 4x5, 5x5, 6x6, with no sign key. They go into the existing ZC2 zone, and the 32 old Palaces are untouched.
- **Run:** `2026-11-17_221548` (16 of 16), staged as `1_READY_GEMINI_2026-11-17_221548_16`. SeaBathhouse got `promenade=True` to clear the 8 triangles per m² floor at 6x6. Backup `lt_roster.pre_zc2x.py`.
