using System;
using System.Collections.Generic;

namespace WaterfrontAuto.Core
{
    /// <summary>
    /// Helpers for curved ExistingNetSegments (quadratic curve passing through Start, Mid at t=0.5, End)
    /// and polygon containment. Used by EntityMatcher, ShorelineDetector, WaterfrontPlanner, and PlanValidator.
    /// </summary>
    internal static class NetShape
    {
        public static Vec2 QuadThroughMid(Vec2 a, Vec2 mid, Vec2 b, float t)
        {
            if (mid.LengthSq < 1e-6f && (a.LengthSq > 1f || b.LengthSq > 1f))
                return Vec2.Lerp(a, b, t);
            Vec2 linearMid = (a + b) * 0.5f;
            if (Vec2.DistanceSq(mid, linearMid) < 0.01f)
                return Vec2.Lerp(a, b, t);
            Vec2 ctrl = mid * 2f - linearMid;
            float u = 1f - t;
            return a * (u * u) + ctrl * (2f * u * t) + b * (t * t);
        }

        public static void IndexNet(SpatialGrid2D<ExistingNetSegment> grid, ExistingNetSegment net)
        {
            Vec2 a = net.Start.XZ, b = net.End.XZ, mid = net.Mid.XZ;
            bool hasMid = (mid.LengthSq > 1e-6f || (a.LengthSq < 1f && b.LengthSq < 1f))
                && Vec2.DistanceSq(mid, (a + b) * 0.5f) > 0.04f;
            if (hasMid) grid.AddCurve(a, mid, b, net);
            else grid.AddSegment(a, b, net);
        }

        public static float DistanceToNet(Vec2 p, ExistingNetSegment net, out Vec2 closest)
        {
            Vec2 a = net.Start.XZ, b = net.End.XZ, mid = net.Mid.XZ;
            bool curved = (mid.LengthSq > 1e-6f || (a.LengthSq < 1f && b.LengthSq < 1f))
                && Vec2.DistanceSq(mid, (a + b) * 0.5f) > 0.04f;
            if (!curved)
                return Geom2D.PointToSegmentDist(p, a, b, out _, out closest);

            float best = float.MaxValue;
            closest = a;
            Vec2 prev = a;
            for (int k = 1; k <= 4; k++)
            {
                Vec2 next = QuadThroughMid(a, mid, b, k * 0.25f);
                float d = Geom2D.PointToSegmentDist(p, prev, next, out _, out Vec2 c);
                if (d < best) { best = d; closest = c; }
                prev = next;
            }
            return best;
        }

        public static bool SegmentHitsNet(Vec2 s0, Vec2 s1, ExistingNetSegment net, float margin)
        {
            Vec2 a = net.Start.XZ, b = net.End.XZ, mid = net.Mid.XZ;
            bool curved = (mid.LengthSq > 1e-6f || (a.LengthSq < 1f && b.LengthSq < 1f))
                && Vec2.DistanceSq(mid, (a + b) * 0.5f) > 0.04f;
            if (!curved)
                return SegmentNearSegment(s0, s1, a, b, margin);

            Vec2 prev = a;
            for (int k = 1; k <= 4; k++)
            {
                Vec2 next = QuadThroughMid(a, mid, b, k * 0.25f);
                if (SegmentNearSegment(s0, s1, prev, next, margin)) return true;
                prev = next;
            }
            return false;
        }

        private static bool SegmentNearSegment(Vec2 a0, Vec2 a1, Vec2 b0, Vec2 b1, float margin)
        {
            if (Geom2D.SegmentsIntersect(a0, a1, b0, b1)) return true;
            if (margin <= 0f) return false;
            if (Geom2D.PointToSegmentDist(a0, b0, b1, out _, out _) < margin) return true;
            if (Geom2D.PointToSegmentDist(a1, b0, b1, out _, out _) < margin) return true;
            if (Geom2D.PointToSegmentDist((a0 + a1) * 0.5f, b0, b1, out _, out _) < margin) return true;
            if (Geom2D.PointToSegmentDist(b0, a0, a1, out _, out _) < margin) return true;
            if (Geom2D.PointToSegmentDist(b1, a0, a1, out _, out _) < margin) return true;
            return false;
        }

