using System.Collections.Generic;
using Colossal.Mathematics;
using Unity.Mathematics;

namespace InterchangeStudio.Core
{
    /*
     * Frontage roads (Loop 101 / Price Freeway, 2026-10-31; reshaped after the author's own build, 2026-11-08): a one-way
     * highway beside each carriageway, running the same way as its traffic. Near the cross street it is four lanes
     * wide. Further out it narrows to two: there the four lanes split into a two-lane frontage carrying on and a
     * two-lane ramp to the freeway (on), or a two-lane ramp from the freeway merges in (off). Those ramps are long
     * and gentle, real ramps rather than short slips. Highway pieces throughout, so the merges and splits flow
     * freely: between ordinary roads the game puts traffic lights there (the author, 2026-11-01). The frontage stops a
     * little past the ramps, for the player to carry on.
     */
    public partial class Planner
    {
        /*
         * The frontage beside the cross street: the game's four-lane one-way highway (three, or a one-way road, if
         * it is missing). Picking by width alone once chose an add-on's "HarborGateRoadOneway02" (2026-10-31).
         */
        Entity FrontagePrefab()
        {
            foreach (var n in new[] { "Highway Oneway - 4 lanes", "Highway Oneway - 3 lanes", "Medium Road Oneway", "Small Road Oneway" })
            {
                var e = Named(n, "Frontage");
                if (e != Entity.Null) return e;
            }
            return OnewayRoad(7.5f, 20f, widest: false, "Frontage");
        }

        /* the two-lane pieces: the frontage carrying on past the ramps, and the ramps themselves */
        Entity FrontageTwoLane(Entity fallback)
        {
            var e = Named("Highway Oneway - 2 lanes", "Frontage two-lane");
            return e != Entity.Null ? e : fallback;
        }

        /// <summary>How far out the frontage runs: clear of the highway by its own width plus room for the ramps between.</summary>
        float FrontageOffset(Plan p) => p.HighwayHalf + WidthOfPrefab(FrontagePrefab()) * 0.5f + (Size == 0 ? 28f : Size == 2 ? 48f : 36f);

        /// <summary>
        /// How far before the cross street the four lanes begin (where the off-ramp merges in): room to change lanes
        /// before the signal, and past the frontage's climb to a street up on its bridge, so the merge is on the level.
        /// </summary>
        float FrontageJoin(Plan p, float ej) => math.max(p.StreetHalf + (Size == 0 ? 60f : Size == 2 ? 120f : 90f), ej / (math.max(Grade, 0.03f) * 0.9f) + LevelRun);

        /// <summary>How long a ramp between the freeway and the frontage runs along it: long and gentle (the author: "more of a ramp").</summary>
        float FrontageRampRun(Plan p) => math.max(Size == 0 ? 180f : Size == 2 ? 300f : 240f, 6f * (FrontageOffset(p) - p.HighwayHalf));

        /// <summary>How far the frontage runs each way from the cross street: past the ramps, and back down to the ground.</summary>
        float FrontageReach(Plan p, float ej) => math.max(FrontageJoin(p, ej) + 80f, ej / (math.max(Grade, 0.03f) * 0.9f) + 20f);

        /* the frontage's height above ground, d metres along it from the cross street: down from the junction at the gradient */
        float FrontageElevation(float ej, float d) => math.max(0f, ej - math.abs(d) * math.max(Grade, 0.03f) * 0.9f);

