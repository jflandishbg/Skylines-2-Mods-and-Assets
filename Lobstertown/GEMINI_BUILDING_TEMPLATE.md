# New France: building request for Gemini

Paste everything below the line into Gemini, then fill in **Part 3** for the building you want. One building per request.

---

You are designing one building for **New France ("Paris on the Delaware")**, a custom building pack for the game **Cities: Skylines II**. The city is a 19th-century French-American river town: Philadelphia brick and Paris stone, row houses, hôtels particuliers, Haussmann apartment blocks, river industry.

Your job is to write **one Blender Python script** that builds this building. Claude (another AI) will run it in Blender, add the game's textures, export it, check it and stage it for import. Follow Parts 1 and 2 exactly: they are measured facts about what the game accepts.

## Part 1: Technical rules (the game rejects the building if any of these fail)

### 1. Script format
- Plain Python for **Blender 5.2**, run headless with `blender -b --python building.py`.
- Use only `bpy`, `bmesh` and `mathutils`: no add-ons, no downloads, no image files.
- Deterministic: if you use randomness, seed it.
- Define exactly one entry point:
  ```python
  def build(lod: int) -> None:
      """lod 0 = close-up, 1 = mid distance, 2 = far. Creates two objects: 'Body' and 'Windows'."""
  ```
- Calling `build(0)`, `build(1)` and `build(2)` on an empty scene must each produce exactly two mesh objects:
  - **`Body`**: every solid surface (walls, roofs, trim, chimneys, steps).
  - **`Windows`**: only the glass panes that light up at night. Each pane sits 0.02 m behind its opening, inside the wall's reveal.
- Near the top of the file, two settings lines (the runner reads them):
  ```python
  ZONE = "Z1A"                   # the zone key from Part 3
  HOUSEHOLDS = 1
  PARTY_WALLS = ("left", "right")   # row houses only: sides that touch the neighbours. Use () for a free-standing building.
  ```
- **Name the script after the building**, e.g. `NA_PdDMaisonDuQuai_L1_1x3.py`. (the author saves it into `NewFrance/gemini/scripts/`.)
- At the end of the file:
  ```python
  if __name__ == "__main__": build(0)
  ```

### 2. Coordinates
- Units are metres.
- **The origin (0, 0, 0) is the centre of the lot, at ground level.** Not a corner, not the front edge.
- +X is to the right when you face the building from the street. +Z is up.
- **The street is on the −Y side.**
- The lot is W cells wide and D cells deep, each cell 8 m square. So the lot spans:
  - x from −4·W to +4·W;
  - y from −4·D (the street front) to +4·D (the rear line).
- **Every vertex of both objects, at every LOD, must lie inside the lot.**
  - Keep 0.25 m clear of the side and rear lines.
  - Keep 0.05 m clear of the front line.
  - This includes cornices, sills, eaves, chimneys and balconies: anything that projects counts.
- The ground floor sits at z = 0. There is no basement, and nothing goes below z = 0.

### 3. Triangle budgets
Count both objects together, after triangulation:

| LOD | Max triangles | What it should look like |
| --- | ---: | --- |
| 0 | 45,000 | Full detail: window reveals, sills, cornices, door surrounds, chimneys, roof dormers |
| 1 | 9,000 | Same silhouette and window grid; trim simplified to flat bands |
| 2 | 1,000 | Massing only: main volumes and roof shapes, no windows in `Body` |

- LOD 0 should use **at least 8 triangles per square metre of outer surface**, so no wall reads as a blank slab.
- All three LODs must have the **same outline and roofline**: the game swaps between them as you zoom.

### 4. Clean geometry
- **No two faces may lie in the same plane and overlap.** They flicker in game.
  - Where a part touches another (a cornice on a wall, a step on a plinth), offset it by at least 0.003 m, or cut the hidden face away.
- Normals face outward. No zero-area faces. No loose vertices or edges.
- Faces nobody can see (the bottom of the ground floor, the inside of walls) may be left out.

### 5. Materials
Assign every `Body` face a material **named exactly** from this list. Claude maps each name to the game's texture sheet. Don't invent colours or textures.

