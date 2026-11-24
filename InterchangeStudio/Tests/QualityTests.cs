using System.Collections.Generic;
using System.Linq;
using Colossal.Mathematics;
using InterchangeStudio.Core;
using InterchangeStudio.Testing;
using Unity.Mathematics;
using Xunit;
using M = InterchangeStudio.Core.Planner.ToolMode;

/*
 * Regression tests for the bottom-to-top geometry, hover, water, curved-highway, skewed-street,
 * and Stage 2 reliability fixes.
 */
public class QualityTests
{
    static CityBuilder CurvedSeparatedCrossing(float bendDegrees = 40f)
    {
        var c = new CityBuilder();
        float r = 3400f;
        float halfRad = math.radians(bendDegrees * 0.5f); // ~2370 m total arc length (~1185 m each side)
        foreach (var (name, offset, dir) in new[] { ("Eastbound", -12f, 1f), ("Westbound", 12f, -1f) })
        {
            var pts = new List<float3>();
            int steps = 30; // ~79 m per segment, matching standard CS2 highway pieces
            for (int i = 0; i <= steps; i++)
            {
                float a = math.lerp(-halfRad, halfRad, i / (float)steps);
                float rad = r - offset;
                float x = rad * math.sin(a);
                float z = r - rad * math.cos(a);
                float dist = math.abs(a) * r;
                float e = dist <= 80f ? 9f : dist <= 240f ? 5.4f : dist <= 420f ? 0.9f : 0f;
                pts.Add(new float3(x, e, z));
            }
            if (dir < 0) pts.Reverse();
            c.Road("Highway Oneway - 4 lanes", name, pts, maxPiece: 90f);
        }
        c.Road("Large Road", "Cross Avenue", new[] { new float3(0, 0, -800), new float3(0, 0, 800) });
        return c;
    }

    [Theory]
    [InlineData(M.Exit)]
    [InlineData(M.Spui)]
    [InlineData(M.Frontage)]
    public void CurvedHighwayBuildsCleanWithoutOversizedSegments(M mode)
    {
        var city = CurvedSeparatedCrossing(40f);
        var run = PlanChecks.Run(city, new PlanConfig { Mode = mode, Autofit = false }, new float2(0, -12));
        Assert.True(run.Plan != null, run.Status);
        Assert.Empty(PlanChecks.Violations(run.Plan, city.World, allowDeadEnds: mode == M.Frontage));
        foreach (var s in run.Plan.Specs.Where(x => !x.Delete))
        {
            float len = MathUtils.Length(s.Curve);
            Assert.True(len >= 10f && len <= 112f, $"{mode} emitted a {len:0.0} m piece");
        }
    }

