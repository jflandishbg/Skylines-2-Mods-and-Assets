# Lobstertown rulebook

These are the rules every Lobstertown building follows. Rules 1–16 came over from New France, so they include the classical proportion rules from Vignola, the École des Beaux-Arts, Haussmann's Paris building rules and the American row-house pattern books. Rules 17–27 are lessons from building Lobstertown (Shore Rows, triple-deckers, Main Street, Prestige Cottages, Cottage Flats, Grand Hotels, Boardwalk, 2026-11-14/15), mostly from things the author spotted in game. Everything is in our own words and numbers.

Consolidated 2026-11-15; zones and staging folders added 2026-11-15 (backup `RULEBOOK.pre_boardwalk.md`). The New France version is kept as `RULEBOOK.pre_consolidate.md`.

**How they are enforced.**
- **While building:** the kit (`source/nf_kit.py`, `source/lt_kit.py`) checks rules 1–10 through `source/nf_rules.py`. A break fails the bake, and the report names the rule, the wall and the numbers.
- **After the bake:** `source/audit_gemini.py` checks slits, eave heights, blank walls, flush faces, the lot bounds and the triangle budget.
- **By eye:** the rest are checked in the 8-point `_REVIEW.md` against the preview, before anything is staged.
- **"Where it is checked":** the tables below say which of these covers each rule. "Review" means only the eye catches it.

**Deliberate exceptions.**
- A design may waive a rule, but only by writing down why, e.g. `waive={"balance": "side-hall row house"}`. Each waiver is printed in the bake log. A waiver without a reason is not allowed.
- **Standing waiver:** Shingle Style is asymmetric on purpose, so every Lobstertown front waives rule 6 (`balance`) with that reason.

**Adding rules.** When the author spots something in game, it becomes a new numbered line here and, where it can be measured, a check that fails the bake. It never becomes a one-off patch. His eye in game outranks every rule.

## Walls and windows

| # | Key | Rule | Numbers |
| --- | --- | --- | --- |
| 1 | `corners` | A corner needs solid wall. The wall between the last opening and a corner must carry the corner visually. | Outside corner with quoins: at least the window width, and at least 0.85 m (long quoin) + lintel overhang + 1 cm. Outside corner without quoins: 0.6 × width, at least 0.6 m. Inside corner: 0.6 × width, at least 0.6 m. Party-wall end: 0.5 × width, at least 0.6 m (a shop at a party end: 0.6 m). |
| 2 | `rhythm` | Bays are evenly spaced, with real wall between openings. | Bay centres even within 30%. Clear wall between two openings: at least 0.7 × the narrower, at most 2.5 × the wider (2.25 m for 0.9 m windows, 2.0 m for 0.8 m). Pairs involving a shopfront are skipped. |
| 3 | `axes` | Openings stack on vertical axes, and the door sits on one of them. | The door's bay must be one of the wall's bays. |
| 4 | `shape` | Windows are upright. | Height ÷ width: main storeys 1.4–2.4; top storey 1.2–2.4; low storeys (`low=`) 0.9–1.6; lucarnes 1.0–2.0; doors at least 1.25. |
| 5 | `order` | Storeys get less important going up; windows never grow taller going up. | Above the ground floor, each floor's window height ≤ the one below + 0.1 m. |
| 6 | `balance` | A formal front is symmetrical: odd number of bays, door in the centre. | Standing Lobstertown waiver (Shingle Style is picturesque). Also waived for side-hall rows, shopfronts, garden and kitchen doors on service courts. |
| 7 | `glass` | Walls are mostly solid. | Openings 10–45% of any wall of 20 m² or more that has windows. |

## Trim

| # | Key | Rule | Numbers |
| --- | --- | --- | --- |
| 8 | `clearance` | No two pieces of trim touch. A band crossing an opening is cut around it. A surround never meets the next one, the floor above's, or a shop fascia. | Window surround = sill (14 cm below) to cap (34 cm above), plus the casing each side. A shopfront's surround is the shop ±0.36 m wide, from 0 to head + 0.66 m. |
| 9 | `cornice` | The cornice grows with the building. | Street fronts: projection H/40 to H/20. Other walls: H/80 to H/15. |
| 10 | `dormers` | Dormers stand on the window axes below, or on the centre line, and are narrower than the windows below. | Centre within 5 cm of a bay or the wall centre. Hay-loft and cottage dormers are placed over the bays below by the design code. |

## Massing and roofs

