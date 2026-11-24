// Interchange Studio - Testing/PlanSvg.cs
// Draws a plan over its synthetic city as an SVG: existing roads in grey, roads the plan removes in
// dashed red, new pieces coloured by height (ground teal -> high amber), joins as dots. The tests write
// one per scenario plus an index page, so every style can be looked at without the game.
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using Colossal.Mathematics;
using InterchangeStudio.Core;
using Unity.Mathematics;

namespace InterchangeStudio.Testing
{
    public static class PlanSvg
    {
        static string F(float v) => v.ToString("0.#", CultureInfo.InvariantCulture);

        public static string Render(NetWorld w, Planner.Preview pv, string title, string status)
        {
            var deleted = new HashSet<Entity>();
            var box = new List<float2>();
            if (pv != null)
                foreach (var s in pv.Specs)
                {
                    if (s.Delete) { deleted.Add(s.Original); continue; }
                    box.Add(s.Curve.a.xz); box.Add(s.Curve.d.xz);
                }
            if (box.Count == 0) box.Add(float2.zero);
            float2 lo = box[0], hi = box[0];
            foreach (var p in box) { lo = math.min(lo, p); hi = math.max(hi, p); }
            float2 c = (lo + hi) * 0.5f; float half = math.max(260f, math.cmax(hi - lo) * 0.5f + 120f);
            lo = c - half; hi = c + half;
            float size = hi.x - lo.x;
            string Pt(float3 p) => F(p.x - lo.x) + "," + F(hi.y - p.z);       // north up
            string PathOf(Bezier4x3 b) => $"M{Pt(b.a)} C{Pt(b.b)} {Pt(b.c)} {Pt(b.d)}";

            var sb = new StringBuilder();
            sb.Append($"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {F(size)} {F(size)}' width='520' height='520' style='background:#1d2731'>");
            // existing network
            foreach (var list in new[] { w.TrackEdges, w.RoadEdges })
                foreach (var e in list)
                {
                    var cv = w.GetComponentData<Curve>(e).m_Bezier;
                    if (math.all(math.max(math.max(cv.a.xz, cv.d.xz), math.max(cv.b.xz, cv.c.xz)) < lo) || math.all(math.min(math.min(cv.a.xz, cv.d.xz), math.min(cv.b.xz, cv.c.xz)) > hi)) continue;
                    float width = w.GetComponentData<NetGeometryData>(w.GetComponentData<PrefabRef>(e).m_Prefab).m_DefaultWidth;
                    bool track = list == w.TrackEdges;
                    string col = deleted.Contains(e) ? "#d9534f" : track ? "#8a6d4b" : "#5b6875";
                    string dash = deleted.Contains(e) ? " stroke-dasharray='8 6' opacity='0.8'" : "";
                    sb.Append($"<path d='{PathOf(cv)}' stroke='{col}' stroke-width='{F(deleted.Contains(e) ? 3 : width * 0.9f)}' fill='none' stroke-linecap='round'{dash}/>");
                }
            // the plan, lowest first so flyovers draw on top
            if (pv != null)
            {
                var courses = new List<Planner.Spec>();
                foreach (var s in pv.Specs) if (!s.Delete) courses.Add(s);
                courses.Sort((a, b) => (a.E0 + a.E1).CompareTo(b.E0 + b.E1));
                foreach (var s in courses)
                {
                    float e = (s.E0 + s.E1) * 0.5f;
                    float k = math.saturate(e / 20f);
                    string col = $"rgb({(int)math.lerp(70, 244, k)},{(int)math.lerp(200, 162, k)},{(int)math.lerp(190, 89, k)})";
                    float width = w.GetComponentData<NetGeometryData>(s.Prefab).m_DefaultWidth;
                    sb.Append($"<path d='{PathOf(s.Curve)}' stroke='#11181f' stroke-width='{F(width + 3)}' fill='none'/>");
                    sb.Append($"<path d='{PathOf(s.Curve)}' stroke='{col}' stroke-width='{F(width * 0.8f)}' fill='none' stroke-linecap='round'/>");
                }
                foreach (var s in courses) foreach (var p in new[] { s.Curve.a, s.Curve.d }) sb.Append($"<circle cx='{Pt(p).Split(',')[0]}' cy='{Pt(p).Split(',')[1]}' r='2.2' fill='#e8edf2'/>");
            }
            sb.Append($"<text x='12' y='28' fill='#f4a259' font-family='Segoe UI,sans-serif' font-size='{F(size / 26f)}'>{System.Security.SecurityElement.Escape(title)}</text>");
            sb.Append("</svg>");
            return sb.ToString();
        }

        /// <summary>Collects rendered plans and writes an index page next to them.</summary>
        public sealed class Sheet
        {
            readonly string m_Dir;
            readonly List<(string name, string title, string status, int violations)> m_Items = new List<(string, string, string, int)>();
            public Sheet(string dir) { m_Dir = dir; Directory.CreateDirectory(dir); }

            public void Add(string name, string title, NetWorld w, Planner.Preview pv, string status, int violations)
            {
                File.WriteAllText(Path.Combine(m_Dir, name + ".svg"), Render(w, pv, title, status));
                m_Items.Add((name, title, status, violations));
                Write();
            }

            void Write()
            {
                var sb = new StringBuilder("<!doctype html><meta charset='utf-8'><title>Interchange Studio review sheet</title><body style='background:#121a21;color:#dde5ec;font-family:Segoe UI,sans-serif;margin:24px'><h1 style='color:#f4a259;font-weight:600'>Interchange Studio: review sheet</h1><p style='opacity:.7'>Every style, planned offline against synthetic cities. Grey: existing roads. Dashed red: removed. New pieces: teal at ground to amber when raised.</p><div style='display:flex;flex-wrap:wrap;gap:18px'>");
                foreach (var it in m_Items)
                    sb.Append($"<figure style='margin:0;width:520px'><img src='{it.name}.svg' width='520' height='520' style='border-radius:10px'><figcaption style='font-size:13px;margin-top:6px'><b>{System.Security.SecurityElement.Escape(it.title)}</b> {(it.violations == 0 ? "<span style='color:#6fcf8a'>clean</span>" : $"<span style='color:#f4a259'>{it.violations} rule problem(s)</span>")}<br><span style='opacity:.65'>{System.Security.SecurityElement.Escape(it.status ?? "")}</span></figcaption></figure>");
                sb.Append("</div></body>");
                File.WriteAllText(Path.Combine(m_Dir, "index.html"), sb.ToString());
            }
        }
    }
}
