using System.Collections.Generic;
using System.Linq;
using InterchangeStudio.Core;
using InterchangeStudio.Testing;
using Unity.Mathematics;
using Xunit;
using M = InterchangeStudio.Core.Planner.ToolMode;

public class DumbbellTests
{
    [Theory]
    [InlineData(0)] [InlineData(1)] [InlineData(2)]
    public void TwoClosedRingsAndFourRampsHaveNoDanglingEnds(int size)
    {
        var city = CityBuilder.SeparatedCrossing();
        var cfg = new PlanConfig { Mode = M.Dumbbell, Autofit = false }.WithSize(size);
        var run = PlanChecks.Run(city, cfg, new float2(0, -12));
        Assert.True(run.Plan != null, run.Status);
        Assert.Contains("two roundabouts", run.Status);
        Assert.Empty(PlanChecks.Violations(run.Plan, city.World));
        var rings = run.Plan.Specs.Where(s => !s.Delete && city.World.PrefabName(s.Prefab) == "Highway Oneway - 3 lanes").ToList();
        Assert.Equal(8, rings.Count);
        foreach (var arc in rings)
        {
            Assert.Single(rings.Where(s => math.distance(s.Curve.a, arc.Curve.d) < 0.01f));
            Assert.Single(rings.Where(s => math.distance(s.Curve.d, arc.Curve.a) < 0.01f));
            Assert.Equal(0, arc.Group); // rings/street changes are never trimmed as optional ramps
            // A quarter arc has perpendicular radial vectors and turns in the same direction.
            float2 t0 = math.normalizesafe((arc.Curve.b - arc.Curve.a).xz);
            float2 t1 = math.normalizesafe((arc.Curve.d - arc.Curve.c).xz);
            Assert.True(t0.x * t1.y - t0.y * t1.x > 0.8f);
        }
        Assert.Equal(5, run.Plan.GroupNames.Count); // core + 4 ramps
        var deletes = run.Plan.Specs.Where(s => s.Delete).Select(s => s.Original).ToList();
        Assert.Equal(deletes.Count, deletes.Distinct().Count());
        Assert.DoesNotContain(run.Plan.Specs, s => !s.Delete && (deletes.Contains(s.StartEntity) || deletes.Contains(s.EndEntity)));
    }

    // the author, 2026-10-31: "the dumbbell doesn't appear to spawn". On a bare highway stage 1 lays a new street over
    // it, and stage 2 then refused it ("needs the highway above the cross street"). Now the rings sit on the deck.
    [Theory]
    [InlineData(0)] [InlineData(1)] [InlineData(2)]
    public void BareHighwayDumbbellBuildsItsRingsOnTheNewBridge(int size)
    {
        var cfg = new PlanConfig { Mode = M.Dumbbell, Autofit = false }.WithSize(size);
        var stage1 = PlanChecks.Run(CityBuilder.BareHighway(), cfg, new float2(0, -12));
        Assert.True(stage1.Plan != null, stage1.Status);
        Assert.True(stage1.Plan.NextStep);
        // the same city with that bridge built
        var built = CityBuilder.BareHighwayWithRoadAt(600f);
        var pts = new List<float3>();
        foreach (var s in stage1.Plan.Specs.Where(s => !s.Delete))
        {
            if (pts.Count == 0) pts.Add(new float3(s.Curve.a.x, s.E0, s.Curve.a.z));
            pts.Add(new float3(s.Curve.d.x, s.E1, s.Curve.d.z));
        }
        built.Road("Large Road", "New Street", pts, maxPiece: 1000f);
        var run = PlanChecks.Run(built, cfg, new float2(0, -12));
        Assert.True(run.Plan != null, run.Status);
        Assert.Contains("two roundabouts", run.Status);
        Assert.Empty(PlanChecks.Violations(run.Plan, built.World));
        var rings = run.Plan.Specs.Where(s => !s.Delete && built.World.PrefabName(s.Prefab) == "Highway Oneway - 3 lanes").ToList();
        Assert.Equal(8, rings.Count);
        Assert.All(rings, r => Assert.InRange(r.E0, 8f, 10f));               // up on the deck
        // close beside the highway, not out past the ramps
        float hwEdge = 12f + 7.5f;
        Assert.All(rings, r => Assert.True(math.abs(r.Curve.a.z) > hwEdge + 4f && math.abs(r.Curve.a.z) < hwEdge + 2f * 36f + 20f));
    }

    [Fact]
    public void ExistingShortDeckIsRefusedWithAReason()
    {
        // a street already over the highway whose flat deck is too short to carry a roundabout
        var run = PlanChecks.Run(CityBuilder.StreetOverCrossing(), new PlanConfig { Mode = M.Dumbbell }, new float2(0, -12));
        Assert.Null(run.Plan);
        Assert.False(string.IsNullOrEmpty(run.Status));
    }

    [Fact]
    public void RefusesHalfAnInterchange()
    {
        var run = PlanChecks.Run(CityBuilder.SeparatedCrossing(), new PlanConfig { Mode = M.Dumbbell, BothCarriageways = false }, new float2(0, -12));
        Assert.Null(run.Plan);
        Assert.Contains("both carriageways", run.Status);
    }

    [Fact]
    public void GroundLevelCrossingSchedulesDumbbellAfterLiftingHighway()
    {
        var city = CityBuilder.AtGradeCrossing();
        var cfg = new PlanConfig { Mode = M.Dumbbell, LiftStreet = true };
        var p = city.Planner(cfg);
        var o = p.Frame(new FrameInput { HasHit = true, Hit = PlanChecks.HitNear(city.World, new float2(0, -12)) });
        Assert.NotNull(o.Emit);
        Assert.True(o.Emit.NextStep);
        Assert.Equal(M.Dumbbell, o.Emit.NextMode);
        Assert.All(o.Emit.Specs.Where(s => s.Delete), s => Assert.Contains("Highway", city.World.PrefabName(city.World.GetComponentData<PrefabRef>(s.Original).m_Prefab)));
        Assert.Same(cfg, p.Cfg);
    }

    [Fact]
    public void DroppingARampNeverDropsARingOrStreetReplacement()
    {
        var run = PlanChecks.Run(CityBuilder.SeparatedCrossing(), new PlanConfig { Mode = M.Dumbbell }, new float2(0, -12));
        Assert.NotNull(run.Plan);
        var trimmed = Planner.Trimmed(run.Plan, new[] { 1 });
        Assert.Equal(run.Plan.Specs.Count(s => s.Group == 0), trimmed.Specs.Count(s => s.Group == 0));
        Assert.DoesNotContain(trimmed.Specs, s => s.Group == 1);
    }

    [Fact]
    public void SavedDumbbellModeSurvivesValidation()
    {
        Assert.Equal(M.Dumbbell, (new PlanConfig { Mode = M.Dumbbell }).Supported().Mode);
    }
}
