// Interchange Studio - Core/Planner.Frame.cs
// The per-frame state machine, ported by hand from the old OnUpdate. It is pure: the adapter passes in
// what happened this frame (cursor hit, click, cancel, whether the game would allow the build, what the
// game shows in red) and gets back what to do (close the tool, apply, which preview to draw).
using System;
using System.Collections.Generic;
using Colossal.Mathematics;
using Unity.Mathematics;

namespace InterchangeStudio.Core
{
    public sealed class FrameInput
    {
        public bool HasHit;
        public RaycastHit Hit;
        public bool HasTerrainHit;
        public float3 TerrainPos;
        public bool Apply, Cancel;
        public bool AllowApply;                       // the game's verdict on last frame's preview (no red)
        public List<RedItem> Red = new List<RedItem>();
    }

    public sealed class FrameOutput
    {
        public bool Close;                            // leave the tool
        public bool ApplyNow;                         // build what was previewed last frame
        public Planner.Preview Emit;                  // draw this preview (null: draw nothing)
    }

    public partial class Planner
    {
        public IPlanLog Log { get; private set; } = NullLog.Instance;
        public NetWorld EntityManager { get; private set; }
        FrameInput m_In = new FrameInput();

        public Planner(NetWorld world, TerrainSystem terrain, NameSystem names, IPlanLog log)
        {
            m_TerrainSystem = terrain;
            m_NameSystem = names;
            Log = log ?? NullLog.Instance;
            SetWorld(world);
        }

        /// <summary>Point the planner at a fresh mirror of the network (the adapter rebuilds it when the city changes).</summary>
        public void SetWorld(NetWorld world)
        {
            EntityManager = world;
            m_PrefabSystem = new PrefabSystem(world);
            m_RoadEdges = new EntityQuery(() => world.RoadEdges);
            m_TrackEdges = new EntityQuery(() => world.TrackEdges);
            m_RoadPrefabs = new EntityQuery(() => world.RoadPrefabs);
            m_Oneways.Clear();
            m_GridDirty = true; m_HoverKey = ""; m_PreviewKey = ""; m_SepKey = NoSepKey;
        }

        public bool Stage2Waiting => m_Pending > 0 || m_AutoApply;

        private int m_PendingWait, m_AutoFrames, m_AutoAge;
        private bool m_Parked;     // a two-step build's trimmed ramps, on show until the player clicks or right-clicks

        /// <summary>The status after a build: what was built, in numbers (Planner.Summary.cs).</summary>
        static string BuiltText(Preview built, string what)
        {
            string sum = built == null ? "" : Summarize(built);
            return what + (sum.Length > 0 ? ": " + sum : "") + ". Hover another crossing, or right-click to finish.";
        }

        bool GetRaycastResult(out Entity entity, out RaycastHit hit)
        {
            hit = m_In.Hit; entity = hit.m_HitEntity;
            if (m_In.HasHit && EntityManager.Exists(entity))
            {
                // hovering a joint (node) along a highway or street: resolve to its best connected road piece so previews don't flicker
                if (!EntityManager.HasComponent<Edge>(entity) && EntityManager.HasComponent<Node>(entity))
                {
                    Classify(entity, m_Hw, m_Other, out _);
                    Entity best = Entity.Null; float bd = float.MaxValue;
                    var pool = m_Hw.Count > 0 ? m_Hw : m_Other;
                    foreach (var e in pool)
                    {
                        var cv = EntityManager.GetComponentData<Curve>(e).m_Bezier;
                        float d = MathUtils.Distance(cv.xz, hit.m_HitPosition.xz, out float t);
                        if (d < bd) { bd = d; best = e; hit.m_CurvePosition = t; }
                    }
                    if (best != Entity.Null) { entity = best; hit.m_HitEntity = best; }
                }
                return true;
            }
            // cursor drifted into the median or just off a carriageway: snap within 14 m so the preview stays steady
            if (m_In.HasTerrainHit)
            {
                float2 p = m_In.TerrainPos.xz;
                Entity best = Entity.Null; float bd = 14f, bt = 0.5f; bool bestHw = false;
                foreach (var e in RoadsNear(p - 16f, p + 16f))
                {
                    if (!IsRoadEdge(e)) continue;
                    bool hw = IsHighway(e);
                    var cv = EntityManager.GetComponentData<Curve>(e).m_Bezier;
                    float d = MathUtils.Distance(cv.xz, p, out float t);
                    if (d > 14f) continue;
                    // prefer highways slightly when hovering the median next to a side road
                    if (best == Entity.Null || (hw && !bestHw && d <= bd + 4f) || (hw == bestHw && d < bd))
                    { best = e; bd = d; bt = t; bestHw = hw; }
                }
                if (best != Entity.Null)
                {
                    var cv = EntityManager.GetComponentData<Curve>(best).m_Bezier;
                    entity = best;
                    hit = new RaycastHit { m_HitEntity = best, m_CurvePosition = bt, m_HitPosition = MathUtils.Position(cv, bt) };
                    return true;
                }
            }
            return false;
        }

