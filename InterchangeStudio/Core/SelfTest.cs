// Interchange Studio - Core/SelfTest.cs
// The self-test (2026-10-23): on the player's own city, try each tool at a set of test spots and let the
// game judge every preview (what it shows in red), then write a report. Preview only: it never builds.
// The adapter feeds it the game's red each frame; offline, the tests feed it none.
using System;
using System.Collections.Generic;
using System.Text;
using Colossal.Mathematics;
using Unity.Mathematics;

namespace InterchangeStudio.Core
{
    public partial class Planner
    {
        public struct TestSpot { public string Kind, Where; public RaycastHit Hit; public bool RailOnly; public bool EndingOnly; public bool Separated; }

        /// <summary>Spots worth testing on this map, spread out: separated crossings (ramps), ground-level crossings, railway crossings, highway dead ends, bare highway, avenues away from highways.</summary>
        public List<TestSpot> SelfTestSpots(int perKind = 4)
        {
            var spots = new List<TestSpot>();
            var taken = new List<float3>();
            bool Far(float3 p, float d) { foreach (var q in taken) if (math.distance(q.xz, p.xz) < d) return false; return true; }
            RaycastHit On(Entity e, float t) => new RaycastHit { m_HitEntity = e, m_CurvePosition = t, m_HitPosition = MathUtils.Position(EntityManager.GetComponentData<Curve>(e).m_Bezier, t) };
            var edges = new List<Entity>();
            using (var ents = m_RoadEdges.ToEntityArray(Allocator.Temp)) foreach (var e in ents) if (Live(e)) edges.Add(e);
            // the same spots every run on the same city (the game hands the pieces over in no fixed order)
            edges.Sort((x, y) => { var a = MathUtils.Position(EntityManager.GetComponentData<Curve>(x).m_Bezier, 0.5f); var b = MathUtils.Position(EntityManager.GetComponentData<Curve>(y).m_Bezier, 0.5f); int c = a.x.CompareTo(b.x); return c != 0 ? c : a.z.CompareTo(b.z); });
            int grade = 0, rail = 0, sep = 0, ending = 0, bare = 0, ave = 0;
            var seenNodes = new HashSet<Entity>();
            foreach (var e in edges)
            {
                var ed = EntityManager.GetComponentData<Edge>(e);
                foreach (var (n, t) in new[] { (ed.m_Start, 0.08f), (ed.m_End, 0.92f) })
                {
                    if (!seenNodes.Add(n) || !Live(n)) continue;
                    float3 p = NodePos(n);
                    if (rail < 2 && RailCount(n) > 0 && Far(p, 600f)) { spots.Add(new TestSpot { Kind = "railway crossing", Where = Where(p), Hit = On(e, t), RailOnly = true }); taken.Add(p); rail++; }
                    else if (grade < perKind && IsHighway(e) && IsCrossing(n) && !IsTerminal(n) && Far(p, 600f)) { spots.Add(new TestSpot { Kind = "ground-level crossing", Where = Where(p), Hit = On(e, t) }); taken.Add(p); grade++; }
                }
            }
            foreach (var e in edges)
            {
                var c = EntityManager.GetComponentData<Curve>(e);
                if (c.m_Length < 40f) continue;
                float3 p = MathUtils.Position(c.m_Bezier, 0.5f);
                if (!Far(p, 600f)) continue;
                var ed2 = EntityManager.GetComponentData<Edge>(e);
                bool raised = IsRaised(ed2.m_Start) || IsRaised(ed2.m_End);
                if (sep < perKind && IsHighway(e) && IsOneway(e))
                {
                    var seps = FindSeparated(p, true);
                    if (seps.Count > 0)
                    {
                        float3 sp = Nearest(seps, p).P;
                        if (Far(sp, 600f))
                        {
                            spots.Add(new TestSpot { Kind = "separated crossing", Where = Where(sp), Hit = On(e, 0.5f), Separated = true });
                            taken.Add(sp); sep++; continue;
                        }
                    }
                }
                if (!Far(p, 900f)) continue;
                if (bare < perKind && IsHighway(e) && IsOneway(e) && !raised && FindSeparated(p, true).Count == 0 && NoCrossingNear(p, 450f))
                { spots.Add(new TestSpot { Kind = "bare highway", Where = Where(p), Hit = On(e, 0.5f) }); taken.Add(p); bare++; }
                else if (ave < perKind - 1 && !IsHighway(e) && WidthOf(e) >= 20f && !IsOneway(e) && NoHighwayNear(p, 700f))
                { spots.Add(new TestSpot { Kind = $"street with no highway ({NameOf(e) ?? m_PrefabSystem.GetPrefabName(PrefabOf(e))})", Where = Where(p), Hit = On(e, 0.5f) }); taken.Add(p); ave++; }
            }
            // pick highway dead-end spots last so they don't crowd out bare-highway stretches on the same corridor
            var endingTaken = new List<float3>();
            seenNodes.Clear();
            foreach (var e in edges)
            {
                if (ending >= 2) break;
                if (!IsHighway(e) || !IsOneway(e)) continue;
                var ed = EntityManager.GetComponentData<Edge>(e);
                foreach (var (n, t) in new[] { (ed.m_Start, 0.08f), (ed.m_End, 0.92f) })
                {
                    if (ending >= 2 || !seenNodes.Add(n) || !Live(n)) continue;
                    float3 p = NodePos(n);
                    bool farEnd = true;
                    foreach (var q in endingTaken) if (math.distance(q.xz, p.xz) < 600f) { farEnd = false; break; }
                    if (!farEnd) continue;
                    if (TryDeadEnd(n, e, out var de) && FindPartnerDeadEnd(de, out _))
                    { spots.Add(new TestSpot { Kind = "highway dead end", Where = Where(p), Hit = On(e, t), EndingOnly = true }); endingTaken.Add(p); ending++; }
                }
            }
            m_SepKey = NoSepKey;
            return spots;
        }