        void WriteFrontage(Preview pv, Plan p, Entity rampPrefab, Attach off, Attach on, Attach junction, ref TerrainHeightData heights, List<Bezier4x3> curves)
        {
            Entity wide = FrontagePrefab(), narrow = FrontageTwoLane(wide);
            Entity ramp = RampLanes == 1 ? rampPrefab : FrontageTwoLane(rampPrefab);
            float rampHalf = WidthOfPrefab(ramp) * 0.5f;
            float3 cp = Position(p, p.Cross), cr = Right(p, p.Cross);
            float3 tc = Flat(Tangent(p, p.Cross));
            float lat = math.dot(junction.Pos - cp, cr);       // the frontage lines up with the junction on the street
            float sCross = math.clamp(p.Cross + math.dot(junction.Pos - cp, tc), 10f, p.Total - 10f);
            float ej = junction.Elevation, join = FrontageJoin(p, ej), reach = FrontageReach(p, ej);
            // past the ramps the two-lane frontage aligns with the four lanes' outer edge via a smooth S-taper,
            // leaving the inner side clear for the ramp to merge/diverge cleanly like a real freeway split
            float shift = math.max(0f, (WidthOfPrefab(wide) - WidthOfPrefab(narrow)) * 0.5f);
            var hd = heights;
            float SAt(float d) => math.clamp(sCross + d, 2f, p.Total - 2f);
            float3 At(float d)
            {
                if (math.abs(d) < 0.01f) return junction.Pos;
                var q = Beside(p, SAt(d), lat + (math.abs(d) > join + 0.01f ? shift : 0f), ref hd);
                q.y += FrontageElevation(ej, d);
                return q;
            }
            // the frontage itself, in the direction of the highway's traffic: core of the plan, never trimmed
            var stops = new List<float> { -reach, -join, 0f, join, reach };
            // climbing to a street up on its bridge: a joint where the climb starts, so the pieces at each merge are level
            if (ej > 0.1f) { stops.Insert(2, -(join - LevelRun)); stops.Insert(4, join - LevelRun); }
            var points = new List<float3>();
            var marks = new List<float>();
            for (int i = 0; i + 1 < stops.Count; i++)
            {
                int n = math.max(1, (int)math.ceil((stops[i + 1] - stops[i]) / MaxPiece));
                for (int k = 0; k < n; k++) marks.Add(math.lerp(stops[i], stops[i + 1], k / (float)n));
            }
            marks.Add(reach);
            foreach (var d in marks) points.Add(At(d));
            for (int i = 0; i + 1 < points.Count; i++)
            {
                bool intoJunction = math.abs(marks[i + 1]) < 0.01f, fromJunction = math.abs(marks[i]) < 0.01f;
                bool inner = math.abs(marks[i]) <= join + 0.01f && math.abs(marks[i + 1]) <= join + 0.01f;   // four lanes between the ramps
                float e0 = FrontageElevation(ej, marks[i]), e1 = FrontageElevation(ej, marks[i + 1]);
                float3 t0 = Flat(Tangent(p, SAt(marks[i]))), t1 = Flat(Tangent(p, SAt(marks[i + 1])));
                var seg = NetUtils.FitCurve(points[i], t0, t1, points[i + 1]);
                seg.a.y = points[i].y; seg.d.y = points[i + 1].y;
                if (e0 < 0.05f && e1 < 0.05f)
                {
                    seg.b.y = TerrainUtils.SampleHeight(ref heights, seg.b);
                    seg.c.y = TerrainUtils.SampleHeight(ref heights, seg.c);
                }
                else
                {
                    seg.b.y = math.lerp(seg.a.y, seg.d.y, 1f / 3f);
                    seg.c.y = math.lerp(seg.a.y, seg.d.y, 2f / 3f);
                }
                Ramp(pv, inner ? wide : narrow, seg, fromJunction ? junction : null, intoJunction ? junction : null, e0, e1, curves);
            }
            float3 J = points[marks.IndexOf(-join)], K = points[marks.IndexOf(join)];
            float sJ = SAt(-join), sK = SAt(join);
            float eJ = FrontageElevation(ej, join);
            string dir = Bound(tc);

            // the slip ramps: leave/rejoin the freeway at a crisp gore angle, follow highway curvature via intermediate
            // waypoints so curved freeways never bowstring into overlaps, and meet the frontage at local tangent +/- 17 deg
            const float Meet = 0.30f;
            float sOff = float.IsNaN(off.S) ? p.Diverge : off.S, sOn = float.IsNaN(on.S) ? p.Merge : on.S;
            float eOff = math.max(0, AboveGround(p, sOff, ref heights)), eOn = math.max(0, AboveGround(p, sOn, ref heights));
            off.Elevation = eOff; on.Elevation = eOn;

            BeginRamp(pv, $"the {dir} ramp to the frontage road");
            float3 tA = Flat(Tangent(p, sOff));
            float3 tJ = Flat(Tangent(p, sJ)), rJ = Right(p, sJ);
            var offParts = BuildRampCurveChain(p, sOff, off.Pos, sJ, J, lat, math.normalizesafe(tJ + rJ * Meet), isOff: true, p.HighwayHalf, rampHalf, ref heights);
            RampChain(pv, ramp, offParts, off, new Attach { Pos = J, Elevation = eJ }, eOff, eJ, tA, p.HighwayHalf, ref heights, curves);

            BeginRamp(pv, $"the {dir} ramp from the frontage road");
            float3 tB = Flat(Tangent(p, sOn));
            float3 tK = Flat(Tangent(p, sK)), rK = Right(p, sK);
            var onParts = BuildRampCurveChain(p, sOn, on.Pos, sK, K, lat, math.normalizesafe(tK - rK * Meet), isOff: false, p.HighwayHalf, rampHalf, ref heights);
            RampChain(pv, ramp, onParts, new Attach { Pos = K, Elevation = eJ }, on, eJ, eOn, tB, p.HighwayHalf, ref heights, curves);
            EndRamp();
        }
    }
}
