# Lobstertown: handoff note

*Written 2026-11-15 by Claude (Claude Code desktop session) for the Lobstertown Cowork project.*

This note describes the project as it stands on 2026-11-15, updated 2026-11-16 (château for ZC2/ZP3, rule 28 window fix for ZC1, everything imported and set up). Read it first, then `BRIEF.md` and `gemini/RULEBOOK.md`.

## What Lobstertown is

Lobstertown is the author's custom building pack for **Cities: Skylines II**.

- **The idea:** Maine/New England shingle-style beach-town architecture, "on steroids". US shore towns put big houses on the beach and Brazil puts towers there, so Lobstertown puts towers there in Maine shingle style.
- **How it should look:** believable, just huge. Weathered grey shingle, white trim, muted colours, and a high-density look in every zone. The density benchmark is Paradox's Toronto Townhouses pack.
- **Where it came from:** it replaced an earlier pack, New France, on 2026-11-14. That pack is deleted, but its toolkit was copied here, so some names still say `newfrance` / `NA_PdD`.

The full brief is in `BRIEF.md`. The research notes (Toronto, Prestige and other packs) are in `research/`.

## Who the author is (how to work with him)

- **Background:** the author is not a programmer. He wants working results and plain-language questions.
  - Never give him code to write, `TODO(human)` sections or "Learn by Doing" tasks. Write the code yourself.
  - Ask design questions in planning terms.
- **His eye in the game outranks every rule** in the rulebook.
- **Full sets, no pilots.** Bake every design at every size in one run. Small test bakes waste his tokens.
- **He watches cost.** Never run paid API calls (Gemini, GPT and so on) unless he asks.
- **No branding.** The Atlantic City / Boardwalk Empire flavour is welcome: real AC avenue names, red tin roofs as a nod to the board game's hotels. No Monopoly branding.
- **Format:** he likes short status updates with a table, plus a screenshot or contact sheet.

## Standing rules for every building

- **Level 1 only.** "There is no L2." Height and size tiers are separate zones, not building levels.
- **No props, benches, water or outbuildings in the mesh.** the author dresses lots himself with Placemaker.
- **Fill the lot to 0.6 m off the rear line.** Empty ground inside a lot is dead space.
- **Muted colours only.** An early pastel palette was rejected.
- **Shingle style is asymmetric on purpose.** Every front waives rule 6 (`balance`) with that reason.
- **Proportion rules:** the general architecture rulebook (corners, rhythm, order, trim, cornice) applies. It is encoded in `gemini/source/nf_rules.py` and the audit.

## The zone ladder (as of 2026-11-16)

All eight zones are in the game and set up (2026-11-16): ZC1 with the rule 28 window fix, ZC2 and ZP3 with the château crowns, ZI1 new.

| Key | Zone name in the game | Base zone it clones | Sets | Buildings |
| --- | --- | --- | --- | --- |
| ZL1 | Lobstertown Low Residential | Residential Low | Shore Rows second edition (2026-11-17): painted ladies (Carpenter Gothic, Queen Anne, Stick, painted triple-deckers), 1x2–1x6, `shorerows.py`. **In game and set up 2026-11-17** | 100 |
| ZM1 | Lobstertown Mixed Main Street | Mixed Housing | Shops with flats above, painted signs | 50 |
| ZP1 | Lobstertown Prestige Cottages | Residential Low | Federal / Greek Revival harbour town (2026-11-17), 2x4–3x6, 1 household, `federal.py`. **In game and set up 2026-11-17** | 48 |
| ZP2 | Lobstertown Cottage Flats | Residential Medium | Federal harbour town flats (2026-11-17): doubles, brick rows, twin Greek fronts, 3x5–4x6, 6–10 households, `federal.py`. **In game and set up 2026-11-17** | 32 |
| ZP3 | Lobstertown Grand Hotels | Residential High | 12–20 storey shingle towers, 4x6–6x6, 40–70 households | 24 |
| ZC1 | Lobstertown Commercial Waterfront | NA Commercial Low Waterfront | Boardwalk Shops, rebuilt 2026-11-16 in `shops.py`: "built up over time", half brick blocks (cast-iron or granite shop storey), half painted clapboard false fronts, 1–3 storeys, stockrooms filling deep lots, 1x2–3x3. **Staged; needs re-import** | 32 |
| ZC2 | Lobstertown Commercial Boardwalk | Commercial High | Boardwalk Palaces, 4–6 storeys, 4x4–6x6 | 32 |
| ZI1 | Lobstertown Industrial Cannery Row | Industrial Manufacturing | Cannery Row: 6 brick-and-granite works and 2 board sheds, green industry (one product each), 2x4–4x6. **Staged; zone not created yet** | 32 |

