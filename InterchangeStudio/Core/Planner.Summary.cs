// Interchange Studio - Core/Planner.Summary.cs
// One line under the status: what a click would build, in numbers (an idea from GPT's review of the old mod,
// 2026-10-30). Geometry only: road length and pieces, not cost or traffic.
using Colossal.Mathematics;
using Unity.Mathematics;

namespace InterchangeStudio.Core
{
    public partial class Planner
    {
        /// <summary>The summary of the preview being shown ("" when there is none).</summary>
        public string PreviewSummary { get; private set; } = "";
        Preview m_SummaryOf, m_LastSummaryOf; string m_LastSummary = "";

        void NoteSummary(Preview shown)
        {
            if (shown == null) { PreviewSummary = ""; m_SummaryOf = null; m_LastSummaryOf = null; return; }
            m_SummaryOf = shown;
            if (ReferenceEquals(shown, m_LastSummaryOf)) { PreviewSummary = m_LastSummary; return; }
            m_LastSummaryOf = shown; m_LastSummary = PreviewSummary = Summarize(shown);
        }

        public static string Summarize(Preview pv)
        {
            int pieces = 0, replaced = 0; float length = 0, raised = 0, sunk = 0;
            foreach (var s in pv.Specs)
            {
                if (s.Delete) { replaced++; continue; }
                pieces++;
                float l = MathUtils.Length(s.Curve);
                length += l;
                if (math.max(s.E0, s.E1) > 2f) raised += l;
                if (math.min(s.E0, s.E1) < -2f) sunk += l;
            }
            if (pieces == 0) return "";
            string Km(float m) => m >= 1000f ? $"{m / 1000f:0.0} km" : $"{math.round(m / 10f) * 10f:0} m";
            string text = $"New road: {Km(length)} in {pieces} piece{(pieces == 1 ? "" : "s")}";
            if (raised > 1f) text += $", {Km(raised)} of it raised";
            if (sunk > 1f) text += $", {Km(sunk)} of it in a cutting";
            if (replaced > 0) text += $" \u00b7 {replaced} existing piece{(replaced == 1 ? "" : "s")} replaced";
            if (pv.NextStep) text += " \u00b7 bridge first; the ramps follow automatically";
            return text;
        }
    }
}
