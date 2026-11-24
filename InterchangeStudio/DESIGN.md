# Interchange Studio: rebuild design

Mod id `InterchangeStudio`, display name "Interchange Studio". Project folder `C:\Users\<you>\CS2Planner\InterchangeStudio`.
This replaces `C:\Users\<you>\CS2Planner\ClaudeInterchanges` (OverpassToolSystem.cs and friends, about 4,500 lines), which stays installable until the rebuild reaches parity.

**Use this document together with `Core/Contracts.cs`.** Every code block in section 6 is copied from that file by `Build/sync-design.sh`. `Contracts.cs` compiles on netstandard2.1 and on net8.0 with C# 9, using only Unity.Mathematics and the `Bezier4x3` type from Colossal.Mathematics. If this document and the file ever disagree, the file is right, and the `DesignInSync` test fails until someone reruns the script.

Contents
1. Goals
2. How this design was chosen
3. Repository layout and build
4. Layering rules and how they are enforced
5. Module map
6. Shared contracts (generated from Core/Contracts.cs)
7. Planning pipeline
8. Geometry and aesthetics
9. Style recipes
10. Autofit
11. Tool session (per-frame state machine)
12. Game adapter
13. UI and bindings
14. Invariants and where each is enforced
15. Validators
16. Test harness
17. Phase-0 in-game spikes
18. Feature-parity checklist
19. Work breakdown and milestones
20. Risks and open questions

---

## 1. Goals

**The single biggest goal.** The planning core must be pure: no Unity.Entities, no Game.dll. That way every style can be unit-tested offline against synthetic road networks and against real spots captured from the author's city. A thin game adapter turns ECS state into a `NetworkSnapshot` and turns a finished `BuildPlan` into `CreationDefinition` / `NetCourse` entities.

Other goals:

| # | Goal | How |
|---|---|---|
| G1 | At least feature parity with everything in the catalogue | Section 18 maps every catalogued feature to its new home |
| G2 | Configuration is an immutable snapshot passed into planning | `PlanConfig` / `EngineRules` are C# 9 records; autofit uses `with`; a reflection test fails on any mutable static in Core |
| G3 | Every engine invariant is enforced by construction or by a validator in Core | `IPlanBuilder` guarantees plus validators V01-V28; matrix in section 14 |
| G4 | No red without Anarchy, and plain-English reasons when something is red | Core validation steers autofit before anything is drawn; the game's red preview stays the final judge; `Narrator` explains |
| G5 | Aesthetics: curvature-continuous ramps, long tapers, realistic geometry, a polished panel | Clothoid smoothing seeded with mainline curvature, quintic tapers (length at least 3x the offset), chain-offset ramps, eased vertical curves with peak grade equal to the setting, exact rings, catalogue-driven panel |
| G6 | One click at a crossing gives a finished interchange | Bridge first, then the ramps automatically: stage 2 is predicted before the click and replanned after it |
| G7 | No hover stutter in big cities | Snapshot rebuilt only on real change, region-versioned plan cache, time-sliced planning (worker thread optional) |
| G8 | Parallel implementation | A frozen contract, interfaces for every cross-unit service, and units of 1-3 files (section 19) |

Non-goals for v1: left-hand traffic (designed for: `TrafficSide` everywhere, a mirrored-snapshot path behind `EngineRules.LhtViaMirror`; shipped only once property P5 passes); Burst/jobs; a custom DSL; git.

---

## 2. How this design was chosen

Three proposals were judged. **Proposal 0 (testability first) won** (totals 40, 43 and 42 from the three judges). This design is Proposal 0 plus the ideas the judges asked to graft in, with the conflicts between proposals settled as below.

