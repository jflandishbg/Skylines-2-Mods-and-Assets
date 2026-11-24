using InterchangeStudio.Core;
using InterchangeStudio.Testing;
using Unity.Mathematics;
using Xunit;
using Xunit.Abstractions;
using M = InterchangeStudio.Core.Planner.ToolMode;

/* The one-line summary under the status: what a click would build, in numbers. */
public class SummaryTests
{
    readonly ITestOutputHelper m_Out;
    public SummaryTests(ITestOutputHelper o) { m_Out = o; }

    [Fact]
    public void ABridgeStageSaysWhatItReplacesAndThatRampsFollow()
    {
        var city = CityBuilder.AtGradeCrossing();
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Exit }, new float2(0, -12));
        string s = Planner.Summarize(run.Plan);
        m_Out.WriteLine(s);
        Assert.StartsWith("New road: ", s);
        Assert.Contains("of it raised", s);
        Assert.Contains("existing pieces replaced", s);
        Assert.Contains("the ramps follow automatically", s);
    }

    [Fact]
    public void ADiamondOnAnExistingBridgeReplacesNothing()
    {
        var city = CityBuilder.SeparatedCrossing();
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Exit }, new float2(0, -12));
        string s = Planner.Summarize(run.Plan);
        m_Out.WriteLine(s);
        Assert.DoesNotContain("replaced", s);
        Assert.DoesNotContain("ramps follow", s);
    }

    [Fact]
    public void TheSummaryShowsWithAPreviewAndClearsWithout()
    {
        var city = CityBuilder.SeparatedCrossing();
        var p = city.Planner(new PlanConfig { Mode = M.Exit });
        var hit = PlanChecks.HitNear(city.World, new float2(0, -12));
        for (int f = 0; f < 5; f++) p.Frame(new FrameInput { HasHit = true, Hit = hit, AllowApply = true });
        Assert.StartsWith("New road: ", p.PreviewSummary);
        p.Frame(new FrameInput { HasHit = false, AllowApply = true });
        Assert.Equal("", p.PreviewSummary);
    }
}
