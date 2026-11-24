# Interchange Studio restoration — 2026-10-31

## Latest pass: dumbbell interchange

Added `ToolMode.Dumbbell = 4` end-to-end (config, persisted settings, UI tile, planning), using archived ring construction adapted to the maintained service-interchange pipeline. This is an experimental double-roundabout service interchange for right-hand traffic. Real-world references: [VDOT double roundabout](https://www.vdot.virginia.gov/about/our-system/highways/innovative-intersections/double-roundabout/) and [MassDOT interchange guidance](https://www.mass.gov/info-details/pddg-chapter-7-interchanges).

`Core/Planner.Roundabouts.cs` contains the ring writer and street surgery. Compact/Standard/Spacious use 24/30/36 m centreline radii. Rings circulate consistently and use a narrow ordinary one-way road prefab (7.5–12 m wide; special bus/tram/pedestrian roads excluded). Four ramps use the current safe highway attachment and equalisation code.

Safeguards added beyond the archived version:

- Requires both carriageways and highway-over-street geometry. Ground-level existing crossings lift the highway first; elevated cross streets are refused. Selecting the UI tile sets highway-over and both carriageways.
- Requires nearly straight, level, roughly perpendicular cross-street approaches.
- Refuses overlapping terminal rings, duplicate rebuilding of a street piece, one-way cross streets, and internal side-street junctions.
- Searches seven outward terminal positions at 12 m increments to avoid road remnants shorter than 12 m. No deletion specs are written until a candidate has passed these checks.
- Preserves upgrades on rebuilt street remnants and queues existing road names for restoration.
- Keeps rings and street reconstruction in core group zero, with four separately grouped ramps. Trimming a blocked ramp cannot remove a ring or leave street reconstruction unfinished.

Validation: **64 tests passed**, including three size/topology/circulation cases, elevated-street and half-interchange refusals, ground-level staging, core preservation during trimming, and config validation. The SVG scenario sheet includes `dumbbell.svg`. Release build passes with the same two assembly-reference warnings; CorePurity and JavaScript syntax checks pass.

Not certified in-game: actual lane connections, yield/priority settings, traffic throughput, and the rendered UI. These are ordinary one-way-road rings, not automatically configured native roundabout objects. Users must inspect connections and set appropriate junction priorities. The existing ErrorGate disables several geometry error categories; this pass did not change that behavior, so engine acceptance alone is not proof of good geometry. Best fit still compares only Diamond and SPUI; it does not select this experimental style automatically.

Source backup before this pass: `C:\Users\<you>\CS2Planner\backups\studio-before-dumbbell-7d30143e.zip`. Test sources in this archive are flattened at its root. The final build is deployed to the actual Mods/InterchangeStudio directory after a separate installed-mod backup; restart the game to load it. Earlier sections below document the preceding pass and its then-current deployment status.

## Correct project

Work in `C:\Users\<you>\CS2Planner\InterchangeStudio`. Its `DESIGN.md` explicitly identifies it as the replacement for ClaudeInterchanges. The previous GPT pass mistakenly targeted the retired mod. The current project already contains Claude's lifecycle/summary adaptations of that work; those are preserved.

Before this pass, source/UI were backed up to `C:\Users\<you>\CS2Planner\backups\studio-before-restoration-20261031-b9a73082.zip`. The test files in that ZIP are at the archive root; Core/Game/UI/Testing retain their folders. No Git repository is used.

## Evidence and feature selection

The main archive is `backups\studio-before-prune-2026-10-24`. It contains freehand routing, system presets (cloverleaf/cloverstack/stack/turbine/trumpet/directional/partial clover), frontage/UTurns, dumbbells, highway endings, and Best fit. The current Config.cs recorded their removal after too many builds were rejected in-game. DESIGN.md is a historical blueprint, not an accurate list of implemented files: many specified modules/contracts do not exist in the live Core tree.

This pass implements two bounded restorations, rather than enabling all retired enum values:

### Best fit (saved mode 5)

- New `Core/Planner.Restored.cs` compares the maintained `ServicePreview(Exit)` and `ServicePreview(Spui)` recipes at existing separated crossings.
- Selects fewer deleted road pieces first, then SPUI when the diamond has closely spaced junctions, then less generated road length. A single successful recipe is used if the other fails.
- Status and logs explain the choice. This is a geometry heuristic, not a traffic simulation or proof of an engine-clean build.
- Local streets at existing crossings receive bridge-only treatment; already separated local streets are left alone. At arterial ground-level crossings, bridge stage remains automatic and stage two invokes Best fit.
- Bare-highway/new-street/stub workflows retain the current planner's behavior and select the ramp style after the bridge is built. They are not precomputed stage-two simulations.
- Retains the existing autofit and ramp-trimming pipeline. Selection compares geometry for each config variant; it does not independently compare the game's red verdict for both styles.

### Explicit Direction repair (new saved mode 9)

- Restores the archived reversed-run idea as a dedicated Repairs tab tool; it never intercepts ordinary construction modes.
- Only offers a one-way highway run of at most 1 km with opposing traffic at both ends. Every traversed/boundary node must have exactly two connected edges; one-way highway type/prefab must match and headings must align closely.
- Rejects merges, branches, dead ends, loops, normal highways, and ordinary streets. Traversal is bounded to 100 steps per direction.
- Replacement curves are reversed with start/end entities and elevations swapped. Road types and names are retained, general upgrade bits retained, left/right upgrade fields swapped to keep their physical sides.
- No automatic apply or follow-up stage is added. The user must inspect and click the preview, subject to the existing game gate.
- It cannot infer whether a bounded opposing run was intentional; preview review is still necessary.

## Integration

- `Planner.cs`: mode IDs, repair hover dispatch, best-fit dispatcher, local-street bridge-only behavior; no autofit for repairs.
- `Config.cs`, `Game/Mod.cs`, `Game/StudioUISystem.cs`: validation, persisted mode loading, UI configuration.
- `UI/InterchangeStudio.mjs`: Best fit tile, Repairs tab and explanation; hides unrelated geometry controls for repair.
- New SVGs: `is-bestfit.svg`, `is-repair.svg`.
- `InterchangeStudio.csproj`: adds `DeployOnBuild=false` opt-out, preserving default deployment behavior. Verification uses opt-out; installed mod has not been overwritten.

## Verification

All 56 tests pass (45 existing plus 11 new cases). Tests cover comparison/config immutability, local-street bridge-only and no-op behavior, arterial staging, bounded repair geometry/elevation/names, refusal of branches/open ends/ordinary streets/healthy highways, and config validation. ScenarioTests includes Best fit in its SVG review sheet.

Run from the active project:

```powershell
$env:DOTNET_ROOT = 'C:\Users\<you>\.dotnet'
& 'C:\Users\<you>\.dotnet\dotnet.exe' test Tests\InterchangeStudio.Tests.csproj --no-restore
& 'C:\Users\<you>\.dotnet\dotnet.exe' build InterchangeStudio.csproj --no-restore -c Release -p:DeployOnBuild=false
& 'C:\Users\<you>\.dotnet\dotnet.exe' build Build\CorePurity\CorePurity.csproj --no-restore
node --check UI\InterchangeStudio.mjs
```

Tests require running outside this sandbox for the runner's process connection. The default PATH dotnet lacks an SDK; the user-local executable above works. Release compilation has two assembly-reference conflict warnings (System.Net.Http and System.IO.Compression). CorePurity compiles without warnings. Final test count is recorded in the chat.

Not validated in a live game: preview rendering/appearance, build acceptance, actual lane connections after reversal, upgrade-side appearance, settings persistence across a game restart. Test on a disposable save, especially the direction-repair case. Geometry unit tests cannot certify these.

## Next restoration candidates

1. Freehand ramps: recover archived Planner.Ramp.cs/RampRouter.cs with whole-profile terrain/world-grade validation and exact emitted-curve clearance checks; preserve current safe splits and generation groups. Start with one direct ramp, then loops and symmetry.
2. Frontage ramps: reuse the active safe attachment logic; validate every crossing against roads, tracks and paths. Add U-turns only after bridge/pillar clearance tests.
3. Dumbbells and highway endings: rework exact ring joins and split/delete conflicts before exposing the tiles again.
4. System interchanges: joint elevation planning and required movement groups, avoiding a partial layout that silently omits necessary turns.

These are candidate follow-ups, not implemented functionality. The old design's larger architecture remains aspirational.
