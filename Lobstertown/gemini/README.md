# Gemini building runner

Turns a Blender script from Gemini into a checked, importable New France building.

## the author's part

1. Open `../GEMINI_BUILDING_TEMPLATE.md`, paste it into Gemini, and fill in Part 3 for one building.
2. Save Gemini's script as `scripts/<name>.py`. The file name must be the building name, for example `scripts/NA_PdDMaisonDuQuai_L1_1x3.py`.
3. Tell Claude: "run <name>".
4. Look at the preview sheet `runs/<stamp>/<name>_preview.png`. It shows street-level views of every side, an aerial, and the two far views.
5. Then do one of the following:
   - **FAIL, or you don't like it:** copy the "Paste this back to Gemini" block from `runs/<stamp>/REPORT.md` into Gemini. Add your own design notes, then save the new script over the old one and repeat from step 3.
   - **PASS and you like it:** tell Claude "stage it". The building lands in `generator/imports/1_READY_GEMINI_<stamp>_<n>/` for you to import, with the game closed. After you import, Claude runs setup so the building gets its zone.

## Claude's part

```
python run.py NA_PdDMaisonDuQuai_L1_1x3 [more names]
python run.py --stage runs/<stamp>
```

### What a run does

Each run works in its own `runs/<stamp>/` folder, in this order:

1. **Precheck.** Confirms the script has `build(lod)`, a `ZONE` line and a correctly formed name, and uses no file or network imports.
2. **Bake.** Runs `source/bake_r12.py` in GEMINI mode. This step builds the three detail levels (LODs), cuts the textures, exports the files and checks:
   - triangle budgets;
   - a density of at least 8 triangles per m²;
   - that no two faces lie in the same plane;
   - that everything stays inside the lot bounds.
3. **Audit.** `source/audit_gemini.py` checks the baked files:
   - the building is one piece;
   - no rooms float off the building;
   - no blank walls of 30 m² or more without glass. Declared party walls on the side lot line are excused.
4. **Preview.** `source/preview_gemini.py` renders the textured EEVEE views.
5. **Report.** `REPORT.md` says PASS or FAIL. Failures are written in plain words, ready to paste back to Gemini.
6. **Architecture review.** For every building that passes, the run writes `<name>_REVIEW.md`, an eight-point design checklist. Claude fills it in from the preview sheet:
   - one composition;
   - grounded porticos;
   - every side designed;
   - clean roofs;
   - clear hierarchy;
   - reads as its style;
   - far views hold;
   - the author's rules.

   Claude ends it with `Verdict: PASS` or `REDO`. **`--stage` refuses any building whose review doesn't say PASS.**

The audit also fails a building outright in two cases (outline on declared party walls is ignored for eaves):
- slits between blocks, of 1 m² or more;
- more than 3 eave heights. An eave height counts only if it runs at least 3 m unbroken along the outline, so dormers and pediments don't count.

## The rulebook

`RULEBOOK.md` lists the proportion rules every building follows. The kit checks rules 1–10 while it builds (`source/nf_rules.py`), and a broken rule fails the bake with the rule, the wall and the numbers. A design can waive a rule only with a written reason: `waive={"balance": "side-hall row house"}`.

## The kit (how Claude builds now)

Gemini is optional now.

**`source/nf_kit.py`** holds the parts, pulled from the benchmark hôtel:
- `wall()`: a whole facade in a `style()`. It includes cut windows with casements and stone surrounds, the plinth or cap, belt courses, rustication, quoins, and a cornice with dentils. Corners wrap correctly: `'x'` for outside corners, `'c'` for inside ones.
- `mansard()`, `lucarne()`, `pediment()`, `pilasters()`, `steps()`, `chimney()`.
- For rows and party-wall blocks:
  - `party()`: a bare wall on the side lot line (x = ±(4·W − 0.01)).
  - `mansard_row()`: a mansard whose sides can slope, end in a party gable, or stay open where a block butts into a taller one.
  - `flat_roof()`.
  - `wall(..., '-' ends)`: a plain end on a party line.
  - `wall(z0=...)`: a wall that starts above a lower block.
  - `wall(shop=...)`: a shopfront.
  - `balcony()`: a stone slab with an iron railing; use `"fwin"` windows above it.
- Every part leaves a 4 mm air gap where it touches another, so nothing flickers.

**Designs:**
- **Each design** is one module in `source/nf_designs/` with `build(lod, **variant)`. For example, `hotel_brique_et_pierre.py` takes the keys `brick`, `ground`, `deck`, `roll`, `steep` and `door`.
- **Each building** is a short stub in `scripts/` that sets `ZONE`, `HOUSEHOLDS` and `PARTY_WALLS`, then calls the design with its variant. See `NA_PdDHotelBriqueEtPierreB_L1_3x4.py`.
- **Speed:** a new variant is a few lines. Baking, auditing and previewing two buildings takes about 20 seconds.

**Note:** the preview washes out brick colour. The A hôtel looked salmon in the preview and came out orange-red in game, so judge brick tones in game.

### Notes

- Every building is its own texture owner: its 15 PNGs are copied from `atlas_template/`.
- `--stage` copies only the buildings that passed. It leaves out the preview folders. It also registers each building's zone in `GPT_INBOX/gemini/designs.json`.
- `scripts/NA_PdDTestRowHouse_L1_1x3.py` is Claude's test building, used only to prove the runner works. **Do not stage it.**