        public FrameOutput Frame(FrameInput input)
        {
            m_In = input ?? new FrameInput();
            if (m_SummaryOf != null) { m_SummaryOf = null; PreviewSummary = ""; }   // shown again below if a preview still is
            var o = new FrameOutput();
            // an undo preview, once asked for, has the frame to itself (Planner.Undo.cs)
            if (UndoFrame(o)) return o;
            if (m_In.Cancel)
            {
                if (m_Parked)
                {
                    // right-click on the trimmed ramps: drop them, keep the tool open
                    m_Parked = false; Built();
                    StatusKind = 0; StatusText = "The ramps were not built. The bridge stays; hover a crossing, or right-click again to finish.";
                    m_HoldStatus = 120;
                    return o;
                }
                m_Pending = 0; m_PendingWait = 0; m_AutoApply = false; m_AutoFrames = 0; m_AutoAge = 0;
                o.Close = true;
                return o;
            }
            // left-hand traffic: every ramp, merge and one-way the planner draws assumes driving on the right
            if (EntityManager.LeftHandTraffic)
            {
                m_Pending = 0; m_PendingWait = 0; m_AutoApply = false; m_AutoFrames = 0; m_AutoAge = 0; m_Parked = false;
                m_HasPreview = false; m_PreviewKey = ""; m_HoverKey = "";
                NoteSummary(null);
                StatusKind = 2;
                StatusText = "Left-hand traffic cities are not supported yet; Interchange Studio currently plans for right-hand traffic only.";
                return o;
            }
            // second step of a one-click interchange: the ramps were previewed, validate (and autofit/trim if needed) then build
            if (m_AutoApply)
            {
                m_AutoFrames++;
                m_AutoAge++;
                // trust the game's verdict only once it has settled (3 frames), like the red check below
                if (m_HasPreview && m_AutoAge >= 3 && m_In.AllowApply && m_In.Red.Count == 0)
                {
                    m_AutoApply = false;
                    var built = m_Shown ?? m_Preview;
                    if (m_Drop.Count > 0)
                    {
                        // some ramps were left out: never build a partial interchange without the player's say-so
                        m_Parked = true; m_HasPreview = true; m_KeyAge = m_AutoAge;
                        o.Emit = built; NoteSummary(built);
                        int total = built.GroupNames.Count - 1, left = 0;
                        for (int g = 1; g <= total; g++) if (built.Specs.Exists(s => !s.Delete && s.Group == g)) left++;
                        StatusKind = 2;
                        StatusText = $"The bridge is built, but only {left} of {total} ramps fit; the rest run into something. Click to build those {left}, or right-click to leave the ramps out.";
                        SafeLog($"Ramps after the bridge: only {left} of {total} fit, waiting for the player: " + built.Log);
                        return o;
                    }
                    o.ApplyNow = true;
                    SafeLog("Built: " + built.Log);
                    RecordUndo(built, LabelFor(m_PendingMode) + " ramps");
                    StatusKind = 3;
                    m_Renames.AddRange(built.Names); m_RenameFrames = 12;
                    StatusText = BuiltText(built, "Ramps built");
                    Built();
                    return o;
                }
                if (!m_HasPreview || m_AutoFrames > 70)
                {
                    m_AutoApply = false;
                    Log.Warn("Bridge built, ramps not: " + (m_HasPreview ? "they collide with something" : "none could be planned"));
                    StatusKind = 2;
                    StatusText = "The bridge is built, but the ramps " + (m_HasPreview ? "collide with something" : "couldn't be planned") + ". Hover the crossing to see why.";
                    Built();
                    return o;
                }
                // wait 3 frames for CS2's red verdict to settle, then let autofit/trim resolve minor ramp collisions automatically
                if (m_AutoAge >= 3 && (!m_In.AllowApply || m_In.Red.Count > 0))
                {
                    m_KeyAge = m_AutoAge;
                    string red = Blocked();
                    if (OnRed())
                    {
                        m_AutoAge = 0;
                        var lifted = FindSeparated(m_PendingPos, true);
                        var retry = lifted.Count > 0 ? WithFit(() => PreviewFor(m_PendingMode, lifted, m_PendingPos), m_FitVariant) : null;
                        if (retry != null && retry.Specs.Count > 0)
                        {
                            JoinPieces(retry);
                            m_Preview = retry;
                            var shown = m_Drop.Count > 0 ? Trimmed(retry, m_Drop) : retry;
                            bool any = shown.Specs.Exists(s => !s.Delete);
                            m_Shown = shown; m_HasPreview = any;
                            if (any) { o.Emit = shown; NoteSummary(shown); return o; }
                        }
                    }
                    m_AutoApply = false;
                    Log.Warn("Bridge built, ramps not: they collide with something" + (red.Length > 0 ? " -" + red : ""));
                    StatusKind = 2;
                    StatusText = "The bridge is built, but the ramps collide with something." + (red.Length > 0 ? red : " Hover the crossing to see why.");
                    Built();
                    return o;
                }
                var cur = m_Shown ?? m_Preview;
                if (cur != null && cur.Specs.Exists(s => !s.Delete)) { o.Emit = cur; NoteSummary(cur); }
                return o;
            }
            // the trimmed ramps of a two-step build stay on show (wherever the cursor goes) until a click or right-click
            if (m_Parked)
            {
                var cur = m_Shown ?? m_Preview;
                if (cur == null || !StillValid(cur) || !cur.Specs.Exists(s => !s.Delete)) { m_Parked = false; m_HasPreview = false; }
                else if (!m_In.Apply)
                {
                    m_HasPreview = true; m_KeyAge++;
                    o.Emit = cur; NoteSummary(cur);
                    string red = Blocked();
                    if (red.Length > 0) { StatusKind = 2; StatusText = "These ramps run into something now." + red + " Right-click to leave them out."; }
                    return o;
                }
            }
            // autofit just switched layouts: the game hasn't judged this one yet, so a click now would build it blind
            bool stillChecking = m_In.Apply && m_HasPreview && !m_Parked && AutofitActive() && m_FitVariant > 0 && m_KeyAge < 3;
            if (m_In.Apply && m_HasPreview && !stillChecking)
            {
                if (m_In.AllowApply)
                {
                    var built = m_Shown ?? m_Preview;
                    o.ApplyNow = true;
                    SafeLog("Built: " + built.Log);
                    RecordUndo(built, m_Parked ? LabelFor(m_PendingMode) + " ramps" : LabelFor(Mode) + (m_Preview.NextStep ? " bridge" : ""));
                    StatusKind = 3;
                    m_Renames.AddRange(m_Preview.Names); m_RenameFrames = 12;
                    if (m_Preview.NextStep && !m_Parked) { m_PendingFit = m_FitVariant; m_Pending = 1; m_PendingWait = 0; m_PendingPos = m_Preview.NextPos; m_PendingMode = m_Preview.NextMode; StatusText = "Bridge built. Adding the ramps..."; }
                    else StatusText = BuiltText(built, m_Parked ? "Ramps built" : "Built");
                    m_Parked = false;
                }
                else
                {
                    Log.Warn("Not built: the preview collides with something");
                    StatusKind = 2;
                    string red = Blocked();
                    StatusText = "Can't build: something is in the way." + (red.Length > 0 ? red : " (Shown in red.)");
                }
                Built();
                return o;
            }
            m_HasPreview = false;
            if (m_HoldStatus > 0) m_HoldStatus--;
            try
            {
                Preview pv;
                if (m_Pending > 0)
                {
                    m_PendingWait++;
                    if (m_PendingWait < 6) return o;
                    var lifted = FindSeparated(m_PendingPos, true);
                    if (lifted.Count == 0)
                    {
                        if (m_PendingWait < 20) return o;
                        m_Pending = 0; m_PendingWait = 0;
                        StatusText = "The bridge is built, but I lost track of it. Hover it to add the ramps.";
                        StatusKind = 2;
                        Log.Info("Ramps after the bridge: bridge not found");
                        m_HoldStatus = 240;
                        return o;
                    }
                    m_Pending = 0; m_PendingWait = 0;
                    m_HoverPos = m_PendingPos;
                    ResetTrim(); m_FitBase = "stage2"; m_FitVariant = m_PendingFit; m_PreviewKey = "stage2|v" + m_FitVariant; m_BlockKey = "";
                    pv = WithFit(() => PreviewFor(m_PendingMode, lifted, m_PendingPos), m_PendingFit);
                    if (pv == null || pv.Specs.Count == 0)
                    {
                        StatusText = "The bridge is built, but no ramps: " + (pv?.Status ?? "couldn't plan ramps");
                        StatusKind = 2;
                        Log.Info("Ramps after the bridge: " + (pv?.Log ?? "none"));
                        m_HoldStatus = 240;
                        return o;
                    }
                    m_AutoApply = true; m_AutoFrames = 0; m_AutoAge = 0;
                }
                else { pv = HoverPreview(); FitAfterFailure(pv); }
                if (m_HoldStatus <= 0) StatusKind = pv == null ? 0 : pv.Specs.Count == 0 ? 2 : 1;
                if (pv != null && pv.Specs.Count > 0)
                {
                    JoinPieces(pv);
                    m_Preview = pv; m_HasPreview = true;
                    var shown = m_Drop.Count > 0 ? Trimmed(pv, m_Drop) : pv;     // less any ramps left out (Planner.Trim.cs)
                    bool any = shown.Specs.Exists(s => !s.Delete);
                    m_Shown = shown; m_HasPreview = any;
                    if (any) o.Emit = shown;
                    NoteSummary(any ? shown : null);
                    string red = Blocked();
                    if ((red.Length > 0 || !any) && m_HoldStatus <= 0) StatusKind = 2;
                    if (red.Length > 0 && OnRed()) { }
                    else Say((AutofitActive() && m_FitVariant > 0 && red.Length == 0 && m_Drop.Count == 0
                            ? (m_KeyAge < 3 ? $"Autofit: checking layout {m_FitVariant + 1}... " : $"Autofit found a clean layout (try {m_FitVariant + 1}). ") : "")
                        + shown.Status + (red.Length > 0 ? " The bridge or street changes run into something, so this can't be built." : "") + red);
                }
            }
            catch (Exception e)
            {
                Log.Error(e, "Interchange tool");
                m_HasPreview = false; m_PreviewKey = "";
                StatusText = "Something went wrong here (details in the log). Try another spot.";
            }
            if (stillChecking && m_HasPreview && m_HoldStatus <= 0)
            {
                StatusKind = 1;
                StatusText = $"Still checking layout {m_FitVariant + 1}... the game hasn't judged it yet. Click again in a moment.";
            }
            return o;
        }

