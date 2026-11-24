using System.Collections.Generic;
using Colossal.Mathematics;
using Unity.Mathematics;

namespace InterchangeStudio.Core
{
    public partial class Planner
    {
        // Ring centreline radius; the island is smaller by half the chosen road width.
        float RingRadius => Size == 0 ? 24f : Size == 2 ? 36f : 30f;
        bool WriteRoundabout(Preview pv, Attach j, float3 travel, HashSet<Entity> deleted, HashSet<Entity> ignore, ref TerrainHeightData heights, List<Bezier4x3> curves, out Attach rampIn, out Attach rampOut, out string why)
        {
            rampIn = rampOut = null; why = "";
            Entity ring = RingPrefab();
            if (ring == Entity.Null) { why = "no one-way road type found for the roundabout"; return false; }
            // the street around the junction, as a short chain
            var q = new Plan();
            Entity street = j.Street != Entity.Null ? j.Street : j.Entity;
            float split = j.Street != Entity.Null ? j.StreetT : j.Split;
            var seg0 = MakeSeg(street, EntityManager.GetComponentData<Edge>(street).m_Start);
            var back = StreetBeyond(seg0.From, street, RingRadius + 8f);
            var fwd = StreetBeyond(seg0.To, street, RingRadius + 8f);
            float s = 0;
            for (int i = back.Count - 1; i >= 0; i--) { var r = Reverse(back[i]); r.S0 = s; q.Segs.Add(r); s += r.Length; }
            seg0.S0 = s; q.Segs.Add(seg0);
            float sJ = s + LengthAt(seg0, split);
            s += seg0.Length;
            foreach (var f in fwd) { f.S0 = s; q.Segs.Add(f); s += f.Length; }
            q.Total = s;
            float sA = sJ - RingRadius, sB = sJ + RingRadius;
            if (sA < 1f || sB > s - 1f) { why = "the street is too short around the junction for a roundabout"; return false; }
            List<Seg> Touched() { var l = new List<Seg>(); foreach (var sg in q.Segs) if (sg.S0 + sg.Length > sA + 0.01f && sg.S0 < sB - 0.01f) l.Add(sg); return l; }
            var touched = Touched();
            // a joint a few metres from where the ring meets the street (a new street's deck has them right there):
            // slide the ring onto it rather than leave a sliver of road
            if (touched.Count > 0)
            {
                float lead = sA - touched[0].S0, tail = touched[touched.Count - 1].S0 + touched[touched.Count - 1].Length - sB;
                float slide = lead > 0.01f && lead < 4f ? -lead : tail > 0.01f && tail < 4f ? tail : 0f;
                if (slide != 0f) { sA += slide; sB += slide; sJ += slide; touched = Touched(); }
            }
            if (touched.Count == 0 || touched.Exists(sg => deleted.Contains(sg.Edge)))
            { why = "the two terminals would rebuild the same street piece; use a crossing with more room"; return false; }
            foreach (var sg in touched)
                if (IsOneway(sg.Edge)) { why = "roundabout terminals need a two-way cross street"; return false; }
            float before = sA - touched[0].S0;
            float after = touched[touched.Count - 1].S0 + touched[touched.Count - 1].Length - sB;
            // (none at all is fine: the ring meets the street at its existing joint)
            if (before > 0.01f && before < 12f || after > 0.01f && after < 12f)
            { why = "a roundabout would leave a street stub shorter than 12 m; change Size or move the crossing"; return false; }
            float3 pa = Position(q, sA), pb = Position(q, sB), pc = Position(q, sJ);
            float2 streetDir = math.normalizesafe(pb.xz - pa.xz);
            if (math.abs(math.dot(streetDir, travel.xz)) > 0.2f ||
                math.abs(math.distance(pa.xz, pc.xz) - RingRadius) > 0.5f ||
                math.abs(math.distance(pb.xz, pc.xz) - RingRadius) > 0.5f ||
                math.abs(pa.y - pc.y) > 0.5f || math.abs(pb.y - pc.y) > 0.5f)
            { why = "roundabout terminals need a nearly straight, level cross street meeting the highway roughly square"; return false; }
            for (int i = 1; i < touched.Count; i++)
            {
                Classify(touched[i].From, m_Hw, m_Other, out int n);
                if (n > 2) { why = "a side street joins too close to the ramp junction for a roundabout"; return false; }
            }
            float3 c = pc; float ej = j.Elevation;
            float3 uPos = c - travel * RingRadius, wPos = c + travel * RingRadius;
            float hU = TerrainUtils.SampleHeight(ref heights, uPos), hW = TerrainUtils.SampleHeight(ref heights, wPos);
            if (ej <= 1.5f && (math.abs(hU - (c.y - ej)) > 2.5f || math.abs(hW - (c.y - ej)) > 2.5f))
            { why = "the ground slopes too steeply here for a level roundabout terminal"; return false; }
            foreach (var sg in touched)
            {
                if (deleted.Add(sg.Edge)) pv.Specs.Add(new Spec { Delete = true, Original = sg.Edge });
                ignore.Add(sg.Edge);
                string name = NameOf(sg.Edge);
                if (!string.IsNullOrEmpty(name)) pv.Names.Add((MathUtils.Position(sg.Curve, 0.5f), name, false));
            }
            var first = touched[0]; var last = touched[touched.Count - 1];
            // where the ring meets the street at an existing joint, the street piece beyond it touches the ring there
            int i0 = q.Segs.IndexOf(first), i1 = q.Segs.IndexOf(last);
            if (before <= 0.01f && i0 > 0) ignore.Add(q.Segs[i0 - 1].Edge);
            if (after <= 0.01f && i1 + 1 < q.Segs.Count) ignore.Add(q.Segs[i1 + 1].Edge);
            var A = Cut(pv, first, first.S0, sA, true, ref heights, curves);
            var B = Cut(pv, last, sB, last.S0 + last.Length, false, ref heights, curves);
            // the ring's four meeting points: street (both sides), ramp in (upstream), ramp out (downstream)
            // Keep world Y and Elevation strictly consistent with terrain so sloped ground never twists the ring.
            bool onDeck = math.abs(ej) > 1.5f;
            float eU = onDeck ? c.y - hU : ej, eW = onDeck ? c.y - hW : ej;
            if (math.abs(eU) < 0.05f) eU = 0f;
            if (math.abs(eW) < 0.05f) eW = 0f;
            var U = new Attach { Pos = new float3(uPos.x, onDeck ? c.y : hU + ej, uPos.z), Elevation = eU };
            var W = new Attach { Pos = new float3(wPos.x, onDeck ? c.y : hW + ej, wPos.z), Elevation = eW };
            WriteRing(pv, c, RingRadius, new List<Attach> { A, B, U, W }, ring, curves);
            rampIn = U; rampOut = W;
            return true;
        }

