# Cascadian League: project brief (Claude + Gemini)

A new Cities: Skylines II building pack in Hanseatic-Showa timber brutalism. It lives in `C:\Users\<you>\CS2Planner\cascadian_league` and nowhere else.

Written by Claude on 2026-11-13, correcting Gemini's first draft. the author is not a programmer: keep explanations in plain language, ask him planning questions, never hand him code to write.

## 0. Ground rules
- **New France comes first.** New France (`C:\Users\<you>\CS2Planner\NewFrance`, "Paris on the Delaware", ~1,180 buildings) is mid-way through its second pass (rounds R23–R36). This pack never slows that down.
- **Read New France, never write it.**
  - Nothing in `NewFrance\` is edited, moved or reorganised for this pack.
  - Tools this pack needs are **copied** into `cascadian_league\pipeline\` (see section 5).
  - No shared-core refactor until both packs are stable and the author agrees.
- **Cost.** the author pays per use and is cost-sensitive.
  - Price every batch before baking: model count and roughly how many sessions.
  - No subagents, no workflows, no paid API calls.
  - Full sets, no pilots, once the first priced batch (section 8) has been approved.
- **The game.**
  - the author imports; Claude never does.
  - Claude touches the game's `ImportedData` only with the game closed.
  - Deletions go to the Recycle Bin only.
  - At most 120 buildings per import batch.

## 1. Who does what
| | Gemini | Claude |
| --- | --- | --- |
| Design | Concept art, style guide, orthographic elevations and plans, the catalogue (which buildings, which zones, how many) | Turns the catalogue into build specs |
| Textures | Paints the texture sheets to the region map in section 4 | Lays out the region map, wires the UVs, checks the sheets load |
| Geometry | Draws to the datums in section 3 | Writes the Blender builders, bakes, audits, previews, stages imports |
| Facts about the files | Asks Claude, never guesses | Reads the files and answers |

**Handoff files** (both models read and write these; nothing important lives only in a chat):
- `specs\datums.yaml`: the numbers in section 3. Claude owns it; Gemini proposes changes.
- `specs\catalogue.yaml`: one row per design. Gemini owns it; Claude checks it against section 3.
- `reference\`: Gemini's drawings, named `<Design>_front.png`, `<Design>_plan.png`, etc.
- `textures\`: Gemini's painted sheets, named to section 4.

**Drawings are for intent, not measurement.** Claude builds from the numbers in `catalogue.yaml` and `datums.yaml`, never by measuring pixels. Put a dimension on a drawing only if it is also in the YAML.

## 2. What the game needs (learned on New France)
These are facts proven in the author's game, not preferences.
- **Origin at the lot centre.**
  - The model's (0, 0, 0) is the centre of the lot at ground level, not the front edge.
  - A lot W cells wide and D cells deep spans x −W·4 … +W·4 and y −D·4 … +D·4 metres.
  - The **lot front (street) is at y = −D·4**.
  - The validator rejects any vertex more than 2 mm outside the lot, on any side, in any detail level.
- **Axes.**
  - Blender: +X right, +Z up, the street toward −Y.
  - FBX export: forward −Z, up Y. This is what New France ships with.
- **Lot sizes.**
  - 8 m cells.
  - Zoned widths 1–6 cells; depths 2–6 cells.
  - Name pattern: `CL_<Design>[B|C]_L<level>_<W>x<D>`, for example `CL_KontorArcade_L1_2x4`, with colourway A unmarked and B or C added. New France uses `NA_PdD…`. The prefixes must never overlap.
- **Files per building**, one folder each:
  - `<name>.fbx`, `<name>_LOD1.fbx`, `<name>_LOD2.fbx`: three detail levels, one mesh each;
  - `<name>_Win.fbx`, `_LOD1_Win.fbx`, `_LOD2_Win.fbx`: the window glass that lights at night, as a separate mesh;
  - 15 texture images (section 4), or a `settings.json` pointing at a shared owner's images.
- **No coplanar faces.**
  - Two faces on the same plane flicker in game. Every touching part is offset by a few millimetres.
  - Trim (cornices, sills, signs) projects past the wall line, so the wall sits back far enough for the trim to stay inside the lot.
  - **The datums below are design targets. The builders add the millimetre offsets.** A model 3 mm off a datum is correct, not an error.
- **Triangle budgets** (close / mid / far):
  - 45,000 / 9,000 / 1,000;
  - at least 8 triangles per m² of the close-up model, so nothing looks blank.

## 3. Datums (`specs\datums.yaml`)
```yaml
frame:
  origin: lot centre, ground level        # NOT the front edge
  street_side: -Y                          # lot front line at y = -D*4
  units: metres
  fbx_export: {forward: -Z, up: Y}

grid:
  cell: 8.0
  bay: 4.0                                 # 2 structural bays per cell
  lot_widths_cells: [1, 2, 3, 4, 5, 6]
  lot_depths_cells: [2, 3, 4, 5, 6]

lot_edges:                                 # measured inward from the lot lines
  front_wall: 0.30                         # street wall 0.30 m inside the front line
  side_and_rear_keep_in: 0.25              # nothing closer than 0.25 m to the side or rear lines
  party_wall_thickness: 0.40               # inside the keep-in, not on the line

vertical:                                  # z, metres, finished targets
  plinth: [0.0, 4.0]                       # board-formed concrete / basalt base
  level_1: [4.0, 7.5]
  level_2: [7.5, 11.0]
  level_3: [11.0, 14.5]
  podium_cornice: 14.5                     # street-wall line for medium, mixed-use and high density
  roof_gable_zone: [14.5, 20.5]            # 45-degree default
  tower_storey: 3.5                        # above 14.5 each storey steps back 2.0 m from the street wall

