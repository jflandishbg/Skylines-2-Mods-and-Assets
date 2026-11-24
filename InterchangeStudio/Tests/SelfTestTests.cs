using InterchangeStudio.Core;
using InterchangeStudio.Testing;
using Xunit;
using Xunit.Abstractions;

/* The in-game self-test, run offline (the stand-in game shows no red): it finds spots, plans each style, restores the settings. */
public class SelfTestTests
{
    readonly ITestOutputHelper m_Out;
    public SelfTestTests(ITestOutputHelper o) { m_Out = o; }

    [Fact]
    public void TheSelfTestVisitsEachKindOfSpotAndPutsTheSettingsBack()
    {
        var city = CityBuilder.AtGradeCrossing();
        city.Road("Large Road", "Hickory Street", new[] { new Unity.Mathematics.float3(-900, 0, 1500), new Unity.Mathematics.float3(900, 0, 1500) });
        var cfg = new PlanConfig { Mode = Planner.ToolMode.Spui, Grade = 0.06f };
        var p = city.Planner(cfg);
        var run = new SelfTestRun(p);
        Assert.True(run.Count >= 6, $"only {run.Count} cases");
        int guard = 0;
        while (!run.Done && guard++ < 100000) p.Frame(run.Input(null, true)).Also(run);
        Assert.True(run.Done);
        Assert.Same(cfg, p.Cfg);
        string report = run.Report();
        m_Out.WriteLine(report);
        Assert.Contains("ground-level crossing", report);
        Assert.Contains("bare highway", report);
        Assert.Contains("street with no highway (Hickory Street)", report);
        Assert.DoesNotContain("NOT PLANNED  diamond      ground-level", report);
    }
}

static class TestExt { public static void Also(this FrameOutput o, SelfTestRun r) => r.Observe(o); }