| # | Rule | Where it is checked |
| --- | --- | --- |
| 11 | One composition. Blocks touch or overlap with no slits; wings butt in or step down whole storeys. **Three eave heights at most** (party-wall tops don't count). | Audit: slits, eave heights (see "How the audit sees" below) |
| 11b | **Château crowns** (the author 2026-11-16, ZC2 Boardwalk Palaces and ZP3 Grand Hotels only). A pavilion or turret whose plan is under 150 m² is part of the crown, not an eave level: towers may cluster at different heights. The main body still keeps three eave heights at most. | Audit (ZC2/ZP3): a cell is crown when the connected mass standing at or above its height covers under 150 m² in plan; crown cells link eave runs but never set a level. Keep crown blocks apart with visible roof between them, or they merge into one big block |
| 12 | Chimneys stand on party walls or the ridge, in pairs or evenly spaced, and rise clear of the roof. | Review |
| 13 | Every side the camera sees is designed. Only declared party walls on the lot line may be bare. | Audit: blank walls; review |
| 14 | the author's look: one stand-alone building, broad top. Hôtel Brique et Pierre is the quality bar. | Review |

## Construction (the author, 2026-11-14: "architects don't leave gaps in the roof")

| # | Rule | Where it is checked |
| --- | --- | --- |
| 15 | **Closed construction.** Every roof slab, porch roof, cap, cupola and turret cone is a closed solid that seals onto the wall below. Nothing is see-through from any angle, including the party side of a house standing with no neighbour. | Kit: `lt_kit.roof_check` fails any open edge |
| 16 | **Materials run continuously.** No grid of tile seams: every atlas tile has a gutter filled with its own wrapped pattern; swapped slots carry their own metres per LOD (1.2 / 4.8 / 174). | Runner: `lt_atlas.check_gutters` fails the run before the bake |

## The lot and the set (the author's calls, 2026-11-14/15)

| # | Rule | Where it is checked |
| --- | --- | --- |
| 17 | **Fill the lot.** Build to 0.6 m off the rear line. Empty ground inside a lot is dead space Placemaker can't use. Detached houses keep only a narrow side yard (1.2 m) and a front lawn strip; anything deeper is filled with a joined wing, court and carriage house (the Toronto big-house model, not the Prestige yard). | Audit reports `occupied_pct`; review |
| 18 | **Level 1 only.** "There is no L2." A bigger or denser version is a new set of designs in a new zone, not a level. | Setup writes level 1 |
| 19 | **Stand-alone, nothing loose.** No props, benches, water, flags, outbuildings or loose spires (flagpoles, weathervanes, free-standing spires) in the mesh. Placemaker dresses the lot. A needle cone that caps a turret is part of the roof, not a spire (the author 2026-11-16), and must be a closed solid (rule 15). | Review |
| 20 | **Each district has its own material family** (the author 2026-11-15: the sets looked "very samey with everything else"; he wants variety between districts, not more of the same). Within a family, colours stay muted and toned toward grey (no pastels). The families: **residential** (ZL1, ZP1, ZP2, ZP3) weathered grey shingle and clapboard, white trim, granite water table (except ZL1 since 2026-11-17: painted ladies in strong period colours; ZP1 and ZP2 since 2026-11-17: Federal painted clapboard in white, cream, straw or pale grey-blue, brick ends and rows, red or white barns; see Zones); **industrial** (ZI1 Cannery Row) granite work storey with open arched or square loading bays, red/brown/buff brick above, granite lintels, sills, string courses and gable copings, dark slate, no white trim (two weathered board sheds keep the old waterfront in the set); **offices** (ZO1 Exchange Row) grey granite base, pale limestone ashlar, stone trim and cornices, green copper roofs, dark bronze sashes, no white trim; **commercial streets** (ZC1, ZM1) their own mix, chosen per set. A new set states its family before it is designed, and must not read as a recolour of another district. | Review: a side-by-side sheet of the new set against its neighbouring districts |
| 21 | **Variety from every side, the back included** (the author 2026-11-15: the cottages looked "samey, especially in the back"). The designs in a set must differ in mass and roofline, not only in colour or trim, as seen from the street, the rear and above. Give each design its own combination of the set's variant keys (roof type, cupola, dormers, stone base, wing side) so no two share a rear elevation. | Review: a contact sheet of every design's rear and aerial views, side by side, before the full bake |

## Detail lessons (from the bakes)

| # | Rule | Where it is checked |
| --- | --- | --- |
| 22 | **Nothing shares a plane.** Two faces that overlap in one plane flicker in game. Keep parts at least 3 mm apart. Specifically: step crossing trim bands about 8 mm apart in height; pull roof slab ends 4 mm in from a party line, and 12 mm for a roof that runs on under another; a box under a frieze stops 1 cm below the frieze top; don't build a zero-height wall (a "sliver" from the wing's eave to the same main eave), because its trim end caps land in the wing's frieze plane. | Audit: coplanar faces, with positions |
| 23 | **Mirror whole buildings, not parts.** Flipping a whole finished mesh (hand R) is safe. Flipping just part of one swaps which wall's corner boards and bands win at each corner where it meets the unflipped part, and they collide. To put a wing on the other side, build that part natively mirrored (each wall keeps its outward normal and swaps its start and end corners: `bwall`/`bgable`/`broof` in `cottage.py`). | Audit: coplanar faces |
| 24 | **Roofs run into each other, never through.** A wing roof running on into a bigger roof must die into its slope before that roof's ridge. If it can't, steepen the receiving roof (the carriage house pitches up to stand 0.5 m over the wing ridge). | Kit: an assert fails the build |
| 25 | **Every view on a budget.** LOD0 at most 45,000 triangles, LOD1 9,000, LOD2 1,000. A detailed sash window costs about 150 triangles at LOD0, so big buildings spend detail where it is seen: full sashes on the street front, one-over-one (`simple`) on sides, rear and back blocks; wider windows spaced further apart on back blocks. LOD1 windows are flat panes (`lean`), or bare panes on a frame plate (`lean="bare"`) on the biggest; LOD2 keeps the outline (end posts only on verandahs, no minor stacks). | Audit: triangle counts |
| 25a | **Towers get a bigger budget, sized by their skin** (Grand Hotels, 2026-11-15). The bake also demands at least 8 triangles per m² of outside surface, and a 12-20 storey tower has 5,500-10,000 m² of skin, so 45k can't hold one. Zones ZP3 (Grand Hotels) and ZC2 (Boardwalk Palaces) run LOD0 160,000 / LOD1 24,000 / LOD2 3,000 (set in `gemini_specs.py`). Two levers keep it there: full sashes up the whole street front (where the eye is), and `lite_above` windows on the sides, rear and court (a real recess, glass and one flat frame: about 18 triangles against 156). The bake cuts faces at every texture tile, so 1.2 m shingle costs about 3× what 4 m clapboard does on the same wall. | Bake: budget and density asserts |
| 25b | **Tower balconies stay inside the verandah.** Balconies on every floor project 1.5 m, inside the 2.6 m verandah and 0.6 m clear of the side walls, so seen from above the verandah keeps the front edge and the tower still has three eave heights (verandah, court block, tower). | Audit: eave heights |
| 26 | **Decals on the grid.** A sign plate or other decal must sit exactly on its atlas tile grid (planar UVs, origin at world 0), or the UV splits it. Mirrored corner pieces get no lettering, because the game mirrors them. | Review |
| 27 | **Tints only darken.** ControlMask channels R/G/B drive colours 0/1/2; colour 0 stays white. A base texture that should tint light must be lifted near white first (clapboard 236,234,228). | Runner: `check_tint` |
| 28 | **Windows need a room behind them** (the author 2026-11-16, from the Taffy Shop's false front). Every window opens onto enclosed space under the building's own roof: a storey, an attic under a gable, a dormer, a turret, a cupola or a monitor. Never onto sky, a roof slope or an open parapet. A false front over a one-storey shop gets windows only where the gable attic stands behind them (the middle of each gable), and boards, a sign or a painted panel elsewhere. A raised parapet step gets a panel, not a window. Boomtown fronts did sometimes carry sham windows, but in the game they read as a mistake from above and from behind. | Audit: half a metre behind the head of each pane, at three points across it, a ray straight up must meet the building; two misses fail the building |
| 29 | **Fronts meet the sidewalk** (the author 2026-11-18, from the service and landmark sets that sat 2 to 3 m back). A building's front wall, its foremost facade, stands within about 1 m of the lot front line, so the building meets the sidewalk. Porches, stoops, bays and cornices may project past it; setbacks and forecourts are not built into the mesh. | Dry run: measure the foremost facade against the lot front line; more than about 1 m back fails the building |

## How the audit sees (so designs don't trip it by accident)

The audit looks straight down on a grid. Some honest designs fail it by geometry accident, so design around these:

- **Eave heights:** the top of the building along its outline, on a 0.25 m grid. Steps under 0.4 m chain into one run, and a run needs 3 m of outline to count.
  - A **gambrel**'s steep lower slope must rise less than about 1.6 per 1 (Lobstertown uses 2.7 in 1.8). If it's steeper, each cell breaks the chain, and the upper rake counts as an extra eave.
  - A **main roof's front rake** left uncovered by a porch counts as a level. Give every front a full porch or bay. A stoop under 3 m doesn't count; a full door hood does.
  - Outline within 0.6 m of a **declared party line** is skipped. A barn ridging front-to-back then shows its rear rake as its own eave, so on party-wall lots, barns ridge across the lot.
- **Slits:** empty runs of 0.5–1.5 m between built cells on a 0.5 m grid (counted above 2 m).
  - Tuck a verandah roof into the tower it meets, or the gap in front of the tower's chamfer reads as a slit.
  - Keep overhang edges off grid-cell centres (cells sit at 0.25 m + n × 0.5 m). An edge exactly on a centre aliases into a slit, so use 0.5 m, not 0.45.
- **Blank walls:** vertical faces are grouped by plane; a plane of 30 m² or more with no glass near it fails. Since 2026-11-15 a plane must also be at least half solid across its extent, so a long verandah's posts, rails and deck edges (an open frame) don't read as a blank wall.
- **Bands count too (boardwalk, 2026-11-15):** the plane check catches long horizontal bands, not only walls. A shop fascia 47 m × 0.9 m above the glass, or a stockroom cornice and its crown 48 m × 0.5 m, fails on a 6-wide lot. Keep fascias shallow (tall shopfront glass under them), and leave crown mouldings off a cornice edge that butts a taller wall, where nobody sees them anyway.
- **Turret cones overhang:** an octagonal turret's cone eave ring reaches 0.32 m past its apothem. A corner turret's centre sits at `apothem + 0.34` from the side lot line, not `+ 0.02`.
- **Rails through posts:** on an upper deck the rail runs straight through the posts, so balusters can land exactly on a post face; the porch skips any baluster inside a post.
- **Rule engine:** doors above the ground floor, or glazed doors off the window rows, get bucketed as ground-floor openings and fail rules 2/3. Keep plain windows behind decks.

## Zones

Every set has a zone key. `lt_roster.py` lists the designs under each key, and `tools/newfrance_setup.py` (`ZONE_KEY`) turns the key into the zone's exact in-game name. Level 1 only (rule 18): a bigger or denser version is a new row here.

| Key | Zone name in the game (exact) | Clones | Set | Lots | Buildings |
| --- | --- | --- | --- | --- | --- |
| ZL1 | Lobstertown Low Residential | Residential Low | Shore Rows, second edition (`shorerows.py`): late-Victorian painted ladies (Carpenter Gothic, Queen Anne, Stick, painted triple-deckers). Steep gables, bargeboards, fishscale and board-and-batten in strong period colours with contrasting trim; towers small and wooden; every rear its own sequence of wings and carriage house | 1x2–1x6 | 100 |
| ZM1 | Lobstertown Mixed Main Street | Mixed Housing | Shops with flats above, painted signs | 1x2–1x6 | 50 |
| ZP1 | Lobstertown Prestige Cottages | Residential Low | Federal and Greek Revival harbour town, second edition (`federal.py`): Portland West End / Bath / Wiscasset 1800–1850 captains' houses (hipped with widow's walks, brick-ended, gambrel, capes, Greek temple fronts), painted clapboard, green or black shutters, granite steps; an ell to a red or white carriage barn round a court; 1 household | 2x4–3x6 | 48 |
| ZP2 | Lobstertown Cottage Flats | Residential Medium | Federal harbour town flats (`federal.py`): Federal doubles, brick rows, twin Greek fronts and double capes, 6–10 households | 3x5–4x6 | 32 |
| ZP3 | Lobstertown Grand Hotels | Residential High | 12–20 storey shingle towers, 40–70 households | 4x6–6x6 | 24 |
| ZC1 | Lobstertown Commercial Waterfront | NA Commercial Low Waterfront | Boardwalk Shops (rebuilt 2026-11-16, `shops.py`, "built up over time"): 8 designs, half brick commercial blocks (cast-iron or granite shop storey, corbelled or bracketed cornice, painted name; Penny Arcade, Fudge Kitchen, Bath Houses, Tintype Studio) and half painted clapboard false fronts in shop paint (Taffy Shop, Oyster House, Clam Shack, Kite Shop), 1-3 storeys, doors at grade off a plank walk; deep lots filled by a one-storey stockroom (shed, flat or gabled) | 1x2, 2x2, 2x3, 3x3 | 32 |
| ZC2 | Lobstertown Commercial Boardwalk | Commercial High | Boardwalk Palaces: 8 designs (Grand Arcade, Emporium, Music Hall, Roller Rink, Natatorium, Picture Palace, Ballroom, Seaside Market), 4–6 storeys behind a two-deck promenade arcade, corner turrets and lanterns | 4x4, 4x5, 5x5, 6x6 | 32 |
| ZI1 | Lobstertown Industrial Cannery Row | Industrial Manufacturing | Cannery Row: 8 designs. Six brick and granite works behind a granite quay (Sardine Cannery: side-ridge piles, cross-gabled pavilion, stack; Ice House: mansard with dormers, stair tower, warehouse behind; Ropewalk: side ridges, stair tower, warehouse behind; Sail Loft: brick gambrels; Boat Shop: gables with clerestory monitors, stack, warehouse behind; Cooperage: gambrel and gable, buff brick, stack) and two weathered board sheds (Smokehouse Row, Lobster Pound) | 2x4, 3x4, 4x4, 4x6 | 32 |
| ZO1 | Lobstertown Office Exchange Row | Office Low | Exchange Row (exchange.py): Beaux-Arts banks and offices, granite banking storey, limestone ashlar, stone cornices and balustrades, green copper mansards, hips, dome and clock tower, bronze sashes; backs in ashlar or buff brick with banking halls, stepped blocks or a light court | 2x3, 3x3, 3x4, 4x4 | 32 |

