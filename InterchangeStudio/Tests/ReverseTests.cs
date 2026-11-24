using System.Collections.Generic;
using InterchangeStudio.Core;
using InterchangeStudio.Testing;
using Unity.Mathematics;
using Xunit;
using M = InterchangeStudio.Core.Planner.ToolMode;

/*
 * 2026-10-23, the author: bring back the plain overpass/underpass, and try it "in reverse": point at the avenue
 * or large road, and the crossing is built around it.
 */
public class ReverseTests
{
    [Fact]
    public void StreetUnderDipsTheStreetAndLeavesTheHighwayAlone()
    {
        var city = CityBuilder.AtGradeCrossing();
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Overpass, LiftStreet = true, Dig = true }, new float2(0, -12));
        Assert.NotNull(run.Plan);
        Assert.Contains("dips under", run.Status);
        Assert.False(run.Plan.NextStep, "an overpass adds no ramps");
        float low = 0;
        foreach (var s in run.Plan.Specs)
        {
            low = math.min(low, math.min(s.E0, s.E1));
            if (s.Delete) Assert.Equal("Large Road", city.World.PrefabName(city.World.GetComponentData<PrefabRef>(s.Original).m_Prefab));
        }
        Assert.True(low <= -8.9f, $"the street only goes {low:0.0} m down");
        Assert.Empty(PlanChecks.Violations(run.Plan, city.World, allowBelow: true));
    }

    [Fact]
    public void PointingAtAStreetJoinsItToItsOtherHalfAcrossTheHighway()
    {
        var city = CityBuilder.StubsAtHighway();
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Exit }, new float2(0, 300));     // on Aspen Street, not the highway
        Assert.NotNull(run.Plan);
        Assert.Contains("Aspen Street is joined across the highway", run.Status);
        Assert.Empty(PlanChecks.Violations(run.Plan, city.World));
    }

    [Fact]
    public void PointingAtAStreetWithNothingAcrossCarriesItOnToTheRoadInLine()
    {
        var city = CityBuilder.OneStub(-400f);
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Exit }, new float2(0, 300));
        Assert.NotNull(run.Plan);
        Assert.Contains("Aspen Street is extended across the highway", run.Status);
        Assert.Contains("carrying straight on to Elm Street", run.Status);
        Assert.True(run.Plan.NextStep);
        Assert.Empty(PlanChecks.Violations(run.Plan, city.World));          // both ends meet existing roads
        int joins = 0;
        foreach (var s in run.Plan.Specs) if (!s.Delete && s.EndEntity != Entity.Null && city.World.Exists(s.EndEntity) && s.Curve.d.z < -390f) joins++;
        Assert.Equal(1, joins);
    }

    [Fact]
    public void PointingAtAStreetWithNothingBeyondStopsShortOnTheFarSide()
    {
        var city = CityBuilder.OneStub(float.NaN);
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Exit }, new float2(0, 300));
        Assert.NotNull(run.Plan);
        Assert.Contains("stopping short on the far side", run.Status);
        Assert.Empty(PlanChecks.Violations(run.Plan, city.World, allowDeadEnds: true));
    }
}
