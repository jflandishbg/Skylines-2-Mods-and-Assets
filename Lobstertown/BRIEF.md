# LOBSTERTOWN — design brief

Started 2026-11-14. Replaces New France as the CS2 building pack.

## The idea in one line
A Maine beach town that grew like Copacabana: the American shore's big shingled
houses, stretched into towers and lined up along the beach.

## the author's calls (2026-11-14)
- **Tone: believable, just huge.** Real New England grammar scaled up. It should
  look like a developer actually built it in 1905 or 1925, not a theme park. No
  giant lobsters on roofs.
- **Range: the whole town ladder**, several zones, not only towers.
- **Palette: weathered gray + white.** Silver cedar shingle, white trim, shutters
  in dark green, barn red or navy. Muted, per the New Holland lesson.
- **New France: delete everything** (confirmed list first).

## Where the look comes from
- **Shingle Style** (1880–1910): McKim Mead & White, the Newport and Kennebunkport
  "cottages". Continuous shingle skin wrapping round corners, gambrel and hip roofs,
  turrets that melt into the wall, deep porches, eyebrow dormers.
- **Grand resort hotels:** Wentworth by the Sea, the Colony in Kennebunkport,
  Mount Washington. Long verandah ranges, red roofs, white columns, cupolas.
- **Portland triple-deckers and Maine capes:** stacked porches, side-hall plans.
- **The Brazilian move:** the tall buildings sit on the beach avenue and step down
  inland. One continuous wall of towers along the sand, with a promenade in front.

## "Cranked to 11", but still believable
- Porches become balconies on every floor, stacked like a triple-decker 25 high.
- The turret runs the full height and ends in a broad conical or bell cap.
- Gambrel and widow's-walk crowns on the towers, with a lantern on the very top.
  Keep tops broad (the R22 rule: no needles).
- Shingle wraps the tower; white trim marks floors every 3–4 storeys like belt
  courses.
- The base is a stone or granite plinth, with shop fronts and boardwalk arcades.

## Density target: the Toronto Townhouses look (the author, 2026-11-14)
Every zone reads **high density**, whatever its zoning type. The benchmark is
the Toronto Townhouses pack (Paradox mod 161230): tall, narrow houses
shoulder to shoulder, a continuous street wall, a busy skyline of gables and
turrets, and only a stoop or porch between the house and the sidewalk. We keep
that density and partial look, and change the style.
- No freestanding cottages in yards. Even the smallest type is a tall, narrow
  gable-front house packed tight, like Provincetown, Nantucket or Bar Harbor's
  West Street.
- 1-wide lots in every row zone, and each design comes in every depth from 1x2
  to 1x6. Deep lots fill up with the Maine connected farm: big house, little
  house, back house, barn, all in one line. It's the New England version of
  Toronto's rear additions and laneway garages.
- Corner pieces (2x3) that face both streets: a turret or wraparound porch
  turns the corner.

## The ladder (zones)
| Zone | Type | Height | Lots |
|---|---|---|---|
| L1 | Shingle row houses (gable-front, tight) | 3 storeys + attic | 1x2–1x6, corners 2x3 |
| L2 | Triple-deckers, stacked porches | 3–4 | 1x2–1x6, corners 2x3 |
| L3 | Main-street mixed (shops below, flats above) | 3–4 | 1x2–1x6, corners 2x3 |
| L4 | Verandah hotels and apartment houses | 5–8 | 2–4 wide |
| L5 | Beachfront shingle towers | 15–30 | 3–6 wide |

Level 1 only, many distinct designs (the Chicago model). Households come from the
zone multipliers.

## Market review (2026-11-14): what to take and what to avoid
**Toronto Townhouses** (161230, 30.6k subscribers, also made with Claude in
Blender). 44 designs, 690 buildings, 4 zones, levels 1–5, 1-wide 1x2–1x6 plus
corners. The whole pack shares one small texture set (~70 MB). Budgets: about
6,400 triangles close up, 4,100 mid, under 460 far, with a baked facade picture
on the far model.
- *Take:* the street wall, the lot-depth range, corner pieces, rear additions,
  per-building roof colour variation, separate recolour channels for walls,
  roof and trim, and the baked far model.
- *Avoid (from its comments):* the white base pad under each building that
  can't be removed; hearses and ambulances with no route (a misplaced path
  marker); flicker; LOD holes from cutting the mid model too hard; colours too
  orange; bright green copper roofs too loud; too many back sheds.

**20 Brick Revival Apartments** (164781, 17k). 20 brick mid-rise apartment
blocks with cornices, placed by hand as signatures only.
- *Take:* the look of mid-rise blocks filling a whole street block, a good
  model for L4.
- *Avoid:* signature-only placement. Ours grow on their own.

**Midwest Prestige Houses** (163817, 13.6k). 28 boulevard mansions on 2x5 and
3x5 lots, level 1 only, landscaped yards.
- *Take:* mirrored variants (10 designs mirrored, 38 growables, cheap variety);
  three colour schemes per house through colour masks; a few shared 4096 px
  texture sets.
- *Avoid:* yards and setbacks (the opposite of the look we want); texture
  repetition (a top complaint). Commenters also asked for levels and for an
  apartment version with more households, which our density covers.

## Rules carried over
- The architecture rulebook applies. **Standing waiver for rule 3 (symmetry):**
  Shingle Style is picturesque and asymmetric by nature. The asymmetry must be
  deliberate: one dominant turret or gable, the entrance still clearly marked.
- Benchmark process from Hôtel Brique et Pierre: one composition, every side
  designed, 4 mm air gaps, the 8-point review, small batches seen in game.
- Shoulder to shoulder in every row zone. Only a stoop or porch sits in front,
  with a clear front walk so there's no "no pedestrian access" error, and a path
  marker at every door so hearses and ambulances can reach the residents.
- No benches. No water, no outbuildings, no props: Placemaker handles those.
- Full-set bakes, no pilots.
- Real CC0 textures: cedar shingle (weathered and painted), white clapboard,
  granite, red asphalt and slate roofing.

## Open questions for later
- The name in game: "Lobstertown" for the pack, with zone names like
  "Shore Cottages" and "Beachfront Towers"?
- A signature set later (lighthouse, pier, lobster pound, bandstand)?
