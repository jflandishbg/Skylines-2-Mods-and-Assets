using System.Collections.Generic;
using Colossal.Mathematics;
using InterchangeStudio.Core;
using InterchangeStudio.Testing;
using Unity.Mathematics;
using Xunit;

/* Regression tests for the Neon + Claude collaboration pass: settled verdicts, no silent partial auto-apply,
 * NetWorld.Apply + Stage 2 pre-validation, sunken elevations, LHT guard, Undo, railway avoidance, NewHighway
 * length-weighted prefab selection, Highway End RHT pairing, per-mode autofit, and Core Audit. */
public class CollabUpgradeTests
{
    [Fact]
    public void LeftHandTrafficIsRefusedCleanly()
    {
        var city = CityBuilder.SeparatedCrossing();
        city.World.LeftHandTraffic = true;
        var p = city.Planner(new PlanConfig { Mode = Planner.ToolMode.Exit });
        var hit = PlanChecks.HitNear(city.World, float2.zero);
        var o = p.Frame(new FrameInput { HasHit = true, Hit = hit, AllowApply = true });
        Assert.Null(o.Emit);
        Assert.False(o.ApplyNow);
        Assert.Equal(2, p.StatusKind);
        Assert.Contains("Left-hand traffic", p.StatusText);
    }

    [Fact]
    public void Stage2AutoApplyWaitsForSettledVerdict()
    {
        var city = CityBuilder.AtGradeCrossing();
        var p = city.Planner(new PlanConfig { Mode = Planner.ToolMode.Exit, LiftStreet = true });
        var hit = PlanChecks.HitNear(city.World, float2.zero);

        // Hover until Stage 1 preview is ready
        FrameOutput stage1Out = null;
        for (int i = 0; i < 6; i++)
            stage1Out = p.Frame(new FrameInput { HasHit = true, Hit = hit, AllowApply = true });
        Assert.NotNull(stage1Out.Emit);

        // Click to apply Stage 1
        var click = p.Frame(new FrameInput { HasHit = true, Hit = hit, Apply = true, AllowApply = true });
        Assert.True(click.ApplyNow);
        Assert.True(p.Stage2Waiting);

        // Virtually apply Stage 1 to the world, then step frames into Stage 2
        var afterStage1 = city.World.Apply(stage1Out.Emit);
        p.SetWorld(afterStage1);

        int autoFramesWithEmit = 0;
        bool applied = false;
        for (int f = 0; f < 30; f++)
        {
            var o = p.Frame(new FrameInput { AllowApply = true });
            if (o.ApplyNow)
            {
                // Must have waited at least 2 preview frames (applied on 3rd auto-apply frame)
                Assert.True(autoFramesWithEmit >= 2, $"Applied too early after only {autoFramesWithEmit} emitted preview frame(s)");
                applied = true;
                break;
            }
            if (o.Emit != null) autoFramesWithEmit++;
        }
        Assert.True(applied, "Stage 2 should auto-apply once verdict settles cleanly");
        Assert.Contains("built:", p.StatusText.ToLowerInvariant());
    }

