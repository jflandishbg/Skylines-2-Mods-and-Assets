// Interchange Studio - Core/Planner.Stubs.cs
// Streets the player drew up to the highway from both sides, stopping short of it: point at the highway
// between them and click. The two stubs are joined across the highway, and their own pieces near it are
// lifted into the bridge's slopes, so the crossing follows the streets that are already there instead of
// laying a new straight road. A side street on a stub limits its slope, which steepens (up to MaxGrade).
using System.Collections.Generic;
using Colossal.Mathematics;
using Unity.Mathematics;

namespace InterchangeStudio.Core
{
    public partial class Planner
    {
        public struct Stub { public Entity Node, Edge; public float3 Pos; public float W, A; }

        /*
         * Along a line from o (direction d), beyond 'deck' metres: where a new street ends. The first ordinary
         * road in line within reach is joined (its junction gets 15 m of flat first, and the slope steepens to
         * fit, up to MaxGrade); with none, the street stops a stub's length past the slope.
         */
        bool FarEnd(float2 o, float2 d, float deck, float ramp, float minRamp, ref TerrainHeightData heights, out float end, out Attach attach, out string roadName, out string fail)
        {
            attach = null; roadName = null; fail = "";
            end = deck + ramp + NewStreetStub;
            float best = ramp + 15f + NewStreetReach; Entity road = Entity.Null; float bt = 0; bool isRail = false;
            foreach (var e in RoadsNear(o + d * deck - (ramp + NewStreetReach), o + d * deck + (ramp + NewStreetReach)))
            {
                if (!Live(e) || !EntityManager.HasComponent<Curve>(e)) continue;
                var c = EntityManager.GetComponentData<Curve>(e).m_Bezier;
                if (!LineMeets(o, d, c, out float u, out float t) || u <= deck - 1f) continue;
                float3 q = MathUtils.Position(c, t);
                if (q.y - TerrainUtils.SampleHeight(ref heights, q) > Clearance + 2f) continue;
                if (u - deck < best) { best = u - deck; road = e; bt = t; isRail = false; }
            }
            foreach (var tr in TracksNear(o + d * deck - (ramp + NewStreetReach), o + d * deck + (ramp + NewStreetReach)))
            {
                if (!Live(tr) || !EntityManager.HasComponent<Curve>(tr)) continue;
                var c = EntityManager.GetComponentData<Curve>(tr).m_Bezier;
                if (!LineMeets(o, d, c, out float u, out float t) || u <= deck - 1f) continue;
                float3 q = MathUtils.Position(c, t);
                if (q.y - TerrainUtils.SampleHeight(ref heights, q) > Clearance + 2f) continue;
                if (u - deck < best) { best = u - deck; road = tr; bt = t; isRail = true; }
            }
            if (road == Entity.Null) return true;
            roadName = isRail ? "a railway track" : (NameOf(road) ?? m_PrefabSystem.GetPrefabName(PrefabOf(road)));
            if (best - 15f < minRamp) { fail = $"{roadName} is only {(int)best} m past the highway, too close for the street to come down even at {MaxGrade * 100f:0}%"; return false; }
            if (isRail || IsHighway(road)) { end = deck + math.max(minRamp + 10f, best - 40f); roadName = null; return true; }
            var rc = EntityManager.GetComponentData<Curve>(road);
            var red = EntityManager.GetComponentData<Edge>(road);
            float st = SafeSplit(rc.m_Length, bt);
            attach = st <= 0f ? new Attach { Entity = red.m_Start, Pos = NodePos(red.m_Start) }
                : st >= 1f ? new Attach { Entity = red.m_End, Pos = NodePos(red.m_End) }
                : new Attach { Entity = road, Split = st, Pos = MathUtils.Position(rc.m_Bezier, st) };
            end = math.dot(attach.Pos.xz - o, d);
            return true;
        }

