// Interchange Studio - Core/Planner.Audit.cs
// A plan checked against the engine rules learned in the game, in pure geometry (each rule cost a real bug):
// no split slivers, gores long enough, pieces under 112 m, sane grades along the whole curve, nothing
// underground by accident, rebuilt one-ways keep their direction, no joints on highway pavement, exact joins,
// ramps not crammed against an existing ramp junction, and no new railway level crossings.
// Started as Testing/PlanChecks.Violations; lives in Core so the game and the tests run the same audit.
using System.Collections.Generic;
using Colossal.Mathematics;
using Unity.Mathematics;

namespace InterchangeStudio.Core
{
    public partial class Planner
    {
        /// <summary>Steepest grade a new piece may have anywhere along it (rise over run).</summary>
        public const float AuditMaxSlope = 0.135f;
        /// <summary>Longest new piece CS2 builds without stretching the mesh.</summary>
        public const float AuditMaxPiece = 112f;
        /// <summary>A new ramp may not meet a highway closer than this to an existing ramp junction on that carriageway.</summary>
        public const float AuditRampSpacing = 45f;

        /// <summary>Every rule the plan breaks, in words (empty when clean). Reads only <paramref name="w"/>, the network before the build.</summary>
        public static List<string> Audit(Preview pv, NetWorld w, bool allowDeadEnds = false, bool allowBelow = false)
        {
            var bad = new List<string>();
            if (pv == null || w == null) return bad;
            var deleted = new HashSet<Entity>();
            foreach (var s in pv.Specs)
            {
                if (!s.Delete) continue;
                deleted.Add(s.Original);
                if (!w.Exists(s.Original)) bad.Add($"deletes {s.Original}, which no longer exists");
            }
            var free = new List<float3>();

            foreach (var s in pv.Specs)
            {
                if (s.Delete) continue;
                bool rampPiece = IsHighwayPrefab(w, s.Prefab);
                for (int k = 0; k < 2; k++)
                {
                    Entity ent = k == 0 ? s.StartEntity : s.EndEntity;
                    float split = k == 0 ? s.StartSplit : s.EndSplit;
                    float3 pos = k == 0 ? s.Curve.a : s.Curve.d;
                    if (ent == Entity.Null) { free.Add(pos); continue; }
                    if (!w.Exists(ent)) { bad.Add($"end refers to a missing {ent}"); continue; }
                    if (!w.HasComponent<Edge>(ent))
                    {
                        if (!w.HasComponent<Node>(ent)) { bad.Add($"end refers to {ent}, which is neither a road piece nor a joint"); continue; }
                        // a node: if a ramp meets the highway there, every highway piece at it must outlast the gore
                        if (!rampPiece) continue;
                        var legs = w.GetBuffer<ConnectedEdge>(ent, true);
                        for (int j = 0; j < legs.Length; j++)
                        {
                            var leg = legs[j].m_Edge;
                            if (deleted.Contains(leg) || !w.HasComponent<Curve>(leg)) continue;
                            float l = w.GetComponentData<Curve>(leg).m_Length;
                            if (IsHighwayPrefab(w, w.GetComponentData<PrefabRef>(leg).m_Prefab) && l < Splits.GoreClear - 0.5f)
                                bad.Add($"a ramp meets the highway at a joint next to a {l:0} m piece (the gore folds it: invalid shape)");
                        }
                        continue;
                    }
                    if (deleted.Contains(ent)) bad.Add($"splits {ent}, which the same build deletes (the split would dangle)");
                    float len = w.GetComponentData<Curve>(ent).m_Length;
                    float fromEnd = math.min(split, 1f - split) * len;
                    if (fromEnd < Splits.MinSplit - 0.5f) bad.Add($"splits {ent} {fromEnd:0.0} m from its end (a sliver under {Splits.MinSplit} m)");
                    else if (rampPiece && IsHighwayPrefab(w, w.GetComponentData<PrefabRef>(ent).m_Prefab) && fromEnd < Splits.GoreClear - 0.5f)
                        bad.Add($"a ramp splits the highway {fromEnd:0} m from a joint (the gore folds that piece: invalid shape)");
                }

                float segLen = MathUtils.Length(s.Curve);
                if (segLen > AuditMaxPiece) bad.Add($"a piece is {segLen:0} m long (over CS2's {AuditMaxPiece:0} m limit, stretches mesh / triggers LongDistance)");
                // grade end to end, then along the curve (an S-shaped profile can be steep in the middle with level ends)
                float run = math.distance(s.Curve.a.xz, s.Curve.d.xz);
                float rise = math.abs(s.Curve.d.y - s.Curve.a.y);
                if (run > 1f && rise / run > AuditMaxSlope) bad.Add($"a piece climbs {rise / run * 100f:0}% ({rise:0.0} m in {run:0} m)");
                else
                {
                    float steepest = 0f, at = 0f;
                    foreach (float t in new[] { 0.25f, 0.5f, 0.75f })
                    {
                        float3 tan = MathUtils.Tangent(s.Curve, t);
                        float h = math.length(tan.xz);
                        if (h < 1e-3f) continue;
                        float g = math.abs(tan.y) / h;
                        if (g > steepest) { steepest = g; at = t; }
                    }
                    if (steepest > AuditMaxSlope)
                        bad.Add($"a piece is {steepest * 100f:0}% steep partway along (at {MathUtils.Position(s.Curve, at)}), though its ends are gentler");
                }
                if (!allowBelow && (s.E0 < -0.01f || s.E1 < -0.01f)) bad.Add("a piece is below ground");
            }

            // a rebuilt one-way piece runs the way the piece it replaces ran (2026-10-23: a misplaced else flipped every lifted piece)
            foreach (var s in pv.Specs)
            {
                if (s.Delete || !(w.PrefabName(s.Prefab) ?? "").Contains("Oneway")) continue;
                float3 m = MathUtils.Position(s.Curve, 0.5f);
                foreach (var old in deleted)
                {
                    if (!w.HasComponent<Curve>(old)) continue;
                    var oc = w.GetComponentData<Curve>(old).m_Bezier;
                    if (MathUtils.Distance(oc.xz, m.xz, out float t) > 2f) continue;
                    if (math.dot(MathUtils.Tangent(oc, t).xz, MathUtils.Tangent(s.Curve, 0.5f).xz) < 0f)
                        bad.Add($"a rebuilt one-way piece at {m} runs against the traffic it replaces");
                    break;
                }
            }

            // a joint between new pieces must not sit on a highway's pavement at its height: the game fuses it into
            // the highway as an extra junction (2026-10-31: a ramp's joint 60 m past the gore, beside the lanes)
            var highways = new List<(Entity e, Bezier4x3 c, float half, float2 lo, float2 hi)>();
            foreach (var e in w.RoadEdges)
            {
                if (deleted.Contains(e)) continue;
                var pf = w.GetComponentData<PrefabRef>(e).m_Prefab;
                if (!IsHighwayPrefab(w, pf)) continue;
                var c = w.GetComponentData<Curve>(e).m_Bezier;
                Box(c, out float2 lo, out float2 hi);
                highways.Add((e, c, AuditWidth(w, pf) * 0.5f, lo, hi));
            }
            foreach (var s in pv.Specs)
            {
                if (s.Delete) continue;
                float half = AuditWidth(w, s.Prefab) * 0.5f;
                for (int k = 0; k < 2; k++)
                {
                    if ((k == 0 ? s.StartEntity : s.EndEntity) != Entity.Null) continue;
                    float3 pos = k == 0 ? s.Curve.a : s.Curve.d;
                    foreach (var h in highways)
                    {
                        float reach = h.half + half;
                        if (pos.x < h.lo.x - reach || pos.x > h.hi.x + reach || pos.z < h.lo.y - reach || pos.z > h.hi.y + reach) continue;
                        float d = MathUtils.Distance(h.c.xz, pos.xz, out float t);
                        if (d < reach - 0.5f && math.abs(MathUtils.Position(h.c, t).y - pos.y) < 4f)
                        { bad.Add($"a joint at {pos} sits on the highway's pavement (the game fuses it in as an extra junction)"); break; }
                    }
                }
            }

            // every free end must meet another piece at exactly the same point
            for (int i = 0; i < free.Count; i++)
            {
                int same = 0, near = 0;
                for (int j = 0; j < free.Count; j++)
                {
                    if (i == j) continue;
                    float d = math.distance(free[i], free[j]);
                    if (d == 0f) same++; else if (d < 1f) near++;
                }
                if (near > 0) bad.Add($"two pieces meet {free[i]} only approximately (the game would not join them)");
                if (same == 0 && !allowDeadEnds) bad.Add($"a new piece ends in mid-air at {free[i]}");
            }

            AuditRampJunctions(pv, w, deleted, bad);
            AuditLevelCrossings(pv, w, deleted, bad);
            return bad;
        }

