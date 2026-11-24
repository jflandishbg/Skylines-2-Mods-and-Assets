// Interchange Studio - Core/Planner.Ending.cs
// Highway end transition: merges two parallel opposing one-way highway dead ends cleanly into a single
// two-way road (two-way highway, Medium Road, Large Road, or Avenue), preserving traffic direction and
// smoothly ramping down if the highway ends are elevated.
using System.Collections.Generic;
using Colossal.Mathematics;
using Unity.Mathematics;

namespace InterchangeStudio.Core
{
    public partial class Planner
    {
        struct HighwayDeadEnd
        {
            public Entity Node, Edge;
            public float3 Pos, OutDir;
            public bool Arriving;          // true: traffic enters this dead end (edge.m_End == Node); false: departs
            public float Elevation;
        }

        /// <summary>Road prefab for the combined two-way road at a highway end (0 two-way hwy, 1 medium, 2 large, 3 avenue).</summary>
        Entity EndingRoadPrefab(out string label)
        {
            string[] wanted = EndRoad == 0
                ? new[] { "Highway Twoway - 4 lanes", "Highway Twoway - 2 lanes", "Large Road" }
                : EndRoad == 1 ? new[] { "Medium Road", "Large Road" }
                : EndRoad == 3 ? new[] { "Large Road Divided", "Medium Road Divided", "XL Road Divided", "Large Road" }
                : new[] { "Large Road", "Medium Road" };
            foreach (var name in wanted)
            {
                var p = Named(name, "Highway end");
                if (p != Entity.Null)
                {
                    label = EndRoad == 3 && !name.Contains("Divided") ? "Large Road (no avenue type found)" : name;
                    return p;
                }
            }
            label = "";
            return Entity.Null;
        }

        bool TryDeadEnd(Entity node, Entity edge, out HighwayDeadEnd info)
        {
            info = default;
            if (!Live(node) || !IsHighway(edge) || !IsOneway(edge)) return false;
            Classify(node, m_Hw, m_Other, out _);
            if (m_Hw.Count != 1 || m_Other.Count != 0 || RailCount(node) > 0) return false;
            var ed = EntityManager.GetComponentData<Edge>(edge);
            if (ed.m_Start != node && ed.m_End != node) return false;
            var cv = EntityManager.GetComponentData<Curve>(edge).m_Bezier;
            bool arriving = ed.m_End == node;
            float3 outDir = Flat(arriving ? MathUtils.EndTangent(cv) : -MathUtils.StartTangent(cv));
            if (math.lengthsq(outDir.xz) < 1e-4f) return false;
            info = new HighwayDeadEnd
            {
                Node = node, Edge = edge, Pos = NodePos(node), OutDir = outDir,
                Arriving = arriving, Elevation = NodeElevation(node),
            };
            return true;
        }

        /// <summary>Find the nearest one-way highway dead end within 2 hops and 160 m of the hovered spot.</summary>
        bool FindDeadEndNear(Entity hitEntity, float3 cursor, out HighwayDeadEnd found)
        {
            found = default;
            var edges = new HashSet<Entity>();
            if (IsHighway(hitEntity)) edges.Add(hitEntity);
            else if (Live(hitEntity) && EntityManager.HasComponent<Node>(hitEntity))
            {
                Classify(hitEntity, m_Hw, m_Other, out _);
                foreach (var h in m_Hw) edges.Add(h);
            }
            if (edges.Count == 0) return false;

            var frontier = new List<Entity>(edges);
            for (int hop = 0; hop < 2; hop++)
            {
                var next = new List<Entity>();
                foreach (var e in frontier)
                {
                    var ed = EntityManager.GetComponentData<Edge>(e);
                    foreach (var n in new[] { ed.m_Start, ed.m_End })
                    {
                        Classify(n, m_Hw, m_Other, out _);
                        foreach (var h in m_Hw) if (edges.Add(h)) next.Add(h);
                    }
                }
                frontier = next;
            }

            float bestD = 160f; bool ok = false;
            foreach (var e in edges)
            {
                var ed = EntityManager.GetComponentData<Edge>(e);
                foreach (var n in new[] { ed.m_Start, ed.m_End })
                {
                    if (!TryDeadEnd(n, e, out var cand)) continue;
                    float d = math.distance(cand.Pos.xz, cursor.xz);
                    if (d < bestD) { bestD = d; found = cand; ok = true; }
                }
            }
            return ok;
        }