        /* one-way arcs anticlockwise (right-hand traffic) round centre c through the given points */
        void WriteRing(Preview pv, float3 c, float radius, List<Attach> pts, Entity ring, List<Bezier4x3> curves)
        {
            pts.Sort((a, b) => Angle(a.Pos, c).CompareTo(Angle(b.Pos, c)));
            for (int i = 0; i < pts.Count; i++)
            {
                var a = pts[i]; var b = pts[(i + 1) % pts.Count];
                float t0 = Angle(a.Pos, c), t1 = Angle(b.Pos, c); if (t1 <= t0) t1 += 2 * math.PI;
                if (t1 - t0 > math.PI * 0.75f)
                {
                    // a long arc: split it so each piece stays round
                    float tm = (t0 + t1) * 0.5f;
                    var m = new Attach { Pos = new float3(c.x + math.cos(tm) * radius, (a.Pos.y + b.Pos.y) * 0.5f, c.z + math.sin(tm) * radius), Elevation = (a.Elevation + b.Elevation) * 0.5f };
                    Arc(pv, c, radius, a, m, t0, tm, ring, curves);
                    Arc(pv, c, radius, m, b, tm, t1, ring, curves);
                }
                else Arc(pv, c, radius, a, b, t0, t1, ring, curves);
            }
        }

        void Arc(Preview pv, float3 c, float radius, Attach a, Attach b, float t0, float t1, Entity ring, List<Bezier4x3> curves)
        {
            float k = 4f / 3f * math.tan((t1 - t0) / 4f) * radius;
            float3 d0 = new float3(-math.sin(t0), 0, math.cos(t0)), d1 = new float3(-math.sin(t1), 0, math.cos(t1));
            var arc = new Bezier4x3(a.Pos, a.Pos + d0 * k, b.Pos - d1 * k, b.Pos);
            arc.b.y = math.lerp(a.Pos.y, b.Pos.y, 1f / 3f); arc.c.y = math.lerp(a.Pos.y, b.Pos.y, 2f / 3f);
            Ramp(pv, ring, arc, a, b, a.Elevation, b.Elevation, curves);
        }

        static float Angle(float3 p, float3 c) => math.atan2(p.z - c.z, p.x - c.x);

        /* keep the part of one street piece between two positions; returns the cut end as a ring point */
        Attach Cut(Preview pv, Seg sg, float s0, float s1, bool cutAtEnd, ref TerrainHeightData heights, List<Bezier4x3> curves)
        {
            float t0 = TAt(sg, s0 - sg.S0), t1 = TAt(sg, s1 - sg.S0);
            float3 at = MathUtils.Position(sg.Curve, cutAtEnd ? t1 : t0);
            float eAt = at.y - TerrainUtils.SampleHeight(ref heights, at);
            if (math.abs(eAt) < 0.05f) eAt = 0f;
            var point = new Attach { Pos = at, Elevation = eAt };
            if (s1 - s0 < 2f) { point.Entity = cutAtEnd ? sg.From : sg.To; point.Pos = NodePos(point.Entity); return point; }
            var piece = MathUtils.Cut(sg.Curve, new float2(t0, t1));
            Entity node = cutAtEnd ? sg.From : sg.To;
            float en = NodeElevation(node);
            var spec = new Spec { Prefab = PrefabOf(sg.Edge) };
            float eStart = cutAtEnd ? en : point.Elevation, eEnd = cutAtEnd ? point.Elevation : en;
            Entity startE = cutAtEnd ? node : Entity.Null, endE = cutAtEnd ? Entity.Null : node;
            if (sg.Forward) { spec.Curve = piece; spec.StartEntity = startE; spec.EndEntity = endE; spec.E0 = eStart; spec.E1 = eEnd; }
            else { spec.Curve = MathUtils.Invert(piece); spec.StartEntity = endE; spec.EndEntity = startE; spec.E0 = eEnd; spec.E1 = eStart; }
            if (EntityManager.HasComponent<Upgraded>(sg.Edge)) { spec.HasUpgrade = true; spec.Upgrade = EntityManager.GetComponentData<Upgraded>(sg.Edge).m_Flags; }
            pv.Specs.Add(spec);
            curves.Add(piece);
            return point;
        }

