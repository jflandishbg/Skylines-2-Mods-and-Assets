// Interchange Studio - Core/Planner.NewHighway.cs
// The reverse of the other tools (2026-10-23, the author: "you have the existing ave, hickory st, then you click a
// point there and it draws the highway above it and potentially the intersection"): point at a street with
// no highway near and click. A divided highway is laid square across it, going over it on a bridge, its
// four ends left at ground level (or raised, with Keep elevated) for the player to carry on; in Diamond or
// Single-point the ramps follow automatically, as for any highway crossing a street.
using System.Collections.Generic;
using Colossal.Mathematics;
using Unity.Mathematics;

namespace InterchangeStudio.Core
{
    public partial class Planner
    {
        const float NewHighwayRun = 300f;       // level highway beyond each slope: room for the ramps to leave and join
        const float NewHighwayMedian = 5f;      // between the two carriageways (the Admiral Electron stamps use about this)

        long m_NewHwPrefVer = -1;
        Entity m_NewHwPrefCache = Entity.Null;
        string m_NewHwPrefLabel = "";

        /// <summary>The multi-lane one-way highway type most used in the city by total length (never a 1-lane ramp), else the 2-lane one.</summary>
        Entity NewHighwayPrefab(out string label)
        {
            if (m_NewHwPrefVer == EntityManager.Version && m_NewHwPrefCache != Entity.Null && EntityManager.Exists(m_NewHwPrefCache))
            { label = m_NewHwPrefLabel; return m_NewHwPrefCache; }
            var lengthByPrefab = new Dictionary<Entity, float>();
            using (var ents = m_RoadEdges.ToEntityArray(Allocator.Temp))
                foreach (var e in ents)
                {
                    if (!IsHighway(e) || !IsOneway(e)) continue;
                    var p = PrefabOf(e);
                    string pn = m_PrefabSystem.GetPrefabName(p) ?? "";
                    if (pn.Contains("1 lane") || WidthOfPrefab(p) < 8f) continue;      // skip 1-lane ramps
                    float len = EntityManager.GetComponentData<Curve>(e).m_Length;
                    lengthByPrefab[p] = (lengthByPrefab.TryGetValue(p, out float cur) ? cur : 0f) + len;
                }
            Entity best = Entity.Null; float longest = 0f;
            foreach (var kv in lengthByPrefab) if (kv.Value > longest) { longest = kv.Value; best = kv.Key; }
            if (best == Entity.Null) best = Named("Highway Oneway - 2 lanes", "New highway");
            if (best == Entity.Null) best = Named("Highway Oneway - 3 lanes", "New highway");
            label = best != Entity.Null ? m_PrefabSystem.GetPrefabName(best) : "";
            m_NewHwPrefVer = EntityManager.Version; m_NewHwPrefCache = best; m_NewHwPrefLabel = label;
            return best;
        }