    [Fact]
    public void Stage2NeverSilentlyAutoAppliesTrimmedPlan()
    {
        var city = CityBuilder.AtGradeCrossing();
        var p = city.Planner(new PlanConfig { Mode = Planner.ToolMode.Exit, LiftStreet = true, Autofit = false });
        var hit = PlanChecks.HitNear(city.World, float2.zero);

        FrameOutput stage1Out = null;
        for (int i = 0; i < 6; i++)
            stage1Out = p.Frame(new FrameInput { HasHit = true, Hit = hit, AllowApply = true });
        Assert.NotNull(stage1Out.Emit);

        var click = p.Frame(new FrameInput { HasHit = true, Hit = hit, Apply = true, AllowApply = true });
        Assert.True(click.ApplyNow);

        p.SetWorld(city.World.Apply(stage1Out.Emit));

        // Wait until Stage 2 emits its ramp preview, then feed red on one ramp so trimming kicks in
        Planner.Preview stage2Preview = null;
        for (int f = 0; f < 15; f++)
        {
            var o = p.Frame(new FrameInput { AllowApply = true });
            if (o.Emit != null) { stage2Preview = o.Emit; break; }
        }
        Assert.NotNull(stage2Preview);

        // Pick a point on ramp group 1
        var rampSpec = stage2Preview.Specs.Find(s => !s.Delete && s.Group == 1);
        Assert.NotNull(rampSpec);
        float3 redPos = MathUtils.Position(rampSpec.Curve, 0.5f);

        // Feed red for 3 frames so trimming drops group 1
        for (int f = 0; f < 4; f++)
        {
            var inp = new FrameInput { AllowApply = false };
            inp.Red.Add(new RedItem { What = "a new ramp (overlaps something)", At = redPos });
            var o = p.Frame(inp);
            Assert.False(o.ApplyNow);
        }

        // Now feed clean AllowApply for 6 frames: because ramps were trimmed, it MUST NOT silently auto-apply
        bool showedTrimmed = false;
        for (int f = 0; f < 6; f++)
        {
            var o = p.Frame(new FrameInput { AllowApply = true });
            Assert.False(o.ApplyNow, "Trimmed Stage 2 plan must never silently auto-apply");
            if (o.Emit != null && p.StatusText.Contains("Click to build")) showedTrimmed = true;
        }
        Assert.True(showedTrimmed, "Expected trimmed Stage 2 to pause for user confirmation; status was: " + p.StatusText);
    }

    [Fact]
    public void Stage1RefusesDumbbellWhenOnlyOneCarriagewayCanBeLifted()
    {
        // Build a single-carriageway at-grade crossing (no partner carriageway)
        var city = new CityBuilder();
        city.Road("Highway Oneway - 3 lanes", "I-10", new[] { new float3(-600, 0, -10), new float3(0, 0, -10), new float3(600, 0, -10) });
        city.Road("Large Road", "Main St", new[] { new float3(0, 0, -400), new float3(0, 0, -10), new float3(0, 0, 400) });

        var run = PlanChecks.Run(city, new PlanConfig { Mode = Planner.ToolMode.Dumbbell, LiftStreet = false, Autofit = false }, new float2(0, -10));
        Assert.Null(run.Plan);
        Assert.Contains("stage 2", run.Status.ToLowerInvariant());
    }

    [Fact]
    public void SunkenEndingPreservesNegativeElevation()
    {
        var city = new CityBuilder();
        // Two parallel one-way highway dead ends in a -8 m trench, heading +X (inEnd on right Z=-12, outEnd on left Z=+12)
        city.Road("Highway Oneway - 3 lanes", "I-10 E", new[] { new float3(-400, -8, -12), new float3(0, -8, -12) });
        city.Road("Highway Oneway - 3 lanes", "I-10 W", new[] { new float3(0, -8, 12), new float3(-400, -8, 12) });

        var run = PlanChecks.Run(city, new PlanConfig { Mode = Planner.ToolMode.Ending, EndRoad = 2 }, new float2(-10, -12));
        Assert.NotNull(run.Plan);
        Assert.Empty(PlanChecks.Violations(run.Plan, run.World, allowDeadEnds: true, allowBelow: true));
        // The merge legs should stay at -8 m rather than jumping up to 0 m
        Assert.Contains(run.Plan.Specs, s => !s.Delete && s.E1 < -7f);
    }

    [Fact]
    public void HighwayEndEnforcesRightHandCarriagewayOrder()
    {
        // Reversed pair: arriving carriageway on the LEFT (Z=+12) and departing on the RIGHT (Z=-12) when heading +X
        var city = new CityBuilder();
        city.Road("Highway Oneway - 3 lanes", "Wrong E", new[] { new float3(-400, 0, 12), new float3(-100, 0, 12), new float3(0, 0, 12) });
        city.Road("Highway Oneway - 3 lanes", "Wrong W", new[] { new float3(0, 0, -12), new float3(-100, 0, -12), new float3(-400, 0, -12) });

        var run = PlanChecks.Run(city, new PlanConfig { Mode = Planner.ToolMode.Ending, Autofit = false }, new float2(-10, 12));
        Assert.Null(run.Plan);
    }

