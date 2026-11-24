// Interchange Studio - Core/Planner.Undo.cs
// Undo for builds, up to the last five. Each build is remembered as geometry, not entity ids (the game gives
// every new and split piece a fresh id): what it deleted (every piece in full, with its name), which pieces it
// split, and where each new piece lies. Undo finds the new pieces again in the live network, deletes them,
// and puts the old pieces back (rejoined to the joints still there). It is shown as a preview first, so the
// game checks it for collisions and the player confirms it with a click (right-click cancels).
using System.Collections.Generic;
using Colossal.Mathematics;
using Unity.Mathematics;

namespace InterchangeStudio.Core
{
    public partial class Planner
    {
        const int UndoDepth = 5;
        const float UndoMatchMid = 2f, UndoMatchEnd = 3f, UndoJoint = 1f;

        /// <summary>A road piece as it was before a build: enough to build it again.</summary>
        sealed class OldPiece
        {
            public Bezier4x3 Curve; public Entity Prefab, StartEntity, EndEntity; public float E0, E1;
            public bool HasUpgrade; public CompositionFlags Upgrade; public string Name; public bool IsHighway;
            public bool Split;      // the build split it rather than deleted it (its halves are found and replaced)
        }

        /// <summary>Where a build's new piece lies, to find it again after the game gave it an id.</summary>
        struct NewPiece { public float3 Mid, A, D; public Entity Prefab; }

        sealed class UndoRecord
        {
            public string Label = "";
            public readonly List<OldPiece> Old = new List<OldPiece>();
            public readonly List<NewPiece> New = new List<NewPiece>();
        }

        readonly List<UndoRecord> m_Undo = new List<UndoRecord>();     // newest last
        bool m_UndoQueued;           // asked for; the preview is worked out on the next frames (the mirror may lag a build)
        bool m_UndoActive;           // the undo preview is showing, waiting for a click
        int m_UndoWait, m_UndoAge;
        Preview m_UndoPv;
        int m_UndoFound, m_UndoRestored;

        /// <summary>There is a build to undo (not while the ramps of a two-step build are still on their way).</summary>
        public bool CanUndo => m_Undo.Count > 0 && !Stage2Waiting;

        /// <summary>What the undo button would undo, e.g. "Undo Diamond" ("" when there is nothing).</summary>
        public string UndoLabel => m_Undo.Count > 0 ? "Undo " + m_Undo[m_Undo.Count - 1].Label : "";

        /// <summary>The undo preview is showing (or being worked out), waiting for the player's click.</summary>
        public bool UndoPreviewing => m_UndoQueued || m_UndoActive;

        /// <summary>
        /// Show the undo of the latest build as a preview: one click builds it, right-click cancels. True when it
        /// was queued; false when there is nothing to undo. The tool must be active for the preview to show.
        /// </summary>
        public bool RequestUndo()
        {
            if (!CanUndo) return false;
            m_Pending = 0; m_PendingWait = 0; m_AutoApply = false; m_Parked = false;
            m_UndoQueued = true; m_UndoActive = false; m_UndoWait = 0; m_UndoAge = 0; m_UndoPv = null;
            m_HasPreview = false; m_PreviewKey = ""; m_HoverKey = "";
            StatusKind = 1; StatusText = "Getting the undo ready...";
            return true;
        }

        /// <summary>Put away the undo preview; the undo history is kept.</summary>
        public void CancelUndo()
        {
            if (!UndoPreviewing) return;
            m_UndoQueued = false; m_UndoActive = false; m_UndoPv = null;
            StatusKind = 0; StatusText = "Undo cancelled. Nothing was changed.";
            m_HoldStatus = 120;
        }

        static string LabelFor(ToolMode m)
        {
            switch (m)
            {
                case ToolMode.Overpass: return "Overpass";
                case ToolMode.Exit: return "Diamond";
                case ToolMode.Spui: return "Single-point";
                case ToolMode.Dumbbell: return "Dumbbell";
                case ToolMode.Frontage: return "Frontage";
                case ToolMode.Auto: return "Interchange";
                case ToolMode.Ending: return "Highway ending";
                case ToolMode.Repair: return "Repair";
                default: return "build";
            }
        }