        public static string StyleNameOf(ToolMode m) => m == ToolMode.Overpass ? "overpass"
            : m == ToolMode.Spui ? "SPUI"
            : m == ToolMode.Exit ? "diamond"
            : m == ToolMode.Auto ? "best fit"
            : m == ToolMode.Dumbbell ? "dumbbell"
            : m == ToolMode.Frontage ? "frontage"
            : m == ToolMode.Ending ? "highway end"
            : m == ToolMode.Repair ? "repair"
            : m.ToString();

        static string Where(float3 p) => $"({(int)p.x}, {(int)p.z})";

        bool NoCrossingNear(float3 p, float r)
        {
            foreach (var e in RoadsNear(p.xz - r, p.xz + r))
                if (Live(e) && !IsHighway(e) && MathUtils.Distance(EntityManager.GetComponentData<Curve>(e).m_Bezier.xz, p.xz, out float _) < r) return false;
            return true;
        }

        bool NoHighwayNear(float3 p, float r)
        {
            foreach (var e in RoadsNear(p.xz - r, p.xz + r))
                if (IsHighway(e) && MathUtils.Distance(EntityManager.GetComponentData<Curve>(e).m_Bezier.xz, p.xz, out float _) < r) return false;
            return true;
        }
    }

    /// <summary>Steps through spot x style, a fixed number of frames each, and records how each preview fared.</summary>
    public sealed class SelfTestRun
    {
        public const int FramesPerCase = 50;
        static readonly Planner.ToolMode[] BasicStyles = { Planner.ToolMode.Overpass, Planner.ToolMode.Exit, Planner.ToolMode.Spui };
        static readonly Planner.ToolMode[] RampStyles = { Planner.ToolMode.Exit, Planner.ToolMode.Spui, Planner.ToolMode.Dumbbell, Planner.ToolMode.Frontage, Planner.ToolMode.Auto };

        readonly Planner m_P;
        readonly PlanConfig m_Saved;
        readonly List<(Planner.TestSpot spot, Planner.ToolMode style)> m_Cases = new List<(Planner.TestSpot, Planner.ToolMode)>();
        readonly List<string> m_Lines = new List<string>();
        int m_Case = -1, m_Frame;
        bool m_Planned; int m_RedNow; string m_Status = "";
        readonly List<string> m_RedWhat = new List<string>();
        readonly Dictionary<string, int> m_Reasons = new Dictionary<string, int>();
        int m_Ok, m_Partial, m_Red, m_None;
        public DateTime Started = DateTime.Now;

