using System.Collections.Generic;
using InterchangeStudio.Core;
using InterchangeStudio.Testing;
using Unity.Mathematics;
using Xunit;
using M = InterchangeStudio.Core.Planner.ToolMode;

/* Point at a bare highway and click: the new cross street the tool lays down (stage 1). */
public class NewStreetTests
{
    [Fact]
    public void ABareHighwayGetsACrossStreetThatJoinsTheRoadInLineAndStopsShortOtherwise()
    {
        var city = CityBuilder.BareHighway();
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Exit }, new float2(0, -12));
        Assert.NotNull(run.Plan);
        var pv = run.Plan;
        Assert.True(pv.NextStep, "the ramps should follow automatically");
        Assert.Contains("joining Elm Street on one side", run.Status);
        Assert.Empty(PlanChecks.Violations(pv, city.World, allowDeadEnds: true));

        // one end joins Elm Street, the other is a free stub; every other end meets the next piece
        var free = new Dictionary<float3, int>(); int joinsElm = 0;
        foreach (var s in pv.Specs)
            foreach (var (e, p) in new[] { (s.StartEntity, s.Curve.a), (s.EndEntity, s.Curve.d) })
                if (e == Entity.Null) free[p] = (free.TryGetValue(p, out int n) ? n : 0) + 1;
                else joinsElm++;                                   // the only existing thing it touches: Elm Street (a piece or a joint)
        Assert.Equal(1, joinsElm);
        int stubs = 0; foreach (var kv in free) if (kv.Value == 1) stubs++;
        Assert.Equal(1, stubs);

        // over the highway at full clearance, and no pillar (raised node) standing on a carriageway
        float top = 0;
        foreach (var s in pv.Specs)
        {
            top = math.max(top, math.max(s.E0, s.E1));
            foreach (var (p, e) in new[] { (s.Curve.a, s.E0), (s.Curve.d, s.E1) })
                if (e > 0.5f) Assert.True(math.abs(p.z - 12f) >= 15f && math.abs(p.z + 12f) >= 15f, $"a pillar stands on a carriageway at z={p.z:0.0}");
        }
        Assert.True(top >= 8.9f, $"the deck is only {top:0.0} m up");
    }
}
