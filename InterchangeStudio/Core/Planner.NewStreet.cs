// Interchange Studio - Core/Planner.NewStreet.cs
// Point at a bare stretch of highway and click: a new cross street is laid square across both carriageways
// on a bridge, its ends running out to the nearest road in line (or stopping short for the player to
// continue), and then, as with any crossing, the interchange ramps are added to it automatically.
using System.Collections.Generic;
using Colossal.Mathematics;
using Unity.Mathematics;

namespace InterchangeStudio.Core
{
    public partial class Planner
    {
        const float NewStreetReach = 500f;      // how far past the bridge an end looks for a road to join
        const float NewStreetStub = 45f;        // otherwise, how far past the bridge slope it stops (compact landing, not 250 m bloat)
        const float KeptUpReach = 80f;          // kept elevated: how far past the deck its raised ends reach

        bool Wet(float2 xz) => m_TerrainSystem.WaterDepth(new float3(xz.x, 0, xz.y)) > 0.05f;

        /*
         * Walking out from the deck's edge along o + d*u (u growing by 'side'): the first point low enough to put
         * road pavement, grading or a low embankment in water (checked across the full road width + skirt, not just
         * the centreline, because angled shorelines hit the road edges first). NaN when dry all the way.
         */
        float WaterAlong(float2 o, float2 d, float deck, float slope, float end, int side, float halfWidth = 0f)
        {
            float2 perp = new float2(-d.y, d.x);
            float band = halfWidth > 0f ? halfWidth + 8f : 0f;
            bool WetBand(float dist)
            {
                float2 c = o + d * (dist * side);
                if (Wet(c)) return true;
                return band > 0f && (Wet(c + perp * band) || Wet(c - perp * band));
            }
            for (float x = math.abs(deck); x <= math.abs(end); x += 4f)
            {
                float u = slope > 0f ? math.saturate((x - math.abs(deck)) / slope) : 0f;
                float low = slope > 0f ? Clearance * (1f - (3f * u * u - 2f * u * u * u)) : Clearance;
                if (low < 5f && WetBand(x))
                {
                    // found within the last 4 m: step back to the exact shoreline
                    float edge = x;
                    while (edge - 1f >= math.abs(deck) && WetBand(edge - 1f)) edge -= 1f;
                    return edge;
                }
            }
            return float.NaN;
        }

        /// <summary>The road type for a new cross street (setting NewStreet: 0 medium, 1 large, 2 avenue).</summary>
        Entity NewStreetPrefab(out string label)
        {
            var wanted = NewStreet == 0 ? new[] { "Medium Road", "Large Road" }
                : NewStreet == 2 ? new[] { "Medium Road Divided", "Large Road Divided", "XL Road Divided", "Large Road" }
                : new[] { "Large Road", "Medium Road" };
            foreach (var name in wanted)
            {
                var p = Named(name, "New street");
                if (p != Entity.Null) { label = NewStreet == 2 && !name.Contains("Divided") ? "Large Road (no avenue type found)" : name; return p; }
            }
            label = ""; return Entity.Null;
        }

        /// <summary>Where a straight line o + d*u meets a road piece's curve (2D): the u and the curve parameter.</summary>
        static bool LineMeets(float2 o, float2 d, Bezier4x3 c, out float u, out float t)
        {
            u = t = 0; const int N = 24;
            float2 prev = c.a.xz; bool found = false; float best = float.MaxValue;
            for (int i = 1; i <= N; i++)
            {
                float2 q = MathUtils.Position(c, i / (float)N).xz, e = q - prev;
                float den = d.x * e.y - d.y * e.x;
                if (math.abs(den) > 1e-6f)
                {
                    float2 w = prev - o;
                    float uu = (w.x * e.y - w.y * e.x) / den, vv = (w.x * d.y - w.y * d.x) / den;
                    if (vv >= 0f && vv <= 1f && math.abs(uu) < best) { best = math.abs(uu); u = uu; t = (i - 1 + vv) / N; found = true; }
                }
                prev = q;
            }
            return found;
        }

