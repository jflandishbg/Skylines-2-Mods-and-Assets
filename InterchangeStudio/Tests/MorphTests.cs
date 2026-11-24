using System.Collections.Generic;
using InterchangeStudio.Core;
using InterchangeStudio.Testing;
using Unity.Mathematics;
using Xunit;
using M = InterchangeStudio.Core.Planner.ToolMode;

/*
 * The crossing fits the roads that are there (2026-10-21, the author: "ideally it can morph to the road that's
 * there"): streets already drawn up to the highway are joined across it, and the bridge comes down in time
 * for a road close by instead of refusing.
 */
public class MorphTests
{
    static float Top(Planner.Preview pv) { float t = 0; foreach (var s in pv.Specs) t = math.max(t, math.max(s.E0, s.E1)); return t; }

    static void NoPillarOnACarriageway(Planner.Preview pv)
    {
        foreach (var s in pv.Specs)
            foreach (var (p, e) in new[] { (s.Curve.a, s.E0), (s.Curve.d, s.E1) })
                if (e > 0.5f) Assert.True(math.abs(p.z - 12f) >= 15f && math.abs(p.z + 12f) >= 15f, $"a pillar stands on a carriageway at z={p.z:0.0}");
    }

    [Fact]
    public void StreetsDrawnUpToTheHighwayAreJoinedAcrossIt()
    {
        var city = CityBuilder.StubsAtHighway();
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Exit }, new float2(5, -12));
        Assert.NotNull(run.Plan);
        Assert.Contains("Aspen Street is joined across the highway", run.Status);
        Assert.True(run.Plan.NextStep);
        Assert.Empty(PlanChecks.Violations(run.Plan, city.World));        // no dead ends: it meets the streets' own pieces
        Assert.Contains(run.Plan.Specs, s => s.Delete);                     // their pieces near the highway are lifted
        Assert.True(Top(run.Plan) >= 8.9f);
        NoPillarOnACarriageway(run.Plan);
        foreach (var s in run.Plan.Specs) if (!s.Delete) Assert.Equal("Large Road", city.World.PrefabName(s.Prefab));
    }

    [Fact]
    public void ASideStreetCloseByMakesTheSlopeSteeperNotTheBuildFail()
    {
        var city = CityBuilder.StubsAtHighway(sideStreetAt: 200f);
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Exit }, new float2(5, -12));
        Assert.NotNull(run.Plan);
        Assert.Contains("steepened", run.Status);
        Assert.Empty(PlanChecks.Violations(run.Plan, city.World));
        // Birch Lane's junction is left alone: nothing is deleted at or beyond it
        foreach (var s in run.Plan.Specs)
            if (!s.Delete) Assert.True(math.max(s.Curve.a.z, s.Curve.d.z) <= 200.5f, "the bridge was laid past Birch Lane");
    }

    [Fact]
    public void ANewStreetComesDownInTimeForARoadClose()
    {
        var city = CityBuilder.BareHighwayWithRoadAt(180f);
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Exit }, new float2(0, -12));
        Assert.NotNull(run.Plan);
        Assert.Contains("joining Elm Street", run.Status);
        Assert.Contains("steepened", run.Status);
        Assert.Empty(PlanChecks.Violations(run.Plan, city.World, allowDeadEnds: true));
        NoPillarOnACarriageway(run.Plan);
    }

    [Fact]
    public void ARoadTooCloseToComeDownForIsExplained()
    {
        var city = CityBuilder.BareHighwayWithRoadAt(110f);
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Exit }, new float2(0, -12));
        Assert.Null(run.Plan);
        Assert.Contains("Elm Street is only", run.Status);
    }
}
