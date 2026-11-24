using System.Collections.Generic;
using Colossal.Mathematics;
using Unity.Mathematics;

namespace InterchangeStudio.Core
{
    public partial class Planner
    {
        // Recover the old recommendation idea using only the currently maintained recipes.
        // Prefer fewer removals, then avoid closely spaced diamond terminals, then road length.
        Preview BestFitPreview(List<Sep> list, float3 pos)
        {
            var nearest = Nearest(list, pos);
            if (WidthOf(nearest.S) < 16f)
                return FailFinal("Best fit: bridge only", "this local street is already grade-separated; no exit is needed");
            var diamond = ServicePreview(ToolMode.Exit, list, pos);
            var spui = ServicePreview(ToolMode.Spui, list, pos);
            bool d = diamond.Specs.Count > 0, s = spui.Specs.Count > 0;
            if (!d && !s)
            {
                var failure = Fail("Best fit found no layout", "Diamond: " + diamond.Status + " Single-point: " + spui.Status);
                failure.NoFit = diamond.NoFit && spui.NoFit;
                return failure;
            }
            int Removed(Preview p) => p.Specs.FindAll(x => x.Delete).Count;
            float Length(Preview p)
            {
                float n = 0; foreach (var spec in p.Specs) if (!spec.Delete) n += MathUtils.Length(spec.Curve);
                return n;
            }
            bool chooseSpui;
            string reason;
            if (!d || !s) { chooseSpui = s; reason = "the other style could not be planned with these settings"; }
            else if (Removed(diamond) != Removed(spui))
            { chooseSpui = Removed(spui) < Removed(diamond); reason = "it removes fewer existing road pieces"; }
            else if (diamond.TightGap > 0)
            { chooseSpui = true; reason = $"the diamond's junctions would be only {diamond.TightGap:0} m apart"; }
            else { chooseSpui = Length(spui) < Length(diamond); reason = "it uses less new or rebuilt road"; }
            var chosen = chooseSpui ? spui : diamond;
            chosen.Status = $"Best fit chose {(chooseSpui ? "Single-point" : "Diamond")}: {reason}. " + chosen.Status;
            chosen.Log = "Best fit: " + reason + ". " + chosen.Log;
            return chosen;
        }

        // The old automatic reversal hijacked ordinary construction modes. Repair is explicit,
        // and only a simple run bounded by opposing flows on BOTH ends can be reversed.
        Preview RepairPreview(Entity edge)
        {
            const string title = "Direction repair";
            if (!IsRoadEdge(edge) || !IsHighway(edge) || !IsOneway(edge))
                return FailFinal(title, "point at a one-way highway piece");
            var run = new List<Entity> { edge };
            bool Boundary(bool forward)
            {
                Entity current = edge;
                for (int guard = 0; guard < 100; guard++)
                {
                    var ed = EntityManager.GetComponentData<Edge>(current);
                    var curve = EntityManager.GetComponentData<Curve>(current).m_Bezier;
                    var node = forward ? ed.m_End : ed.m_Start;
                    var legs = EntityManager.GetBuffer<ConnectedEdge>(node, true);
                    // Junctions, merges, missing connections and dead ends are ambiguous.
                    if (legs.Length != 2) return false;
                    var next = legs[0].m_Edge == current ? legs[1].m_Edge : legs[0].m_Edge;
                    if (!IsRoadEdge(next) || !IsHighway(next) || !IsOneway(next) || PrefabOf(next) != PrefabOf(edge)) return false;
                    var ne = EntityManager.GetComponentData<Edge>(next);
                    var nc = EntityManager.GetComponentData<Curve>(next).m_Bezier;
                    float3 leaving = forward ? MathUtils.EndTangent(curve) : -MathUtils.StartTangent(curve);
                    float3 entering = ne.m_Start == node ? MathUtils.StartTangent(nc) : -MathUtils.EndTangent(nc);
                    if (math.dot(math.normalizesafe(leaving.xz), math.normalizesafe(entering.xz)) < 0.95f) return false;
                    if (forward ? ne.m_Start != node : ne.m_End != node) return true;
                    if (run.Contains(next)) return false;
                    run.Add(next); current = next;
                }
                return false;
            }
            bool a = Boundary(true), b = Boundary(false);
            float length = 0; foreach (var e in run) length += EntityManager.GetComponentData<Curve>(e).m_Length;
            if (!a || !b || length > 1000f)
                return FailFinal(title, "no unambiguous reversed run under 1 km was found; junctions and open ends are left alone");
            var pv = new Preview();
            foreach (var e in run)
            {
                var ed = EntityManager.GetComponentData<Edge>(e);
                var cv = EntityManager.GetComponentData<Curve>(e).m_Bezier;
                pv.Specs.Add(new Spec { Delete = true, Original = e });
                var spec = new Spec { Prefab = PrefabOf(e), Curve = MathUtils.Invert(cv), StartEntity = ed.m_End,
                    EndEntity = ed.m_Start, E0 = NodeElevation(ed.m_End), E1 = NodeElevation(ed.m_Start) };
                if (EntityManager.HasComponent<Upgraded>(e))
                {
                    spec.HasUpgrade = true;
                    var flags = EntityManager.GetComponentData<Upgraded>(e).m_Flags;
                    // Physical sides stay put when the direction of the curve reverses.
                    uint left = flags.m_Left; flags.m_Left = flags.m_Right; flags.m_Right = left;
                    spec.Upgrade = flags;
                }
                pv.Specs.Add(spec);
                string name = NameOf(e);
                if (!string.IsNullOrEmpty(name)) pv.Names.Add((MathUtils.Position(cv, 0.5f), name, true));
            }
            pv.Status = $"Direction repair: reverse {run.Count} highway pieces ({length:0} m) to match traffic at both ends. Check the preview, then click to build.";
            pv.Log = pv.Status;
            return pv;
        }
    }
}