        /// <summary>Remember a build that is being applied now (call before the network changes).</summary>
        void RecordUndo(Preview built, string label)
        {
            if (built == null) return;
            try
            {
                var rec = new UndoRecord { Label = label };
                var seen = new HashSet<Entity>();
                foreach (var s in built.Specs)
                {
                    if (s.Delete) { if (seen.Add(s.Original)) Remember(rec, s.Original, false); continue; }
                    rec.New.Add(new NewPiece { Mid = MathUtils.Position(s.Curve, 0.5f), A = s.Curve.a, D = s.Curve.d, Prefab = s.Prefab });
                }
                // pieces the new ends split: the game replaces each with two halves, which undo puts back as one
                foreach (var s in built.Specs)
                {
                    if (s.Delete) continue;
                    foreach (var ent in new[] { s.StartEntity, s.EndEntity })
                        if (ent != Entity.Null && EntityManager.Exists(ent) && EntityManager.HasComponent<Edge>(ent) && seen.Add(ent))
                            Remember(rec, ent, true);
                }
                if (rec.New.Count == 0 && rec.Old.Count == 0) return;
                m_Undo.Add(rec);
                while (m_Undo.Count > UndoDepth) m_Undo.RemoveAt(0);
            }
            catch (System.Exception e) { Log.Error(e, "Recording the undo"); }
        }

        void Remember(UndoRecord rec, Entity edge, bool split)
        {
            if (!EntityManager.Exists(edge) || !EntityManager.HasComponent<Curve>(edge)) return;
            var ed = EntityManager.GetComponentData<Edge>(edge);
            var old = new OldPiece
            {
                Curve = EntityManager.GetComponentData<Curve>(edge).m_Bezier, Prefab = PrefabOf(edge),
                StartEntity = ed.m_Start, EndEntity = ed.m_End,
                E0 = EntityManager.Exists(ed.m_Start) ? NodeElevation(ed.m_Start) : 0f,
                E1 = EntityManager.Exists(ed.m_End) ? NodeElevation(ed.m_End) : 0f,
                HasUpgrade = EntityManager.HasComponent<Upgraded>(edge), Name = NameOf(edge), IsHighway = IsHighway(edge), Split = split,
            };
            if (old.HasUpgrade) old.Upgrade = EntityManager.GetComponentData<Upgraded>(edge).m_Flags;
            rec.Old.Add(old);
        }