        Preview NewStreetPreview(Entity hwEdge, RaycastHit hit)
        {
            string what = "Can't add a cross street here";
            var prefab = NewStreetPrefab(out string typeName);
            if (prefab == Entity.Null) return FailFinal(what, "no ordinary road type found to build it with");
            var heights = m_TerrainSystem.GetHeightData(false);
            var hc = EntityManager.GetComponentData<Curve>(hwEdge).m_Bezier;
            float3 at = MathUtils.Position(hc, hit.m_CurvePosition);
            float2 along = math.normalizesafe(MathUtils.Tangent(hc, hit.m_CurvePosition).xz);
            float2 o = at.xz, d = new float2(-along.y, along.x);          // square across the highway

            // the carriageways the street crosses (the clicked one, and its partner running the other way)
            var under = new List<float>(); float hwHalf = WidthOf(hwEdge) * 0.5f, hwTop = 0f;
            bool partnerFound = !IsOneway(hwEdge);
            foreach (var e in RoadsNear(o - 160f, o + 160f))
            {
                if (!Live(e) || !EntityManager.HasComponent<Curve>(e)) continue;
                var c = EntityManager.GetComponentData<Curve>(e).m_Bezier;
                if (!LineMeets(o, d, c, out float u, out float t) || math.abs(u) > 150f) continue;
                float3 q = MathUtils.Position(c, t);
                float lift = q.y - TerrainUtils.SampleHeight(ref heights, q);
                if (!IsHighway(e)) continue;                                   // other roads: the ends deal with them, below
                float dot = math.dot(math.normalizesafe(MathUtils.Tangent(c, t).xz), along);
                if (math.abs(dot) < 0.8f) return FailFinal(what, "the highway is curving or branching here; point at a straight stretch");
                if (math.abs(u) > 1f && dot > 0f) continue;                    // another lane of traffic the same way: a parallel road, not the partner
                if (math.abs(u) > 1f) { if (partnerFound) continue; partnerFound = true; }
                under.Add(u); hwHalf = math.max(hwHalf, WidthOf(e) * 0.5f); hwTop = math.max(hwTop, lift);
            }
            if (under.Count == 0) under.Add(0f);
            if (hwTop > 2f) return FailFinal(what, "the highway is raised here; point where it runs at ground level");
            under.Sort();
            float uMin = under[0], uMax = under[under.Count - 1];

            // the bridge: the same flat deck as when a drawn street is lifted over the highway; each side's slope
            // fits the room before the first road in line (as steep as MaxGrade), and the end joins that road
            float margin = hwHalf + DeckMargin;
            float ramp = Clearance / Grade, minRamp = Clearance / MaxGrade;
            const float FlatBeforeJunction = 15f;
            var p = new Plan { RampUp = uMin - margin, RampDown = uMax + margin, KeepOff = hwHalf + 8f };
            p.Under.AddRange(under);
            // on a bare highway there is no street at ground level for the highway to go over, so "highway over" means the street goes under
            bool dig = Mode == ToolMode.Overpass && (DigUnder || !LiftStreet);
            bool keep = KeepUp && !dig;
            if (dig) p.Sign = -1f;
            Attach endA = null, endB = null; string joined = "", steeper = "", water = "";
            float uA = 0, uB = 0;
            if (keep)
            {
                // kept elevated: up at bridge height end to end, ends left raised; pillars kept off any road it passes over
                uA = p.RampUp - KeptUpReach; uB = p.RampDown + KeptUpReach;
                p.Start = uA - 1f; p.RampUp = uA; p.RampDown = uB; p.End = uB + 1f;
                foreach (var e in RoadsNear(o + d * uA - 20f, o + d * uB + 20f))
                {
                    if (!Live(e) || IsHighway(e) || !EntityManager.HasComponent<Curve>(e)) continue;
                    if (LineMeets(o, d, EntityManager.GetComponentData<Curve>(e).m_Bezier, out float u, out float _) && u > uA && u < uB) p.Under.Add(u);
                }
                foreach (var tr in TracksNear(o + d * uA - 20f, o + d * uB + 20f))
                {
                    if (!Live(tr) || !EntityManager.HasComponent<Curve>(tr)) continue;
                    if (LineMeets(o, d, EntityManager.GetComponentData<Curve>(tr).m_Bezier, out float u, out float _) && u > uA && u < uB) p.Under.Add(u);
                }
            }
            else foreach (int side in new[] { -1, 1 })
            {
                float deck = side < 0 ? p.RampUp : p.RampDown;
                float best = ramp + FlatBeforeJunction + NewStreetReach; Entity road = Entity.Null; float bt = 0; bool isRail = false;
                foreach (var e in RoadsNear(o + d * deck - (ramp + NewStreetReach), o + d * deck + (ramp + NewStreetReach)))
                {
                    if (!Live(e) || !EntityManager.HasComponent<Curve>(e)) continue;
                    var c = EntityManager.GetComponentData<Curve>(e).m_Bezier;
                    if (!LineMeets(o, d, c, out float u, out float t)) continue;
                    if (u * side <= 0f) continue;                                // the other side's business
                    if (IsHighway(e) && math.abs(u) < math.abs(deck)) continue;  // the carriageways being crossed
                    float3 q = MathUtils.Position(c, t);
                    if (q.y - TerrainUtils.SampleHeight(ref heights, q) > Clearance + 2f) continue;   // a bridge high above
                    float beyond = (u - deck) * side;
                    if (beyond < 0f) return FailFinal(what, $"{NameOf(e) ?? "a road"} runs right beside the highway, under where the bridge deck would be; point elsewhere");
                    if (beyond < best) { best = beyond; road = e; bt = t; isRail = false; }
                }
                foreach (var tr in TracksNear(o + d * deck - (ramp + NewStreetReach), o + d * deck + (ramp + NewStreetReach)))
                {
                    if (!Live(tr) || !EntityManager.HasComponent<Curve>(tr)) continue;
                    var c = EntityManager.GetComponentData<Curve>(tr).m_Bezier;
                    if (!LineMeets(o, d, c, out float u, out float t)) continue;
                    if (u * side <= 0f) continue;
                    float3 q = MathUtils.Position(c, t);
                    if (q.y - TerrainUtils.SampleHeight(ref heights, q) > Clearance + 2f) continue;
                    float beyond = (u - deck) * side;
                    if (beyond < 0f) return FailFinal(what, "a railway track runs right beside the highway, under where the bridge deck would be; point elsewhere");
                    if (beyond < best) { best = beyond; road = tr; bt = t; isRail = true; }
                }
                float slope = ramp; float end = deck + side * (ramp + NewStreetStub);
                if (road != Entity.Null)
                {
                    string rn = isRail ? "a railway track" : (NameOf(road) ?? m_PrefabSystem.GetPrefabName(PrefabOf(road)));
                    slope = math.min(ramp, best - FlatBeforeJunction);
                    if (slope < minRamp)
                        return FailFinal(what, $"{rn} is only {(int)best} m from the bridge deck, and coming down {Clearance:0} m needs at least {(int)(minRamp + FlatBeforeJunction)} m even at {MaxGrade * 100f:0}%; point where there's more room");
                    if (slope < ramp - 1f) steeper = $" The slope on the {rn} side is steepened to {Clearance / slope * 100f:0.#}% to come down in time.";
                    if (isRail || IsHighway(road)) end = deck + side * math.max(slope + 10f, best - 40f);     // never join a highway or rail: stop short of it
                    else
                    {
                        var rc = EntityManager.GetComponentData<Curve>(road);
                        var red = EntityManager.GetComponentData<Edge>(road);
                        float st = SafeSplit(rc.m_Length, bt);
                        var attach = st <= 0f ? new Attach { Entity = red.m_Start, Pos = NodePos(red.m_Start) }
                            : st >= 1f ? new Attach { Entity = red.m_End, Pos = NodePos(red.m_End) }
                            : new Attach { Entity = road, Split = st, Pos = MathUtils.Position(rc.m_Bezier, st) };
                        end = math.dot(attach.Pos.xz - o, d);
                        if (side < 0) endA = attach; else endB = attach;
                        joined += (joined == "" ? "" : " and ") + rn;
                        slope = math.min(slope, math.abs(end - deck) - FlatBeforeJunction * 0.5f);   // a junction that snapped to a node nearer in
                        if (slope < minRamp) return FailFinal(what, $"{rn} meets the line too close to the bridge deck for the street to come down in time; point elsewhere");
                    }
                }
                // water ahead at ground level or low on the slope: stop short of it (the junction beyond is dropped), or stay raised at the shore
                float streetHalf = WidthOfPrefab(prefab) * 0.5f;
                float wet = WaterAlong(o, d, deck, slope, end, side, streetHalf);
                if (!float.IsNaN(wet))
                {
                    if (side < 0) endA = null; else endB = null;
                    float setback = math.max(15f, streetHalf + 10f);
                    if (wet <= math.abs(deck) + slope + 15f)
                    {
                        // no room to come down before the water (2026-10-23 self-test: a highway along the shore): this end
                        // stays raised and stops at the water's edge, for the player to carry on as a bridge or leave
                        end = side * math.max(math.abs(deck) + 10f, wet - 5f); slope = 0f;
                        water = " Water comes too soon for it to come down on one side, so that end is left raised at the water's edge; carry it on as a bridge.";
                    }
                    else { end = side * math.max(math.abs(deck) + slope + 5f, wet - setback); water = " It stops short of the water."; }
                }
                // a raised end stays up all the way to its end; otherwise the slope starts at the deck's edge
                if (side < 0) { if (slope == 0f) { p.RampUp = end; p.Start = end - 1f; } else p.Start = deck - slope; uA = end; }
                else { if (slope == 0f) { p.RampDown = end; p.End = end + 1f; } else p.End = deck + slope; uB = end; }
            }

            // keep bridge pillars off footpaths crossing under the deck too
            foreach (var path in EntityManager.Paths)
                if (LineMeets(o, d, path.Curve, out float pu, out float _) && pu > uA + 4f && pu < uB - 4f)
                    p.Under.Add(pu);

            // break points: ends, ramp tops, enough in between; no node (pillar) over a carriageway
            var bps = new List<float> { uA, uB, p.Start, p.RampUp, p.RampDown, p.End };
            // a dumbbell's roundabouts will sit on the deck: joints exactly where each ring meets the street
            if (Mode == ToolMode.Dumbbell && !dig && !keep)
            {
                float ringAt = hwHalf + RingRadius + 12f;      // as ServicePreview places it
                bps.AddRange(new[] { uMin - ringAt - RingRadius, uMin - ringAt + RingRadius, uMax + ringAt - RingRadius, uMax + ringAt + RingRadius });
            }
            bps.RemoveAll(x => x < uA || x > uB);
            bps.Sort();
            var filled = new List<float>();
            for (int i = 0; i < bps.Count; i++)
            {
                filled.Add(bps[i]);
                if (i + 1 >= bps.Count) break;
                float gap = bps[i + 1] - bps[i];
                int n = (int)math.ceil(gap / MaxPiece);
                for (int k = 1; k < n; k++) filled.Add(bps[i] + gap * k / n);
            }
            var final = new List<float>();
            foreach (var x0 in filled)
            {
                float x = x0;
                if (x0 != uA && x0 != uB) x = OffUnder(x, p.Under, p.KeepOff);
                if (final.Count > 0 && x - final[final.Count - 1] < 4f) continue;
                final.Add(x);
            }
            float3 P(float u) { var q = new float3(o.x + d.x * u, 0, o.y + d.y * u); q.y = TerrainUtils.SampleHeight(ref heights, q); return q; }
            var pv = new Preview();
            for (int i = 0; i + 1 < final.Count; i++)
            {
                float s0 = final[i], s1 = final[i + 1];
                float e0 = ElevationAt(p, s0), e1 = ElevationAt(p, s1);
                float3 a = i == 0 && endA != null ? endA.Pos : P(s0), b = i == final.Count - 2 && endB != null ? endB.Pos : P(s1);
                float ha = TerrainUtils.SampleHeight(ref heights, a), hb = TerrainUtils.SampleHeight(ref heights, b);
                a.y = ha + e0; b.y = hb + e1;
                var curve = NetUtils.StraightCurve(a, b);
                if (math.abs(e0) < 0.05f && math.abs(e1) < 0.05f)
                {
                    curve.b.y = TerrainUtils.SampleHeight(ref heights, curve.b);
                    curve.c.y = TerrainUtils.SampleHeight(ref heights, curve.c);
                }
                else
                {
                    float segLen = math.max(1f, s1 - s0);
                    float tSlope = (hb - ha) / segLen;
                    float g0 = tSlope + ElevationSlopeAt(p, s0), g1 = tSlope + ElevationSlopeAt(p, s1);
                    float lo = math.min(curve.a.y, curve.d.y), hi = math.max(curve.a.y, curve.d.y);
                    curve.b.y = math.clamp(curve.a.y + g0 * (segLen / 3f), lo, hi);
                    curve.c.y = math.clamp(curve.d.y - g1 * (segLen / 3f), lo, hi);
                }
                var spec = new Spec { Prefab = prefab, Curve = curve, E0 = e0, E1 = e1 };
                if (i == 0 && endA != null) { spec.StartEntity = endA.Entity; spec.StartSplit = endA.Split; }
                if (i == final.Count - 2 && endB != null) { spec.EndEntity = endB.Entity; spec.EndSplit = endB.Split; }
                pv.Specs.Add(spec);
            }

            bool ramps = Mode != ToolMode.Overpass;
            string style = StyleName(Mode);
            int bridge = (int)(p.End - p.Start);
            if (endA == null && endB == null) joined = "";
            string ends = keep ? $"kept up at {Clearance:0} m all the way, its ends left raised for you to carry on elevated"
                : endA != null && endB != null ? $"joining {joined} on both sides"
                : endA != null || endB != null ? $"joining {joined} on one side and stopping short on the other for you to continue"
                : "stopping short on both sides for you to continue";
            pv.NextStep = ramps; pv.NextPos = at; pv.NextMode = Mode;
            pv.Log = $"new {typeName} across the highway ({bridge} m bridge, {ends})" + (ramps ? $", then a {style} interchange" : "");
            if (keep) bridge = (int)(uB - uA);
            pv.Status = $"A new {typeName} crosses the highway {(dig ? $"in a {bridge} m cutting under it" : $"on a {bridge} m bridge")}, {ends}."
                + (dig && !DigUnder ? " (Highway over needs a street already crossing at ground level, so the new street goes under instead.)" : "")
                + steeper + water + (ramps ? $" Then the {style} interchange ramps are added automatically." : "") + " Click to build.";
            return pv;
        }
    }
}