        Preview NewHighwayPreview(Entity street, RaycastHit hit)
        {
            string name = NameOf(street) ?? m_PrefabSystem.GetPrefabName(PrefabOf(street));
            string what = $"Can't put a highway over {name} here";
            var hwPrefab = NewHighwayPrefab(out string hwName);
            if (hwPrefab == Entity.Null) return FailFinal(what, "no highway road type found");
            var heights = m_TerrainSystem.GetHeightData(false);
            var sc = EntityManager.GetComponentData<Curve>(street).m_Bezier;
            float3 at = MathUtils.Position(sc, hit.m_CurvePosition);
            if (at.y - TerrainUtils.SampleHeight(ref heights, at) > 2f) return FailFinal(what, $"{name} is raised here; point where it runs at ground level");
            float2 ts = math.normalizesafe(MathUtils.Tangent(sc, hit.m_CurvePosition).xz);
            float2 t = new float2(-ts.y, ts.x);                       // the highway runs square across the street
            float2 right = new float2(t.y, -t.x);                     // right of travel (right-hand traffic)
            float hwHalf = WidthOfPrefab(hwPrefab) * 0.5f, streetHalf = WidthOf(street) * 0.5f;
            float off = hwHalf + NewHighwayMedian * 0.5f;
            bool keep = KeepUp;

            // the bridge over the street, as when a highway is lifted over a street (PlanHighwayBridge)
            float margin = streetHalf + 14f, ramp = Clearance / Grade, minRamp = Clearance / MaxGrade;
            const float MaxDeckReach = 900f;      // in a dense grid, the highway stays up at most this far each side
            float look = MaxDeckReach + ramp + NewHighwayRun;

            // every road crossing either carriageway's line, nearest crossing per road, by side
            var hits = new Dictionary<Entity, (float u, string n, float half)>();
            foreach (int k in new[] { 1, -1 })
            {
                float2 o = at.xz + right * off * k;
                foreach (var e in RoadsNear(o - look - 20f, o + look + 20f))
                {
                    if (e == street || !Live(e) || !EntityManager.HasComponent<Curve>(e)) continue;
                    var c = EntityManager.GetComponentData<Curve>(e).m_Bezier;
                    if (!LineMeets(o, t, c, out float u, out float tt) || math.abs(u) > look) continue;
                    if (EntityManager.HasComponent<Edge>(e))
                    {
                        // the street itself, continuing in another piece, is what the bridge is for
                        var ed = EntityManager.GetComponentData<Edge>(e); var sed = EntityManager.GetComponentData<Edge>(street);
                        if (math.abs(u) < margin && (ed.m_Start == sed.m_Start || ed.m_Start == sed.m_End || ed.m_End == sed.m_Start || ed.m_End == sed.m_End)) continue;
                    }
                    float3 q = MathUtils.Position(c, tt);
                    if (q.y - TerrainUtils.SampleHeight(ref heights, q) > Clearance + 2f) continue;           // high above
                    string n = NameOf(e) ?? m_PrefabSystem.GetPrefabName(PrefabOf(e));
                    if (IsHighway(e) && math.abs(u) < MaxDeckReach) return FailFinal(what, $"another highway ({n}) runs {(int)math.abs(u)} m away, across the line; point elsewhere");
                    if (!hits.TryGetValue(e, out var h) || math.abs(u) < math.abs(h.u)) hits[e] = (u, n, WidthOf(e) * 0.5f);
                }
            }

            // railway tracks crossing the line must also be spanned (never build a level rail crossing)
            foreach (int k in new[] { 1, -1 })
            {
                float2 o = at.xz + right * off * k;
                foreach (var tr in TracksNear(o - look - 20f, o + look + 20f))
                {
                    if (!Live(tr) || !EntityManager.HasComponent<Curve>(tr)) continue;
                    var c = EntityManager.GetComponentData<Curve>(tr).m_Bezier;
                    if (!LineMeets(o, t, c, out float u, out float tt) || math.abs(u) > look) continue;
                    float3 q = MathUtils.Position(c, tt);
                    if (q.y - TerrainUtils.SampleHeight(ref heights, q) > Clearance + 2f) continue;
                    float trHalf = math.max(5f, WidthOf(tr) * 0.5f);
                    if (!hits.TryGetValue(tr, out var h) || math.abs(u) < math.abs(h.u)) hits[tr] = (u, "a railway track", trHalf);
                }
            }

            // footpaths crossing the line count too: the highway spans them like streets, pillars kept off
            foreach (int k in new[] { 1, -1 })
            {
                float2 o = at.xz + right * off * k;
                foreach (var path in EntityManager.Paths)
                {
                    var b = path.Curve;
                    float2 lo = math.min(math.min(b.a.xz, b.b.xz), math.min(b.c.xz, b.d.xz)), hi = math.max(math.max(b.a.xz, b.b.xz), math.max(b.c.xz, b.d.xz));
                    float2 o2 = o + t * look;
                    if (math.any(hi < math.min(o - t * look, o2) - 20f) || math.any(lo > math.max(o - t * look, o2) + 20f)) continue;
                    if (!LineMeets(o, t, b, out float u, out float tt) || math.abs(u) > look || math.abs(u) < margin) continue;
                    float3 q = MathUtils.Position(b, tt);
                    if (q.y - TerrainUtils.SampleHeight(ref heights, q) > Clearance + 2f || q.y - TerrainUtils.SampleHeight(ref heights, q) < -2f) continue;
                    if (!hits.TryGetValue(path.Id, out var h) || math.abs(u) < math.abs(h.u)) hits[path.Id] = (u, "a footpath", path.Width * 0.5f);
                }
            }

            // each side, outwards: every street within reach of the slope is spanned (pillars kept off it) and the
            // deck carries on past it; the slope goes in the first gap long enough (steepened up to MaxGrade)
            var p = new Plan { KeepOff = streetHalf + 12f };
            p.Under.Add(0f);
            float uLo = 0, uHi = 0; var spanned = new List<string>(); string steeper = "", water = ""; bool raisedEnds = false, shoreEnd = false;
            var rampAt = new[] { RampReach, RampReach };      // where the ramps will join, each side (south/west first)
            foreach (int side in new[] { 1, -1 })
            {
                var list = new List<(float d, string n, float half)>();
                foreach (var kv in hits) if (kv.Value.u * side > 0f) list.Add((math.abs(kv.Value.u), kv.Value.n, kv.Value.half));
                list.Sort((x, y) => x.d.CompareTo(y.d));
                float deck = margin, slope = ramp, endAt = 0; bool done = false;
                for (int i = 0; i <= list.Count && !done; i++)
                {
                    float next = i < list.Count ? list[i].d : float.MaxValue;
                    float room = next - deck - 15f;                       // a slope needs room before the next road, plus a little level
                    if (!keep && room >= minRamp)
                    {
                        slope = math.min(ramp, room);
                        if (slope < ramp - 1f) steeper = $" A slope is steepened to {Clearance / slope * 100f:0.#}% to come down between streets.";
                        // just long enough: past the slope, and (with ramps) 60 m past where they will join it, which is
                        // out on the level beyond the slope (the author, 2026-11-01: ramps on a rising piece glitch)
                        rampAt[side > 0 ? 1 : 0] = math.max(RampReach, deck + slope + math.max(LevelRun, Splits.GoreClear) + 5f);   // its joint keeps the foot of the slope
                        float want = Mode == ToolMode.Overpass ? deck + slope + 40f : math.max(deck + slope + 20f, rampAt[side > 0 ? 1 : 0] + 60f);
                        endAt = math.min(want, next - 30f);
                        done = true;
                    }
                    else if (i < list.Count && (keep ? next < deck + KeptUpReach : true) && next + list[i].half + 14f <= MaxDeckReach)
                    {
                        p.Under.Add(next * side); p.KeepOff = math.max(p.KeepOff, list[i].half + 12f);
                        if (!spanned.Contains(list[i].n)) spanned.Add(list[i].n);
                        deck = next + list[i].half + 14f;
                    }
                    else { endAt = keep ? deck + KeptUpReach : deck + 40f; slope = 0; raisedEnds = true; done = true; }
                }
                // water at ground level or low on the slope ahead: check across both carriageways, stop short or stay raised
                if (slope > 0f)
                {
                    float totalHalf = off + hwHalf;
                    float wet = WaterAlong(at.xz, t, deck * side, slope, endAt * side, side, totalHalf);
                    if (!float.IsNaN(wet))
                    {
                        // no room to come down before the water: this end stays raised and stops at the water's edge
                        if (wet <= deck + slope + 15f) { endAt = math.max(deck + 10f, wet - 5f); slope = 0f; shoreEnd = true; }
                        else { endAt = math.max(deck + slope + 5f, wet - math.max(15f, hwHalf + 10f)); water = " It stops short of the water."; }
                    }
                }
                // a raised end stays up all the way to its end; otherwise the slope starts at the deck's edge
                if (side > 0) { p.RampDown = slope == 0 ? endAt : deck; p.End = slope == 0 ? endAt + 1f : deck + slope; uHi = endAt; }
                else { p.RampUp = slope == 0 ? -endAt : -deck; p.Start = slope == 0 ? -endAt - 1f : -deck - slope; uLo = -endAt; }
            }

            // two carriageways, each one way, traffic keeping right; pieces at most MaxPiece, no pillar on the street
            var bps = new List<float> { uLo, uHi, p.Start, p.RampUp, p.RampDown, p.End };
            // a joint exactly where the ramps will join (PlaceRampEnds: RampReach, or the level beyond the slope), clear of other joints by the
            // 55 m a ramp's split needs, so they have somewhere clean to leave and rejoin
            bool ramps0 = Mode != ToolMode.Overpass;
            var joins = new List<float>();
            if (ramps0) foreach (float r in new[] { -rampAt[0], rampAt[1] }) if (r > uLo + Splits.GoreClear && r < uHi - Splits.GoreClear) { bps.Add(r); joins.Add(r); }
            bps.RemoveAll(x => x < uLo || x > uHi);
            bps.Sort();
            var filled = new List<float>();
            for (int i = 0; i < bps.Count; i++)
            {
                filled.Add(bps[i]);
                if (i + 1 >= bps.Count) break;
                float gap = bps[i + 1] - bps[i];
                int n = (int)math.ceil(gap / MaxPiece);
                for (int j = 1; j < n; j++) filled.Add(bps[i] + gap * j / n);
            }
            var final = new List<float>();
            foreach (var x0 in filled)
            {
                float x = x0 == uLo || x0 == uHi ? x0 : OffUnder(x0, p.Under, p.KeepOff);
                if (final.Count > 0 && x - final[final.Count - 1] < 4f) continue;
                final.Add(x);
            }

            foreach (float r in joins) final.RemoveAll(x => x != r && x != uLo && x != uHi && math.abs(x - r) < Splits.GoreClear);
            final.Sort();

            // each raised joint is a pillar on both carriageways: keep it off any footpath or street that runs
            // underneath at an angle or alongside (crossing ones are handled above). Slide it up to 30 m; failing
            // that, drop it if the span stays reasonable (2026-10-23 self-test: pillars on park paths).
            var under = new List<(Bezier4x3 c, float half)>();
            float2 boxLo = at.xz - (math.abs(uLo) + math.abs(uHi) + 40f), boxHi = at.xz + (math.abs(uLo) + math.abs(uHi) + 40f);
            foreach (var path in EntityManager.Paths) under.Add((path.Curve, path.Width * 0.5f));
            foreach (var e in RoadsNear(boxLo, boxHi))
                if (e != street && Live(e) && !IsHighway(e)) under.Add((EntityManager.GetComponentData<Curve>(e).m_Bezier, WidthOf(e) * 0.5f));
            foreach (var tr in TracksNear(boxLo, boxHi))
                if (Live(tr) && EntityManager.HasComponent<Curve>(tr)) under.Add((EntityManager.GetComponentData<Curve>(tr).m_Bezier, math.max(5f, WidthOf(tr) * 0.5f)));
            bool Clear(float u)
            {
                foreach (int k in new[] { 1, -1 })
                {
                    float2 q = at.xz + right * off * k + t * u;
                    foreach (var (c, half) in under)
                    {
                        if (math.abs(c.a.y - TerrainUtils.SampleHeight(ref heights, c.a)) > Clearance + 2f) continue;
                        if (MathUtils.Distance(c.xz, q, out float _) < half + hwHalf * 0.5f + 3f) return false;
                    }
                }
                return true;
            }
            for (int i = 1; i + 1 < final.Count; i++)
            {
                if (ElevationAt(p, final[i]) < 0.5f || Clear(final[i])) continue;
                float lo = final[i - 1] + 8f, hi = final[i + 1] - 8f, moved = float.NaN;
                for (float dlt = 4f; dlt <= 30f && float.IsNaN(moved); dlt += 4f)
                    foreach (float cand in new[] { final[i] - dlt, final[i] + dlt })
                        if (cand > lo && cand < hi && math.abs(OffUnder(cand, p.Under, p.KeepOff) - cand) < 0.01f && Clear(cand)) { moved = cand; break; }
                if (!float.IsNaN(moved)) final[i] = moved;
                else if (final[i + 1] - final[i - 1] <= 120f) { final.RemoveAt(i); i--; }
            }
            var pv = new Preview();
            foreach (int k in new[] { 1, -1 })
            {
                float2 o = at.xz + right * off * k;
                float3 P(float u) { var q = new float3(o.x + t.x * u * k, 0, o.y + t.y * u * k); q.y = TerrainUtils.SampleHeight(ref heights, q); return q; }
                // k = +1 flows along t on the right-hand side; k = -1 flows back along -t on the other side
                var us = new List<float>(final);
                if (k < 0) { us.Reverse(); for (int i = 0; i < us.Count; i++) us[i] = -us[i]; }
                for (int i = 0; i + 1 < us.Count; i++)
                {
                    float s0 = us[i], s1 = us[i + 1];
                    float e0 = ElevationAt(p, s0 * k), e1 = ElevationAt(p, s1 * k);
                    float3 a = P(s0), b = P(s1);
                    float ha = a.y, hb = b.y;
                    a.y = ha + e0; b.y = hb + e1;
                    var curve = NetUtils.StraightCurve(a, b);
                    if (math.abs(e0) < 0.05f && math.abs(e1) < 0.05f)
                    {
                        curve.b.y = TerrainUtils.SampleHeight(ref heights, curve.b);
                        curve.c.y = TerrainUtils.SampleHeight(ref heights, curve.c);
                    }
                    else
                    {
                        float segLen = math.max(1f, math.abs(s1 - s0));
                        float tSlope = (hb - ha) / segLen;
                        float g0 = tSlope + ElevationSlopeAt(p, s0 * k) * k;
                        float g1 = tSlope + ElevationSlopeAt(p, s1 * k) * k;
                        float lo = math.min(curve.a.y, curve.d.y), hi = math.max(curve.a.y, curve.d.y);
                        curve.b.y = math.clamp(curve.a.y + g0 * (segLen / 3f), lo, hi);
                        curve.c.y = math.clamp(curve.d.y - g1 * (segLen / 3f), lo, hi);
                    }
                    pv.Specs.Add(new Spec { Prefab = hwPrefab, Curve = curve, E0 = e0, E1 = e1 });
                }
            }

            bool ramps = Mode != ToolMode.Overpass;
            string style = StyleName(Mode);
            int length = (int)(uHi - uLo);
            pv.NextStep = ramps; pv.NextPos = at; pv.NextMode = Mode;
            bool up = keep || raisedEnds;
            string over = spanned.Count == 0 ? "" : $" It stays up over {spanned.Count} more street{(spanned.Count == 1 ? "" : "s")} ({string.Join(", ", spanned.GetRange(0, math.min(4, spanned.Count)))}{(spanned.Count > 4 ? ", ..." : "")}), keeping its pillars off them.";
            pv.Log = $"new {hwName} over {name} ({length} m, {(up ? "ends raised" : "ends at ground")}, {spanned.Count} more street(s) spanned)" + (ramps ? $", then a {style} interchange" : "");
            pv.Status = $"A new highway ({hwName}, both directions) goes over {name} on a bridge ({length} m of new highway), "
                + (keep ? $"kept up at {Clearance:0} m with its ends left raised for you to carry on elevated."
                    : raisedEnds ? "with its ends left raised: the streets here are too close together for it to come down within reach, so carry it on elevated (or turn on Keep elevated)."
                    : "with its four ends left at ground level for you to carry on.") + over + steeper + water
                + (shoreEnd && !keep ? " Water comes too soon for it to come down on one side, so that end is left raised at the water's edge; carry it on as a bridge." : "")
                + (ramps ? $" Then the {style} interchange ramps are added automatically." : "") + " Click to build.";
            return pv;
        }
    }
}
