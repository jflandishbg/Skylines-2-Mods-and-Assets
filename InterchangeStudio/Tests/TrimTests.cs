using System.Collections.Generic;
using Colossal.Mathematics;
using InterchangeStudio.Core;
using InterchangeStudio.Testing;
using Unity.Mathematics;
using Xunit;
using M = InterchangeStudio.Core.Planner.ToolMode;

/*
 * "Keep what the game accepts": the game is played by a stand-in that shows red on one chosen ramp in
 * whatever is previewed, every frame, as a real collision would. The tool must end up offering every
 * other ramp, and leaving that one out must not leave any piece hanging.
 */
public class TrimTests
{
    /// <summary>Run frames; the stand-in game marks red on every piece of the ramp named by pick(groupNames).</summary>
    static (Planner.Preview shown, Planner.Preview full, string status) Play(CityBuilder city, PlanConfig cfg, float2 at, System.Func<List<string>, int> pick, int frames = 300)
    {
        var planner = city.Planner(cfg);
        var hit = PlanChecks.HitNear(city.World, at);
        Planner.Preview last = null, full = null;
        for (int f = 0; f < frames; f++)
        {
            var input = new FrameInput { HasHit = true, Hit = hit, AllowApply = true };
            if (last != null)
            {
                int g = pick(last.GroupNames);
                foreach (var s in last.Specs)
                    if (!s.Delete && s.Group == g) input.Red.Add(new RedItem { What = "a new ramp", At = MathUtils.Position(s.Curve, 0.5f) });
                input.AllowApply = input.Red.Count == 0;
            }
            var o = planner.Frame(input);
            if (o.Emit != null) last = o.Emit;
            if (last != null && last.GroupNames.Count > 1 && (full == null || full.Specs.Count < last.Specs.Count)) full = last;
        }
        return (last, full, planner.StatusText);
    }

    /// <summary>Free ends that don't meet anything: leaving ramps out may not add any.</summary>
    static HashSet<float3> Loose(Planner.Preview pv)
    {
        var n = new Dictionary<float3, int>();
        foreach (var s in pv.Specs)
        {
            if (s.Delete) continue;
            if (s.StartEntity == Entity.Null) n[s.Curve.a] = (n.TryGetValue(s.Curve.a, out int a) ? a : 0) + 1;
            if (s.EndEntity == Entity.Null) n[s.Curve.d] = (n.TryGetValue(s.Curve.d, out int d) ? d : 0) + 1;
        }
        var loose = new HashSet<float3>();
        foreach (var kv in n) if (kv.Value == 1) loose.Add(kv.Key);
        return loose;
    }

    static void AssertTrimmed(Planner.Preview shown, Planner.Preview full, int dropped, string status)
    {
        Assert.NotNull(shown);
        Assert.False(shown.Specs.Exists(s => !s.Delete && s.Group == dropped), "the red ramp is still in the preview");
        int total = shown.GroupNames.Count - 1;
        for (int g = 1; g <= total; g++)
            if (g != dropped) Assert.True(shown.Specs.Exists(s => !s.Delete && s.Group == g), $"{shown.GroupNames[g]} was left out too");
        Assert.Contains($"Only {total - 1} of {total} ramps fit", status);
        Assert.Contains(shown.GroupNames[dropped], status);
        var before = Loose(full);
        foreach (var p in Loose(shown)) Assert.True(before.Contains(p), $"leaving the ramp out left a piece hanging at {p}");
    }

    static int Named(List<string> names, string name) => names.IndexOf(name);

    [Fact]
    public void DiamondLeavesOutTheOneRedRampWithoutAutofit()
    {
        var city = CityBuilder.SeparatedCrossing();
        var (shown, full, status) = Play(city, new PlanConfig { Mode = M.Exit, Autofit = false }, new float2(0, -12), n => Named(n, "the eastbound off-ramp"));
        AssertTrimmed(shown, full, Named(shown.GroupNames, "the eastbound off-ramp"), status);
        Assert.Empty(PlanChecks.Violations(shown, city.World));
    }

    [Fact]
    public void DiamondLeavesOutTheOneRedRampAfterAutofitTriesEveryLayout()
    {
        var city = CityBuilder.SeparatedCrossing();
        var (shown, full, status) = Play(city, new PlanConfig { Mode = M.Exit, Autofit = true }, new float2(0, -12), n => Named(n, "the westbound on-ramp"));
        AssertTrimmed(shown, full, Named(shown.GroupNames, "the westbound on-ramp"), status);
        Assert.Empty(PlanChecks.Violations(shown, city.World));
    }

    [Fact]
    public void SpuiKeepsItsOtherRampsAtTheSharedJunction()
    {
        var city = CityBuilder.SeparatedCrossing();
        var (shown, full, status) = Play(city, new PlanConfig { Mode = M.Spui, Autofit = false }, new float2(0, -12), n => Named(n, "the westbound off-ramp"));
        AssertTrimmed(shown, full, Named(shown.GroupNames, "the westbound off-ramp"), status);
        Assert.Empty(PlanChecks.Violations(shown, city.World));
    }
}
