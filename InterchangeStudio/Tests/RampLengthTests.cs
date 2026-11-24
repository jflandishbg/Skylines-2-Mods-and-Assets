using System.Collections.Generic;
using InterchangeStudio.Core;
using InterchangeStudio.Testing;
using Unity.Mathematics;
using Xunit;
using Xunit.Abstractions;
using M = InterchangeStudio.Core.Planner.ToolMode;

/*
 * 2026-10-23, the author: "theoretically the ramps should all be equal but it really wants to stretch out the ramps".
 * Where a ramp meets the highway it slides to a spot clear of short pieces; it now takes the nearest such spot,
 * so the four ramps of a diamond stay close to equal length even on a highway cut into uneven pieces.
 */
public class RampLengthTests
{
    readonly ITestOutputHelper m_Out;
    public RampLengthTests(ITestOutputHelper o) { m_Out = o; }

    static List<float> RampReach(Planner.Preview pv, NetWorld w)
    {
        // how far from the cross street (x = 0) each ramp leaves or joins the highway
        var d = new List<float>();
        foreach (var s in pv.Specs)
        {
            if (s.Delete) continue;
            if (s.StartEntity != Entity.Null && math.abs(s.Curve.a.z) > 5f && math.abs(s.Curve.a.x) > 60f) d.Add(math.abs(s.Curve.a.x));
            if (s.EndEntity != Entity.Null && math.abs(s.Curve.d.z) > 5f && math.abs(s.Curve.d.x) > 60f) d.Add(math.abs(s.Curve.d.x));
        }
        return d;
    }

    [Fact]
    public void FourRampsStayNearlyEqualNextToShortHighwayPieces()
    {
        var city = CityBuilder.UnevenCrossing();
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Exit }, new float2(0, -12));
        Assert.NotNull(run.Plan);
        var reach = RampReach(run.Plan, city.World);
        m_Out.WriteLine("ramps meet the highway at: " + string.Join(", ", reach.ConvertAll(x => x.ToString("0"))));
        Assert.Equal(4, reach.Count);
        float lo = float.MaxValue, hi = 0; foreach (var x in reach) { lo = math.min(lo, x); hi = math.max(hi, x); }
        Assert.True(hi - lo <= 40f, $"the ramps differ by {hi - lo:0} m");
        Assert.Empty(PlanChecks.Violations(run.Plan, city.World));
    }

    [Fact]
    public void RampsStandClearOfTheHighwayNearTheStreet()
    {
        // 2026-10-23: ramps hugged the highway (3-12 m from its edge); the author's own stand 40-60 m out
        var city = CityBuilder.SeparatedCrossing();
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Exit }, new float2(0, -12));
        Assert.NotNull(run.Plan);
        // sampled finely, so where the pieces happen to be cut doesn't matter (2026-10-31: a new joint where the
        // ramp starts climbing exposed a point 13.9 m out that coarser sampling had always missed)
        foreach (var s in run.Plan.Specs)
            for (int i = 0; i <= 64; i++)
            {
                var q = Colossal.Mathematics.MathUtils.Position(s.Curve, i / 64f);
                if (math.abs(q.x) < 80f && math.abs(q.x) > 20f) Assert.True(math.abs(q.z) >= 12f + 7.5f + 12f, $"a ramp hugs the highway at {q}");
            }
        Assert.Empty(PlanChecks.Violations(run.Plan, city.World));
    }

    [Theory]
    [InlineData(1, "Highway Oneway - 1 lane")]
    [InlineData(2, "Highway Oneway - 2 lanes")]
    public void RampLanesAreThePlayersChoice(int lanes, string prefab)
    {
        var city = CityBuilder.SeparatedCrossing();
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Exit, RampLanes = lanes }, new float2(0, -12));
        Assert.NotNull(run.Plan);
        foreach (var s in run.Plan.Specs) if (!s.Delete) Assert.Equal(prefab, city.World.PrefabName(s.Prefab));
    }
}
