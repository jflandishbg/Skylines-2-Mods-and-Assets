using InterchangeStudio.Core;
using InterchangeStudio.Testing;
using Unity.Mathematics;
using Xunit;
using M = InterchangeStudio.Core.Planner.ToolMode;

/*
 * Autofit in the game: the player's cursor wanders between the two carriageways of one crossing while
 * autofit works through layouts. Seen 2026-10-15: each move restarted autofit at layout 1, so it kept
 * showing the same red layout and never got past layout 3.
 */
public class AutofitTests
{
    [Fact]
    public void AutofitKeepsItsPlaceWhenTheCursorMovesToTheOtherCarriageway()
    {
        var city = CityBuilder.SeparatedCrossing();
        var planner = city.Planner(new PlanConfig { Mode = M.Exit, Autofit = true });
        var east = PlanChecks.HitNear(city.World, new float2(-30, -12));
        var west = PlanChecks.HitNear(city.World, new float2(30, 12));

        // the game shows red on whatever layout is previewed, until autofit has moved on twice
        int moves = 0;
        for (int f = 0; f < 40 && moves < 2; f++)
        {
            var o = planner.Frame(new FrameInput { HasHit = true, Hit = east, AllowApply = false });
            var input = new FrameInput { HasHit = true, Hit = east, AllowApply = false };
            if (o.Emit != null && o.Emit.Specs.Count > 0)
            {
                var c = o.Emit.Specs[o.Emit.Specs.Count - 1].Curve;
                input.Red.Add(new RedItem { What = "a new Highway Oneway - 2 lanes", At = c.a });
            }
            planner.Frame(input);
            if (planner.StatusText.Contains("doesn't fit cleanly")) moves++;
        }
        Assert.Equal(2, moves);

        // now the cursor drifts onto the other carriageway, and the game shows no red
        for (int f = 0; f < 8; f++) planner.Frame(new FrameInput { HasHit = true, Hit = west, AllowApply = true });
        Assert.Contains("Autofit found a clean layout (try 3)", planner.StatusText);
    }
}
