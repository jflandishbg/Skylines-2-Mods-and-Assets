using InterchangeStudio.Core;
using InterchangeStudio.Testing;
using Unity.Mathematics;
using Xunit;
using M = InterchangeStudio.Core.Planner.ToolMode;

/* A two-step build (bridge now, ramps a few frames later) must not finish after the tool is closed or the settings change. */
public class LifecycleTests
{
    [Fact]
    public void ClosingTheToolDropsTheRampsStillToCome()
    {
        var city = CityBuilder.AtGradeCrossing();
        var hit = PlanChecks.HitNear(city.World, new float2(0, -12));
        foreach (bool abandon in new[] { false, true })
        {
            var p = city.Planner(new PlanConfig { Mode = M.Exit });
            for (int f = 0; f < 3; f++) p.Frame(new FrameInput { HasHit = true, Hit = hit, AllowApply = true });
            var o = p.Frame(new FrameInput { HasHit = true, Hit = hit, AllowApply = true, Apply = true });
            Assert.True(o.ApplyNow, "the bridge should build");
            Assert.Contains("Adding the ramps", p.StatusText);
            if (abandon) p.Abandon();                       // the tool is closed (or a setting changed)
            bool stage2 = false;
            for (int f = 0; f < 30; f++)
            {
                p.Frame(new FrameInput { HasHit = true, Hit = hit, AllowApply = true });
                if (p.StatusText.Contains("The bridge is built")) stage2 = true;
            }
            // without abandoning, the second step runs (here it finds no bridge: the test world doesn't build);
            // after abandoning, it never runs
            Assert.Equal(!abandon, stage2);
        }
    }
}
