using System.Linq;
using Colossal.Mathematics;
using InterchangeStudio.Core;
using InterchangeStudio.Testing;
using Unity.Mathematics;
using Xunit;
using M = InterchangeStudio.Core.Planner.ToolMode;

/* the author, 2026-10-31, from aerials of Phoenix: Loop 202's ramps beside the freeway, Loop 101's frontage roads. */
public class PhoenixTests
{
    static bool IsFrontage(CityBuilder c, Planner.Spec s) => s.Group == 0 && c.World.PrefabName(s.Prefab) is "Highway Oneway - 4 lanes" or "Highway Oneway - 2 lanes";

    [Theory]
    [InlineData(0)] [InlineData(1)] [InlineData(2)]
    public void FrontageRoadsRunWithTheTrafficAndMeetTheStreet(int size)
    {
        var city = CityBuilder.SeparatedCrossing();
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Frontage, Autofit = false }.WithSize(size), new float2(0, -12));
        Assert.True(run.Plan != null, run.Status);
        Assert.Contains("frontage road", run.Status);
        Assert.Empty(PlanChecks.Violations(run.Plan, city.World, allowDeadEnds: true));
        var front = run.Plan.Specs.Where(s => !s.Delete && IsFrontage(city, s)).ToList();
        Assert.NotEmpty(front);
        foreach (var s in front)
        {
            // south of the highway (z < 0) the eastbound side: traffic heads +x; north, westbound: -x
            float3 t = MathUtils.Tangent(s.Curve, 0.5f);
            float want = s.Curve.a.z < 0 ? 1f : -1f;
            Assert.True(math.normalizesafe(t.xz).x * want > 0.95f, $"a frontage piece at {s.Curve.a} runs against its highway's traffic");
            Assert.Equal(0, s.Group);                          // the frontage is never trimmed away with a slip ramp
            Assert.True(math.abs(s.Curve.a.z) > 12f + 7.5f + 7f, "the frontage overlaps the highway");
        }
        // each side's frontage passes through its junction on the cross street (x = 0)
        foreach (float side in new[] { -1f, 1f })
        {
            Assert.Contains(front, s => math.sign(s.Curve.a.z) == side && math.abs(s.Curve.d.x) < 0.5f && s.EndEntity != Entity.Null);
            Assert.Contains(front, s => math.sign(s.Curve.a.z) == side && math.abs(s.Curve.a.x) < 0.5f && s.StartEntity != Entity.Null);
        }
        Assert.Equal(5, run.Plan.GroupNames.Count);           // core + 4 slip ramps
    }

    [Fact]
    public void FrontageClimbsToAStreetThatGoesOver()
    {
        var city = CityBuilder.StreetOverCrossing();
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Frontage }, new float2(0, -12));
        Assert.True(run.Plan != null, run.Status);
        Assert.Empty(PlanChecks.Violations(run.Plan, city.World, allowDeadEnds: true));
        var front = run.Plan.Specs.Where(s => !s.Delete && IsFrontage(city, s)).ToList();
        Assert.Contains(front, s => s.E1 > 7f);                // up at the bridge (it meets the street 20 m down its slope)
        Assert.Contains(front, s => s.E0 < 0.01f);             // and back on the ground at its ends
    }

    [Fact]
    public void BareHighwayGetsItsStreetThenFrontageRoads()
    {
        var cfg = new PlanConfig { Mode = M.Frontage, Autofit = false };
        var stage1 = PlanChecks.Run(CityBuilder.BareHighway(), cfg, new float2(0, -12));
        Assert.True(stage1.Plan != null && stage1.Plan.NextStep, stage1.Status);
        var built = CityBuilder.BareHighwayWithRoadAt(600f);
        var pts = new System.Collections.Generic.List<float3>();
        foreach (var s in stage1.Plan.Specs.Where(s => !s.Delete))
        {
            if (pts.Count == 0) pts.Add(new float3(s.Curve.a.x, s.E0, s.Curve.a.z));
            pts.Add(new float3(s.Curve.d.x, s.E1, s.Curve.d.z));
        }
        built.Road("Large Road", "New Street", pts, maxPiece: 1000f);
        var run = PlanChecks.Run(built, cfg, new float2(0, -12));
        Assert.True(run.Plan != null, run.Status);
        Assert.Empty(PlanChecks.Violations(run.Plan, built.World, allowDeadEnds: true));
    }

    /*
     * the author, 2026-11-01: road-to-road merges get traffic lights; the ramps merge into the frontage on highway pieces, on the level.
     * 2026-11-08, after his own build: four lanes by the street, splitting into a two-lane frontage and a two-lane ramp.
     */
    [Theory]
    [InlineData(false)] [InlineData(true)]
    public void SlipRampsMergeOnLevelHighwayPieces(bool streetOver)
    {
        var city = streetOver ? CityBuilder.StreetOverCrossing() : CityBuilder.SeparatedCrossing();
        var run = PlanChecks.Run(city, new PlanConfig { Mode = M.Frontage }, new float2(0, -12));
        Assert.True(run.Plan != null, run.Status);
        var front = run.Plan.Specs.Where(s => !s.Delete && IsFrontage(city, s)).ToList();
        var slips = run.Plan.Specs.Where(s => !s.Delete && s.Group > 0).ToList();
        int merges = 0;
        foreach (var r in slips)
            foreach (var end in new[] { r.Curve.a, r.Curve.d })
            {
                var at = front.Where(f => math.distance(f.Curve.a.xz, end.xz) < 0.5f || math.distance(f.Curve.d.xz, end.xz) < 0.5f).ToList();
                if (at.Count == 0) continue;
                merges++;
                Assert.Equal(2, at.Count);
                Assert.Equal("Highway Oneway - 2 lanes", city.World.PrefabName(r.Prefab));
                Assert.Equal(new[] { "Highway Oneway - 2 lanes", "Highway Oneway - 4 lanes" }, at.Select(f => city.World.PrefabName(f.Prefab)).OrderBy(n => n));
                foreach (var f in at)
                {
                    Assert.True(math.abs(f.E0 - f.E1) < 0.01f, $"the frontage is climbing where a slip ramp meets it ({f.E0:0.0} to {f.E1:0.0} m)");
                }
            }
        Assert.Equal(4, merges);
    }

    /* the author, 2026-11-01: "any ramp should probably leave from level ground": not on the highway's slope up to its bridge */
    [Theory]
    [InlineData(M.Exit)] [InlineData(M.Spui)] [InlineData(M.Dumbbell)] [InlineData(M.Frontage)]
    public void RampsLeaveTheHighwayWhereItIsLevel(M mode)
    {
        var city = CityBuilder.SeparatedCrossing();     // the highway comes down off its bridge until 420 m out
        var run = PlanChecks.Run(city, new PlanConfig { Mode = mode }, new float2(0, -12));
        Assert.True(run.Plan != null, run.Status);
        foreach (var s in run.Plan.Specs.Where(s => !s.Delete && s.Group > 0))
        {
            if (s.StartEntity != Entity.Null && math.abs(s.Curve.a.z) <= 13f && math.abs(s.Curve.a.x) > 60f) Assert.True(math.abs(s.Curve.a.x) >= 445f, $"a ramp leaves the sloping highway at x = {s.Curve.a.x:0}");
            if (s.EndEntity != Entity.Null && math.abs(s.Curve.d.z) <= 13f && math.abs(s.Curve.d.x) > 60f) Assert.True(math.abs(s.Curve.d.x) >= 445f, $"a ramp joins the sloping highway at x = {s.Curve.d.x:0}");
        }
    }

    [Fact]
    public void ADiamondOnAStreetStillSlopingSaysSo()
    {
        var run = PlanChecks.Run(CityBuilder.StreetOverCrossing(), new PlanConfig { Mode = M.Exit, Autofit = false }, new float2(0, -12));
        Assert.True(run.Plan != null, run.Status);
        Assert.Contains("still sloping", run.Status);
    }

    [Theory]
    [InlineData(M.Exit)] [InlineData(M.Spui)]
    public void BesideHighwayRampsRunCloseThenFlare(M mode)
    {
        var city = CityBuilder.SeparatedCrossing();
        var cfg = new PlanConfig { Mode = mode, Autofit = false, TightRamps = true };
        var run = PlanChecks.Run(city, cfg, new float2(0, -12));
        Assert.True(run.Plan != null, run.Status);
        Assert.Empty(PlanChecks.Violations(run.Plan, city.World));
        // the off-ramp's distance from its carriageway's centre line, x metres along
        float Lateral(float x)
        {
            float best = float.MaxValue;
            foreach (var s in run.Plan.Specs.Where(s => !s.Delete && city.World.PrefabName(s.Prefab).Contains("Highway")))
                for (int i = 0; i <= 128; i++)
                {
                    var q = MathUtils.Position(s.Curve, i / 128f);
                    if (math.abs(q.x - x) < 1.5f && q.z < -12f - 7.5f) best = math.min(best, -q.z - 12f);
                }
            return best;
        }
        // a straight stretch just clear of the highway's edge (a 2-lane ramp: 7.5 + 7.5 + 2 m from the centre line)
        foreach (float x in new[] { -105f, -95f })
            Assert.InRange(Lateral(x), 16f, 18f);
    }
}