    [Fact]
    public void SkewedCrossStreetDiamondNeverFoldsApproachStubs()
    {
        var city = new CityBuilder();
        foreach (var (name, z, dir) in new[] { ("Eastbound", -12f, 1f), ("Westbound", 12f, -1f) })
        {
            var pts = new List<float3>();
            foreach (float x in new[] { -1200f, -420f, -240f, -80f, 80f, 240f, 420f, 1200f })
            {
                float e = math.abs(x) <= 80f ? 9f : math.abs(x) <= 240f ? 5.4f : math.abs(x) <= 420f ? 0.9f : 0f;
                pts.Add(new float3(x, e, z));
            }
            if (dir < 0) pts.Reverse();
            city.Road("Highway Oneway - 2 lanes", name, pts);
        }
        // 30-degree skewed cross street
        float sx = math.sin(math.radians(30f)), sz = math.cos(math.radians(30f));
        city.Road("Large Road", "Skewed Boulevard", new[] { new float3(-900 * sx, 0, -900 * sz), new float3(900 * sx, 0, 900 * sz) });

        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Exit, Autofit = false }, new float2(0, -12));
        Assert.True(run.Plan != null, run.Status);
        Assert.Empty(PlanChecks.Violations(run.Plan, city.World));
        foreach (var s in run.Plan.Specs.Where(x => !x.Delete))
        {
            // every ramp piece must travel generally along its carriageway (never fold backwards)
            float3 dir = MathUtils.Tangent(s.Curve, 0.5f);
            float want = s.Curve.a.z < 0 ? 1f : -1f;
            Assert.True(math.normalizesafe(dir.xz).x * want > 0.3f, $"ramp folded at {s.Curve.a} -> {s.Curve.d}");
        }
    }

    [Fact]
    public void WaterEdgeNextToRoadFootprintAndShallowWaterAreDetected()
    {
        var city = CityBuilder.BareHighwayWithRoadAt(float.NaN);
        // Diagonal/edge shallow shoreline: dry on centreline x=0, wet (0.12 m deep) at road edge x=18 m past z=260
        city.Water = p => p.z > 260f && p.x > 14f ? 0.12f : 0f;
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Exit }, new float2(0, -12));
        Assert.NotNull(run.Plan);
        Assert.Contains("stops short of the water", run.Status);
        foreach (var s in run.Plan.Specs)
            Assert.True(s.Curve.a.z < 260f && s.Curve.d.z < 260f, $"piece reached edge water at z={math.max(s.Curve.a.z, s.Curve.d.z):0}");
    }

    [Fact]
    public void HoveringANodeOrHighwayMedianKeepsPreviewSteady()
    {
        var city = CityBuilder.BareHighway();
        var p = city.Planner(new PlanConfig { Mode = M.Exit });
        // Pick an actual node on Eastbound highway
        var eb = city.World.RoadEdges[0];
        var node = city.World.GetComponentData<Edge>(eb).m_End;
        var nodePos = city.World.GetComponentData<Node>(node).m_Position;

        var oNode = p.Frame(new FrameInput { HasHit = true, Hit = new RaycastHit { m_HitEntity = node, m_HitPosition = nodePos, m_CurvePosition = 0f }, AllowApply = true });
        Assert.NotNull(oNode.Emit);

        // Now hover the empty median at z = 0 (12 m from both carriageways) via terrain hit
        var oMedian = p.Frame(new FrameInput { HasHit = false, HasTerrainHit = true, TerrainPos = new float3(0, 0, 0), AllowApply = true });
        Assert.NotNull(oMedian.Emit);

        // Far away from any road (> 14 m): should NOT snap
        var oFar = p.Frame(new FrameInput { HasHit = false, HasTerrainHit = true, TerrainPos = new float3(0, 0, 200), AllowApply = true });
        Assert.Null(oFar.Emit);
    }

    [Fact]
    public void CacheKeyChangesForEveryToggle()
    {
        var baseCfg = new PlanConfig();
        Assert.NotEqual(baseCfg.CacheKey(), (baseCfg with { Size = 2 }).CacheKey());
        Assert.NotEqual(baseCfg.CacheKey(), (baseCfg with { TightRamps = true }).CacheKey());
        Assert.NotEqual(baseCfg.CacheKey(), (baseCfg with { Dig = true }).CacheKey());
        Assert.NotEqual(baseCfg.CacheKey(), (baseCfg with { KeepElevated = true }).CacheKey());
        Assert.NotEqual(baseCfg.CacheKey(), (baseCfg with { NewStreet = 2 }).CacheKey());
        Assert.NotEqual(baseCfg.CacheKey(), (baseCfg with { EndRoad = 0 }).CacheKey());
    }

    [Fact]
    public void BareHighwayOverpassUsesCompactLandingStubInsteadOfBloat()
    {
        var city = CityBuilder.BareHighwayWithRoadAt(float.NaN);
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Overpass, Autofit = false }, new float2(0, -12));
        Assert.NotNull(run.Plan);
        Assert.Empty(PlanChecks.Violations(run.Plan, city.World, allowDeadEnds: true));
        float minZ = float.MaxValue, maxZ = float.MinValue;
        foreach (var s in run.Plan.Specs.Where(x => !x.Delete))
        {
            minZ = math.min(minZ, math.min(s.Curve.a.z, s.Curve.d.z));
            maxZ = math.max(maxZ, math.max(s.Curve.a.z, s.Curve.d.z));
        }
        // Previously 920+ m because NewStreetStub was 250 m per side; now compact (~520 m at 5% grade, ~410 m in Compact)
        Assert.True(maxZ - minZ < 580f, $"overpass is still too long ({maxZ - minZ:0} m)");
    }

    [Theory]
    [InlineData(M.Exit)]
    [InlineData(M.Spui)]
    public void StreetOverRampsKeepHighwayGorePieceFlatAtGroundLevel(M mode)
    {
        // Regression for Screenshot 2: climbing on the gore segment itself tore terrain into the highway shoulder
        var city = CityBuilder.StreetOverCrossing();
        var run = PlanChecks.Run(city, new PlanConfig { Mode = mode, Autofit = false }, new float2(0, -12));
        Assert.True(run.Plan != null, run.Status);
        Assert.Empty(PlanChecks.Violations(run.Plan, city.World));
        int gorePieces = 0;
        foreach (var s in run.Plan.Specs.Where(x => !x.Delete && x.Group > 0))
        {
            bool atHwyStart = s.StartEntity != Entity.Null && math.abs(s.Curve.a.x) > 80f;
            bool atHwyEnd = s.EndEntity != Entity.Null && math.abs(s.Curve.d.x) > 80f;
            if (!atHwyStart && !atHwyEnd) continue;
            gorePieces++;
            Assert.True(s.E0 < 0.05f && s.E1 < 0.05f, $"gore piece climbed at highway ({s.E0:0.0} -> {s.E1:0.0} m)");
        }
        Assert.Equal(4, gorePieces);
    }

    static CityBuilder DividedHighwayDeadEnds(float elevation = 0f, float stagger = 6f)
    {
        var c = new CityBuilder();
        c.Road("Highway Oneway - 4 lanes", "Eastbound", new[] { new float3(-600, elevation, -13), new float3(0, elevation, -13) });
        c.Road("Highway Oneway - 4 lanes", "Westbound", new[] { new float3(-stagger, elevation, 13), new float3(-600, elevation, 13) });
        return c;
    }

    [Theory]
    [InlineData(0, "Highway Twoway - 2 lanes")]
    [InlineData(1, "Medium Road")]
    [InlineData(2, "Large Road")]
    public void HighwayEndMergesTwoOpposingCarriagewaysIntoOneTwoWayRoad(int endRoad, string expectedPrefab)
    {
        var city = DividedHighwayDeadEnds(elevation: 0f, stagger: 6f);
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Ending, EndRoad = endRoad, Autofit = false }, new float2(-10, -13));
        Assert.True(run.Plan != null, run.Status);
        Assert.Contains("merges both carriageways", run.Status);
        Assert.Empty(PlanChecks.Violations(run.Plan, city.World, allowDeadEnds: true));
        Assert.DoesNotContain(run.Plan.Specs, s => s.Delete);
        var built = run.Plan.Specs.Where(s => !s.Delete).ToList();
        Assert.Contains(built, s => city.World.PrefabName(s.Prefab) == expectedPrefab);
        // Incoming leg starts at eastbound end node and heads +x; outgoing leg ends at westbound start node and heads -x
        var inLeg = built.Single(s => s.StartEntity != Entity.Null);
        var outLeg = built.Single(s => s.EndEntity != Entity.Null);
        Assert.True(inLeg.Curve.d.x > inLeg.Curve.a.x);
        Assert.True(outLeg.Curve.d.x < outLeg.Curve.a.x);
        // Both legs meet the exact same merge node M
        Assert.True(math.distance(inLeg.Curve.d, outLeg.Curve.a) < 0.01f);
        // Continuing two-way road starts at M and goes +x
        Assert.Contains(built, s => city.World.PrefabName(s.Prefab) == expectedPrefab && math.distance(s.Curve.a, inLeg.Curve.d) < 0.01f && s.Curve.d.x > s.Curve.a.x);
    }

    [Fact]
    public void ElevatedHighwayEndMergesAtDeckHeightThenRampsDownToGround()
    {
        var city = DividedHighwayDeadEnds(elevation: 9f, stagger: 0f);
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Ending, EndRoad = 2, Autofit = false }, new float2(-10, -13));
        Assert.True(run.Plan != null, run.Status);
        Assert.Contains("ramping down", run.Status);
        Assert.Empty(PlanChecks.Violations(run.Plan, city.World, allowDeadEnds: true));
        var twoWay = run.Plan.Specs.Where(s => !s.Delete && city.World.PrefabName(s.Prefab) == "Large Road").ToList();
        Assert.NotEmpty(twoWay);
        Assert.True(twoWay.First().E0 >= 8.9f, "merge node should stay level at deck height");
        Assert.True(twoWay.Last().E1 < 0.05f, "continuing road should reach ground level");
    }

    [Fact]
    public void HighwayEndRefusesMidHighwayWithoutDeadEnds()
    {
        var city = CityBuilder.BareHighway();
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Ending, Autofit = false }, new float2(0, -12));
        Assert.Null(run.Plan);
        Assert.Contains("open ends", run.Status);
    }

    [Fact]
    public void DumbbellOnSlopedTerrainKeepsWorldYAndElevationConsistent()
    {
        var city = CityBuilder.SeparatedCrossing();
        // Gentle 1.5% slope in x (well within level-roundabout tolerance)
        var terrain = new FuncTerrain(p => p.x * 0.015f);
        var p = new Planner(city.World, new TerrainSystem { Terrain = terrain }, city.Names(), city.Log)
        {
            Cfg = new PlanConfig { Mode = M.Dumbbell, Autofit = false }
        };
        var hit = PlanChecks.HitNear(city.World, new float2(0, -12));
        Planner.Preview pv = null;
        for (int f = 0; f < 4 && pv == null; f++)
            pv = p.Frame(new FrameInput { HasHit = true, Hit = hit, AllowApply = true }).Emit;
        Assert.NotNull(pv);
        var rings = pv.Specs.Where(s => !s.Delete && city.World.PrefabName(s.Prefab) == "Highway Oneway - 3 lanes").ToList();
        Assert.Equal(8, rings.Count);
        foreach (var r in rings)
        {
            Assert.InRange(r.Curve.a.y - (terrain.Height(r.Curve.a) + r.E0), -0.05f, 0.05f);
            Assert.InRange(r.Curve.d.y - (terrain.Height(r.Curve.d) + r.E1), -0.05f, 0.05f);
        }
    }
}