        public static bool PointInPolygon(Vec2 p, Vec2[] ring)
        {
            if (ring == null || ring.Length < 3) return false;
            bool inside = false;
            int n = ring.Length;
            for (int i = 0, j = n - 1; i < n; j = i++)
            {
                Vec2 a = ring[i], b = ring[j];
                bool intersect = ((a.Z > p.Z) != (b.Z > p.Z)) &&
                    (p.X < (b.X - a.X) * (p.Z - a.Z) / (b.Z - a.Z + 1e-7f) + a.X);
                if (intersect) inside = !inside;
            }
            return inside;
        }
    }

    /// <summary>
    /// Pure geometry validator and filter run at the end of WaterfrontPlanner.Plan and in offline tests.
    /// Prevents road/rail overlaps, building overlaps, opposing canal-bank sand overlaps, steep ramps, and slivers.
    /// </summary>
    public static class PlanValidator
    {
        public static int ValidateAndFilter(
            WaterfrontPlan plan,
            IReadOnlyList<BuildingLot> buildings,
            IReadOnlyList<ExistingNetSegment> existingNets,
            IWorldSampler sampler,
            WaterfrontConfig cfg)
        {
            if (plan == null) return 0;
            cfg = cfg ?? new WaterfrontConfig();
            var buildingGrid = ShorelineDetector.BuildBuildingGrid(buildings);
            var netGrid = ShorelineDetector.BuildNetGrid(existingNets);
            var nearNets = new List<ExistingNetSegment>(24);
            var nearBldgs = new List<BuildingLot>(24);
            int removed = 0;

            // 1. Validate and filter PlannedNets
            for (int i = plan.Nets.Count - 1; i >= 0; i--)
            {
                var n = plan.Nets[i];
                if (n == null) { plan.Nets.RemoveAt(i); removed++; continue; }
                float len = Vec2.Distance(n.A.XZ, n.D.XZ);
                bool drop = len < 2.2f;

                if (!drop && (n.Role == NetRole.AccessSpur || n.IsBeachCurl))
                {
                    float grade = Math.Abs(n.D.Y - n.A.Y) / Math.Max(1f, len);
                    if (grade > cfg.MaxPedestrianGrade + 0.02f) drop = true;
                }

                if (!drop && existingNets != null && existingNets.Count > 0)
                {
                    Vec2 mid = (n.A.XZ + n.D.XZ) * 0.5f;
                    netGrid.QueryRadius(mid, len * 0.5f + 22f, nearNets);
                    for (int k = 0; k < nearNets.Count; k++)
                    {
                        var en = nearNets[k];
                        if (en.IsGeneratedByUs || (!en.IsRoad && !en.IsRail)) continue;
                        float halfW = en.Width * 0.5f;
                        if (n.Role == NetRole.AccessSpur && en.IsRoad)
                        {
                            // Spur end D is allowed to meet the sidewalk edge, never enter the carriageway
                            float dEnd = NetShape.DistanceToNet(n.D.XZ, en, out _);
                            float dMid = NetShape.DistanceToNet(mid, en, out _);
                            if (dEnd < halfW - 0.1f || dMid < halfW - 0.1f) { drop = true; break; }
                        }
                        else if (NetShape.SegmentHitsNet(n.A.XZ, n.D.XZ, en, halfW + 0.25f))
                        {
                            drop = true;
                            break;
                        }
                    }
                }

                if (drop)
                {
                    if (n.IsBeachCurl && plan.BeachCurls > 0) plan.BeachCurls--;
                    if (n.Role == NetRole.AccessSpur && plan.AccessSpurs > 0) plan.AccessSpurs--;
                    if (n.Role == NetRole.IndustrialPier && plan.FingerPiers > 0) plan.FingerPiers--;
                    plan.Nets.RemoveAt(i);
                    removed++;
                }
            }

            // 2. Validate and filter PlannedSurfaces (road/rail overlap + opposing canal bank sand overlap)
            var keptSand = new List<(int chainId, Vec2 lo, Vec2 hi, Vec2[] ring)>();
            for (int i = plan.Surfaces.Count - 1; i >= 0; i--)
            {
                var s = plan.Surfaces[i];
                if (s == null || s.Ring == null || s.Ring.Length < 3 || Math.Abs(Geom2D.SignedArea(s.Ring)) < 4f)
                {
                    plan.Surfaces.RemoveAt(i); removed++; continue;
                }

                RingBounds(s.Ring, out Vec2 lo, out Vec2 hi, out Vec2 center);
                float rad = Vec2.Distance(lo, hi) * 0.5f + 16f;
                bool drop = false;

                if (existingNets != null && existingNets.Count > 0)
                {
                    netGrid.QueryRadius(center, rad, nearNets);
                    for (int k = 0; k < nearNets.Count && !drop; k++)
                    {
                        var en = nearNets[k];
                        if (en.IsGeneratedByUs || (!en.IsRoad && !en.IsRail)) continue;
                        float margin = en.Width * 0.5f + 0.6f;
                        if (NetShape.DistanceToNet(center, en, out _) < margin) { drop = true; break; }
                        for (int v = 0; v < s.Ring.Length; v++)
                            if (NetShape.DistanceToNet(s.Ring[v], en, out _) < margin) { drop = true; break; }
                    }
                }

                if (!drop && s.Role == SurfaceRole.Sand)
                {
                    // Prevent opposing canal-bank sand strips from overlapping each other
                    for (int k = 0; k < keptSand.Count; k++)
                    {
                        var other = keptSand[k];
                        if (other.chainId == s.ChainId) continue;
                        if (hi.X < other.lo.X || lo.X > other.hi.X || hi.Z < other.lo.Z || lo.Z > other.hi.Z) continue;
                        if (RingsOverlap(s.Ring, other.ring)) { drop = true; break; }
                    }
                }

                if (drop)
                {
                    plan.Surfaces.RemoveAt(i);
                    removed++;
                }
                else if (s.Role == SurfaceRole.Sand)
                {
                    keptSand.Add((s.ChainId, lo, hi, s.Ring));
                }
            }

            // 3. Validate and filter PlannedProps (no props on roads, rails, or inside building lots)
            for (int i = plan.Props.Count - 1; i >= 0; i--)
            {
                var p = plan.Props[i];
                if (p == null) { plan.Props.RemoveAt(i); removed++; continue; }
                bool drop = false;

                if (existingNets != null && existingNets.Count > 0)
                {
                    netGrid.QueryRadius(p.Position.XZ, 20f, nearNets);
                    for (int k = 0; k < nearNets.Count; k++)
                    {
                        var en = nearNets[k];
                        if (en.IsGeneratedByUs || (!en.IsRoad && !en.IsRail)) continue;
                        if (NetShape.DistanceToNet(p.Position.XZ, en, out _) < en.Width * 0.5f + 0.5f) { drop = true; break; }
                    }
                }

                if (!drop && buildings != null && buildings.Count > 0)
                {
                    buildingGrid.QueryRadius(p.Position.XZ, 22f, nearBldgs);
                    for (int k = 0; k < nearBldgs.Count; k++)
                    {
                        var lot = nearBldgs[k];
                        if (lot.Corners != null && Geom2D.PointInConvexQuad(p.Position.XZ, lot.Corners, 0.2f))
                        { drop = true; break; }
                    }
                }

                if (drop) { plan.Props.RemoveAt(i); removed++; }
            }

            plan.ValidatorRemoved += removed;
            return removed;
        }

