using InterchangeStudio.Core;
using InterchangeStudio.Testing;
using Unity.Mathematics;
using Xunit;
using M = InterchangeStudio.Core.Planner.ToolMode;

/* 2026-10-23 self-test on the author's map: most red was "in water". New roads stop short of water, or say why not. */
public class WaterTests
{
    [Fact]
    public void ANewStreetStopsShortOfALake()
    {
        var city = CityBuilder.BareHighwayWithRoadAt(600f);
        city.Water = p => p.z > 330f && p.z < 500f ? 4f : 0f;          // a lake between the highway and Elm Street
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Exit }, new float2(0, -12));
        Assert.NotNull(run.Plan);
        Assert.Contains("stops short of the water", run.Status);
        Assert.DoesNotContain("joining Elm Street", run.Status);
        foreach (var s in run.Plan.Specs) Assert.True(s.Curve.a.z < 330f && s.Curve.d.z < 330f, "a piece is in the lake");
    }

    [Fact]
    public void WaterTooCloseLeavesThatEndRaisedAtTheShore()
    {
        // 2026-10-23 self-test: a highway along the shore; the new street was refused ("would come down into water")
        var city = CityBuilder.BareHighwayWithRoadAt(float.NaN);
        city.Water = p => p.z > 150f ? 4f : 0f;
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Exit }, new float2(0, -12));
        Assert.NotNull(run.Plan);
        Assert.Contains("left raised at the water's edge", run.Status);
        foreach (var s in run.Plan.Specs)
        {
            Assert.True(s.Curve.a.z < 150f && s.Curve.d.z < 150f, "a piece is in the water");
            if (s.Curve.a.z > 12f && s.Curve.d.z > 12f) Assert.True(s.E0 > 8.9f && s.E1 > 8.9f, "the shore end comes down");
        }
        Assert.Empty(PlanChecks.Violations(run.Plan, city.World, allowDeadEnds: true));
    }

    [Fact]
    public void ANewHighwayWithNoRoomBeforeWaterEndsRaisedAtTheShore()
    {
        // 2026-10-23 self-test, Thornbury Street: refused with "would come down into water"
        var city = CityBuilder.AvenueOnly();
        city.Water = p => p.z < -120f ? 4f : 0f;
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Overpass }, new float2(0, 0));
        Assert.NotNull(run.Plan);
        Assert.Contains("left raised at the water's edge", run.Status);
        foreach (var s in run.Plan.Specs) if (s.Curve.a.z < -60f || s.Curve.d.z < -60f) Assert.True(s.E0 > 8.9f && s.E1 > 8.9f, "the south end comes down by the water");
    }

    [Fact]
    public void ANewHighwayStopsShortOfALake()
    {
        var city = CityBuilder.AvenueOnly();
        city.Water = p => p.z < -240f ? 4f : 0f;
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Exit }, new float2(0, 0));
        Assert.NotNull(run.Plan);
        Assert.Contains("stops short of the water", run.Status);
        foreach (var s in run.Plan.Specs) Assert.True(s.Curve.a.z > -240f && s.Curve.d.z > -240f, "a piece is in the lake");
    }
}