        public SelfTestRun(Planner p, int perKind = 4)
        {
            m_P = p; m_Saved = p.Cfg;
            foreach (var s in p.SelfTestSpots(perKind))
            {
                if (s.RailOnly) { m_Cases.Add((s, Planner.ToolMode.Overpass)); continue; }
                if (s.EndingOnly) { m_Cases.Add((s, Planner.ToolMode.Ending)); continue; }
                foreach (var st in s.Separated ? RampStyles : BasicStyles) m_Cases.Add((s, st));
            }
            Advance();
        }

        public bool Done => m_Case >= m_Cases.Count;
        public int Count => m_Cases.Count;
        public int Index => m_Case;
        public float3 Focus => Done ? default : m_Cases[m_Case].spot.Hit.m_HitPosition;

        /// <summary>What the planner gets this frame: the test spot under the "cursor", the game's red, no clicks.</summary>
        public FrameInput Input(List<RedItem> red, bool allowApply)
        {
            var i = new FrameInput { HasHit = true, Hit = m_Cases[m_Case].spot.Hit, AllowApply = allowApply };
            if (red != null) i.Red.AddRange(red);
            m_RedNow = red?.Count ?? 0;
            m_RedWhat.Clear(); if (red != null) foreach (var r in red) if (!m_RedWhat.Contains(r.What)) m_RedWhat.Add(r.What);
            return i;
        }

        /// <summary>After the planner's frame: note the outcome; after FramesPerCase, record it and move on.</summary>
        public void Observe(FrameOutput o)
        {
            m_Planned = o.Emit != null && o.Emit.Specs.Exists(s => !s.Delete);
            m_Status = m_P.StatusText ?? "";
            if (++m_Frame < FramesPerCase) return;
            var (spot, style) = m_Cases[m_Case];
            string verdict = !m_Planned ? "NOT PLANNED" : m_RedNow > 0 ? "RED" : m_Status.Contains("ramps fit") ? "PARTIAL" : "OK";
            if (verdict == "OK") m_Ok++; else if (verdict == "PARTIAL") m_Partial++; else if (verdict == "RED") m_Red++; else m_None++;
            m_Lines.Add($"{verdict,-12} {Planner.StyleNameOf(style),-12} {spot.Kind} at {spot.Where}: {m_Status}");
            if (verdict == "RED")
            {
                m_Lines.Add("             red: " + string.Join("; ", m_RedWhat.GetRange(0, Math.Min(6, m_RedWhat.Count))));
                foreach (var w in m_RedWhat)
                {
                    int i = w.IndexOf(" ("); string why = i >= 0 ? w.Substring(i + 2).TrimEnd(')') : "reason not recorded";
                    m_Reasons[why] = (m_Reasons.TryGetValue(why, out int n) ? n : 0) + 1;
                }
            }
            Advance();
        }

        void Advance()
        {
            m_Case++; m_Frame = 0; m_Planned = false; m_RedNow = 0;
            if (Done) { m_P.Cfg = m_Saved; m_P.Reset(); return; }
            m_P.Cfg = m_Saved with { Mode = m_Cases[m_Case].style, Autofit = true, KeepElevated = false, Dig = false };
            m_P.Reset();
        }

        /// <summary>Stop early (the player took over): put the settings back.</summary>
        public void Abort() { if (!Done) { m_Lines.Add($"(stopped by the player after {m_Case} of {m_Cases.Count} cases)"); m_Case = m_Cases.Count; m_P.Cfg = m_Saved; m_P.Reset(); } }

        public string Report()
        {
            var sb = new StringBuilder();
            sb.AppendLine($"Interchange Studio self-test, {Started:yyyy-MM-dd HH:mm} to {DateTime.Now:HH:mm}");
            sb.AppendLine("Preview only: nothing was built. Each case: the tool pointed at the spot for " + FramesPerCase + " frames and the game judged the preview.");
            sb.AppendLine($"{m_Cases.Count} cases: {m_Ok} clean, {m_Partial} built partly (ramps left out), {m_Red} still red, {m_None} not planned.");
            if (m_Reasons.Count > 0)
            {
                sb.Append("Why the red pieces were red: ");
                var parts = new List<string>(); foreach (var kv in m_Reasons) parts.Add($"{kv.Key} ({kv.Value})");
                sb.AppendLine(string.Join(", ", parts));
            }
            sb.AppendLine("OK = clean preview; PARTIAL = clean after leaving ramps out; RED = the game still shows red; NOT PLANNED = the tool explained why not.");
            sb.AppendLine();
            foreach (var l in m_Lines) sb.AppendLine(l);
            return sb.ToString();
        }
    }
}