    [Fact]
    public void NewHighwayPrefabWeightsByLengthAndExcludesOneLaneRamps()
    {
        var city = new CityBuilder();
        // 10 short 1-lane ramp pieces vs 2 long 3-lane highway pieces
        for (int i = 0; i < 10; i++)
            city.Road("Highway Oneway - 1 lane", "Ramp", new[] { new float3(2000 + i * 50, 0, 2000), new float3(2030 + i * 50, 0, 2000) });
        city.Road("Highway Oneway - 3 lanes", "I-10", new[] { new float3(2000, 0, 2400), new float3(2500, 0, 2400) });
        city.Road("Large Road", "Hickory St", new[] { new float3(-400, 0, 0), new float3(400, 0, 0) });

        var run = PlanChecks.Run(city, new PlanConfig { Mode = Planner.ToolMode.Overpass }, float2.zero);
        Assert.NotNull(run.Plan);
        Assert.All(run.Plan.Specs.FindAll(s => !s.Delete), s => Assert.Equal("Highway Oneway - 3 lanes", run.World.PrefabName(s.Prefab)));
    }

    [Fact]
    public void NewStreetAvoidsCreatingRailwayLevelCrossing()
    {
        var city = CityBuilder.BareHighway();
        // Put a ground-level railway track parallel to the highway 70 m south, inside where the new street's slope would land
        city.Road("Twoway Train Track", "Rail", new[] { new float3(-600, 0, -70), new float3(600, 0, -70) }, track: true);

        var run = PlanChecks.Run(city, new PlanConfig { Mode = Planner.ToolMode.Overpass, LiftStreet = true, Autofit = false }, new float2(0, -12));
        // Either cleanly refused (too close to descend before rail) or stops short with zero rail-crossing audit violations
        if (run.Plan != null)
            Assert.Empty(Planner.Audit(run.Plan, run.World, allowDeadEnds: true));
    }

    [Fact]
    public void AutofitNeverFlipsExplicitStreetUnder()
    {
        // At-grade crossing where street-under is blocked by a close side road: autofit must NOT flip Dig=true into a bridge
        var city = CityBuilder.AtGradeCrossing();
        city.Road("Large Road", "Close St", new[] { new float3(-300, 0, 60), new float3(0, 0, 60), new float3(300, 0, 60) });

        var run = PlanChecks.Run(city, new PlanConfig { Mode = Planner.ToolMode.Overpass, LiftStreet = true, Dig = true, Autofit = true }, float2.zero);
        if (run.Plan != null)
        {
            // Every non-zero elevation must remain <= 0 (never flipped to a raised bridge)
            Assert.DoesNotContain(run.Plan.Specs, s => !s.Delete && (s.E0 > 0.5f || s.E1 > 0.5f));
        }
    }

    [Fact]
    public void UndoRestoresOriginalNetworkAfterApply()
    {
        var city = CityBuilder.AtGradeCrossing();
        int origCount = city.World.RoadEdges.Count;
        var p = city.Planner(new PlanConfig { Mode = Planner.ToolMode.Overpass, LiftStreet = true });
        var hit = PlanChecks.HitNear(city.World, float2.zero);

        FrameOutput previewOut = null;
        for (int i = 0; i < 6; i++)
            previewOut = p.Frame(new FrameInput { HasHit = true, Hit = hit, AllowApply = true });
        Assert.NotNull(previewOut.Emit);

        var applyOut = p.Frame(new FrameInput { HasHit = true, Hit = hit, Apply = true, AllowApply = true });
        Assert.True(applyOut.ApplyNow);
        Assert.True(p.CanUndo);

        var afterBuild = city.World.Apply(previewOut.Emit);
        p.SetWorld(afterBuild);

        Assert.True(p.RequestUndo());
        FrameOutput undoPreview = null;
        for (int i = 0; i < 4; i++)
            undoPreview = p.Frame(new FrameInput { AllowApply = true });
        Assert.NotNull(undoPreview.Emit);

        var undoApply = p.Frame(new FrameInput { Apply = true, AllowApply = true });
        Assert.True(undoApply.ApplyNow);
        Assert.False(p.CanUndo);

        var afterUndo = afterBuild.Apply(undoPreview.Emit);
        Assert.Equal(origCount, afterUndo.RoadEdges.Count);
    }