        /// <summary>Road names to restore, once the game has settled after a build (call from the UI update); null when not yet.</summary>
        public List<(float3 pos, string name, bool highway)> TakeRenames()
        {
            if (m_RenameFrames <= 0 || --m_RenameFrames > 0) return null;
            var list = new List<(float3, string, bool)>(m_Renames);
            m_Renames.Clear();
            return list;
        }

        /// <summary>The game drew parts of the preview in red: say which ones and where (from the adapter's red list).</summary>
        string Blocked()
        {
            if (m_KeyAge < 3 || m_In.Red.Count == 0) return "";
            if (m_BlockKey == m_PreviewKey) return m_BlockText;
            m_BlockKey = m_PreviewKey;
            var parts = new List<string>(); var log = new List<string>();
            foreach (var r in m_In.Red)
            {
                if (!NearPreview(r.At)) continue;
                float3 d = r.At - m_HoverPos; float dist = math.length(d.xz);
                string where = dist < 15f ? "right at the crossing" : $"{(int)dist} m {Compass(d)} of the cursor";
                log.Add($"{r.What} at {r.At} ({where})");
                string part = $"{r.What} {where}";
                if (!parts.Contains(part) && parts.Count < 3) parts.Add(part);
            }
            if (parts.Count == 0) { m_BlockText = ""; return ""; }
            SafeLog($"Red in the preview ({log.Count}): " + string.Join("; ", log));
            m_BlockText = $" Shown in red: {string.Join("; ", parts)}." + (AutofitActive() ? "" : " Anarchy would force it through, but it may not work well; try another style or setting.");
            return m_BlockText;
        }

