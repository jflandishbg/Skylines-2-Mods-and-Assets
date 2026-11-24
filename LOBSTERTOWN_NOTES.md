# Lobstertown: notes for future ideas

*Written 2026-11-18. Full pipeline steps: `Lobstertown\AI_HANDOFF.md`. Zone detail: `Lobstertown\ZONE_HANDOFF.md`. Rules: `Lobstertown\gemini\RULEBOOK.md` (do not edit without the author's OK).*

## Zones built (key, name, look)
- **ZL1 Shore Rows**: painted Victorian / Carpenter Gothic rowhouses, 1x2 to 1x6, each with its own rear.
- **ZM1 Main Street**: brick and shingle mixed-use blocks (reworked 2026-11-16).
- **ZP1 Prestige Cottages / ZP2 Cottage Flats**: Federal / Greek Revival doubles, plus shingle Coastal Inns in ZP2.
- **ZP3 Grand Hotels**: big château-style oceanfront hotels, 4x6 to 6x6. **ZC2 Boardwalk Palaces**: 4 to 6 storey casino / bathhouse / palace blocks.
- **ZC1 Boardwalk Shops**: low waterfront shops (48 incl. corners).
- **ZI1 Cannery Row**: brick and shingle works with cupolas and monitors.
- **ZO1 Exchange Row**: brick and stone bank / office blocks.
- **ZS1 Service buildings (11)**: fieldstone and shingle. Garbage = decorative barn plus vanilla incinerator. Powerhouse = untuned Battersea fuel plant.
- **ZH1 Harbour Hill (26)**: approved in game.
- **Landmarks (5)**: Siren Theatre, Seahorse Carousel House, Lobstermen's Lodge, Tidewater Aquarium, Exhibition Hall. Plain ploppables with gaudy sea-creature ornament.
- Zone key registry: `GPT_INBOX\gemini\designs.json`; game zone names: `ZONE_KEY` in `tools\newfrance_setup.py`.

## Town palette (all assets)
Blues and navies (soft slate, watery grey to navy, deep indigo). Whites and creams (crisp white, alabaster, cream for trim, beadboard, walls). Driftwood and sand (greige, taupe, weathered tan). Muted greens and sage (seafoam, grey-green, marsh grass). Heritage accents on doors and shutters only: weathered buoy red, rust brown, charcoal black. Zones stay distinct through different mixes. Swatches: Skylines project files, `palette\coastal_swatches.png`.

## Design rules the author cares about
- Each zone looks distinct from the others. For château / grand sets keep the materials, push form and grandeur.
- Entrances at street level. Main front wall within about 1 m of the sidewalk (rule 29).
- High lot coverage, 70% or more. the author dislikes big empty yards.
- Every window needs a room behind it (rule 28).
- LeftCorner only; the game mirrors it. No RightCorner, no lettering on corners. (Antigravity found 7 explicit RightCorner designs in ZL1 and ZM1 from the 2026-11-18 roster expansion. Check them in game.)
- Small towers or pavilions under 150 m² count as crown; needle cones on turrets are fine; hotels use lighter windows above the 10th floor (160k tri cap kept).
- the author imports in game himself. Before a replacement set goes in, move that zone's old ImportedData to `CS2Planner\backups` (ZC1 once had 320 stale duplicates).

## Rejected
- **Motor Courts (ZP4)**: too much empty lot. Replaced in plan by Coastal Inns (3 to 4 storey shingle summer inns, 70 to 85% coverage); a Coastal Inns set is baked and waits for the author's go.
- **Landfills**: the author dislikes them. Garbage uses a barn look plus the vanilla incinerator.

## Open ideas
- Shipyard and cold storage (industry beyond Cannery Row; more clean trades: paper, timber, beverages, machinery).
- Sea Ranch style brutalist / modernist coastal set.
- Mixed-use avenue (Antigravity's ZM2 "Mixed Avenue") and Office High (ZO2 Harbour Exchange Towers).
- Main Street corners; also corner pieces for ZC2, ZO1, ZI1 and ZH1 (all bare party walls today).
- Cove Cottages fishing village (ZL2). Odd-depth fills for ZH1; 4-deep and 5-deep ZP3 and ZC2 variants.
- 16 service buildings lack menu icons.
- Details: `Lobstertown\antigravity\ZONE_AUDIT_AND_PROPOSALS.md`.

## Where things live
- Bake output: `Lobstertown\gemini\runs\<stamp>` (runs before 2026-11-17 are in `Lobstertown\_archive\old_runs`).
- Staged sets: `Lobstertown\generator\imports\1_READY_*`; finished sets: `2_PROCESSED`.
- Review reports: `Lobstertown\GPT_INBOX\<set> - review`.
- Old game files and superseded imports: `CS2Planner\backups`.