**Total: 350 buildings.** 318 are imported and set up; ZI1 is new and ZC1 is a replacement. the author hasn't yet reported back on how the Boardwalk Palaces or the Grand Hotels look in the game.

## Where things live (`C:\Users\<you>\CS2Planner\Lobstertown\`)

| Path | What it is |
| --- | --- |
| `BRIEF.md` | The original brief and market review |
| `gemini/RULEBOOK.md` | Every design rule and lesson, how the audit sees, and the process |
| `gemini/lt_roster.py` | All designs by zone, sizes, households, and the zone-to-module map |
| `gemini/source/lt_designs/` | Design modules: `shore_row.py`, `cottage.py` (prestige, flats, hotels), `boardwalk.py` (ZC2 palaces), `shops.py` (ZC1 shops), `cannery.py` (ZI1) |
| `CHATEAU_PLAN.md` | The château plan for ZC2 and ZP3 (2026-11-16), approved and built (see Open threads) |
| `gemini/source/lt_kit.py`, `lt_shapes.py` | Shared parts: walls, windows, porches, turrets, cornices |
| `gemini/source/lt_atlas.py` | Texture atlas: shingles, tints, and the painted name boards |
| `gemini/source/gemini_specs.py` | Triangle budgets (45k/9k/1k normally; 160k/24k/3k for ZP3 and ZC2) |
| `gemini/run.py` | Bakes, audits, previews and stages |
| `gemini/runs/<stamp>/` | Each bake: meshes, previews, `REPORT.md`, `_REVIEW.md` files |
| `generator/imports/` | Staged sets: `1_READY_*` waiting for import, `2_PROCESSED/` done, `0_SUPERSEDED_*` old |
| `tools/newfrance_setup.py` | Post-import setup: zone, lot, access, households, colour variations |
| `research/` | Studies of other packs, contact sheets |
| `*.pre_<name>.py` files | Backups taken before each change |

## How a set gets made (the pipeline)

**Tools:** use the full Python path, `C:\Users\<you>\AppData\Local\Programs\Python\Python313\python.exe`. Bare `python` opens the Microsoft Store stub. The bakes also use Blender 5.2.

1. **Design:** write or extend a design module and add the roster entries.
2. **Bake all sizes in one run,** so they share one texture set. From `gemini/`:
   `python run.py $(python lt_roster.py ZC1 ZC2 | tr ',' ' ')`
   The roster prints commas; run.py needs spaces.
3. **Fix failures at their cause,** then look at front, rear and aerial contact sheets.
4. **Review:** fill each `_REVIEW.md` with 8 PASS rows and `Verdict: PASS`.
5. **Stage:** `python run.py --stage runs/<stamp>`. This creates `generator/imports/1_READY_GEMINI_<stamp>_<count>`.
6. **Zone key:** add the new key to `ZONE_KEY` in `tools/newfrance_setup.py`.
   - A zone that sells goods needs "Mixed" in its name.
   - A zone with "Commercial" in its name gets no households.