        /// <summary>A dead end of the hovered street (or a few pieces along it) pointing at a highway close by.</summary>
        bool FindStubToward(Entity street, float3 cursor, out Stub stub, out Entity hw, out RaycastHit hwHit)
        {
            stub = default; hw = Entity.Null; hwHit = default;
            var seen = new HashSet<Entity> { street }; var frontier = new List<Entity> { street };
            float bestD = float.MaxValue;
            for (int depth = 0; depth < 6 && frontier.Count > 0; depth++)
            {
                var next = new List<Entity>();
                foreach (var e in frontier)
                {
                    if (!EntityManager.HasComponent<Edge>(e)) continue;          // a junction under the cursor, not a road piece (in-game crash 2026-10-23)
                    var ed = EntityManager.GetComponentData<Edge>(e); var c = EntityManager.GetComponentData<Curve>(e).m_Bezier;
                    foreach (var n in new[] { ed.m_Start, ed.m_End })
                    {
                        Classify(n, m_Hw, m_Other, out _);
                        if (m_Hw.Count > 0) continue;
                        if (m_Other.Count == 1 && !IsOneway(e))
                        {
                            float3 pos = NodePos(n);
                            float2 head = -math.normalizesafe((n == ed.m_Start ? MathUtils.StartTangent(c) : -MathUtils.EndTangent(c)).xz);
                            foreach (var h in RoadsNear(pos.xz - 200f, pos.xz + 200f))
                            {
                                if (!IsHighway(h)) continue;
                                var hc = EntityManager.GetComponentData<Curve>(h).m_Bezier;
                                if (!LineMeets(pos.xz, head, hc, out float u, out float t) || u <= 0f || u > 150f) continue;
                                float dist = math.distance(pos.xz, cursor.xz) + u;
                                if (dist >= bestD) continue;
                                bestD = dist; hw = h;
                                stub = new Stub { Node = n, Edge = e, Pos = pos };
                                hwHit = new RaycastHit { m_HitEntity = h, m_CurvePosition = t, m_HitPosition = MathUtils.Position(hc, t) };
                            }
                        }
                        foreach (var o in new List<Entity>(m_Other)) if (!IsHighway(o) && seen.Add(o)) next.Add(o);
                    }
                }
                frontier = next;
            }
            return hw != Entity.Null;
        }

        /// <summary>Two dead-end streets facing each other across the highway near the click, if there are.</summary>
        bool FindStubPair(Entity hwEdge, RaycastHit hit, out Stub sa, out Stub sb)
        {
            sa = sb = default;
            var hc = EntityManager.GetComponentData<Curve>(hwEdge).m_Bezier;
            float2 o = MathUtils.Position(hc, hit.m_CurvePosition).xz;
            float2 along = math.normalizesafe(MathUtils.Tangent(hc, hit.m_CurvePosition).xz), d = new float2(-along.y, along.x);
            float hwHalf = WidthOf(hwEdge) * 0.5f;
            var ends = new List<Stub>();
            foreach (var e in RoadsNear(o - 260f, o + 260f))
            {
                if (!IsRoadEdge(e) || IsHighway(e) || IsOneway(e)) continue;
                var ed = EntityManager.GetComponentData<Edge>(e); var c = EntityManager.GetComponentData<Curve>(e).m_Bezier;
                foreach (var n in new[] { ed.m_Start, ed.m_End })
                {
                    Classify(n, m_Hw, m_Other, out _);
                    if (m_Other.Count != 1 || m_Hw.Count != 0 || RailCount(n) > 0) continue;       // a dead end, nothing else there
                    float3 pos = NodePos(n);
                    float w = math.dot(pos.xz - o, d), a = math.dot(pos.xz - o, along);
                    if (math.abs(a) > 250f || math.abs(w) > 200f || math.abs(w) < hwHalf) continue;
                    float2 outward = math.normalizesafe((n == ed.m_Start ? MathUtils.StartTangent(c) : -MathUtils.EndTangent(c)).xz);
                    if (math.dot(outward, d * math.sign(w)) < 0.5f) continue;                       // it must lead away from the highway
                    ends.Add(new Stub { Node = n, Edge = e, Pos = pos, W = w, A = a });
                }
            }
            float bestScore = float.MaxValue;
            foreach (var x in ends)
                foreach (var y in ends)
                {
                    if (x.W >= 0f || y.W <= 0f) continue;                                          // one on each side of the clicked carriageway
                    float2 ab = math.normalizesafe(y.Pos.xz - x.Pos.xz);
                    if (math.abs(math.dot(ab, along)) > 0.7f) continue;                            // too shallow a crossing
                    float score = math.abs((x.A + y.A) * 0.5f) + math.abs(x.A - y.A) * 0.5f;
                    if (score < bestScore) { bestScore = score; sa = x; sb = y; }
                }
            return bestScore < float.MaxValue;
        }

