// Interchange Studio - Testing/PlanChecks.cs
// Runs the planner against a synthetic city and checks each plan against the engine rules learned in
// the game (each one cost a real bug): no split slivers, exact joins, no dangling new pieces, sane
// grades, and never splitting a road that the same build deletes.
using System.Collections.Generic;
using System.Text;
using Colossal.Mathematics;
using InterchangeStudio.Core;
using Unity.Mathematics;

namespace InterchangeStudio.Testing
{
    public sealed class PlanRun
    {
        public Planner.Preview Plan;      // null when nothing was planned
        public string Status;
        public int Frames;
        public NetWorld World;
    }

    public static class PlanChecks
    {
        /// <summary>Point at the road nearest <paramref name="at"/> and run frames until a preview appears (autofit may need a few).</summary>
        public static PlanRun Run(CityBuilder city, PlanConfig cfg, float2 at, int maxFrames = 16)
        {
            var planner = city.Planner(cfg);
            var hit = HitNear(city.World, at);
            var run = new PlanRun { World = city.World };
            for (int f = 0; f < maxFrames; f++)
            {
                var o = planner.Frame(new FrameInput { HasHit = true, Hit = hit, AllowApply = true });
                run.Frames = f + 1;
                run.Status = planner.StatusText;
                if (o.Emit != null) { run.Plan = o.Emit; break; }
            }
            return run;
        }

        public static RaycastHit HitNear(NetWorld w, float2 at)
        {
            Entity best = Entity.Null; float bd = float.MaxValue, bt = 0;
            foreach (var e in w.RoadEdges)
            {
                var c = w.GetComponentData<Curve>(e).m_Bezier;
                float d = MathUtils.Distance(c.xz, at, out float t);
                if (d < bd) { bd = d; best = e; bt = t; }
            }
            var cv = w.GetComponentData<Curve>(best).m_Bezier;
            return new RaycastHit { m_HitEntity = best, m_HitPosition = MathUtils.Position(cv, bt), m_CurvePosition = bt };
        }

        /// <summary>Every rule the plan breaks, in words (empty when clean). Delegates to Core's single source of truth.</summary>
        public static List<string> Violations(Planner.Preview pv, NetWorld w, bool allowDeadEnds = false, bool allowBelow = false) =>
            Planner.Audit(pv, w, allowDeadEnds, allowBelow);

        public static string Describe(List<string> v) { var sb = new StringBuilder(); foreach (var s in v) sb.AppendLine(" - " + s); return sb.ToString(); }
    }
}