        /* the street carrying on beyond a node, away from 'from', for at least 'need' metres */
        List<Seg> StreetBeyond(Entity node, Entity from, float need, Entity firstEdge = default)
        {
            var list = new List<Seg>(); Entity at = node, cur = from; float total = 0;
            if (firstEdge != Entity.Null)
            {
                var f = MakeSeg(firstEdge, node); list.Add(f); total += f.Length; at = f.To; cur = firstEdge;
            }
            for (int guard = 0; guard < 10 && total < need; guard++)
            {
                var cv = EntityManager.GetComponentData<Curve>(cur).m_Bezier; var ce = EntityManager.GetComponentData<Edge>(cur);
                float3 dir = ce.m_End == at ? MathUtils.EndTangent(cv) : -MathUtils.StartTangent(cv);
                Classify(at, m_Hw, m_Other, out _);
                Entity next = Entity.Null; float best = 0.7f;
                foreach (var o in m_Other)
                {
                    if (o == cur) continue;
                    var oc = EntityManager.GetComponentData<Curve>(o).m_Bezier; var oe = EntityManager.GetComponentData<Edge>(o);
                    float3 od = oe.m_Start == at ? MathUtils.StartTangent(oc) : -MathUtils.EndTangent(oc);
                    float d = math.dot(math.normalizesafe(dir.xz), math.normalizesafe(od.xz));
                    if (d > best) { best = d; next = o; }
                }
                if (next == Entity.Null) break;
                var sg = MakeSeg(next, at); list.Add(sg); total += sg.Length;
                at = sg.To; cur = next;
            }
            return list;
        }

        /*
         * The roundabout's road type: a 3-lane one-way highway (the author, 2026-10-31: "the 3ln hwy works better than just
         * the single lane"; he had rebuilt a ring that way), else the narrowest ordinary one-way road.
         */
        Entity RingPrefab() => Named("Highway Oneway - 3 lanes", "Roundabout") is var e && e != Entity.Null ? e : OnewayRoad(7.5f, 12f, widest: false, "Roundabout");

        /* a road type by its exact vanilla name (found once); Entity.Null when the game doesn't have it */
        Entity Named(string name, string purpose)
        {
            string key = purpose + ":" + name;
            if (m_Oneways.TryGetValue(key, out var cached) && EntityManager.Exists(cached)) return cached;
            using (var ents = m_RoadPrefabs.ToEntityArray(Allocator.Temp))
                foreach (var e in ents)
                    if (m_PrefabSystem.GetPrefabName(e) == name)
                    {
                        Log.Info($"{purpose} road type: {name}");
                        m_Oneways[key] = e;
                        return e;
                    }
            return Entity.Null;
        }

        /*
         * An ordinary one-way city road between two widths, found by name once. Only roads named "Road": the game
         * also has one-way alleys, and the first roundabouts were built from "Alley Oneway" (2026-10-31).
         */
        private readonly Dictionary<string, Entity> m_Oneways = new Dictionary<string, Entity>();
        Entity OnewayRoad(float minWidth, float maxWidth, bool widest, string purpose)
        {
            if (m_Oneways.TryGetValue(purpose, out var cached) && EntityManager.Exists(cached)) return cached;
            Entity found = Entity.Null; float best = 0; string chosen = "";
            using (var ents = m_RoadPrefabs.ToEntityArray(Allocator.Temp))
                foreach (var e in ents)
                {
                    string n = m_PrefabSystem.GetPrefabName(e);
                    if (n == null || !n.Contains("Oneway") || !n.Contains("Road") || n.Contains("Highway") || n.Contains("Alley") || n.Contains("Gravel")
                        || n.Contains("Bus") || n.Contains("Tram") || n.Contains("Pedestrian") || n.Contains("Parking")) continue;
                    float w = WidthOfPrefab(e);
                    if (w < minWidth || w > maxWidth) continue;
                    bool better = found == Entity.Null || (widest ? w > best : w < best) || w == best && string.CompareOrdinal(n, chosen) < 0;
                    if (better) { best = w; found = e; chosen = n; }
                }
            if (found == Entity.Null) return Entity.Null;
            Log.Info($"{purpose} road type: {chosen}");
            m_Oneways[purpose] = found;
            return found;
        }
    }
}