        /// <summary>Find the opposing parallel carriageway's dead end right beside <paramref name="a"/>.</summary>
        bool FindPartnerDeadEnd(HighwayDeadEnd a, out HighwayDeadEnd partner)
        {
            partner = default;
            float bestScore = float.MaxValue; bool ok = false;
            float3 rightA = new float3(a.OutDir.z, 0, -a.OutDir.x);
            foreach (var e in RoadsNear(a.Pos.xz - 95f, a.Pos.xz + 95f))
            {
                if (e == a.Edge || !IsHighway(e) || !IsOneway(e)) continue;
                var ed = EntityManager.GetComponentData<Edge>(e);
                foreach (var n in new[] { ed.m_Start, ed.m_End })
                {
                    if (n == a.Node || !TryDeadEnd(n, e, out var b)) continue;
                    if (b.Arriving == a.Arriving) continue;                         // must be opposing traffic directions
                    if (math.dot(a.OutDir.xz, b.OutDir.xz) < 0.70f) continue;       // must point roughly the same way out
                    if (math.abs(a.Elevation - b.Elevation) > 4f) continue;
                    float3 delta = b.Pos - a.Pos;
                    float signedSep = math.dot(delta.xz, rightA.xz);
                    // Right-hand traffic: arriving carriageway (a.Arriving) is on the RIGHT of OutDir,
                    // so its departing partner b must lie to its LEFT (signedSep < 0), and vice versa.
                    if (a.Arriving ? signedSep >= 0f : signedSep <= 0f) continue;
                    float sep = math.abs(signedSep);
                    float stag = math.abs(math.dot(delta.xz, a.OutDir.xz));
                    if (sep < 6f || sep > 80f || stag > 60f) continue;
                    float score = sep + stag * 1.5f;
                    if (score < bestScore) { bestScore = score; partner = b; ok = true; }
                }
            }
            return ok;
        }