7. **the author's part:** he makes the zone in the game's editor and imports the READY folder.
8. **Setup:** with the game closed, run `newfrance_setup.py --dry-run`, then run it for real.
   - Spot-check one building's level, lot, access, zone and households.
   - Then move the READY folder into `generator/imports/2_PROCESSED/`.
9. **Re-imports:** if a set replaces an older import, first move the old files out of the game's ImportedData folder.
   - The folder is `%USERPROFILE%\AppData\LocalLow\Colossal Order\Cities Skylines II\ImportedData`.
   - Group the files by base name (strip `.bak` / `.cid`); setup-edited files carry later timestamps.
   - Old imports go to `CS2Planner\backups\`.

## Hard-won lessons (details in RULEBOOK.md)

- **Counting triangles:** the bake cuts every face per atlas tile, so baked counts are about 2× the raw counts. It also requires at least 8 triangles per m² of envelope ("too plain" otherwise).
- **The blank-wall audit checks long horizontal bands too.** A 47 m sign fascia or a 48 m cornice fails on wide lots.
- **Turret cones overhang 0.32 m.** Put a corner turret's centre at apothem + 0.34 m from the side lot line.
- **Atlas seams and gaps:** see `research/` and the "Construction" section of the rulebook before any bake.
- **Signs** must sit on the 3 m atlas tile grid (z 3.48–4.06) or the texture splits.
- **Inline comments:** a `#` comment pasted mid-line in `gemini_specs.py` once silently commented out the households.
- **CRLF files:** to patch a CRLF file from Python, write bytes (`write_bytes`). `write_text` on Windows turns `\r\n` into `\r\r\n`, and the roster then fails with a syntax error far past its last line.

## Kit and module options added 2026-11-15/16

- **`lt_kit.py`, opt-in keys for brick (Cannery Row):**
  - a `"bay"` opening kind: an open loading bay
  - `masonry=`: stone lintels and sills instead of white casings
  - `belt_mat=`: stone string courses
- **`cannery.py` (ZI1):** `masonry`, `storeys`, `roof` (`side` / `front` / `mansard`), `roofs`, `cross`, `stack`, `arch`, `tower`, `back='store'`, `vents` (`monitor` / `cupola`), `base`. The roster's `PRODUCT` table gives each design its one product.
- **`shops.py` (ZC1):**
  - `kind` (`brick` / `clap`)
  - brick: `ground` (`iron` / `granite`), `cornice` (`corbel` / `bracket`), `pediment`, `skylight`, `back` (`full` / `store`)
  - clap: `top` (`flat` / `step`), `roof` (`gable` / `shed`), `awning`, `stock` (`shed` / `flat` / `gable`), `stock_mat`, `vent`
  - The `shopfront` palette carries the stronger shop paints.
- **`lt_shapes.py`:** `pavilion_roof()` (a steep closed hip with soffit, crest and finials) and `dome()` (an octagonal drum with a bell dome, a closed solid).
- **`boardwalk.py` (ZC2):** `towers=((pos, k, cap), ...)` (pos `l`/`c`/`r`, k storeys over the eave, cap `hip`/`hipl`/`dome`), `spire=(left, right)` (storeys the corner turrets rise past the eave under a needle cone), `pitch`. Towers never stand in touching cells, so narrow lots drop the second one.
- **`cottage.py` (ZP3, `hotel=True`):** `pavilions=((frac, k, cap), ...)` and `spire`. Pavilion width is capped so its roof plan stays under 150 m², it keeps 2 m clear of the turret and cross wing, and its eave clears the main ridge by 1 m. Above the 10th storey the street front uses light windows (`lite_above`, option (a)).

## Open threads