        /// <summary>Read-only audit for tests: returns human-readable violations (empty when clean).</summary>
        public static List<string> Audit(
            WaterfrontPlan plan,
            IReadOnlyList<BuildingLot> buildings,
            IReadOnlyList<ExistingNetSegment> existingNets,
            IWorldSampler sampler,
            WaterfrontConfig cfg)
        {
            var issues = new List<string>();
            if (plan == null) return issues;
            cfg = cfg ?? new WaterfrontConfig();
            var netGrid = ShorelineDetector.BuildNetGrid(existingNets);
            var nearNets = new List<ExistingNetSegment>(24);

            for (int i = 0; i < plan.Nets.Count; i++)
            {
                var n = plan.Nets[i];
                float len = Vec2.Distance(n.A.XZ, n.D.XZ);
                if (len < 2.2f) issues.Add($"Net[{i}] ({n.Role}) is too short ({len:0.0} m)");
                if (n.Role == NetRole.AccessSpur || n.IsBeachCurl)
                {
                    float grade = Math.Abs(n.D.Y - n.A.Y) / Math.Max(1f, len);
                    if (grade > cfg.MaxPedestrianGrade + 0.02f)
                        issues.Add($"Net[{i}] ({n.Role}) grade {grade * 100f:0}% exceeds limit {cfg.MaxPedestrianGrade * 100f:0}%");
                }
                if (existingNets != null && existingNets.Count > 0)
                {
                    Vec2 mid = (n.A.XZ + n.D.XZ) * 0.5f;
                    netGrid.QueryRadius(mid, len * 0.5f + 22f, nearNets);
                    for (int k = 0; k < nearNets.Count; k++)
                    {
                        var en = nearNets[k];
                        if (en.IsGeneratedByUs || (!en.IsRoad && !en.IsRail)) continue;
                        float halfW = en.Width * 0.5f;
                        if (n.Role == NetRole.AccessSpur && en.IsRoad)
                        {
                            if (NetShape.DistanceToNet(n.D.XZ, en, out _) < halfW - 0.1f)
                                issues.Add($"Spur Net[{i}] ends inside road carriageway");
                        }
                        else if (NetShape.SegmentHitsNet(n.A.XZ, n.D.XZ, en, halfW + 0.25f))
                        {
                            issues.Add($"Net[{i}] ({n.Role}) overlaps existing {(en.IsRail ? "rail" : "road")}");
                        }
                    }
                }
            }

            if (sampler != null)
            {
                var pmExtendedChains = new HashSet<int>();
                for (int i = 0; i < plan.BeachGrades.Count; i++)
                    if (plan.BeachGrades[i].IsPlacemakerExtension) pmExtendedChains.Add(plan.BeachGrades[i].ChainId);

                for (int i = 0; i < plan.Surfaces.Count; i++)
                {
                    var s = plan.Surfaces[i];
                    if (s.Role != SurfaceRole.Sand || s.Ring == null || s.Ring.Length < 3) continue;
                    if (pmExtendedChains.Contains(s.ChainId)) continue;
                    RingBounds(s.Ring, out _, out _, out Vec2 c);
                    if (sampler.WaterDepth(c) >= cfg.MinWaterDepth)
                        issues.Add($"Sand Surface[{i}] centroid is underwater (depth {sampler.WaterDepth(c):0.00} m)");
                }
            }

            return issues;
        }