The first seven were imported and set up as of 2026-11-15. ZI1 was redone in brick and granite on 2026-11-15; its final run `2026-11-15_213023` (brick and granite at grade) was reviewed and staged on 2026-11-16, waiting for the author to create the zone and import. ZC1 was rebuilt as `shops.py` and re-staged on 2026-11-16 for a re-import over the old boardwalk shops. The brick works use opt-in kit keys in `lt_kit.py`: a `"bay"` opening kind (open loading bay), `masonry=` trim (stone lintel and sill instead of white casings) and `belt_mat=` (stone string courses). ZC1 is built by `lt_designs/shops.py`, ZC2 by `lt_designs/boardwalk.py` (`promenade=True`). Both are "Commercial" zones, so they get no households. ZI1 (`lt_designs/cannery.py`) is green industry like New France's Z10: each stub carries a `PRODUCT` line (Food, Textiles, Vehicles or Furniture), staging copies it into `designs.json`, and setup lets the building make only that product.

## Process

1. **Design:** a design module (`lt_designs/*.py`) plus roster entries (`lt_roster.py`). Full sets every time, no pilots.
2. **Test:** bake one sample size per design (`run.py <names>`). Fix failures at their cause, then check a rear-and-aerial contact sheet for rule 21.
3. **Full bake:** all sizes in ONE run, so they share one texture set (owned by the run's first `NA_LT` building).
4. **Review:** fill each `_REVIEW.md` from its preview (8 checks, `Verdict: PASS`).
5. **Stage:** `run.py --stage runs/<stamp>` copies every building that passed the checks and has `Verdict: PASS` into `generator/imports/1_READY_GEMINI_<stamp>_<count>/`, writes its `IMPORT-LIST.txt`, and registers each building in `GPT_INBOX/gemini/designs.json` under its zone key. Buildings without a PASS review are left out.
6. **Zone key:** add it to `ZONE_KEY` in `tools/newfrance_setup.py` and add a row to the Zones table above. A zone that sells goods must have "Mixed" in its name. A zone with "Commercial" in its name gets no households (ZC1, ZC2).
7. **Re-imports first:** if the set replaces an older import, move the old files out of `%USERPROFILE%\AppData\LocalLow\Colossal Order\Cities Skylines II\ImportedData` into `CS2Planner\backups\`, grouping them by base name (strip `.bak`/`.cid`), because setup-edited files carry later timestamps.
8. **the author's part:** he makes the zone in the editor (exact name from the Zones table) and imports the `1_READY_*` folder.
9. **Setup:** with the game closed, run `newfrance_setup.py --dry-run`, check every building lands in the right zone, then run it for real. Spot-check one prefab's level, lot, access, zone ID and households (`m_ResidentialProperties`).
10. **File it:** move the `1_READY_*` folder into `generator/imports/2_PROCESSED/`. A READY folder that a newer bake replaces before import is renamed `0_SUPERSEDED_<stamp>_<count>` and stays in `generator/imports/`. Only sets waiting for the author's import should be sitting as `1_READY_*`.
