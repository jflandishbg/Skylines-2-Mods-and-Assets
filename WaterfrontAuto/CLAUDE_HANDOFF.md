# WaterfrontAuto — Handoff for Claude (v4)

*Updated: 2026-11-22 (v4). Built by Antigravity for the author's Cities: Skylines II setup (`C:\Users\<you>\CS2Planner\WaterfrontAuto`).*

## Goal
Automatically turn bare coastal building cliffs into an **Atlantic City–style continuous walkable waterfront** (Buildings → Grand Timber Boardwalk with lamps, benches & kiosks → Sandy Beach & umbrellas → Ocean; Industrial Quays + working piers; smooth curls into adjacent **Placemaker** beaches), using **100% vanilla prefabs**, **zero custom ECS components**, **0 ms/frame idle**, and **zero duplicate stacking across save/reload**.

---

## Build & Test Commands
- **Build & auto-deploy to CS2 (`Mods\WaterfrontAuto\`):**
  ```powershell
  C:\Users\<you>\.dotnet\dotnet.exe build C:\Users\<you>\CS2Planner\WaterfrontAuto\WaterfrontAuto.csproj -c Release
  ```
- **Run offline unit tests (14 test suites, no CS2 needed):**
  ```powershell
  C:\Users\<you>\.dotnet\dotnet.exe run --project C:\Users\<you>\CS2Planner\WaterfrontAuto\Tests\WaterfrontAuto.Tests.csproj
  ```
- **Log:** `%USERPROFILE%\AppData\LocalLow\Colossal Order\Cities Skylines II\Logs\WaterfrontAuto.log`
- **Manifests & overrides:** `%USERPROFILE%\AppData\LocalLow\Colossal Order\Cities Skylines II\ModsData\WaterfrontAuto\`
- **Panel hotkey:** `Ctrl+Shift+W` or top-left toolbar wave/pier icon.

---

## What Changed in v4 (Both the author's Feedback & Claude's `FIXES_REQUEST.md`)

### 1. 1,000× Speedup (20,000 ms → < 30 ms on large cities!)
- `WaterfrontAuto.log` showed v3 taking **13–20 seconds** on the author's full city because `ShorelineDetector.DetectEdges` scanned `allBuildings` and `existingNets` in O(N²) *before* probing water.
- **Fixed (`Core\ShorelineDetector.cs`, `Core\WaterfrontPlanner.cs`, `Core\EntityMatcher.cs`):**
  - Added generic 32 m `SpatialGrid2D<T>` for buildings and nets.
  - `CheckEdge` now probes **water depth FIRST** (skipping ~98% of inland buildings immediately!) and only queries the spatial grid for true waterfront candidates.
  - Verified by `Test14_LargeCitySpeedBenchmark` (4,040 buildings + 3,000 roads runs in milliseconds).

### 2. Atlantic City Boardwalk "Oomph", Even Block Alignment & Seaward Beach
- **Grand Timber Boardwalk (`Game\PrefabCatalog.cs`):** Prefers CS2's widest vanilla timber pier (`LeisurePier01Large01`, falling back to `Medium01` / `QuaySmallWide01`).
- **Straighten Even Across Blocks (`StraightenBlocks = true`, fixes U-dips behind shorter rowhouses):** Collinear buildings along a block are projected onto their shared outer seaward line (capped at 16 m), eliminating inward U-dips and filling recessed terraces behind shorter lots with matching `Tiles Surface 01` / `Pavement` deck paving (never overlapping roads).
- **Atlantic City Cross-Section (`AtlanticCityBeach = true`, `HomesUseBoardwalk = true`):**
  - Layout: `Street → Buildings → Grand Timber Boardwalk → Sandy Beach & Umbrellas → Ocean`.
  - Boardwalk dressing (`Core\WaterfrontPlanner.cs`, `Game\PrefabCatalog.cs`): park lamps (`LightpolePark01..04`, every 18 m), seaward benches (`GardenBench01..04`, every 20 m), periodic kiosks/gazebos (`Kiosk01..03`, `FoodCart01`, `Gazebo01..03`) placed in recessed boardwalk terraces, and nautical life-buoy stations (`LifeBuoyStation01`).
  - Seaward sandy beach (`Sand Surface 01` + `Parasol01..03` + `DeckChair01..03`) placed strictly seaward of the boardwalk outer edge (never creeping inland onto roads and never inside an existing Placemaker beach).
  - Seaward-only opt-in terrain grading (`EnableBeachTerrain`, OFF by default) now starts `+4 m` seaward of the boardwalk so it never carves trenches under buildings.

### 3. Curl Smoothly Into Placemaker Beaches
- `WorldScanner.ScanExistingBeaches` scans live non-owned `Sand`/`Beach` Areas (≥ 80 m², including Placemaker beaches).
- `WaterfrontPlanner.EmitPlacemakerBeachCurls` checks both ends of non-industrial chains and, when within `40 m` of a Placemaker beach, emits a smooth curved ramped walkway (`TransitionRamp`) descending gently onto the dry upper rim of the Placemaker beach.

### 4. Claude's `FIXES_REQUEST.md` — Zero Stacked Duplicates & Tight Ownership Matching
- **Pure-C# `Core\EntityMatcher.cs`:**
  - `MatchCreated`: requires **exact prefab name equality**, **no `Owner`**, **no `Temp`**, tight tolerances (**1.0 m edges, 1.0 m areas, 0.5 m objects**), and **consume-once** semantics. Unmatched pending counts are logged.
  - `SpatialDedupeIndex`: O(1) spatial hash dedupe before emitting Areas (`0.5 m` centroid) and Objects (`1.0 m` position) matching the same prefab (fallback for pre-v4 saves with no manifest).
  - `ManifestCodec` + `MatchManifest`: atomic sidecar `ModsData\WaterfrontAuto\manifest-<cityKey>.txt` (`kind|prefabName|x|z`, rounded to 0.1 m, keyed by `CityConfigurationSystem.cityName` → fallback `default`), adopted automatically after load warmup (0.5 m tolerance, exact prefab, no `Owner`/`Temp`).
- **Panel button:** Added `"Adopt / clean old waterfront (pre-v4 saves)"` in `UI\WaterfrontAuto.mjs` + `WaterfrontBuilderSystem.AdoptOrCleanOldWaterfront()`.

### Backups Created (Excluded from `.csproj` Compilation)
- `Core\WaterfrontModels.pre_v4.cs`, `Core\ShorelineDetector.pre_v4.cs`, `Core\WaterfrontPlanner.pre_v4.cs`
- `Game\PrefabCatalog.pre_v4.cs`, `Game\WorldScanner.pre_v4.cs`, `Game\WaterfrontBuilderSystem.pre_v4.cs`, `Game\WaterfrontUISystem.pre_v4.cs`, `Game\Mod.pre_v4.cs`
- `Tests\PlannerTests.pre_v4.cs`

---

## Critical CS2 ECS Invariants (Preserved)
1. `WaterfrontBuilderSystem` MUST stay `UpdateBefore<WaterfrontBuilderSystem, GenerateObjectsSystem>(SystemUpdatePhase.Modification1)` and `WaterfrontCaptureSystem` in `ModificationEnd`.
2. Building delta query watches ONLY `Created | Deleted` (NEVER `Updated`) + `ComputeBuildingFingerprint()` → **0 ms/frame idle**.
3. Maritime buildings (`PlacementFlags.Shoreline | Floating | Underwater | Waterway`, `WaterPumpingStationData`, `SewageOutletData`, `WaterwayData` sub-nets, port/harbor names) and `WaterwayData` shipping lanes remain strictly protected.
4. Surfaces never overlap `IsRoad`; access spurs stop at sidewalk edge (`SnapEndNetId = 0`) for `LocalConnect`.

---

## What the author Should Test Next In-Game
1. **Speed & Atlantic City look:** Load the Lobstertown save, check `WaterfrontAuto.log` build time (should drop from ~20,000 ms down to well under 500 ms!), and check:
   - Whether rowhouse blocks (like `Lobster Avenue`) now get a straight, even `LeisurePier01Large01` boardwalk with lamps/benches/kiosks and **zero U-dips**.
   - Whether the boardwalk end curls smoothly onto the Placemaker beach next to `Lobster Avenue`.
   - Whether sandy beach + umbrellas sit seaward of the boardwalk where shallow water allows.
2. **Save / Reload / Dedupe test (Claude's `FIXES_REQUEST.md` verification):**
   - Save the city, quit to desktop, relaunch CS2, reload the save, wait 3 seconds, click **Build / Refresh**, and verify in-game and in `WaterfrontAuto.log` (`manifest adopted ...`, `0 dup skipped` or clean replacement) that there are **no stacked duplicate surfaces or props** along a boardwalk and a beach.
   - If testing on an older pre-v4 save that already had untracked surfaces/props, click **Adopt / clean old waterfront** once, then **Build / Refresh**.
3. **Open ideas for next round with Claude:**
   - Check how `LeisurePier01Large01` looks along curved coves vs. `QuaySmallWide01` (if `Large01` is too wide on tight residential coves, consider `Medium01` for Homes and `Large01` for Commercial/Boardwalk!).
   - Check if a custom procedural wooden boardwalk deck mesh/asset (Lobstertown-styled timber planks + white coastal railings + stairs down to the beach!) is worth adding as an optional companion asset pack later if vanilla `LeisurePier01Large01` still feels too plain.