    [Fact]
    public void CoreAuditCatchesMidCurveSteepnessAndNewRailCrossing()
    {
        var city = new CityBuilder();
        city.Road("Twoway Train Track", "Rail", new[] { new float3(0, 0, -200), new float3(0, 0, 200) }, track: true);
        var roadPrefab = city.World.RoadPrefabs[0];

        // 1. Mid-curve steepness: ends level at 0 and 4m over 60m (~6.7% overall) but sharp S-kink in middle
        var kink = new Bezier4x3(new float3(-100, 0, 100), new float3(-80, 0, 100), new float3(-60, 12, 100), new float3(-40, 4, 100));
        var pvSteep = new Planner.Preview();
        pvSteep.Specs.Add(new Planner.Spec { Prefab = roadPrefab, Curve = kink, E0 = 0f, E1 = 4f });
        var vSteep = Planner.Audit(pvSteep, city.World, allowDeadEnds: true);
        Assert.Contains(vSteep, s => s.Contains("steep"));

        // 2. New railway level crossing at ground level
        var crossRail = NetUtils.StraightCurve(new float3(-40, 0, 0), new float3(40, 0, 0));
        var pvRail = new Planner.Preview();
        pvRail.Specs.Add(new Planner.Spec { Prefab = roadPrefab, Curve = crossRail, E0 = 0f, E1 = 0f });
        var vRail = Planner.Audit(pvRail, city.World, allowDeadEnds: true);
        Assert.Contains(vRail, s => s.ToLowerInvariant().Contains("rail"));
    }

    [Fact]
    public void HighwayEndRefusesRoadOrRailJustPastMergePoint()
    {
        // Standard Ending mergeDist for 24 m separation is ~53 m (so mergeXZ.x ~ 53)
        // Put a railway track at x = 60 (~7 m past merge) and an ordinary road at x = 75 (~22 m past merge)
        var cityRail = new CityBuilder();
        cityRail.Road("Highway Oneway - 3 lanes", "I-10 E", new[] { new float3(-400, 0, -12), new float3(0, 0, -12) });
        cityRail.Road("Highway Oneway - 3 lanes", "I-10 W", new[] { new float3(0, 0, 12), new float3(-400, 0, 12) });
        cityRail.Road("Twoway Train Track", "Rail", new[] { new float3(60, 0, -200), new float3(60, 0, 200) }, track: true);
        var runRail = PlanChecks.Run(cityRail, new PlanConfig { Mode = Planner.ToolMode.Ending, Autofit = false }, new float2(-10, -12));
        Assert.Null(runRail.Plan);

        var cityRoad = new CityBuilder();
        cityRoad.Road("Highway Oneway - 3 lanes", "I-10 E", new[] { new float3(-400, 0, -12), new float3(0, 0, -12) });
        cityRoad.Road("Highway Oneway - 3 lanes", "I-10 W", new[] { new float3(0, 0, 12), new float3(-400, 0, 12) });
        cityRoad.Road("Large Road", "Close Ave", new[] { new float3(75, 0, -200), new float3(75, 0, 200) });
        var runRoad = PlanChecks.Run(cityRoad, new PlanConfig { Mode = Planner.ToolMode.Ending, Autofit = false }, new float2(-10, -12));
        Assert.Null(runRoad.Plan);
    }

    [Fact]
    public void SelfTestCoversSeparatedCrossingsAndDeadEnds()
    {
        var city = CityBuilder.SeparatedCrossing();
        var p = city.Planner(new PlanConfig { Mode = Planner.ToolMode.Exit });
        var spots = p.SelfTestSpots();
        Assert.Contains(spots, s => s.Kind == "separated crossing");
        Assert.Contains(spots, s => s.Kind == "highway dead end");
    }
}