        Preview EndingPreview(Entity hitEntity, RaycastHit hit)
        {
            const string what = "Can't build a highway end here";
            if (!FindDeadEndNear(hitEntity, hit.m_HitPosition, out var a))
                return FailFinal(what, "point near the open ends of a divided one-way highway");
            if (!FindPartnerDeadEnd(a, out var b))
                return FailFinal(what, "no matching opposite-direction highway dead end found beside this one");

            var outPrefab = EndingRoadPrefab(out string roadName);
            if (outPrefab == Entity.Null) return FailFinal(what, "no two-way road type found to merge into");

            var inEnd = a.Arriving ? a : b;
            var outEnd = a.Arriving ? b : a;
            var heights = m_TerrainSystem.GetHeightData(false);

            float3 fwd = Flat(inEnd.OutDir + outEnd.OutDir);
            if (math.lengthsq(fwd.xz) < 1e-4f) return FailFinal(what, "the two highway ends don't line up");
            float3 right = new float3(fwd.z, 0, -fwd.x);
            float3 midBase = (inEnd.Pos + outEnd.Pos) * 0.5f;
            float projIn = math.dot(inEnd.Pos.xz - midBase.xz, fwd.xz);
            float projOut = math.dot(outEnd.Pos.xz - midBase.xz, fwd.xz);
            float front = math.max(projIn, projOut);
            float sep = math.abs(math.dot(inEnd.Pos.xz - outEnd.Pos.xz, right.xz));

            float sizeScale = Size == 0 ? 0.85f : Size == 2 ? 1.2f : 1f;
            float mergeDist = math.clamp(sep * 2.2f * sizeScale, 44f, 82f);
            // ensure neither staggered leg exceeds CS2's comfortable segment length
            float maxLegRun = math.max(front - projIn, front - projOut) + mergeDist;
            if (maxLegRun > 96f) mergeDist = math.max(38f, mergeDist - (maxLegRun - 96f));

            float2 mergeXZ = midBase.xz + fwd.xz * (front + mergeDist);
            float eM = (inEnd.Elevation + outEnd.Elevation) * 0.5f;
            if (math.abs(eM) < 0.05f) eM = 0f;
            float hM = TerrainUtils.SampleHeight(ref heights, new float3(mergeXZ.x, 0f, mergeXZ.y));
            float3 mergePos = new float3(mergeXZ.x, hM + eM, mergeXZ.y);

            // Check water at the merge node if near ground level
            if (eM < 3f && eM > -3f && Wet(mergeXZ))
                return FailFinal(what, "water is right in front of the highway ends");

            // Smooth Y-convergence: each leg leaves parallel to its carriageway and meets M at ~18 deg inward (36 deg total Y)
            const float Inward = 0.32f;
            float sideIn = math.sign(math.dot(inEnd.Pos.xz - mergePos.xz, right.xz));
            float sideOut = math.sign(math.dot(outEnd.Pos.xz - mergePos.xz, right.xz));
            if (sideIn == 0f) sideIn = 1f;
            if (sideOut == 0f) sideOut = -sideIn;

            float3 arriveInTan = math.normalizesafe(fwd - right * (sideIn * Inward));
            float3 departOutTan = math.normalizesafe(-fwd + right * (sideOut * Inward));

            var curveIn = NetUtils.FitCurve(inEnd.Pos, inEnd.OutDir, arriveInTan, mergePos);
            curveIn = Lift(curveIn, inEnd.Elevation, eM, ref heights, mergePos.y);
            curveIn.a.y = inEnd.Pos.y;
            if (math.abs(inEnd.Elevation) >= 0.05f || math.abs(eM) >= 0.05f)
            { curveIn.b.y = math.lerp(curveIn.a.y, curveIn.d.y, 1f / 3f); curveIn.c.y = math.lerp(curveIn.a.y, curveIn.d.y, 2f / 3f); }

            var curveOut = NetUtils.FitCurve(mergePos, departOutTan, -outEnd.OutDir, outEnd.Pos);
            curveOut = Lift(curveOut, eM, outEnd.Elevation, ref heights, outEnd.Pos.y);
            curveOut.a.y = mergePos.y; curveOut.d.y = outEnd.Pos.y;
            if (math.abs(eM) >= 0.05f || math.abs(outEnd.Elevation) >= 0.05f)
            { curveOut.b.y = math.lerp(curveOut.a.y, curveOut.d.y, 1f / 3f); curveOut.c.y = math.lerp(curveOut.a.y, curveOut.d.y, 2f / 3f); }

            // Refuse if either Y-leg would cross a railway track at the same level
            float2 legLo = math.min(math.min(inEnd.Pos.xz, outEnd.Pos.xz), mergeXZ) - 20f;
            float2 legHi = math.max(math.max(inEnd.Pos.xz, outEnd.Pos.xz), mergeXZ) + 20f;
            foreach (var tr in TracksNear(legLo, legHi))
            {
                if (!Live(tr) || !EntityManager.HasComponent<Curve>(tr)) continue;
                var tc = EntityManager.GetComponentData<Curve>(tr).m_Bezier;
                foreach (var leg in new[] { curveIn, curveOut })
                    if (CurvesCrossAtSameLevel(leg, tc))
                        return FailFinal(what, "a railway track crosses right in front of the highway ends");
            }

            var pv = new Preview();
            pv.Specs.Add(new Spec
            {
                Prefab = PrefabOf(inEnd.Edge), Curve = curveIn,
                StartEntity = inEnd.Node, E0 = inEnd.Elevation, E1 = eM,
            });
            pv.Specs.Add(new Spec
            {
                Prefab = PrefabOf(outEnd.Edge), Curve = curveOut,
                EndEntity = outEnd.Node, E0 = eM, E1 = outEnd.Elevation,
            });

            // Continue as a single two-way road ahead from M along fwd
            float roadHalf = WidthOfPrefab(outPrefab) * 0.5f;
            bool elevated = math.abs(eM) > 0.5f;
            bool keepUp = elevated && (KeepUp || eM < -0.5f);
            float ramp = elevated && !keepUp ? math.abs(eM) / math.max(Grade, 0.03f) : 0f;
            float minRamp = elevated && !keepUp ? math.abs(eM) / MaxGrade : 0f;
            float stubLen = elevated ? (keepUp ? 75f : ramp + 50f) : 75f;
            const float SearchAhead = 280f;

            // Check for an existing ordinary road or railway track straight ahead
            Attach farAttach = null; string joinedName = null;
            float bestAhead = math.max(stubLen, SearchAhead); Entity aheadRoad = Entity.Null; float aheadT = 0f;
            bool aheadIsRail = false;
            if (!keepUp)
            {
                foreach (var e in RoadsNear(mergeXZ - bestAhead, mergeXZ + bestAhead))
                {
                    if (e == inEnd.Edge || e == outEnd.Edge || !Live(e) || !EntityManager.HasComponent<Curve>(e)) continue;
                    var c = EntityManager.GetComponentData<Curve>(e).m_Bezier;
                    if (!LineMeets(mergeXZ, fwd.xz, c, out float u, out float t) || u <= 0f || u > bestAhead) continue;
                    float3 q = MathUtils.Position(c, t);
                    if (q.y - TerrainUtils.SampleHeight(ref heights, q) > eM + 4f) continue;
                    if (u < bestAhead) { bestAhead = u; aheadRoad = e; aheadT = t; aheadIsRail = false; }
                }
            }
            foreach (var tr in TracksNear(mergeXZ - bestAhead, mergeXZ + bestAhead))
            {
                if (!Live(tr) || !EntityManager.HasComponent<Curve>(tr)) continue;
                var c = EntityManager.GetComponentData<Curve>(tr).m_Bezier;
                if (!LineMeets(mergeXZ, fwd.xz, c, out float u, out float t) || u <= 0f || u > bestAhead) continue;
                float3 q = MathUtils.Position(c, t);
                float trElev = q.y - TerrainUtils.SampleHeight(ref heights, q);
                if (keepUp && math.abs(trElev - eM) > 5f) continue;
                if (u < bestAhead) { bestAhead = u; aheadRoad = tr; aheadT = t; aheadIsRail = true; }
            }

            float endDist = stubLen;
            string note = "";
            if (aheadRoad != Entity.Null)
            {
                string rn = aheadIsRail ? "a railway track" : (NameOf(aheadRoad) ?? m_PrefabSystem.GetPrefabName(PrefabOf(aheadRoad)));
                if (bestAhead <= 15f)
                    return FailFinal(what, $"{rn} crosses right at the merge point");
                float avail = bestAhead - 15f;
                if (aheadIsRail)
                {
                    float stop = bestAhead - 30f;
                    if (stop < 25f) return FailFinal(what, "a railway track is too close ahead of the merge");
                    if (elevated && !keepUp && stop < minRamp + 10f)
                    {
                        keepUp = true; ramp = 0f; endDist = math.min(stubLen, stop);
                        note = " Stops short of the railway track while staying elevated.";
                    }
                    else
                    {
                        endDist = math.min(endDist, stop);
                        if (elevated && !keepUp) ramp = math.min(ramp, math.max(minRamp, endDist - 10f));
                        note = " Stops short of the railway track.";
                    }
                }
                else if (elevated && avail < minRamp)
                {
                    // too close to descend before that road: stay raised and stop safely short of it
                    float safeStop = bestAhead - 30f;
                    if (safeStop < 25f) return FailFinal(what, $"{rn} is too close ahead of the highway ends");
                    keepUp = true; ramp = 0f; endDist = math.min(stubLen, safeStop);
                    note = $" {rn} is too close to descend, so the road stays elevated.";
                }
                else if (IsHighway(aheadRoad))
                {
                    float safeStop = bestAhead - 35f;
                    if (safeStop < 25f) return FailFinal(what, $"{rn} is too close ahead of the highway ends");
                    endDist = math.min(endDist, math.max(elevated ? minRamp + 15f : 25f, safeStop));
                    if (elevated) ramp = math.min(ramp, math.max(minRamp, endDist - 10f));
                }
                else if (bestAhead >= (elevated ? minRamp + 15f : 35f))
                {
                    var rc = EntityManager.GetComponentData<Curve>(aheadRoad);
                    var red = EntityManager.GetComponentData<Edge>(aheadRoad);
                    float st = SafeSplit(rc.m_Length, aheadT);
                    var cand = st <= 0f ? new Attach { Entity = red.m_Start, Pos = NodePos(red.m_Start), Elevation = NodeElevation(red.m_Start) }
                        : st >= 1f ? new Attach { Entity = red.m_End, Pos = NodePos(red.m_End), Elevation = NodeElevation(red.m_End) }
                        : new Attach { Entity = aheadRoad, Split = st, Pos = MathUtils.Position(rc.m_Bezier, st), Elevation = MathUtils.Position(rc.m_Bezier, st).y - TerrainUtils.SampleHeight(ref heights, MathUtils.Position(rc.m_Bezier, st)) };
                    float candDist = math.dot(cand.Pos.xz - mergeXZ, fwd.xz);
                    float candLat = math.abs(math.dot(cand.Pos.xz - mergeXZ, right.xz));
                    float minJoin = elevated ? minRamp + 15f : 35f;
                    if (candDist >= minJoin && candLat <= 16f)
                    {
                        farAttach = cand;
                        endDist = candDist;
                        if (elevated) ramp = math.min(ramp, math.max(minRamp, endDist - 12f));
                        joinedName = rn;
                    }
                    else
                    {
                        // Snapped node was behind or far off-axis; stop cleanly short instead of kinking
                        float safeStop = bestAhead - 30f;
                        if (safeStop < 25f) return FailFinal(what, $"{rn} is too close ahead of the highway ends");
                        endDist = math.min(endDist, safeStop);
                        if (elevated) ramp = math.min(ramp, math.max(minRamp, endDist - 10f));
                    }
                }
                else
                {
                    return FailFinal(what, $"{rn} is too close ahead of the highway ends ({(int)bestAhead} m past the merge)");
                }
            }

            // Avoid running the continuing road into water
            float wet = WaterAlong(mergeXZ, fwd.xz, 0f, ramp, endDist, 1, roadHalf);
            if (!float.IsNaN(wet))
            {
                farAttach = null; joinedName = null;
                if (elevated && wet <= ramp + 15f)
                {
                    keepUp = true; ramp = 0f; endDist = math.max(35f, wet - 5f);
                    note = " Water is close ahead, so the road stays raised at the shore.";
                }
                else
                {
                    endDist = math.max(30f, wet - math.max(15f, roadHalf + 10f));
                    if (elevated) ramp = math.min(ramp, math.max(0f, endDist - 5f));
                    note = " Stops short of the water.";
                }
            }

            float EndElev(float u)
            {
                if (!elevated) return 0f;
                if (keepUp || ramp <= 0.1f) return eM;
                if (u >= ramp) return 0f;
                return eM * (1f - math.smoothstep(0f, ramp, u));
            }
            float EndSlope(float u)
            {
                if (!elevated || keepUp || ramp <= 0.1f || u <= 0f || u >= ramp) return 0f;
                float t = math.saturate(u / ramp);
                return -eM * (6f * t * (1f - t)) / ramp;
            }

            // Build continuing road in smooth <= MaxPiece segments
            var stops = new List<float> { 0f, endDist };
            if (elevated && !keepUp && ramp > 4f && ramp < endDist - 4f) stops.Insert(1, ramp);
            var marks = new List<float>();
            for (int i = 0; i + 1 < stops.Count; i++)
            {
                float gap = stops[i + 1] - stops[i];
                int n = math.max(1, (int)math.ceil(gap / MaxPiece));
                for (int k = 0; k < n; k++) marks.Add(math.lerp(stops[i], stops[i + 1], k / (float)n));
            }
            marks.Add(endDist);

            for (int i = 0; i + 1 < marks.Count; i++)
            {
                float u0 = marks[i], u1 = marks[i + 1];
                float e0 = EndElev(u0), e1 = EndElev(u1);
                float3 p0 = i == 0 ? mergePos : new float3(mergeXZ.x + fwd.x * u0, 0f, mergeXZ.y + fwd.z * u0);
                float3 p1 = i == marks.Count - 2 && farAttach != null ? farAttach.Pos : new float3(mergeXZ.x + fwd.x * u1, 0f, mergeXZ.y + fwd.z * u1);
                float h0 = TerrainUtils.SampleHeight(ref heights, p0), h1 = TerrainUtils.SampleHeight(ref heights, p1);
                if (i > 0) p0.y = h0 + e0;
                if (!(i == marks.Count - 2 && farAttach != null)) p1.y = h1 + e1;
                bool lastJoin = i == marks.Count - 2 && farAttach != null;
                float latOff = lastJoin ? math.abs(math.dot(p1.xz - p0.xz, right.xz)) : 0f;
                var seg = latOff > 0.5f ? NetUtils.FitCurve(p0, fwd, math.normalizesafe(p1 - p0), p1) : NetUtils.StraightCurve(p0, p1);
                if (math.abs(e0) < 0.05f && math.abs(e1) < 0.05f)
                {
                    seg.b.y = TerrainUtils.SampleHeight(ref heights, seg.b);
                    seg.c.y = TerrainUtils.SampleHeight(ref heights, seg.c);
                }
                else
                {
                    float segLen = math.max(1f, u1 - u0);
                    float tSlope = (h1 - h0) / segLen;
                    float g0 = tSlope + EndSlope(u0), g1 = tSlope + EndSlope(u1);
                    float lo = math.min(seg.a.y, seg.d.y), hi = math.max(seg.a.y, seg.d.y);
                    seg.b.y = math.clamp(seg.a.y + g0 * (segLen / 3f), lo, hi);
                    seg.c.y = math.clamp(seg.d.y - g1 * (segLen / 3f), lo, hi);
                }
                var spec = new Spec { Prefab = outPrefab, Curve = seg, E0 = e0, E1 = e1 };
                if (i == marks.Count - 2 && farAttach != null) { spec.EndEntity = farAttach.Entity; spec.EndSplit = farAttach.Split; spec.E1 = farAttach.Elevation; }
                pv.Specs.Add(spec);
            }

            string tail = joinedName != null ? $"joining {joinedName}" : keepUp ? (eM < -0.5f ? "staying sunken for you to continue" : "staying elevated for you to continue") : elevated ? "ramping down to ground level" : "ready for you to continue";
            pv.Log = $"highway end merging both carriageways into {roadName} ({(int)(mergeDist + endDist)} m, {tail})";
            pv.Status = $"Highway end: merges both carriageways cleanly into one {roadName}, {tail}.{note} Click to build.";
            return pv;
        }

        static bool CurvesCrossAtSameLevel(Bezier4x3 a, Bezier4x3 b)
        {
            const int N = 12;
            float3 pa0 = a.a;
            for (int i = 1; i <= N; i++)
            {
                float3 pa1 = MathUtils.Position(a, i / (float)N);
                float3 pb0 = b.a;
                for (int j = 1; j <= N; j++)
                {
                    float3 pb1 = MathUtils.Position(b, j / (float)N);
                    float2 da = pa1.xz - pa0.xz, db = pb1.xz - pb0.xz;
                    float den = da.x * db.y - da.y * db.x;
                    if (math.abs(den) > 1e-6f)
                    {
                        float2 w = pb0.xz - pa0.xz;
                        float u = (w.x * db.y - w.y * db.x) / den;
                        float v = (w.x * da.y - w.y * da.x) / den;
                        if (u >= 0f && u <= 1f && v >= 0f && v <= 1f)
                        {
                            float ya = math.lerp(pa0.y, pa1.y, u), yb = math.lerp(pb0.y, pb1.y, v);
                            if (math.abs(ya - yb) < 4.5f) return true;
                        }
                    }
                    pb0 = pb1;
                }
                pa0 = pa1;
            }
            return false;
        }
    }
}