| Topic | Decision | From |
|---|---|---|
| Core shape | Pure Core: `NetworkSnapshot -> Site -> BuildPlan -> ValidationReport`; `PlanBuilder` enforces invariants by construction; `BatchSafety` generalises the two-step build; pure `ToolSession`; CorePurity build; source-rule tests; SVG review sheet; capture and replay | P0 |
| Records | `PlanConfig`, `EngineRules`, `SessionTuning` are `sealed record` with init-only properties (P0's `with` on a class would not compile). Tests compile at LangVersion 9 | judges (all) |
| Click gate | **The game is the final judge.** A click applies when the verdict has settled (age >= 3 frames, Temp count stable 2 frames) and `GetAllowApply()` is true. Core Blocking violations steer autofit and the status; they never veto a click the game allows. Core Fatal plans are never emitted | P1/P2, fixes P0 |
| Snapshot versioning | The version bumps only on a **semantic content diff**, with per-128 m-cell stamps (`RegionVersion`) in cache keys. Change detection never relies on `GetCombinedComponentOrderVersion` alone, because the tool's own Temp preview edges would bump it every frame | P2 |
| Stage-2 settle | Wait for "network version changed and 2 quiet frames" (timeout 120). Relocate with a ladder (anchor, street aggregate, highway prefab at 40/120/250 m). Stage-0 knobs are locked for stage-2 autofit | P2 |
| Speculative stage 2 | Before the click, stage 2 is planned on `EngineSim.Apply(net, stage1).After`, never emitted. If it fails, the bridge alone is offered with the reason and a one-click suggestion. Autofit can widen the deck (`DeckMarginExtra`) so stage 2 fits | P1/P2 |
| Multi-ramp | Joint `ILevelSolver` over every routed ramp of a stage (fork elevations are variables), then a multi-pass pillar placer over all pending paths, later ramps included. Atomic, Required and Optional groups with rollback and Fallback | P1 |
| In-game red | Red positions become session-learned keep-out discs (`LearnedObstacles`). When autofit is exhausted, the least-red layout is shown, not the last one tried | P1 |
| Joins | Exact `JoinPoint`s by construction. IsFirst/IsLast are cleared only for 2-ref points with the same prefab and continuous heading (dot >= 0.995); everything else keeps the flags, and the engine forms a node from identical positions. Splits of one edge within 1 m share one t | P0 + P1 |
| Attach | When a split is a batch hazard or a sliver, search +/-40 m for another safe split, then a safe node, before staging | P1 |
| Apply frame | Type-level: `FrameOutput.ApplyNow` carries no plan. The emitter accepts only a finished `BuildPlan` | P2 |
| Explanations | Structured `Explanation` (Because, Tried, Facts, Warnings, Suggestions as one-click buttons) rendered by `Narrator`. Site hysteresis (keep the current site unless another is 25 % nearer). Status pinned until the cursor leaves the site | P2 |
| Engine model | `IEngineSim` (splits, node formation, healing, deletions) gives Dangling / DeadEnds / Slivers / FlowConflicts. Calibrated against the three historic failures; Warn severity until spike S7 confirms it | P2 (+P1 EngineModel) |
| Prefabs | `PrefabCapabilities`: a missing ramp, ring or avenue prefab disables the affected tiles with a reason. Deterministic picks (exact vanilla names first, then name-sorted fuzzy match) | P2 |
| Tapers | Quintic G2 tapers, length >= max(60, 3 x offset). The diverge starts exactly at the split point on the centreline (P2's "share the lane line for 30 m" variant is rejected) | P2, corrected |
| Hashing | Fnv64 everywhere a hash must be stable (fingerprints, keys, seeds) | P2 |
| Names | Road names for descriptions come from a per-aggregate dictionary read with the snapshot. Names to RESTORE are captured from the live source edges on the click frame | P0 + P2 |
| Vertical | One eased profile for lifts and ramps (parabolic ends, peak slope = configured grade). Adaptive break points where a linear-y chord leaves the profile by more than 0.25 m. Linear handles stay the default until spike S1 proves Hermite handles | P0 (kept) |
| Phase-0 spikes | S1-S10 answered in-game before dependent units commit | P2 |
| Captures | Each capture can carry an `Expect` sidecar ("builds clean" or "fails: <code>") so a bug report becomes an asserting test | P1 |
| Autofit order | Variants sorted by deviation cost (Clearance > Flip > Grade > Compact > Radius > Route), with a "Use my settings" link on the autofit chip | P1 |
| Reversed runs | Shown as a status badge with a "Turn it round" suggestion, plus a Fix tab tile. They no longer hijack every mode | P2 |
| Fix tab | Find next (with counts), Fix direction, Save this spot | P1 |
| Misc | `GetAvailableSnapMask = Snap.None`; requireNet and requireUnderground set explicitly; underground-view flags logged on activation; `shouldBeEnabled = false` in OnDispose; verbose-gated per-hover logging | P2/P1 |

**The id conflict.** The brief requires mod id `InterchangeStudio`, but the catalogue says the `ClaudeInterchanges` ids hold player data. **The brief wins, and data is migrated.** `LegacyImport` reads `ModsSettings/ClaudeInterchanges/ClaudeInterchanges` once into a never-saved `LegacySettings` and maps (Mode, PresetStyle) to a style. Custom key rebinds cannot be carried over; a one-time notice says so. If the old mod is still installed, a one-time notice asks the author to remove it, because both would claim Ctrl+Shift+H.

---

## 3. Repository layout and build

```
C:\Users\<you>\CS2Planner\InterchangeStudio\
  DESIGN.md                       this document
  Directory.Build.props           LangVersion 9.0, Nullable disable; GameDir chain Local.props -> $(CS2_GAME_DIR) -> C:\SteamLibrary\...\Cities Skylines II;
                                  GameManaged = $(GameDir)\Cities2_Data\Managed
  Local.props.example
  InterchangeStudio.csproj        netstandard2.1, AssemblyName InterchangeStudio, EnableDefaultCompileItems=false,
                                  <Compile Include="Core\**\*.cs;Game\**\*.cs" />, game refs Private=false,
                                  target CheckCorePurity (BeforeTargets=Build) builds Build\CorePurity\CorePurity.csproj,
                                  target Deploy (AfterTargets=Build) copies dll, pdb, UI\InterchangeStudio.mjs/.css, UI\images\is-*.svg
  Core\                           PURE. namespace InterchangeStudio.Core (and InterchangeStudio.UI for Core\Panel)
    Contracts.cs                  the frozen shared contract (this document, section 6)
    Common\ Model\ Geometry\ Network\ Profile\ Plan\ Write\ Validate\ Sites\ Kit\ Styles\ Autofit\ Pipeline\ Session\ Text\ Panel\ Diagnostics\
  Game\                           ADAPTER. namespace InterchangeStudio.Game. References Game.dll, Unity.Entities, Colossal.UI.Binding ...
  UI\                             InterchangeStudio.mjs, InterchangeStudio.css, images\is-*.svg (no build step)
  Testing\                        PURE test support, never in the mod: CityBuilder, VanillaPrefabs, Scenarios, InvariantChecks, PlanSvg, ProfileSvg, ReviewSheet, Approvals, Fuzz
  Tests\                          InterchangeStudio.Tests.csproj (net8.0, LangVersion 9, xunit 2.5.3) links ..\Core\**\*.cs and ..\Testing\**\*.cs;
                                  Approved\*.json (golden metrics), Captures\*.json (+ *.expect.txt), Data\fitcurve.json (spike S9 dump)
  Harness\                        Harness.csproj (net8.0 console): review sheet, fuzz, replay, preview\catalog.json
  Build\CorePurity\CorePurity.csproj   netstandard2.1, links ..\..\Core\**\*.cs, references ONLY Unity.Mathematics and Colossal.Mathematics
  Build\sync-design.sh            regenerates section 6 of this document from Core\Contracts.cs
  Spikes\                         SpikeProbe.csproj + SpikeSystem.cs: a throwaway mod for the phase-0 questions (deploys to Mods\InterchangeStudioSpikes)
  preview\panel.html              stateful browser mock of the panel (served by a launch.json entry "studio-panel")
```

Build: `C:\Users\<you>\.dotnet\dotnet.exe build InterchangeStudio.csproj -c Release` (this also runs CorePurity). Tests: `dotnet test Tests`. Review sheet: `dotnet run --project Harness -- all`.

Deploy: the build copies to `%USERPROFILE%\AppData\LocalLow\Colossal Order\Cities Skylines II\Mods\InterchangeStudio\` (never `.cache\Mods\local`). `EnableDefaultCompileItems=false` means stray backup `.cs` files can never be compiled in. Backups go to `C:\Users\<you>\CS2Planner\backups\`.

No git. Golden approval files are plain files: `Approvals` writes `*.received.json` next to `*.approved.json`.

---

## 4. Layering rules and how they are enforced

```
UI (mjs) <-> bindings <-> Game adapter --uses--> Core.Session / Core.Pipeline --> Core.Styles --> Core.Kit --> Core.Plan / Write / Geometry / Model
Testing --uses--> Core (all)                   Tests / Harness --link--> Core + Testing
```

| Rule | Enforcement |
|---|---|
| Core uses only the BCL, Unity.Mathematics and Colossal.Mathematics (Bezier4x3; MathUtils allowed in implementation files) | CorePurity project, built before every mod build, has no other references. The test project references nothing else either |
| Core has no mutable statics | `SourceRules.CoreHasNoMutableStatics`: reflection over every type in `InterchangeStudio.Core` / `.UI`; any static field that is not `readonly` or `const` fails. `static readonly` fields must hold immutable types (records, strings, arrays never) |
| Only `Plan\PlanBuilder.cs`, `Plan\AttachFactory.cs`, `Plan\BatchSafety.cs` and `Diagnostics\CaptureCodec.cs` call `EndRef.Make*`, `new JoinPoint`, `new AttachChoice`, `new BuildPlan` | Source scan (internal access cannot stop same-assembly use) |
| Only `AttachFactory` calls `Splits.Decide` | Source scan |
| Only `Game\DefinitionWriter.cs` creates `CreationDefinition` / `NetCourse` | Source scan over `Game\*.cs` |
| Only `Game\NameKeeper.cs` calls `SetCustomName` | Source scan |
| Only `Game\Log.cs` calls `Mod.log` / `ILog` | Source scan |
| `ConnectedEdge` is read only in `Game\NetworkReader.cs` (and preferably not at all: legs come from edge endpoints) | Source scan |
| No redeclaration of `m_ErrorQuery`, `m_PrefabSystem`, `m_ToolSystem`, `m_ToolRaycastSystem` | Source scan |
| No literal right-vectors (`t.z, 0, -t.x` / `d.y, -d.x`) outside `TrafficSide` | Source scan over Core |
| CSS stays inside the Gameface subset | `CssLint` over `UI\*.css` (section 13.4) |
| No missing glyphs | Glyph lint over `.mjs` (forbid triangle arrows; allow + U+2212 x middle-dot degree) |
| The .mjs has no `import` of cs2 packages and exports `hasCSS` and a default `register` | UI lint |
| DESIGN.md section 6 equals Core/Contracts.cs | `DesignInSync` test |

---

## 5. Module map

Unit ids (Uxx) refer to the work breakdown in section 19. "Port" names the old code each file starts from (OTS = OverpassToolSystem.cs).

| Module | Files | Responsibility | Port | Unit |
|---|---|---|---|---|
| Contracts | `Core/Contracts.cs` | Shared types and interfaces (section 6) | new | done |
| Model: snapshot | `Core/Model/NetworkSnapshot.cs`, `Core/Model/SnapshotBuilder.cs`, `Core/Model/SpatialGrid.cs` | `INetwork` implementation, `ISnapshotBuilder` (legs from edge endpoints, content diff, version, cell stamps), 128 m grid | OTS.Index.cs, OTS 802-904 | U03 |
| Model: prefabs, terrain | `Core/Model/PrefabTable.cs`, `Core/Model/Terrains.cs` | `IPrefabTable` role picks, skip lists, capabilities; `GridTerrain` (wraps HeightSamples), `FlatTerrain`, `PlaneTerrain`, `FuncTerrain` | OTS 1830-1869, 2439-2461, Presets 241-254 | U04 |
| Geometry: curves | `Core/Geometry/CurveMath.cs`, `Core/Geometry/Arcs.cs`, `Core/Geometry/Cross2D.cs` | Static curve maths: FitCurve port from `tools\decomp\Game.Net.NetUtils.cs:90-160`, Cut, ArcTable, arcs, semicircle, all-hits Cross2D (the `ICurveKit` facade is in U06) | OTS 948-983, 1230-1250, 1769-1778, 2326 | U05 |
| Geometry: paths | `Core/Geometry/Prims.cs`, `Core/Geometry/Dubins.cs`, `Core/Geometry/PathOps.cs` | Line/Arc/Curve prims, `CompositePath`, fixed `LargestTurnDeg`, `CrossesItself`; Dubins verbatim; Concat, chain Offset, quintic Taper; the `CurveKit` facade (`ICurveKit`) forwarding to the statics | RampRouter.cs 14-142, 199-253 | U06 |
| Geometry: smoothing | `Core/Geometry/LaplacianSmoother.cs`, `Core/Geometry/ClothoidSmoother.cs` | `IAlignmentSmoother` (clothoid primary, Laplacian fallback with 1.15x pre-inflation) | RampRouter.cs 162-197 | U07 |
| Profile | `Core/Profile/VerticalProfile.cs`, `Core/Profile/ProfileSolver.cs` | Eased profile (`IVerticalProfile`), level DP (merged zones, no input mutation), `RunFor` | RampRouter.cs 255-372, OTS 1104-1110 | U08 |
| Level solver | `Core/Profile/LevelSolver.cs` | Joint levelling of all routed ramps of a stage | new | U09 |
| Network | `Core/Network/Chain.cs`, `Core/Network/NetworkKit.cs`, `Core/Network/Topology.cs` | `IChain`, walkers, Follow, StreetThrough/Between, FromEnd, IsTerminal, IsEndNode, ClassOf | OTS 908-946, 1059-1102, 1272-1326, 580-602, 2052-2167 | U10 |
| Sites A | `Core/Sites/CrossingDetector.cs`, `Core/Sites/SeparationDetector.cs`, `Core/Sites/HighwayEndDetector.cs` | At-grade and rail crossings (+partners), grade separations (all hits, same-street pairing), highway ends | OTS 654-904, 1196-1269, 1883-1950 | U11 |
| Sites B | `Core/Sites/Cross4Detector.cs`, `Core/Sites/StemDetector.cs`, `Core/Sites/ReversedRunDetector.cs` | Four-way crossings and carriageway lines (canonical key), stems (incl. at-grade T and two-way), reversed runs | Presets 65-123, 315-376; OTS 2459-2499 | U12 |
| Sites C | `Core/Sites/SiteFinder.cs`, `Core/Sites/Relocator.cs`, `Core/Sites/FixFinder.cs` | Hover dispatch with hysteresis and badge; stage-2 relocation ladder; find-next (pairs counted once, terminals excluded) | OTS 283-331, 520-578 | U13 |
| Plan builder | `Core/Plan/PlanBuilder.cs`, `Core/Plan/AttachFactory.cs`, `Core/Plan/BatchSafety.cs` | `IPlanBuilder`, `IPlanBuilderFactory`; exact joins, split rules and window search, relays, transactions, promotion and staging, Finish | OTS 1113-1192, 1336-1357, 2569-2600 | U14 |
| Writer | `Core/Write/Breakpoints.cs`, `Core/Write/PillarPlacer.cs`, `Core/Write/PathWriter.cs` | `IPathWriter`: break points, multi-pass pillar nudging over all paths, piece fitting with adaptive chord points | OTS 1126-1181, Ramp.cs 548-621 | U15 |
| Validators A | `Core/Validate/AfterWorld.cs`, `Core/Validate/ValidatorSet.cs`, `Core/Validate/Rules/ContractRules.cs` | `IAfterWorld`, `IValidatorSet`, V01-V14 | new | U16 |
| Validators B | `Core/Validate/Rules/WorldRules.cs`, `Core/Validate/Rules/QualityRules.cs` | V20-V28, W30-W33 | OTS 1426-1448, Ramp.cs 430-544 | U17 |
| Engine model | `Core/Validate/EngineSim.cs`, `Core/Validate/OverlayNetwork.cs` | `IEngineSim` and the after-network | new | U18 |
| Lift kit | `Core/Kit/LiftKit.cs` | `ILiftKit`: street over highway, highway over street, road over rail | OTS 995-1192, 751-798 | U19 |
| Service kit | `Core/Kit/ServiceKit.cs`, `Core/Kit/ExistingInterchangeGuard.cs` | `IServiceKit`: carriageways, ramp ends, junction/centre terminals, ramp zones, ramp writing | OTS 1272-1448, 1586-1702, 1613-1637 | U20 |
| Surgery and rings | `Core/Kit/StreetSurgery.cs`, `Core/Kit/RingKit.cs` | `IStreetSurgery` (Cut, SplitPath, CloseStreets, Trim), `IRingKit` | OTS 1704-1828, 2095-2167, 2405-2437 | U21 |
| Frontage kits | `Core/Kit/FrontageKit.cs`, `Core/Kit/UTurnKit.cs` | `IFrontageKit`, `IUTurnKit` | OTS 2225-2403 | U22 |
| Ramp ends and symmetry | `Core/Kit/RampEnds.cs`, `Core/Kit/SymmetryKit.cs` | `IRampEnds` (FromHit, Match, Options, Anchor), `ISymmetryKit` | Ramp.cs 96-150, 184-230, 320-379 | U23 |
| Router | `Core/Kit/Router.cs`, `Core/Kit/RampCrossings.cs` | `IRouter`: candidates, cheap-first checks, crossings, overlap, profile, G2 smoothing | Ramp.cs 257-318, 381-544 | U24 |
| Multi-ramp | `Core/Kit/MultiRampPlanner.cs` | `IMultiRampPlanner`: dependency order, transactions, joint levelling, AddPath | Ramp.cs 234-255 | U25 |
| Preset geometry | `Core/Kit/PresetGeometry.cs` | `IPresetGeometry`: Tangency, movements, ArcJob, ShareForks | Presets 125-239 | U26 |
| Style catalogue | `Core/Styles/StyleCatalog.cs`, `Core/Styles/StyleRegistry.cs`, `Core/Styles/LiftThen.cs` | `StyleInfo` data with the author's copy, `IStyleRegistry`, the at-grade stage-1 wrapper | mjs 21-59 | U27 |
| Styles: lift | `Core/Styles/OverpassStyle.cs`, `Core/Styles/RailOverpassStyle.cs`, `Core/Styles/FixDirectionStyle.cs` | Overpass, road over rail, flip repair | OTS 604-798, 2459-2513 | U28 |
| Styles: service | `Core/Styles/ServiceStyleBase.cs`, `Core/Styles/DiamondSpuiStyles.cs`, `Core/Styles/DumbbellStyle.cs` | Diamond, SPUI, Dumbbell | OTS 1512-1778 | U29 |
| Styles: frontage, best fit | `Core/Styles/FrontageStyle.cs`, `Core/Styles/BestFitStyle.cs` | Frontage with U-turns, Best fit policy | OTS 1463-1509, 2226-2293 | U30 |
| Styles: highway end | `Core/Styles/HighwayEndStyle.cs` | Avenue merge and roundabout | OTS 1883-2223 | U31 |
| Styles: free ramp | `Core/Styles/FreeRampStyle.cs` | Two-click ramp with symmetry | Ramp.cs 87-182 | U32 |
| Styles: four-way | `Core/Styles/FourWayFamily.cs`, `Core/Styles/ParcloStyle.cs` | Cloverleaf, Cloverstack, Stack, Turbine; Partial cloverleaf A4 | Presets 154-311 | U33 |
| Styles: stem | `Core/Styles/StemFamily.cs` | Trumpet, Directional T, trim-back | Presets 378-478 | U34 |
| Autofit | `Core/Autofit/VariantTable.cs`, `Core/Autofit/AutofitSearch.cs`, `Core/Autofit/ConfigDiff.cs` | `IAutofitFactory`, `IAutofitSearch`, variant table, fixability filter, fingerprint dedupe, speculative stage 2, least-red | OTS 404-492 | U35 |
| Pipeline | `Core/Pipeline/PlanJob.cs`, `Core/Pipeline/PlanService.cs`, `Core/Pipeline/Planner.cs` | `IPlanJob`, `IPlanService` (LRU cache, sync time-sliced and optional worker), `IPlanner` | OTS 333-358 | U36 |
| Composition root | `Core/Pipeline/CoreServicesFactory.cs` | `CoreServicesFactory.CreateDefault()` wires every implementation | new | U37 |
| Session | `Core/Session/ToolSession.cs` | `IToolSession` state machine | OTS 142-246 | U38 |
| Text | `Core/Text/Phrases.cs`, `Core/Text/Narrator.cs`, `Core/Text/RedExplainer.cs` | All English strings, `INarrator`, red descriptions with compass | OTS 360-402, 494-518; Ramp.cs 623-643 | U39 |
| Settings and panel model | `Core/Config/SettingsSchema.cs`, `Core/Panel/PanelModel.cs`, `Core/Common/Json.cs` | Setting specs and clamps; `IPanelModel` JSON; tiny JSON writer and reader | InterchangesUISystem.cs 25-145 | U40 |
| Capture codec | `Core/Diagnostics/CaptureCodec.cs` | `ICaptureCodec` | new | U41 |
| Adapter: mod and settings | `Game/Mod.cs`, `Game/StudioSettings.cs`, `Game/LocaleSource.cs` | Load order, keybinding, persisted PanelState, LegacySettings + LegacyImport, locale | Mod.cs, Settings.cs | U42 |
| Adapter: reader | `Game/NetworkReader.cs`, `Game/PrefabReader.cs`, `Game/GameTerrain.cs` | Change detection, time-sliced ECS read to `SnapshotData`, prefabs, terrain patch | OTS 88-112, Index.cs | U43 |
| Adapter: writer | `Game/DefinitionWriter.cs` | Verbatim Emit / DeleteDef recipe, StillValid | OTS 2602-2643 | U44 |
| Adapter: red and log | `Game/RedReader.cs`, `Game/Log.cs` | Temp+Error to `RedReport`; brace-safe logging | OTS 129-138, 360-402, 494-510 | U45 |
| Adapter: names, camera, captures | `Game/NameKeeper.cs`, `Game/CameraJumper.cs`, `Game/CaptureWriter.cs` | UI-phase rename, camera jump, capture files | OTS 249, 2519-2545, 552-566 | U46 |
| Adapter: tool system | `Game/StudioToolSystem.cs` | ToolBaseSystem subclass, frame skeleton | OTS 88-246 | U47 |
| Adapter: UI system | `Game/StudioUISystem.cs` | Bindings, name ticks, PanelState persistence | InterchangesUISystem.cs | U48 |
| UI module | `UI/InterchangeStudio.mjs` | Toolbar button, panel (catalogue-driven) | UI/ClaudeInterchanges.mjs | U49 |
| UI styles and icons | `UI/InterchangeStudio.css`, `UI/images/is-*.svg` | Stylesheet, tile schematics, toolbar icon | UI/ClaudeInterchanges.css, UI/images/ci-*.svg | U50 |
| UI mock | `preview/panel.html` | Stateful browser mock driven by Harness-written catalog.json | preview/panel.html | U51 |
| Test support | `Testing/*.cs` | City builder, scenarios, invariant checks, SVG, approvals, fuzz | Tests/RouterTests.cs | U52-U57 |
| Build | `Directory.Build.props`, `InterchangeStudio.csproj`, `Local.props.example`; `Build/CorePurity/*`, `Tests/*.csproj`, `Harness/*.csproj` | Build, purity, deploy | ClaudeInterchanges.csproj | U01-U02 |
| Spikes | `Spikes/SpikeProbe.csproj`, `Spikes/SpikeSystem.cs` | Phase-0 in-game probes | new | U58 |

---

## 6. Shared contracts (generated from Core/Contracts.cs)

Everything below is `Core/Contracts.cs`, region by region; together the blocks are the whole file. It compiles as-is (verified on netstandard2.1 and net8.0, LangVersion 9). All Core types live in `namespace InterchangeStudio.Core`; the panel view-model contract is in `InterchangeStudio.UI`; stable ids are in `InterchangeStudio.Game`.

How to read it:
- **Data** (records, init-only classes) is immutable once built. The exceptions are `FitCandidate.Verdict` and `RedCount`, which the autofit search updates when the game reports.
- **Interfaces** are the seams between units. Implementations are registered in `CoreServices` by the composition root (U37). Tests may wire fakes.
- **Behaviour in this file is limited to tiny, proven helpers** that must not differ between units.

### 6.0 Header (usings and the C# 9 polyfill)
<!-- contract:Header -->
```csharp
// =====================================================================================================
// Interchange Studio - Core/Contracts.cs
//
// The frozen, shared contract that every unit compiles against. It is PURE: it uses the BCL,
// Unity.Mathematics and Colossal.Mathematics.Bezier4x3 only (no Game.*, Unity.Entities, UnityEngine,
// Colossal.UI). The Bezier4x3 alias below is deliberate: nothing else from Colossal.Mathematics can be
// named in this file.
//
// Rules for changing it:
//   * Change only by agreement. DESIGN.md section 6 is generated from the #region blocks of this file.
//   * C# 9 only (netstandard2.1): records, init, with, switch expressions. No record struct, no
//     file-scoped namespaces, no global usings, no default interface methods.
//   * Behaviour lives in the units. This file only holds data types, interfaces, ids and a few tiny,
//     proven helpers (Fnv64, StableHashing, Rect2, TrafficSide, Splits, SizePresets, FitVariant.Apply,
//     PlanKey.For, LegacyMap) that many units need and that must not differ between them.
// =====================================================================================================
using System;
using System.Collections.Generic;
using System.Reflection;
using System.Threading;
using Unity.Mathematics;
using Bezier4x3 = Colossal.Mathematics.Bezier4x3;
using InterchangeStudio.Core;

#if !NET5_0_OR_GREATER
namespace System.Runtime.CompilerServices
{
    /// <summary>Lets C# 9 records and init accessors compile on netstandard2.1 (net8 has its own).</summary>
    internal static class IsExternalInit { }
}
#endif

```

### 6.1 Common
Fnv64, StableHashing, Rect2, TrafficSide (the only place traffic side is decided), logging and budget.
<!-- contract:Common -->
```csharp
namespace InterchangeStudio.Core
{
    /// <summary>
    /// Stable 64-bit FNV-1a. Used for fingerprints, cache keys and random seeds. string.GetHashCode is
    /// randomised on net8, so never use it for anything that must match between tests and the game.
    /// Mutating struct: <c>h.Add(x)</c> updates h in place and also returns it, so chaining works.
    /// </summary>
    public struct Fnv64
    {
        public const ulong OffsetBasis = 14695981039346656037UL;
        public const ulong Prime = 1099511628211UL;
        public ulong Value;

        public static Fnv64 Start() { Fnv64 h; h.Value = OffsetBasis; return h; }
        public Fnv64 Add(ulong v)
        {
            unchecked { for (int i = 0; i < 8; i++) { Value ^= (byte)(v >> (8 * i)); Value *= Prime; } }
            return this;
        }
        public Fnv64 Add(long v) => Add(unchecked((ulong)v));
        public Fnv64 Add(int v) => Add(unchecked((ulong)(uint)v));
        public Fnv64 Add(bool v) => Add(v ? 1UL : 2UL);
        public Fnv64 Add(float v, float quantum) => Add(float.IsNaN(v) ? long.MinValue : unchecked((long)Math.Round(v / quantum)));
        public Fnv64 Add(float3 p, float quantum) { Add(p.x, quantum); Add(p.y, quantum); return Add(p.z, quantum); }
        public Fnv64 Add(string s)
        {
            if (s == null) return Add(ulong.MaxValue);
            foreach (char c in s) Add((ulong)c);
            return Add((long)s.Length);
        }
        public string Hex => Value.ToString("x16");
    }

    /// <summary>
    /// Stable hash of every public settable (init) property of a record, sorted by name, recursing into
    /// nested records. Floats are quantised to 1e-4. PlanConfig and EngineRules use it, so a new setting
    /// is part of every cache key automatically (the old hand-written hover key missed new settings).
    /// </summary>
    public static class StableHashing
    {
        public static ulong Of(object value) { var h = Fnv64.Start(); AddObject(ref h, value, 0); return h.Value; }

        static void AddObject(ref Fnv64 h, object value, int depth)
        {
            if (value == null) { h.Add(ulong.MaxValue - 1); return; }
            var props = value.GetType().GetProperties(BindingFlags.Public | BindingFlags.Instance);
            Array.Sort(props, (a, b) => string.CompareOrdinal(a.Name, b.Name));
            foreach (var p in props)
            {
                if (!p.CanWrite || p.GetIndexParameters().Length != 0) continue;   // computed properties are not state
                h.Add(p.Name);
                AddValue(ref h, p.GetValue(value), depth);
            }
        }

        static void AddValue(ref Fnv64 h, object v, int depth)
        {
            switch (v)
            {
                case null: h.Add(ulong.MaxValue - 1); break;
                case float f: h.Add(f, 1e-4f); break;
                case double d: h.Add((float)d, 1e-4f); break;
                case int i: h.Add(i); break;
                case long l: h.Add(l); break;
                case bool b: h.Add(b); break;
                case string s: h.Add(s); break;
                case Enum e: h.Add(Convert.ToInt64(e)); break;
                case float2 f2: h.Add(f2.x, 1e-4f); h.Add(f2.y, 1e-4f); break;
                case float3 f3: h.Add(f3, 1e-4f); break;
                default: if (depth < 4) AddObject(ref h, v, depth + 1); else h.Add(v.ToString()); break;
            }
        }
    }

    /// <summary>Axis-aligned box in the x/z plane (x = east, y component = world z = north).</summary>
    public readonly struct Rect2
    {
        public readonly float2 Min, Max;
        public Rect2(float2 min, float2 max) { Min = min; Max = max; }
        public static Rect2 Empty => new Rect2(new float2(float.MaxValue), new float2(float.MinValue));
        public bool IsEmpty => Min.x > Max.x || Min.y > Max.y;
        public float2 Center => (Min + Max) * 0.5f;
        public float2 Size => IsEmpty ? float2.zero : Max - Min;
        public Rect2 Include(float2 p) => new Rect2(math.min(Min, p), math.max(Max, p));
        public Rect2 Include(Rect2 r) => r.IsEmpty ? this : IsEmpty ? r : new Rect2(math.min(Min, r.Min), math.max(Max, r.Max));
        public Rect2 Grow(float margin) => IsEmpty ? this : new Rect2(Min - margin, Max + margin);
        public bool Overlaps(Rect2 r) => !(IsEmpty || r.IsEmpty || r.Min.x > Max.x || r.Max.x < Min.x || r.Min.y > Max.y || r.Max.y < Min.y);
        public bool Contains(float2 p) => p.x >= Min.x && p.x <= Max.x && p.y >= Min.y && p.y <= Max.y;
        public static Rect2 Around(float2 centre, float half) => new Rect2(centre - half, centre + half);
        /// <summary>Conservative bounds of a Bezier: the curve lies inside its control hull.</summary>
        public static Rect2 OfHull(in Bezier4x3 c) => Empty.Include(c.a.xz).Include(c.b.xz).Include(c.c.xz).Include(c.d.xz);
        public override string ToString() => "[" + Min.x.ToString("0") + "," + Min.y.ToString("0") + " .. " + Max.x.ToString("0") + "," + Max.y.ToString("0") + "]";
    }

    public enum Handedness : byte { Right = 0, Left = 1 }

    /// <summary>
    /// The ONLY place the traffic side is decided (source rule: no literal right-vectors such as
    /// (t.z, 0, -t.x) anywhere else in Core). CS2 world space: x east, z north, y up; headings run
    /// anticlockwise from +x towards +z, so a left turn has cross(a, b) &gt; 0.
    /// </summary>
    public readonly struct TrafficSide
    {
        public readonly Handedness Hand;
        public TrafficSide(Handedness hand) { Hand = hand; }
        public static readonly TrafficSide Right = new TrafficSide(Handedness.Right);
        public bool IsRight => Hand == Handedness.Right;

        /// <summary>Unit vector (x/z) on the side exits and entrances use, for travel direction d. RHT: (d.y, -d.x).</summary>
        public float2 Outer(float2 travel)
        {
            float2 d = math.normalizesafe(travel);
            return IsRight ? new float2(d.y, -d.x) : new float2(-d.y, d.x);
        }
        public float2 Inner(float2 travel) => -Outer(travel);
        public float3 Outer3(float3 tangent) { float2 o = Outer(tangent.xz); return new float3(o.x, 0f, o.y); }

        /// <summary>+1: rings circulate anticlockwise seen from above (atan2 ascending), which is RHT; -1 for LHT.</summary>
        public int RingSign => IsRight ? 1 : -1;

        /// <summary>True when turning from heading a to heading b crosses oncoming traffic (left in RHT, right in LHT).</summary>
        public bool IsFarSideTurn(float2 a, float2 b) { float cr = a.x * b.y - a.y * b.x; return IsRight ? cr > 0f : cr < 0f; }
    }

    /// <summary>Plain-string log sink. Core never formats for the game logger; the adapter strips braces and caps length.</summary>
    public interface IPlanLog
    {
        bool Verbose { get; }
        void Info(string line);
        void Warn(string line);
    }

    public sealed class NullLog : IPlanLog
    {
        public static readonly NullLog Instance = new NullLog();
        public bool Verbose => false;
        public void Info(string line) { }
        public void Warn(string line) { }
    }

    /// <summary>Time budget for incremental work. Adapter: a Stopwatch of a few ms per frame. Tests: unlimited.</summary>
    public interface IBudget { bool Exhausted { get; } }

    public sealed class UnlimitedBudget : IBudget
    {
        public static readonly UnlimitedBudget Instance = new UnlimitedBudget();
        public bool Exhausted => false;
    }

    /// <summary>Thrown when a planner breaks a construction rule (for example an end 0.6 m off its join point). Surfaces as a Fatal violation.</summary>
    public sealed class PlannerBugException : Exception
    {
        public PlannerBugException(string message) : base(message) { }
    }
}
```

### 6.2 Model
Ids that mirror Entity, prefabs, the network snapshot interface and the raycast hit.
<!-- contract:Model -->
```csharp
namespace InterchangeStudio.Core
{
    /// <summary>Mirrors Game Entity(Index, Version) one-to-one, so the adapter converts without a lookup table. Index &lt; 0 = synthetic (tests, EngineSim).</summary>
    public readonly struct EdgeId : IEquatable<EdgeId>, IComparable<EdgeId>
    {
        public readonly int Index, Version;
        public EdgeId(int index, int version) { Index = index; Version = version; }
        public static readonly EdgeId None = default;
        public bool IsNone => Index == 0 && Version == 0;
        public bool IsSynthetic => Index < 0;
        public bool Equals(EdgeId o) => Index == o.Index && Version == o.Version;
        public override bool Equals(object o) => o is EdgeId e && Equals(e);
        public override int GetHashCode() => (Index * 397) ^ Version;
        public int CompareTo(EdgeId o) => Index != o.Index ? Index.CompareTo(o.Index) : Version.CompareTo(o.Version);
        public static bool operator ==(EdgeId a, EdgeId b) => a.Equals(b);
        public static bool operator !=(EdgeId a, EdgeId b) => !a.Equals(b);
        public override string ToString() => "e" + Index + "." + Version;
    }

    public readonly struct NodeId : IEquatable<NodeId>, IComparable<NodeId>
    {
        public readonly int Index, Version;
        public NodeId(int index, int version) { Index = index; Version = version; }
        public static readonly NodeId None = default;
        public bool IsNone => Index == 0 && Version == 0;
        public bool IsSynthetic => Index < 0;
        public bool Equals(NodeId o) => Index == o.Index && Version == o.Version;
        public override bool Equals(object o) => o is NodeId n && Equals(n);
        public override int GetHashCode() => (Index * 397) ^ Version;
        public int CompareTo(NodeId o) => Index != o.Index ? Index.CompareTo(o.Index) : Version.CompareTo(o.Version);
        public static bool operator ==(NodeId a, NodeId b) => a.Equals(b);
        public static bool operator !=(NodeId a, NodeId b) => !a.Equals(b);
        public override string ToString() => "n" + Index + "." + Version;
    }

    /// <summary>Mirrors the prefab Entity(Index, Version).</summary>
    public readonly struct PrefabId : IEquatable<PrefabId>
    {
        public readonly int Index, Version;
        public PrefabId(int index, int version) { Index = index; Version = version; }
        public static readonly PrefabId None = default;
        public bool IsNone => Index == 0 && Version == 0;
        public bool Equals(PrefabId o) => Index == o.Index && Version == o.Version;
        public override bool Equals(object o) => o is PrefabId p && Equals(p);
        public override int GetHashCode() => (Index * 397) ^ Version;
        public static bool operator ==(PrefabId a, PrefabId b) => a.Equals(b);
        public static bool operator !=(PrefabId a, PrefabId b) => !a.Equals(b);
        public override string ToString() => "p" + Index + "." + Version;
    }

    /// <summary>What a net piece is. Highway = RoadData UseHighwayRules (ramp prefabs are highways too). Street = Road and not Highway. Rail = TrainTrack and not Road.</summary>
    [Flags]
    public enum NetKind : ushort
    {
        None = 0,
        Road = 1,
        Highway = 2,
        Street = 4,
        OneWay = 8,
        Rail = 16,
        Tram = 32,
        Path = 64,
        Other = 128,
        Tunnel = 256,     // set by the reader when the piece runs more than 3 m below terrain
        Ramp = 512,       // a highway ramp prefab ("Highway Oneway - 1/2 lane", "Highway Twoway")
        Raised = 1024,    // either end elevation above RaisedNode
        All = 0xFFFF,
    }

    [Flags]
    public enum PrefabCapabilities : byte { None = 0, Ramp = 1, Ring = 2, Avenue = 4, TwoWayRamp = 8 }

    /// <summary>One net prefab, read once by the adapter's PrefabReader. Name is the internal (locale-independent) prefab name.</summary>
    public sealed record PrefabInfo
    {
        public PrefabId Id { get; init; }
        public string Name { get; init; }
        public NetKind Kind { get; init; }
        public float Width { get; init; } = 8f;            // NetGeometryData.m_DefaultWidth
        public int LanesPerDirection { get; init; }        // 0 = unknown (name fallback in PrefabTable)
        public float MaxEdgeLength { get; init; }          // m_EdgeLengthRange.max; 0 = unknown (EngineRules.MaxPiece applies)
        public float MaxElevatedLength { get; init; }      // m_ElevatedLength; 0 = unknown
        public float MinNodeOffset { get; init; }          // m_MinNodeOffset
        public float MaxSlope { get; init; }               // m_MaxSlopeSteepness; 0 = unknown
        public bool Is(NetKind k) => (Kind & k) != 0;
        public float Half => Width * 0.5f;
    }

    /// <summary>Prefab lookups and role picks. Implemented in Core (pure, testable): deterministic, exact vanilla names first, then name-sorted fuzzy match with skip lists.</summary>
    public interface IPrefabTable
    {
        IReadOnlyList<PrefabInfo> All { get; }
        PrefabInfo Get(PrefabId id);                         // throws KeyNotFoundException
        bool TryGet(PrefabId id, out PrefabInfo prefab);
        PrefabInfo ByName(string internalName);              // null when absent
        PrefabCapabilities Capabilities { get; }
        PrefabInfo Ramp(int lanes);                          // "Highway Oneway - 1 lane" / "- 2 lanes"; each falls back to the other; null => capability missing
        PrefabInfo TwoWayRamp();                             // narrowest "Highway"+"Twoway"; falls back to Avenue(null, 16)
        PrefabInfo Ring(float minWidth);                     // narrowest one-way non-highway >= minWidth (skip list applied); falls back to >= 7.5 m
        PrefabInfo Avenue(PrefabInfo crossStreet, float want); // cross street's own prefab if two-way, non-highway, >= 16 m; else widest ordinary road <= want * 1.1
    }

    /// <summary>Raw copy of CompositionFlags (General, Left, Right) from the Upgraded component.</summary>
    public readonly struct UpgradeBits : IEquatable<UpgradeBits>
    {
        public readonly uint General, Left, Right;
        public readonly bool Present;                        // the source edge had an Upgraded component
        public UpgradeBits(uint general, uint left, uint right, bool present) { General = general; Left = left; Right = right; Present = present; }
        public static readonly UpgradeBits None = default;
        public bool Any => Present && (General | Left | Right) != 0;
        /// <summary>Swap the side flags. Used ONLY when a course is laid against its source edge's own direction (FixDirection).</summary>
        public UpgradeBits Mirrored() => new UpgradeBits(General, Right, Left, Present);
        public bool Equals(UpgradeBits o) => General == o.General && Left == o.Left && Right == o.Right && Present == o.Present;
        public override bool Equals(object o) => o is UpgradeBits u && Equals(u);
        public override int GetHashCode() => (int)(General * 31 + Left * 17 + Right * 7) ^ (Present ? 1 : 0);
        public override string ToString() => Present ? "upg " + General.ToString("x") + "/" + Left.ToString("x") + "/" + Right.ToString("x") : "upg none";
    }

    /// <summary>A live edge (never Temp, never Deleted). One-way traffic runs Start to End.</summary>
    public sealed class EdgeInfo
    {
        public EdgeId Id { get; init; }
        public NodeId Start { get; init; }
        public NodeId End { get; init; }
        public Bezier4x3 Curve { get; init; }      // world space, absolute y, Start -> End orientation
        public float Length { get; init; }         // Curve.m_Length (the game's own length)
        public PrefabId Prefab { get; init; }
        public NetKind Kind { get; init; }         // prefab kind plus Tunnel / Raised for this piece
        public float Width { get; init; }
        public UpgradeBits Upgrades { get; init; }
        public float2 Elevation { get; init; }     // above terrain at Start / End (node elevation mean)
        public int AggregateKey { get; init; }     // Aggregated.m_Aggregate.Index; grouping and name lookup only
        public bool Is(NetKind k) => (Kind & k) != 0;
        public float Half => Width * 0.5f;
    }

    /// <summary>Legs of a node, built ONLY from edges whose Start or End is the node (never from ConnectedEdge). Immutable; replaces the old shared m_Hw/m_Other lists.</summary>
    public sealed class NodeLegs
    {
        public static readonly NodeLegs Empty = new NodeLegs();
        public EdgeId[] Highway { get; init; } = Array.Empty<EdgeId>();   // mainline and ramp highway edges ending here
        public EdgeId[] Ramp { get; init; } = Array.Empty<EdgeId>();      // subset of Highway that are ramp prefabs
        public EdgeId[] Street { get; init; } = Array.Empty<EdgeId>();
        public EdgeId[] Rail { get; init; } = Array.Empty<EdgeId>();
        public EdgeId[] Other { get; init; } = Array.Empty<EdgeId>();
        public int RoadCount => Highway.Length + Street.Length;
        public int Total => Highway.Length + Street.Length + Rail.Length + Other.Length;
        public bool IsCrossing => Highway.Length == 2 && Street.Length >= 1;
        public bool IsRailCrossing => Rail.Length > 0 && RoadCount >= 2;
        public bool HasRail => Rail.Length > 0;
    }

    public sealed class NodeInfo
    {
        public NodeId Id { get; init; }
        public float3 Position { get; init; }
        public float Elevation { get; init; }      // mean of Elevation.m_Elevation; 0 when absent
        public float ElevationMax { get; init; }   // max of Elevation.m_Elevation; raised when > EngineRules.RaisedNode
        public NodeLegs Legs { get; init; } = NodeLegs.Empty;   // filled by ISnapshotBuilder
    }

    /// <summary>Terrain height. Must be pure and thread-safe (the adapter copies a height patch; tests use flat or sloped functions).</summary>
    public interface ITerrain { float Height(float2 xz); }

    /// <summary>Arc length to Bezier t and back, for one edge (33+ samples, binary search).</summary>
    public interface IArcTable
    {
        float Length { get; }
        float TAt(float s);
        float SAt(float t);
    }

    /// <summary>
    /// Immutable view of the live road and rail network at one version. Implemented by the Model unit
    /// (NetworkSnapshot) and by EngineSim's overlay (the network as it would be after a plan).
    /// </summary>
    public interface INetwork
    {
        long Version { get; }                     // bumps only on a semantic content change, never on preview Temp churn
        IPrefabTable Prefabs { get; }
        ITerrain Terrain { get; }
        int EdgeCount { get; }
        int NodeCount { get; }
        bool TryEdge(EdgeId id, out EdgeInfo edge);
        EdgeInfo Edge(EdgeId id);                  // throws KeyNotFoundException
        bool TryNode(NodeId id, out NodeInfo node);
        NodeInfo Node(NodeId id);
        IEnumerable<EdgeInfo> AllEdges { get; }    // deterministic order (by id)
        IEnumerable<NodeInfo> AllNodes { get; }
        /// <summary>Edges whose control-hull box overlaps <paramref name="box"/> and whose Kind has any bit of <paramref name="mask"/>. Each edge once; caller does the exact distance test.</summary>
        void EdgesNear(Rect2 box, NetKind mask, List<EdgeInfo> into);
        void NodesNear(Rect2 box, List<NodeInfo> into);
        /// <summary>Highest per-cell change stamp over the box. Edits elsewhere in the city do not change it.</summary>
        long RegionVersion(Rect2 box);
        IArcTable Arc(EdgeId id);                  // lazy, memoised, thread-safe
        NodeId Other(EdgeInfo edge, NodeId node);
        /// <summary>Rendered road name of the edge's aggregate if the reader captured it, else the prefab name. For descriptions only; name RESTORE is captured from the live edge on the click frame.</summary>
        string NameOf(EdgeId id);
    }

    /// <summary>What the adapter hands to the snapshot builder (and what captures store).</summary>
    public sealed class SnapshotData
    {
        public IReadOnlyList<EdgeInfo> Edges { get; init; } = Array.Empty<EdgeInfo>();
        public IReadOnlyList<NodeInfo> Nodes { get; init; } = Array.Empty<NodeInfo>();   // Legs may be empty; the builder fills them
        public IPrefabTable Prefabs { get; init; }
        public ITerrain Terrain { get; init; }
        public IReadOnlyDictionary<int, string> AggregateNames { get; init; } = new Dictionary<int, string>();
    }

    public interface ISnapshotBuilder
    {
        /// <summary>
        /// Builds legs, the 128 m grid and per-cell stamps. Returns <paramref name="previous"/> itself (same
        /// Version) when no edge or node changed in content; otherwise a new snapshot with Version + 1 whose
        /// changed cells carry the new stamp.
        /// </summary>
        INetwork Build(SnapshotData data, INetwork previous);
    }

    /// <summary>Raycast result: the hit can be an edge or a node (handle both).</summary>
    public readonly struct Hit
    {
        public readonly EdgeId Edge;
        public readonly NodeId Node;
        public readonly float3 Position;            // RaycastHit.m_HitPosition
        public readonly float CurveT;               // RaycastHit.m_CurvePosition on the hit edge
        public Hit(EdgeId edge, NodeId node, float3 position, float curveT) { Edge = edge; Node = node; Position = position; CurveT = curveT; }
        public bool OnEdge => !Edge.IsNone;
        public bool OnNode => !Node.IsNone;
    }
}
```

### 6.3 Geometry
Splits, paths, chains and curve maths.
<!-- contract:Geometry -->
```csharp
namespace InterchangeStudio.Core
{
    public enum SplitKind : byte { AtStartNode, AtEndNode, Split }

    public readonly struct SplitDecision
    {
        public readonly SplitKind Kind;
        public readonly float U;                    // arc-length fraction along the edge (Start -> End) when Kind == Split
        public SplitDecision(SplitKind kind, float u) { Kind = kind; U = u; }
        public bool IsNode => Kind != SplitKind.Split;
    }

    /// <summary>
    /// Where a new road may split an existing piece: at least MinSplit metres from either end, so neither
    /// leftover is a sliver the game rejects as an invalid shape. Ported verbatim from RampRouter.cs.
    /// Works on the ARC-LENGTH fraction u; callers convert u to Bezier t with IArcTable.
    /// Source rule: only AttachFactory calls Decide (every split goes through it).
    /// </summary>
    public static class Splits
    {
        public const float MinSplit = 30f;

        /// <summary>Old API: returns 0 or 1 to mean "use that end's node", otherwise a clamped fraction.</summary>
        public static float Safe(float length, float u, float minSplit = MinSplit)
        {
            if (length < minSplit * 2f) return u < 0.5f ? 0f : 1f;
            float lo = minSplit / length, hi = 1f - lo;
            if (u < lo * 0.5f) return 0f;
            if (u > 1f - lo * 0.5f) return 1f;
            return math.clamp(u, lo, hi);
        }

        public static SplitDecision Decide(float length, float u, float minSplit = MinSplit)
        {
            float v = Safe(length, u, minSplit);
            if (v <= 0f) return new SplitDecision(SplitKind.AtStartNode, 0f);
            if (v >= 1f) return new SplitDecision(SplitKind.AtEndNode, 1f);
            return new SplitDecision(SplitKind.Split, v);
        }
    }

    /// <summary>A position and unit travel direction in the x/z plane.</summary>
    public readonly struct Pose2
    {
        public readonly float2 Pos, Dir;
        public Pose2(float2 pos, float2 dir) { Pos = pos; Dir = math.normalizesafe(dir); }
        public float Heading => math.atan2(Dir.y, Dir.x);
    }

    /// <summary>One 2D intersection of two curves. TA/TB are Bezier t on each; YA/YB absolute heights there.</summary>
    public readonly struct CrossHit
    {
        public readonly float2 Point;
        public readonly float TA, TB, YA, YB;
        public CrossHit(float2 point, float ta, float tb, float ya, float yb) { Point = point; TA = ta; TB = tb; YA = ya; YB = yb; }
        public float Dy => YA - YB;
    }

    /// <summary>A planar path in travel order (y ignored). Prims, routed ramps, tapers, chain offsets and chains all implement it.</summary>
    public interface IPath2
    {
        float Length { get; }
        float2 Pos(float s);
        float2 Dir(float s);
        float Curvature(float s);                   // signed 1/m, + = turning left (anticlockwise from above)
        Bezier4x3 Piece(float s0, float s1);        // flat (y = 0): exact inside one primitive, fitted across joints
        float MaxPiece(float s);                    // 80 m, or min(80, 1.3 r) on arcs
        IReadOnlyList<float> Joints { get; }        // primitive boundaries: preferred break points
        string Word { get; }                        // e.g. "LSR", "taper", "chain"; for logs and descriptions
    }

    /// <summary>One existing edge inside a chain, oriented in CHAIN direction.</summary>
    public sealed class ChainSeg
    {
        public EdgeId Edge { get; init; }
        public NodeId From { get; init; }
        public NodeId To { get; init; }
        public Bezier4x3 Curve { get; init; }       // oriented From -> To (inverted copy of the edge curve when Forward is false)
        public float S0 { get; init; }              // chain distance where this seg starts
        public float Length { get; init; }          // the edge's game length
        public bool Forward { get; init; }          // chain runs Start -> End of the edge (= its traffic for one-way roads)
        public PrefabId Prefab { get; init; }
        public UpgradeBits Upgrades { get; init; }
        public float2 Elevation { get; init; }      // above terrain at From / To
        public float S1 => S0 + Length;
    }

    /// <summary>Chain distance converted to the edge's OWN parameter (Forward ? t : 1 - t).</summary>
    public readonly struct EdgeParam
    {
        public readonly EdgeId Edge;
        public readonly float T;                    // Bezier t in the edge's Start -> End parameterisation
        public readonly float U;                    // arc-length fraction in edge space
        public readonly float Local;                // metres from the seg's chain start
        public readonly bool Forward;
        public EdgeParam(EdgeId edge, float t, float u, float local, bool forward) { Edge = edge; T = t; U = u; Local = local; Forward = forward; }
    }

    /// <summary>An ordered string of existing edges (traffic order for carriageways). Implemented in the Network unit.</summary>
    public interface IChain : IPath2
    {
        IReadOnlyList<ChainSeg> Segs { get; }
        float Total { get; }
        ChainSeg SegAt(float s, out float local);   // binary search on S0
        float3 Position(float s);                   // absolute (y = road height)
        float3 Tangent(float s);                    // unit, chain direction
        float ElevationAt(float s);                 // above terrain
        float2 Outer(float s, TrafficSide side);    // exit side of the chain direction
        EdgeParam EdgeParamAt(float s);
        float DistanceOf(NodeId node);              // NaN when the node is not on the chain
        float Project(float3 p, float s0, float s1); // nearest chain distance in [s0, s1]
        IChain Reverse();
    }

    /// <summary>Pure curve maths (Geometry unit). FitCurve is a verbatim port of Game.Net.NetUtils.FitCurve.</summary>
    public interface ICurveKit
    {
        Bezier4x3 Fit(float3 a, float3 startTangent, float3 endTangent, float3 d);
        Bezier4x3 Fit(float3 a, float3 startTangent, float3 middle, float3 endTangent, float3 d);
        Bezier4x3 Straight(float3 a, float3 d);
        Bezier4x3 Cut(in Bezier4x3 c, float t0, float t1);
        Bezier4x3 Invert(in Bezier4x3 c);
        float3 Position(in Bezier4x3 c, float t);
        float3 Tangent(in Bezier4x3 c, float t);
        float Length(in Bezier4x3 c);
        IArcTable ArcTable(in Bezier4x3 c, float gameLength);
        float DistanceXZ(in Bezier4x3 c, float2 p, out float t);

        /// <summary>One cubic arc piece about centre, angles atan2(z, x); |a1 - a0| &lt;= 135 deg; handles 4/3 tan(da/4) r; y lerped at 1/3, 2/3.</summary>
        Bezier4x3 Arc(float2 centre, float radius, float a0, float a1, float y0, float y1);
        void ArcPieces(float2 centre, float radius, float a0, float a1, float y0, float y1, float maxDeg, List<Bezier4x3> into);
        /// <summary>Single-cubic semicircle from a to b (k = 4/3 r), leaving a along travelAtA. Texas U-turn.</summary>
        Bezier4x3 Semicircle(float3 a, float3 b, float3 travelAtA);

        /// <summary>EVERY 2D intersection of two curves (16 x 16 polyline, bbox reject). Shared endpoints excluded when asked.</summary>
        int Cross2D(in Bezier4x3 a, in Bezier4x3 b, List<CrossHit> into, bool excludeSharedEnds);

        IPath2 Line(float2 a, float2 b);
        IPath2 Concat(IReadOnlyList<IPath2> parts);
        /// <summary>Path parallel to a chain between s0 and s1 at a lateral offset (+ = Outer side), so ramps follow a curved highway.</summary>
        IPath2 Offset(IChain chain, float s0, float s1, Func<float, float> lateral, TrafficSide side);
        /// <summary>Quintic (G2) taper: lateral w(u) = offset * (10u^3 - 15u^4 + 6u^5). Diverge starts ON the centreline at s; merge ends on it at s.</summary>
        IPath2 Taper(IChain chain, float s, TaperSpec spec, bool diverge, TrafficSide side);
    }

    public sealed record TaperSpec
    {
        public float Length { get; init; } = 100f;  // along the road; must be >= max(TaperMin, TaperRatio * |Offset|)
        public float Offset { get; init; }          // lateral offset (m) reached at the far end, + = Outer side
    }

    public sealed class SmoothStats
    {
        public float MinRadius { get; init; }
        public float MaxCurvatureJump { get; init; }
        public bool UsedFallback { get; init; }
        public int Iterations { get; init; }
    }

    /// <summary>Turns a G1 Dubins path into a curvature-continuous one. Primary: clothoid smoother seeded with the attached roads' curvature (k0, k1). Fallback: the ported Laplacian smoother with radius pre-inflation.</summary>
    public interface IAlignmentSmoother
    {
        IPath2 Smooth(IPath2 raw, float minRadius, float k0, float k1, out SmoothStats stats);
    }
}
```

### 6.4 Config
Styles, engine rules, immutable PlanConfig, size presets and settings.
<!-- contract:Config -->
```csharp
namespace InterchangeStudio.Core
{
    /// <summary>Every style. Values 0-7 match the old ToolMode; 10 + old PresetStyle for presets (LegacyMap relies on this).</summary>
    public enum StyleId
    {
        Overpass = 0, Diamond = 1, Frontage = 2, Spui = 3, Dumbbell = 4, BestFit = 5, HighwayEnd = 6, FreeRamp = 7,
        Cloverleaf = 10, Cloverstack = 11, Stack = 12, Trumpet = 13, Turbine = 14, DirectionalT = 15, Parclo = 16,
        FixDirection = 20,
        RailOverpass = 30,   // internal: every mode routes a rail level crossing here
    }

    public enum LiftPreference : byte { StreetOver = 0, HighwayOver = 1 }
    public enum SizePreset : byte { Compact = 0, Standard = 1, Spacious = 2, Custom = 3 }
    public enum RampLength : byte { Compact = 0, Gentle = 1 }
    public enum EndStyle : byte { Avenue = 0, Roundabout = 1 }
    public enum Symmetry : byte { Off = 0, Opposite = 1, AllFour = 2 }
    public enum VerticalHandles : byte { Linear = 0, Hermite = 1 }   // Linear until spike S1 confirms the game honours handle y

    /// <summary>The settings autofit may change, and the knobs a failure says could fix it. None = final failure.</summary>
    [Flags]
    public enum Knob
    {
        None = 0, Grade = 1, Clearance = 2, Radius = 4, Compact = 8, Lift = 16, Route = 32, DeckMargin = 64,
        Any = Grade | Clearance | Radius | Compact | Lift | Route | DeckMargin,
    }

    /// <summary>Every engine constant and tuning number, named once. Immutable (init-only record); tests may derive variants with `with`.</summary>
    public sealed record EngineRules
    {
        public static readonly EngineRules Default = new EngineRules();

        // ---- engine shape rules ----
        public float MinSplit { get; init; } = 30f;              // splits leave >= 30 m on both sides
        public float MaxPiece { get; init; } = 80f;              // longest new piece (also capped by prefab MaxEdgeLength)
        public float MinPiece { get; init; } = 6f;               // shortest NEW piece; relays of short existing edges are exempt
        public float SnapToNode { get; init; } = 4f;             // bridge ends snap to an existing node this close
        public float MaxSpan { get; init; } = 2500f;             // longest bridge
        public int MaxPieces { get; init; } = 600;
        public float JoinSnap { get; init; } = 0.75f;            // near-miss window the validator reports (the builder makes joins exact)
        public float JoinDistinctMin { get; init; } = 1f;        // distinct free points at least this far apart
        public float ContinuationDot { get; init; } = 0.995f;    // a 2-ref join clears IsFirst/IsLast only with the same prefab and continuous heading
        public float SplitCanonical { get; init; } = 1f;         // two splits of one edge within 1 m become one t (one junction)
        public float AttachWindow { get; init; } = 40f;          // search window for another safe split before staging

        // ---- heights and classification ----
        public float SeparatedDy { get; init; } = 4f;            // highway/street pair counts as grade-separated
        public float AtGradeDy { get; init; } = 5f;              // closer than this at a 2D crossing = at grade
        public float RaisedNode { get; init; } = 2f;             // node counts as raised (part of a viaduct)
        public float PillarNode { get; init; } = 3f;             // new node this high gets a pillar
        public float TunnelBelow { get; init; } = -3f;           // pieces lower than this are tunnels (no conflict)
        public float GroundEps { get; init; } = 0.6f;            // highway this close to terrain counts as on the ground
        public float ArterialWidth { get; init; } = 16f;
        public float MajorArterialWidth { get; init; } = 24f;
        public float PresetMinRoadWidth { get; init; } = 9f;

        // ---- search radii ----
        public float CrossingSearch { get; init; } = 120f;
        public float SeparatedSearch { get; init; } = 250f;
        public float PartnerSearch { get; init; } = 150f;
        public int PartnerSteps { get; init; } = 4;
        public int RailPartnerSteps { get; init; } = 6;
        public float TerminalWalk { get; init; } = 450f;
        public int TerminalSteps { get; init; } = 16;
        public float HighwayEndSearch { get; init; } = 150f;
        public float CarriagewayPairMax { get; init; } = 90f;
        public float StemSearch { get; init; } = 300f;
        public float StemAheadMax { get; init; } = 700f;
        public float Cross4Search { get; init; } = 260f;
        public float Cross4Pick { get; init; } = 200f;
        public float RegionMargin { get; init; } = 400f;         // site bounds grown by this for RegionVersion cache keys
        public float SiteHysteresis { get; init; } = 0.75f;      // keep the sticky site unless another is 25 % nearer
        public float ChainFollow { get; init; } = 1500f;         // ChainThrough follows a carriageway this far each way

        // ---- lifts ----
        public float DeckMarginOverpass { get; init; } = 12f;
        public float DeckMarginExitCompact { get; init; } = 26f;
        public float DeckMarginExit { get; init; } = 40f;
        public float DeckMarginOtherCompact { get; init; } = 48f;
        public float DeckMarginOther { get; init; } = 62f;
        public float KeepOffStreetOverHighway { get; init; } = 8f;   // + highway half
        public float KeepOffHighwayOverStreet { get; init; } = 12f;  // + street half
        public float KeepOffUTurn { get; init; } = 30f;              // + street half (frontage with U-turns)
        public float KeepOffRailExtra { get; init; } = 6f;           // + rail half
        public float KeepOffRailMin { get; init; } = 12f;
        public float RailMargin { get; init; } = 10f;
        public float HighwayOverMargin { get; init; } = 14f;
        public float PillarRoadMargin { get; init; } = 3f;
        public float PillarNudgeStep { get; init; } = 6f;            // nudges try 6, 12, 18, 26 m either way
        public float PillarNudgeMax { get; init; } = 26f;

        // ---- vertical ----
        public float MaxGrade { get; init; } = 0.09f;            // steepest PEAK grade accepted when room is short
        public float Steep { get; init; } = 1f / 0.85f;          // eased climb needs Steep * rise / grade of run (peak = grade)
        public float EaseBlend { get; init; } = 0.15f;           // parabolic ends of each eased climb
        public float ChordTolerance { get; init; } = 0.25f;      // add a break point where a linear-y chord leaves the profile by more
        public VerticalHandles Handles { get; init; } = VerticalHandles.Linear;
        public float ClearanceTolerance { get; init; } = 0.5f;
        public float OverlapTolerance { get; init; } = 1.5f;

        // ---- service ramps ----
        public float RampSplitCompact { get; init; } = 70f;
        public float RampSplitGentle { get; init; } = 140f;
        public float DiamondReach { get; init; } = 340f;
        public float GentleDivergeBeforeStart { get; init; } = 120f;
        public float RampGapCompact { get; init; } = 3f;
        public float RampGapGentle { get; init; } = 12f;
        public float DumbbellExtraOffset { get; init; } = 6f;
        public float ApproachExtra { get; init; } = 18f;
        public float TightDiamond { get; init; } = 160f;
        public float ExistingRampWalk { get; init; } = 220f;
        public int ExistingRampSteps { get; init; } = 8;
        public float CloseCutExtra { get; init; } = 14f;
        public float ViaductProbe { get; init; } = 250f;
        public float ExistingJunctionGap { get; init; } = 150f;

        // ---- tapers and curves ----
        public float TaperRatio { get; init; } = 3f;             // taper length >= 3 x lateral offset (the parclo S-bend was 1.32)
        public float TaperMin { get; init; } = 60f;
        public float SmoothInflate { get; init; } = 1.15f;       // Laplacian fallback pre-inflates the radius
        public float MinRadiusWarn { get; init; } = 0.9f;
        public float MinRadiusBlock { get; init; } = 0.6f;
        public float MinRadiusAbs { get; init; } = 15f;
        public float KinkDeg { get; init; } = 1.5f;

        // ---- rings ----
        public float RingMinRadius { get; init; } = 20f;
        public float EndRingMinRadius { get; init; } = 40f;
        public float RingLegGap { get; init; } = 10f;
        public float RingArcMaxDeg { get; init; } = 135f;
        public float RingPrefabMinWidth { get; init; } = 7.5f;
        public float EndRingPrefabWidth { get; init; } = 11f;

        // ---- frontage and U-turns ----
        public float SlipCompact { get; init; } = 150f;
        public float SlipGentle { get; init; } = 240f;
        public float LandGapCompact { get; init; } = 40f;
        public float LandGapGentle { get; init; } = 60f;
        public float FrontageMaxLateral { get; init; } = 160f;
        public float FrontageParallelDot { get; init; } = 0.95f;
        public float UTurnMinRadius { get; init; } = 8f;
        public float UTurnMaxRadius { get; init; } = 90f;
        public float UTurnDeck { get; init; } = 5.5f;
        public float UTurnSearch { get; init; } = 160f;
        public float UTurnStep { get; init; } = 8f;
        public float UTurnPush { get; init; } = 35f;

        // ---- highway end ----
        public float AvenueCompact { get; init; } = 60f;
        public float Avenue { get; init; } = 100f;
        public float ConvergeCompact { get; init; } = 100f;
        public float Converge { get; init; } = 160f;
        public float AvenueMinWidth { get; init; } = 16f;

        // ---- router ----
        public float RouteMaxLength { get; init; } = 3000f;
        public int RouteFullChecks { get; init; } = 24;
        public float LoopTurnDeg { get; init; } = 200f;
        public float SweepTurnDeg { get; init; } = 120f;
        public float LeftPenalty { get; init; } = 0.6f;
        public float RadiusBonus { get; init; } = 0.4f;
        public float TaperDefault { get; init; } = 100f;
        public float JunctionSkewDeg { get; init; } = 35f;
        public float MatchWithin { get; init; } = 30f;
        public float SymmetryMatchWithin { get; init; } = 45f;
        public float SharedEndIgnore { get; init; } = 70f;

        // ---- misc ----
        public float NameMatch { get; init; } = 10f;
        public float RedRadius { get; init; } = 45f;
        public float ReversedRunMax { get; init; } = 3000f;
        public bool LhtViaMirror { get; init; } = false;         // left-hand traffic through a mirrored snapshot (off until the mirror property passes)

        public ulong StableHash() => StableHashing.Of(this);
    }

    /// <summary>
    /// Immutable planning configuration. The user's settings plus autofit-only knobs. Autofit derives
    /// variants with <c>cfg with { ... }</c>; nothing global is swapped.
    /// </summary>
    public sealed record PlanConfig
    {
        // player settings (persisted through SettingsSchema)
        public float Clearance { get; init; } = 9f;              // m, 6..20
        public float Grade { get; init; } = 0.05f;               // fraction, 0.03..0.08 (peak grade of every climb)
        public LiftPreference Lift { get; init; } = LiftPreference.StreetOver;
        public bool BothCarriageways { get; init; } = true;
        public bool CloseLocalStreets { get; init; } = true;
        public bool UTurns { get; init; } = true;
        public bool Autofit { get; init; } = true;
        public RampLength RampLength { get; init; } = RampLength.Compact;
        public float RampRadius { get; init; } = 70f;            // 20..250; 70 matches Size = Standard
        public int RampLanes { get; init; } = 1;                 // 1 | 2
        public Symmetry Symmetry { get; init; } = Symmetry.Off;
        public EndStyle EndStyle { get; init; } = EndStyle.Avenue;
        public Handedness Handedness { get; init; } = Handedness.Right;   // from the city, not a panel setting

        // autofit-only knobs (never persisted)
        public float RadiusMul { get; init; } = 1f;
        public int AltRoute { get; init; } = 0;
        public float DeckMarginExtra { get; init; } = 0f;

        public EngineRules Rules { get; init; } = EngineRules.Default;

        public bool Compact => RampLength == RampLength.Compact;
        public float EffectiveRadius => RampRadius * RadiusMul;
        public float MaxGrade => Rules.MaxGrade;
        public TrafficSide Side => new TrafficSide(Handedness);
        public ulong StableHash() => StableHashing.Of(this);
    }

    /// <summary>Size is a UI macro over radius, grade and ramp length. Match returns Custom once Advanced values diverge.</summary>
    public static class SizePresets
    {
        public static PlanConfig Apply(PlanConfig c, SizePreset s)
        {
            switch (s)
            {
                case SizePreset.Compact: return c with { RampRadius = 45f, Grade = 0.07f, RampLength = RampLength.Compact };
                case SizePreset.Standard: return c with { RampRadius = 70f, Grade = 0.05f, RampLength = RampLength.Compact };
                case SizePreset.Spacious: return c with { RampRadius = 110f, Grade = 0.04f, RampLength = RampLength.Gentle };
                default: return c;
            }
        }

        public static SizePreset Match(PlanConfig c)
        {
            for (int i = 0; i < 3; i++)
            {
                var p = Apply(c, (SizePreset)i);
                if (math.abs(p.RampRadius - c.RampRadius) < 0.01f && math.abs(p.Grade - c.Grade) < 1e-4f && p.RampLength == c.RampLength)
                    return (SizePreset)i;
            }
            return SizePreset.Custom;
        }
    }

    public enum SettingKind : byte { Toggle, Choice, Stepper }

    /// <summary>One persisted or panel setting. SettingsSchema (Config unit) lists them; it drives C# clamps, the CATALOG json, the preview harness and PlanConfig construction.</summary>
    public sealed record SettingSpec
    {
        public string Key { get; init; }
        public SettingKind Kind { get; init; }
        public string Label { get; init; }
        public string Help { get; init; }
        public string Group { get; init; } = "main";             // main | advanced | testing
        public double Default { get; init; }
        public double Min { get; init; }
        public double Max { get; init; } = 1;
        public double Step { get; init; } = 1;
        public string Unit { get; init; }
        public IReadOnlyList<string> Options { get; init; } = Array.Empty<string>();      // Choice labels; value = index
        public IReadOnlyList<StyleId> RelevantFor { get; init; } = Array.Empty<StyleId>(); // empty = every style
        public bool Persisted { get; init; } = true;
    }

    /// <summary>Stable setting keys (persisted JSON, the SET trigger payload "key=value", the UI).</summary>
    public static class SettingKeys
    {
        public const string Style = "style";             // style key, e.g. "diamond"
        public const string Size = "size";               // macro: 0 compact, 1 standard, 2 spacious (3 custom is display only)
        public const string Clearance = "clearance";     // m
        public const string Grade = "grade";             // PERCENT in the UI and persisted file; fraction in PlanConfig
        public const string Lift = "lift";               // 0 street over, 1 highway over
        public const string Both = "both";
        public const string Close = "close";
        public const string UTurns = "uturns";
        public const string Autofit = "autofit";
        public const string RampLength = "rampLength";   // 0 compact, 1 gentle
        public const string Radius = "radius";
        public const string Lanes = "lanes";
        public const string Symmetry = "symmetry";
        public const string EndStyle = "endStyle";
        public const string AsyncPlanning = "asyncPlanning";
        public const string VerboseLog = "verboseLog";
        public const string DevTools = "devTools";
    }
}
```

### 6.5 Sites
What the cursor is pointing at.
<!-- contract:Sites -->
```csharp
namespace InterchangeStudio.Core
{
    public enum SiteKind : byte { None, AtGradeCrossing, RailCrossing, Separated, HighwayEnd, Stem, Cross4, ReversedRun, RampEnds }
    public enum StreetClass : byte { Local = 0, Arterial = 1, MajorArterial = 2 }

    /// <summary>Canonical key: kind plus SORTED defining ids (or a rounded centre). Never the cursor cell, never "which carriageway is nearer".</summary>
    public readonly struct SiteKey : IEquatable<SiteKey>
    {
        public readonly string Value;
        public SiteKey(string value) { Value = value ?? ""; }
        public static readonly SiteKey None = new SiteKey("");
        public bool IsNone => string.IsNullOrEmpty(Value);
        public bool Equals(SiteKey o) => string.Equals(Value ?? "", o.Value ?? "", StringComparison.Ordinal);
        public override bool Equals(object o) => o is SiteKey k && Equals(k);
        public override int GetHashCode() => (Value ?? "").GetHashCode();
        public ulong Stable => Fnv64.Start().Add(Value ?? "").Value;
        public override string ToString() => Value ?? "";
    }

    /// <summary>What a site looks like, so it can be found again after a rebuild replaced its entities (Relocator ladder).</summary>
    public sealed record SiteSignature
    {
        public PrefabId A { get; init; }                 // e.g. highway prefab
        public PrefabId B { get; init; }                 // e.g. street prefab
        public float2 DirA { get; init; }
        public float2 DirB { get; init; }
        public float3 Centre { get; init; }
        public int StreetAggregate { get; init; }
    }

    public abstract record Site
    {
        public abstract SiteKind Kind { get; }
        public SiteKey Key { get; init; }
        public float3 Focus { get; init; }               // where the status and camera point
        public float Radius { get; init; } = 60f;        // hysteresis radius: the sticky site is kept while the cursor is inside
        public Rect2 Bounds { get; init; }               // area the plan may touch (RegionVersion uses it, grown by RegionMargin)
        public SiteSignature Signature { get; init; }
    }

    public sealed record AtGradeCrossingSite : Site
    {
        public override SiteKind Kind => SiteKind.AtGradeCrossing;
        public NodeId Node { get; init; }
        public NodeId Partner { get; init; }             // the other carriageway's crossing on the same street (None if single)
        public IReadOnlyList<EdgeId> HighwayEdges { get; init; } = Array.Empty<EdgeId>();
        public IReadOnlyList<EdgeId> StreetEdges { get; init; } = Array.Empty<EdgeId>();
        public StreetClass Street { get; init; }
        public float StreetWidth { get; init; }
        public float HighwayWidth { get; init; }
    }

    public sealed record RailCrossingSite : Site
    {
        public override SiteKind Kind => SiteKind.RailCrossing;
        public NodeId Node { get; init; }
        public NodeId Partner { get; init; }             // other carriageway's crossing, found by following the tracks
        public bool RoadIsHighway { get; init; }
        public float RailHalf { get; init; }
        public string Refusal { get; init; }             // non-null: final failure text ("a junction sits right on the tracks...")
    }

    public sealed record Separation
    {
        public EdgeId Highway { get; init; }
        public EdgeId Street { get; init; }
        public float THighway { get; init; }             // edge t (own parameterisation)
        public float TStreet { get; init; }
        public float3 Lower { get; init; }               // the lower of the two points at the 2D crossing
        public float Dy { get; init; }
        public bool HighwayOver { get; init; }
        public float2 Travel { get; init; }              // highway travel direction at the crossing
    }

    public sealed record SeparatedSite : Site
    {
        public override SiteKind Kind => SiteKind.Separated;
        public IReadOnlyList<Separation> Carriageways { get; init; } = Array.Empty<Separation>();  // 1 or 2, paired on the SAME street
        public bool HighwayOver { get; init; }
        public StreetClass Street { get; init; }
        public float StreetWidth { get; init; }
        public int StreetAggregate { get; init; }
    }

    public sealed record HighwayEndSite : Site
    {
        public override SiteKind Kind => SiteKind.HighwayEnd;
        public NodeId In { get; init; }                  // end node of the inbound carriageway (or the single two-way highway)
        public NodeId Out { get; init; }                 // None when TwoWay
        public bool TwoWay { get; init; }
    }

    /// <summary>One carriageway as an infinite line near a four-way crossing (preset geometry).</summary>
    public sealed record CwLine
    {
        public float2 P { get; init; }                   // point on the line level with the crossing
        public float2 Dir { get; init; }                 // travel direction
        public float Half { get; init; }
        public bool Highway { get; init; }
        public bool OneWay { get; init; }
        public EdgeId Edge { get; init; }
        public PrefabId Prefab { get; init; }
        public string Label { get; init; }
    }

    public sealed record Cross4Site : Site
    {
        public override SiteKind Kind => SiteKind.Cross4;
        public CwLine Xp { get; init; }
        public CwLine Xm { get; init; }
        public CwLine Yp { get; init; }
        public CwLine Ym { get; init; }
        public float2 C { get; init; }
        public bool AtGrade { get; init; }               // presets on an at-grade crossing lift first (LiftThen)
        public NodeId AtGradeNode { get; init; }
    }

    public sealed record StemSite : Site
    {
        public override SiteKind Kind => SiteKind.Stem;
        public NodeId In { get; init; }
        public NodeId Out { get; init; }                 // None for a two-way stem
        public float2 S { get; init; }                   // stem direction (inbound travel)
        public CwLine QR { get; init; }                  // carriageway turning right from the stem
        public CwLine QL { get; init; }
        public float2 C { get; init; }
        public bool AtGradeT { get; init; }              // stem already joined to the road at grade
        public bool TwoWayStem { get; init; }
    }

    public sealed record ReversedRunSite : Site
    {
        public override SiteKind Kind => SiteKind.ReversedRun;
        public IReadOnlyList<EdgeId> Run { get; init; } = Array.Empty<EdgeId>();
    }

    public sealed record RampEndsSite : Site
    {
        public override SiteKind Kind => SiteKind.RampEnds;
        public RampEnd A { get; init; }
        public RampEnd B { get; init; }
    }

    /// <summary>Free-ramp click 1, stored as position + road signature and re-matched every hover (the clicked edge may be rebuilt).</summary>
    public sealed record RampAnchor
    {
        public float3 Pos { get; init; }
        public float2 Dir { get; init; }
        public EdgeId Edge { get; init; }
        public float T { get; init; }
        public PrefabId Prefab { get; init; }
        public RampEndKind Kind { get; init; }
    }

    public sealed record SiteLookup
    {
        public Site Site { get; init; }                  // null => show the hint
        public string HintCode { get; init; }
        public StyleId? Suggest { get; init; }           // e.g. "you're at a highway end: Highway end mode handles this"
        public IReadOnlyList<EdgeId> ReversedRun { get; init; } = Array.Empty<EdgeId>();  // non-empty => status badge + Fix direction suggestion
    }

    public interface ISiteFinder
    {
        /// <summary>Hover dispatch in priority order (DESIGN 7.2) with hysteresis against <paramref name="sticky"/>.</summary>
        SiteLookup Find(PlanContext ctx, Hit hit, StyleId style, RampAnchor from, Site sticky);
        /// <summary>Re-find a site after a build, from scratch: anchor, then street aggregate, then highway prefab, at 40 / 120 / 250 m.</summary>
        Site Relocate(PlanContext ctx, FollowUp followUp);
    }

    public enum FixKind : byte { HighwayCrossing, RailCrossing, NeedsManualFix }

    public sealed record FixTarget
    {
        public SiteKey Key { get; init; }
        public float3 Position { get; init; }
        public FixKind Kind { get; init; }
        public string Label { get; init; }
    }

    public sealed class FixReport
    {
        public long Version { get; init; }
        public IReadOnlyList<FixTarget> Crossings { get; init; } = Array.Empty<FixTarget>();   // one per street x divided highway (pairs counted once), terminals excluded
        public IReadOnlyList<FixTarget> Rail { get; init; } = Array.Empty<FixTarget>();
        public IReadOnlyList<FixTarget> Manual { get; init; } = Array.Empty<FixTarget>();      // e.g. a junction on the tracks
    }

    public interface IFixFinder
    {
        FixReport Scan(PlanContext ctx);
        FixTarget Next(FixReport report, float3 from, IReadOnlyCollection<SiteKey> visited);   // nearest unvisited; null when none left
    }
}
```

### 6.6 Plan
EndRef, JoinPoint, pieces, BuildPlan and the IPlanBuilder seam.
<!-- contract:Plan -->
```csharp
namespace InterchangeStudio.Core
{
    public enum EndKind : byte { Free, Node, Split }

    /// <summary>
    /// How a piece end attaches. Constructors are internal: only PlanBuilder / AttachFactory create them
    /// (source rule enforced by a test). Split carries the EDGE's own Bezier t (Start -> End), already
    /// passed through Splits.Decide, and the piece end position equals MathUtils.Position(edge, t) exactly.
    /// </summary>
    public readonly struct EndRef : IEquatable<EndRef>
    {
        public readonly EndKind Kind;
        public readonly int Point;                     // JoinPoint index (Free)
        public readonly NodeId Node;                   // Node
        public readonly EdgeId Edge;                   // Split
        public readonly float EdgeT;                   // Split

        internal EndRef(EndKind kind, int point, NodeId node, EdgeId edge, float edgeT) { Kind = kind; Point = point; Node = node; Edge = edge; EdgeT = edgeT; }
        internal static EndRef MakeFree(int point) => new EndRef(EndKind.Free, point, NodeId.None, EdgeId.None, 0f);
        internal static EndRef MakeNode(NodeId node) => new EndRef(EndKind.Node, -1, node, EdgeId.None, 0f);
        internal static EndRef MakeSplit(EdgeId edge, float edgeT) => new EndRef(EndKind.Split, -1, NodeId.None, edge, edgeT);

        public bool Equals(EndRef o) => Kind == o.Kind && Point == o.Point && Node == o.Node && Edge == o.Edge && EdgeT == o.EdgeT;
        public override bool Equals(object o) => o is EndRef e && Equals(e);
        public override int GetHashCode() => ((int)Kind * 7919) ^ Point ^ Node.GetHashCode() ^ Edge.GetHashCode();
        public override string ToString() => Kind == EndKind.Free ? "free#" + Point : Kind == EndKind.Node ? Node.ToString() : Edge + "@" + EdgeT.ToString("0.000");
    }

    /// <summary>An exact shared meeting point for free ends. Every free end that refers to it has bit-identical coordinates.</summary>
    public sealed class JoinPoint
    {
        internal JoinPoint(int index, float3 position, float elevation) { Index = index; Position = position; Elevation = elevation; }
        public int Index { get; }
        public float3 Position { get; }                // y = terrain + Elevation (or exact cut position)
        public float Elevation { get; }
        public int Refs { get; internal set; }
    }

    public enum AttachKind : byte { Split, Node, Hazard, None }

    /// <summary>Result of asking the builder to attach at a place: a safe split, a node fallback, a hazard (resolved in Finish by promotion or staging), or nothing usable.</summary>
    public readonly struct AttachChoice
    {
        public readonly AttachKind Kind;
        public readonly EndRef Ref;
        public readonly float3 Position;
        public readonly float Elevation;
        public readonly float S;                       // chain distance actually used (may move within the window)
        public readonly string Why;
        internal AttachChoice(AttachKind kind, EndRef endRef, float3 position, float elevation, float s, string why)
        { Kind = kind; Ref = endRef; Position = position; Elevation = elevation; S = s; Why = why; }
        public bool Ok => Kind != AttachKind.None;
    }

    public enum PieceRole : byte { Relay, Bridge, Ramp, Taper, Trunk, Slip, Ring, Lane, Stub, UTurn, Avenue, Flip }

    /// <summary>One new course. Immutable once the plan is finished. Curve a -> d is the traffic direction (one-way) or the source orientation (two-way).</summary>
    public sealed class Piece
    {
        public int Index { get; internal set; }
        public PrefabId Prefab { get; internal set; }
        public Bezier4x3 Curve { get; internal set; }
        public EndRef Start { get; internal set; }
        public EndRef End { get; internal set; }
        public float E0 { get; internal set; }
        public float E1 { get; internal set; }
        public UpgradeBits Upgrades { get; internal set; }
        public PieceRole Role { get; internal set; }
        public EdgeId Source { get; internal set; }            // Relay / Flip
        public bool InvertedFromSource { get; internal set; }  // laid against the source edge's own Start -> End
        public string Group { get; internal set; }
        public string Label { get; internal set; }             // "the north-east loop"
        public bool ContinuesAtStart { get; internal set; }    // exactly-2 same-prefab continuation: Emit clears IsFirst
        public bool ContinuesAtEnd { get; internal set; }      // ... clears IsLast
        public int RampId { get; internal set; } = -1;
    }

    /// <summary>A single new piece. xz of Curve matters; end y is recomputed as terrain + E0/E1 unless KeepCurve.</summary>
    public sealed record PieceSpec
    {
        public PrefabId Prefab { get; init; }
        public Bezier4x3 Curve { get; init; }
        public EndRef A { get; init; }
        public EndRef B { get; init; }
        public float E0 { get; init; }
        public float E1 { get; init; }
        public float Slope0 { get; init; } = float.NaN;        // dE/ds at the ends for Hermite handles; NaN = linear
        public float Slope1 { get; init; } = float.NaN;
        public PieceRole Role { get; init; }
        public string Label { get; init; }
        public string Group { get; init; }
        public UpgradeBits Upgrades { get; init; }
        public bool KeepCurve { get; init; }                   // relay pieces cut from an existing curve: keep it exactly
    }

    public sealed record NoNodeSpan(float S0, float S1, string Why);

    /// <summary>A routed path written in Finish: break points (no node inside a NoNode span), pillar nudging across ALL pending paths, then pieces.</summary>
    public sealed record PathSpec
    {
        public PrefabId Prefab { get; init; }
        public IPath2 Path { get; init; }                      // planar, travel order A -> B
        public IVerticalProfile Profile { get; init; }         // elevation above terrain along Path
        public EndRef A { get; init; }
        public EndRef B { get; init; }
        public PieceRole Role { get; init; } = PieceRole.Ramp;
        public string Label { get; init; }
        public string Group { get; init; }
        public float Half { get; init; }
        public UpgradeBits Upgrades { get; init; }
        public IReadOnlyList<NoNodeSpan> NoNode { get; init; } = Array.Empty<NoNodeSpan>();
        public IReadOnlyList<float> Fixed { get; init; } = Array.Empty<float>();       // must-have break points
        public IReadOnlyList<float> Preferred { get; init; } = Array.Empty<float>();   // joints, seg boundaries
        public float KeepOff { get; init; }                    // raised nodes at least this far from roads below (0 = Half + PillarRoadMargin)
        public int RampId { get; init; } = -1;
    }

    public sealed record NameCarry
    {
        public EdgeId Source { get; init; }                    // a Relay source (never a ramp); the adapter reads its name on the click frame
        public float3 Anchor { get; init; }
        public bool Highway { get; init; }
        public PrefabId Prefab { get; init; }
    }

    public sealed record Deletion(EdgeId Edge, string Why);

    /// <summary>Stage-2 hand-off: what to re-plan after this plan has been applied and the world has settled.</summary>
    public sealed record FollowUp
    {
        public StyleId Style { get; init; }
        public int Stage { get; init; } = 2;
        public float3 Anchor { get; init; }
        public SiteKind Expect { get; init; } = SiteKind.Separated;
        public SiteSignature Signature { get; init; }
        public PlanConfig Config { get; init; }                // the variant stage 1 used
        public Knob Locked { get; init; } = Knob.Lift | Knob.Clearance | Knob.DeckMargin;   // stage-2 autofit may not change these
        public string Stage1Summary { get; init; }
    }

    public enum GroupPolicy : byte { Required, Atomic, Optional }

    public sealed record GroupReport
    {
        public string Id { get; init; }
        public string Label { get; init; }
        public GroupPolicy Policy { get; init; }
        public bool Built { get; init; }
        public bool FellBack { get; init; }
        public Failure Reason { get; init; }
    }

    /// <summary>Checkpoint over the builder. Dispose without Commit rolls back every delete, piece, path, point and name added since Begin.</summary>
    public interface IPlanTransaction : IDisposable
    {
        string Group { get; }
        bool Committed { get; }
        void Commit();
        void Fail(Failure reason);                             // roll back and record the reason in GroupReport
    }

    public sealed record PlanMetrics
    {
        public int Pieces { get; init; }
        public int Ramps { get; init; }
        public int Loops { get; init; }
        public int Flyovers { get; init; }
        public int ClosedStreets { get; init; }
        public int UTurns { get; init; }
        public int Pillars { get; init; }
        public int Levels { get; init; }
        public float BridgeLength { get; init; }
        public float MaxHeight { get; init; }
        public float MaxGradeUsed { get; init; }
        public float MinRadiusUsed { get; init; }
        public float NewLength { get; init; }
        public float DiamondGap { get; init; }                 // 0 when not a diamond
        public float MaxTaperRatio { get; init; }              // offset / length
    }

    public sealed class Footprint
    {
        public Rect2 Bounds { get; init; }
        public IReadOnlyList<float3[]> Polylines { get; init; } = Array.Empty<float3[]>();   // per piece index, about 4 m spacing, absolute y
    }

    /// <summary>The immutable result of planning. Only PlanBuilder.Finish (and the capture codec) can create one.</summary>
    public sealed class BuildPlan
    {
        internal BuildPlan() { }
        public StyleId Style { get; init; }
        public SiteKey Site { get; init; }
        public int Stage { get; init; } = 1;
        public long NetworkVersion { get; init; }
        public ulong ConfigHash { get; init; }
        public IReadOnlyList<Deletion> Deletes { get; init; } = Array.Empty<Deletion>();
        public IReadOnlyList<Piece> Pieces { get; init; } = Array.Empty<Piece>();
        public IReadOnlyList<JoinPoint> Points { get; init; } = Array.Empty<JoinPoint>();
        public IReadOnlyList<NameCarry> Names { get; init; } = Array.Empty<NameCarry>();
        public IReadOnlyList<GroupReport> Groups { get; init; } = Array.Empty<GroupReport>();
        public FollowUp FollowUp { get; init; }
        public PlanMetrics Metrics { get; init; } = new PlanMetrics();
        public Explanation Why { get; init; } = new Explanation();
        public Footprint Footprint { get; init; } = new Footprint();
        public IReadOnlyList<EdgeId> ReferencedEdges { get; init; } = Array.Empty<EdgeId>();   // deletes + split targets (StillValid)
        public IReadOnlyList<NodeId> ReferencedNodes { get; init; } = Array.Empty<NodeId>();
        public string Fingerprint { get; init; } = "";       // Fnv64 hex of deletes + rounded geometry + refs
        public bool Partial { get; init; }                    // some optional groups failed ("6 of 8 ramps")
        public bool IsEmpty => Pieces.Count == 0 && Deletes.Count == 0;
    }

    public sealed record Failure
    {
        public string Code { get; init; }                     // stable id for Narrator and tests, e.g. "lift.no-room"
        public string What { get; init; }                     // "Overpass"
        public string Why { get; init; }                      // plain English, already formatted
        public Knob Fixable { get; init; }                    // knobs that could fix it; None => final (autofit stops)
        public float3? Where { get; init; }
        public bool Final => Fixable == Knob.None;
        public static Failure FinalOf(string code, string what, string why) => new Failure { Code = code, What = what, Why = why, Fixable = Knob.None };
        public static Failure Retry(string code, string what, string why, Knob fixable) => new Failure { Code = code, What = what, Why = why, Fixable = fixable == Knob.None ? Knob.Any : fixable };
    }

    public sealed class PlanOutcome
    {
        PlanOutcome(BuildPlan plan, Failure failure, Explanation why) { Plan = plan; Failure = failure; Why = why ?? new Explanation(); }
        public BuildPlan Plan { get; }
        public Failure Failure { get; }
        public Explanation Why { get; }
        public bool Ok => Plan != null;
        public static PlanOutcome Built(BuildPlan plan) => new PlanOutcome(plan ?? throw new ArgumentNullException(nameof(plan)), null, plan.Why);
        public static PlanOutcome Fail(Failure failure, Explanation why = null) => new PlanOutcome(null, failure ?? throw new ArgumentNullException(nameof(failure)), why);
    }

    /// <summary>
    /// The only way styles and kits write a plan. Guarantees by construction: exact join points, splits
    /// only through Splits (edge-space t), y = terrain + elevation, relays keep prefab, upgrades and
    /// direction, names only from relays, all-or-nothing groups. Finish runs break points, pillars,
    /// joins, batch safety (promotion / staging) and freezes the plan.
    /// </summary>
    public interface IPlanBuilder
    {
        PlanContext Context { get; }
        StyleId Style { get; }

        JoinPoint Point(float2 xz, float elevation);                 // y = terrain(xz) + elevation, exact
        JoinPoint PointExact(float3 position, float elevation);      // cut ends of existing roads
        EndRef Free(JoinPoint point);
        EndRef AtNode(NodeId node);
        /// <summary>Safe split at metres from the edge Start; falls back to a node; searches +/- window for another safe split when this one is a hazard.</summary>
        AttachChoice OnEdge(EdgeId edge, float metresFromStart, float window = 0f);
        AttachChoice OnChain(IChain chain, float s, float window = 0f);

        void Delete(EdgeId edge, string why = null);                 // idempotent; throws PlannerBugException for rail
        bool IsDeleted(EdgeId edge);
        void Ignore(EdgeId edge);                                     // plan-ignore set: router/matcher skip it
        IReadOnlyCollection<EdgeId> Ignored { get; }

        Piece Add(PieceSpec spec);
        int AddPath(PathSpec spec);
        /// <summary>Re-lay part of an existing seg (chain distances s0..s1, ends in chain order). Keeps prefab and upgrades; inverts to the source edge's traffic direction. elevationAt null = keep the original curve exactly.</summary>
        void Relay(ChainSeg source, float s0, float s1, EndRef a, EndRef b, Func<float, float> elevationAt, string label = null);
        void Flip(EdgeId edge);                                       // FixDirection only: inverted course, mirrored upgrades
        void CarryName(EdgeId relaySource, float3 anchor);            // throws unless the source was relaid or deleted by this plan

        IPlanTransaction Begin(string group, GroupPolicy policy, string label);
        void SetFollowUp(FollowUp followUp);

        void Because(string code, string text);
        void Tried(string what, bool won, string why);
        void Fact(string code, string label, string value);
        void Warn(string code, string text, float3? where = null);
        void Suggest(Suggestion suggestion);

        PlanOutcome Finish(string headline);
    }

    public interface IPlanBuilderFactory
    {
        IPlanBuilder Create(PlanContext ctx, StyleId style, Site site, int stage);
    }

    public sealed record PillarObstacle(float3[] Samples, float Half, NetKind Kind, string Label);

    public sealed class BreakResult
    {
        public IReadOnlyList<float[]> Breaks { get; init; } = Array.Empty<float[]>();   // per path, ascending, including 0 and Length
        public IReadOnlyList<Violation> Unresolved { get; init; } = Array.Empty<Violation>();
        public int Passes { get; init; }
    }

    /// <summary>Write unit: break points and pillar nudging over every pending path at once (later ramps included), and piece fitting.</summary>
    public interface IPathWriter
    {
        BreakResult PlaceBreaks(IReadOnlyList<PathSpec> paths, PlanContext ctx, IReadOnlyList<PillarObstacle> extra);
        /// <summary>Ends are exact (y = terrain + profile); handles follow Rules.Handles; xz from Path.Piece.</summary>
        Bezier4x3 PieceOf(PathSpec path, float s0, float s1, PlanContext ctx);
    }
}
```

### 6.7 Network
Chains and walkers.
<!-- contract:Network -->
```csharp
namespace InterchangeStudio.Core
{
    public enum StopReason : byte { RoomReached, SideStreet, RoadEnds, HighwayJunction, RampTerminal, RailJunction, TooLong, TooBroken }

    public sealed record WalkPolicy
    {
        public float Need { get; init; }                     // room wanted since the last obstacle
        public float MaxSpan { get; init; } = 2500f;
        public int MaxSteps { get; init; } = 200;
        public bool AbsorbRail { get; init; } = true;         // rail nodes are things to bridge over
        public bool AbsorbRaised { get; init; } = true;       // raised nodes merge into a continuous viaduct
        public bool AbsorbCrossings { get; init; } = true;    // street walk: other carriageways; highway walk: street crossings
        public bool StopAtTerminals { get; init; } = true;    // a diamond terminal is a stop, never a carriageway to bridge
    }

    public sealed class Obstacle
    {
        public float S { get; init; }                         // chain distance from the walk origin
        public float Half { get; init; }
        public float SurfaceY { get; init; }                  // absolute height of the thing below
        public NetKind Kind { get; init; }
        public NodeId Node { get; init; }
        public EdgeId Edge { get; init; }
        public string Label { get; init; }
    }

    public sealed class WalkResult
    {
        public IReadOnlyList<ChainSeg> Segs { get; init; } = Array.Empty<ChainSeg>();
        public IReadOnlyList<Obstacle> Under { get; init; } = Array.Empty<Obstacle>();
        public StopReason Stop { get; init; }
        public float StopAt { get; init; }                    // distance of the stopping node
        public string StopText { get; init; }                 // "a side street 76 m out", "the highway ends"
        public float Covered { get; init; }
    }

    /// <summary>Network unit: chains, walkers and topology predicates over an INetwork.</summary>
    public interface INetworkKit
    {
        ChainSeg MakeSeg(INetwork net, EdgeId edge, NodeId from, float s0);
        IChain FromSegs(INetwork net, IReadOnlyList<ChainSeg> segs);
        /// <summary>Reverses the outward back walk and appends the forward walk; cross = chain distance of the shared node.</summary>
        IChain Join(INetwork net, IReadOnlyList<ChainSeg> back, IReadOnlyList<ChainSeg> forward, out float cross);
        WalkResult WalkStreet(INetwork net, NodeId from, EdgeId first, WalkPolicy policy);
        WalkResult WalkHighway(INetwork net, NodeId from, EdgeId first, WalkPolicy policy);
        /// <summary>ChainFrom: walk back from a carriageway end; fails at any junction, street or rail node.</summary>
        WalkResult WalkFromEnd(INetwork net, NodeId end, float need);
        /// <summary>Follow a carriageway with its traffic both ways (m_Start/m_End continuity, dot &gt; 0.7, mainline tie-break: same prefab, more lanes, straighter).</summary>
        IChain Follow(INetwork net, EdgeId start, float back, float forward);
        IChain StreetThrough(INetwork net, EdgeId street, float edgeT, float each);
        IChain StreetBetween(INetwork net, NodeId a, NodeId b, float maxLength, int maxSteps);
        EdgeId StraightestContinuation(INetwork net, NodeId at, EdgeId from, NetKind mask, float minDot);
        bool IsTerminal(INetwork net, NodeId node);           // 2 highway legs reaching a merge/diverge both ways within 450 m
        bool IsEndNode(INetwork net, NodeId node);            // 1 highway leg + >= 1 street
        bool IsOneWay(INetwork net, EdgeId edge);
        StreetClass ClassOf(float width, EngineRules rules);
        float WidestStreetAt(INetwork net, NodeId node);
    }
}
```

### 6.8 Profile
Vertical profiles.
<!-- contract:Profile -->
```csharp
namespace InterchangeStudio.Core
{
    /// <summary>Something a path crosses. RoadElev = height of its SURFACE above this path's terrain at S (clearance is measured to the real road, not the ground).</summary>
    public sealed record ProfileCrossing
    {
        public float S { get; init; }
        public float RoadElev { get; init; }
        public float Flat { get; init; }                     // half-length of the level zone over/under it
        public NetKind Kind { get; init; }
        public string Label { get; init; }
        public int OtherRamp { get; init; } = -1;            // crossing with another new ramp of the same plan
        public bool MustBeOver { get; init; }
    }

    public sealed record ProfileRequest
    {
        public float Length { get; init; }
        public float EStart { get; init; }
        public float EEnd { get; init; }
        public float WStart { get; init; }                   // hold the start level this long (leave a raised road level)
        public float WEnd { get; init; }
        public IReadOnlyList<ProfileCrossing> Crossings { get; init; } = Array.Empty<ProfileCrossing>();
        public float Clearance { get; init; } = 9f;
        public float Grade { get; init; } = 0.05f;           // PEAK grade
        public float MaxGrade { get; init; } = 0.09f;        // retried at this when Grade does not fit (result flagged Steep)
        public int MaxLevels { get; init; } = 3;             // levels 0, C, 2C, 3C plus road + C
    }

    public sealed record LevelChoice(int Crossing, float Level, bool Over);

    /// <summary>Elevation above terrain along a path: level zones joined by eased climbs (parabolic ends, peak slope = grade).</summary>
    public interface IVerticalProfile
    {
        float Length { get; }
        float At(float s);
        float Slope(float s);
        float MaxSlope { get; }
        IReadOnlyList<float> Breaks { get; }                 // zone edges and curve tangent points
    }

    public sealed class ProfileSolution
    {
        public IVerticalProfile Profile { get; init; }       // null when nothing fits
        public IReadOnlyList<LevelChoice> Levels { get; init; } = Array.Empty<LevelChoice>();
        public bool Steep { get; init; }                     // needed MaxGrade
        public string FailWhy { get; init; }
        public bool Ok => Profile != null;
    }

    /// <summary>Profile unit. Never mutates its inputs. Overlapping same-level flat zones are merged before fitting.</summary>
    public interface IProfileSolver
    {
        ProfileSolution Solve(ProfileRequest request);
        /// <summary>Run an eased climb of <paramref name="rise"/> needs at peak <paramref name="grade"/>: Steep * rise / grade.</summary>
        float RunFor(float rise, float grade);
        IVerticalProfile Constant(float length, float elevation);
    }
}
```

### 6.9 Kits
Lifts, service ramps, rings, street surgery, frontage and U-turns.
<!-- contract:Kits -->
```csharp
namespace InterchangeStudio.Core
{
    // ---------------- lifts (street over highway, highway over street, road over rail) ----------------
    public enum LiftKind : byte { StreetOverHighway, HighwayOverStreet, RoadOverRail }

    public sealed record LiftRequest
    {
        public NodeId Cross { get; init; }
        public NodeId Partner { get; init; }                 // second crossing on the same road; merged into one chain when they overlap
        public LiftKind Kind { get; init; }
        public float ObstacleHalf { get; init; }
        public float Margin { get; init; }                   // flat deck beyond the obstacle (style deck margin + DeckMarginExtra)
        public float KeepOff { get; init; }
        public string Label { get; init; }
    }

    public sealed class LiftResult
    {
        public Failure Failure { get; init; }
        public IChain Chain { get; init; }
        public float Cross { get; init; }
        public float Start { get; init; }
        public float RampUp { get; init; }
        public float RampDown { get; init; }
        public float End { get; init; }
        public IReadOnlyList<Obstacle> Under { get; init; } = Array.Empty<Obstacle>();
        public IVerticalProfile Profile { get; init; }
        public IReadOnlyList<EdgeId> Touched { get; init; } = Array.Empty<EdgeId>();
        public float MaxHeight { get; init; }
        public bool Ok => Failure == null;
        public float BridgeLength => End - Start;
    }

    public interface ILiftKit
    {
        LiftResult Plan(PlanContext ctx, LiftRequest request);   // pure: walks, ramp-room arithmetic, profile
        void Write(IPlanBuilder b, LiftResult lift);              // delete touched edges, relay ground + deck, carry names
        bool Overlaps(LiftResult a, LiftResult b);
    }

    // ---------------- service interchanges (diamond, SPUI, dumbbell, frontage) ----------------
    public enum TerminalStyle : byte { Straight, CurvedIn }

    public sealed class Carriageway
    {
        public int Index { get; init; }
        public IChain Chain { get; init; }                   // traffic-ordered
        public float Cross { get; init; }                    // chain s of the street crossing
        public float Start { get; init; }                    // first point either side with the highway on the ground (= Cross on a viaduct)
        public float End { get; init; }
        public bool Viaduct { get; init; }
        public float HighwayHalf { get; init; }
        public float StreetHalf { get; init; }
        public StreetClass Street { get; init; }
        public int RampLanes { get; init; } = 1;             // 2 at major arterials
        public EdgeId StreetEdge { get; init; }
        public float StreetT { get; init; }
        public float2 Travel { get; init; }
        public string Compass { get; init; }                 // "north-bound"
    }

    public sealed record RampEndsPlacement
    {
        public float Diverge { get; init; }
        public float Merge { get; init; }
        public float OffNear { get; init; }                  // Cross - approach
        public float OnNear { get; init; }                   // Cross + approach
        public float Climb { get; init; }
        public TaperSpec Taper { get; init; }
        public float Lateral { get; init; }                  // RampOffset
        public float ElevOff { get; init; }                  // highway height above ground at Diverge
        public float ElevOn { get; init; }
    }

    /// <summary>Where a ramp meets the cross street: a safe split, a node, or a ring leg point.</summary>
    public sealed class Terminal
    {
        public EndRef Ref { get; init; }
        public float3 Position { get; init; }
        public float Elevation { get; init; }
        public float2 StreetDir { get; init; }
        public string Label { get; init; }
    }

    public interface IServiceKit
    {
        IReadOnlyList<Carriageway> Carriageways(PlanContext ctx, SeparatedSite site);
        Failure ExistingInterchange(PlanContext ctx, SeparatedSite site);          // null when clear; final otherwise
        float RampOffset(PlanContext ctx, Carriageway cw, StyleId style);
        RampEndsPlacement PlaceEnds(PlanContext ctx, Carriageway cw, float approach, out Failure failure);
        Terminal Junction(IPlanBuilder b, Carriageway cw, float lateral, out Failure failure);              // metre steps, Splits rule, node fallback
        Terminal Centre(IPlanBuilder b, SeparatedSite site, IReadOnlyList<Carriageway> cws, out Failure failure); // SPUI centre
        Failure RampZoneClear(PlanContext ctx, Carriageway cw, RampEndsPlacement ends, ISet<NodeId> close);
        void WriteRamps(IPlanBuilder b, Carriageway cw, RampEndsPlacement ends, Terminal off, Terminal on, TerminalStyle style, string group);
    }

    // ---------------- rings ----------------
    public enum RingLegKind : byte { StreetCut, RampIn, RampOut, LaneIn, LaneOut }

    public sealed record RingLeg
    {
        public RingLegKind Kind { get; init; }
        public float Angle { get; init; }                    // atan2(z, x) about the centre; ignored for StreetCut
        public IChain Street { get; init; }                  // StreetCut: the street chain through the centre
        public float StreetS { get; init; }                  // chain s nearest the centre
        public int Side { get; init; } = 1;                  // +1 beyond the centre along the chain, -1 before
        public string Label { get; init; }
    }

    public sealed class RingResult
    {
        public Failure Failure { get; init; }
        public IReadOnlyList<Terminal> Legs { get; init; } = Array.Empty<Terminal>();   // same order as the request; legs lie ON the circle
        public float Radius { get; init; }
        public PrefabId Prefab { get; init; }
        public bool Ok => Failure == null;
    }

    public interface IRingKit
    {
        RingResult Build(IPlanBuilder b, float2 centre, float radius, float elevation, IReadOnlyList<RingLeg> legs, float minPrefabWidth, string group);
        float2 PointAt(float2 centre, float radius, float angle);
    }

    // ---------------- street surgery ----------------
    public sealed class CutResult
    {
        public EndRef End { get; init; }                     // free end (or the far node when the kept piece would be under 2 m)
        public float3 Position { get; init; }
        public float Elevation { get; init; }
        public bool AtNode { get; init; }
    }

    public sealed class TrimResult
    {
        public Failure Failure { get; init; }
        public IChain Chain { get; init; }                   // from the old end backwards
        public EndRef End { get; init; }
        public float3 Position { get; init; }
        public float Elevation { get; init; }
        public float2 TravelDir { get; init; }               // traffic direction of the carriageway at the cut
        public float Back { get; init; }
        public bool Ok => Failure == null;
    }

    public interface IStreetSurgery
    {
        CutResult Cut(IPlanBuilder b, ChainSeg seg, float keepFrom, float keepTo, bool cutAtEnd);
        CutResult SplitPath(IPlanBuilder b, IChain path, float s);    // delete + re-lay; within 30 m of a node uses the node
        int CloseStreets(IPlanBuilder b, IReadOnlyCollection<NodeId> crossingNodes, float cut);   // returns STREETS closed; stubs keep upgrades and elevation
        TrimResult Trim(IPlanBuilder b, NodeId endNode, float back);  // ChainFrom + CutChain
    }

    // ---------------- frontage roads and Texas U-turns ----------------
    public sealed class FrontageRoad
    {
        public EdgeId Edge { get; init; }
        public Terminal Attach { get; init; }
        public float Lateral { get; init; }
        public float2 Travel { get; init; }
        public bool DirectionOk { get; init; }               // one-way frontage runs the same way as the carriageway (or two-way)
    }

    public interface IFrontageKit
    {
        FrontageRoad Find(IPlanBuilder b, Carriageway cw, float s, IReadOnlyCollection<EdgeId> exclude);
        void WriteSlip(IPlanBuilder b, Carriageway cw, float sHighway, FrontageRoad road, bool offRamp, string group);
    }

    public sealed class UTurnResult
    {
        public bool Ok { get; init; }
        public string WhyNot { get; init; }
        public float SA { get; init; }
        public float SB { get; init; }
        public float Radius { get; init; }
    }

    public interface IUTurnKit
    {
        UTurnResult Try(IPlanBuilder b, Carriageway a, Carriageway c, FrontageRoad fa, FrontageRoad fc, float streetHalf, string group);
    }
}
```

### 6.10 Routing
Free ramps, routing, levelling, symmetry and preset geometry.
<!-- contract:Routing -->
```csharp
namespace InterchangeStudio.Core
{
    public enum RampEndKind : byte { Taper, Junction, Node, ExistingNode }

    public sealed record RampEnd
    {
        public RampEndKind Kind { get; init; }
        public EdgeId Edge { get; init; }                    // road the end attaches to (Taper / Junction)
        public float T { get; init; }                        // edge's own parameter, already split-safe
        public NodeId Node { get; init; }                    // ExistingNode
        public float3 Pos { get; init; }                     // centreline point, node, or free point
        public float2 Dir { get; init; }                     // travel direction at Pos
        public float Half { get; init; } = 6f;
        public float Elevation { get; init; }                // above terrain; negative in a cutting is kept (not clamped)
        public float Curvature { get; init; }                // of the attached road at Pos (G2 start / end)
        public bool Exact { get; init; }                     // NodeAt at an exact cut position
        public PrefabId Prefab { get; init; }
        public string Label { get; init; }
    }

    public sealed record RampShape
    {
        public float Radius { get; init; } = 60f;
        public bool ExactRadius { get; init; }
        public bool WantLoop { get; init; }
        public float MaxTurnDeg { get; init; } = 400f;
        public bool AllowLeft { get; init; }
        public IReadOnlyList<Pose2> Via { get; init; } = Array.Empty<Pose2>();
        public TaperSpec TaperA { get; init; }               // null: default for the end kind
        public TaperSpec TaperB { get; init; }
        public int Lanes { get; init; } = 1;
        public bool TwoWay { get; init; }
        public TerminalStyle Terminal { get; init; }
        public int LevelPriority { get; init; }              // loops 0 < directs 1 < trunks 2 < flyovers 3
        public string Label { get; init; }
    }

    public sealed record RampJob
    {
        public string Id { get; init; }
        public RampEnd A { get; init; }
        public RampEnd B { get; init; }
        public RampShape Shape { get; init; } = new RampShape();
        public PrefabId Prefab { get; init; }
        public string Group { get; init; }
        public GroupPolicy Policy { get; init; } = GroupPolicy.Optional;
        public IReadOnlyList<string> DependsOn { get; init; } = Array.Empty<string>();
        public int LineA { get; init; } = -1;                // ShareForks: carriageway index and distances
        public int LineB { get; init; } = -1;
        public float UA { get; init; }
        public float VB { get; init; }
    }

    public sealed class RoutedRamp
    {
        public RampJob Job { get; init; }
        public IPath2 Path { get; init; }
        public IReadOnlyList<ProfileCrossing> Crossings { get; init; } = Array.Empty<ProfileCrossing>();
        public ProfileSolution Profile { get; init; }
        public IReadOnlyList<NoNodeSpan> NoNode { get; init; } = Array.Empty<NoNodeSpan>();
        public float Length { get; init; }
        public float LargestTurnDeg { get; init; }
        public float MinRadius { get; init; }
        public bool Steep { get; init; }
        public bool UsedFallbackSmoother { get; init; }
        public int Rank { get; init; }
        public string Description { get; init; }             // "412 m, a 270 deg loop, up to 18 m high, over A and B"
    }

    public sealed record RouteRequest
    {
        public RampJob Job { get; init; }
        public PlanContext Context { get; init; }
        public IReadOnlyList<RoutedRamp> Earlier { get; init; } = Array.Empty<RoutedRamp>();
        public IReadOnlyCollection<EdgeId> Ignore { get; init; } = Array.Empty<EdgeId>();
    }

    public sealed class RouteResult
    {
        public RoutedRamp Best { get; init; }
        public IReadOnlyList<RoutedRamp> Alternatives { get; init; } = Array.Empty<RoutedRamp>();
        public Failure Failure { get; init; }
        public int Generated { get; init; }
        public int Evaluated { get; init; }
        public IReadOnlyList<Attempt> Rejected { get; init; } = Array.Empty<Attempt>();   // top rejected candidates with reasons
        public bool Ok => Best != null;
    }

    public interface IRouter { RouteResult Route(RouteRequest request); }

    public sealed class RampEndOption
    {
        public IPath2 Prim { get; init; }                    // taper S-curve / junction stub / node stub, in travel order
        public Pose2 Pose { get; init; }                     // where the routed middle starts (or ends)
        public float Curvature { get; init; }
        public bool Left { get; init; }
        public float LevelLen { get; init; }                 // keep the attached road's elevation this long
        public float SkipLen { get; init; }                  // ignore the attached road (and roads sharing its nodes) this long
    }

    public interface IRampEnds
    {
        RampEnd FromHit(PlanContext ctx, Hit hit, bool isStart);   // Taper on highways (cursor side picks direction on two-way), Junction on streets; null on rail
        RampEnd Match(PlanContext ctx, float2 at, float2 wantDir, RampEndKind? kind, float within, IReadOnlyCollection<EdgeId> ignore);   // kind null: re-derive from the matched road
        RampEnd NodeAt(PlanContext ctx, float2 xz, float2 dir, float? exactY, float elevation, string label);
        RampEnd Existing(PlanContext ctx, NodeId node, float2 dir);
        RampAnchor Anchor(RampEnd end);
        RampEnd Rematch(PlanContext ctx, RampAnchor anchor);       // null when the road is gone
        IReadOnlyList<RampEndOption> Options(PlanContext ctx, RampEnd end, bool isStart, RampShape shape);
    }

    public sealed class LevelResult
    {
        public IReadOnlyList<RoutedRamp> Ramps { get; init; } = Array.Empty<RoutedRamp>();   // with final profiles
        public IReadOnlyList<string> Failed { get; init; } = Array.Empty<string>();           // job ids that could not be levelled
        public int Sweeps { get; init; }
    }

    /// <summary>Joint levelling of every routed ramp of a stage (forward and backward sweeps, fork elevations as variables).</summary>
    public interface ILevelSolver { LevelResult Solve(IReadOnlyList<RoutedRamp> ramps, PlanContext ctx); }

    public sealed class MultiRampResult
    {
        public IReadOnlyList<GroupReport> Groups { get; init; } = Array.Empty<GroupReport>();
        public IReadOnlyList<RoutedRamp> Built { get; init; } = Array.Empty<RoutedRamp>();
        public int Ok { get; init; }
        public int Total { get; init; }
        public string First { get; init; }                   // first ramp's description or first failure reason
    }

    /// <summary>Plans jobs in dependency/priority order, levels them jointly, writes them through the builder (AddPath) inside transactions.</summary>
    public interface IMultiRampPlanner { MultiRampResult Plan(IPlanBuilder b, IReadOnlyList<RampJob> jobs); }

    public interface ISymmetryKit
    {
        /// <summary>Rotated (never mirrored) copies about the axis centre, refitted with Match and kinds re-derived.</summary>
        IReadOnlyList<RampJob> Copies(PlanContext ctx, RampJob main, Symmetry symmetry, out string note);
    }

    public sealed record Movement
    {
        public int From { get; init; }                       // index into Xp, Xm, Yp, Ym
        public int To { get; init; }
        public CwLine P { get; init; }
        public CwLine Q { get; init; }
        public bool FarSide { get; init; }                   // left turn in RHT
        public int Quadrant { get; init; }
    }

    public readonly struct Tangency
    {
        public readonly bool Ok;
        public readonly float U, V;                          // distance along P from P.P, and along Q from Q.P, to the tangent points
        public readonly float2 Centre;
        public Tangency(bool ok, float u, float v, float2 centre) { Ok = ok; U = u; V = v; Centre = centre; }
    }

    public interface IPresetGeometry
    {
        Tangency Solve(CwLine p, float offA, CwLine q, float offB, float radius, bool centreOnOuterSide, TrafficSide side);
        IReadOnlyList<Movement> Movements(Cross4Site site, TrafficSide side);
        RampJob ArcJob(PlanContext ctx, Movement m, float radius, TaperSpec taperA, TaperSpec taperB, bool loop, string id, IReadOnlyCollection<EdgeId> ignore);
        /// <summary>Gives each carriageway's two exits one diverge trunk to fork F (entrances: merge trunk from G); trunks use Ramp2 when they carry two movements.</summary>
        IReadOnlyList<RampJob> ShareForks(PlanContext ctx, Cross4Site site, IReadOnlyList<RampJob> jobs);
    }
}
```

### 6.11 Validate
Validators and the engine model.
<!-- contract:Validate -->
```csharp
namespace InterchangeStudio.Core
{
    /// <summary>Fatal: a planner bug, never emitted. Blocking: would be red; steers autofit and the status, never vetoes a click the game allows. Warn: shown as a secondary line.</summary>
    public enum Severity : byte { Warn = 0, Blocking = 1, Fatal = 2 }

    public sealed record Violation
    {
        public string Rule { get; init; }                    // "V03 SplitSafe"
        public Severity Severity { get; init; }
        public float3 Where { get; init; }
        public int Piece { get; init; } = -1;
        public string Group { get; init; }
        public string Message { get; init; }
        public Knob HelpedBy { get; init; } = Knob.Any;
    }

    public sealed class ValidationReport
    {
        public static readonly ValidationReport Empty = new ValidationReport(Array.Empty<Violation>());
        public ValidationReport(IReadOnlyList<Violation> items)
        {
            Items = items ?? Array.Empty<Violation>();
            foreach (var v in Items) { if (v.Severity == Severity.Fatal) HasFatal = true; else if (v.Severity == Severity.Blocking) HasBlocking = true; }
        }
        public IReadOnlyList<Violation> Items { get; }
        public bool HasFatal { get; }
        public bool HasBlocking { get; }
        public bool Clean => !HasFatal && !HasBlocking;
        public int Count(Severity s) { int n = 0; foreach (var v in Items) if (v.Severity == s) n++; return n; }
    }

    /// <summary>A body in the after-world: a remaining existing edge or a new piece, as a polyline with absolute y.</summary>
    public readonly struct Body
    {
        public readonly int Piece;                           // -1 for an existing edge
        public readonly EdgeId Edge;
        public readonly float3[] Samples;
        public readonly float Half;
        public readonly NetKind Kind;
        public Body(int piece, EdgeId edge, float3[] samples, float half, NetKind kind) { Piece = piece; Edge = edge; Samples = samples; Half = half; Kind = kind; }
        public bool IsNew => Piece >= 0;
    }

    public interface IAfterWorld
    {
        INetwork Before { get; }
        BuildPlan Plan { get; }
        bool IsDeleted(EdgeId edge);
        void BodiesNear(Rect2 box, List<Body> into);
        Body BodyOf(int piece);
        /// <summary>True when the two bodies meet at a planned junction or a shared node (exempt from clash rules near it).</summary>
        bool SharesJoin(in Body a, in Body b, out float3 at);
    }

    public interface IValidator
    {
        string Id { get; }
        Severity Default { get; }
        void Check(IAfterWorld world, PlanContext ctx, List<Violation> into);
    }

    public interface IValidatorSet
    {
        IReadOnlyList<IValidator> All { get; }
        ValidationReport Run(BuildPlan plan, PlanContext ctx);
    }

    public sealed record SimIssue(string Kind, float3 Where, EdgeId Edge, NodeId Node, string Text);

    public sealed class SimReport
    {
        public static readonly SimReport Empty = new SimReport();
        public IReadOnlyList<SimIssue> Dangling { get; init; } = Array.Empty<SimIssue>();       // a reference to an edge the batch replaces
        public IReadOnlyList<SimIssue> DeadEnds { get; init; } = Array.Empty<SimIssue>();       // a new piece end that connects to nothing
        public IReadOnlyList<SimIssue> Slivers { get; init; } = Array.Empty<SimIssue>();        // a split leaving < 30 m
        public IReadOnlyList<SimIssue> FlowConflicts { get; init; } = Array.Empty<SimIssue>();  // one-way sink/source or reversed continuation
        public bool Clean => Dangling.Count == 0 && DeadEnds.Count == 0 && Slivers.Count == 0 && FlowConflicts.Count == 0;
    }

    public sealed class SimResult
    {
        public INetwork After { get; init; }
        public SimReport Report { get; init; } = SimReport.Empty;
        public IReadOnlyDictionary<EdgeId, IReadOnlyList<EdgeId>> Replaced { get; init; } = new Dictionary<EdgeId, IReadOnlyList<EdgeId>>();
    }

    /// <summary>Pure model of how the engine applies a plan: deletions, splits at t, nodes from identical positions, 2-way continuations, healing of nodes left with two compatible edges. Calibrated against the three historic failures.</summary>
    public interface IEngineSim { SimResult Apply(INetwork before, BuildPlan plan); }
}
```

### 6.12 Text
Explanation, status and red reports.
<!-- contract:Text -->
```csharp
namespace InterchangeStudio.Core
{
    /// <summary>Values 0-3 match the old STATUS_KIND.</summary>
    public enum StatusKind : byte { Hint = 0, Ready = 1, Problem = 2, Built = 3, Working = 4 }

    public sealed record Reason(string Code, string Text);
    public sealed record Attempt(string What, bool Won, string Why);
    public sealed record ConfigChange(Knob Knob, string From, string To);
    public sealed record Note(string Code, string Text, bool IsWarning);
    public sealed record Fact(string Code, string Label, string Value);
    /// <summary>One-click fix: sets a setting (SettingKey = Value) and/or switches style.</summary>
    public sealed record Suggestion(string Id, string Text, string SettingKey, string Value, StyleId? Style);

    public sealed record Explanation
    {
        public string Headline { get; init; } = "";
        public IReadOnlyList<Reason> Because { get; init; } = Array.Empty<Reason>();
        public IReadOnlyList<Attempt> Tried { get; init; } = Array.Empty<Attempt>();
        public IReadOnlyList<ConfigChange> Autofit { get; init; } = Array.Empty<ConfigChange>();
        public IReadOnlyList<Note> Warnings { get; init; } = Array.Empty<Note>();
        public IReadOnlyList<Fact> Facts { get; init; } = Array.Empty<Fact>();
        public IReadOnlyList<Suggestion> Suggestions { get; init; } = Array.Empty<Suggestion>();
        public Failure Failure { get; init; }
    }

    public sealed record StageView
    {
        public int Index { get; init; } = 1;                 // 1-based
        public int Count { get; init; } = 1;
        public string Label { get; init; }                   // "Bridge", "Ramps"
        public string State { get; init; }                   // "done" | "checking" | "waiting" | "failed"
    }

    /// <summary>Everything the status card shows. Narrator renders it from a PlanResult; the UI never formats text itself.</summary>
    public sealed record StatusView
    {
        public StatusKind Kind { get; init; }
        public string Headline { get; init; } = "";
        public IReadOnlyList<string> Detail { get; init; } = Array.Empty<string>();      // up to 3 lines
        public IReadOnlyList<Fact> Facts { get; init; } = Array.Empty<Fact>();          // chips
        public IReadOnlyList<ConfigChange> Autofit { get; init; } = Array.Empty<ConfigChange>();
        public IReadOnlyList<Note> Warnings { get; init; } = Array.Empty<Note>();
        public IReadOnlyList<Suggestion> Suggestions { get; init; } = Array.Empty<Suggestion>();
        public IReadOnlyList<Attempt> Tried { get; init; } = Array.Empty<Attempt>();    // the "Why" expander
        public StageView Stage { get; init; }
        public bool OfferUseMySettings { get; init; }
        public string Badge { get; init; }                   // e.g. "This stretch runs against its carriageway"
        public static StatusView Of(StatusKind kind, string headline) => new StatusView { Kind = kind, Headline = headline ?? "" };
    }

    public enum RedKind : byte { Pillar, Edge, Node, Other }

    public readonly struct RedItem
    {
        public readonly RedKind Kind;
        public readonly bool Existing;                       // Temp.m_Original was set
        public readonly string PrefabName;
        public readonly float3 Position;
        public readonly int Piece;                           // nearest plan piece, -1 unknown
        public RedItem(RedKind kind, bool existing, string prefabName, float3 position, int piece) { Kind = kind; Existing = existing; PrefabName = prefabName; Position = position; Piece = piece; }
    }

    public sealed class RedReport
    {
        public static readonly RedReport None = new RedReport();
        public IReadOnlyList<RedItem> Near { get; init; } = Array.Empty<RedItem>();   // within RedRadius of this preview's pieces
        public int ElsewhereCount { get; init; }                                       // red elsewhere in the city (blocks GetAllowApply)
        public string PlanFingerprint { get; init; } = "";                             // which emitted plan this was read against
    }

    public interface INarrator
    {
        StatusView ForResult(PlanResult result, PlanConfig user, StageView stage);
        StatusView ForLookup(SiteLookup lookup);
        StatusView Message(StatusKind kind, string code, params string[] args);
        string DescribeRed(RedReport red, float3 cursor, int max);
        IReadOnlyList<ConfigChange> Changes(PlanConfig user, PlanConfig chosen, Knob relevant);
    }
}
```

### 6.13 Styles
StyleInfo, PlanContext, CoreServices and IStyle.
<!-- contract:Styles -->
```csharp
namespace InterchangeStudio.Core
{
    public sealed record StyleInfo
    {
        public StyleId Id { get; init; }
        public string Key { get; init; }                     // persisted and used by the UI: "diamond"
        public string Tab { get; init; }                     // crossings | interchanges | freehand | fix
        public string Name { get; init; }
        public string Blurb { get; init; }
        public string More { get; init; }
        public string Icon { get; init; }                    // "is-diamond.svg"
        public IReadOnlyList<string> Settings { get; init; } = Array.Empty<string>();   // SettingKeys shown for this style
        public Knob SensitiveTo { get; init; }               // autofit knobs that can change the outcome
        public IReadOnlyList<SiteKind> Accepts { get; init; } = Array.Empty<SiteKind>();
        public bool Ramped { get; init; }
        public bool Autofit { get; init; } = true;
        public bool PreserveMainline { get; init; }          // validator V14: highway carriageway edges may only be split
        public bool AllowPartial { get; init; }              // presets / free ramp: "N of M ramps" is buildable
        public bool Internal { get; init; }                  // RailOverpass: never a tile
        public PrefabCapabilities Needs { get; init; }
    }

    public sealed record LearnedDisc(float2 Centre, float Radius, RedKind Kind);

    /// <summary>In-game red turned into keep-out discs for the router and pillar placer (per site, per session). Immutable.</summary>
    public sealed class LearnedObstacles
    {
        public static readonly LearnedObstacles None = new LearnedObstacles(Array.Empty<LearnedDisc>());
        public LearnedObstacles(IReadOnlyList<LearnedDisc> discs) { Discs = discs ?? Array.Empty<LearnedDisc>(); }
        public IReadOnlyList<LearnedDisc> Discs { get; }
        public LearnedObstacles With(IEnumerable<LearnedDisc> more) { var l = new List<LearnedDisc>(Discs); l.AddRange(more); return new LearnedObstacles(l); }
        public ulong StableHash()
        {
            var h = Fnv64.Start();
            foreach (var d in Discs) { h.Add(new float3(d.Centre.x, d.Radius, d.Centre.y), 0.5f); h.Add((int)d.Kind); }
            return h.Value;
        }
    }

    /// <summary>Every cross-unit service. The composition root (Pipeline unit) fills it; tests may substitute fakes.</summary>
    public sealed record CoreServices
    {
        public ISnapshotBuilder Snapshots { get; init; }
        public ICurveKit Curves { get; init; }
        public INetworkKit Network { get; init; }
        public IProfileSolver Profiles { get; init; }
        public IAlignmentSmoother Smoother { get; init; }
        public IPathWriter Writer { get; init; }
        public IPlanBuilderFactory Builders { get; init; }
        public ILiftKit Lift { get; init; }
        public IServiceKit Service { get; init; }
        public IRingKit Rings { get; init; }
        public IStreetSurgery Surgery { get; init; }
        public IFrontageKit Frontage { get; init; }
        public IUTurnKit UTurns { get; init; }
        public IRampEnds RampEnds { get; init; }
        public IRouter Router { get; init; }
        public ILevelSolver Levels { get; init; }
        public IMultiRampPlanner MultiRamp { get; init; }
        public ISymmetryKit Symmetry { get; init; }
        public IPresetGeometry Presets { get; init; }
        public IValidatorSet Validators { get; init; }
        public IEngineSim Sim { get; init; }
        public ISiteFinder Sites { get; init; }
        public IFixFinder Fix { get; init; }
        public IStyleRegistry Styles { get; init; }
        public IAutofitFactory Autofit { get; init; }
        public INarrator Narrator { get; init; }
    }

    /// <summary>Everything a style or kit needs. Immutable; autofit makes variants with <c>ctx with { Cfg = ... }</c>.</summary>
    public sealed record PlanContext
    {
        public INetwork Net { get; init; }
        public PlanConfig Cfg { get; init; } = new PlanConfig();
        public CoreServices Services { get; init; }
        public IPlanLog Log { get; init; } = NullLog.Instance;
        public IBudget Budget { get; init; } = UnlimitedBudget.Instance;
        public LearnedObstacles Learned { get; init; } = LearnedObstacles.None;
        public CancellationToken Cancel { get; init; }
        public ITerrain Terrain => Net.Terrain;
        public EngineRules Rules => Cfg.Rules;
        public TrafficSide Side => Cfg.Side;
    }

    public interface IStyle
    {
        StyleInfo Info { get; }
        PlanOutcome Plan(PlanContext ctx, Site site);
        /// <summary>Flat deck beyond the obstacle that this style's stage 1 needs (LiftThen): Overpass 12, Diamond/SPUI 26 or 40, others 48 or 62, plus DeckMarginExtra.</summary>
        float DeckMargin(PlanConfig cfg);
    }

    public interface IStyleRegistry
    {
        IStyle Get(StyleId id);
        StyleInfo ByKey(string key);                         // null when unknown
        IReadOnlyList<StyleInfo> All { get; }
    }
}
```

### 6.14 Autofit
<!-- contract:Autofit -->
```csharp
namespace InterchangeStudio.Core
{
    public enum GameVerdict : byte { Untested, Clean, Red }

    /// <summary>One autofit layout. Row 0 is the player's own settings. Apply never lowers grade or raises clearance below/above the player's values.</summary>
    public sealed record FitVariant
    {
        public int Index { get; init; }
        public float RadiusMul { get; init; } = 1f;
        public int AltRoute { get; init; }
        public float MinGrade { get; init; }
        public float MaxClearance { get; init; } = float.MaxValue;
        public RampLength? Length { get; init; }
        public bool FlipLift { get; init; }
        public float DeckMarginExtra { get; init; }
        public float Cost { get; init; }                     // deviation cost: Clearance > Flip > Grade > Compact > Radius > Route

        public Knob Touches =>
            (MinGrade > 0f ? Knob.Grade : Knob.None) | (MaxClearance < float.MaxValue ? Knob.Clearance : Knob.None) |
            (math.abs(RadiusMul - 1f) > 1e-3f ? Knob.Radius : Knob.None) | (Length.HasValue ? Knob.Compact : Knob.None) |
            (FlipLift ? Knob.Lift : Knob.None) | (AltRoute != 0 ? Knob.Route : Knob.None) | (DeckMarginExtra > 0f ? Knob.DeckMargin : Knob.None);

        public PlanConfig Apply(PlanConfig c) => c with
        {
            Grade = math.max(c.Grade, MinGrade),
            Clearance = math.min(c.Clearance, MaxClearance),
            RampLength = Length ?? c.RampLength,
            Lift = FlipLift ? (c.Lift == LiftPreference.StreetOver ? LiftPreference.HighwayOver : LiftPreference.StreetOver) : c.Lift,
            RadiusMul = RadiusMul,
            AltRoute = AltRoute,
            DeckMarginExtra = DeckMarginExtra,
        };
    }

    public sealed class FitCandidate
    {
        public FitVariant Variant { get; init; }
        public PlanConfig Cfg { get; init; }
        public PlanOutcome Outcome { get; init; }
        public ValidationReport Report { get; init; } = ValidationReport.Empty;
        public SimReport Sim { get; init; } = SimReport.Empty;
        public BuildPlan PredictedNext { get; init; }        // speculative stage 2 on net.With(stage1); never emitted
        public Failure NextFailure { get; init; }
        public double Score { get; init; }                   // 1e6 Fatal + 1000 Blocking + 10 Warn + stage-2 penalty + variant cost
        public string Fingerprint { get; init; }
        public GameVerdict Verdict { get; set; }             // set by the search when the game reports
        public int RedCount { get; set; }
    }

    public sealed class FitTrace
    {
        public IReadOnlyList<FitCandidate> Tried { get; init; } = Array.Empty<FitCandidate>();
        public FitCandidate Chosen { get; init; }
        public int Generated { get; init; }
        public bool Exhausted { get; init; }
    }

    public interface IAutofitSearch
    {
        bool Done { get; }
        bool Step(IBudget budget);                           // plans, validates and simulates the next variant; false when nothing is left
        FitCandidate Proposal { get; }                       // best core-clean candidate the game has not refuted, else least-bad
        bool Refute(RedReport red);                          // marks the proposal Red, learns discs; false when exhausted
        FitCandidate LeastRed { get; }
        FitTrace Trace { get; }
    }

    public interface IAutofitFactory
    {
        IAutofitSearch Create(PlanContext userCtx, StyleId style, Site site, Knob locked, int stage);
    }
}
```

### 6.15 Pipeline
<!-- contract:Pipeline -->
```csharp
namespace InterchangeStudio.Core
{
    public sealed record PlanRequest
    {
        public PlanContext Context { get; init; }            // user config, network, services, learned obstacles
        public StyleId Style { get; init; }
        public Site Site { get; init; }
        public FollowUp Continue { get; init; }              // stage-2 re-plan
        public int Stage { get; init; } = 1;
    }

    public readonly struct PlanKey : IEquatable<PlanKey>
    {
        public readonly string Site;
        public readonly StyleId Style;
        public readonly ulong Config;
        public readonly long Region;
        public readonly int Stage;
        public readonly ulong Learned;
        public PlanKey(string site, StyleId style, ulong config, long region, int stage, ulong learned)
        { Site = site ?? ""; Style = style; Config = config; Region = region; Stage = stage; Learned = learned; }

        public static PlanKey For(PlanRequest r)
        {
            var ctx = r.Context;
            long region = r.Site == null ? ctx.Net.Version : ctx.Net.RegionVersion(r.Site.Bounds.Grow(ctx.Rules.RegionMargin));
            return new PlanKey(r.Site == null ? "" : r.Site.Key.Value, r.Style, ctx.Cfg.StableHash(), region, r.Stage, ctx.Learned.StableHash());
        }

        public bool Equals(PlanKey o) => string.Equals(Site, o.Site, StringComparison.Ordinal) && Style == o.Style && Config == o.Config && Region == o.Region && Stage == o.Stage && Learned == o.Learned;
        public override bool Equals(object o) => o is PlanKey k && Equals(k);
        public override int GetHashCode() => (Site ?? "").GetHashCode() ^ ((int)Style * 31) ^ Config.GetHashCode() ^ Region.GetHashCode() ^ (Stage * 7) ^ Learned.GetHashCode();
        public override string ToString() => Site + "|" + Style + "|" + Config.ToString("x") + "|r" + Region + "|s" + Stage;
    }

    public sealed class PlanResult
    {
        public PlanKey Key { get; init; }
        public Site Site { get; init; }
        public BuildPlan Plan { get; init; }                 // null on failure
        public ValidationReport Report { get; init; } = ValidationReport.Empty;
        public SimReport Sim { get; init; } = SimReport.Empty;
        public Failure Failure { get; init; }
        public FitTrace Fit { get; init; } = new FitTrace();
        public PlanConfig Chosen { get; init; }
        public Explanation Why { get; init; } = new Explanation();
        public BuildPlan PredictedNext { get; init; }
        public Failure NextFailure { get; init; }
        public double Millis { get; init; }
        public bool Ok => Plan != null;
    }

    public interface IPlanJob
    {
        PlanKey Key { get; }
        bool Done { get; }
        Exception Error { get; }
        void Advance(IBudget budget);                        // main-thread time slice; no-op for worker jobs
        PlanResult Current { get; }                          // best so far; never null after the first Advance
        void GameRejected(RedReport red);                    // emitted candidate went red: next clean candidate or least-red
        void Cancel();
    }

    public interface IPlanService
    {
        bool Async { get; }
        IPlanJob Start(PlanRequest request);
        bool TryCached(PlanKey key, out PlanResult result);
        void Retain(IReadOnlyCollection<PlanKey> keep);
    }

    /// <summary>Synchronous convenience for tests and the harness.</summary>
    public interface IPlanner { PlanResult RunToCompletion(PlanRequest request); }
}
```

### 6.16 Session
<!-- contract:Session -->
```csharp
namespace InterchangeStudio.Core
{
    public enum Phase : byte { Idle, Planning, Previewing, Applying, Settling, FollowUpPlanning, FollowUpPreviewing, Pinned }

    public enum PreviewOpKind : byte { None, Show }

    /// <summary>What to emit this frame. Definitions are destroyed every frame, so Show must be returned every frame the preview stays up.</summary>
    public readonly struct PreviewOp
    {
        public readonly PreviewOpKind Kind;
        public readonly BuildPlan Plan;
        PreviewOp(PreviewOpKind kind, BuildPlan plan) { Kind = kind; Plan = plan; }
        public static PreviewOp None => new PreviewOp(PreviewOpKind.None, null);
        public static PreviewOp Show(BuildPlan plan) => new PreviewOp(PreviewOpKind.Show, plan ?? throw new ArgumentNullException(nameof(plan)));
    }

    public readonly struct CameraMove
    {
        public readonly float3 Pivot;
        public readonly float ZoomCap;                       // 350
        public readonly float ZoomAbove;                     // cap only when the zoom is above this (700)
        public CameraMove(float3 pivot, float zoomCap, float zoomAbove) { Pivot = pivot; ZoomCap = zoomCap; ZoomAbove = zoomAbove; }
    }

    public sealed record FrameInput
    {
        public int Frame { get; init; }
        public double Time { get; init; }                    // seconds
        public Hit? Hover { get; init; }
        public bool Click { get; init; }
        public bool Cancel { get; init; }
        public bool FindNext { get; init; }
        public bool Capture { get; init; }
        public bool UseMySettings { get; init; }
        public INetwork Net { get; init; }
        public PlanConfig Config { get; init; }
        public StyleId Style { get; init; }
        public RedReport Red { get; init; } = RedReport.None;
        public int TempCount { get; init; }                  // Temp entity count; must be stable 2 frames for a verdict
        public bool AllowApply { get; init; }                // ToolBaseSystem.GetAllowApply()
        public bool IgnoreErrors { get; init; }              // ToolSystem.ignoreErrors (Anarchy-like)
        public IBudget Budget { get; init; } = UnlimitedBudget.Instance;
        public float3 CameraPivot { get; init; }
        public float SnapshotProgress { get; init; } = 1f;   // < 1 while the first snapshot is being read
    }

    /// <summary>Type-level guarantee: an Apply frame carries no plan to emit.</summary>
    public sealed class FrameOutput
    {
        FrameOutput() { }
        public PreviewOp Preview { get; private set; }
        public bool Apply { get; private set; }
        public StatusView Status { get; private set; }
        public IReadOnlyList<NameCarry> CaptureNamesNow { get; private set; } = Array.Empty<NameCarry>();
        public CameraMove? Camera { get; private set; }
        public bool ExitTool { get; private set; }
        public CaptureBundle Capture { get; private set; }
        public BuildPlan Ghost { get; private set; }         // optional outline of the predicted stage 2

        public static FrameOutput ApplyNow(StatusView status, IReadOnlyList<NameCarry> names) =>
            new FrameOutput { Apply = true, Preview = PreviewOp.None, Status = status, CaptureNamesNow = names ?? Array.Empty<NameCarry>() };

        public static FrameOutput Frame(PreviewOp preview, StatusView status, CameraMove? camera = null, bool exitTool = false, BuildPlan ghost = null, CaptureBundle capture = null) =>
            new FrameOutput { Preview = preview, Status = status, Camera = camera, ExitTool = exitTool, Ghost = ghost, Capture = capture };
    }

    public sealed record SessionTuning
    {
        public int RedWindow { get; init; } = 3;             // trust red/clean only after the same plan has been up this many frames
        public int TempStableFrames { get; init; } = 2;
        public int SettleQuietFrames { get; init; } = 2;     // after the network version changes, wait this many quiet frames
        public int SettleTimeout { get; init; } = 120;
        public int MaxGameTrials { get; init; } = 6;
        public int KeepOldPreviewFrames { get; init; } = 15;
        public double PinMinSeconds { get; init; } = 1.5;
        public double PinMaxSeconds { get; init; } = 4.0;
        public double FindNextHoldSeconds { get; init; } = 6.5;
        public int PlanBudgetMs { get; init; } = 6;
    }

    public interface IToolSession
    {
        Phase Phase { get; }
        RampAnchor Anchor { get; }                           // free-ramp click 1
        FrameOutput Step(FrameInput input);
        void Reset();
        void ReportCrash(string where);
    }
}
```

### 6.17 Diagnostics
<!-- contract:Diagnostics -->
```csharp
namespace InterchangeStudio.Core
{
    /// <summary>Terrain samples on a regular grid (captures and tests). Model unit wraps it as an ITerrain (bilinear).</summary>
    public sealed class HeightSamples
    {
        public float2 Origin { get; init; }
        public float Cell { get; init; } = 8f;
        public int Width { get; init; }
        public int Height { get; init; }
        public float[] Heights { get; init; } = Array.Empty<float>();   // row-major, z rows
    }

    /// <summary>"Save a report of this spot": everything needed to replay a hover offline as a regression scenario.</summary>
    public sealed class CaptureBundle
    {
        public int FormatVersion { get; init; } = 1;
        public string Created { get; init; }
        public string GameVersion { get; init; }
        public SnapshotData Snapshot { get; init; }          // cropped to 1.5 km around the cursor
        public HeightSamples Terrain { get; init; }          // 3 km at 8 m
        public PlanConfig Config { get; init; }
        public StyleId Style { get; init; }
        public Hit Hit { get; init; }
        public RampAnchor From { get; init; }
        public string PlanFingerprint { get; init; }
        public ValidationReport Report { get; init; }
        public RedReport Red { get; init; }
        public string StatusText { get; init; }
        public string Expect { get; init; }                  // sidecar assertion: "builds clean" | "fails: <code>"
    }

    public interface ICaptureCodec
    {
        string Write(CaptureBundle bundle);
        CaptureBundle Read(string json);
    }
}
```

### 6.18 UI view model (namespace InterchangeStudio.UI)
<!-- contract:UI -->
```csharp
namespace InterchangeStudio.UI
{
    /// <summary>Binding namespace and names. The .mjs uses exactly these strings.</summary>
    public static class Bindings
    {
        public const string Namespace = "InterchangeStudio";

        // ValueBindings (C# -> JS)
        public const string ToolActive = "TOOL_ACTIVE";      // bool
        public const string Catalog = "CATALOG";             // string: CatalogView json (sent once, re-sent if prefab capabilities change)
        public const string Settings = "SETTINGS";           // string: SettingsView json
        public const string State = "STATE";                 // string: StateView json (pushed only on change)
        public const string HotKey = "HOTKEY";               // string: display of the current binding

        // TriggerBindings (JS -> C#)
        public const string ToggleTool = "TOGGLE_TOOL";      // no args
        public const string FindNext = "FIND_NEXT";          // no args
        public const string Capture = "CAPTURE";             // no args
        public const string UseMySettings = "USE_MY_SETTINGS"; // no args
        public const string DismissIntro = "DISMISS_INTRO";  // no args
        public const string SetStyle = "SET_STYLE";          // string style key (one trigger per tile click)
        public const string Set = "SET";                     // string "key=value", parsed and clamped by SettingsSchema
        public const string SetSize = "SET_SIZE";            // int 0..2
        public const string ApplySuggestion = "APPLY_SUGGESTION"; // string suggestion id
        public const string PanelPrefs = "PANEL_PREFS";      // string PanelPrefs json (on drag end, tab change, collapse)
    }

    /// <summary>Glyphs the game font is known to render. Never use the triangle arrows (they render as boxes).</summary>
    public static class Glyphs
    {
        public const string Plus = "+";
        public const string Minus = "−";
        public const string Times = "×";
        public const string Dot = "·";
        public const string Degree = "°";
    }

    public sealed record PanelPrefs
    {
        public float X { get; init; } = 12f;                 // rem
        public float Y { get; init; } = 110f;
        public string Tab { get; init; } = "crossings";
        public bool SettingsOpen { get; init; } = true;
        public bool AdvancedOpen { get; init; }
        public bool IntroSeen { get; init; }
    }

    public sealed record TabView(string Key, string Label);

    public sealed record TileView
    {
        public string Key { get; init; }
        public string Tab { get; init; }
        public string Name { get; init; }
        public string Blurb { get; init; }
        public string More { get; init; }
        public string Icon { get; init; }                    // coui://ui-mods/images/is-*.svg
        public IReadOnlyList<string> Settings { get; init; } = Array.Empty<string>();
        public bool Enabled { get; init; } = true;
        public string DisabledReason { get; init; }          // e.g. "No highway ramp road type is installed"
    }

    public sealed record SettingView
    {
        public string Key { get; init; }
        public string Kind { get; init; }                    // toggle | choice | stepper
        public string Label { get; init; }
        public string Help { get; init; }
        public string Group { get; init; }
        public double Min { get; init; }
        public double Max { get; init; }
        public double Step { get; init; }
        public string Unit { get; init; }
        public IReadOnlyList<string> Options { get; init; } = Array.Empty<string>();
    }

    public sealed record CatalogView
    {
        public IReadOnlyList<TabView> Tabs { get; init; } = Array.Empty<TabView>();
        public IReadOnlyList<TileView> Tiles { get; init; } = Array.Empty<TileView>();
        public IReadOnlyList<SettingView> Settings { get; init; } = Array.Empty<SettingView>();
    }

    public sealed record SettingsView
    {
        public string Style { get; init; }
        public string Size { get; init; }                    // compact | standard | spacious | custom
        public IReadOnlyDictionary<string, string> Values { get; init; } = new Dictionary<string, string>();
        public PanelPrefs Panel { get; init; } = new PanelPrefs();
    }

    public sealed record FixCounts(int Crossings, int Rail, int Manual);

    public sealed record StateView
    {
        public InterchangeStudio.Core.StatusView Status { get; init; } = new InterchangeStudio.Core.StatusView();
        public FixCounts Fix { get; init; }
        public bool Working { get; init; }
        public string Notice { get; init; }                  // one-time notices (old mod installed, keybind not migrated)
        public string Summary { get; init; }                 // "4 ramps · max 5 % · min radius 62 m · bridge 420 m"
    }

    /// <summary>Pure view model: JSON in and out of the panel. Lives in Core/Panel (namespace InterchangeStudio.UI).</summary>
    public interface IPanelModel
    {
        string CatalogJson(IReadOnlyList<InterchangeStudio.Core.StyleInfo> styles, IReadOnlyList<InterchangeStudio.Core.SettingSpec> settings, InterchangeStudio.Core.PrefabCapabilities caps);
        string SettingsJson(InterchangeStudio.Core.PlanConfig cfg, InterchangeStudio.Core.StyleId style, PanelPrefs prefs);
        string StateJson(StateView state);
        bool TryApply(string keyEqualsValue, InterchangeStudio.Core.PlanConfig cfg, InterchangeStudio.Core.StyleId style,
                      out InterchangeStudio.Core.PlanConfig newCfg, out InterchangeStudio.Core.StyleId newStyle, out string error);
        PanelPrefs ParsePrefs(string json);
        string PersistJson(InterchangeStudio.Core.PlanConfig cfg, InterchangeStudio.Core.StyleId style, PanelPrefs prefs);
        bool TryLoad(string persisted, out InterchangeStudio.Core.PlanConfig cfg, out InterchangeStudio.Core.StyleId style, out PanelPrefs prefs);
    }
}
```

### 6.19 Game ids (namespace InterchangeStudio.Game)
<!-- contract:Game -->
```csharp
namespace InterchangeStudio.Game
{
    /// <summary>Stable ids. The adapter classes themselves reference game DLLs and live in Game/ (outlined in DESIGN.md 13).</summary>
    public static class ModIds
    {
        public const string ModId = "InterchangeStudio";
        public const string DisplayName = "Interchange Studio";
        public const string ToolId = "Interchange Studio";
        public const string SettingsId = "InterchangeStudio";
        public const string SettingsFile = "ModsSettings/InterchangeStudio/InterchangeStudio";
        public const string ToggleAction = "ToggleInterchangeStudio";
        public const string LogName = "InterchangeStudio";
        public const string ImagePrefix = "is-";
        public const string ImageRoot = "coui://ui-mods/images/";
        public const string ToolbarIcon = "coui://ui-mods/images/is-toolbar.svg";
        public const string CaptureFolder = "ModsData/InterchangeStudio/captures";
        public const string LegacyModId = "ClaudeInterchanges";
        public const string LegacySettingsFile = "ModsSettings/ClaudeInterchanges/ClaudeInterchanges";
    }

    /// <summary>Old (ToolMode, PresetStyle) pair to the new style, for LegacyImport.</summary>
    public static class LegacyMap
    {
        public static InterchangeStudio.Core.StyleId StyleOf(int mode, int preset)
        {
            if (mode == 8) return (InterchangeStudio.Core.StyleId)(10 + Math.Clamp(preset, 0, 6));
            if (mode >= 0 && mode <= 7) return (InterchangeStudio.Core.StyleId)mode;
            return InterchangeStudio.Core.StyleId.Overpass;
        }
    }
}
```

### 6.20 Composition root and implementation entry points (not in Contracts.cs)

These are the public entry points each unit must expose, so other units and tests can construct them. Every class is `sealed`, takes its collaborators through `PlanContext.Services` at call time (never through statics), and has a parameterless constructor unless stated otherwise.

```csharp
namespace InterchangeStudio.Core
{
    public static class CoreServicesFactory { public static CoreServices CreateDefault(); }        // U37
    public sealed class SnapshotBuilder : ISnapshotBuilder { }                                       // U03
    public sealed class PrefabTable : IPrefabTable { public PrefabTable(IReadOnlyList<PrefabInfo> all); }   // U04
    public sealed class GridTerrain : ITerrain { public GridTerrain(HeightSamples samples); }         // U04
    public sealed class FlatTerrain : ITerrain { public FlatTerrain(float height = 0f); }             // U04
    public sealed class PlaneTerrain : ITerrain { public PlaneTerrain(float height, float2 slope); } // U04
    public sealed class FuncTerrain : ITerrain { public FuncTerrain(Func<float2, float> f); }        // U04
    public sealed class CurveKit : ICurveKit { }   // U06 (facade in PathOps.cs over CurveMath / Arcs / Cross2D from U05)
    public sealed class LaplacianSmoother : IAlignmentSmoother { }                                   // U07
    public sealed class ClothoidSmoother : IAlignmentSmoother { public ClothoidSmoother(IAlignmentSmoother fallback); }   // U07
    public sealed class ProfileSolver : IProfileSolver { }                                           // U08
    public sealed class LevelSolver : ILevelSolver { }                                               // U09
    public sealed class NetworkKit : INetworkKit { }                                                 // U10
    public sealed class SiteFinder : ISiteFinder { }                                                 // U13
    public sealed class FixFinder : IFixFinder { }                                                   // U13
    public sealed class PlanBuilderFactory : IPlanBuilderFactory { }                                 // U14
    public sealed class PathWriter : IPathWriter { }                                                 // U15
    public sealed class ValidatorSet : IValidatorSet { public static ValidatorSet Default(); }       // U16 (+ U17 rules)
    public sealed class EngineSim : IEngineSim { }                                                   // U18
    public sealed class LiftKit : ILiftKit { }                                                       // U19
    public sealed class ServiceKit : IServiceKit { }                                                 // U20
    public sealed class StreetSurgery : IStreetSurgery { }  public sealed class RingKit : IRingKit { } // U21
    public sealed class FrontageKit : IFrontageKit { }  public sealed class UTurnKit : IUTurnKit { }  // U22
    public sealed class RampEnds : IRampEnds { }  public sealed class SymmetryKit : ISymmetryKit { } // U23
    public sealed class Router : IRouter { }                                                         // U24
    public sealed class MultiRampPlanner : IMultiRampPlanner { }                                     // U25
    public sealed class PresetGeometry : IPresetGeometry { }                                         // U26
    public sealed class StyleRegistry : IStyleRegistry { public static StyleRegistry Default(); }   // U27 (styles from U28-U34)
    public sealed class AutofitFactory : IAutofitFactory { }                                         // U35
    public sealed class PlanService : IPlanService { public PlanService(bool async, int capacity = 64); }   // U36
    public sealed class Planner : IPlanner { }                                                       // U36
    public sealed class ToolSession : IToolSession { public ToolSession(CoreServices services, IPlanService plans, SessionTuning tuning); }   // U38
    public sealed class Narrator : INarrator { }                                                     // U39
    public static class SettingsSchema { public static IReadOnlyList<SettingSpec> All { get; } public static PlanConfig Clamp(PlanConfig c); }   // U40
    public sealed class CaptureCodec : ICaptureCodec { }                                             // U41
}
namespace InterchangeStudio.UI { public sealed class PanelModel : IPanelModel { } }                 // U40
```

---

## 7. Planning pipeline

```
 ECS --NetworkReader (time-sliced, change-detected)--> SnapshotData --ISnapshotBuilder--> INetwork(v)   (same instance when nothing changed)
 raycast --> Hit;  panel --> PlanConfig + StyleId
                       |
 ToolSession.Step(FrameInput)
   |-- ISiteFinder.Find(ctx, hit, style, anchor, sticky)  -> SiteLookup (Site | hint | reversed-run badge)
   |-- key = PlanKey.For(request)   (canonical site key, cfg.StableHash, RegionVersion(site bounds + 400 m), stage, learned)
   |-- IPlanService.TryCached(key) ?  : Start(request) -> IPlanJob
   |        IPlanJob.Advance(budget)    (or worker thread)
   |          IAutofitSearch.Step: for each variant v (cost order, filtered, deduped)
   |             ctx' = ctx with { Cfg = v.Apply(user) }
   |             outcome = Styles[style].Plan(ctx', site)          builder: groups, joins, BatchSafety (promote | stage)
   |             report  = Validators.Run(plan, ctx')              Fatal never shown; Blocking steers; Warn shows
   |             sim     = Sim.Apply(net, plan)                    Dangling / DeadEnds / Slivers / FlowConflicts
   |             if plan.FollowUp: stage2 = Styles[f.Style].Plan(ctx' on sim.After, Sites.Relocate(sim.After, f))   speculative, never emitted
   |             score   = 1e6 Fatal + 1000 Blocking + 10 Warn + 500 (stage 2 failed) + v.Cost
   |-- FrameOutput { Preview Show(plan) every frame | ApplyNow | None, Status (Narrator), Camera, Ghost, Capture }
 StudioToolSystem: applyMode = Clear; ApplyNow -> applyMode = Apply, DestroyDefinitions, return;
                   else DestroyDefinitions; if StillValid(plan) DefinitionWriter.Emit(plan)
 RedReader (Temp + Error near the plan's footprint) -> RedReport -> next FrameInput   (the game is the final judge)
```

### 7.1 Snapshot and versioning

- **Change detection, cheap and every frame while the tool is active.**
  - `CalculateEntityCount` of the Temp/Deleted-excluded road-edge, track-edge and node queries.
  - Any `Edge + Updated` that is not Temp this frame.
  - The adapter's own apply counter.
  - A safety refresh every 120 frames.
  - `GetCombinedComponentOrderVersion` is not used on its own (the preview's Temp entities change it every frame).
- **Read.** On a trigger, `NetworkReader` copies the edge, curve, prefab, upgrade, elevation and aggregate arrays, then converts them to `EdgeInfo` / `NodeInfo` in slices (about 4 ms per frame). The old snapshot stays current while this runs. The first read on a big map shows "Getting to know your roads... 40 %".
- **Build.**
  - `ISnapshotBuilder.Build(data, previous)` hashes each edge's content (id, nodes, rounded curve, prefab, upgrades, elevation) and compares it with the previous snapshot.
  - If nothing changed it returns `previous`, so the Version is unchanged and every cache stays warm.
  - Otherwise Version + 1, and only the cells whose content changed get the new stamp. `RegionVersion(box)` is the highest stamp over the box, so edits elsewhere in the city do not evict cached plans.
- **Legs and names.** Legs come from edge endpoints only, so the ConnectedEdge pass-through bug cannot happen. Names for descriptions come from `AggregateNames`, read once per aggregate.

### 7.2 Hover dispatch (`SiteFinder`, priority order, ported from OTS 283-331)

1. FreeRamp: before click 1, a hint. After click 1, `RampEndsSite(Rematch(anchor), FromHit(hover))`.
2. Preset styles: `Cross4Site` (Cloverleaf, Cloverstack, Stack, Turbine, Parclo), or `StemSite` (Trumpet, Directional T).
3. HighwayEnd style: `HighwayEndSite`; otherwise the hint "Hover where a highway ends at a street".
4. FixDirection style: `ReversedRunSite` when the hovered highway edge belongs to a reversed run.
5. Rail level crossing vs highway crossing: the nearer one wins. A rail crossing always routes to the internal `RailOverpass` style, in every mode.
6. An at-grade highway crossing that is not a ramp terminal: `AtGradeCrossingSite`.
7. A grade separation within 250 m: `SeparatedSite`, carriageways paired on the same street.
8. Otherwise a hint, which suggests Highway end mode when the cursor is at a highway end.

Two cross-cutting rules:
- **Hysteresis.** While the cursor stays inside `sticky.Radius`, the sticky site is kept unless another site is at least 25 % nearer (`EngineRules.SiteHysteresis`). This ends the old diamond preview flipping between carriageways.
- **Badge.** In every mode, if the hovered one-way highway edge is in a reversed run, `SiteLookup.ReversedRun` is set. The status shows the badge "This stretch runs against its carriageway" and the suggestion "Turn it round", which switches to FixDirection.

### 7.3 Routing a site and a style to a plan

| Site | Style chosen | What is planned |
|---|---|---|
| RailCrossing | any | `RailOverpass`: bridge only; the status says so |
| AtGradeCrossing | Overpass | one lift |
| AtGradeCrossing | Diamond, SPUI, Dumbbell, Frontage, Parclo, Best fit | `LiftThen(style)`: stage 1 = the lift with that style's deck margin plus closures; `FollowUp(style)`; stage 2 predicted |
| Separated | Overpass | Final: "already has a bridge here" + suggestions Diamond / Best fit |
| Separated | ramped styles | the style itself (a hazard inside it may stage, see 7.5) |
| Cross4 at grade | presets | `LiftThen(preset)` (closes the old gap where presets never lifted) |
| Cross4 / Stem | presets | the preset |
| HighwayEnd | HighwayEnd | the end recipe (no autofit, as before) |
| ReversedRun | FixDirection | flip every edge of the run |

### 7.4 Plan builder guarantees (U14)

Styles describe; the builder enforces.

1. **Exact joins.**
   - A free end takes its position from its `JoinPoint`.
   - `Add` snaps a curve end onto the point and shifts the neighbouring handle by the same delta (tangent kept), but only when the end is within 0.5 m. Beyond that it is a `PlannerBugException`, which surfaces as Fatal V01.
   - A split end is set to exactly `Position(edge.Curve, t)`; a node end to exactly the node position.
2. **Continuation flags.** In `Finish`, a point with exactly two refs (one ending, one starting), the same prefab and heading dot >= 0.995 gets `ContinuesAt*`. Emit then clears IsFirst / IsLast. Every other point keeps the flags, and the engine forms a node from identical positions.
3. **Splits.**
   - `OnEdge` / `OnChain` are the only ways to make a split. Both convert metres to arc fraction to edge-space t through the arc table and `Splits.Decide`.
   - A split registry maps every split within 1 m on the same edge to one canonical t, so two ramps meeting a street form one junction (the parclo lesson).
   - When the chosen split is a known hazard, the builder searches +/-`AttachWindow` (40 m) for another safe split, then a safe node.
4. **Elevation.** Planners pass xz and an elevation. The builder sets end y = terrain + E, and the handles linear (or Hermite when `Rules.Handles == Hermite`). `Relay` with `elevationAt == null` keeps the original curve exactly.
5. **Direction.** `Relay` inverts the curve and swaps the ends, splits and E0/E1 whenever the chain runs against the source edge (`Forward == false`), so every course runs Start -> End of its source edge. New one-way paths are always produced A -> B in travel order.
6. **Identity.** Relays keep prefab and upgrades. Only `Flip` inverts against the source and mirrors upgrades.
7. **Names.** `CarryName` accepts only relaid or deleted non-ramp sources. Ramps are never named, because ramps aggregate with the mainline.
8. **Groups.** `Begin(group, policy)` checkpoints everything. Dispose without Commit rolls back. Atomic groups are all-or-nothing, Required failures fail the plan, Optional failures are reported.
9. **Finish order.**
   1. Batch safety.
   2. `IPathWriter.PlaceBreaks` over all pending paths (pillar passes until stable).
   3. Piece fitting.
   4. Join flags.
   5. Footprint polylines.
   6. Metrics.
   7. Fingerprint (Fnv64).
   8. Freeze.

### 7.5 Batch safety (no reference to an edge whose node changes in the same batch)

1. **Unstable nodes** are the endpoints of every deleted edge.
2. **Hazards:**
   - a split on a deleted edge;
   - a split on an edge with an unstable endpoint;
   - a node reference to a node that loses all its legs and gains no new piece.
3. **Resolution, in order:**
   - (a) **Window search** (already tried in `OnChain`).
   - (b) **Promotion**, for non-highway prefabs. Replace `Split(E, t)` with `Delete(E)` + `Relay(E, 0..t)` + `Relay(E, t..L)` meeting at a free point, and attach there. Same geometry, names carried. This is the proven SplitPath pattern.
   - (c) **Staging**, for highway mainlines, which the author does not want rebuilt. Everything in the transaction groups that hold a hazard is dropped from stage 1 and replaced by `FollowUp(style)`. Stage 2 is planned fresh on the real network after apply.
4. **Check.** Validator V05 re-checks the result. Any hazard left is Fatal. EngineSim's `Dangling` list is the independent cross-check.

Example. A diamond whose ramp zone needs a local street closed: closing the street at a crossing node makes the two highway edges there merge, so the diverge split on them is a hazard. The plan stages: stage 1 = closures, stage 2 = ramps. This removes the catalogue's "plausibly remains inside ServicePreview" hazard.

### 7.6 Speculative stage 2 and what the player is offered

- **When the stage-1 plan has a FollowUp,** autofit simulates it: `Sim.Apply(net, stage1).After`, then `Sites.Relocate`, then the follow-up style is planned there.
  - If that stage 2 is core-clean, the preview offers the whole thing: "Builds the bridge, then 4 diamond ramps: one click". An optional ghost outline shows the ramps (if spike S5 confirms the overlay API).
  - If it is not, autofit first tries variants that touch `DeckMargin`, `Grade` and `Compact`.
  - If none works, the result is stage 1 alone with `FollowUp = null`. The status reads: "A diamond won't fit here (only 60 m before a side street). Click to build just the bridge." The suggestion is "Compact size".
- **After the click,** the predicted plan is thrown away. The session waits for the network version to change plus 2 quiet frames, relocates the site from scratch and replans stage 2 with the stage-1 variant and `FollowUp.Locked` knobs. It auto-applies once the verdict is Clean and `GetAllowApply()` is true.

---

## 8. Geometry and aesthetics

### 8.1 Horizontal

- **Routing (free ramps and presets).**
  1. Candidates: start option x end option x radius (r, 1.6 r, 2.5 r unless exact) x every Dubins word, chained through Via waypoints.
  2. Cheap checks first: length <= 3000 m, `LargestTurnDeg` (fixed: the run resets after >= 20 m with |k| < 1/2000), MaxTurn, loop preference, self-crossing.
  3. Score = L x (1 + 0.6 x left ends) - 0.4 x (r - wanted r), plus loop penalties.
  4. The best candidates get the full check (crossings, profile at Grade then MaxGrade, side-on overlap), up to `RouteFullChecks` (24) or the time budget. The best failure reason is reported, not the last.
- **G2 smoothing.** Each arc of a Dubins path becomes spiral (Ls) - arc (R) - spiral (Ls), with Ls = clamp(0.35 R, 20, 90) capped at theta R / 2. An S-curve becomes spiral-spiral.
  - The end curvatures are seeded with the attached roads' curvature (`RampEnd.Curvature`), so a ramp leaving a curved highway is curvature-continuous at the gore.
  - A Newton correction restores the arrival pose (0.25 m, 0.25 deg).
  - On failure the router uses the Laplacian smoother with the radius pre-inflated 1.15x (it tightens curves 8-15 %), and flags the result.
  - V24 checks the built radius.
- **Tapers.** Quintic lateral profile w(u) = offset x (10u^3 - 15u^4 + 6u^5), so curvature is zero at both ends. Length >= max(60, 3 x |offset|) (the parclo off-ramp was 1.32, which caused the author's "wonky curves"). The diverge course starts exactly at the split point on the centreline; the merge course ends there.
- **Service ramps follow the highway.** The run from taper end to approach is `ICurveKit.Offset(chain, s0, s1, lateral)`, a path parallel to the carriageway, not a straight line. This fixes clipping on curved highways (a sagitta of about 10 m on a 200 m chord at R 500).
- **Rings and U-turns.** Exact cubic arcs (k = 4/3 tan(theta/4) R), pieces <= 135 deg, y lerped at 1/3 and 2/3. Ring legs are projected onto the circle. Circulation follows `TrafficSide.RingSign`. U-turns are a single-cubic semicircle (k = 4/3 r).

### 8.2 Vertical

- **One profile type for lifts and ramps.** Level zones are joined by eased climbs (parabolic ends of 15 %, linear middle).
  - The peak slope equals the configured grade, so an eased climb of rise h needs `Steep x h / grade` metres, with Steep = 1/0.85. This is the proven router rule.
  - The old lift used a smoothstep whose peak was 1.5x the setting (5 % became 7.5 %). The rebuild is honest, so bridges need about 18 % more room than the old tool claimed. See open question Q1.
- **Profile solver.** A DP over candidate levels {0, C, 2C, 3C} plus {road + C} per crossing, minimising total level change plus 0.01 x level. Over: v - roadElev >= C - 0.5. Under: roadElev - v >= C - 0.5 and v >= 0 (no tunnels). Overlapping same-level flat zones are merged before fitting (fixes the verified 11.8 %-at-6 % step). Inputs are never mutated.
- **Clearance** is measured to the crossed road's surface (`ProfileCrossing.RoadElev` is relative to the path's own terrain), not to the ground under the deck.
- **Pieces.** End y is exact (terrain + profile). The handles are linear by default, and a break point is added wherever the linear chord leaves the profile by more than 0.25 m. Hermite handles are a switch (`Rules.Handles`) to flip after spike S1.

### 8.3 Break points and pillars (U15)

- **Break points.**
  - Included: 0, L, `Fixed`, `Preferred` (primitive joints, seg boundaries) and profile breaks.
  - None inside a `NoNodeSpan`: one span per crossing, capped at the prefab's `MaxElevatedLength` / `MaxEdgeLength`.
  - Gaps <= min(MaxPiece 80, prefab max, 1.3 R on arcs); new pieces >= MinPiece 6.
  - Ground-level relays reuse an old node only within 0.05 m of a touched seg boundary at elevation <= 0.5.
- **Pillar placer.** Every raised node (E >= 3 m) must be at least `half below + KeepOff` from every road, rail, learned disc and every other pending path, later ramps included. Nudges are +/-6, 12, 18, 26 m, outside no-node spans and at least MinPiece from neighbours. Passes repeat until stable (at most 5). What remains is reported as V22 (Blocking), so autofit or a fallback takes over.
- **KeepOff values (catalogue):**
  - street over highway: hwHalf + 8;
  - highway over street: streetHalf + 12, or streetHalf + 30 with Frontage U-turns;
  - road over rail: max(railHalf + 6, 12);
  - ramps: half below + 3.

---

## 9. Style recipes

Every recipe is a class implementing `IStyle`. Recipes compute numbers in plain C# and write only through `IPlanBuilder` and the kits. "Fixable" lists the knobs the main failures name, which is what autofit filters on.

### 9.1 Overpass (`OverpassStyle`, site AtGradeCrossing)

1. `Lift == StreetOver`: `LiftKit.Plan(StreetOverHighway, Cross = node, Partner = site.Partner, ObstacleHalf = hwHalf, Margin = DeckMargin(cfg) [12], KeepOff = hwHalf + 8)`. The street walk absorbs the other carriageway into one bridge.
   - Walks stop at side streets, road ends and ramp terminals, with a reason. They never sever a T, and never bridge over a diamond terminal.
   - Failure is Retry(Grade | Clearance | Lift), worded exactly as before: "only 18 m to come down on one side before a side street 76 m out; a ramp needs 99 m", plus the suggestion "Highway over street".
2. `Lift == HighwayOver`: one lift per carriageway (`HighwayOverStreet`, ObstacleHalf = max(6, streetHalf), Margin = streetHalf + 14, KeepOff = streetHalf + 12).
   - With `BothCarriageways`, the partner crossing comes from the site (up to 4 street pieces or 150 m).
   - If the two lifts overlap, they are re-planned as one request with `Partner`. Nothing is dropped silently; a second-carriageway failure becomes a Warning.
3. `Write`, facts (bridge length, clearance, steepest grade), warnings. "Exits belong at arterials" is a suggestion when the street is >= 16 m.

At a Separated site: Final "already has a bridge here", with suggestions Diamond and Best fit. Fixable: Grade, Clearance, Lift.

### 9.2 Road over rail (`RailOverpassStyle`, site RailCrossing, every mode)

- `site.Refusal` gives a Final failure: "the road ends at the tracks", or "a junction sits right on the tracks; move it off them first".
- The road must run straight through: 2 highway edges and 0 others, or 2 street edges and 0 highway.
- `LiftKit.Plan(RoadOverRail, ObstacleHalf = max(3, railHalf), Margin = railHalf + 10, KeepOff = max(railHalf + 6, 12))`. Highways get both carriageways via the partner found along the tracks (up to 6 pieces or 150 m).
- The rail is never deleted or split (V09, and `IPlanBuilder.Delete` throws). The status says "bridge only".

### 9.3 LiftThen (stage 1 for ramped styles at an at-grade crossing)

- Plans the lift with `style.DeckMargin(cfg) + cfg.DeckMarginExtra`:
  - Overpass 12;
  - Diamond / SPUI 26 compact or 40;
  - others 48 or 62.
- Frontage forces HighwayOver; others use `cfg.Lift`.
- Adds closures that the style will need and that do not create hazards.
- Sets `FollowUp { Style, Anchor = node position, Expect = Separated, Signature, Config = cfg, Locked = Lift | Clearance | DeckMargin }`.
- Status: "Step 1 of 2: bridge (420 m). The ramps follow automatically."

### 9.4 Service skeleton (`ServiceStyleBase`: Diamond, SPUI, Dumbbell; site Separated)

1. `Service.ExistingInterchange` gives Final "There is already an interchange here; bulldoze its ramps first." It walks the straightest continuation 220 m and flags only highway prefabs meeting this street.
2. `cws = Service.Carriageways(site)` (1 or 2).
   - `ChainThrough` follows the traffic 1500 m each way, with a mainline tie-break.
   - Start and End are the first points either side where the highway is within 0.6 m of the ground, or Cross itself on a viaduct.
   - Ramp lanes are 2 at major arterials (>= 24 m).
3. Per carriageway, in an **Atomic** group:
   1. `lateral = RampOffset(cw, style)` = hwHalf + rampHalf + (compact 3 / gentle 12), plus 6 for a dumbbell.
   2. `ends = PlaceEnds(cw, approach)`. Climb = rise / max(grade, 0.03) x Steep, with viaduct descent from the height at Cross +/- 250.
      - Compact: reach = approach + 70 + max(30, climb) + 10, and the ramp may leave on the rising section.
      - Gentle: reach = max(340, approach + 140 + climb + 10), Diverge = min(Start - 120, Cross - reach).
      - Failure if Diverge < 5 or Merge > Total - 5: Retry(Compact | Grade).
   3. `RampZoneClear`:
      - a local street (< 16 m) at an at-grade crossing in the zones goes into the close set when `CloseLocalStreets` is on;
      - an arterial gives Retry(Compact) "an arterial crosses the highway where the ramp has to be";
      - otherwise Retry(Compact) plus the suggestion "Close streets in the way".
   4. The terminals strategy (below).
   5. `WriteRamps(off, on)`: quintic taper from the split at Diverge, chain-offset run, approach. The profile goes from the highway's own height at the diverge (ElevOff) to the terminal elevation, flat for the last approach.
4. `Surgery.CloseStreets(close, cut = hwHalf + rampWidth + 14)`. Stubs keep their upgrades and elevation, and the count is streets (not nodes). Batch safety stages the ramps when a closure would make a diverge split dangle.
5. Facts: ramp count, closures, the "the highway is not rebuilt" note. Metric `DiamondGap`.

Terminal strategies:
- **Diamond:** `Service.Junction(cw, lateral)` on the outer side. Metre steps, `Splits` with node fallback, hopping to the straightest continuation up to 4 times. The off-ramp and on-ramp share one split. W30 fires when the junctions are less than 160 m apart, with suggestions SPUI / Dumbbell.
- **SPUI:** one `Service.Centre(site, cws)` (midway between the carriageway crossings, split or node), shared by all four ramps. `TerminalStyle.CurvedIn`; approach = streetHalf + 18. Pillar clearance for ramps under a highway-over deck is checked by V22.
- **Dumbbell:** one `RingKit.Build` per side.
  - R = max(20, streetHalf + rampLanes x 3.5 + 8).
  - The centre's lateral offset is >= hwHalf + 12 + R, so the ring and its elevated nodes clear the carriageway (fixes the old pillar-over-the-highway bug).
  - Legs: two `StreetCut`, an upstream `RampIn` and a downstream `RampOut`. The leg gap is >= 10 m.
  - A side street inside the ring is Final. The ring prefab is `Prefabs.Ring(7.5)`.
  - Approach = streetHalf + 18 + R + 6.

Fixable for the family: Compact, Grade, Clearance (and DeckMargin when staged).

### 9.5 Frontage (`FrontageStyle`, site Separated with the highway over; at grade via LiftThen(HighwayOver))

1. Guards:
   - `RampPrefab(cw.RampLanes)` is null: Final (capability);
   - `ExistingInterchange`: Final;
   - the highway is not over the street: Final, with the suggestion "switch At ground level to Highway over".
2. Per carriageway, Atomic:
   - landAt = Cross - (streetHalf + LandGap 40/60); takeAt = Cross + (...);
   - Diverge = min(landAt - Slip 150/240, Start - (compact 10 : 30)), and Merge mirrors it. Refuse if within 5 m of the chain ends: Retry(Compact).
   - `Frontage.Find(cw, landAt)` and `Find(cw, takeAt)`:
     - the nearest live non-highway road not in the chain, on the outer side at lateral >= hwHalf + 6;
     - parallel (|dot| >= 0.95), within 160 m laterally;
     - split through `Splits`;
     - a one-way frontage must run with the carriageway (`DirectionOk`).
   - `RampZoneClear`, then `WriteSlip` (off: highway to frontage before the street; on: frontage to highway after). The elevation follows the chain profile; it is no longer hard-coded 0, so slips work from viaducts.
3. Texas U-turns (with `UTurns` and both carriageways): `UTurns.Try` searches outward in 8 m steps for up to 160 m.
   - Rejected when R < 8 or R > 90, the apex is within streetHalf + half + 3 of the street, the deck clearance is < 5.5 m, or the lane comes within half + 4 of a pillar.
   - On success the landings move to SA - 35 and SB + 35.
   - The highway-over bridge keeps pillars streetHalf + 30 from the street (LiftThen passes `KeepOffUTurn`).
   - A missing U-turn is explained in the status.
4. `CloseStreets`. Facts: slips, U-turns, closures.

### 9.6 Best fit (`BestFitStyle`, policy as data)

| Rule | Tries | Reason text |
|---|---|---|
| Street < 16 m (local) | none: **Final** "local streets get a bridge only; exits belong at arterials" (+ suggestion Overpass) | - |
| Highway over the street and frontage roads found | Frontage (its failures stay quiet) | "frontage roads already run alongside" |
| Street >= 24 m (major arterial) | SPUI, then Dumbbell | "it is a major arterial, so a single signal keeps traffic moving" |
| 16-24 m (arterial) | Dumbbell, then SPUI | "it is an arterial, so roundabouts avoid a second stop" |
| always last | Diamond, accepted only if `Metrics.DiamondGap` is 0 or >= 160 m | "nothing with a single stop fits" |

- The winner is the first style whose plan has **no Blocking** violation and whose speculative stage 2 (if any) fits, not merely the first with pieces.
- If every try failed Final, Best fit is Final (fixes the lost NoFit).
- Status: "Best fit: single-point, because Elm Ave is a major arterial (24 m wide). Tried first: frontage (no frontage roads)." Every skipped style goes into `Tried`.

### 9.7 Highway end (`HighwayEndStyle`, site HighwayEnd, autofit off)

- **Avenue (EndStyle 0).**
  1. `StreetBetween` the two carriageway end nodes (up to 4 steps, under 120 m, no side street).
  2. `Surgery.SplitPath` at the midpoint M (sliver-guarded: within 30 m of a node it uses the node).
  3. T = ground(mid + axis x avLen), with avLen 60 compact / 100.
  4. `Surgery.Trim` each carriageway back by avLen + converge (100 / 160). This fails if a junction, street or rail node is in the way: "the highway has a junction only N m from its end".
  5. Converge lanes: pIn -> T (ending with tangent -axis) and T -> pOut, as G2 paths (not a single FitCurve), keeping the highway prefab and upgrades.
  6. An avenue from T to M with `Prefabs.Avenue(crossStreet, 16)`.
  7. T and M become nodes from identical positions.
  - Names: highway at pIn, and the street on **both** halves.
  - Single two-way highway: the last `back` metres become one avenue piece to the existing end node, inverted when needed to keep the edge orientation.
- **Roundabout (EndStyle 1).**
  - R = max(40, pathLen/2 + hwWidth/4 + 15, streetW + 15), ring prefab `Prefabs.Ring(11)`. Refused if either end node has more than 2 street edges.
  - Street legs are cut where the street chain meets the **circle** (not at arc length R). A divided highway joins at +/-0.5 rad either side of the axis (incoming radial-inward, outgoing radial-outward); a two-way highway at 0 rad.
  - Legs at least 10 m apart.
  - Status: "merges into <avenue> 100 m before the street" / "a 90 m roundabout with no signals".

### 9.8 Free ramp (`FreeRampStyle`, site RampEnds, two clicks)

- Click 1 stores `RampAnchor` (position + road signature) and rematches it every hover. Right-click with an anchor resets to click 1; a second right-click leaves the tool.
- End kinds:
  - **Taper** on highways: the cursor side picks the direction on two-way roads; right side preferred, left penalised 0.6 x length.
  - **Junction** on streets: a straight stub at 0 or +/-35 deg, either side, length half/cos + 12.
  - **Node** at forks and trims.
- Main job plus symmetry copies: `Symmetry.Copies` rotates by pi (or pi/2, pi, 3pi/2 when the roads cross roughly square, |dot| < 0.4) about the axis centre, never mirrored, and refits with `Match` re-deriving the end kind.
- Each job is an Optional group. Status: "Ramp from X to Y: 412 m, a 270 deg loop, up to 18 m high, over A and B, under C (steeper than your 5 % gradient, to fit)."
- "Both ends are on the same piece of road" is Final.

### 9.9 Four-way presets (`FourWayFamily`: Cloverleaf, Cloverstack, Stack, Turbine; site Cross4)

- **Movements.** `Presets.Movements(site)`: 8 movements; a far-side (left) turn when `IsFarSideTurn(P.Dir, Q.Dir)`.
- **Radii:**
  - RL = max(R, 45) for loops;
  - Rd = max(1.6 R, 90) for directs;
  - Rf = max(4 R, 300) for stack flyovers, or max(1.8 R, 110) for the turbine;
  - R = `cfg.EffectiveRadius`, so autofit's radius variants now really widen preset arcs, subject to room.

| Style | Far-side turns | Near-side turns | ShareForks |
|---|---|---|---|
| Cloverleaf | 270 deg loops (WantLoop, MaxTurn 320) | directs; pushed out 2 RL + 35 around a loop in the same quadrant, taper 120 + 1.6 x extra | no |
| Cloverstack | loops for turns leaving X, flyovers for turns leaving Y | directs | Y side |
| Stack | flyovers (left arcs, Rf) | directs | yes |
| Turbine | flyovers at max(1.8 R, 110) (parity first); a true spiral with Via poses is a later flag | directs | yes |

- **Arc jobs.** Each arc is `Presets.ArcJob`: Tangency (closed form, verified: R60 loop U = +90 / V = -90; direct right R96 U = -126 / V = +126; flyover R300 U = -270 / V = +270), with A at U - taperA and B at V + taperB, so the taper lands exactly on the tangent point. Exact radius (the 0.92 slack is gone, because the clothoid smoother keeps R).
- **Job order:** loops, trunks, directs, flyovers (LevelPriority). `MultiRamp.Plan` levels them jointly.
- **ShareForks.** Each carriageway's two exits get one diverge trunk (Ramp2 when it carries two movements) to fork F = P + p x fa + outer x Off, where fa = min(UA) - 30. F's elevation is a level variable. The trunk and its branches form one Atomic group whose Fallback routes the branches directly.
- Status: "Cloverleaf: 7 of 8 ramps, 4 loops. Not fitted: the north-east direct (would cross Main St at ground level)." Buildable when at least one group fits (`AllowPartial`).
- `ExistingInterchange` guard applies. An at-grade crossing goes through LiftThen.

### 9.10 Partial cloverleaf A4 (`ParcloStyle`, site Cross4: highway x two-way street; at grade via LiftThen)

Per highway carriageway, one Atomic group:
- **Street junction J:** at lateral latJ = offP + 2 RL + 25 (`Match` Junction within 25 m).
- **Fork F:** (sh + 45) upstream of J.
- **Two-way stub** J -> F (`Prefabs.TwoWayRamp`, E0 = J elevation, F's elevation solved).
- **Loop** F -> taper at aF + 30 (TaperB 60, MaxTurn 270).
- **Off-ramp:** taper at aF - 260 -> F, with taper length >= 3 x (latJ + 25). This fixes the S-bend.
- **On-ramp:** J -> taper at sh + 170 after the bridge (TaperB 110).

The stub exists only if its loop and off-ramp exist. The parclo tile gets crossing settings (Both carriageways, Close streets, At ground level) because it is a crossing recipe now.

### 9.11 Trumpet and Directional T (`StemFamily`, site Stem)

- Works in the stem frame. Rejects yR > yL ("carriageways the other way round from right-hand traffic"). Accepts a dead-end pair, an at-grade T end, and a two-way stem.
- **Trim-back:**
  - wantY = (yR - offR) - max(max(R, 60) + 15, `Profiles.RunFor(Clearance, cfg.Grade)` + 30). This uses the **player's grade**, not MaxGrade.
  - If short: `Surgery.Trim` each carriageway, add the cut edges to the ignore set, and give the ramps exact `NodeAt` cut points.
  - Everything sits in one Atomic group, so a failed ramp never leaves the highway trimmed.
- **Trumpet:**
  - right turns R1 / R4 = min(room, max(1.6 R, 110));
  - loop QL -> stem Out (taper 50, WantLoop, MaxTurn 320);
  - a bell flyover from stem In to QL, concentric at R2 = RL + 2 x rampHalf + 16 via two Via poses, tapering 170 m into QL.
- **Directional T:** both left turns become left arcs, Rd = min(max(2.2 R, 140), Rmax), and fail if Rd < 60. They cross each other; the level solver gives them separate levels.
- Status: "Trumpet: 4 of 4 ramps, with a loop and a flyover wrapped round it. The highway is trimmed back 38 m to make room."

### 9.12 Fix direction (`FixDirectionStyle`, site ReversedRun, autofit off)

A run counts as reversed when each end conflicts topologically with the best geometric continuation (one-way highway, horizontal dot > 0.85) and the run is under 3 km. Each edge is deleted and re-laid with an inverted curve, Start = old End, E0/E1 from the node elevations, the same prefab, and mirrored upgrades. Status: "This stretch runs against the rest of its carriageway. Click to turn it round."

---

## 10. Autofit

**Variant table** (`VariantTable`, ported from OTS 412-427 plus two deck rows). Row 0 is the player's own settings. Cost = 4 per m of clearance lowered + 8 for a flip + 2 per % of grade raised + 1.5 for a length change + 3 x |ln RadiusMul| + 1 per alternative route + 0.1 per m of deck margin. Rows are tried in cost order (ties by index).

| Row | RadiusMul | Alt | MinGrade | MaxClearance | Length | Flip | Deck + | Cost |
|---|---|---|---|---|---|---|---|---|
| 0 | 1 | 0 | - | - | - | - | - | 0 |
| 1 | 1 | 1 | - | - | - | - | - | 1 |
| 2 | 1 | 0 | 6.5 % | - | - | - | - | 3 |
| 3 | 1.3 | 0 | - | - | - | - | - | 0.8 |
| 4 | 1 | 0 | 7.5 % | - | compact | - | - | 5 |
| 5 | 0.8 | 0 | 7.5 % | - | - | - | - | 5.7 |
| 6 | 1 | 0 | - | - | - | yes | - | 8 |
| 7 | 1.6 | 0 | 6.5 % | - | gentle | - | - | 5.9 |
| 8 | 1 | 0 | 8.5 % | 7.5 m | - | - | - | 13 |
| 9 | 0.7 | 1 | 8.5 % | 7.5 m | compact | - | - | 15.1 |
| 10 | 2.2 | 0 | 6 % | - | - | - | - | 4.4 |
| 11 | 1 | 2 | 9 % | 7 m | - | yes | - | 26 |
| 12 | 1 | 0 | - | - | - | - | 10 | 1 |
| 13 | 1 | 0 | 6.5 % | - | - | - | 20 | 5 |

(Costs shown assume the default 5 % grade, 9 m clearance and compact ramps; a length change costs only when it differs from the player's. Cost is recomputed from the player's actual settings, because `Apply` never lowers grade or raises clearance below or above the player's values.)

**Search** (`AutofitSearch`, one variant per `Step`):

1. Row 0 first. If it is core-clean and the game agrees, nothing else is tried and the status carries no autofit prefix.
2. **Skip pointless variants.** A row is skipped unless `Touches & style.SensitiveTo & lastFailure.Fixable & ~locked` is non-zero. A Final failure stops the search at once.
3. **Dedupe by result.** A variant whose plan fingerprint matches one already tried is skipped. This removes the flip rows on SPUI and presets, and radius rows that do not change exact arcs.
4. **Score** = 1e6 x Fatal + 1000 x Blocking + 10 x Warn + 500 if the speculative stage 2 failed + cost. The proposal is the lowest-score candidate the game has not refuted. A Fatal candidate is never a proposal.
5. **Game feedback.** The session emits the proposal. Once the verdict settles (age >= 3, Temp stable 2 frames):
   - red near the footprint calls `Refute(red)`: the candidate is marked Red, red positions become `LearnedDisc`s (pillar 8 m, edge 12 m), and the next candidate (or a re-plan of the same variant with the learned discs) becomes the proposal;
   - at most `MaxGameTrials` (6) game trials per site.
6. **Exhausted.** Show `LeastRed` (fewest red items, existing roads weighted 2, then score), not the last one tried. Status: "Tried 7 layouts; none is completely clear. Showing the closest: 1 red piece, a pillar of the new ramp 30 m north-east of the cursor." The click stays refused unless `GetAllowApply()` passes (Anarchy).
7. **Text.** `Narrator.Changes(user, chosen, style.SensitiveTo)` lists only knobs the style reads ("Autofit changed gradient to 6.5 % and ramps to compact"). They show as chips with a "Use my settings" link, which re-plans this site with row 0 only.
8. **Cache.** Search state is cached by `(SiteKey, style, user.StableHash, RegionVersion)`, so mouse jitter within a site never restarts it. Stage 2 starts from the stage-1 variant with `FollowUp.Locked` knobs fixed.
9. **Progress.** "Checking layout 2 of 4" (viable candidates, not 12) shows only when a search spans more than 3 frames.
10. **Off.** With autofit off, only row 0. Failures show their Suggestions as one-click buttons instead.

---

## 11. Tool session (pure state machine, `ToolSession`)

| From | Event | Guard | To / outputs |
|---|---|---|---|
| any | Cancel | FreeRamp anchor set | clear the anchor; "Pick where the ramp leaves" |
| any | Cancel | otherwise | `ExitTool` (right-click finishes). A follow-up in flight is abandoned: "Bridge built; ramps skipped." |
| Idle / Previewing | Frame | site or settings changed (canonical key) | Planning: cached result or a new job; the old preview is kept for up to 15 frames |
| Planning | job yields a result | Plan non-null | Previewing(age 0): `Show(plan)` every frame; status Ready or Working |
| Planning | job yields a result | failure | Idle: hint or Problem with suggestions |
| Previewing | Frame | age >= 3 and Temp count stable 2 frames | verdict Clean or Red. On Red: `job.GameRejected(red)`, then Planning (next candidate) or least-red shown |
| Previewing | Click | verdict not settled yet | the click is queued for up to 6 frames, then resolved as below |
| Previewing | Click | `AllowApply` (verdict Clean, or Anarchy on) | Applying: `ApplyNow(names = plan.Names)` |
| Previewing | Click | not `AllowApply` | Problem: RedExplainer text, or "Something elsewhere in the city is red, so the game won't build" when the red is only away from the preview. No cache reset |
| Applying | next frame | - | Settling(versionAtApply) |
| Settling | Frame | Net.Version changed and 2 quiet frames | no FollowUp: Pinned(Built). FollowUp: FollowUpPlanning |
| Settling | Frame | 120 frames without a change | Problem: "The game didn't build it." |
| FollowUpPlanning | - | `Sites.Relocate` fails | Problem: "Bridge built. Hover the new bridge to add ramps." (falls back to normal hover) |
| FollowUpPlanning | result | Plan | FollowUpPreviewing (age 0); stage chips "Bridge: done, Ramps: checking" |
| FollowUpPreviewing | Frame | verdict Clean and `AllowApply` | Applying (auto) |
| FollowUpPreviewing | Frame | exhausted | Previewing, with "Bridge built. The ramps need attention: ..."; the player can change settings and click |
| Pinned | Frame | cursor left the site radius and >= 1.5 s, or 4 s passed | Idle |
| any | FindNext | - | `Fix.Scan` (cached per version), nearest unvisited from the camera pivot, `CameraMove(pivot, 350, 700)`, counts held 6.5 s |
| any | Capture | - | `CaptureBundle` (snapshot cropped to 1.5 km, terrain 3 km at 8 m, config, request, result, red) |

Invariants (tested): an `Apply` frame never shows a plan (type-level); auto-apply needs a settled verdict; no transition depends on a magic frame count except the documented timeouts.

---

## 12. Game adapter

Outline of the adapter classes (namespace `InterchangeStudio.Game`). These reference game DLLs and are **not** part of Contracts.cs.

```csharp
public sealed class Mod : IMod
{
    // OnLoad:
    //  1. settings = new StudioSettings(this); RegisterInOptionsUI();
    //     AssetDatabase.global.LoadSettings(ModIds.SettingsId, settings, new StudioSettings(this))
    //  2. LegacyImport.Run(settings)        once: reads ModIds.LegacySettingsFile into LegacySettings (never saved)
    //  3. settings.RegisterKeyBindings(); locale sources for every supported locale (English text)
    //  4. updateSystem.UpdateAt<StudioToolSystem>(SystemUpdatePhase.ToolUpdate);
    //     updateSystem.UpdateAt<StudioUISystem>(SystemUpdatePhase.UIUpdate)
    //  5. action = settings.GetAction(ModIds.ToggleAction); action.shouldBeEnabled = true;
    //     action.onInteraction += (_, phase) => { if (phase == Performed && gameMode has Game) tool.Toggle(); }
    // OnDispose: action.shouldBeEnabled = false
}

[FileLocation(ModIds.SettingsFile)]
public sealed class StudioSettings : ModSetting
{
    [SettingsUIKeyboardBinding(BindingKeyboard.H, ModIds.ToggleAction, ctrl: true, shift: true)] public ProxyBinding Toggle { get; set; }
    [SettingsUIHidden] public string PanelState { get; set; }      // IPanelModel.PersistJson: settings + style + PanelPrefs
    [SettingsUIHidden] public string MigratedFrom { get; set; }
    [SettingsUIHidden] public bool AsyncPlanning { get; set; }      // off until spike S4
}
public sealed class LegacySettings : ModSetting { /* the 14 old properties, read only, never saved */ }

public sealed class StudioToolSystem : ToolBaseSystem
{
    public override string toolID => ModIds.ToolId;
    public override PrefabBase GetPrefab() => null;
    public override bool TrySetPrefab(PrefabBase prefab) => false;
    public override void InitializeRaycast();     // TypeMask.Net, Layer.Road | Layer.TrainTrack
    public override Snap GetAvailableSnapMask(...) => Snap.None;   // requireNet = Layer.None, requireUnderground = false set explicitly
    protected override void OnStartRunning();     // applyAction / cancelAction shouldBeEnabled = true; log UndergroundViewSystem flags
    protected override JobHandle OnUpdate(JobHandle deps);
    public void Toggle();                          // activeTool = this <-> DefaultToolSystem
    internal IToolSession Session { get; }
    EntityQuery m_DefinitionQuery, m_RedQuery;     // never m_ErrorQuery (the base already has one)
}
// OnUpdate skeleton:
//   applyMode = ApplyMode.Clear;
//   try {
//     m_Terrain.Refresh(); m_Reader.Tick(budget);                       // change detection + time-sliced read
//     var o = m_Session.Step(BuildInput());                             // raycast -> Hit, actions, Red (RedReader), GetAllowApply(), Temp count
//     if (o.CaptureNamesNow.Count > 0) m_Names.Capture(o.CaptureNamesNow);
//     if (o.Apply) { applyMode = ApplyMode.Apply; m_Reader.MarkApplied(); return DestroyDefinitions(m_DefinitionQuery, m_ToolOutputBarrier, deps); }
//     deps = DestroyDefinitions(m_DefinitionQuery, m_ToolOutputBarrier, deps);
//     if (o.Preview.Kind == PreviewOpKind.Show && DefinitionWriter.StillValid(o.Preview.Plan, EntityManager))
//         DefinitionWriter.Emit(o.Preview.Plan, EntityManager, m_ToolOutputBarrier.CreateCommandBuffer());
//     if (o.Camera.HasValue) CameraJumper.Jump(o.Camera.Value);
//     if (o.Capture != null) m_Captures.Write(o.Capture);
//     if (o.ExitTool) m_ToolSystem.activeTool = m_DefaultTool;
//   } catch (Exception e) { Log.Error("Frame failed", e); m_Session.ReportCrash("frame"); }  // "Something went wrong here; it's in the log"
//   return deps;

public sealed class NetworkReader   { public INetwork Current { get; } public float Progress { get; } public void Tick(IBudget b); public void MarkApplied(); }
public sealed class PrefabReader    { public IPrefabTable Read(EntityManager em, PrefabSystem ps); }   // PrefabData+RoadData+NetGeometryData, TrainTrack nets; internal names
public sealed class GameTerrain : ITerrain { public void Refresh(); public HeightSamples Patch(float2 centre, float half, float cell); }   // GetHeightData(false), SampleHeight
public static class DefinitionWriter
{
    public static bool StillValid(BuildPlan plan, EntityManager em);    // every ReferencedEdges/Nodes entity exists and is not Temp/Deleted
    public static void Emit(BuildPlan plan, EntityManager em, EntityCommandBuffer cb);   // verbatim Emit/DeleteDef recipe (OTS 2602-2643):
    //  course: NetCourse{ m_Curve, m_Length = MathUtils.Length, m_FixedIndex = -1, m_Elevation = (E0, E1) }
    //  CoursePos{ m_Entity = node | edge | Entity.Null, m_SplitPosition = EdgeT, m_Position = curve end, m_Elevation = (E, E),
    //             m_CourseDelta 0 / 1, m_ParentMesh = -1, m_Rotation = NetUtils.GetNodeRotation(tangent),
    //             m_Flags = (ContinuesAt ? 0 : IsFirst / IsLast) | IsRight | IsLeft }
    //  CreationDefinition{ m_Prefab, m_RandomSeed = (int)(Fnv64(curve.a, prefab) & 0x7fffffff) } + Updated + Upgraded (when Upgrades.Present)
    //  delete: CreationDefinition{ m_Original, Delete } + Updated + NetCourse over the edge's own curve between its m_Start / m_End nodes (only if live)
}
public sealed class RedReader       { public RedReport Read(BuildPlan shown, EngineRules rules); }   // Temp+Error; Owner -> edge for pillars; Temp.m_Original = existing; 45 m filter
public sealed class NameKeeper      { public void Capture(IReadOnlyList<NameCarry> carries); public void Tick(INetwork net); }   // UI phase; GetRenderedLabelName / SetCustomName; waits for the new aggregate (frame 12..180)
public static class CameraJumper    { public static void Jump(CameraMove m); }                          // Game.CameraController.TryGet(out cam); pivot; zoom cap
public sealed class CaptureWriter   { public string Write(CaptureBundle b); }                          // ModsData/InterchangeStudio/captures/<time>.json
public static class Log             { public static void Info(string s); public static void Error(string s, Exception e); }   // strip { }, cap 1500, swallow, LogOnce, verbose gate
public sealed class StudioUISystem : UISystemBase { /* bindings (13.1), NameKeeper.Tick, TOOL_ACTIVE = activeTool == tool, PanelState save */ }
```

Notes:
- `EdgeId` / `NodeId` / `PrefabId` mirror `Entity(Index, Version)`, so conversion needs no table.
- `UpgradeBits` maps to `CompositionFlags` (`m_General`, `m_Left`, `m_Right`); spike S6 confirms the field names.
- The traffic side comes from the city's left-hand-traffic setting (spike S10). While LHT is unsupported, an LHT city gets a Final "left-hand traffic isn't supported yet" from every ramped style, unless `LhtViaMirror` is on.
- **Worker planning.** `PlanService(async: true)` runs jobs with Task.Run. Inputs are immutable (snapshot, height patch, config). Results are drained at the start of Step, and logs are queued to the main thread. A job that throws poisons its key for the session. Default is off until spike S4; the synchronous path uses the 6 ms budget.

---

## 13. UI and bindings

### 13.1 Bindings (namespace `InterchangeStudio`)

| Kind | Name | Type | Content |
|---|---|---|---|
| value | TOOL_ACTIVE | bool | `ToolSystem.activeTool == tool` each UI frame |
| value | CATALOG | string | `CatalogView` json: tabs, tiles (copy, icon, settings, enabled + reason from capabilities), setting specs. Sent once; re-sent when capabilities change |
| value | SETTINGS | string | `SettingsView` json: style, size (compact / standard / spacious / custom), values, panel prefs |
| value | STATE | string | `StateView` json: StatusView (kind, headline, detail, facts, autofit chips, warnings, suggestions, tried, stage, badge), fix counts, working, notice, summary. Pushed only on change (ValueBinding comparer) |
| value | HOTKEY | string | display of the current binding; fallback "your shortcut in Options" |
| trigger | TOGGLE_TOOL | - | toggle the tool |
| trigger | FIND_NEXT | - | find the next crossing to fix |
| trigger | CAPTURE | - | save a report of this spot |
| trigger | USE_MY_SETTINGS | - | re-plan this site with row 0 |
| trigger | DISMISS_INTRO | - | first-run coach line seen |
| trigger | SET_STYLE | string | style key (one trigger per tile; replaces SET_PRESET + SET_MODE) |
| trigger | SET | string | "key=value", parsed and clamped by SettingsSchema, then PanelState saved |
| trigger | SET_SIZE | int | 0 compact, 1 standard, 2 spacious; echoes the new values |
| trigger | APPLY_SUGGESTION | string | suggestion id from the current StatusView |
| trigger | PANEL_PREFS | string | PanelPrefs json on drag end, tab change, collapse |

Old to new mapping (for parity):
- The 14 setting values (CLEARANCE, GRADE, BOTH, CLOSE, LIFT_STREET, COMPACT, RAMP_LANES, RAMP_RADIUS, SIZE, AUTOFIT, SYMMETRY, PRESET, END_STYLE, UTURNS) and their SET_* triggers become SETTINGS + SET.
- MODE + PRESET become `style`.
- STATUS + STATUS_KIND become STATE.
- TOGGLE_TOOL and FIND_NEXT keep their names.
- Clamps are unchanged: radius 20-250, clearance 6-20, grade 3-8 %, lanes 1|2, size and symmetry 0-2, end 0|1.

### 13.2 Settings (SettingsSchema)

| Key | Kind | Range / options | Default | Group | Shown for |
|---|---|---|---|---|---|
| size | choice (macro) | Compact / Standard / Spacious (Custom display only) | Standard | main | ramped styles, presets, free ramp |
| autofit | toggle | - | on | main | all but Highway end and Fix direction |
| lift | choice | Street over / Highway over | Street over | main | Overpass, Diamond, SPUI, Dumbbell, Parclo (crossing styles except Frontage and Best fit) |
| both | toggle | - | on | main | crossing styles |
| close | toggle | - | on | main | crossing styles except Overpass |
| uturns | toggle | - | on | main | Frontage, Best fit |
| symmetry | choice | Off / Opposite / All four | Off | main | Free ramp |
| lanes | choice | 1 / 2 | 1 | main | Free ramp, presets |
| endStyle | choice | Avenue / Roundabout | Avenue | main | Highway end (the only setting shown there) |
| radius | stepper | 20-250 step 5 m | 70 | advanced | Free ramp, presets |
| grade | stepper | 3-8 step 0.5 % | 5 | advanced | all with climbs |
| clearance | stepper | 6-20 step 1 m | 9 | advanced | all with climbs |
| rampLength | choice | Compact / Gentle | Compact | advanced | crossing styles except Overpass |
| asyncPlanning, verboseLog | toggle | - | off | testing | hidden unless dev tools are on |

### 13.3 Panel (`UI/InterchangeStudio.mjs`, no build step)

- **Module rules.** Globals `window.React`, `window['cs2/api']`, `window['cs2/ui']`; `h = React.createElement`; no JSX, no imports. `export const hasCSS = true`. `register(r)` appends `GameTopLeft` (floating Button + Tooltip "Interchange Studio", with a fallback button) and `Game` (the panel). All hooks run before the TOOL_ACTIVE early return.
- **Panel contents:**
  1. Title bar: draggable, rem-converted, clamped so at least 120 x 44 rem stays on screen. Position persisted via PANEL_PREFS. The close x stops mousedown propagation.
  2. Tabs: Crossings (Overpass, Diamond, Single-point, Dumbbell, Frontage, Partial clover, Best fit), Interchanges (Cloverleaf, Cloverstack, Stack, Turbine, Trumpet, Directional T), Freehand (Ramp, Highway end), Fix (Find next with counts, Fix direction, Save this spot).
  3. Tiles: rows of 4 built manually, 64 x 64 `is-*.svg` schematics (#d5dde6 streets, #8c97a3 highway, #5fb4ff ramps, #f4a259 accent), selected glow. Disabled tiles show the reason on hover.
  4. About card with More / Less (the author-approved copy from the old GROUPS, kept verbatim in StyleCatalog).
  5. Status card with a coloured left border and tag (Hint grey, Ready blue #5fb4ff, Working slate, Problem amber #f4a259, Built green #6fcf8a). It holds:
     - the headline;
     - up to 3 detail lines;
     - fact chips;
     - autofit chips with "Use my settings";
     - warnings;
     - suggestion buttons;
     - a "Why" expander (Because and Tried);
     - stage chips for two-step builds ("Bridge: done", "Ramps: checking 2 of 4");
     - the reversed-run badge.
  6. Plan summary line ("4 ramps · max 5 % · min radius 62 m · bridge 420 m").
  7. Settings: Size segmented control, autofit switch with a note, style-relevant controls. Advanced is collapsed, with + / U+2212 disclosure, steppers, and Ramp length.
  8. Footer: "Click to build · right-click to finish · <HOTKEY>". The unverified Esc claim is dropped.
  9. First run: one coach line, "Point at a crossing. Click to build. Right-click to close."
  10. One-time notices: old mod installed; keybinding not migrated.
- **Sizing.** `max-height` with `overflow-y: scroll` on the body for low resolutions. Spike S8 checks `vh` support; otherwise rem.

### 13.4 Gameface CSS rules (CssLint)

- **Allowed:** flex with an explicit flex-direction, rgba, longhand borders, a single box-shadow, rem units, `pointer-events: auto` on the panel. The old ClaudeInterchanges.css logged zero UI.log warnings and is the baseline.
- **Forbidden:**
  - grid, table, inline-block, inline-flex, `fr`, `inherit`;
  - `var()` or `hsla()` inside shorthands;
  - more than one box-shadow, a transition shorthand with only a duration, `space-evenly`;
  - `max-width` / `max-height: none`, `pointer-events: all`, dashed borders, font-weight ranges;
  - the selectors `:disabled`, `:not(`, `:focus-within`, `:focus-visible`, `:nth-of-type`, `::placeholder`, `::-webkit-scrollbar`.

---

## 14. Invariants and where each is enforced

C = by construction, V = validator, A = adapter, S = session, T = test.

| # | Invariant (catalogue) | Mechanism | Where | Test |
|---|---|---|---|---|
| I01 | Every frame: applyMode = Clear, DestroyDefinitions, re-emit; the apply frame emits nothing | C (FrameOutput.ApplyNow has no plan) + A skeleton | Session, StudioToolSystem | session tests; in-game checklist |
| I02 | Apply only when GetAllowApply() | S gate (the game is the final judge) | ToolSession | session tests |
| I03 | Trust red or clean only after >= 3 frames | S: age >= RedWindow and Temp count stable 2 frames, also for stage-2 auto-apply | ToolSession | session tests (the old one-frame race) |
| I04 | Never reference an edge whose node changes in the same batch; at-grade ramps are two-step | C: AttachFactory window search, BatchSafety promotion or staging; V05; EngineSim Dangling | PlanBuilder, LiftThen | BatchSafety tests; scenario close-street-in-ramp-zone; property P1 |
| I05 | One-way courses run in traffic direction; relays invert the curve and swap ends, splits, E0/E1 | C: Relay auto-inversion; kit paths A->B; V06; EngineSim FlowConflicts; SVG arrows | PlanBuilder, kits | relay idempotence P6; reversed-run scenario |
| I06 | Exact shared endpoints; IsFirst/IsLast cleared only on 2-way continuations; 3+ meet at identical positions with flags kept | C: JoinPoint; flags in Finish (same prefab, dot >= 0.995); V01, V02 | PlanBuilder, DefinitionWriter | builder unit tests; P1 |
| I07 | NetCourse / CoursePos field recipe | A: one verbatim port | DefinitionWriter | source rule; in-game |
| I08 | Bulldozer delete; whole-edge deletes, remainder re-laid | C: `Delete(EdgeId)` only; LiftKit relays lo..Start and End..hi; A: DeleteDef guarded by Live | PlanBuilder, LiftKit, DefinitionWriter | lift tests |
| I09 | Splits >= 30 m from both ends, else the node | C: only AttachFactory -> Splits.Decide; V03 | AttachFactory | Splits theory; P7 |
| I10 | Split t in the edge's own parameter space; position exact | C: `IChain.EdgeParamAt`; arc fraction -> t; V04 | AttachFactory | reversed-seg tests |
| I11 | Live only (no Temp / Deleted) | A: reader queries exclude both; C: the snapshot holds only live entities; A: StillValid before emit | NetworkReader, DefinitionWriter | source rule; in-game |
| I12 | Revalidate caches after builds | C: every key carries RegionVersion; A: MarkApplied forces a re-read | PlanService, NetworkReader | session test with a version bump |
| I13 | Highway = UseHighwayRules; ramps are highways; terminals are not crossings | C: NodeLegs.Ramp subset; INetworkKit.IsTerminal used by every detector and walker | Model, Network, Sites | finished-diamond scenario: not offered, not counted by FindNext |
| I14 | ConnectedEdge may list pass-through edges | C: legs built from edge endpoints only | SnapshotBuilder | source rule; builder test |
| I15 | Rail is never moved; the road goes over; level crossing = shared node; raycast includes TrainTrack | C: Delete throws for rail; walkers treat rail as under or as a stop; V09; A: raycast mask | PlanBuilder, LiftKit, StudioToolSystem | rail scenarios |
| I16 | Renames only in the UI phase, after aggregation; never rename ramps | C: NameCarry only from non-ramp relays; V10; A: NameKeeper ticked by the UI system | Plan, NameKeeper | V10 tests; source rule |
| I17 | Logger braces and length | A: Log is the only entry; Core returns plain strings | Log | source rule |
| I18 | No base-field shadowing (m_ErrorQuery, m_PrefabSystem...) | A: naming; m_RedQuery | StudioToolSystem | source rule |
| I19 | Camera via CameraController | A | CameraJumper | in-game |
| I20 | Raycast hit can be a node or an edge | C: Hit carries both; detectors handle both | SiteFinder | node-hit tests |
| I21 | Pillars KeepOff from what passes underneath; one span per crossing | C: PathWriter (no-node spans, multi-pass nudging over all paths); V22 | PathWriter, LiftKit | dense-grid scenarios |
| I22 | y = terrain + elevation; CoursePos / NetCourse elevations agree | C: builder derives y from E; V08 | PlanBuilder | sloped-terrain scenarios |
| I23 | Metres along a chain need arc-length tables | C: IArcTable, IChain | Geometry, Network | uneven-parameter Bezier tests |
| I24 | Upgrades preserved; mirrored only when laid against the source (Flip) | C: Relay copies; Flip mirrors; V07 | PlanBuilder | unit |
| I25 | No shared scratch classification lists | C: immutable NodeLegs | Model | reflection test |
| I26 | RHT conventions: exits on the outer side; rings anticlockwise; rotate, never mirror | C: TrafficSide only; SymmetryKit rotates; V06(d) | everywhere | rotation and mirror properties; source rule |
| I27 | Bezier arc handles 4/3 tan(theta/4) R; arcs > 135 deg split | C: ICurveKit.Arc / ArcPieces | CurveKit | radial error < 0.03 % R |
| I28 | Deterministic random seed | A: Fnv64(curve.a, prefab) | DefinitionWriter | - |
| I29 | Settings before the UI system; deploy path; explicit compile items; no backups in the project | A + build | Mod, csproj | build |
| I30 | UI: no build step, safe glyphs, Gameface CSS, rem, pointer-events | lints | UI | UI lint tests |
| I31 | Hotkey via ProxyBinding, Performed only, GameMode.Game, disabled on dispose | A | Mod, StudioSettings | in-game |
| I32 | Immutable config; no statics swapped | C: records + `with`; reflection test; StableHash covers every property | Config | ConfigFingerprintTests |
| I33 | Grade includes the ease factor | C: peak slope = grade by construction; V23 measures the real slope | Profile | property P8 |
| I34 | Tunnels (< -3 m) don't conflict | C: NetKind.Tunnel; AfterWorld skips | Validate | tunnel scenario |
| I35 | Prefabs by internal name, deterministic, capabilities reported | C: PrefabTable | Model | VanillaPrefabs + modded-name fixture |
| I36 | Piece lengths within prefab limits | C: PathWriter; V11 | Write, Validate | unit |
| I37 | Thresholds: separated dy >= 4 m, at grade dy < 5 m | C: EngineRules | Sites, Validate | unit |
| I38 | Same split t = one junction | C: split registry (1 m) | PlanBuilder | parclo scenario |
| I39 | Underground view must not switch on | A: requireNet = None, requireUnderground = false, Snap.None, flags logged | StudioToolSystem | spike S10; checklist |
| I40 | Red near this preview only (45 m) | A: RedReader footprint filter; "elsewhere" count | RedReader | in-game |
| I41 | Deleted edges are ignored by the planner (plan-ignore) | C: IPlanBuilder.Ignore | PlanBuilder, Router | trumpet trim scenario |
| I42 | applyAction / cancelAction enabled; TOOL_ACTIVE from activeTool | A | StudioToolSystem, StudioUISystem | in-game |
| I43 | Image and binding namespaces prefixed | C: ModIds, Bindings | UI | lint |
| I44 | Planning thread safety | C: immutable inputs; no statics; worker optional | Pipeline | 8 parallel searches give identical fingerprints |

---

## 15. Validators

Severity policy: **Fatal** = planner bug; never emitted; status "Internal check failed (this is a bug)". **Blocking** = would likely be red; emitted, steers autofit and the status, never vetoes a click the game allows. **Warn** = a secondary status line.

| Id | Severity | Rule |
|---|---|---|
| V01 JoinExact | Fatal | Every free end equals its JoinPoint bit for bit. Distinct free points are >= 1 m apart. No free end within 1 m of a node or split end |
| V02 JoinFlags | Fatal | Continuation flags only on 2-ref start+end points with the same prefab and heading dot >= 0.995 |
| V03 SplitSafe | Fatal | Every split leaves >= 30 m on both sides. Splits on one edge are >= 30 m apart unless they share the same t |
| V04 SplitPosition | Fatal | A split end equals Position(edge.Curve, t) within 1 cm |
| V05 BatchStability | Fatal | No hazard left after batch safety |
| V06 TrafficDirection | Fatal | (a) relays run in the source direction; (b) diverge start and merge end tangents align with the one-way edge (dot > 0.5); (c) no touched point becomes a one-way sink or source; (d) rings circulate in RingSign |
| V07 RelayIdentity | Fatal | Relays keep prefab and upgrades; only Flip mirrors |
| V08 Elevation | Fatal | End y = terrain + E within 2 cm; one elevation per JoinPoint |
| V09 RailUntouched | Fatal | No delete, split or relay of rail |
| V10 NoRampNames | Fatal | Name carries only from non-ramp relays or deletes |
| V11 PieceLength | Fatal / Warn | New pieces MinPiece..min(MaxPiece, prefab max); single spans up to MaxElevatedLength are Warn; relays of short existing edges exempt |
| V12 Prefabs | Fatal | No null prefab |
| V13 Limits | Fatal | Span <= 2500 m; pieces <= 600 |
| V14 Mainline | Fatal | Styles with PreserveMainline never delete a site carriageway edge (splits only) |
| V20 Clearance | Blocking | Where the plan distance < halfA + halfB - 0.5, \|dy\| >= Clearance - 1.5 (shared joins and skip zones exempt). Includes highways and other interchanges' ramps |
| V21 AtGradeCrossing | Blocking | Any 2D crossing of a new piece with a remaining road or rail where \|dy\| < 5 m and it is not a planned junction (all hits, shared endpoints excluded) |
| V22 PillarsClear | Blocking | Raised nodes (E >= 3) at least KeepOff from every body >= 2 m below |
| V23 Grade | Blocking / Warn | Real 3D slope <= MaxGrade and <= prefab MaxSlope (Blocking); above the player's grade is Warn ("steeper than your setting, to fit") |
| V24 MinRadius | Warn / Blocking | Built horizontal radius of ramps >= 0.9 R (Warn), >= 0.6 R and >= 15 m (Blocking) |
| V25 TaperRatio | Warn | Taper offset / length <= 1/3 |
| V26 RingGeometry | Blocking | Legs on the circle (+/-0.2 m), arcs between legs >= 10 m, no raised ring node over a highway |
| V27 ExistingJunctionGap | Warn | A new diverge or merge >= 150 m from an existing highway junction |
| V28 LearnedRed | Blocking | No new piece or raised node inside a learned disc |
| W30 TightDiamond | Warn | Diamond junctions < 160 m apart (suggest SPUI / Dumbbell) |
| W31 Continuity | Warn | Tangent kink > 1.5 deg or curvature jump > 1/(5R) at a continuation |
| W32 LocalStreetExit | Warn | Ramps at a street < 16 m |
| W33 SteepFallback | Warn | Profile needed MaxGrade |
| E40-E43 EngineSim | Warn (until spike S7), then Blocking | Dangling, DeadEnds, Slivers, FlowConflicts from IEngineSim |

---

## 16. Test harness

### 16.1 Projects and layers

`Tests/InterchangeStudio.Tests.csproj` (net8.0, LangVersion 9, xunit 2.5.3) links `..\Core\**\*.cs` and `..\Testing\**\*.cs` and references only `$(GameManaged)\Unity.Mathematics.dll` and `Colossal.Mathematics.dll`. The game must be installed; `CS2_GAME_DIR` / Local.props overrides the path.

| Layer | Content |
|---|---|
| Geometry and profile | The 17 ported tests (Dubins arrival, tangent, min radius, quarter circle, 270 deg loop, profile clearance, max grade, level zones, infeasible, smoothing ends, figure-eight, Splits), plus the known bugs: smoothed min radius; LargestTurnDeg after smoothing (L90 + 600 m + L108 measures 108); nested flat zones; Profile with wEnd > 0 and eEnd != eStart; Splits node fallback; symmetry kind re-derivation; Tangency signs; FitCurve parity against `Tests/Data/fitcurve.json` from spike S9; quintic taper G2; clothoid end pose and curvature continuity; arc roundness |
| Builder and validators | Each validator gets a minimal **bad** plan that must fire and a good plan that must stay quiet. Builder: join snapping, 0.5 m bug threshold, continuation flags, split canonicalisation, window search, promotion, staging, transactions, relay inversion |
| Scenarios (golden) | `[Theory]` over Scenarios x applicable styles. `Approved/<scenario>.<style>.json` holds the outcome (ok, or failure code), no Fatal, Blocking count, metrics within tolerance (pieces +/-0, bridge +/-1 m, max grade +/-0.1 %, min radius +/-1 m, max height +/-0.2 m) and the exact headline. On mismatch `*.received.json` and SVGs are written |
| EngineSim oracle | Every scenario plan: `Sim.Apply(...).Report` is clean. Calibration fixtures reproduce the three historic failures: a 0.02 m gap gives DeadEnds; a 3 % split gives Slivers; the one-step at-grade diamond gives Dangling |
| Properties (seeded Fuzz) | P1 no Fatal for any input x style (500 cases per style in CI, `HARNESS_FUZZ=5000` locally); P2 rotation invariance within 2 cm; P3 translation at +/-7000 m within 2 cm; P4 determinism (same fingerprint twice, also across 8 parallel runs); P5 mirror + LHT (until LHT ships, RHT-only styles must refuse with the LHT message); P6 relay idempotence; P7 splits never leave < 30 m; P8 profiles meet clearance and slope <= grade (1 + 1e-3) sampled every 0.5 m; P9 idempotence: after `Sim.Apply` of a crossing plan, `FixFinder` no longer lists the site |
| Session | Scripted FrameInput sequences with a fake plan service and a fake red stream, one test per row of section 11 |
| Autofit | Variant filtering by SensitiveTo / Fixable / Locked; fingerprint dedupe; Final stops; least-red; cost order; "Use my settings" |
| Source rules | Section 4 |
| Performance | 60k-edge synthetic city: snapshot + grid < 50 ms; SiteFinder < 0.5 ms; diamond plan + validate < 10 ms; cloverleaf < 80 ms; stack < 120 ms; autofit worst case < 250 ms; FixFinder < 40 ms |
| Captures | Every `Tests/Captures/*.json` is replayed against its style; an `*.expect.txt` sidecar asserts "builds clean" or "fails: <code>" |

### 16.2 Synthetic city builder (`Testing/CityBuilder.cs`, U52)

```csharp
namespace InterchangeStudio.Testing
{
    public sealed class CityBuilder
    {
        public CityBuilder(ITerrain terrain = null, float maxEdge = 96f);                     // flat by default; pieces split at maxEdge
        public RoadHandle Road(string prefab, params float2[] polyline);                     // at grade: shares nodes where it crosses other at-grade roads
        public RoadHandle Curve(string prefab, float2 a, float2 b, float2 c, float2 d);
        public (RoadHandle up, RoadHandle down) Divided(string prefab, float2 from, float2 to, float median, float curveRadius = 0f);
        public CityBuilder Grid(float2 origin, float2 axis, float spacing, int nx, int ny, string prefab);
        public CityBuilder Elevate(RoadHandle road, float s0, float s1, float height, float approach = 120f);   // viaducts / overpasses: no shared node where |dy| >= 4
        public CityBuilder Rail(params float2[] polyline);
        public CityBuilder Upgrade(RoadHandle road, UpgradeBits bits);
        public CityBuilder Tunnel(RoadHandle road, float s0, float s1);
        public CityBuilder Reverse(RoadHandle road, float s0, float s1);                      // makes a reversed run
        public CityBuilder Name(RoadHandle road, string name);
        public CityBuilder Apply(BuildPlan plan);                                              // through IEngineSim, for multi-step scenarios
        public SnapshotData Data();
        public INetwork Build();                                                               // through SnapshotBuilder (same code path as the game); ids from 1, version 1
    }
    public sealed class RoadHandle { public IReadOnlyList<EdgeId> Edges { get; } public string Prefab { get; } }
    public static class VanillaPrefabs { public static IPrefabTable Load(); public static IPrefabTable Modded(); }   // Testing/vanilla-prefabs.json from spike S9
}
```

**Scenario library** (`Testing/Scenarios.cs`, about 40, named for review):
- crossings: square-divided, skew-35, curved-highway-R600;
- dense grids: dense-grid-60m (the Oct 14 "18 m to come down"), side-street-76m-out;
- existing structures: highway-over-existing, street-over-existing, viaduct-never-lands;
- rail: rail-x-street, rail-x-divided, rail-junction-on-tracks;
- street classes and guards: existing-diamond, local-street, arterial-18m, major-arterial-26m;
- frontage: frontage-both-sides, frontage-two-way;
- terrain: hill-6pct, tunnel-under;
- highway ends: highway-end-pair, highway-end-two-way;
- stems: stem-120m (trim), stem-at-grade-T;
- presets: hwy-x-hwy-separated, parclo-hwy-x-avenue;
- repair and batch safety: reversed-run, close-street-in-ramp-zone, two-splits-one-edge;
- lht-mirror;
- every capture in Tests/Captures.

### 16.3 Invariant checks (`Testing/InvariantChecks.cs`, U53)

`InvariantChecks.All(PlanResult r, PlanContext ctx)` asserts, for any produced plan:
- no Fatal violation;
- EngineSim clean (Dangling, DeadEnds, Slivers, FlowConflicts);
- every relay keeps prefab, upgrades and source direction;
- every split >= 30 m with an exact position;
- every JoinPoint is exact and has the correct flags;
- no rail touched;
- no ramp named;
- every piece within length limits;
- profiles within grade.

Scenario, property and capture tests all call it.

### 16.4 SVG renderer (`Testing/PlanSvg.cs`, `ProfileSvg.cs`, `ReviewSheet.cs`, U54)

```csharp
namespace InterchangeStudio.Testing
{
    public sealed record SvgOptions { public Rect2? Window { get; init; } public float PxPerMetre { get; init; } = 0.6f; public bool Arrows { get; init; } = true;
                                      public bool ElevationColours { get; init; } = true; public bool Labels { get; init; } = true; public bool CurvatureComb { get; init; }
                                      public bool Violations { get; init; } = true; }
    public static class PlanSvg { public static string Render(INetwork net, PlanResult result, SvgOptions options); }
    public static class ProfileSvg { public static string Render(PlanResult result, int rampOrGroup, PlanContext ctx); }
    public static class ReviewSheet { public static void Write(string dir, IEnumerable<(string scenario, StyleId style, PlanResult result, INetwork net)> runs, string approvedDir = null); }
}
```

- **Plan view:**
  - north up (+z), compass, scale bar;
  - existing roads grey by width, rail hatched, deleted edges as red outlines;
  - new pieces at true width, coloured by elevation band (0-3, 3-9, 9-18, 18+ m);
  - one-way arrows every 60 m, so direction bugs are visible at a glance;
  - pillar dots, JoinPoints sized by refs, splits as diamonds;
  - learned discs, ramp labels, violations as numbered rings with a side list.
- **Profile strip:** elevation vs s, obstacles as boxes at their real height, grade labels, eased-climb extents, red above MaxGrade.
- **Curvature comb** (optional) to judge G2 smoothness.
- **`out/review/index.html`:** a card per scenario x style with a pass/fail badge, metrics, and approved vs received side by side. It can be published as a private page for the author to review shapes without starting the game.

### 16.5 Capture and replay

In-game "Save this spot" writes a `CaptureBundle`. `dotnet run --project Harness -- replay <file>` re-plans, renders SVG, and diffs against the in-game fingerprint. Dropping the file into `Tests/Captures/` (with an optional `.expect.txt`) makes it a permanent test. Captures with game red but no core Blocking are logged as calibration cases ("Core missed this red").

### 16.6 In-game checklist (per milestone, in the harness output as checklist.html)

- overpass at the square scenario;
- rail crossing;
- diamond two-step;
- names restored;
- upgrades kept;
- no red without Anarchy;
- right-click finishes;
- hotkey rebind;
- settings migrated from ClaudeInterchanges;
- underground view stays off;
- fresh `Logs/InterchangeStudio.log` with no exceptions (the log resets each game start).

---

## 17. Phase-0 in-game spikes

Answered with the throwaway `Spikes` mod before the units that depend on them commit. Results are recorded at the top of DESIGN.md section 20.

| Id | Question | Blocks |
|---|---|---|
| S1 | Are Bezier b/c handle heights honoured on elevated courses (Hermite handles), or is elevation linear between nodes? | `Rules.Handles` default (U15) |
| S2 | Do two different-t splits of the same edge in one batch work? | V03 second clause; BatchSafety staging rule |
| S3 | Does our own preview churn component order versions or `Updated` tags on originals? | NetworkReader change detection (U43) |
| S4 | Does Task.Run planning behave under the game's Mono (exceptions, GC)? | `PlanService(async)` default |
| S5 | Can `OverlayRenderSystem` draw curve outlines (ghost of stage 2)? | optional ghost |
| S6 | CompositionFlags field names, and is mirroring Left/Right right when inverting an edge? | UpgradeBits mapping, Flip |
| S7 | EngineSim calibration: reproduce the 0.02 m gap, the near-end sliver and the one-step diamond dangling split; record how the engine heals 2-leg nodes | E40-E43 severity |
| S8 | Settle timing: frames from apply to the version bump; Gameface `vh` support | SessionTuning, CSS |
| S9 | HeightPatch vs TerrainUtils.SampleHeight parity (1000 points, < 1 cm); dump FitCurve samples and vanilla prefab table | GameTerrain, fitcurve.json, vanilla-prefabs.json |
| S10 | Underground view: does Layer.TrainTrack in the raycast mask or anything else switch it on? Also find the city's left-hand-traffic flag | StudioToolSystem, TrafficSide source |

---

## 18. Feature-parity checklist

Every catalogued feature, with its new home. Duplicate catalogue entries are merged into one row (all names listed). "Change" notes behaviour that is deliberately different.

| # | Catalogued feature | New home | Change |
|---|---|---|---|
| 1 | Tool registration and activation | Game/StudioToolSystem.cs (prefab-less, toolID, raycast Net Road\|TrainTrack, OnStartRunning, Toggle), Game/Mod.cs | Snap.None; flags explicit |
| 2 | Modes and panel settings (global statics) | StyleId, PlanConfig, EngineRules (Contracts), Core/Config/SettingsSchema.cs | immutable; every constant named |
| 3 | Per-frame tool loop (OnUpdate state machine) | Core/Session/ToolSession.cs + StudioToolSystem skeleton | explicit phases |
| 4 | Automatic two-step build; Two-step one-click interchange | LiftThen + FollowUp + Session Settling/FollowUp + ISiteFinder.Relocate + speculative stage 2 | settle on version + quiet frames; predicted before the click |
| 5 | Hover cache | PlanKey (canonical site, cfg hash, RegionVersion) in PlanService; SiteFinder hysteresis | no reset on mouse jitter |
| 6 | Hover dispatch | Core/Sites/SiteFinder.cs (7.2) | reversed run is a badge |
| 7 | Plan cache plus per-frame re-emit | PlanService + PreviewOp.Show every frame + DefinitionWriter.StillValid | - |
| 8 | Red-preview reporter (Blocked) (x2) | Game/RedReader.cs + Core/Text/RedExplainer.cs | re-read every frame; "elsewhere" message |
| 9 | Autofit (layout variants); Autofit hooks; Autofit and caching integration (presets); Autofit | Core/Autofit/* | immutable configs, fixability filter, dedupe, cost order, least-red, game feedback |
| 10 | Find next crossing to fix (x3) | Core/Sites/FixFinder.cs + Session + Game/CameraJumper.cs + Fix tab | divided pairs counted once; tracks junctions listed as manual |
| 11 | Ramp-terminal exclusion (IsTerminal) | INetworkKit.IsTerminal (Core/Network/Topology.cs) | also stops walkers |
| 12 | At-grade highway crossing preview | OverpassStyle, LiftThen, INetworkKit.ClassOf, W32 | partner overlap merged, not dropped |
| 13 | Railway level crossings (x2); PlanRoadOverRail + FindRailPartner | CrossingDetector (rail), RailOverpassStyle, LiftKit RoadOverRail, V09 | - |
| 14 | At-grade crossing detection | CrossingDetector, NodeLegs | value-type legs |
| 15 | Spatial grid index | Core/Model/SpatialGrid.cs | per-cell stamps, pooled lists |
| 16 | Road-name restore after rebuild; Road name preservation; Road-name restore tick | NameCarry + Game/NameKeeper.cs ticked by StudioUISystem; V10 | several anchors; waits for the new aggregate |
| 17 | Status and logging plumbing | StatusView + Narrator + Session pinning + Game/Log.cs | pinned until the cursor leaves; verbose gate |
| 18 | Seg / Plan chain model | ChainSeg, IChain (Contracts), Core/Network/Chain.cs | - |
| 19 | Arc-length parameterisation helpers | IArcTable, CurveKit, Chain | binary search |
| 20 | PlanStreetBridge (street over highway) | OverpassStyle + LiftKit StreetOverHighway + IStyle.DeckMargin | - |
| 21 | PlanHighwayBridge (one carriageway over the street) | OverpassStyle HighwayOver + LiftKit | - |
| 22 | WalkStreet; WalkHighway | INetworkKit.WalkStreet / WalkHighway | stop (not sever) at T side streets; stop at ramp terminals |
| 23 | Finish (ramp-room arithmetic) | LiftKit.Plan | same wording; honest grade (Q1) |
| 24 | ElevationAt (vertical profile) | IProfileSolver eased profile | peak = grade |
| 25 | WriteLift | LiftKit.Write + IPathWriter.PlaceBreaks + IPlanBuilder.Relay | multi-pass keep-off; chain ends never dropped; clearance to the road surface |
| 26 | FindSeparated plus Cross2D | SeparationDetector + ICurveKit.Cross2D | all intersections |
| 27 | Carriageways (pair both directions) | SeparationDetector | same-street pairing |
| 28 | ChainThrough; Follow; Carriageway chain (Follow / ChainThrough) | IServiceKit.Carriageways + INetworkKit.Follow | mainline tie-break |
| 29 | AttachAt; Highway attach (AttachAt) | IPlanBuilder.OnChain (AttachFactory) | window search before staging |
| 30 | FindJunction; Street junction search (FindJunction) | IServiceKit.Junction | metres, Splits, node fallback |
| 31 | Network predicates | NodeLegs, EdgeInfo.Kind, INetworkKit, IPrefabTable | - |
| 32 | Style dispatcher (PreviewFor) | IStyleRegistry + routing table 7.3 | presets also lift at grade |
| 33 | Best fit (AutoPreview) (x2) | BestFitStyle | Final propagates; winner must be Blocking-free; grammar |
| 34 | Diamond (ToolMode.Exit) (x2) | DiamondSpuiStyles (ServiceStyleBase) | chain-offset ramps |
| 35 | SPUI (x2) | DiamondSpuiStyles + IServiceKit.Centre | pillar check under the deck |
| 36 | Dumbbell (x2) | DumbbellStyle + IRingKit | ring clears the carriageway; leg gap |
| 37 | Ramp end placement (PlaceRampEnds) | IServiceKit.PlaceEnds | - |
| 38 | Ramp geometry (WriteRamps) | IServiceKit.WriteRamps | quintic taper + chain offset + profile |
| 39 | Existing-interchange guard (ExistingRamps) (x2) | IServiceKit.ExistingInterchange | straightest walk; also Frontage and presets |
| 40 | Ramp-zone streets (RampZoneClear + CloseStreets); Close local streets in the ramps' way; CloseStreets | IServiceKit.RampZoneClear + IStreetSurgery.CloseStreets + BatchSafety | stubs keep upgrades and elevation; counts streets |
| 41 | At-grade conflict check (RampsClear) | V21 + V20 | includes ramp prefabs; all hits |
| 42 | Frontage slip ramps; Frontage ramps mode; Frontage mode | FrontageStyle + IFrontageKit | slips follow elevation; direction and prefab checks |
| 43 | Texas U-turns (TryUTurn); Texas U-turn | IUTurnKit | projection replaces the 3 m scan |
| 44 | Prefab pickers; RampPrefab (x2); Two-way ramp prefab lookup | IPrefabTable (Core/Model/PrefabTable.cs) + Game/PrefabReader.cs | skip list for rings; capabilities |
| 45 | Roundabout builder (shared) | IRingKit | legs on the circle |
| 46 | Highway end (start); Highway end (ToolMode 6); Highway end -> avenue (divided); -> avenue (single two-way); -> roundabout | HighwayEndStyle + IStreetSurgery + IRingKit | G2 converge; both street halves named |
| 47 | Carriageway trim-back (ChainFrom / CutChain / ChainDir) | IStreetSurgery.Trim | - |
| 48 | Street split by delete + re-lay (SplitPath / AddPiece) | IStreetSurgery.SplitPath + IPlanBuilder.Relay | sliver guard |
| 49 | Lane helper | IPlanBuilder.Add / Relay | - |
| 50 | StreetBetween / PointAlong / StreetWidthAt | INetworkKit.StreetBetween / WidestStreetAt + IChain.Position | - |
| 51 | FindFrontage / SOf / WriteSlip | IFrontageKit (Find via grid + IChain.Project) | Splits; direction check |
| 52 | Reversed-run repair (flip); Flip repair of reversed carriageway | ReversedRunDetector + FixDirectionStyle + IPlanBuilder.Flip | badge + Fix tab instead of hijacking hover |
| 53 | Spec / Preview model | PieceSpec, PathSpec, Piece, BuildPlan (Contracts) | immutable |
| 54 | JoinPieces | JoinPoint by construction + V01 / V02 | heading condition for continuations |
| 55 | Emit (definitions); DeleteDef | Game/DefinitionWriter.cs (verbatim) | seed = Fnv64 |
| 56 | Ramp mode two-click flow | Session anchor + IRampEnds.FromHit / Anchor / Rematch + FreeRampStyle | - |
| 57 | End kinds: Taper / Junction / Node | IRampEnds.Options | quintic tapers |
| 58 | Two-way highway side picking and direction | IRampEnds.FromHit | - |
| 59 | End placement and road matching (EndAt / MatchEnd) | IRampEnds.Match | Splits + node fallback; kind re-derived |
| 60 | Route search (PlanRamp) | IRouter | cheap checks first, 24 full checks, best failure reported |
| 61 | Dubins shortest paths | Core/Geometry/Dubins.cs (verbatim) | - |
| 62 | Smoothing (transition-curve approximation) | IAlignmentSmoother (Clothoid + Laplacian fallback) | true G2; radius kept |
| 63 | Turn and self-crossing limits | Core/Geometry/Prims.cs | LargestTurnDeg fixed |
| 64 | Crossing detection (ramps) | Core/Kit/RampCrossings.cs | uses the other ramp's slope across the deck |
| 65 | Vertical profile (Profile.Solve DP) | IProfileSolver | merged zones; no input mutation |
| 66 | Side-on overlap check | Router overlap + V20 | taper included past MinNodeOffset + 10 |
| 67 | Writing road pieces and placing pillars | IPathWriter (Core/Write/*) | all paths at once; adaptive chord points |
| 68 | Multi-ramp planning (PlanJobs) | IMultiRampPlanner + ILevelSolver | joint levels; transactions |
| 69 | Symmetry (180 deg / 4-way) | ISymmetryKit | kind re-derived |
| 70 | Plain-English status and description; Plain-language status/log | RoutedRamp.Description + INarrator + Phrases | structured Explanation |
| 71 | RampJob options used by presets | RampJob, RampShape (Contracts) | - |
| 72 | Plan-ignore set | IPlanBuilder.Ignore / Ignored | - |
| 73 | Ramp settings | SettingsSchema (radius, lanes, symmetry) | Standard radius 70 |
| 74 | Unit tests for the game-independent geometry | Tests/Geometry/RouterTests.cs (ported) + new suites | - |
| 75 | Preset dispatch (PresetHover) | SiteFinder (Cross4 / Stem) + IStyleRegistry | - |
| 76 | Grade-separated crossing finder (FindRoadCross) | Cross4Detector | canonical key; existing-interchange guard |
| 77 | Carriageway line extraction (Lines / CwLine) | Cross4Detector + CwLine | - |
| 78 | Exact arc placement (Tangency) | IPresetGeometry.Solve | - |
| 79 | ArcJob | IPresetGeometry.ArcJob | exact R; taper ratio |
| 80 | Four-way interchange layout (FourWayPreview) | FourWayFamily | atomic groups |
| 81 | Shared diverge/merge trunks (ShareForks) | IPresetGeometry.ShareForks + MultiRamp | elevated forks; Ramp2 trunks; fallback |
| 82 | Partial cloverleaf A4 (ParcloPreview) | ParcloStyle | taper >= 3x offset; stub atomic |
| 83 | Highway-end stem finder (FindStem) | StemDetector | at-grade T and two-way stems |
| 84 | Trumpet; Directional T | StemFamily | - |
| 85 | Stem trim-back | StemFamily + IStreetSurgery.Trim | player's grade |
| 86 | Interchange presets (ToolMode 8) | FourWayFamily, ParcloStyle, StemFamily | - |
| 87 | Freehand ramp tool (ToolMode 7) | FreeRampStyle + router family | - |
| 88 | Overpass mode (ToolMode 0) | OverpassStyle | - |
| 89 | Ramps on existing overpasses / viaducts | SeparationDetector + IServiceKit.Carriageways (viaduct) + PlaceEnds descent | - |
| 90 | Toolbar button; Toolbar button + floating panel | UI/InterchangeStudio.mjs | - |
| 91 | Rebindable hotkey toggle; Rebindable keybinding | Game/StudioSettings.cs + Game/Mod.cs | new action name; rebinds not migrated |
| 92 | Options-page locale (en-US only) | Game/LocaleSource.cs | registered for every locale |
| 93 | Draggable floating panel | mjs + PanelPrefs | position and tabs persisted |
| 94 | Style catalogue: tabs and tiles | CATALOG from StyleCatalog | Fix tab; disabled tiles explained |
| 95 | About card | mjs; copy in StyleCatalog | - |
| 96 | Context-sensitive settings | SettingSpec.RelevantFor + StyleInfo.Settings | parclo gets crossing settings |
| 97 | Size macro-setting; Size presets | SizePresets + SET_SIZE | "Custom" when diverged |
| 98 | Status card | StatusView + mjs | Working kind, chips, suggestions, stages |
| 99 | Key hint footer | HOTKEY binding | follows rebinds |
| 100 | Settings persistence (x3) | StudioSettings.PanelState + LegacyImport | style persisted |
| 101 | Binding inventory | Bindings (Contracts UI) + 13.1 | consolidated JSON bindings |
| 102 | Build and deploy on build | InterchangeStudio.csproj Deploy | explicit compile items; CorePurity |
| 103 | Browser mock-up harness | preview/panel.html | stateful; catalog from Harness |
| 104 | Rebuilt roads keep identity | Relay + NameCarry + V07 | - |
| 105 | Performance caches | PlanService LRU, SpatialGrid, snapshot versioning, time-sliced / worker planning | - |
| 106 | Logging | Game/Log.cs | verbose gate |
| 107 | Dev tooling | Tests, Harness (review, fuzz, replay), preview, captures | - |

---

## 19. Work breakdown and milestones

Units are small enough for one engineer each (1-3 files). Every unit compiles against `Core/Contracts.cs` alone. Dependencies are only needed to run the unit's own tests against real collaborators; fakes are fine before then.

**Waves (units in a wave can run in parallel; each wave depends only on earlier waves):**
- Wave 0: U01, U04, U05, U08, U27, U36, U38, U39, U40, U49, U50, U54, U58.
- Wave 1: U02, U03, U06, U09, U15, U35, U41, U42, U44, U45, U51.
- Wave 2: U07, U10, U16, U18, U43, U46, U52, U56.
- Wave 3: U11, U12, U14, U17, U23, U47, U53, U55.
- Wave 4: U13, U19, U20, U21, U24, U26.
- Wave 5: U22, U25, U28, U29, U31.
- Wave 6: U30, U32, U33, U34.
- Wave 7: U37.
- Wave 8: U48, U57.

The critical path is U05, U03, U10, U14, U20, U29, U30, U37, U48. Units that only consume interfaces (U27, U35, U36, U38, U39, U40) start on day one and test against fakes.

| Unit | Title | Layer | Files | Depends on |
|---|---|---|---|---|
| U01 | Mod project and build props | build | Directory.Build.props, InterchangeStudio.csproj, Local.props.example | - |
| U02 | Purity, test and harness projects | build | Build/CorePurity/CorePurity.csproj, Tests/InterchangeStudio.Tests.csproj, Harness/Harness.csproj | U01 |
| U03 | Network snapshot and grid | core | Core/Model/NetworkSnapshot.cs, SnapshotBuilder.cs, SpatialGrid.cs | U05 |
| U04 | Prefab table and terrains | core | Core/Model/PrefabTable.cs, Terrains.cs | - |
| U05 | Curve maths | core | Core/Geometry/CurveMath.cs, Arcs.cs, Cross2D.cs | - |
| U06 | Prims, Dubins, path ops, CurveKit facade | core | Core/Geometry/Prims.cs, Dubins.cs, PathOps.cs | U05 |
| U07 | Smoothers | core | Core/Geometry/LaplacianSmoother.cs, ClothoidSmoother.cs | U06 |
| U08 | Vertical profile and solver | core | Core/Profile/VerticalProfile.cs, ProfileSolver.cs | - |
| U09 | Joint level solver | core | Core/Profile/LevelSolver.cs | U08 |
| U10 | Chain, walkers, topology | core | Core/Network/Chain.cs, NetworkKit.cs, Topology.cs | U03, U05 |
| U11 | Crossing, separation, end detectors | core | Core/Sites/CrossingDetector.cs, SeparationDetector.cs, HighwayEndDetector.cs | U10 |
| U12 | Four-way, stem, reversed-run detectors | core | Core/Sites/Cross4Detector.cs, StemDetector.cs, ReversedRunDetector.cs | U10 |
| U13 | SiteFinder, Relocator, FixFinder | core | Core/Sites/SiteFinder.cs, Relocator.cs, FixFinder.cs | U11, U12 |
| U14 | Plan builder | core | Core/Plan/PlanBuilder.cs, AttachFactory.cs, BatchSafety.cs | U10, U15 |
| U15 | Path writer | core | Core/Write/Breakpoints.cs, PillarPlacer.cs, PathWriter.cs | U05, U08 |
| U16 | Validators A (contract rules) | core | Core/Validate/AfterWorld.cs, ValidatorSet.cs, Rules/ContractRules.cs | U03, U05 |
| U17 | Validators B (world and quality rules) | core | Core/Validate/Rules/WorldRules.cs, Rules/QualityRules.cs | U16 |
| U18 | Engine model | core | Core/Validate/EngineSim.cs, OverlayNetwork.cs | U03 |
| U19 | Lift kit | core | Core/Kit/LiftKit.cs | U10, U08, U15, U14 |
| U20 | Service kit | core | Core/Kit/ServiceKit.cs, ExistingInterchangeGuard.cs | U10, U06, U08, U14 |
| U21 | Street surgery and rings | core | Core/Kit/StreetSurgery.cs, RingKit.cs | U10, U14 |
| U22 | Frontage and U-turn kits | core | Core/Kit/FrontageKit.cs, UTurnKit.cs | U20 |
| U23 | Ramp ends and symmetry | core | Core/Kit/RampEnds.cs, SymmetryKit.cs | U10, U06 |
| U24 | Router | core | Core/Kit/Router.cs, RampCrossings.cs | U07, U08, U23 |
| U25 | Multi-ramp planner | core | Core/Kit/MultiRampPlanner.cs | U24, U09, U14 |
| U26 | Preset geometry | core | Core/Kit/PresetGeometry.cs | U23 |
| U27 | Style catalogue, registry, LiftThen | core | Core/Styles/StyleCatalog.cs, StyleRegistry.cs, LiftThen.cs | - |
| U28 | Overpass, rail, fix-direction styles | core | Core/Styles/OverpassStyle.cs, RailOverpassStyle.cs, FixDirectionStyle.cs | U19, U27, U11 |
| U29 | Diamond, SPUI, Dumbbell | core | Core/Styles/ServiceStyleBase.cs, DiamondSpuiStyles.cs, DumbbellStyle.cs | U20, U21, U27 |
| U30 | Frontage and Best fit | core | Core/Styles/FrontageStyle.cs, BestFitStyle.cs | U22, U29 |
| U31 | Highway end | core | Core/Styles/HighwayEndStyle.cs | U21, U27 |
| U32 | Free ramp | core | Core/Styles/FreeRampStyle.cs | U25, U23 |
| U33 | Four-way presets and parclo | core | Core/Styles/FourWayFamily.cs, ParcloStyle.cs | U25, U26, U27 |
| U34 | Trumpet and Directional T | core | Core/Styles/StemFamily.cs | U25, U26, U21 |
| U35 | Autofit | core | Core/Autofit/VariantTable.cs, AutofitSearch.cs, ConfigDiff.cs | U27 (interfaces; fakes until styles land) |
| U36 | Plan jobs and service | core | Core/Pipeline/PlanJob.cs, PlanService.cs, Planner.cs | - |
| U37 | Composition root | core | Core/Pipeline/CoreServicesFactory.cs | all core units |
| U38 | Tool session | core | Core/Session/ToolSession.cs | - |
| U39 | Text and narrator | core | Core/Text/Phrases.cs, Narrator.cs, RedExplainer.cs | - |
| U40 | Settings schema, panel model, JSON | core | Core/Config/SettingsSchema.cs, Core/Panel/PanelModel.cs, Core/Common/Json.cs | - |
| U41 | Capture codec | core | Core/Diagnostics/CaptureCodec.cs | U40 |
| U42 | Mod, settings, migration, locale | adapter | Game/Mod.cs, StudioSettings.cs, LocaleSource.cs | U01, U40 |
| U43 | Network reader, prefabs, terrain | adapter | Game/NetworkReader.cs, PrefabReader.cs, GameTerrain.cs | U03, U04, S3 answered |
| U44 | Definition writer | adapter | Game/DefinitionWriter.cs | U01 |
| U45 | Red reader and log | adapter | Game/RedReader.cs, Log.cs | U01 |
| U46 | Names, camera, captures | adapter | Game/NameKeeper.cs, CameraJumper.cs, CaptureWriter.cs | U41 |
| U47 | Tool system | adapter | Game/StudioToolSystem.cs | U38, U43, U44, U45, U46 |
| U48 | UI system | adapter | Game/StudioUISystem.cs | U42, U47, U40, U39, U37 |
| U49 | Panel module | ui | UI/InterchangeStudio.mjs | - |
| U50 | Stylesheet and icons | ui | UI/InterchangeStudio.css, UI/images/is-*.svg | - |
| U51 | Stateful browser mock | ui | preview/panel.html | U49, U50, U40 |
| U52 | City builder and vanilla prefabs | tests | Testing/CityBuilder.cs, VanillaPrefabs.cs, vanilla-prefabs.json | U03, U04 |
| U53 | Scenarios, invariant checks, approvals | tests | Testing/Scenarios.cs, InvariantChecks.cs, Approvals.cs | U52, U18 |
| U54 | SVG renderer and review sheet | tests | Testing/PlanSvg.cs, ProfileSvg.cs, ReviewSheet.cs | - |
| U55 | Ported geometry tests | tests | Tests/Geometry/RouterTests.cs, Tests/Geometry/ProfileTests.cs | U06, U07, U08 |
| U56 | Source rules and lints | tests | Tests/SourceRules/SourceRuleTests.cs, CssLintTests.cs, ConfigTests.cs | U02 |
| U57 | Fuzz, properties, harness CLI | tests | Testing/Fuzz.cs, Tests/Properties/PropertyTests.cs, Harness/Program.cs | U53, U54, U37, U41 |
| U58 | Phase-0 spike probe | adapter | Spikes/SpikeProbe.csproj, Spikes/SpikeSystem.cs | - |

**Milestones** (each ships only after its scenarios are approved and its in-game checklist passes; the author gets working buttons early):
- M0: contracts frozen, spikes answered, skeleton end to end (Overpass on a fixture and in game).
- M1: Overpass, rail, find next, fix direction, names, red explanations, autofit, panel shell, legacy import.
- M2: Diamond, SPUI, Dumbbell, Best fit with the predicted two-step.
- M3: Frontage with U-turns; Highway end.
- M4: Free ramp with symmetry.
- M5: all presets.
- M6: polish (G2 default after the review sheet, Hermite decision, ghost overlay, LHT flag, thumbnail, Paradox Mods packaging).

---

## 20. Risks and open questions

Spike results (fill in as answered): S1 - ; S2 - ; S3 - ; S4 - ; S5 - ; S6 - ; S7 - ; S8 - ; S9 - ; S10 - .

| # | Risk | Mitigation |
|---|---|---|
| R1 | Core validators drift from the game's collision rules | The game stays the final judge; Blocking never vetoes; captures with red but no core Blocking become calibration tests |
| R2 | EngineSim mis-predicts healing, merging or multi-splits | Used only for prediction and as a Warn oracle until S7; stage 2 always re-plans on the real network |
| R3 | Snapshot version churn (preview Temp, per-frame writes) causes a re-plan loop | Content diff before bumping; region stamps; a debug assert "version bumped with zero semantic change"; S3 |
| R4 | Clothoid smoother fails to converge | Laplacian fallback with pre-inflation; V24; property tests over 1000 seeds |
| R5 | Honest peak grade needs more room than the old tool, so some tight-grid bridges that built before now refuse | Measured by the dense-grid scenarios; autofit grade rows; open question Q1 |
| R6 | Scope: 15 styles plus a new engine | Milestones; shared kits; the old mod stays installable until M2 |
| R7 | Two mods installed at once (two buttons, one hotkey) | Prefixed ids and images; a one-time notice; never auto-delete the old mod |
| R8 | Worker planning under Mono | Off by default until S4; immutable inputs make the sync and async paths identical |
| R9 | Name restore misses (not yet aggregated, matched to a ramp) | Wait for the new aggregate (up to 180 frames); match by class and prefab; several anchors; misses logged |
| R10 | Gameface CSS or font regressions | CssLint and glyph lint; check UI.log after every UI deploy |
| R11 | Prefab heuristics with modded assets | Deterministic picks, skip lists, capabilities shown in the UI |
| R12 | Underground view still unexplained | Spike S10; explicit flags; activation logging |

Open questions for the author:
- **Q1 (vertical honesty vs fit).** The old bridges ramped at up to 1.5x the gradient shown in the panel (5 % really peaked at 7.5 %; the 9 % fallback peaked at 13.5 %). The rebuild makes the panel value true, so some tight-grid bridges will need about 18 % more room or will refuse. Should the steepest fallback stay at 9 % (honest), or be raised toward the old effective 12-13 % when room is short?
- **Q2 (key binding).** The new mod id means a custom key rebind of Ctrl+Shift+H cannot be carried over automatically. A one-time notice will say so. Is that acceptable?
- **Q3 (Turbine).** Ship the turbine as today (a stack with smaller flyovers) for parity and add a true spiral turbine later behind a flag, or wait for the spiral?
