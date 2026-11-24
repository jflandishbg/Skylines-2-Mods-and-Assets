# Château plan: Boardwalk Palaces (ZC2) and Grand Hotels (ZP3)

Prepared 2026-11-16 by Claude, for the author's OK. **Nothing is built yet.**

The idea is to keep every material as it is (shingle and clapboard, white trim, granite bases, oxide-red tin and dark slate) and change the form and the grandeur. The model is the Gilded Age resort château: Château Frontenac, the Banff Springs and the Mount Washington Hotel's towers, done in Maine shingle. Each design gets:

- **A cluster of towers at different heights**, not one even eave.
- **Steep pavilion roofs:** square hipped roofs at about 60°, with a ridge crest and finials.
- **Spired turrets:** the existing octagonal turrets rise higher and end in a needle cone, about 3× the apothem high (today's cone is about 2×).
- **A crown:** a dome, a lantern, or both, on the tallest block.
- **Stepped wings:** the lower ranges step up a storey or two toward the main block instead of meeting it at one height.

## Three things that need your call first

1. **Rule 11 (three eave heights at most) can't hold for a château.** Clusters of towers are the point. I'd add a **rule 11b** for ZC2 and ZP3 only:
   - Pavilions and turrets whose plan is under 150 m² each count as a crown, not as eaves.
   - The audit skips them. The main body still keeps three eave levels at most.
2. **Rule 19 says "no spires".** I read that as no loose spires, flagpoles or weathervanes. A needle cone that caps a turret is part of the roof: a closed solid (rule 15), like today's cones. If you agree, I'll write that into rule 19.
3. **Grand Hotels triangle room.** The tallest hotels are already near the 160,000 cap (Pennsylvania 6x6 measures 152,013 after the bake). Two ways to make room:
   - **(a) Recommended, no cap change.** Above the 10th storey, the street front switches from full sashes to light windows. The light windows are recessed glass with a frame, already used on the sides and rear. That saves about 17,000 triangles on a 16-storey 6x6. Up there the eye reads the crown, not the glazing bars.
   - **(b)** Raise the ZP3 LOD0 cap to 190,000 in `gemini_specs.py`.

## How the budget numbers were measured

| | |
| --- | --- |
| Raw counts | Taken from today's builds, at the biggest lot of each design (where the cap bites) |
| Baked counts | Raw × 1.6–1.75 at LOD0, × 2.0–2.2 at LOD1, × 1.0 at LOD2 |
| Calibration | Four of last night's FBX bakes, counted in Blender: Pennsylvania 6x6 152,013 / 16,536 / 1,536; Picture Palace 6x6 48,960 / 5,148 / 830 |
| Caps (ZC2, ZP3) | LOD0 160,000 / LOD1 24,000 / LOD2 3,000 |

Rough cost of each piece, baked LOD0 (LOD1 / LOD2):

| Piece | LOD0 | LOD1 | LOD2 |
| --- | --- | --- | --- |
| Square pavilion, 2 storeys over the eave, steep roof, 2 dormers | ≈ 4,500 | 850 | 40 |
| Spired turret raised 1 storey | ≈ 1,000 | 200 | 20 |
| Dome on an octagonal drum, plus lantern | ≈ 1,700 | 400 | 40 |
| Stepped wing (an extra step, cornice and roof) | ≈ 700 | 150 | 20 |

## Boardwalk Palaces (ZC2): 8 designs × 4 lots, row buildings 4–6 storeys

Today these are 35,000–49,000 baked against the 160,000 cap, so there is plenty of room. Here the towers can keep full sashes on their street faces.

The party walls stay bare and on the lot line. All the towers stand on the front and middle. The stepped wings step down toward the rear, onto the stockroom.

| Design | Today | Château massing | Baked LOD0 at 6x6, today → after | LOD1 / LOD2 after |
| --- | --- | --- | --- | --- |
| **Grand Arcade** | 5 st., gable-gambrel-gable, 2 turrets, lantern | Centre pavilion rises to 7 storeys under a steep pavilion roof with a lantern crown. Both corner turrets get spires and rise to 6½. The side cells become steep hipped mansards. | ~41k → ~52k | ~5.2k / ~0.85k |
| **Emporium** | 6 st., gables, left turret, store, lantern | An asymmetric keep: a square tower on the left at 8 storeys, the left turret beside it to 9 with a needle spire, and the right side stepping down to 5 under a hip. The store behind steps to 2. | ~48k → ~58k | ~5.6k / ~0.9k |
| **Music Hall** | 4 st., gambrels, 2 turrets, lantern | A domed centre: an octagonal drum, a bell dome and a lantern over the auditorium. The flanking spired turrets stand at different heights (6 and 5½). The gambrel steepens into a pavilion roof. | ~36k → ~42k | ~4.6k / ~0.85k |
| **Roller Rink** | 4 st., gambrel-gable, right turret, store | One great steep pavilion roof over the whole rink, with two tiers of dormers. The right turret rises with a spire. A one-storey-lower wing steps down on the left. | ~35k → ~41k | ~4.4k / ~0.75k |
| **Natatorium** | 5 st., gable-gambrel, store, lantern, no turrets | Twin square towers flank the entrance at 7 and 6 storeys, each under its own pavilion roof. The centre is a hip with the lantern crown. | ~42k → ~53k | ~5.6k / ~0.85k |
| **Picture Palace** | 6 st., mgm, 2 turrets | The tallest cluster: a centre tower at 8 storeys with a dome and lantern, corner spired turrets at 7, and steep pavilion roofs on the side cells. | 49k (measured) → ~60k | ~6.3k / ~1.0k |
| **Ballroom** | 5 st., gables, left turret, store, lantern | One long steep pavilion roof with tall dormers. Spired turrets stand on both front corners, and a taller stair tower on the left rises 2 storeys over the eave. The store steps to 3. | ~41k → ~49k | ~5.0k / ~0.8k |
| **Seaside Market** | 4 st., gmmg, right turret, store, granite base | A row of pavilions, one per cell, at alternating heights (tall, low, low, tall), each with a steep hip and finial. The right turret gets a spire. The market hall behind steps down. | ~35k → ~44k | ~4.8k / ~0.8k |

Smaller lots (4x4–5x5) drop one tower or pavilion where the front is too narrow for it, the same way the turrets drop today. All ZC2 stays under a third of the cap, and LOD1 under a quarter.

## Grand Hotels (ZP3): 8 designs × 3 lots, 12–16 storey towers

The château goes at the **top of the tower**, where it's seen across the city, and in the **court block**.

- **The court block** steps up toward the tower: 4 → 6 storeys on the wings, 8 on the near side where the design allows. That gives a stepped silhouette from the side and rear (rule 21).
- **The tower's crown** replaces today's gable or gambrel, dormers and lantern. Some of today's cost comes back that way.

The baked figures below already include option (a), the light windows above the 10th storey.

| Design | Today | Château massing | Baked LOD0 at 6x6, today → after | LOD1 / LOD2 after |
| --- | --- | --- | --- | --- |
| **The Atlantic** (14) | gambrel, turret, cross gable, lantern, twin wings | Steep pavilion roof on the tower. The cross gable becomes a cross pavilion one storey higher with its own roof. The turret rises 2 storeys over the eave with a spire. A dome-and-lantern crown sits on the main ridge. The twin wings step 4 → 6. | ~114k → ~118k | ~17.5k / ~1.6k |
| **The Tennessee** (12) | gable, turret R, lantern, near wing | Pavilion roof. The corner turret becomes a tall spired turret 3 storeys over the eave. A smaller corbelled turret on the opposite corner starts at the 10th floor, so the two stand at different heights. The lantern stays as the crown. The near wing steps 4 → 7. | ~116k → ~114k | ~15.0k / ~1.45k |
| **The New York** (14) | gable, no turret, cross gable, far wing | A keep of two square pavilions at 16 and 15 storeys, both under pavilion roofs. Four small spired corner turrets stand at the main eave. The far wing steps 4 → 6 → 8. | ~104k → ~108k | ~15.8k / ~1.5k |
| **The Virginia** (12) | gambrel, turret, cupola, twin wings | The dome hotel: an octagonal drum, bell dome and lantern over the centre of the tower, with a steep hip round it. The turret rises 2 storeys over the eave with a spire. The twin wings step 4 → 6. | ~119k → ~117k | ~15.6k / ~1.5k |
| **The Oriental** (16) | gable, turret R, cross gable, lantern, far wing | The tallest cluster: three stepped tower blocks at 16, 18 and 17 storeys, each under a pavilion roof. The spired turret rises to 19. The lantern sits on the middle block. | ~122k → ~131k | ~19.0k / ~1.8k |
| **The Vermont** (12) | gambrel, no turret, cross gable R, lantern, near wing | The richest roof, on the lightest tower: a steep pavilion roof with two tiers of dormers, four spired corner turrets at the eave, and the lantern crown. The near wing steps 4 → 6. | ~95k → ~106k | ~15.0k / ~1.5k |
| **The States** (14) | gable, turret, cross gable, twin wings, lofts | Twin end pavilions at 16 and 15 storeys under pavilion roofs. The turret rises to 17 with a spire. The twin wings step 4 → 6. | ~138k → ~132k | ~17.6k / ~1.6k |
| **The Pennsylvania** (16) | gambrel, turret R, cross gable, cupola, twin wings, lantern | A central pavilion rises 2 storeys over the eave with a dome-and-lantern crown, and the spired turret rises to 19. Also drops the carriage-block cupola. | 152k (measured) → ~148k | ~19.5k / ~1.8k |

With option (a), every hotel stays under 160,000 with at least 8% headroom. Without it, the Atlantic, Oriental, States and Pennsylvania would go over. LOD1 stays under 20,000 of 24,000, and LOD2 under 2,000 of 3,000.

## How it would be built (after your OK)

- **New kit pieces in `lt_shapes.py`:**
  - `pavilion_roof`: a steep hip with crest and finial, as a closed slab (rule 15).
  - `dome`: an octagonal drum with a bell dome.
  - `turret(..., spire=True, rise_over=n)`: carries the turret n storeys past the eave, under a needle cone.
- **New variant keys**, on `boardwalk.py` (`promenade=True`) and on `cottage.py` (`hotel=True`):
  - `crown`
  - `towers`
  - `steps`

  Old keys keep working, so ZP1 and ZP2 don't change.
- **Rules:** rule 11b and the rule 19 wording, as above.
- **Bakes:** ZC2 (32 buildings) and ZP3 (24) as two full runs. Then review, stage, and a re-import over the existing ZC2/ZP3 (the old files go to `backups\` first).
- **Re-import, no new zones:** the zone names don't change, so it's a re-import, not a new zone.
