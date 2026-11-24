using System.Linq;
using InterchangeStudio.Core;
using InterchangeStudio.Testing;
using Unity.Mathematics;
using Xunit;
using M = InterchangeStudio.Core.Planner.ToolMode;

public class RestoredTests
{
    [Fact]
    public void BestFitComparesMaintainedRecipesWithoutChangingConfig()
    {
        var city = CityBuilder.SeparatedCrossing();
        var cfg = new PlanConfig { Mode = M.Auto, Autofit = false };
        var p = city.Planner(cfg);
        var o = p.Frame(new FrameInput { HasHit = true, Hit = PlanChecks.HitNear(city.World, new float2(0, -12)) });
        Assert.NotNull(o.Emit);
        Assert.Contains("Best fit chose", p.StatusText);
        Assert.Empty(PlanChecks.Violations(o.Emit, city.World));
        Assert.Same(cfg, p.Cfg);
    }

    static CityBuilder LocalCrossing(bool separated)
    {
        var city = new CityBuilder();
        float y = separated ? 9 : 0;
        city.Road("Highway Oneway - 2 lanes", "Highway", new[] { new float3(-1200, y, 0), new float3(1200, y, 0) }, breaks: new[] { float2.zero });
        city.Road("Small Road", "Local", new[] { new float3(0, 0, -900), new float3(0, 0, 900) }, breaks: new[] { float2.zero });
        return city;
    }

    [Fact]
    public void BestFitDoesNotScheduleRampsForALocalStreet()
    {
        var run = PlanChecks.Run(LocalCrossing(false), new PlanConfig { Mode = M.Auto }, float2.zero);
        Assert.NotNull(run.Plan);
        Assert.False(run.Plan.NextStep);
        Assert.Contains("without interchange ramps", run.Status);
    }

    [Fact]
    public void BestFitLeavesAnAlreadySeparatedLocalStreetAlone()
    {
        var run = PlanChecks.Run(LocalCrossing(true), new PlanConfig { Mode = M.Auto }, float2.zero);
        Assert.Null(run.Plan);
        Assert.Contains("no exit is needed", run.Status);
    }

    [Fact]
    public void BestFitAtAnArterialRetainsTwoStagePlanning()
    {
        var run = PlanChecks.Run(CityBuilder.AtGradeCrossing(), new PlanConfig { Mode = M.Auto }, new float2(0, -12));
        Assert.NotNull(run.Plan);
        Assert.True(run.Plan.NextStep);
        Assert.Equal(M.Auto, run.Plan.NextMode);
    }

    static CityBuilder Reversed(bool branch = false, bool open = false)
    {
        var city = new CityBuilder();
        const string prefab = "Highway Oneway - 2 lanes";
        city.Road(prefab, "West approach", new[] { new float3(0, 9, 0), new float3(200, 9, 0) });
        city.Road(prefab, "Reversed", new[] { new float3(400, 9, 0), new float3(200, 9, 0) });
        if (!open) city.Road(prefab, "East approach", new[] { new float3(400, 9, 0), new float3(600, 9, 0) });
        if (branch) city.Road(prefab, "Branch", new[] { new float3(200, 9, 0), new float3(200, 9, 200) });
        return city;
    }

    [Fact]
    public void DirectionRepairReversesOnlyTheBoundedRunAndKeepsElevationAndNames()
    {
        var city = Reversed();
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Repair }, new float2(300, 0));
        Assert.NotNull(run.Plan);
        Assert.False(run.Plan.NextStep);
        var built = run.Plan.Specs.Where(s => !s.Delete).ToList();
        Assert.Equal(3, built.Count);
        Assert.Equal(3, run.Plan.Specs.Count(s => s.Delete));
        Assert.All(built, s => {
            Assert.True(s.Curve.d.x > s.Curve.a.x);
            Assert.Equal(9f, s.E0); Assert.Equal(9f, s.E1);
            Assert.InRange(s.Curve.a.x, 200f, 400f);
            Assert.InRange(s.Curve.d.x, 200f, 400f);
        });
        Assert.All(run.Plan.Names, n => Assert.Equal("Reversed", n.name));
        Assert.Equal(3, run.Plan.Names.Count);
    }

    [Theory]
    [InlineData(true, false)] [InlineData(false, true)]
    public void DirectionRepairRefusesAmbiguousOrOpenRuns(bool branch, bool open)
    {
        var run = PlanChecks.Run(Reversed(branch, open), new PlanConfig { Mode = M.Repair }, new float2(300, 0));
        Assert.Null(run.Plan);
        Assert.Contains("no unambiguous reversed run", run.Status);
    }

    [Fact]
    public void DirectionRepairDoesNotBuildACrossingOnAnOrdinaryStreet()
    {
        var run = PlanChecks.Run(CityBuilder.AtGradeCrossing(), new PlanConfig { Mode = M.Repair }, new float2(0, 300));
        Assert.Null(run.Plan);
        Assert.Contains("point at a one-way highway", run.Status);
    }

    [Theory]
    [InlineData(M.Auto)] [InlineData(M.Repair)]
    public void RestoredModesSurviveConfigValidation(M mode)
    {
        Assert.Equal(mode, (new PlanConfig { Mode = mode }).Supported().Mode);
    }

    [Fact]
    public void HealthyHighwayIsNotOfferedForReversal()
    {
        var city = new CityBuilder();
        city.Road("Highway Oneway - 2 lanes", "Healthy", new[] { float3.zero, new float3(600, 0, 0) });
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Repair }, new float2(300, 0));
        Assert.Null(run.Plan);
    }
}
