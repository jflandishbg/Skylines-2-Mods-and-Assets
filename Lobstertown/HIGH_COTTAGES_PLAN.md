# Next rung: Lobstertown Grand Hotels (High)

Prepared 2026-11-15, after the Cottage Flats (Medium) went in and set up clean. This is the top of the cottage ladder: the summer palaces become the grand resort hotels of the brief (Wentworth by the Sea, the Colony, Mount Washington), with the Atlantic City boardwalk-hotel look from the flats carried up a size. They have long verandah ranges, white columns, cupolas, and **red roofs**.

## The ladder

| | Low: Prestige Cottages | Medium: Cottage Flats | **High: Grand Hotels (next)** |
| --- | --- | --- | --- |
| Lots | 2x4–3x6 | 3x5–4x6 | **4x6, 5x6, 6x6** |
| Main house | 2–3 storeys | 4 storeys | **6 storeys, a 7-storey tower** |
| Households | 1 | 6–10 | **4x6: 14, 5x6: 18, 6x6: 22** |
| Roofs | grey and dark slate | green slate on most (the houses) | **red slate on most (the hotels)** |
| Zone | Residential Low clone | Residential Medium clone | **Residential High clone** ("Lobstertown Grand Hotels") |

The red roofs are the board-game nod: the green houses go up a rung and become red hotels. As with the flats, there's no Monopoly name, logo or art. The red roofs, and the real Atlantic City avenue names on the name boards, are as far as the nod goes. The red stays a weathered oxide red (rule 20), never a toy red.

## The plan of the building

The 4-wide twin court from the flats grows into a **hotel U**:
- **A front range** the full width of the lot: 6 storeys, with a 7-storey corner tower or a central pavilion under a cupola.
- **Two side wings** running back, 4 storeys of rooms.
- **A back range** closing the court, also 4 storeys, with the hotel's service entrance on it.
- **A court** in the middle, open to the sky, with a walk through it.

That fills the lot to the rear line (rule 17), and gives every view a different face (rule 21).

**Eaves stay at 3 levels (rule 11):**
- the verandah's upper deck, 6.3 m
- the wings and back range, 12.9 m
- the front range, about 18.9 m

The tower and cupola rise above these, as they already do on the cottages.

**Out front:** a two-deck verandah range with white columns along the whole front, wrapping one corner on the wider lots. The name board sits on the deck fascia, the same way as on the flats.

## Variety (8 designs × 3 sizes = 24 buildings, one run)

Each design gets its own combination of these keys:
- **Crown:** corner tower / central pavilion with a cupola / twin end towers (6x6 only)
- **Front roof:** hip / gambrel / gable ends
- **Verandah wrap:** none / left / right
- **Base:** stone ground floor or not
- **Wing roofs:** gable / hip
- **Back range:** full height / one storey lower, with a roof terrace line
- **Roof:** red slate on 6 designs; dark slate on 2, so the skyline isn't all one colour

The name boards use the next 8 real Atlantic City avenues: **The Atlantic, The Tennessee, The New York, The Virginia, The Oriental, The Vermont, The States, The Pennsylvania**.

## What has to be built first (my side)

1. **5- and 6-storey heights** in the kit (`TOPS`, `WINS`, `BELTS`), so rules 4 and 5 check the new floors.
2. **A red slate swatch** in a free atlas slot. I'd use a CC0 slate texture, toned down. I'll check it in the palette preview before baking.
3. **8 more name boards**, cut into strips of two more unused atlas slots, the same way the flats' boards were made.
4. **A `hotel` mode in `cottage.py`:** the U plan, built with the mirrored wrappers (rule 23). The flats' twin-court code is most of it already.
5. **The budget (rule 25) is the hard part.** A 6x6, 6-storey front has about 3× the windows of the biggest flat. The plan:
   - full sashes on the street front only
   - one-over-one (`simple`) windows everywhere else
   - bare panes at LOD1
   - verandah columns without balusters at LOD1
   - LOD2 keeps the U outline and the tower only

   If a 6x6 still won't fit in 45k triangles, I'll widen the bays rather than cut the lot size.
6. **Setup:** add ZP3 "Lobstertown Grand Hotels" to `ZONE_KEY`, with households by lot (the `HH_OF` fix from today already handles per-size counts).

## What you'll do

Nothing until you say go. Once the set is staged:
1. Make the zone **Lobstertown Grand Hotels** as a clone of vanilla **Residential High**.
2. Import.

I run setup with the game closed, the same as always.

## Open questions (my defaults, unless you say otherwise)

- **Lots:** 4x6, 5x6, 6x6. If you'd rather keep them to 4x6 and 5x6, the set drops to 16.
- **Households:** 14 / 18 / 22. That's dense for High but believable for a converted hotel.
- **Roof mix:** 6 red, 2 dark.