        /*
         * The undo of a build, against the network as it is now: delete the pieces it built (and the halves of
         * pieces it split), build the old pieces again. found/expected say how many built pieces were found.
         */
        Preview UndoPreview(UndoRecord rec, out int found, out int restored)
        {
            var pv = new Preview();
            var gone = new HashSet<Entity>();
            var healed = new HashSet<OldPiece>();
            found = 0; restored = 0;

            foreach (var np in rec.New)
            {
                float2 lo = math.min(np.A.xz, np.D.xz) - 8f, hi = math.max(np.A.xz, np.D.xz) + 8f;
                lo = math.min(lo, np.Mid.xz - 8f); hi = math.max(hi, np.Mid.xz + 8f);
                Entity best = Entity.Null; float bd = float.MaxValue;
                foreach (var e in RoadsNear(lo, hi))
                {
                    if (gone.Contains(e) || !IsRoadEdge(e) || PrefabOf(e) != np.Prefab) continue;
                    var c = EntityManager.GetComponentData<Curve>(e).m_Bezier;
                    float dm = math.distance(MathUtils.Position(c, 0.5f), np.Mid);
                    if (dm > UndoMatchMid) continue;
                    float fwd = math.max(math.distance(c.a, np.A), math.distance(c.d, np.D));
                    float rev = math.max(math.distance(c.a, np.D), math.distance(c.d, np.A));
                    float de = math.min(fwd, rev);
                    if (de > UndoMatchEnd) continue;
                    if (dm + de < bd) { bd = dm + de; best = e; }
                }
                if (best == Entity.Null) continue;
                gone.Add(best); found++;
                pv.Specs.Add(new Spec { Delete = true, Original = best });
            }
            // halves of the pieces the build split: live pieces of the same road type lying along the old curve
            foreach (var old in rec.Old)
            {
                if (!old.Split) continue;
                Box(old.Curve, out float2 lo, out float2 hi);
                var halves = new List<Entity>();
                foreach (var e in RoadsNear(lo - 4f, hi + 4f))
                {
                    if (gone.Contains(e) || !IsRoadEdge(e) || PrefabOf(e) != old.Prefab) continue;
                    var c = EntityManager.GetComponentData<Curve>(e).m_Bezier;
                    if (OnCurve(old.Curve, c.a) && OnCurve(old.Curve, c.d) && OnCurve(old.Curve, MathUtils.Position(c, 0.5f))) halves.Add(e);
                }
                // nothing (or one piece: not split after all, or already healed) to heal
                if (halves.Count < 2) continue;
                // heal only when every joint between the halves is left with nothing else (a ramp not found still uses it)
                var mine = new HashSet<Entity>(halves); mine.UnionWith(gone);
                bool free = true;
                foreach (var e in halves)
                {
                    var ed = EntityManager.GetComponentData<Edge>(e);
                    foreach (var n in new[] { ed.m_Start, ed.m_End })
                    {
                        if (math.distance(NodePos(n), old.Curve.a) < UndoJoint || math.distance(NodePos(n), old.Curve.d) < UndoJoint) continue;
                        if (Keeps(n, mine)) free = false;
                    }
                }
                if (!free) continue;
                healed.Add(old);
                foreach (var e in halves) { gone.Add(e); pv.Specs.Add(new Spec { Delete = true, Original = e }); }
            }
            // the old pieces again, rejoined to the joints that stay
            foreach (var old in rec.Old)
            {
                if (old.Split && !healed.Contains(old)) continue;     // its halves were not found or are still in use: leave them be
                var spec = new Spec
                {
                    Prefab = old.Prefab, Curve = old.Curve, E0 = old.E0, E1 = old.E1, HasUpgrade = old.HasUpgrade, Upgrade = old.Upgrade,
                };
                ReattachEnd(spec, old.StartEntity, old.Curve.a, gone, true);
                ReattachEnd(spec, old.EndEntity, old.Curve.d, gone, false);
                pv.Specs.Add(spec);
                restored++;
                if (!string.IsNullOrEmpty(old.Name)) pv.Names.Add((MathUtils.Position(old.Curve, 0.5f), old.Name, old.IsHighway));
            }
            JoinPieces(pv);
            pv.Status = $"Undo preview: restores {restored} original piece{(restored == 1 ? "" : "s")} and removes {found} built piece{(found == 1 ? "" : "s")}"
                + (found < rec.New.Count ? $" ({rec.New.Count - found} built piece{(rec.New.Count - found == 1 ? " was" : "s were")} changed since and stay{(rec.New.Count - found == 1 ? "s" : "")})" : "")
                + ". Click to undo, or right-click to cancel.";
            pv.Log = $"undo {rec.Label}: delete {found}/{rec.New.Count} built, restore {restored}";
            return pv;
        }

        static bool OnCurve(Bezier4x3 curve, float3 p) =>
            MathUtils.Distance(curve.xz, p.xz, out float t) < 1.5f && math.abs(MathUtils.Position(curve, t).y - p.y) < 1.5f;

        /*
         * Join an old piece's end to what is there now: its own joint if it is still there and keeps another piece,
         * else a joint at the same spot, else a road piece passing through the spot (split there), else a free end
         * (JoinPieces welds the free ends of the old pieces to each other).
         */
        void ReattachEnd(Spec spec, Entity node, float3 pos, HashSet<Entity> gone, bool start)
        {
            Entity ent = Entity.Null; float split = 0f;
            if (Live(node) && EntityManager.HasComponent<Node>(node) && math.distance(NodePos(node), pos) < UndoJoint && Keeps(node, gone))
                ent = node;
            else
            {
                float bd = UndoJoint;
                foreach (var e in RoadsNear(pos.xz - 8f, pos.xz + 8f))
                {
                    if (gone.Contains(e) || !IsRoadEdge(e)) continue;
                    var ed = EntityManager.GetComponentData<Edge>(e);
                    foreach (var n in new[] { ed.m_Start, ed.m_End })
                    {
                        if (!Live(n)) continue;
                        float d = math.distance(NodePos(n), pos);
                        if (d < bd && Keeps(n, gone)) { bd = d; ent = n; split = 0f; }
                    }
                }
                if (ent == Entity.Null)
                    foreach (var e in RoadsNear(pos.xz - 8f, pos.xz + 8f))
                    {
                        if (gone.Contains(e) || !IsRoadEdge(e)) continue;
                        var c = EntityManager.GetComponentData<Curve>(e).m_Bezier;
                        if (MathUtils.Distance(c.xz, pos.xz, out float t) > 0.5f || math.abs(MathUtils.Position(c, t).y - pos.y) > 1f) continue;
                        float len = EntityManager.GetComponentData<Curve>(e).m_Length;
                        if (math.min(t, 1f - t) * len < Splits.MinSplit - 0.5f) continue;    // would leave a sliver
                        ent = e; split = t; break;
                    }
            }
            if (start) { spec.StartEntity = ent; spec.StartSplit = split; }
            else { spec.EndEntity = ent; spec.EndSplit = split; }
        }

