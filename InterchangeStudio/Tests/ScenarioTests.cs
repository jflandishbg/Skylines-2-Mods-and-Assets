using System.Collections.Generic;
using System.IO;
using InterchangeStudio.Core;
using InterchangeStudio.Testing;
using Unity.Mathematics;
using Xunit;
using Xunit.Abstractions;
using M = InterchangeStudio.Core.Planner.ToolMode;

/*
 * Every style, planned offline against synthetic cities and checked against the engine rules. Each run
 * is also drawn into Tests/out/index.html (the review sheet), so a change can be looked at without
 * starting the game.
 */
public class ScenarioTests
{
    readonly ITestOutputHelper m_Out;
    public ScenarioTests(ITestOutputHelper output) { m_Out = output; }

    static readonly string OutDir = Path.GetFullPath(Path.Combine(System.AppContext.BaseDirectory, "..", "..", "..", "out"));

    public sealed class Case
    {
        public string Name, Title;
        public System.Func<CityBuilder> City;
        public PlanConfig Cfg;
        public float2 At;
        public float2? RampFrom;            // free ramp: where the first click goes
        public bool MustBuild = true;
        public bool DeadEndsOk;             // street closures leave legitimate stubs
    }

    static PlanConfig C(M mode) => new PlanConfig { Mode = mode };

    public static IEnumerable<Case> Cases()
    {
        yield return new Case { Name = "overpass-street-over", Title = "Overpass: street lifted over the highway", City = CityBuilder.AtGradeCrossing, Cfg = C(M.Overpass), At = new float2(0, -12) };
        yield return new Case { Name = "overpass-highway-over", Title = "Overpass: highway lifted over the street", City = CityBuilder.AtGradeCrossing, Cfg = C(M.Overpass) with { LiftStreet = false }, At = new float2(0, -12) };
        yield return new Case { Name = "rail", Title = "Road over railway", City = CityBuilder.RailCrossing, Cfg = C(M.Overpass), At = new float2(0, 0) };
        yield return new Case { Name = "diamond-stage1", Title = "Diamond at ground level (stage 1: bridge)", City = CityBuilder.AtGradeCrossing, Cfg = C(M.Exit), At = new float2(0, -12) };
        yield return new Case { Name = "diamond", Title = "Diamond under an existing highway bridge", City = () => CityBuilder.SeparatedCrossing(), Cfg = C(M.Exit), At = new float2(0, -12) };
        yield return new Case { Name = "diamond-short-piece", Title = "Diamond next to a 40 m highway piece (must not fold it)", City = CityBuilder.ShortPieceCrossing, Cfg = C(M.Exit), At = new float2(0, -12) };
        yield return new Case { Name = "spui", Title = "Single-point (SPUI)", City = () => CityBuilder.SeparatedCrossing(), Cfg = C(M.Spui), At = new float2(0, -12) };
        yield return new Case { Name = "dumbbell", Title = "Dumbbell: two roundabout terminals", City = () => CityBuilder.SeparatedCrossing(), Cfg = C(M.Dumbbell), At = new float2(0, -12) };
        yield return new Case { Name = "frontage", Title = "Frontage roads with slip ramps (Loop 101 style)", City = () => CityBuilder.SeparatedCrossing(), Cfg = C(M.Frontage), At = new float2(0, -12), DeadEndsOk = true };
        yield return new Case { Name = "frontage-street-over", Title = "Frontage roads climbing to a street that goes over", City = CityBuilder.StreetOverCrossing, Cfg = C(M.Frontage), At = new float2(0, -12), DeadEndsOk = true };
        yield return new Case { Name = "diamond-beside", Title = "Diamond, ramps beside the highway (Loop 202 style)", City = () => CityBuilder.SeparatedCrossing(), Cfg = C(M.Exit) with { TightRamps = true }, At = new float2(0, -12) };
        yield return new Case { Name = "spui-beside", Title = "Single-point, ramps beside the highway", City = () => CityBuilder.SeparatedCrossing(), Cfg = C(M.Spui) with { TightRamps = true }, At = new float2(0, -12) };
        yield return new Case { Name = "dumbbell-beside", Title = "Dumbbell, ramps beside the highway", City = () => CityBuilder.SeparatedCrossing(), Cfg = C(M.Dumbbell) with { TightRamps = true }, At = new float2(0, -12) };
        yield return new Case { Name = "street-over-diamond-beside", Title = "Diamond beside the highway on a street that goes over", City = CityBuilder.StreetOverCrossing, Cfg = C(M.Exit) with { TightRamps = true }, At = new float2(0, -12) };
        yield return new Case { Name = "bestfit-restored", Title = "Restored Best fit: compare maintained styles", City = () => CityBuilder.SeparatedCrossing(), Cfg = C(M.Auto), At = new float2(0, -12) };
        yield return new Case { Name = "new-street", Title = "Bare highway: a new cross street (then ramps)", City = CityBuilder.BareHighway, Cfg = C(M.Exit), At = new float2(0, -12), DeadEndsOk = true };
        yield return new Case { Name = "stubs", Title = "Streets drawn up to the highway: joined across it", City = () => CityBuilder.StubsAtHighway(), Cfg = C(M.Exit), At = new float2(5, -12) };
        yield return new Case { Name = "stubs-side-street", Title = "...with a side street close by (steeper slope)", City = () => CityBuilder.StubsAtHighway(200f), Cfg = C(M.Exit), At = new float2(5, -12) };
        yield return new Case { Name = "new-street-close-road", Title = "New street coming down in time for a road 180 m away", City = () => CityBuilder.BareHighwayWithRoadAt(180f), Cfg = C(M.Exit), At = new float2(0, -12), DeadEndsOk = true };
        yield return new Case { Name = "street-over-diamond", Title = "Diamond on a street that goes over", City = CityBuilder.StreetOverCrossing, Cfg = C(M.Exit), At = new float2(0, -12) };
        yield return new Case { Name = "street-over-spui", Title = "Single-point on a street that goes over", City = CityBuilder.StreetOverCrossing, Cfg = C(M.Spui), At = new float2(0, -12) };
        yield return new Case
        {
            Name = "highway-end",
            Title = "Highway end: two one-way carriageways merging into one road",
            City = () =>
            {
                var c = new CityBuilder();
                c.Road("Highway Oneway - 4 lanes", "Eastbound", new[] { new float3(-500, 0, -13), new float3(0, 0, -13) });
                c.Road("Highway Oneway - 4 lanes", "Westbound", new[] { new float3(-6, 0, 13), new float3(-500, 0, 13) });
                return c;
            },
            Cfg = C(M.Ending),
            At = new float2(-10, -13),
            DeadEndsOk = true,
        };
    }