        /*
         * A new ramp meeting a highway right next to an existing ramp junction on the same carriageway gives
         * weaving traffic no room and the game's gores overlap. Walk the carriageway both ways from where the
         * ramp attaches (through plain two-piece joints) and flag any existing junction of 3+ pieces within 45 m.
         */
        static void AuditRampJunctions(Preview pv, NetWorld w, HashSet<Entity> deleted, List<string> bad)
        {
            var flagged = new HashSet<Entity>();
            foreach (var s in pv.Specs)
            {
                if (s.Delete) continue;
                for (int k = 0; k < 2; k++)
                {
                    Entity ent = k == 0 ? s.StartEntity : s.EndEntity;
                    if (ent == Entity.Null || !w.Exists(ent)) continue;
                    var starts = new List<(Entity node, float dist, Entity via)>();
                    if (w.HasComponent<Edge>(ent))
                    {
                        if (deleted.Contains(ent)) continue;
                        var pf = w.GetComponentData<PrefabRef>(ent).m_Prefab;
                        if (!IsHighwayPrefab(w, pf) || !RampLike(s, pf)) continue;
                        var ed = w.GetComponentData<Edge>(ent);
                        float len = w.GetComponentData<Curve>(ent).m_Length;
                        float t = math.saturate(k == 0 ? s.StartSplit : s.EndSplit);
                        starts.Add((ed.m_Start, t * len, ent));
                        starts.Add((ed.m_End, (1f - t) * len, ent));
                    }
                    else if (w.HasComponent<Node>(ent))
                    {
                        // attaching at a joint: that joint is the attach point itself
                        bool onHighway = false;
                        var legs = w.GetBuffer<ConnectedEdge>(ent, true);
                        for (int j = 0; j < legs.Length; j++)
                        {
                            var leg = legs[j].m_Edge;
                            if (deleted.Contains(leg)) continue;
                            var pf = w.GetComponentData<PrefabRef>(leg).m_Prefab;
                            if (IsHighwayPrefab(w, pf) && RampLike(s, pf)) onHighway = true;
                        }
                        if (!onHighway) continue;
                        starts.Add((ent, 0f, Entity.Null));
                    }
                    else continue;

                    foreach (var st in starts)
                    {
                        Entity node = st.node, via = st.via; float dist = st.dist;
                        for (int hop = 0; hop < 16 && dist < AuditRampSpacing; hop++)
                        {
                            if (!w.HasBuffer<ConnectedEdge>(node)) break;
                            var legs = w.GetBuffer<ConnectedEdge>(node, true);
                            int live = 0; Entity next = Entity.Null;
                            for (int j = 0; j < legs.Length; j++)
                            {
                                var leg = legs[j].m_Edge;
                                if (deleted.Contains(leg)) continue;
                                live++;
                                if (leg != via && IsHighwayPrefab(w, w.GetComponentData<PrefabRef>(leg).m_Prefab)) next = leg;
                            }
                            if (live >= 3)
                            {
                                if (flagged.Add(node))
                                    bad.Add($"a new ramp meets the highway {dist:0} m from an existing ramp junction at {w.GetComponentData<Node>(node).m_Position} (under {AuditRampSpacing:0} m: the gores overlap)");
                                break;
                            }
                            if (live != 2 || next == Entity.Null) break;       // the carriageway ends or changes
                            var ne = w.GetComponentData<Edge>(next);
                            dist += w.GetComponentData<Curve>(next).m_Length;
                            node = ne.m_Start == node ? ne.m_End : ne.m_Start;
                            via = next;
                        }
                    }
                }
            }
        }

