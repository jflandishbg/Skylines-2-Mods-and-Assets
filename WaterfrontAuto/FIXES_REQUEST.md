# WaterfrontAuto v4: two fixes requested by Claude (review of v3)

Read `CLAUDE_HANDOFF.md` first. Back up every file you touch as `<name>.pre_v4.cs` before editing. Keep everything vanilla, no custom ECS components, 0 ms/frame idle. Do not break the invariants in the handoff (system order, no `Updated` watch, maritime and road safety).

## Fix 1: no duplicate surfaces or props after save and reload

Problem: `m_OwnedEdges/Areas/Objects` live in memory only. After a reload they are empty, the building fingerprint uses `Entity.Index` so the first pass always rebuilds, and `ScanNets` is the only scan of existing content. Quays are detected and skipped, but surfaces (Areas) and props (Objects) from the earlier session are not, so a second copy is emitted on top of the first. Each save and reload can stack another copy. Clear and Rebuild also cannot remove the old ones.

Do both of these:

A. Manifest and adopt on load.
- On every capture (`CaptureCreatedEntities`) and after every Clear, write `ModsData\WaterfrontAuto\manifest-<cityKey>.txt`, one row per owned entity: `kind|prefabName|x|z` (kind = E, A or O; x and z rounded to 0.1 m; edge position = Bezier midpoint, area = node centroid, object = transform position). `cityKey` = save/city name from the game (fall back to map name, then `default`). Write to a temp file and move over the old one.
- In `OnGameLoadingComplete`, after the warmup frames and before the first plan, read the manifest. For each row find the live entity with the same prefab name (via `PrefabRef` and `PrefabSystem`) and position within 0.5 m. Add matches to the owned sets. Drop rows with no match. Then the existing first rebuild clears and rebuilds them cleanly, with no stacking.

B. Dedupe on emit, as a fallback for saves with no manifest (anything built by v2 or v3).
- Before queuing a planned surface or prop, scan live non-`Temp`, non-`Deleted` Area and Object entities that use the same prefab. Skip the planned item if one already sits within 0.5 m (areas, by centroid) or 1.0 m (objects). Build the lookup once per pass with a spatial hash, not a nested loop.
- Log how many were skipped as duplicates.

Add a panel button "Adopt/clean old waterfront" that runs the manifest-less dedupe once and reports how many untracked items it found.

## Fix 3: tighter ownership matching

Problem: `CaptureCreatedEntities` claims any `Created` edge within 4 m, area within 5 m, or object within 2 m of any planned item. In a busy area it can claim another mod's or a vanilla entity, and Clear would then delete it.

Change the matching to this:
- Each pending entry stores the expected prefab entity (or prefab name) next to its position. A created entity is claimed only if its `PrefabRef` equals that prefab.
- Tighten the distance to 1.0 m (edges, by curve midpoint), 1.0 m (areas, by centroid) and 0.5 m (objects).
- Each pending entry is consumed once. Remove it from the pending list when matched, so one planned item cannot claim two entities.
- Do not claim entities that have an `Owner` component, or that have `Temp`.
- Log any pending entries left unmatched after the capture. That tells us if the tolerance is too tight.

## Tests and report

- Move the matching rules (prefab equality, tolerance, consume-once, dedupe) into `Core` as pure functions so the offline tests can cover them. Add tests for: two planned items near each other, an unrelated entity with a different prefab nearby, a duplicate surface already present, and a manifest row with no live match.
- Build and run the tests with the commands in the handoff. Report pass counts.
- Update `CLAUDE_HANDOFF.md` with what changed, the backups, and what the author should test in game: save, quit, reload, press Rebuild, then check for stacked surfaces and props along a boardwalk and a beach.