        /// <summary>The next at-grade highway or railway crossing to fix, nearest to <paramref name="from"/>; sets the status. Null when there are none.</summary>
        public float3? FindNextTarget(float3 from)
        {
            try
            {
                var nodes = new HashSet<Entity>();
                using (var ents = m_RoadEdges.ToEntityArray(Allocator.Temp))
                    foreach (var e in ents)
                    {
                        if (!Live(e)) continue;
                        var ed = EntityManager.GetComponentData<Edge>(e);
                        nodes.Add(ed.m_Start); nodes.Add(ed.m_End);
                    }
                var found = new List<(Entity n, bool rail)>();
                foreach (var n in nodes)
                {
                    if (!Live(n) || !EntityManager.HasComponent<Node>(n)) continue;
                    if (RailCount(n) > 0) { Classify(n, m_Hw, m_Other, out _); if (m_Hw.Count + m_Other.Count >= 2) found.Add((n, true)); }
                    else if (IsCrossing(n) && !IsTerminal(n)) found.Add((n, false));
                }
                int rails = 0; foreach (var f in found) if (f.rail) rails++;
                m_HoldStatus = 400;
                if (found.Count == 0)
                {
                    StatusText = "Nothing left to fix: every highway crossing and railway crossing is grade-separated.";
                    Log.Info("Find next: no at-grade crossings left");
                    return null;
                }
                m_Visited.RemoveAll(v => !Live(v));
                if (found.TrueForAll(f => m_Visited.Contains(f.n))) m_Visited.Clear();
                (Entity n, bool rail) pick = default; float bd = float.MaxValue;
                foreach (var f in found)
                {
                    if (m_Visited.Contains(f.n)) continue;
                    float d = math.distance(NodePos(f.n).xz, from.xz);
                    if (d < bd) { bd = d; pick = f; }
                }
                m_Visited.Add(pick.n);
                float3 at = NodePos(pick.n);
                int hw = found.Count - rails;
                StatusText = $"Left to fix: {hw} at-grade highway crossing{(hw == 1 ? "" : "s")} and {rails} railway level crossing{(rails == 1 ? "" : "s")}. "
                    + $"The camera is on a {(pick.rail ? "railway level crossing" : "highway crossing")}: hover it to fix it, or press Find next for another.";
                Log.Info($"Find next: {hw} highway and {rails} railway crossing(s) at grade; showing {(pick.rail ? "railway" : "highway")} crossing at {at}");
                return at;
            }
            catch (Exception e)
            {
                Log.Error(e, "Find next crossing");
                StatusText = "Couldn't search for crossings (details in the log).";
                return null;
            }
        }

        /// <summary>Forget the current preview (the tool was switched on, or a setting changed).</summary>
        public void Reset() { m_HasPreview = false; m_PreviewKey = ""; m_HoverKey = ""; }

        /// <summary>
        /// Drop everything unfinished: the ramps a two-step build would still add, an automatic apply, leftover
        /// ramps and the autofit layout. For closing or reopening the tool and for a settings change, so nothing
        /// planned earlier (elsewhere, with other settings) can build later (GPT's review of the old mod, 2026-10-30).
        /// </summary>
        public void Abandon()
        {
            m_Pending = 0; m_PendingWait = 0; m_AutoApply = false; m_AutoFrames = 0; m_AutoAge = 0; m_Parked = false;
            ResetTrim(); m_FitBase = ""; m_FitVariant = 0;
            // an undo preview on show goes too (the history stays). One asked for but not yet shown survives: the
            // panel may ask for it just before switching the tool on, and switching it on calls Abandon.
            m_UndoActive = false; m_UndoPv = null;
            Reset();
        }
    }
}