| Material | Use for |
| --- | --- |
| `Brick094` | Light red brick |
| `Brick085` | Mid red brick (default walls) |
| `Brick074` | Darker red brick |
| `Brick054` | Dark brown-red brick |
| `BuffBrick` | Yellow/buff brick |
| `BrownBrick` | Brown brick |
| `Greystone` | Grey rough stone walls |
| `Ashlar` | Smooth cut-stone walls |
| `Dressed` | Stone trim: quoins, lintels, sills, cornices |
| `StoneBase` | Plinth / ground-floor base course |
| `Rubble` | Rubble stone |
| `Render` | Plain stucco |
| `RenderOchre` / `RenderRose` / `RenderSage` | Coloured stucco |
| `Clapboard` / `ClapSage` | Painted wood siding |
| `Cream` | Painted trim, window frames |
| `Slate` / `SlateDark` / `SlateGreen` / `SlateBrown` | Pitched and mansard roofs |
| `Tin` / `TinFlat` / `TinOxide` / `TinGreen` | Metal roofs, flat roofs, flashing |
| `RoofGreen` | Green-painted roof |
| `Iron` | Balcony railings, cresting, ironwork |
| `Black` / `Green` / `Oxblood` / `GreyBlue` / `Mustard` | Painted doors and shutters |
| `Chimney` | Chimney stacks |
| `Deck` | Wooden porch floors |

`Windows` faces get one material named `Glass`.

UVs: none needed. Claude projects them per material.

## Part 2: Design rules (the author's standards for this city)

1. **It is one building.** Every part is attached; there are no outbuildings, sheds or free-standing walls.
2. **No props:** no trees, hedges, benches, lamps, fences, cars or people. A separate tool landscapes the lot.
3. **No water:** no pools, canals, fountains or boats.
4. **Nothing hangs on posts.**
   - A room, bay or oriel must stand on walls that reach the ground, or be a corbelled bay projecting 0.6 m or less.
   - Thin posts and columns may carry only a porch roof.
5. **Broad tops.** No spires, needles or thin towers. Domes, belvederes, mansards, hips and gables are fine.
6. **No blank walls.** (A side listed in `PARTY_WALLS` that stands on the side lot line is the one exception: the neighbour covers it.)
   - Any wall face over 6 m long or 6 m tall needs windows, blind arches, pilasters, string courses or a material change.
   - This applies to the sides and the back too: the game camera sees every side.
7. **Every side is designed.** The rear and the sides are real façades, simpler than the front but with windows and trim.
8. **Massing reads as one composition.** Wings and rear ranges share a cornice line or step down deliberately. Roofs meet cleanly, with no slivers or gaps between blocks.
9. **Doors.** The front door faces the street (−Y), on the ground floor, in the front wall.
10. **Front setback:** as Part 3 says.

## Part 3: This building (fill in)

- **Name:** `NA_PdD<DesignName>_L1_<W>x<D>` (example: `NA_PdDMaisonDuQuai_L1_1x3`)
- **Zone:** (Maisons Populaires / Maisons Patriciennes / Maisons en Rangée / Immeubles de Rapport / Appartements Haussmann / Rue Principale Mixte / Commerces Populaires / …)
- **Lot:** W = __ cells wide, D = __ cells deep
- **Storeys:** __ (plus attic or mansard? __)
- **Front wall:** at the street (0.3 m inside the front line), or set back __ m behind a front garden or forecourt
- **Party walls:** does it touch its neighbours on the left/right (row house), or stand free with windows on all sides?
- **Style and look:** (a few sentences, e.g. "Philadelphia brick row house, white marble steps recessed into the doorway, three bays, slate mansard with two dormers")
- **Materials:** walls __, trim __, roof __
- **Must have:** (e.g. corner turret with a broad conical roof; ground-floor shopfront; carriage arch)
- **Reference:** (attach a photo or drawing if you have one)

## Part 4: What to send back

1. **The script**, complete, in one Python code block.
2. **A self-check table** with these values. The figures you can't run, estimate and mark "est."

| Check | LOD 0 | LOD 1 | LOD 2 |
| --- | --- | --- | --- |
| Triangles (Body + Windows) | | | |
| Bounding box x min / max | | | |
| Bounding box y min / max | | | |
| Bounding box z max | | | |
| Materials used | | | |

3. **Three sentences** describing the building, as a passer-by would.

If anything in Part 3 is unclear or conflicts with Parts 1–2, **ask before writing the script.** Don't guess a dimension.