arcade:                                    # medium / mixed / commercial street fronts
  outer_piers: {depth: 0.6, width: 0.6, spacing: 4.0}   # solid concrete or masonry
  shopfront_recess: 2.5                    # shopfront 2.5 m behind the street wall
  soffit: 3.6
```

**Setbacks.** the author's standard since 2026-11-13 for New France: buildings go to the curb and fill the lot, with no front gardens and no dead zones. **This pack follows the same standard unless the author says otherwise.**
- So Gemini's 4 m front moss garden for low density is out by default.
- If the author wants it for this pack, it goes in as a building-owned front court enclosed on all sides, or it is Placemaker landscaping, never empty lot.
- That is the author's decision; ask him in plain words.

## 4. Materials and texture sheets
Each building has **one material**, painted from **one shared texture sheet** per atlas owner. A few buildings own a sheet; the rest point at it through `settings.json`. That is how all of New France works in game. Six separate material slots per building is an untested path, with more draw calls.

**The six looks stay. They become regions of the sheet:**

| Region | Look |
| --- | --- |
| BasaltConcrete | Board-formed grey concrete / dark basalt plinth |
| ShouSugiBan | Matte black vertical charred cedar |
| DouglasFir | Warm amber glulam posts, lintels, diagrid, eaves |
| OxidizedCopper | Patina-green standing-seam roofs, rain chains |
| ClinkerBrick | Dark red-purple stepped-gable brick |
| ShojiGlass | Translucent grid glazing: dark by day, 2700 K warm at night |

Each sheet has 5 maps at 3 detail levels: 15 images.

| Map | Close | Mid | Far |
| --- | ---: | ---: | ---: |
| BaseColor, Normal, MaskMap, ControlMask, Emissive | 4096² | 2048² | 1024² |

- File names: `<owner>_BaseColor.png`, `<owner>_LOD1_Normal.png`, and so on.
- Claude writes `specs\atlas_layout.yaml` (pixel rectangles per region) before Gemini paints. Gemini paints inside those rectangles only.
- **Night lighting** comes from the separate `_Win` glass mesh and the Emissive map. The Shoji glass glows there, not in a sixth material.
- Colourways A, B and C swap regions on the same sheet. They are not new materials.

## 5. Pipeline (copied from New France, adapted here)
Copy from the latest New France round, currently `NewFrance\GPT_INBOX\2026-11-13_round24\source` and `round27\source`, into `cascadian_league\pipeline\`:

| Tool | Job |
| --- | --- |
| `bake_r12.py` | Detail ladder, budgets, density, coplanar check, export, journal |
| `fill_lot.py` | Fills any open lot behind or beside the main building |
| `audit_r24.py` | Bounds, curb, occupancy, one island, nothing floating, no props |
| Validator (`pilot_core.validate`) | ±2 mm lot bounds |
| Preview renderer and contact sheet (`full22.py`, `fsheet.py`) | Previews for checking the look. These live in `C:\Users\<you>\AppData\Local\Temp\claude_swap\`, a temp folder Windows can clear: copy them first. |

Then strip the New France names and atlases.

**The kit is code, not files.** `Base_Arcade_4m`, `Upper_Bay_3.5m`, `Corner_Diagrid` and `Roof_Gable_Stepped` / `Roof_Karahafu` are Python builder functions. Each building calls them and bakes into the single meshes the game wants. Do not export kit pieces as separate FBX modules: the game can't use them, and they add a step that can drift.

Blender 5.2: `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`. Python: `C:\Users\<you>\AppData\Local\Programs\Python\Python313\python.exe`.

## 6. Standing rules carried over from New France (the author's rules)
- **Stand-alone:** nothing detached, no outbuildings, no water, `props: []`. Placemaker does landscaping. No benches.
- **Nothing hangs on posts.**
  - Thin timber posts may carry a roof, never a room.
  - Rooms stand on walls to the ground or on solid piers at least 0.6 m.
  - Corbelled projections are at most 0.6 m.
- **No free-standing thin structures with windows.**
- **Silhouette:** broad tops, no spires. A stepped gable or a karahafu is fine; a needle isn't.
- **Every building passes the audit before staging**, with previews checked by eye.

## 7. Game setup
- **Zones.** the author creates the pack's zones in the editor. Claude needs their exact internal names before writing setup.
- **Setup script.** This pack gets its own setup script modelled on `NewFrance\tools\newfrance_setup.py`. It must not edit the New France one.
- **Zone mapping.** Setup maps buildings to zones from `designs.json`, so every staged batch ships one, with `zone_key` and `households` per building.

## 8. First steps (in order)
1. Gemini: style guide and `specs\catalogue.yaml` for a **first priced batch** (suggest 12 designs × 3 colourways). Each row has the design name, zone, lot sizes, storeys, roof, arcade yes/no and a one-line signature.
2. Claude: check the catalogue against section 3, write `datums.yaml` and `atlas_layout.yaml`, copy the pipeline, and price the batch for the author.
3. the author: approves the price and answers the setback question.
4. Gemini: paints one texture sheet to the layout.
5. Claude: writes the four kit builders, bakes the batch, audits, previews, stages.
6. the author: imports and reviews in game. Only then plan the full 350-building catalogue, in batches of 120 or fewer.
