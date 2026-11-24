# Pack Authoring Guide (`pack.json`, `atlas.json`, `designs/`)

## 1. `pack.json` Schema

```json
{
  "pack_id": "alpenglow",
  "title": "Alpenglow Metropole",
  "prefix": "NA_AG",
  "variation_group": "Alpenglow",
  "textures_roots": ["../../../Lobstertown/textures"],
  "palette": {
    "swatches": { "W1": [0.95, 0.95, 0.93], "Slate": [0.35, 0.40, 0.46] },
    "base_levels": { "clap": [0.92, 0.92, 0.89], "trim": [0.88, 0.88, 0.86] },
    "sets": {
      "chalet": [
        {"c0": "W1", "c1": {"swatch": "Slate", "base": "clap"}, "c2": {"swatch": "W1", "base": "trim"}}
      ]
    },
    "random": [2, 4, 5]
  },
  "zones": {
    "ZL1": {
      "game_name": "Alpenglow Low Residential",
      "kind": "residential",
      "base_zone": "Residential Low",
      "module": "chalet",
      "party_mode": "row",
      "budget": [45000, 9000, 1000],
      "density_floor": 8.0,
      "crown_allowed": false,
      "default_lots": [[1, 2], [1, 3]],
      "expected_lots": [[1, 2], [1, 3], [2, 3]],
      "households_by_lot": {"1x2": 2, "1x3": 3}
    }
  },
  "roster": [
    {
      "design": "ChaletRow",
      "zone_key": "ZL1",
      "display_name": "Alpine Timber Rowhouse",
      "description": "Steep-eaved chalet rowhouse.",
      "palette_key": "chalet",
      "params": {"storeys": 3}
    }
  ]
}
```

### Valid `zone.kind` Values
- `residential`: sets `m_ResidentialProperties` to `households` (from roster or `households_by_lot`).
- `mixed`: sets `m_ResidentialProperties` and copies `m_AllowedSold` from the zone's `ZoneProperties` in `ImportedData`.
- `commercial` / `office`: sets `SpawnableBuilding` (level 1) with no households.
- `green_industry`: sets `m_AllowedManufactured` to `CLEAN_PRODUCTS[product]` and `m_SpaceMultiplier` (default `8`). Requires `"product"` on each roster entry.
- `service` / `landmark`: wires service components (`fire`, `police`, `hospital`, `school`, `elementary`, `post`, `landmark`, `park`, `water`), spawn markers, invisible car paths, `.loc` display name, and 512×512 transparent thumbnail.

---

## 2. `atlas.json` Schema

- **`tiles`**: list of packed rectangles:
  - `key`: material name passed to `Mesh.facing(..., mat)` and `style(...)`.
  - `kind`:
    - `scan`: reads `*_Color`, `*_NormalGL`, `*_Roughness`, optional `*_AmbientOcclusion`/`*_Displacement`/`*_Metalness` from `source` inside `textures_roots`. Optional `target_rgb`, `desat` (`0..1`), `courses` (shingle overlay).
    - `flat_paint`: matte/satin painted surface (`color`, `smoothness`, `metalness`).
    - `shingle_courses`, `shingle_fishscale`, `shingle_diamond`, `board_batten`, `stucco`, `standing_seam`: procedural PBR tiles with normals, AO, and smoothness.
  - `px`: `[width, height]` inside `4096²` (snapped to multiples of 4 so LOD1/LOD2 stay integer-aligned).
  - `metres`: `[w_m, h_m]` real-world repeat tile size at LOD0 (`lod1_metres` defaults to `2x`, `lod2_metres` defaults to `[174, 174]`).
  - `tint_channel`: `0` (R), `1` (G), `2` (B), or `null` for `ControlMask`. Use `lift_target_rgb: [236, 234, 228]` on tinted scans because CS2 color multiplication only darkens.
- **`signs`**: list of painted signboards (`key`, `text`, `board`, `ink`, `metres`, `px`). Automatically clamped in gutters (`Rule 16`) and supersampled 4×. Mount signs with `cs2kit.kit.sign_plate(m, x_slot, y, z_slot, sign_key)` so they stay aligned to `metres` (`Rule 26`).

---

## 3. Design Modules (`designs/<module>.py`)

Every design exposes:

```python
def build(lod, W=1, D=3, **variant):
    m, g = Mesh(), Mesh()
    # ... build geometry using cs2kit.kit / cs2kit.shapes / cs2kit.mesh ...
    finish(m, g)
```

Key architectural invariants enforced by `preflight` + `blender_bake`:
1. **Lot bounds (`±2 mm`):** `x` in `[-4W, +4W]`, `y` in `[-4D, +4D]`, `z >= 0`. Street is `-Y` (`y = -4D`).
2. **Rule 15 (closed roofs):** all roof slabs (`gable_roof`, `shed_roof`, `slab`, `pavilion_roof`, `dome`) must have zero open edges.
3. **Rule 22 (no coplanar overlap):** keep overlapping trim/bands separated by `E = 0.004` (4 mm).
4. **Rule 28 (no blind windows):** every window pane must have enclosed building structure above/behind it.
5. **Rule 29 (front setback):** main facade sits within `max_front_setback_m` (`1.2 m` default) of `y = -4D`.
6. **LeftCorner only:** never create `RightCorner` assets; CS2 mirrors `LeftCorner` automatically.