        /* a piece that joins a highway as a ramp would (not a rebuilt piece of the highway itself) */
        static bool RampLike(Spec s, Entity highwayPrefab) => s.Group > 0 || s.Prefab != highwayPrefab;

        /*
         * Rail came first: a new road piece must never cross a railway at the same height (a new level crossing).
         * A rebuilt piece that only re-creates a level crossing the build deletes anyway is not a new one.
         */
        static void AuditLevelCrossings(Preview pv, NetWorld w, HashSet<Entity> deleted, List<string> bad)
        {
            if (w.TrackEdges.Count == 0) return;
            var tracks = new List<(Entity e, Bezier4x3 c, float2 lo, float2 hi)>();
            foreach (var e in w.TrackEdges)
            {
                if (deleted.Contains(e)) continue;
                var c = w.GetComponentData<Curve>(e).m_Bezier;
                Box(c, out float2 lo, out float2 hi);
                tracks.Add((e, c, lo, hi));
            }
            // the level crossings the deleted road pieces made: rebuilding one of these is not new
            var old = new List<float3>();
            foreach (var d in deleted)
            {
                if (!w.HasComponent<Curve>(d) || !w.HasComponent<Road>(d)) continue;
                var c = w.GetComponentData<Curve>(d).m_Bezier;
                Box(c, out float2 lo, out float2 hi);
                foreach (var tr in tracks)
                    if (Overlap(lo, hi, tr.lo, tr.hi, 1f))
                        foreach (var x in Crossings(c, tr.c)) if (math.abs(x.ya - x.yb) < 4f) old.Add(x.p);
            }
            var said = new List<float3>();
            foreach (var s in pv.Specs)
            {
                if (s.Delete) continue;
                if (!IsRoadPrefab(w, s.Prefab)) continue;
                Box(s.Curve, out float2 lo, out float2 hi);
                foreach (var tr in tracks)
                {
                    if (!Overlap(lo, hi, tr.lo, tr.hi, 1f)) continue;
                    foreach (var x in Crossings(s.Curve, tr.c))
                    {
                        if (math.abs(x.ya - x.yb) >= 4f) continue;
                        bool rebuilt = false;
                        foreach (var o in old) if (math.distance(o.xz, x.p.xz) < 5f) { rebuilt = true; break; }
                        if (rebuilt) continue;
                        bool dup = false;
                        foreach (var p in said) if (math.distance(p.xz, x.p.xz) < 5f) { dup = true; break; }
                        if (dup) continue;
                        said.Add(x.p);
                        bad.Add($"a new road piece crosses the railway at grade at {x.p} (a new level crossing: the road must go over)");
                    }
                }
            }
        }