        private static void RingBounds(Vec2[] ring, out Vec2 lo, out Vec2 hi, out Vec2 center)
        {
            lo = ring[0]; hi = ring[0];
            float sx = 0f, sz = 0f;
            for (int i = 0; i < ring.Length; i++)
            {
                var p = ring[i];
                if (p.X < lo.X) lo.X = p.X;
                if (p.Z < lo.Z) lo.Z = p.Z;
                if (p.X > hi.X) hi.X = p.X;
                if (p.Z > hi.Z) hi.Z = p.Z;
                sx += p.X; sz += p.Z;
            }
            center = new Vec2(sx / ring.Length, sz / ring.Length);
        }

        private static bool RingsOverlap(Vec2[] a, Vec2[] b)
        {
            for (int i = 0; i < a.Length; i++)
                if (NetShape.PointInPolygon(a[i], b)) return true;
            for (int i = 0; i < b.Length; i++)
                if (NetShape.PointInPolygon(b[i], a)) return true;
            for (int i = 0; i < a.Length; i++)
            {
                Vec2 a0 = a[i], a1 = a[(i + 1) % a.Length];
                for (int j = 0; j < b.Length; j++)
                    if (Geom2D.SegmentsIntersect(a0, a1, b[j], b[(j + 1) % b.Length])) return true;
            }
            return false;
        }
    }
}