        /// <summary>Join stub A across the highway: to stub B if there is one (hasB), else carry straight on to the first road in line.</summary>
        Preview StubBridgePreview(Entity hwEdge, Stub sa, Stub sb, bool hasB = true)
        {
            string name = NameOf(sa.Edge) ?? NameOf(sb.Edge) ?? m_PrefabSystem.GetPrefabName(PrefabOf(sa.Edge));
            string what = $"Can't join {name} across the highway";
            float hwHalf = WidthOf(hwEdge) * 0.5f;
            float margin = hwHalf + DeckMargin;
            float ramp = Clearance / Grade, minRamp = Clearance / MaxGrade;

            // each stub, walked away from the highway as far as a slope could need (stopping at a side street)
            var back = WalkStreet(sa.Node, sa.Edge, margin + ramp, out string backStop, out _, out string why);
            if (back == null) return Fail(what, why);
            float3 ta = -math.normalizesafe(MathUtils.StartTangent(back[0].Curve));      // at A, heading for the highway
            var heights = m_TerrainSystem.GetHeightData(false);
            List<Seg> fwd = new List<Seg>(); string fwdStop = "the new street ends"; Attach tail = null; string farName = null;
            if (hasB)
            {
                fwd = WalkStreet(sb.Node, sb.Edge, margin + ramp, out fwdStop, out _, out why);
                if (fwd == null) return Fail(what, why);
            }
            else
            {
                // no street on the far side: carry straight on, over the carriageways, to the first road in line
                float2 o0 = sa.Pos.xz, d0 = math.normalizesafe(ta.xz);
                float uMax = 0;
                foreach (var e in RoadsNear(o0 - 300f, o0 + 300f))
                {
                    if (!IsHighway(e)) continue;
                    var c = EntityManager.GetComponentData<Curve>(e).m_Bezier;
                    if (LineMeets(o0, d0, c, out float u, out float _) && u > 0f && u < 250f) uMax = math.max(uMax, u);
                }
                if (uMax <= 0f) return FailFinal(what, "the street does not point at the highway");
                if (!FarEnd(o0, d0, uMax + margin, ramp, minRamp, ref heights, out float endU, out tail, out farName, out string fail)) return FailFinal(what, fail);
                var bpos = tail != null ? tail.Pos : new float3(o0.x + d0.x * endU, 0, o0.y + d0.y * endU);
                bpos.y = TerrainUtils.SampleHeight(ref heights, bpos);
                sb = new Stub { Node = tail != null && !EntityManager.HasComponent<Edge>(tail.Entity) ? tail.Entity : Entity.Null, Pos = bpos };
            }

            // the new span between the two ends, leaving each the way its street points
            float3 tb = hasB ? math.normalizesafe(MathUtils.StartTangent(fwd[0].Curve)) : math.normalizesafe(sb.Pos - sa.Pos);
            var span = NetUtils.FitCurve(sa.Pos, ta, tb, sb.Pos);
            float spanLen = MathUtils.Length(span);
            var mid = new Seg { Edge = Entity.Null, From = sa.Node, To = sb.Node, Curve = span, Length = spanLen, Table = LengthTable(span), Forward = true };
            var p = new Plan { HighwayHalf = hwHalf, StreetHalf = WidthOf(sa.Edge) * 0.5f, KeepOff = hwHalf + 8f, SpanPrefab = PrefabOf(sa.Edge) };
            if (tail != null && EntityManager.HasComponent<Edge>(tail.Entity)) p.TailAttach = tail;
            var chain = new List<Seg> { mid }; chain.AddRange(fwd);
            float sA = Join(p, back, chain);

            // where the span passes over the carriageways
            var under = new List<float>();
            float2 o = sa.Pos.xz, dir = math.normalizesafe(sb.Pos.xz - sa.Pos.xz);
            float scale = spanLen / math.max(1f, math.distance(sa.Pos.xz, sb.Pos.xz));
            foreach (var e in RoadsNear(math.min(sa.Pos.xz, sb.Pos.xz) - 20f, math.max(sa.Pos.xz, sb.Pos.xz) + 20f))
            {
                if (!IsRoadEdge(e) || !EntityManager.HasComponent<Curve>(e)) continue;
                var c = EntityManager.GetComponentData<Curve>(e).m_Bezier;
                if (!LineMeets(o, dir, c, out float u, out float t) || u <= 0f || u >= math.distance(sa.Pos.xz, sb.Pos.xz)) continue;
                float3 q = MathUtils.Position(c, t);
                if (q.y - TerrainUtils.SampleHeight(ref heights, q) > Clearance + 2f) continue;      // a bridge high above
                if (!IsHighway(e)) return FailFinal(what, $"{NameOf(e) ?? "another road"} runs between the two ends; the bridge would land on it");
                if (q.y - TerrainUtils.SampleHeight(ref heights, q) > 2f) return FailFinal(what, "the highway is raised here");
                under.Add(sA + u * scale); hwHalf = math.max(hwHalf, WidthOf(e) * 0.5f);
            }
            foreach (var tr in TracksNear(math.min(sa.Pos.xz, sb.Pos.xz) - 20f, math.max(sa.Pos.xz, sb.Pos.xz) + 20f))
            {
                if (!Live(tr) || !EntityManager.HasComponent<Curve>(tr)) continue;
                var c = EntityManager.GetComponentData<Curve>(tr).m_Bezier;
                if (!LineMeets(o, dir, c, out float u, out float t) || u <= 0f || u >= math.distance(sa.Pos.xz, sb.Pos.xz)) continue;
                float3 q = MathUtils.Position(c, t);
                if (q.y - TerrainUtils.SampleHeight(ref heights, q) > Clearance + 2f) continue;
                under.Add(sA + u * scale);
            }
            if (under.Count == 0) return FailFinal(what, "the line between the two street ends doesn't cross the highway");
            under.Sort();
            p.Cross = (under[0] + under[under.Count - 1]) * 0.5f;
            var backUnder = new List<float>(); var fwdUnder = new List<float>();
            foreach (float u in under) { if (u < p.Cross) backUnder.Add(p.Cross - u); else if (u > p.Cross) fwdUnder.Add(u - p.Cross); }
            // a junction at the far end gets a short flat stretch before it, like any new street
            float flat = !hasB && tail != null ? 15f : 0f;
            p.Total -= flat;
            bool ok = Finish(p, backUnder, fwdUnder, backStop, fwdStop, margin, ramp, minRamp, out why);
            p.Total += flat;
            if (!ok) return Fail(what, why);

            var pv = new Preview();
            if (DigUnder) p.Sign = -1f;
            WriteLift(pv, p, new HashSet<Entity>());
            bool ramps = Mode != ToolMode.Overpass;
            string style = StyleName(Mode);
            float rampBack = p.RampUp - p.Start, rampFwd = p.End - p.RampDown;
            string steeper = math.min(rampBack, rampFwd) < ramp - 1f
                ? $" A side street is close, so a slope is steepened to {Clearance / math.min(rampBack, rampFwd) * 100f:0.#}%." : "";
            pv.NextStep = ramps; pv.NextPos = Position(p, under[0]); pv.NextMode = Mode;
            pv.Log = $"{name} joined across the highway ({(int)(p.End - p.Start)} m bridge from its two ends)" + (ramps ? $", then a {style} interchange" : "");
            string how = hasB ? "using the street's own ends"
                : farName != null ? $"carrying straight on to {farName}" : "carrying straight on and stopping short on the far side for you to continue";
            pv.Status = $"{name} is {(hasB ? "joined" : "extended")} across the highway {(DigUnder ? "in a cutting under it" : "on a bridge")} ({(int)(p.End - p.Start)} m), {how}.{steeper}"
                + (ramps ? $" Then the {style} interchange ramps are added automatically." : "") + " Click to build.";
            return pv;
        }
    }
}
