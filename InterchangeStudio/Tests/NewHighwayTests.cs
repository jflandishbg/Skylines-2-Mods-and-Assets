using System.Collections.Generic;
using Colossal.Mathematics;
using InterchangeStudio.Core;
using InterchangeStudio.Testing;
using Unity.Mathematics;
using Xunit;
using M = InterchangeStudio.Core.Planner.ToolMode;

/*
 * 2026-10-23, the author: "you have the existing ave, hickory st, then you click a point there and it draws the
 * highway above it and potentially the intersection". Also: Keep elevated, and Street under on a bare highway.
 */
public class NewHighwayTests
{
    /// <summary>Every one-way piece keeps right: its side of the street's line is on the right of its travel.</summary>
    static void KeepsRight(Planner.Preview pv, float3 centre)
    {
        foreach (var s in pv.Specs)
        {
            if (s.Delete) continue;
            float3 d = MathUtils.Tangent(s.Curve, 0.5f), m = MathUtils.Position(s.Curve, 0.5f) - centre;
            float2 right = new float2(d.z, -d.x);
            Assert.True(math.dot(right, new float2(m.x, m.z)) > 0f, $"a highway piece at {m} drives on the left");
        }
    }

    [Fact]
    public void PointingAtAnAvenueBuildsAHighwayOverIt()
    {
        var city = CityBuilder.AvenueOnly();
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Exit }, new float2(0, 0));
        Assert.NotNull(run.Plan);
        Assert.Contains("goes over Hickory Street", run.Status);
        Assert.True(run.Plan.NextStep, "the diamond ramps should follow");
        Assert.Empty(PlanChecks.Violations(run.Plan, city.World, allowDeadEnds: true));
        float top = 0; int pieces = 0;
        foreach (var s in run.Plan.Specs)
        {
            Assert.False(s.Delete, "the avenue is left as it is");
            Assert.Equal("Highway Oneway - 2 lanes", city.World.PrefabName(s.Prefab));
            top = math.max(top, math.max(s.E0, s.E1)); pieces++;
            foreach (var (p, e) in new[] { (s.Curve.a, s.E0), (s.Curve.d, s.E1) })
                if (e > 0.5f) Assert.True(math.abs(p.z) >= 15f + 12f - 0.5f, $"a pillar stands on the avenue at z={p.z:0.0}");
        }
        Assert.True(top >= 8.9f);
        KeepsRight(run.Plan, new float3(0, 0, 0));
        // four free ends (two per carriageway), every other end meets the next piece
        var free = new Dictionary<float3, int>();
        foreach (var s in run.Plan.Specs) foreach (var p in new[] { s.Curve.a, s.Curve.d }) free[p] = (free.TryGetValue(p, out int n) ? n : 0) + 1;
        int ends = 0; foreach (var kv in free) if (kv.Value == 1) ends++;
        Assert.Equal(4, ends);
    }

    [Theory]
    [InlineData(M.Exit)]
    [InlineData(M.Spui)]
    public void OnceBuiltTheNewHighwayTakesTheRamps(M style)
    {
        // stage 1: the highway over Hickory Street
        var city = CityBuilder.AvenueOnly();
        var run = PlanChecks.Run(city, new PlanConfig { Mode = style }, new float2(0, 0));
        Assert.NotNull(run.Plan);
        // build it into a fresh city, piece by piece in traffic order (x > 0 runs north, x < 0 runs south)
        var built = CityBuilder.AvenueOnly();
        foreach (int side in new[] { 1, -1 })
        {
            var pts = new List<float3>();
            var specs = run.Plan.Specs.FindAll(x => x.Curve.a.x * side > 0f);
            specs.Sort((x, y) => (side * x.Curve.a.z).CompareTo(side * y.Curve.a.z));
            pts.Add(new float3(specs[0].Curve.a.x, specs[0].E0, specs[0].Curve.a.z));
            foreach (var sp in specs) pts.Add(new float3(sp.Curve.d.x, sp.E1, sp.Curve.d.z));
            built.Road("Highway Oneway - 2 lanes", side > 0 ? "Northbound" : "Southbound", pts, maxPiece: 1000f);
        }
        // stage 2: the ramps, as the tool adds them automatically after the build
        var ramps = PlanChecks.Run(built, new PlanConfig { Mode = style }, new float2(10, -60));
        Assert.True(ramps.Plan != null, ramps.Status);
        Assert.Contains("4 ramps", ramps.Status);
        Assert.Empty(PlanChecks.Violations(ramps.Plan, built.World));
    }

    [Fact]
    public void InAGridTheHighwayStaysUpOverTheNextStreetAndComesDownBeyondIt()
    {
        // 2026-10-23 self-test on the author's city: grid streets ~110 m apart made every attempt refuse
        var city = CityBuilder.AvenueOnly(oakZ: 120f);
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Overpass }, new float2(-300, 0));
        Assert.NotNull(run.Plan);
        Assert.Contains("stays up over 1 more street (Oak Street)", run.Status);
        Assert.Empty(PlanChecks.Violations(run.Plan, city.World, allowDeadEnds: true));
        foreach (var s in run.Plan.Specs)
            foreach (var (p, e) in new[] { (s.Curve.a, s.E0), (s.Curve.d, s.E1) })
                if (e > 0.5f)
                {
                    Assert.True(math.abs(p.z) >= 26.5f, $"a pillar stands on Hickory Street at z={p.z:0.0}");
                    Assert.True(math.abs(p.z - 120f) >= 21.5f, $"a pillar stands on Oak Street at z={p.z:0.0}");
                }
        KeepsRight(run.Plan, new float3(-300, 0, 0));
    }

    [Fact]
    public void PillarsStayOffFootpaths()
    {
        // 2026-10-23 self-test: the last red was pillars on footpaths under the new highway
        var city = CityBuilder.AvenueOnly();
        foreach (float z in new[] { 45f, 70f, -60f }) city.Path(new float3(-900, 0, z), new float3(900, 0, z));
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Overpass }, new float2(-300, 0));
        Assert.NotNull(run.Plan);
        Assert.Contains("a footpath", run.Status);
        foreach (var s in run.Plan.Specs)
            foreach (var (p, e) in new[] { (s.Curve.a, s.E0), (s.Curve.d, s.E1) })
                if (e > 0.5f) foreach (float z in new[] { 45f, 70f, -60f }) Assert.True(math.abs(p.z - z) >= 13.5f, $"a pillar stands on the footpath at z={z} (pillar at {p.z:0.0})");
    }

    [Fact]
    public void PillarsStayOffAPathRunningAtAnAngleUnderTheHighway()
    {
        // 2026-10-23 self-test, Moonflower Street: park paths running diagonally under the new highway
        var city = CityBuilder.AvenueOnly();
        var a = new float3(-291, 0, 70); var b = new float3(-291, 0, 110);      // alongside, under where a pillar would stand (-290, 89): it never crosses the line
        city.Path(a, b);
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Overpass }, new float2(-300, 0));
        Assert.NotNull(run.Plan);
        var path = InterchangeStudio.Core.NetUtils.StraightCurve(a, b);
        foreach (var s in run.Plan.Specs)
            foreach (var (p, e) in new[] { (s.Curve.a, s.E0), (s.Curve.d, s.E1) })
                if (e > 0.5f) Assert.True(MathUtils.Distance(path.xz, new float2(p.x, p.z), out float _) >= 5f, $"a pillar stands on the path at {p}");
    }

    [Fact]
    public void ADenseGridLeavesTheEndsRaisedAndSaysSo()
    {
        var city = CityBuilder.AvenueOnly();
        for (int i = 1; i <= 12; i++) { city.Road("Small Road", "North " + i, new[] { new float3(-900, 0, 100f * i), new float3(900, 0, 100f * i) }); city.Road("Small Road", "South " + i, new[] { new float3(-900, 0, -100f * i), new float3(900, 0, -100f * i) }); }
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Overpass }, new float2(-300, 0));
        Assert.NotNull(run.Plan);
        Assert.Contains("ends left raised", run.Status);
        foreach (var s in run.Plan.Specs) Assert.True(s.E0 >= 8.9f && s.E1 >= 8.9f, "a raised end comes down");
    }

    [Fact]
    public void KeepElevatedHighwayStaysUpAndPassesOverOtherStreets()
    {
        var city = CityBuilder.AvenueOnly(oakZ: 120f);
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Overpass, KeepElevated = true }, new float2(-300, 0));
        Assert.NotNull(run.Plan);
        Assert.Contains("kept up", run.Status);
        foreach (var s in run.Plan.Specs) { Assert.True(s.E0 >= 8.9f && s.E1 >= 8.9f, "a piece comes down"); }
        KeepsRight(run.Plan, new float3(-300, 0, 0));
    }

    [Fact]
    public void KeepElevatedNewStreetOnABareHighwayStaysUp()
    {
        var city = CityBuilder.BareHighwayWithRoadAt(float.NaN);
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Overpass, KeepElevated = true }, new float2(0, -12));
        Assert.NotNull(run.Plan);
        Assert.Contains("kept up", run.Status);
        foreach (var s in run.Plan.Specs) Assert.True(s.E0 >= 8.9f && s.E1 >= 8.9f, "a piece comes down");
        Assert.Empty(PlanChecks.Violations(run.Plan, city.World, allowDeadEnds: true));
    }

    [Fact]
    public void StreetUnderOnABareHighwayDips()
    {
        foreach (var cfg in new[] { new PlanConfig { Mode = M.Overpass, Dig = true }, new PlanConfig { Mode = M.Overpass, LiftStreet = false } })
        {
            var city = CityBuilder.BareHighwayWithRoadAt(float.NaN);
            var run = PlanChecks.Run(city, cfg, new float2(0, -12));
            Assert.NotNull(run.Plan);
            Assert.Contains("cutting under it", run.Status);
            float low = 0; foreach (var s in run.Plan.Specs) low = math.min(low, math.min(s.E0, s.E1));
            Assert.True(low <= -8.9f);
        }
    }
}
