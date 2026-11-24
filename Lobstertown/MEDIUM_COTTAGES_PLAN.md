# Next rung: Lobstertown Cottage Flats (Medium)

Prepared 2026-11-15, after the Prestige Cottages (Low) went in. the author: "the medium and high level residential zones should be larger versions of this." The precedent is Toronto's big houses: grand houses on 3x6/4x6 lots, cut into 6–10 flats, in a Residential Medium zone, filling the lot depth.

## What it is
The Bar Harbor cottage family, one size up. These are the summer palaces that became apartment houses: the same towers, verandahs, gambrels, cupolas and carriage houses, but the main house is 4 storeys and broader, and every block is flats.

| | Low: Prestige Cottages (done) | **Medium: Cottage Flats (next)** | High (later) |
| --- | --- | --- | --- |
| Lots | 2x4–3x6 | **3x5, 3x6, 4x5, 4x6** | 4x6 and up |
| Main house | 2–3 storeys, 13–15 m tall | **4 storeys (tower to about 22 m)** | grand-hotel scale |
| Households | 1 | **3x5: 6, 3x6: 7, 4x5: 8, 4x6: 10** | 12+ |
| Zone | Residential Low clone | **Residential Medium clone** ("Lobstertown Cottage Flats") | Residential High clone |

## How it builds (reuses `cottage.py`)
- **Sizes:** 4-wide constants for the main depth, cross gable and wing. 4-storey heights and windows already exist in the kit.
- **The back holds flats, not stables:**
  - The service wing becomes a 3-storey flats wing.
  - The carriage house becomes 3 storeys of flats over a carriage arch: the court still opens through to the rear.
  - Each block has its own entrance door on the court.
- **Eaves stay at 3 levels:**
  - verandah, 3.5 m
  - wing and carriage, 9.9 m
  - main eave, 12.9 m
- **New width for variety (rule 21):** 4-wide lots fit a **twin court**: wings down both sides, carriage block across the back, and a court in the middle. That's a new back shape, on top of the five back options already in the set.
- **8 designs × 4 sizes = 32 buildings.** That's 4 per design, one shared texture set, one run.

## What you'll do
Make the zone **Lobstertown Cottage Flats** as a clone of vanilla **Residential Medium**, then import. I run setup with the game closed, the same as always.