- **All 350 buildings imported and set up (2026-11-16, 10:04 AM).** the author re-imported ZC1 (window fix), ZC2 and ZP3 (château) and imported ZI1. I ran `newfrance_setup.py --dry-run`, then for real: 350 set up, the 8 zones found, Cannery Row's clean products Food 16 / Textiles 8 / Vehicles 4 / Furniture 4.
  - Spot checks (lot, level, access, zone CID, households or products), all right: Boat Shop 2x4 (ZI1, Vehicles, space multiplier 8), Taffy Shop 2x2 (ZC1, no households), Grand Arcade 6x6 (ZC2, no households), Pennsylvania 6x6 (ZP3, 70 households).
  - READY folders `213023`, `053203`, `053613` and `062325` are in `2_PROCESSED/`. Nothing is waiting in READY.
  - The old copies taken out of ImportedData are in `CS2Planner\backups\ImportedData_*` (ZC1 old and `044639`, ZC2/ZP3 old, and the stray "Cannery Row" name label the author asked to delete).
- **Rule 28, windows need a room behind them (the author, 2026-11-16).** The Taffy Shop's false front had sash windows with sky or a roof valley behind them.
  - Audit: `blind_windows()` in `audit_gemini.py`. Half a metre behind the head of each pane, at three points across it, a ray goes straight up and must meet the building; two misses fail. One miss is allowed because a ray can slip through a 12 mm seam between roof slabs.
  - Blank-wall audit: board walls (false-front backs, parapets) are now exempt. A ray inward meets the building's other face within 1 m.
  - Survey of all 350 buildings: only the four clapboard false fronts failed (Taffy, Kite, Clam, Oyster). Everything already in the game, and both château sets, passed.
  - Fix in `shops.py`:
    - A false-front attic window stays only where the gable attic stands behind it (the middle of each gable). Elsewhere, and in the raised step, there is a cased board panel.
    - New `"blind"` opening kind in `lt_kit.py`.
    - Pilasters between the bays.
    - New keys: `vent` (louvred ventilators on the ridges; Taffy) and `stock_mat` (Taffy's stockroom is now a tin lean-to). Both bring Taffy back over the density floor.
  - Backups: `*.pre_windows.*`.
- **Château build for ZC2 and ZP3 (2026-11-16).** Built, reviewed and staged (above); the author OK'd the sheets.
  - Baked LOD0 / LOD1 / LOD2 at 6x6: ZC2 38,663–53,029 / 4,185–5,861 / 729–1,009; ZP3 75,719–123,210 / 12,798–17,299 / 1,217–1,609 (Pennsylvania is heaviest; it was 152,013). All under the 160k / 24k / 3k caps.
  - Rule 11b is judged block by block in the audit. Rule 19 is reworded: a needle cone that caps a turret is roof.
  - Simpler than the plan: no stepped court wings, no corner turrets or bartizans, no hipped mansards on the ZC2 side cells.
  - Backups: `*.pre_chateau.*`.

- **A true waterfront zone (on hold at the author's request).**
  - Vanilla waterfront zones are look-only, and the game's zone spawner never checks for water. That came from decompiling `Game.dll`.
  - Options already offered:
    1. A look-only wharf set.
    2. Shoreline-snapping ploppables (`ShorelineObject`).
    3. A C# mod that blocks waterfront-zone cells unless the lot's rear meets water.
- **Wait for the author's in-game look** at the Boardwalk set and the Grand Hotels. Things to watch:
  - The turret cones looked slim at 60 m.
  - The far-view (LOD2) shingle reads dark.
- **Older open item:** a "shiny texture" report that was never reproduced. Ask the author for an example of a building that isn't selected.
- **Next, proposed to the author 2026-11-16 (nothing built):**
  1. **Main Street (ZM1) to the variety bar: BUILT 2026-11-16, run `2026-11-16_103204` (50/50 PASS, reviews filled), the author OK'd the sheets 2026-11-16 21:03Z; staged as `generator/imports/1_READY_GEMINI_2026-11-16_103204_50`; the old ZM1 files (1,430: 930 files + 50 folders) moved out of ImportedData to `CS2Planner\backups\ImportedData_pre_mainst_rework`. IN GAME 2026-11-16 (evening): the author imported once (checked: 50 folders + 930 files, one import pass, no duplicates); `newfrance_setup.py --dry-run` then real: 350 set up, all 50 ZM1 in Lobstertown Mixed Main Street; spot checks CornerBrickShop 1x4 households 3, corner access, BakeryGable 1x3 households 2, front access. READY folder filed in `2_PROCESSED`; the old ZM1 import `2026-11-15_100504` retired as `0_SUPERSEDED`.** New module `gemini/source/lt_designs/mainst.py` (a New England brick downtown: 3-4 storey masonry blocks, iron or granite shopfronts, stone lintels / Italianate hoods / pediments, oriel, canted bays, a Queen Anne turret, mansards, brick and parapet gables, square and octagonal corner towers, backs stepping down in brick with fire escapes, porches and a skylit stockroom). Roster MAIN_STREET rewritten (same 10 names, signs, corners, households), `MODULE['ZM1'] = 'mainst'`, Brick085/Brick094/Greystone in PALETTE_OF. `lt_kit.opening` gained `trim['hood']` ('cap' | 'pediment') for masonry windows. Backups `*.pre_mainst.*` (lt_roster, lt_kit, RULEBOOK, HANDOFF). Watch: ProvisionsMansard's Greystone reads as rubble rather than ashlar; the square corner tower counts as a roof level, so that corner has a 2-storey back range only.
  2. **Shore Rows (ZL1) rebuilt as painted ladies (Direction B, the author 2026-11-17): BUILT, run `2026-11-16_183227` (100/100 PASS, reviews filled, sheets in `runs/2026-11-16_183227/sheets/`). the author OK'd the sheets 2026-11-17 01:45Z; STAGED as `generator/imports/1_READY_GEMINI_2026-11-16_183227_100`. The old ZL1 imports (1,930 items: 100 folders + 1,830 files, all 20 old names incl. the old CornerTripleLeftCorner) moved out of ImportedData to `CS2Planner\backups\ImportedData_pre_shorerows` (game closed). Waiting for the author to import, then `newfrance_setup.py`. IN GAME 2026-11-17 (evening): the author imported Shore Rows and the Federal set (checked: ZL1 100 folders + 1,830 files, ZP1 48 + 894, ZP2 32 + 576, one per building, no duplicates); `newfrance_setup.py --dry-run` then real: 350 set up, 0 warnings, ZL1 100 / ZP1 48 / ZP2 32 in their zones. Spot checks: CaptainsHip 2x4 and GreekTemple 3x6 Prestige Cottages hh 1; GreekTwin 4x6 Cottage Flats hh 10, BrickRow 3x5 hh 6; QueenAnneTurret 1x4 Low Residential hh 2, front access; CornerStickLeftCorner 1x4 hh 3, corner access. READY folders `183227_100` and `191827_80` filed in `2_PROCESSED`; the old ZL1 / ZP1 / ZP2 imports `2026-11-15_085159_100`, `121005_48`, `160635_32` retired as `0_SUPERSEDED`.**
     - New module `gemini/source/lt_designs/shorerows.py`; `MODULE['ZL1'] = 'shorerows'`. 20 new DESIGNS in `lt_roster.py` (new names, so the old ZL1 folders in ImportedData must be moved out before the import), households kept (nine 2s, nine 3s, two 4s) via `hh=`.
     - Each rear is its own sequence of `E(...)` wings (gable / cross / shed, LOW 3.55 or MID 6.7 eave, piazzas) and a `C(...)` carriage house (across / gambrel / hip, cupolas), each with its own roof material.
     - Atlas: `Fishscale`, `DiamondBand` (split from RoofGreen / CourtGlass) and `BoardBatten` tiles, painted in `lt_atlas.py` (`paint_victorian`). They tint as colour 0 (R mask), the accent; Clapboard is colour 1, TrimWhite colour 2. New `victorian` palette: 12 (accent, body, trim) sets, all ZL1 designs use it. Other zones keep colour 0 white.
     - Audit lessons: roof-level runs break at a ridge cap that sits off a 0.25 m grid line (corner houses use `ci=.5` so the ridge lands on one); a cross-gabled wing between a taller wing and the carriage house counts its yard rake as an eave level; piazzas now run tight from the house or back porch to the next piece (no yard slits).
     - Backups: `*.pre_shorerows.*` (lt_atlas, lt_roster, atlas_layout.json, atlas_template folder, HANDOFF).
     - Next after the author's OK: stage, move the old ZL1 out of ImportedData, then Direction A (Federal / Greek Revival) for ZP1/ZP2.
     - RULEBOOK edits made 2026-11-17 on the author's OK (ZL1 Zones row; rule 20 ZL1 exception). Backup `RULEBOOK.pre_shorerows.md`.
  2b. **Prestige Cottages (ZP1) and Cottage Flats (ZP2) rebuilt as the Federal / Greek Revival harbour town (Direction A, the author 2026-11-17): BUILT, run `2026-11-16_191827` (80/80 PASS, reviews filled, sheets in `runs/2026-11-16_191827/sheets/`). the author OK'd the sheets 2026-11-17 02:28Z; STAGED as `generator/imports/1_READY_GEMINI_2026-11-16_191827_80`. The old ZP1/ZP2 imports (1,580 items: 80 folders + 1,500 files, the 16 Bar Harbor / AC-avenue names) moved out of ImportedData to `CS2Planner\backups\ImportedData_pre_federal` (game closed). RULEBOOK ZP1/ZP2 rows and rule 20 exception edited (backup `RULEBOOK.pre_federal.md`). Imported and set up with ZL1, see item 2.**
     - New module `gemini/source/lt_designs/federal.py`; `MODULE['ZP1'] = MODULE['ZP2'] = 'federal'` (ZP3 stays on `cottage.py`). New PRESTIGE (CaptainsHip, BrickEndFederal, GreekTemple, WiscassetGambrel, ConnectedCape, FederalSquare, GreekPorch, BathMansion) and COTTAGE_FLATS (FederalDouble, BrickRow, GreekTwin, CapeDouble, HipDouble, GambrelDouble, BrickEndDouble, GreekFlats); households unchanged (ZP1 1, ZP2 `FLATS_HH`). New names, so at staging the old ZP1/ZP2 folders must be moved out of ImportedData.
     - Main kinds: side gable (brick ends, paired end chimneys), hip (widow's walk or belvedere), gambrel, cape, Greek temple front (0.5 m frieze, corner pilasters, side-hall sidelight door, a 1.5-storey side wing on wide lots), twin temples; doubles and a 3-house brick row. Fanlight or sidelight entrances on granite steps, porticoes where a LOW eave exists. Rear: LOW or MID ell (near / far / twin), optional woodshed, red or white BoardBatten carriage barn (gable / gambrel / cross, cupola, lofts) round a paved court.
     - New `federal` palette: (barn, body, trim) = barn red or white on BoardBatten, white / cream / straw / pale grey-blue / pale grey clapboard.
     - Fenced front yards from the brief were not built (rules 17 and 19); a lawn strip instead.
     - Audit lessons: open shutters reach ~1.04 m from a window centre (`sspread`: piers 1.3-1.8, bays 2.15-3.1 apart); a rear frieze level with an ell's eave ends flush on the ell wall (dropped there); an eave edge on the audit's 0.25 m ray-grid centres reads as a slit after the bake (barn overhang 0.4); baked LOD1 runs ~1.26x the build count, so LOD1 uses `lean="bare"` windows and no shutters; LOD0 dentils under the main eave lift the doubles over the density floor.
     - Backups: `lt_roster.pre_federal.py`, `HANDOFF.pre_federal.md`.
  3. **Corner pieces for the boardwalk** (ZC1/ZC2), like the LeftCorner pieces ZL1 and ZM1 already have, so a block end isn't a bare party wall.
  - Also: the LOD2 brick tile reads coarse at a distance (Cannery Row, the brick shops); the LOD2 shingle reads dark; the turret cones looked slim at 60 m. All of these wait on the author's in-game look.
- **Historic district colours (the author 2026-11-17, "laffy taffy"): DONE 2026-11-17.** `victorian` palette in `lt_roster.py` redone as 12 greyed period sets (sage, putty, stone, olive drab, slate blue-grey, oxblood, spruce, buff, warm grey, cream, lichen, umber; accent a shade off the body; trim cream / off-white / spruce / black). `federal` barn red greyed and straw -> pale buff. No re-bake or re-import needed: colours live in `colour_variations.json` and `newfrance_setup.py` rewrites each main mesh's ColorProperties, so I re-ran setup (game closed): 350 set up, colours on 350 meshes. Swatches `research/hdc/hdc_swatches.png`. Backups `lt_roster.pre_hdc.py`, `colour_variations.pre_hdc.json`, the 180 old ZL1/ZP1/ZP2 mesh prefabs in `CS2Planner\backups\ImportedData_pre_hdc_colours`.
- **Exchange Row, ZO1 (new office district, the author 2026-11-17 "do something newish"): BUILT, run `2026-11-17_061902` (32/32 PASS, reviews filled, sheets in `runs/2026-11-17_061902/sheets/`). NOT staged; waiting for the author's OK on the sheets.** New module `gemini/source/lt_designs/exchange.py`, roster `EXCHANGE_ROW` (SeamensSavings, CustomHouse, MerchantsExchange, MarineInsurance, CableOffice, SteamshipAgency, TrustCompany, GazetteBuilding) at 2x3/3x3/3x4/4x4, `exchange` palette. Beaux-Arts banks and offices: granite banking storey, limestone ashlar (`Dressed`), stone cornices and balustrades, copper (`TinGreen`) mansard / hip / dome / clock tower, bronze sashes, no white trim. Kit: opt-in `glazed` key on `lt_kit.loading_bay` (glazed arched windows). Backups `lt_kit.pre_exchange.py`, `lt_roster.pre_exchange.py`, `HANDOFF.pre_exchange.md`. At staging: add `ZO1` to `ZONE_KEY` and the `nonres` tuple in `newfrance_setup.py`; the author makes an Office Low clone. Proposed RULEBOOK wording (Zones row, rule 20 offices family) is in `ZONE_HANDOFF.md`, not applied.
- **`ZONE_HANDOFF.md` (2026-11-17):** one self-contained section per zone (ZL1, ZM1, ZP1, ZP2, ZP3, ZC1, ZC2, ZI1, ZO1) plus the common pipeline and preferences, so each zone can get its own thread (the author's request). Keep it in step with this file.

## cs2kit (reviewed 2026-11-24)

`C:\Users\<you>\CS2Planner\cs2kit\` is a pack-agnostic rewrite of this pipeline (preflight, atlas, bake, review, stage, setup, driven by `pack.json` and `atlas.json`). Its 6 unit tests and the demo pack's 6/6 bake pass. Lobstertown stays on `gemini/run.py` and `tools/newfrance_setup.py`: its 934 buildings use `lt_kit` modules and per-size stub scripts that cs2kit has no `pack.json` for, and porting them would need a full re-bake.
- **New packs and new small sets:** start in cs2kit (`init-pack`, then `preflight` before any bake).
- **Pre-check Lobstertown ideas:** a design written against `cs2kit.kit` can be checked in about 2 seconds without Blender.
- **Safety:** `cs2kit setup --pre-import` moves stale ImportedData copies to `CS2Planner\backups` and honors `--dry-run`, which matches the re-import rule above. Same go rules apply: no bake, stage or setup without the author's go.