        /* where two curves cross in plan (polyline approximation), with each one's height there */
        static List<(float3 p, float ya, float yb)> Crossings(Bezier4x3 a, Bezier4x3 b)
        {
            const int N = 16;
            var found = new List<(float3, float, float)>();
            for (int i = 0; i < N; i++)
            {
                float ta0 = i / (float)N, ta1 = (i + 1) / (float)N;
                float3 a0 = MathUtils.Position(a, ta0), a1 = MathUtils.Position(a, ta1);
                for (int j = 0; j < N; j++)
                {
                    float tb0 = j / (float)N, tb1 = (j + 1) / (float)N;
                    float3 b0 = MathUtils.Position(b, tb0), b1 = MathUtils.Position(b, tb1);
                    if (!SegCross(a0.xz, a1.xz, b0.xz, b1.xz, out float u, out float v)) continue;
                    float3 pa = math.lerp(a0, a1, u), pb = math.lerp(b0, b1, v);
                    found.Add((pa, pa.y, pb.y));
                }
            }
            return found;
        }

        static bool SegCross(float2 p0, float2 p1, float2 q0, float2 q1, out float u, out float v)
        {
            u = v = 0f;
            float2 r = p1 - p0, s = q1 - q0;
            float den = r.x * s.y - r.y * s.x;
            if (math.abs(den) < 1e-6f) return false;
            float2 qp = q0 - p0;
            u = (qp.x * s.y - qp.y * s.x) / den;
            v = (qp.x * r.y - qp.y * r.x) / den;
            return u >= 0f && u < 1f && v >= 0f && v < 1f;
        }

        static void Box(Bezier4x3 c, out float2 lo, out float2 hi)
        {
            lo = math.min(math.min(c.a.xz, c.b.xz), math.min(c.c.xz, c.d.xz));
            hi = math.max(math.max(c.a.xz, c.b.xz), math.max(c.c.xz, c.d.xz));
        }

        static bool Overlap(float2 alo, float2 ahi, float2 blo, float2 bhi, float pad) =>
            alo.x <= bhi.x + pad && blo.x <= ahi.x + pad && alo.y <= bhi.y + pad && blo.y <= ahi.y + pad;

        static bool IsHighwayPrefab(NetWorld w, Entity prefab) =>
            w.HasComponent<RoadData>(prefab) && (w.GetComponentData<RoadData>(prefab).m_Flags & RoadFlags.UseHighwayRules) != 0;

        static bool IsRoadPrefab(NetWorld w, Entity prefab) => w.HasComponent<RoadData>(prefab);

        static float AuditWidth(NetWorld w, Entity prefab) =>
            w.HasComponent<NetGeometryData>(prefab) ? w.GetComponentData<NetGeometryData>(prefab).m_DefaultWidth : 8f;
    }
}
