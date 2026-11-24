// Interchange Studio - Core/Planner.Trim.cs
// "Keep what the game accepts": every ramp in a plan is its own group, so when the game shows red on some
// ramps (a real collision: the cosmetic checks are switched off by the adapter) the tool can drop just
// those and offer the rest, instead of nothing. Autofit gets its turn first; if no layout is completely
// clear, the layout with the fewest red ramps is trimmed. Red on group 0 (the bridge, street changes,
// the street's own pieces) can't be trimmed away.
using System.Collections.Generic;
using Colossal.Mathematics;
using Unity.Mathematics;

namespace InterchangeStudio.Core
{
    public partial class Planner
    {
        int m_Group;                                                  // the group new pieces are written into (0 = core)
        bool m_Trim;                                                  // autofit is done; dropping red ramps now
        readonly HashSet<int> m_Drop = new HashSet<int>();            // ramp groups left out of this crossing's preview
        readonly Dictionary<int, int> m_FitScore = new Dictionary<int, int>();  // layout -> red ramps (core clear)
        Preview m_Shown;                                              // what was emitted last (the plan less dropped ramps)

        /// <summary>Start writing a ramp: its pieces form one group that can be left out on its own.</summary>
        int BeginRamp(Preview pv, string name) { pv.GroupNames.Add(name); return m_Group = pv.GroupNames.Count - 1; }
        void EndRamp() => m_Group = 0;

        /// <summary>A new crossing (or a build): forget the drops and layout scores.</summary>
        void ResetTrim() { m_Trim = false; m_Drop.Clear(); m_FitScore.Clear(); }

        void ResetRedWait() { m_KeyAge = 0; m_BlockKey = ""; }

        /// <summary>The plan without the dropped ramps, re-joined, with anything left dangling by them removed too.</summary>
        public static Preview Trimmed(Preview pv, ICollection<int> drop)
        {
            var t = new Preview
            {
                Status = pv.Status, Log = pv.Log, NextStep = pv.NextStep, NextPos = pv.NextPos, NextMode = pv.NextMode,
                TightGap = pv.TightGap, NoFit = pv.NoFit, Names = pv.Names, GroupNames = pv.GroupNames,
            };
            foreach (var s in pv.Specs)
                if (s.Delete || !drop.Contains(s.Group)) { var c = s.Clone(); c.JoinStart = c.JoinEnd = false; t.Specs.Add(c); }
            // free ends that met another piece in the full plan must still meet one; else that piece goes too (repeat)
            var met = FreeEndCounts(pv.Specs);
            for (bool changed = true; changed;)
            {
                changed = false;
                var now = FreeEndCounts(t.Specs);
                for (int i = t.Specs.Count - 1; i >= 0; i--)
                {
                    var s = t.Specs[i];
                    if (s.Delete || !Dangles(s, met, now)) continue;
                    t.Specs.RemoveAt(i); changed = true;
                }
            }
            JoinPieces(t);
            int total = pv.GroupNames.Count - 1, left = 0;
            var names = new List<string>();
            for (int g = 1; g <= total; g++)
            {
                bool kept = t.Specs.Exists(s => !s.Delete && s.Group == g);
                if (kept) left++; else names.Add(pv.GroupNames[g]);
            }
            string list = names.Count <= 2 ? string.Join(" and ", names) : string.Join(", ", names.GetRange(0, names.Count - 1)) + " and " + names[names.Count - 1];
            t.Status = left == 0
                ? $"None of the ramps fit here: each one runs into something (shown in red before). Try another size, or clear the way."
                : $"{pv.Status} Only {left} of {total} ramps fit: {list} {(names.Count == 1 ? "runs" : "run")} into something and {(names.Count == 1 ? "is" : "are")} left out. Click to build the rest; add the missing ramps by hand.";
            t.Log = pv.Log + $" (left out: {list})";
            return t;
        }

        static bool Dangles(Spec s, Dictionary<float3, int> met, Dictionary<float3, int> now)
        {
            if (s.StartEntity == Entity.Null && met.TryGetValue(s.Curve.a, out int a) && a > 1 && now[s.Curve.a] < 2) return true;
            if (s.EndEntity == Entity.Null && met.TryGetValue(s.Curve.d, out int d) && d > 1 && now[s.Curve.d] < 2) return true;
            return false;
        }

        static Dictionary<float3, int> FreeEndCounts(List<Spec> specs)
        {
            var n = new Dictionary<float3, int>();
            foreach (var s in specs)
            {
                if (s.Delete) continue;
                if (s.StartEntity == Entity.Null) n[s.Curve.a] = (n.TryGetValue(s.Curve.a, out int x) ? x : 0) + 1;
                if (s.EndEntity == Entity.Null) n[s.Curve.d] = (n.TryGetValue(s.Curve.d, out int y) ? y : 0) + 1;
            }
            return n;
        }

        /// <summary>Which ramp groups the game's red falls on; core = red on something that can't be left out.</summary>
        HashSet<int> RedGroups(out bool core)
        {
            core = false;
            var hit = new HashSet<int>();
            var shown = m_Shown ?? m_Preview;
            foreach (var r in m_In.Red)
            {
                if (!NearPreview(r.At)) continue;
                Spec best = null; float bd = 30f;
                foreach (var s in shown.Specs)
                {
                    if (s.Delete) continue;
                    float d = MathUtils.Distance(s.Curve.xz, r.At.xz, out float _);
                    if (d < bd) { bd = d; best = s; }
                }
                if (best == null || best.Group == 0) core = true; else hit.Add(best.Group);
            }
            return hit;
        }

        /// <summary>
        /// The game shows red on this preview: try the next autofit layout, or (autofit done) go back to the
        /// layout with the fewest red ramps and leave those ramps out. False when nothing more can be done.
        /// </summary>
        bool OnRed()
        {
            var hit = RedGroups(out bool core);
            if (!m_Trim)
            {
                if (!core) m_FitScore[m_FitVariant] = hit.Count;
                if (AutofitActive() && m_FitVariant + 1 < ActiveFits.Length)
                {
                    Say($"Autofit: layout {m_FitVariant + 1} doesn't fit cleanly, trying another...");
                    FitNext();
                    return true;
                }
                if (m_FitScore.Count == 0) return false;          // the core collides in every layout
                int best = -1;
                foreach (var kv in m_FitScore) if (best < 0 || kv.Value < m_FitScore[best] || kv.Value == m_FitScore[best] && kv.Key < best) best = kv.Key;
                m_Trim = true; m_Drop.Clear();
                if (best != m_FitVariant)
                {
                    m_FitVariant = best; m_PreviewKey = ""; m_HoverKey = "";
                    SafeLog($"Trimming: back to layout {best + 1}, the one with the fewest red ramps");
                    Say("Leaving out the ramps that don't fit...");
                    ResetRedWait();
                    return true;
                }
            }
            if (core || hit.Count == 0) return false;
            m_Drop.UnionWith(hit);
            var names = new List<string>(); foreach (int g in hit) names.Add(m_Preview.GroupNames[g]);
            SafeLog("Leaving out " + string.Join(", ", names) + " (red in the game)");
            Say("Leaving out the ramps that don't fit...");
            ResetRedWait();
            return true;
        }
    }
}