    [Fact]
    public void EveryStyleBuildsCleanAndDrawsAReviewSheet()
    {
        var sheet = new PlanSvg.Sheet(OutDir);
        var problems = new List<string>();
        foreach (var c in Cases())
        {
            var city = c.City();
            PlanRun run;
            if (c.RampFrom.HasValue)
            {
                // free ramp: click where it leaves, then point at where it joins
                var planner = city.Planner(c.Cfg);
                planner.Frame(new FrameInput { HasHit = true, Hit = PlanChecks.HitNear(city.World, c.RampFrom.Value), Apply = true, AllowApply = true });
                run = new PlanRun { World = city.World };
                var to = PlanChecks.HitNear(city.World, c.At);
                for (int f = 0; f < 16 && run.Plan == null; f++)
                {
                    var o = planner.Frame(new FrameInput { HasHit = true, Hit = to, AllowApply = true });
                    run.Plan = o.Emit; run.Status = planner.StatusText; run.Frames = f + 1;
                }
            }
            else run = PlanChecks.Run(city, c.Cfg, c.At);
            var v = run.Plan == null ? new List<string>() : PlanChecks.Violations(run.Plan, city.World, c.DeadEndsOk);
            sheet.Add(c.Name, c.Title, city.World, run.Plan, run.Status, v.Count);
            m_Out.WriteLine($"{c.Name}: {(run.Plan == null ? "NO PLAN" : run.Plan.Specs.Count + " specs")} in {run.Frames} frame(s); {run.Status}");
            if (run.Plan == null && c.MustBuild) problems.Add($"{c.Name}: nothing planned ({run.Status})");
            foreach (var x in v) problems.Add($"{c.Name}: {x}");
            foreach (var l in city.Log.Lines) if (l.StartsWith("No route") || l.StartsWith("ERROR")) m_Out.WriteLine("    " + l);
        }
        m_Out.WriteLine("Review sheet: " + Path.Combine(OutDir, "index.html"));
        Assert.True(problems.Count == 0, "\n" + string.Join("\n", problems));
    }

    [Fact]
    public void AutofitPlansWithACopyAndNeverChangesThePlayersSettings()
    {
        var city = CityBuilder.SeparatedCrossing();
        var cfg = new PlanConfig { Mode = M.Spui, Grade = 0.03f, Clearance = 18f };
        var planner = city.Planner(cfg);
        var hit = PlanChecks.HitNear(city.World, new float2(0, -12));
        for (int f = 0; f < 16; f++) planner.Frame(new FrameInput { HasHit = true, Hit = hit, AllowApply = true });
        Assert.Same(cfg, planner.Cfg);
    }
}