        /* a joint survives the undo: at least one of its pieces is not deleted by it */
        bool Keeps(Entity node, HashSet<Entity> gone)
        {
            if (!EntityManager.HasBuffer<ConnectedEdge>(node)) return false;
            var legs = EntityManager.GetBuffer<ConnectedEdge>(node, true);
            for (int i = 0; i < legs.Length; i++) if (!gone.Contains(legs[i].m_Edge)) return true;
            return false;
        }

        /*
         * The undo, frame by frame (called from Frame before anything else once undo is asked for). Returns true
         * when it handled the frame.
         */
        bool UndoFrame(FrameOutput o)
        {
            if (!UndoPreviewing) return false;
            if (m_In.Cancel) { CancelUndo(); return true; }
            if (m_Undo.Count == 0) { m_UndoQueued = m_UndoActive = false; return false; }
            var rec = m_Undo[m_Undo.Count - 1];

            if (m_UndoActive && m_In.Apply)
            {
                if (m_UndoAge < 3) { StatusKind = 1; StatusText = "Still checking the undo... click again in a moment."; }
                else if (m_In.AllowApply && m_UndoPv != null && StillValid(m_UndoPv))
                {
                    o.ApplyNow = true;
                    SafeLog("Undone: " + m_UndoPv.Log);
                    m_Undo.RemoveAt(m_Undo.Count - 1);
                    m_Renames.AddRange(m_UndoPv.Names); m_RenameFrames = 12;
                    StatusKind = 3;
                    StatusText = $"Undone {rec.Label}: removed {m_UndoFound} built piece{(m_UndoFound == 1 ? "" : "s")} and restored {m_UndoRestored} original piece{(m_UndoRestored == 1 ? "" : "s")}.";
                    m_UndoQueued = m_UndoActive = false; m_UndoPv = null;
                    Built();
                    return true;
                }
                else
                {
                    StatusKind = 2;
                    string red = Blocked();
                    StatusText = "Can't undo: something is in the way." + (red.Length > 0 ? red : " (Shown in red.)") + " Right-click to cancel.";
                    if (m_UndoPv != null) o.Emit = m_UndoPv;
                    return true;
                }
            }

            // work out (or refresh) the preview: wait a little for the mirror to catch up with a build just made
            if (m_UndoPv == null || !StillValid(m_UndoPv))
            {
                var pv = UndoPreview(rec, out int found, out int restored);
                if (found < rec.New.Count && m_UndoWait++ < 30) { StatusKind = 1; StatusText = "Getting the undo ready..."; return true; }
                if (pv.Specs.Count == 0)
                {
                    m_Undo.RemoveAt(m_Undo.Count - 1);
                    m_UndoQueued = m_UndoActive = false; m_UndoPv = null;
                    StatusKind = 2; StatusText = $"Can't undo {rec.Label}: the pieces it built have been changed or removed since."; m_HoldStatus = 240;
                    Log.Info("Undo: nothing left to undo for " + rec.Label);
                    return true;
                }
                m_UndoPv = pv; m_UndoFound = found; m_UndoRestored = restored; m_UndoAge = 0;
                m_PreviewKey = "undo|" + m_Undo.Count; m_KeyAge = 0; m_BlockKey = "";
                m_Preview = pv; m_Shown = pv;
                LogOnce("Undo preview: " + pv.Log);
            }
            m_UndoQueued = false; m_UndoActive = true;
            m_UndoAge++; m_KeyAge = m_UndoAge;
            o.Emit = m_UndoPv;
            m_SummaryOf = m_UndoPv;                // cleared at the top of the next frame, set again here while it shows
            PreviewSummary = $"Undo {rec.Label}: {m_UndoFound} built piece{(m_UndoFound == 1 ? "" : "s")} out, {m_UndoRestored} original piece{(m_UndoRestored == 1 ? "" : "s")} back";
            StatusKind = 1;
            StatusText = m_UndoPv.Status + (m_UndoAge >= 3 ? Blocked() : "");
            return true;
        }
    }
}
