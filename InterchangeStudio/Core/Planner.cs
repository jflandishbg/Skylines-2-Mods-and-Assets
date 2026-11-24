// Ported from ClaudeInterchanges (OverpassToolSystem) by Build/port.py, then kept by hand.
// Pure planning code: it reads the road network through the NetWorld look-alike (Core/Ecs.cs) and never
// touches the game. Settings come from the immutable PlanConfig (Core/Config.cs).
using System.Collections.Generic;
using Colossal.Mathematics;
using Unity.Mathematics;

namespace InterchangeStudio.Core
{
    /// <summary>
    /// The interchange tool. Hover where a highway meets a street.
    ///
    ///   Overpass: grade-separate the crossing. By default the STREET is lifted over the highway, so the
    ///             highway itself is left exactly as it was; "highway over street" is the alternative.
    ///   Diamond:  ramps from the highway to the cross street, one pair per carriageway, meeting the
    ///             street at a junction (on its bridge if the street goes over). The highway is not
    ///             rebuilt: the ramps join it the way a player-drawn ramp does.
    ///   Single-point (SPUI): the same four ramps meeting the street at one junction in the middle.
    ///
    /// Also: a bare highway gets a new cross street; streets drawn up to a highway get joined across it;
    /// a street with no highway gets a new highway over it (Planner.NewStreet / Stubs / NewHighway).
    ///
    /// Railway level crossings: the road (street or highway) always goes over the tracks; the railway is
    /// never moved, since rail came first here.
    ///
    /// Anything that has to be rebuilt keeps its road type, its upgrades and (after the build) its name,
    /// and every rebuilt piece runs the way its traffic ran before. A crossing still at ground level
    /// that needs ramps is done in two automatic steps: bridge first, ramps once the game has tidied up.
    /// </summary>
    public partial class Planner
    {
        // Saved IDs stay stable. Auto (5) restored 2026-10-31; Ending (6) added 2026-11-22; Repair gets ID (9).
        public enum ToolMode { Overpass = 0, Exit = 1, Frontage = 2, Spui = 3, Dumbbell = 4, Auto = 5, Ending = 6, Repair = 9 }

        // panel settings: read-only views of Cfg (Core/Config.cs)

        const float MaxGrade = 0.09f;            // steepest bridge ramp we accept when room is short
        const float MaxSpan = 2500f;
        const float SnapToNode = 4f;
        const float MaxPiece = 80f;              // longest new road piece
        const float TightDiamond = 160f;         // diamond junctions closer than this make traffic stop twice

        public string StatusText { get; set; } = "";
        public int StatusKind { get; set; }      // 0 hint, 1 ready to build, 2 problem, 3 just built

        private TerrainSystem m_TerrainSystem;
        private PrefabSystem m_PrefabSystem;
        private NameSystem m_NameSystem;
        private EntityQuery m_RoadPrefabs, m_RoadEdges, m_TrackEdges;
        private Entity m_Ramp1 = Entity.Null, m_Ramp2 = Entity.Null;

        private bool m_HasPreview, m_AutoApply;
        private Preview m_Preview;
        private string m_PreviewKey = "", m_LastStatus = "", m_LastLogged = "";
        private int m_HoldStatus, m_Pending, m_RenameFrames;
        private float3 m_PendingPos;
        private ToolMode m_PendingMode;
        private int m_PendingFit;
        private List<(float3 pos, string name, bool highway)> m_Renames = new List<(float3, string, bool)>();






        void Say(string s) { if (m_HoldStatus <= 0) StatusText = s; }
        void Status(string s) { if (s == m_LastStatus) return; m_LastStatus = s; Log.Info("  " + s); }
        void LogOnce(string s) { if (s == m_LastLogged) return; m_LastLogged = s; SafeLog(s); }
        void SafeLog(string s)
        {
            if (s == null) return;
            s = s.Replace("{", "(").Replace("}", ")");
            if (s.Length > 1500) s = s.Substring(0, 1500) + "...";
            try { Log.Info(s); } catch { }
        }

        /* ================= the frame ================= */



        void Built() { ResetTrim(); m_FitBase = ""; m_GridDirty = true; m_HoverKey = ""; m_HasPreview = false; m_PreviewKey = ""; m_SepKey = NoSepKey; m_LastStatus = ""; m_HoldStatus = 90; }

        /* ================= what's under the cursor ================= */

        /*
         * What's under the cursor is only worked out again when the cursor has moved a few metres (or every
         * half second): at a finished interchange there are dozens of road pieces to look through, and
         * doing that every frame made the game stutter.
         */
        private string m_HoverKey = ""; private int m_HoverAge; private Preview m_HoverPv;

        Preview HoverPreview()
        {
            if (!GetRaycastResult(out Entity hitEntity, out RaycastHit hit))
            {
                m_HoverKey = "";
                Status("nothing under the cursor");
                Say("Point at a road.");
                return null;
            }
            float3 hp = hit.m_HitPosition;
            string hkey = $"{hitEntity.Index}|{(int)math.floor(hp.x / 5f)}|{(int)math.floor(hp.z / 5f)}|{m_FitVariant}|{Cfg.CacheKey()}";
            if (hkey == m_HoverKey && m_HoverAge++ < 30 && (m_HoverPv == null || StillValid(m_HoverPv)))
            {
                if (m_HoverPv != null) m_KeyAge++;
                return m_HoverPv;
            }
            m_HoverKey = hkey; m_HoverAge = 0;
            m_HoverPv = HoverWork(hitEntity, hit);
            return m_HoverPv;
        }

        Preview HoverWork(Entity hitEntity, RaycastHit hit)
        {
            float3 pos = hit.m_HitPosition;
            m_HoverPos = pos;
            if (Mode == ToolMode.Repair)
                return Cached($"repair|{hitEntity.Index}.{hitEntity.Version}", () => RepairPreview(hitEntity));
            string settings = Cfg.CacheKey();
            if (Mode == ToolMode.Ending)
                return Cached(FitKey($"end|{hitEntity.Index}.{hitEntity.Version}|{settings}"), () => EndingPreview(hitEntity, hit));
            Entity crossing = FindCrossing(hitEntity, pos);
            // a road crossing a railway at ground level: the railway was here first, so the road goes over
            Entity rail = FindRailCrossing(hitEntity, pos);
            if (rail != Entity.Null && (crossing == Entity.Null || math.distance(NodePos(rail).xz, pos.xz) < math.distance(NodePos(crossing).xz, pos.xz)))
            {
                Status("hovering " + Describe(hitEntity) + ", railway level crossing");
                return Cached(FitKey($"rail{rail.Index}.{rail.Version}|{Clearance}|{Grade}|{BothCarriageways}"), () => RailPreview(rail));
            }
            if (crossing != Entity.Null)
            {
                Status("hovering " + Describe(hitEntity) + ", at-grade crossing");
                return Cached(FitKey($"grade{crossing.Index}.{crossing.Version}|{settings}"), () => AtGradePreview(crossing));
            }
            var sep = FindSeparated(pos, false);
            if (sep.Count > 0)
            {
                Status("hovering " + Describe(hitEntity) + $", {sep.Count} grade-separated crossing(s) nearby");
                if (Mode == ToolMode.Overpass) { Say("This crossing already has a bridge. Switch to Diamond or Single-point to add ramps."); return null; }
                // one key for the whole crossing (both carriageways), so autofit keeps its place while the cursor moves between them
                var ids = new List<int>(); foreach (var x in sep) { ids.Add(x.H.Index); ids.Add(x.S.Index); }
                ids.Sort();
                return Cached(FitKey($"sep{string.Join(".", ids)}|{settings}"), () => PreviewFor(Mode, sep, pos));
            }
            if (IsHighway(hitEntity) && FindStubPair(hitEntity, hit, out var sa, out var sb))
            {
                // streets drawn up to the highway from both sides: join them across it (Planner.Stubs.cs)
                Status("hovering " + Describe(hitEntity) + ", street ends on both sides");
                return Cached(FitKey($"stub{sa.Node.Index}.{sb.Node.Index}|{settings}"), () => StubBridgePreview(hitEntity, sa, sb));
            }
            if (IsHighway(hitEntity))
            {
                // a bare stretch of highway: offer a new cross street over it (Planner.NewStreet.cs)
                Status("hovering " + Describe(hitEntity) + ", bare highway");
                int cell = (int)math.floor(hit.m_CurvePosition * EntityManager.GetComponentData<Curve>(hitEntity).m_Length / 10f);
                return Cached(FitKey($"new{hitEntity.Index}.{cell}|{NewStreet}|{settings}"), () => NewStreetPreview(hitEntity, hit));
            }
            if (!IsHighway(hitEntity) && FindStubToward(hitEntity, pos, out var st, out var hw, out var hwHit))
            {
                // the reverse: point at the street; it is joined to its other half, or carried on, across the highway
                if (FindStubPair(hw, hwHit, out var pa, out var pb) && (pa.Node == st.Node || pb.Node == st.Node))
                {
                    Status("hovering " + Describe(hitEntity) + ", street ends on both sides of a highway");
                    return Cached(FitKey($"stub{pa.Node.Index}.{pb.Node.Index}|{settings}"), () => StubBridgePreview(hw, pa, pb));
                }
                Status("hovering " + Describe(hitEntity) + ", street ending at a highway");
                return Cached(FitKey($"stub1.{st.Node.Index}|{settings}"), () => StubBridgePreview(hw, st, default, false));
            }
            if (!IsHighway(hitEntity) && IsRoadEdge(hitEntity))
            {
                // the reverse: a street with no highway here; offer a highway over it (Planner.NewHighway.cs)
                Status("hovering " + Describe(hitEntity) + ", street with no highway");
                int cell = (int)math.floor(hit.m_CurvePosition * EntityManager.GetComponentData<Curve>(hitEntity).m_Length / 10f);
                return Cached(FitKey($"newhw{hitEntity.Index}.{cell}|{settings}"), () => NewHighwayPreview(hitEntity, hit));
            }
            Status("hovering " + Describe(hitEntity) + ", no crossing");
            Say("No crossing here. Point at a highway (a new cross street is added), where it meets a street, or where a road crosses a railway.");
            return null;
        }

        /* plans are worked out once per crossing and setting; the preview is re-emitted every frame */
        Preview Cached(string key, System.Func<Preview> plan)
        {
            if (key == m_PreviewKey && m_Preview != null && StillValid(m_Preview)) { m_KeyAge++; if (m_Preview.Specs.Count == 0) Say(m_Preview.Status); return m_Preview; }
            m_PreviewKey = key; m_KeyAge = 0;
            var pv = WithFit(plan, m_FitVariant) ?? new Preview { Status = StatusText };
            if (m_FitVariant == 0) m_FitFirstFail = pv.Specs.Count == 0 ? pv.Status : "";
            m_Preview = pv;
            if (pv.Specs.Count == 0) Say(pv.Status);
            if (pv.Log != null) LogOnce((pv.Specs.Count > 0 ? "Preview: " : "Nothing to build: ") + pv.Log);
            return pv;
        }

        bool StillValid(Preview pv)
        {
            foreach (var s in pv.Specs)
            {
                if (s.Delete && !Live(s.Original)) return false;
                if (s.StartEntity != Entity.Null && !EntityManager.Exists(s.StartEntity)) return false;
                if (s.EndEntity != Entity.Null && !EntityManager.Exists(s.EndEntity)) return false;
            }
            return true;
        }

        Preview Fail(string what, string why) => new Preview { Status = $"{what}: {why}.", Log = why };
        Preview FailFinal(string what, string why) => new Preview { Status = $"{what}: {why}.", Log = why, NoFit = true };

        /* ================= what the game shows in red, in words ================= */

        private int m_KeyAge;
        private float3 m_HoverPos;
        private string m_BlockKey = "", m_BlockText = "";


        /* is a point on or next to one of the pieces this preview builds? (other red things in the city are not ours) */
        bool NearPreview(float3 at)
        {
            if (m_Preview == null) return true;
            foreach (var s in m_Preview.Specs)
            {
                if (s.Delete) continue;
                if (MathUtils.Distance(s.Curve.xz, at.xz, out float _) < 45f) return true;
            }
            return false;
        }

        /* ================= autofit: try other layouts until the game accepts one ================= */

        /*
         * Each layout autofit tries: curve size, alternative route, gradient, clearance, ramp length and which
         * road goes over (0 = as set). It moves on when the game shows red or nothing can be planned, and the
         * status says what it changed.
         */
        public struct Fit { public float grade, clear; public int compact, flip, size, tight; }
        static readonly Fit[] FitVariants =
        {
            new Fit { size = -1 },
            new Fit { grade = 0.065f, size = 0 },
            new Fit { size = -1, tight = 1 },
            new Fit { grade = 0.075f, compact = 1, size = 0, tight = 1 },
            new Fit { flip = 1, size = -1 },
            new Fit { grade = 0.065f, compact = 2, size = 2 },
            new Fit { grade = 0.085f, size = 0 },       // (never a lower clearance: 2026-10-23 self-test, "not enough clearance")
            new Fit { grade = 0.09f, flip = 1, size = 0 },
        };
        static readonly Fit[] GradeSizeFits =
        {
            new Fit { size = -1 },
            new Fit { grade = 0.065f, size = 0 },
            new Fit { grade = 0.065f, size = 2 },
            new Fit { grade = 0.085f, size = 0 },
        };
        static readonly Fit[] FlipGradeFits =
        {
            new Fit { size = -1 },
            new Fit { grade = 0.065f, size = 0 },
            new Fit { flip = 1, size = -1 },
            new Fit { grade = 0.065f, size = 2 },
            new Fit { grade = 0.085f, size = 0 },
            new Fit { grade = 0.09f, flip = 1, size = 0 },
        };
        Fit[] ActiveFits =>
            Mode == ToolMode.Ending || Mode == ToolMode.Dumbbell || (Mode == ToolMode.Overpass && DigUnder) ? GradeSizeFits
            : Mode == ToolMode.Overpass || Mode == ToolMode.Frontage ? FlipGradeFits
            : FitVariants;

        private int m_FitVariant; private string m_FitBase = "", m_FitFirstFail = "";
        bool AutofitActive() => Autofit && Mode != ToolMode.Repair;

        /* run a plan with the current layout's settings swapped in, then put the player's settings back */
        Preview WithFit(System.Func<Preview> plan, int variant)
        {
            var fits = ActiveFits;
            if (!AutofitActive() || variant == 0 || variant >= fits.Length) return plan();
            var f = fits[variant];
            var saved = Cfg;
            try
            {
                // plan with a modified copy of the settings; the player's own settings are restored as a whole
                Cfg = saved with
                {
                    Grade = f.grade > 0 ? math.max(saved.Grade, f.grade) : saved.Grade,
                    Clearance = f.clear > 0 ? math.min(saved.Clearance, f.clear) : saved.Clearance,
                    Compact = f.compact == 1 ? true : f.compact == 2 ? false : saved.Compact,
                    LiftStreet = f.flip == 1 ? !saved.LiftStreet : saved.LiftStreet,
                    Size = f.size >= 0 ? f.size : saved.Size,
                    TightRamps = f.tight == 1 ? !saved.TightRamps : saved.TightRamps,
                };
                var pv = plan();
                if (pv != null && pv.Specs.Count > 0) pv.Status = $"Autofit changed {FitChanges(f, saved)}. " + pv.Status;
                return pv;
            }
            finally { Cfg = saved; }
        }

        string FitChanges(Fit f, PlanConfig saved)
        {
            var parts = new List<string>();
            if (f.grade > 0 && Grade > saved.Grade + 0.001f) parts.Add($"gradient to {Grade * 100f:0.#}%");
            if (f.clear > 0 && Clearance < saved.Clearance - 0.01f) parts.Add($"clearance to {Clearance:0.#} m");
            if (Size != saved.Size) parts.Add("size to " + (Size == 0 ? "compact" : Size == 2 ? "spacious" : "standard"));
            if (TightRamps != saved.TightRamps) parts.Add(TightRamps ? "ramps to beside-highway" : "ramps to angled");
            if (Compact != saved.Compact) parts.Add(Compact ? "ramps to compact" : "ramps to gentle");
            if (LiftStreet != saved.LiftStreet) parts.Add(LiftStreet ? "the street to go over" : "the highway to go over");
            return parts.Count == 0 ? "the layout" : string.Join(", ", parts);
        }

        /* the cache key for a layout: the same place, plus which variant is being tried */
        string FitKey(string baseKey)
        {
            if (baseKey != m_FitBase) { m_FitBase = baseKey; m_FitVariant = 0; ResetTrim(); }
            return baseKey + "|v" + m_FitVariant;
        }

        /* nothing could be planned with these settings: try the next layout straight away */
        bool FitAfterFailure(Preview pv)
        {
            var fits = ActiveFits;
            if (pv == null || pv.Specs.Count > 0 || pv.NoFit || !AutofitActive() || m_FitBase == "") return false;
            if (m_FitVariant + 1 >= fits.Length)
            {
                if (m_FitFirstFail != "") Say($"Autofit tried {fits.Length} layouts and nothing fits. {m_FitFirstFail}");
                return false;
            }
            FitNext();
            Say($"Autofit: trying layout {m_FitVariant + 1} of {fits.Length}...");
            return true;
        }

        /* the game marked the preview red: move on to the next layout */
        void FitNext()
        {
            var fits = ActiveFits;
            if (!AutofitActive() || m_FitVariant + 1 >= fits.Length) return;
            m_FitVariant++; m_PreviewKey = ""; m_HoverKey = "";
            SafeLog($"Autofit: trying layout {m_FitVariant + 1} of {fits.Length}");
        }


        static string Compass(float3 d)
        {
            string[] names = { "east", "north-east", "north", "north-west", "west", "south-west", "south", "south-east" };
            float a = math.atan2(d.z, d.x);
            int i = (int)math.round(a / (math.PI / 4f)); i = ((i % 8) + 8) % 8;
            return names[i];
        }

        /* ================= finding crossings that still need fixing ================= */

        private readonly List<Entity> m_Visited = new List<Entity>();


        /* a junction where interchange ramps meet a street looks like a crossing; it isn't one: a highway merge lies close by both ways */
        bool IsTerminal(Entity node)
        {
            Classify(node, m_Hw, m_Other, out _);
            var hws = new List<Entity>(m_Hw);
            if (hws.Count != 2) return false;
            int merges = 0;
            foreach (var h in hws)
            {
                Entity at = node, edge = h; float dist = 0;
                for (int step = 0; step < 16 && dist < 450f; step++)
                {
                    Entity next = Other(edge, at);
                    dist += EntityManager.GetComponentData<Curve>(edge).m_Length;
                    if (!Live(next)) break;
                    Classify(next, m_Hw, m_Other, out _);
                    if (m_Hw.Count >= 3) { merges++; break; }
                    if (m_Hw.Count != 2) break;
                    edge = m_Hw[0] == edge ? m_Hw[1] : m_Hw[0]; at = next;
                }
            }
            return merges == 2;
        }

        /* ================= a crossing still at ground level ================= */

        Preview AtGradePreview(Entity crossing)
        {
            if (Mode == ToolMode.Dumbbell && LiftStreet)
            {
                var saved = Cfg;
                try { Cfg = saved with { LiftStreet = false }; return AtGradePreview(crossing); }
                finally { Cfg = saved; }
            }
            if (Mode == ToolMode.Auto && StreetClass(crossing) == "local street")
            {
                var saved = Cfg;
                try
                {
                    Cfg = saved with { Mode = ToolMode.Overpass, Dig = false, KeepElevated = false };
                    var bridgeOnly = AtGradePreview(crossing);
                    bridgeOnly.Status = "Best fit: a local street needs a bridge, without interchange ramps. " + bridgeOnly.Status;
                    return bridgeOnly;
                }
                finally { Cfg = saved; }
            }
            bool ramps = Mode != ToolMode.Overpass;
            bool streetOver = LiftStreet;
            var pv = new Preview();
            var deleted = new HashSet<Entity>();
            string what = streetOver ? "Can't lift the street here" : "Can't lift the highway here";
            string bridge;
            if (streetOver)
            {
                var p = PlanStreetBridge(crossing, out string why);
                if (p == null) return Fail(what, why + " (try 'Highway over street' instead)");
                if (DigUnder) p.Sign = -1f;
                WriteLift(pv, p, deleted);
                bridge = DigUnder ? $"the street dips under in a {(int)(p.End - p.Start)} m cutting (the highway is left as it is)" : $"the street goes over on a {(int)(p.End - p.Start)} m bridge";
            }
            else
            {
                var first = PlanHighwayBridge(crossing, out string why);
                if (first == null) return Fail(what, why);
                WriteLift(pv, first, deleted);
                int n = 1;
                Entity partner = BothCarriageways ? FindPartnerCrossing(crossing, first) : Entity.Null;
                if (partner != Entity.Null)
                {
                    var second = PlanHighwayBridge(partner, out string why2);
                    if (second != null && !Overlaps(first, second)) { WriteLift(pv, second, deleted); n++; }
                }
                bridge = $"{(n > 1 ? "both carriageways go" : "the highway goes")} over on a {(int)(first.End - first.Start)} m bridge";
            }
            string kind = StreetClass(crossing);
            pv.NextStep = ramps; pv.NextPos = NodePos(crossing); pv.NextMode = Mode;
            string style = StyleName(Mode);
            if (ramps)
            {
                // Virtual-apply Stage 1 locally (within 700 m) to verify Stage 2 ramps can actually plan before committing the bridge
                var after = EntityManager.Apply(pv, pv.NextPos.xz, 700f);
                var probe = new Planner(after, m_TerrainSystem, m_NameSystem, NullLog.Instance) { Cfg = Cfg };
                var sepAfter = probe.FindSeparated(pv.NextPos, true);
                var stage2 = sepAfter.Count > 0 ? probe.PreviewFor(pv.NextMode, sepAfter, pv.NextPos) : null;
                if (stage2 == null || stage2.Specs.Count == 0)
                {
                    string raw = stage2 != null && !string.IsNullOrEmpty(stage2.Log) ? stage2.Log
                        : stage2 != null && !string.IsNullOrEmpty(stage2.Status) ? stage2.Status
                        : "no ramps could be planned after building the bridge";
                    int colon = raw.IndexOf(": ");
                    string reason = colon >= 0 && raw.StartsWith("Can't ") ? raw.Substring(colon + 2) : raw;
                    var fail = Fail($"Can't build a {style} interchange here", $"the bridge alone would fit, but stage 2 ramps failed ({reason})");
                    if (stage2 != null && stage2.NoFit && !reason.Contains("roundabout")) fail.NoFit = true;
                    return fail;
                }
            }
            pv.Log = $"{(streetOver ? "street" : "highway")} bridge at a {kind}" + (ramps ? $", then a {style} interchange" : "");
            if (ramps)
                pv.Status = $"First {bridge}, then the {style} interchange ramps are added automatically. Click to build."
                    + (kind == "local street" ? " (An exit at a local street is unusual.)" : "");
            else
                pv.Status = $"Grade-separate this {kind}: {bridge}. Click to build." + (kind != "local street" ? " An exit is suggested at an arterial like this one." : "");
            return pv;
        }

        string StreetClass(Entity crossing)
        {
            Classify(crossing, m_Hw, m_Other, out _);
            float w = 0; foreach (var o in m_Other) w = math.max(w, WidthOf(o));
            return w >= 24f ? "major arterial" : w >= 16f ? "arterial" : "local street";
        }

        /* ================= a road crossing a railway at ground level ================= */

        /*
         * The railway takes precedence: it is never moved. The road (a street, or both carriageways of a
         * highway) is lifted over the tracks on a bridge, and over any parallel tracks next to them.
         */
        bool IsRail(Entity e) => Live(e) && EntityManager.HasComponent<Edge>(e) && EntityManager.HasComponent<TrainTrack>(e) && !EntityManager.HasComponent<Road>(e);

        int RailCount(Entity node) => RailEdges(node).Count;

        List<Entity> RailEdges(Entity node)
        {
            var list = new List<Entity>();
            if (!EntityManager.HasBuffer<ConnectedEdge>(node)) return list;
            var buf = EntityManager.GetBuffer<ConnectedEdge>(node, true);
            for (int i = 0; i < buf.Length; i++)
            {
                Entity e = buf[i].m_Edge;
                if (!IsRail(e)) continue;
                var edge = EntityManager.GetComponentData<Edge>(e);
                if (edge.m_Start == node || edge.m_End == node) list.Add(e);
            }
            return list;
        }

        bool IsRailCrossing(Entity node)
        {
            if (!Live(node) || !EntityManager.HasComponent<Node>(node) || RailCount(node) == 0) return false;
            Classify(node, m_Hw, m_Other, out _);
            return m_Hw.Count + m_Other.Count > 0;
        }

        Entity FindRailCrossing(Entity hitEntity, float3 hitPos)
        {
            var nodes = new HashSet<Entity>();
            if (EntityManager.HasComponent<Edge>(hitEntity))
            {
                var e = EntityManager.GetComponentData<Edge>(hitEntity);
                nodes.Add(e.m_Start); nodes.Add(e.m_End);
            }
            else if (EntityManager.HasComponent<Node>(hitEntity)) nodes.Add(hitEntity);
            else return Entity.Null;
            foreach (var n in new List<Entity>(nodes))
            {
                if (!EntityManager.HasBuffer<ConnectedEdge>(n)) continue;
                var buf = EntityManager.GetBuffer<ConnectedEdge>(n, true);
                for (int i = 0; i < buf.Length; i++)
                {
                    Entity e = buf[i].m_Edge;
                    if (!Live(e) || !EntityManager.HasComponent<Edge>(e)) continue;
                    var ed = EntityManager.GetComponentData<Edge>(e);
                    if (ed.m_Start == n || ed.m_End == n) nodes.Add(Other(e, n));
                }
            }
            Entity best = Entity.Null; float bd = 120f;
            foreach (var n in nodes)
            {
                if (!IsRailCrossing(n)) continue;
                float d = math.distance(NodePos(n).xz, hitPos.xz);
                if (d < bd) { bd = d; best = n; }
            }
            return best;
        }

        Preview RailPreview(Entity node)
        {
            const string what = "Can't take the road over the railway here";
            Classify(node, m_Hw, m_Other, out _);
            bool highway = m_Hw.Count == 2 && m_Other.Count == 0;
            if (!highway && !(m_Other.Count == 2 && m_Hw.Count == 0))
                return Fail(what, m_Hw.Count + m_Other.Count < 2 ? "the road ends at the tracks" : "a junction sits right on the tracks; move it off them first");
            float roadW = WidthOf(highway ? m_Hw[0] : m_Other[0]);
            var first = PlanRoadOverRail(node, out string why);
            if (first == null) return Fail(what, why);
            var pv = new Preview();
            var deleted = new HashSet<Entity>();
            WriteLift(pv, first, deleted);
            int n = 1;
            if (highway && BothCarriageways)
            {
                Entity partner = FindRailPartner(node, first);
                if (partner != Entity.Null)
                {
                    var second = PlanRoadOverRail(partner, out string why2);
                    if (second != null && !Overlaps(first, second)) { WriteLift(pv, second, deleted); n++; }
                    else if (second == null) LogOnce("Other carriageway not lifted: " + why2);
                }
            }
            string kind = highway ? (n > 1 ? "highway (both carriageways)" : "highway") : (roadW >= 24f ? "major arterial" : roadW >= 16f ? "arterial" : "street");
            int len = (int)(first.End - first.Start);
            pv.Log = $"{kind} over the railway, {len} m bridge";
            pv.Status = $"Take the {kind} over the railway on a {len} m bridge. The tracks are left as they are. Click to build."
                + (Mode != ToolMode.Overpass ? " (Railway crossings get a bridge only, whatever the style.)" : "");
            return pv;
        }

        /* the road through a level crossing, lifted over the tracks (and any next to them) */
        Plan PlanRoadOverRail(Entity node, out string why)
        {
            why = "";
            Classify(node, m_Hw, m_Other, out _);
            bool highway = m_Hw.Count == 2;
            var roads = new List<Entity>(highway ? m_Hw : m_Other);
            if (roads.Count != 2) { why = "the road doesn't run straight through the crossing"; return null; }
            float railHalf = 3f;
            foreach (var r in RailEdges(node)) railHalf = math.max(railHalf, WidthOf(r) * 0.5f);
            float margin = railHalf + 10f, ramp = Clearance / Grade, minRamp = Clearance / MaxGrade;
            string backStop, fwdStop; List<float> backUnder, fwdUnder;
            var back = highway ? WalkHighway(node, roads[0], margin + ramp, out backStop, out backUnder, out why)
                               : WalkStreet(node, roads[0], margin + ramp, out backStop, out backUnder, out why);
            if (back == null) return null;
            var fwd = highway ? WalkHighway(node, roads[1], margin + ramp, out fwdStop, out fwdUnder, out why)
                              : WalkStreet(node, roads[1], margin + ramp, out fwdStop, out fwdUnder, out why);
            if (fwd == null) return null;
            var p = new Plan { HighwayHalf = railHalf, StreetHalf = WidthOf(roads[0]) * 0.5f, KeepOff = math.max(railHalf + 6f, 12f) };
            p.Cross = Join(p, back, fwd);
            return Finish(p, backUnder, fwdUnder, backStop, fwdStop, margin, ramp, minRamp, out why) ? p : null;
        }

        /* the other carriageway of a highway, where it crosses the same railway (found by following the tracks) */
        Entity FindRailPartner(Entity node, Plan first)
        {
            Entity best = Entity.Null; float bd = 150f;
            foreach (var start in RailEdges(node))
            {
                Entity at = node, edge = start; float dist = 0;
                for (int step = 0; step < 6 && dist < 150f; step++)
                {
                    Entity next = Other(edge, at);
                    dist += EntityManager.GetComponentData<Curve>(edge).m_Length;
                    if (next == node || !Live(next)) break;
                    Classify(next, m_Hw, m_Other, out _);
                    if (m_Hw.Count == 2 && !first.Edges.Contains(m_Hw[0]) && !first.Edges.Contains(m_Hw[1]))
                    {
                        if (dist < bd) { bd = dist; best = next; }
                        break;
                    }
                    var rails = RailEdges(next);
                    if (rails.Count != 2) break;
                    edge = rails[0] == edge ? rails[1] : rails[0];
                    at = next;
                }
            }
            return best;
        }

        /* ================= the network ================= */

        bool Live(Entity e) => e != Entity.Null && EntityManager.Exists(e) && !EntityManager.HasComponent<Temp>(e) && !EntityManager.HasComponent<Deleted>(e);
        bool IsRoadEdge(Entity e) => Live(e) && EntityManager.HasComponent<Edge>(e) && EntityManager.HasComponent<Road>(e);
        Entity PrefabOf(Entity e) => EntityManager.GetComponentData<PrefabRef>(e).m_Prefab;
        float3 NodePos(Entity n) => EntityManager.GetComponentData<Node>(n).m_Position;

        bool IsHighway(Entity e)
        {
            if (!IsRoadEdge(e)) return false;
            var prefab = PrefabOf(e);
            return EntityManager.HasComponent<RoadData>(prefab)
                && (EntityManager.GetComponentData<RoadData>(prefab).m_Flags & RoadFlags.UseHighwayRules) != 0;
        }

        float WidthOf(Entity edge) => WidthOfPrefab(PrefabOf(edge));
        float WidthOfPrefab(Entity prefab) => EntityManager.HasComponent<NetGeometryData>(prefab) ? EntityManager.GetComponentData<NetGeometryData>(prefab).m_DefaultWidth : 8f;

        string Describe(Entity e)
        {
            if (!EntityManager.Exists(e)) return "nothing";
            string kind = EntityManager.HasComponent<Edge>(e) ? "road piece" : EntityManager.HasComponent<Node>(e) ? "node" : "object";
            string name = EntityManager.HasComponent<PrefabRef>(e) ? m_PrefabSystem.GetPrefabName(PrefabOf(e)) : "?";
            return $"{kind} '{name}'";
        }

        readonly List<Entity> m_Hw = new List<Entity>(), m_Other = new List<Entity>();

        void Classify(Entity node, List<Entity> highway, List<Entity> other, out int total)
        {
            highway.Clear(); other.Clear(); total = 0;
            if (!EntityManager.HasBuffer<ConnectedEdge>(node)) return;
            var buf = EntityManager.GetBuffer<ConnectedEdge>(node, true);
            for (int i = 0; i < buf.Length; i++)
            {
                Entity e = buf[i].m_Edge;
                if (!Live(e)) continue;
                var edge = EntityManager.GetComponentData<Edge>(e);
                if (edge.m_Start != node && edge.m_End != node) continue;
                total++;
                if (IsHighway(e)) highway.Add(e); else if (IsRoadEdge(e)) other.Add(e);
            }
        }

        bool IsCrossing(Entity node) { Classify(node, m_Hw, m_Other, out _); return m_Hw.Count == 2 && m_Other.Count >= 1; }
        bool IsRaised(Entity node) => EntityManager.HasComponent<Elevation>(node) && math.cmax(EntityManager.GetComponentData<Elevation>(node).m_Elevation) > 2f;

        Entity Other(Entity edge, Entity node)
        {
            var e = EntityManager.GetComponentData<Edge>(edge);
            return e.m_Start == node ? e.m_End : e.m_Start;
        }

        Entity FindCrossing(Entity hitEntity, float3 hitPos)
        {
            var nodes = new HashSet<Entity>();
            if (EntityManager.HasComponent<Edge>(hitEntity))
            {
                var e = EntityManager.GetComponentData<Edge>(hitEntity);
                nodes.Add(e.m_Start); nodes.Add(e.m_End);
            }
            else if (EntityManager.HasComponent<Node>(hitEntity)) nodes.Add(hitEntity);
            else return Entity.Null;
            foreach (var n in new List<Entity>(nodes))
            {
                if (!EntityManager.HasBuffer<ConnectedEdge>(n)) continue;
                var buf = EntityManager.GetBuffer<ConnectedEdge>(n, true);
                for (int i = 0; i < buf.Length; i++) if (IsRoadEdge(buf[i].m_Edge)) nodes.Add(Other(buf[i].m_Edge, n));
            }
            Entity best = Entity.Null; float bd = 120f;
            foreach (var n in nodes)
            {
                if (!Live(n) || !EntityManager.HasComponent<Node>(n) || !IsCrossing(n) || IsTerminal(n)) continue;
                float d = math.distance(NodePos(n).xz, hitPos.xz);
                if (d < bd) { bd = d; best = n; }
            }
            return best;
        }

        Entity FindPartnerCrossing(Entity crossing, Plan first)
        {
            Classify(crossing, m_Hw, m_Other, out _);
            var streets = new List<Entity>(m_Other);
            Entity best = Entity.Null; float bd = 150f;
            foreach (var s in streets)
            {
                Entity at = crossing, edge = s; float dist = 0;
                for (int step = 0; step < 4 && dist < 150f; step++)
                {
                    Entity next = Other(edge, at);
                    dist += EntityManager.GetComponentData<Curve>(edge).m_Length;
                    if (next == crossing || !Live(next)) break;
                    if (IsCrossing(next) && !first.Edges.Contains(m_Hw[0]) && !first.Edges.Contains(m_Hw[1]))
                    {
                        if (dist < bd) { bd = dist; best = next; }
                        break;
                    }
                    Classify(next, m_Hw, m_Other, out _);
                    if (m_Hw.Count != 0 || m_Other.Count != 2) break;
                    edge = m_Other[0] == edge ? m_Other[1] : m_Other[0];
                    at = next;
                }
            }
            return best;
        }

        /* ================= chains of road ================= */

        public class Seg
        {
            public Entity Edge, From, To; public Bezier4x3 Curve; public float Length, S0; public float[] Table;
            public bool Forward;   // the chain runs the same way as the edge (and its traffic)
        }

        public class Plan
        {
            public List<Seg> Segs = new List<Seg>();
            public HashSet<Entity> Edges = new HashSet<Entity>();
            public List<float> Under = new List<float>();      // positions of what the bridge crosses
            public List<Entity> Close = new List<Entity>();     // local street crossings closed off for ramps
            public float Start, End, RampUp, RampDown, Cross, KeepOff, StreetHalf, HighwayHalf, Total;
            public float Diverge = float.NaN, Merge = float.NaN;
            public int Dir = 1, RampLanes = 1;
            public string StreetClass = "local street";
            public Entity SpanPrefab = Entity.Null;            // a new span in the chain (Seg.Edge null) is built as this
            public float Sign = 1f;                            // +1 over (a bridge), -1 under (a cutting)
            public Attach TailAttach;                          // the new span's far end joins this road piece (a split)
        }

        Seg MakeSeg(Entity edge, Entity from)
        {
            var e = EntityManager.GetComponentData<Edge>(edge); var c = EntityManager.GetComponentData<Curve>(edge);
            bool fwd = e.m_Start == from;
            var bz = fwd ? c.m_Bezier : MathUtils.Invert(c.m_Bezier);
            return new Seg { Edge = edge, From = from, To = fwd ? e.m_End : e.m_Start, Curve = bz, Length = c.m_Length, Table = LengthTable(bz), Forward = fwd };
        }

        static Seg Reverse(Seg s) => new Seg { Edge = s.Edge, From = s.To, To = s.From, Curve = MathUtils.Invert(s.Curve), Length = s.Length, Table = LengthTable(MathUtils.Invert(s.Curve)), Forward = !s.Forward };

        /* join a back walk (outwards from the crossing) and a forward walk into one chain through the crossing */
        float Join(Plan p, List<Seg> back, List<Seg> fwd)
        {
            float s = 0;
            for (int i = back.Count - 1; i >= 0; i--) { var r = Reverse(back[i]); r.S0 = s; p.Segs.Add(r); s += r.Length; }
            float cross = s;
            foreach (var f in fwd) { f.S0 = s; p.Segs.Add(f); s += f.Length; }
            foreach (var sg in p.Segs) p.Edges.Add(sg.Edge);
            p.Total = s;
            return cross;
        }

        static float[] LengthTable(Bezier4x3 c)
        {
            const int N = 32; var t = new float[N + 1]; float acc = 0; float3 prev = c.a;
            for (int i = 1; i <= N; i++) { float3 q = MathUtils.Position(c, i / (float)N); acc += math.distance(prev, q); prev = q; t[i] = acc; }
            return t;
        }

        static float TAt(Seg sg, float local)
        {
            var t = sg.Table; float total = t[t.Length - 1]; if (total <= 0) return 0;
            float want = math.clamp(local, 0, sg.Length) * total / math.max(sg.Length, 0.001f);
            for (int i = 1; i < t.Length; i++)
                if (t[i] >= want) { float f = (want - t[i - 1]) / math.max(t[i] - t[i - 1], 1e-4f); return (i - 1 + f) / (t.Length - 1); }
            return 1;
        }

        static float LengthAt(Seg sg, float t)
        {
            var tb = sg.Table; float f = math.clamp(t, 0, 1) * (tb.Length - 1); int i = math.min((int)f, tb.Length - 2);
            return math.lerp(tb[i], tb[i + 1], f - i) * sg.Length / math.max(tb[tb.Length - 1], 0.001f);
        }

        static Seg SegAt(Plan p, float s)
        {
            foreach (var sg in p.Segs) if (s <= sg.S0 + sg.Length + 0.001f) return sg;
            return p.Segs[p.Segs.Count - 1];
        }

        static float3 Position(Plan p, float s) { var sg = SegAt(p, s); return MathUtils.Position(sg.Curve, TAt(sg, s - sg.S0)); }
        static float3 Tangent(Plan p, float s) { var sg = SegAt(p, s); return MathUtils.Tangent(sg.Curve, TAt(sg, s - sg.S0)); }

        float3 Right(Plan p, float s)
        {
            float3 t = Tangent(p, s) * p.Dir; t.y = 0; t = math.normalizesafe(t);
            return new float3(t.z, 0, -t.x);
        }

        static float3 Ground(float3 q, ref TerrainHeightData heights) { q.y = TerrainUtils.SampleHeight(ref heights, q); return q; }

        bool Overlaps(Plan a, Plan b) { foreach (var e in b.Edges) if (a.Edges.Contains(e)) return true; return false; }

        /* ================= bridges ================= */

        /*
         * The street over the highway: follow the street out from the crossing both ways, over the other
         * carriageway, until there is room to come back down. The highway is not touched.
         */
        Plan PlanStreetBridge(Entity crossing, out string why)
        {
            why = "";
            Classify(crossing, m_Hw, m_Other, out _);
            if (m_Hw.Count != 2) { why = "not a simple crossing"; return null; }
            if (m_Other.Count != 2) { why = "the street stops at the highway"; return null; }
            var streets = new List<Entity>(m_Other);
            float hwHalf = WidthOf(m_Hw[0]) * 0.5f;
            float margin = hwHalf + DeckMargin;   // a flat deck wide enough for the ramp junctions (or roundabouts)
            float ramp = Clearance / Grade, minRamp = Clearance / MaxGrade;
            var back = WalkStreet(crossing, streets[0], margin + ramp, out string backStop, out var backUnder, out why);
            if (back == null) return null;
            var fwd = WalkStreet(crossing, streets[1], margin + ramp, out string fwdStop, out var fwdUnder, out why);
            if (fwd == null) return null;
            var p = new Plan { HighwayHalf = hwHalf, StreetHalf = WidthOf(streets[0]) * 0.5f, KeepOff = hwHalf + 8f };
            p.Cross = Join(p, back, fwd);
            return Finish(p, backUnder, fwdUnder, backStop, fwdStop, margin, ramp, minRamp, out why) ? p : null;
        }

        /* the highway over the street (one carriageway); its partner is planned separately */
        Plan PlanHighwayBridge(Entity crossing, out string why)
        {
            why = "";
            Classify(crossing, m_Hw, m_Other, out _);
            if (m_Hw.Count != 2) { why = "not a simple highway crossing"; return null; }
            float streetW = 0; foreach (var o in m_Other) streetW = math.max(streetW, WidthOf(o));
            float streetHalf = math.max(6f, streetW * 0.5f);
            var hws = new List<Entity>(m_Hw);
            float margin = streetHalf + 14f, ramp = Clearance / Grade, minRamp = Clearance / MaxGrade;
            var back = WalkHighway(crossing, hws[0], margin + ramp, out string backStop, out var backUnder, out why);
            if (back == null) return null;
            var fwd = WalkHighway(crossing, hws[1], margin + ramp, out string fwdStop, out var fwdUnder, out why);
            if (fwd == null) return null;
            float keepOff = streetHalf + 12f;
            var p = new Plan { StreetHalf = streetHalf, HighwayHalf = WidthOf(hws[0]) * 0.5f, KeepOff = keepOff };
            p.Cross = Join(p, back, fwd);
            return Finish(p, backUnder, fwdUnder, backStop, fwdStop, margin, ramp, minRamp, out why) ? p : null;
        }

        bool Finish(Plan p, List<float> backUnder, List<float> fwdUnder, string backStop, string fwdStop, float margin, float ramp, float minRamp, out string why)
        {
            why = "";
            float reachBack = 0, reachFwd = 0;
            p.Under.Add(p.Cross);
            foreach (var d in backUnder) { reachBack = math.max(reachBack, d); p.Under.Add(p.Cross - d); }
            foreach (var d in fwdUnder) { reachFwd = math.max(reachFwd, d); p.Under.Add(p.Cross + d); }
            float rampBack = math.min(ramp, p.Cross - reachBack - margin);
            float rampFwd = math.min(ramp, p.Total - p.Cross - reachFwd - margin);
            if (rampBack < minRamp) { why = $"only {(int)math.max(0, rampBack)} m to come down on one side before {backStop}; a ramp needs {(int)minRamp} m"; return false; }
            if (rampFwd < minRamp) { why = $"only {(int)math.max(0, rampFwd)} m to come down on one side before {fwdStop}; a ramp needs {(int)minRamp} m"; return false; }
            p.Start = p.Cross - reachBack - margin - rampBack;
            p.End = p.Cross + reachFwd + margin + rampFwd;
            foreach (var sg in p.Segs)
            {
                if (math.abs(sg.S0 - p.Start) < SnapToNode) p.Start = sg.S0;
                if (math.abs(sg.S0 + sg.Length - p.End) < SnapToNode) p.End = sg.S0 + sg.Length;
            }
            p.RampUp = p.Start + rampBack; p.RampDown = p.End - rampFwd;
            if (p.End - p.Start > MaxSpan) { why = "the bridge would be longer than 2.5 km"; return false; }
            return true;
        }

        /* along a street: over other carriageways of the highway, stopping at side streets and ends */
        List<Seg> WalkStreet(Entity crossing, Entity firstEdge, float need, out string stop, out List<float> under, out string why)
        {
            why = ""; stop = "the street ends"; under = new List<float>();
            var list = new List<Seg>();
            Entity at = crossing, edge = firstEdge; float since = 0, total = 0;
            for (int guard = 0; guard < 200; guard++)
            {
                var sg = MakeSeg(edge, at); list.Add(sg);
                since += sg.Length; total += sg.Length;
                if (since >= need) return list;
                if (total > MaxSpan) { why = "no room to come down within 2.5 km"; return null; }
                Entity next = sg.To;
                Classify(next, m_Hw, m_Other, out _);
                if (m_Other.Count == 2 && (m_Hw.Count > 0 || RailCount(next) > 0)) { under.Add(total); since = 0; }      // the other carriageway, or another track: over it too
                else if (m_Other.Count != 2 || m_Hw.Count > 0) { stop = m_Other.Count > 2 ? $"a side street {(int)total} m out" : m_Other.Count < 2 ? "the street ends" : "a junction"; return list; }
                edge = m_Other[0] == edge ? m_Other[1] : m_Other[0];
                at = next;
            }
            why = "the street is too broken up here";
            return null;
        }

        /* along a highway carriageway: over streets and existing bridges, stopping at junctions and ends */
        List<Seg> WalkHighway(Entity crossing, Entity firstEdge, float need, out string stop, out List<float> under, out string why)
        {
            why = ""; stop = ""; under = new List<float>();
            var list = new List<Seg>();
            Entity at = crossing, edge = firstEdge; float since = 0, total = 0;
            for (int guard = 0; guard < 300; guard++)
            {
                var sg = MakeSeg(edge, at); list.Add(sg);
                since += sg.Length; total += sg.Length;
                if (since >= need) return list;
                if (total > MaxSpan + 400f) { why = "no room to come down within 2.5 km"; return null; }
                Entity next = sg.To;
                Classify(next, m_Hw, m_Other, out _);
                if (m_Hw.Count != 2) { stop = m_Hw.Count > 2 ? "a highway junction" : "the highway ends"; return list; }
                if (m_Other.Count > 0 || IsRaised(next) || RailCount(next) > 0) { under.Add(total); since = 0; }
                edge = m_Hw[0] == edge ? m_Hw[1] : m_Hw[0];
                at = next;
            }
            why = "the highway is too broken up here";
            return null;
        }

        float ElevationAt(Plan p, float s)
        {
            if (s <= p.Start || s >= p.End) return 0;
            if (s < p.RampUp) return p.Sign * Clearance * math.smoothstep(p.Start, p.RampUp, s);
            if (s > p.RampDown) return p.Sign * Clearance * math.smoothstep(p.End, p.RampDown, s);
            return p.Sign * Clearance;
        }

        /* analytic derivative of ElevationAt (metres of rise per metre along the road) for C1-smooth vertical curves */
        float ElevationSlopeAt(Plan p, float s)
        {
            if (s <= p.Start || s >= p.End) return 0f;
            if (s < p.RampUp)
            {
                float span = p.RampUp - p.Start; if (span <= 0.01f) return 0f;
                float u = math.saturate((s - p.Start) / span);
                return p.Sign * Clearance * (6f * u * (1f - u)) / span;
            }
            if (s > p.RampDown)
            {
                float span = p.End - p.RampDown; if (span <= 0.01f) return 0f;
                float u = math.saturate((p.End - s) / span);
                return -p.Sign * Clearance * (6f * u * (1f - u)) / span;
            }
            return 0f;
        }

        /* rebuild the chain between Start and End on a bridge: same road type, upgrades, direction and (later) name */
        void WriteLift(Preview pv, Plan p, HashSet<Entity> deleted)
        {
            var heights = m_TerrainSystem.GetHeightData(false);
            var touched = new List<Seg>();
            foreach (var sg in p.Segs) if (sg.S0 + sg.Length > p.Start + 0.01f && sg.S0 < p.End - 0.01f) touched.Add(sg);
            if (touched.Count == 0) return;
            foreach (var sg in touched) if (sg.Edge != Entity.Null && deleted.Add(sg.Edge)) pv.Specs.Add(new Spec { Delete = true, Original = sg.Edge });
            float lo = touched[0].S0, hi = touched[touched.Count - 1].S0 + touched[touched.Count - 1].Length;
            // remember the road's name, to give it back after the build
            float mid = (p.Start + p.End) * 0.5f;
            var midEdge = SegAt(p, mid).Edge;
            if (midEdge == Entity.Null) foreach (var sg in touched) if (sg.Edge != Entity.Null) { midEdge = sg.Edge; break; }
            string name = midEdge != Entity.Null ? NameOf(midEdge) : null;
            if (name != null) pv.Names.Add((Position(p, mid), name, IsHighway(midEdge)));
            // break points: ends, ramp tops, old nodes on the ground, and enough in between
            var bps = new List<float> { lo, hi, p.Start, p.End, p.RampUp, p.RampDown };
            foreach (var sg in touched)
                foreach (float at in new[] { sg.S0, sg.S0 + sg.Length })
                    if (at <= p.Start + 0.5f || at >= p.End - 0.5f) bps.Add(at);
            bps.RemoveAll(x => x < lo - 0.01f || x > hi + 0.01f);
            bps.Sort();
            var pts = new List<float>();
            foreach (var x in bps) if (pts.Count == 0 || x - pts[pts.Count - 1] > 2f) pts.Add(x);
            var filled = new List<float>();
            for (int i = 0; i < pts.Count; i++)
            {
                filled.Add(pts[i]);
                if (i + 1 >= pts.Count) break;
                float gap = pts[i + 1] - pts[i];
                int n = (int)math.ceil(gap / MaxPiece);
                for (int k = 1; k < n; k++) filled.Add(pts[i] + gap * k / n);
            }
            // keep every node (and so every pillar) off whatever passes underneath
            var final = new List<float>();
            foreach (var x0 in filled)
            {
                float x = x0;
                if (x0 != lo && x0 != hi) x = OffUnder(x, p.Under, p.KeepOff);
                if (final.Count > 0 && x - final[final.Count - 1] < 4f) continue;
                final.Add(x);
            }
            for (int i = 0; i + 1 < final.Count; i++)
            {
                float s0 = final[i], s1 = final[i + 1];
                float e0 = ElevationAt(p, s0), e1 = ElevationAt(p, s1);
                var curve = Piece(p, s0, s1, ref heights, e0, e1);
                Entity a = NodeAt(touched, s0, e0, i == 0), b = NodeAt(touched, s1, e1, i == final.Count - 2);
                var src = SegAt(p, (s0 + s1) * 0.5f);
                var spec = new Spec { Prefab = src.Edge != Entity.Null ? PrefabOf(src.Edge) : p.SpanPrefab };
                // each piece runs the way its traffic ran before
                if (src.Forward) { spec.Curve = curve; spec.StartEntity = a; spec.EndEntity = b; spec.E0 = e0; spec.E1 = e1; }
                else { spec.Curve = MathUtils.Invert(curve); spec.StartEntity = b; spec.EndEntity = a; spec.E0 = e1; spec.E1 = e0; }
                // the new span's far end joins a road piece part-way along it (the span runs forward, so it's the end)
                if (i == final.Count - 2 && src.Edge == Entity.Null && p.TailAttach != null)
                { spec.Curve.d = p.TailAttach.Pos; spec.EndEntity = p.TailAttach.Entity; spec.EndSplit = p.TailAttach.Split; }
                if (src.Edge != Entity.Null && EntityManager.HasComponent<Upgraded>(src.Edge)) { spec.HasUpgrade = true; spec.Upgrade = EntityManager.GetComponentData<Upgraded>(src.Edge).m_Flags; }
                pv.Specs.Add(spec);
            }
        }

        /*
         * Move a node (a pillar) out of the no-pillar zone round whatever passes underneath. Zones that overlap
         * (two carriageways with a narrow median) are one zone: pushing out of each in turn just bounced the
         * node back into the other (found 2026-10-15, a pillar in a 24 m median).
         */
        static float OffUnder(float x, List<float> under, float keepOff)
        {
            var zones = new List<float2>();
            var cs = new List<float>(under); cs.Sort();
            foreach (float c in cs)
            {
                if (zones.Count > 0 && c - keepOff <= zones[zones.Count - 1].y) zones[zones.Count - 1] = new float2(zones[zones.Count - 1].x, c + keepOff);
                else zones.Add(new float2(c - keepOff, c + keepOff));
            }
            foreach (var z in zones)
                if (x > z.x && x < z.y) return x - z.x < z.y - x ? z.x : z.y;
            return x;
        }

        Bezier4x3 Piece(Plan p, float s0, float s1, ref TerrainHeightData heights, float e0, float e1)
        {
            float3 a = Position(p, s0), d = Position(p, s1);
            float3 ta = math.normalizesafe(Tangent(p, s0)), td = math.normalizesafe(Tangent(p, s1));
            var curve = NetUtils.FitCurve(a, ta, td, d);
            float ha = TerrainUtils.SampleHeight(ref heights, curve.a);
            float hd = TerrainUtils.SampleHeight(ref heights, curve.d);
            curve.a.y = ha + e0;
            curve.d.y = hd + e1;
            if (math.abs(e0) < 0.05f && math.abs(e1) < 0.05f)
            {
                // ground-level piece: hug rolling terrain instead of cutting through hilltops or floating over valleys
                curve.b.y = TerrainUtils.SampleHeight(ref heights, curve.b);
                curve.c.y = TerrainUtils.SampleHeight(ref heights, curve.c);
            }
            else
            {
                float len = math.max(1f, s1 - s0);
                float tSlope = (hd - ha) / len;
                float g0 = tSlope + ElevationSlopeAt(p, s0);
                float g1 = tSlope + ElevationSlopeAt(p, s1);
                float lo = math.min(curve.a.y, curve.d.y), hi = math.max(curve.a.y, curve.d.y);
                curve.b.y = math.clamp(curve.a.y + g0 * (len / 3f), lo, hi);
                curve.c.y = math.clamp(curve.d.y - g1 * (len / 3f), lo, hi);
            }
            return curve;
        }

        Entity NodeAt(List<Seg> touched, float s, float elevation, bool isEnd)
        {
            if (!isEnd && math.abs(elevation) > 0.5f) return Entity.Null;     // raised or lowered: a new node, not the old one
            foreach (var sg in touched)
            {
                if (math.abs(s - sg.S0) < 0.05f) return sg.From;
                if (math.abs(s - (sg.S0 + sg.Length)) < 0.05f) return sg.To;
            }
            return Entity.Null;
        }

        /* ================= crossings already grade-separated ================= */

        public struct Sep { public Entity H, S; public float tH, tS; public float3 P; public bool HighwayOver; }
        // "nothing cached yet" must not be a real position: float3.zero made hovers within 40 m of the map centre see an empty list
        static readonly float3 NoSepKey = new float3(float.NaN);
        private float3 m_SepKey = NoSepKey;
        private List<Sep> m_Sep = new List<Sep>();

        /* every place near pos where a highway and a street cross at different levels (cached until the cursor moves on) */
        List<Sep> FindSeparated(float3 pos, bool force)
        {
            if (!force && math.distance(pos.xz, m_SepKey.xz) < 40f && m_Sep.TrueForAll(l => Live(l.H) && Live(l.S))) return m_Sep;
            m_SepKey = pos; m_Sep = new List<Sep>();
            var hw = new List<(Entity e, Bezier4x3 c)>(); var st = new List<(Entity e, Bezier4x3 c)>();
            foreach (var e in RoadsNear(pos.xz - 260f, pos.xz + 260f))
                {
                    if (!Live(e)) continue;
                    var c = EntityManager.GetComponentData<Curve>(e).m_Bezier;
                    if (MathUtils.Distance(c.xz, pos.xz, out float _) > 250f) continue;
                    if (IsHighway(e)) hw.Add((e, c)); else st.Add((e, c));
                }
            foreach (var h in hw)
                foreach (var s in st)
                    if (Cross2D(h.c, s.c, out float th, out float ts))
                    {
                        float3 ph = MathUtils.Position(h.c, th), ps = MathUtils.Position(s.c, ts);
                        if (math.abs(ph.y - ps.y) >= 4f) m_Sep.Add(new Sep { H = h.e, S = s.e, tH = th, tS = ts, P = ps.y < ph.y ? ps : ph, HighwayOver = ph.y > ps.y });
                    }
            return m_Sep;
        }

        static Sep Nearest(List<Sep> list, float3 pos)
        {
            Sep o = list[0]; float bd = float.MaxValue;
            foreach (var l in list) { float d = math.distance(l.P.xz, pos.xz); if (d < bd) { bd = d; o = l; } }
            return o;
        }

        static bool Cross2D(Bezier4x3 a, Bezier4x3 b, out float ta, out float tb)
        {
            const int N = 16; ta = tb = 0;
            float2 alo = math.min(math.min(a.a.xz, a.b.xz), math.min(a.c.xz, a.d.xz)), ahi = math.max(math.max(a.a.xz, a.b.xz), math.max(a.c.xz, a.d.xz));
            float2 blo = math.min(math.min(b.a.xz, b.b.xz), math.min(b.c.xz, b.d.xz)), bhi = math.max(math.max(b.a.xz, b.b.xz), math.max(b.c.xz, b.d.xz));
            if (math.any(ahi < blo) || math.any(bhi < alo)) return false;
            for (int i = 0; i < N; i++)
            {
                float2 a0 = MathUtils.Position(a, i / (float)N).xz, a1 = MathUtils.Position(a, (i + 1) / (float)N).xz;
                for (int j = 0; j < N; j++)
                {
                    float2 b0 = MathUtils.Position(b, j / (float)N).xz, b1 = MathUtils.Position(b, (j + 1) / (float)N).xz;
                    float2 r = a1 - a0, s = b1 - b0; float den = r.x * s.y - r.y * s.x;
                    if (math.abs(den) < 1e-6f) continue;
                    float2 q = b0 - a0; float u = (q.x * s.y - q.y * s.x) / den, v = (q.x * r.y - q.y * r.x) / den;
                    if (u < 0 || u > 1 || v < 0 || v > 1) continue;
                    ta = (i + u) / N; tb = (j + v) / N; return true;
                }
            }
            return false;
        }

        float3 TravelDir(Entity edge) => math.normalizesafe(MathUtils.Tangent(EntityManager.GetComponentData<Curve>(edge).m_Bezier, 0.5f));

        /* the crossings of this street by both carriageways (the one hovered first) */
        List<Sep> Carriageways(List<Sep> list, float3 pos)
        {
            var o = Nearest(list, pos);
            var sides = new List<Sep> { o };
            if (!BothCarriageways) return sides;
            float3 d1 = TravelDir(o.H); float bd = 150f; bool found = false; Sep o2 = default;
            foreach (var l in list)
            {
                if (l.H == o.H) continue;
                float d = math.distance(l.P.xz, o.P.xz);
                if (d < bd && math.dot(TravelDir(l.H).xz, d1.xz) < -0.3f) { bd = d; o2 = l; found = true; }
            }
            if (found) sides.Add(o2);
            return sides;
        }

        /* one carriageway through a grade-separated crossing, in the direction of travel */
        Plan ChainThrough(Sep o, out string why, ref TerrainHeightData heights)
        {
            why = "";
            if (!Live(o.H) || !Live(o.S)) { why = "the road has just changed; hover again"; return null; }
            var p = new Plan { Dir = 1, StreetHalf = math.max(6f, WidthOf(o.S) * 0.5f), HighwayHalf = WidthOf(o.H) * 0.5f };
            var he = EntityManager.GetComponentData<Edge>(o.H);
            var back = Follow(o.H, false, 1500f);
            var fwd = Follow(o.H, true, 1500f);
            float s = 0;
            for (int i = back.Count - 1; i >= 0; i--) { back[i].S0 = s; p.Segs.Add(back[i]); s += back[i].Length; }
            var hs = MakeSeg(o.H, he.m_Start); hs.S0 = s; p.Segs.Add(hs);
            p.Cross = s + LengthAt(hs, o.tH);
            s += hs.Length;
            foreach (var f in fwd) { f.S0 = s; p.Segs.Add(f); s += f.Length; }
            foreach (var sg in p.Segs) p.Edges.Add(sg.Edge);
            p.Total = s;
            // where the highway is at ground level on each side (right at the crossing if the street goes over)
            p.Start = float.NaN; p.End = float.NaN;
            for (float x = p.Cross; x >= 0; x -= 5f) if (AboveGround(p, x, ref heights) < 0.6f) { p.Start = x; break; }
            for (float x = p.Cross; x <= s; x += 5f) if (AboveGround(p, x, ref heights) < 0.6f) { p.End = x; break; }
            // a viaduct that never comes down: the ramps leave it up there and come down beside it
            if (float.IsNaN(p.Start)) p.Start = p.Cross;
            if (float.IsNaN(p.End)) p.End = p.Cross;
            float sw = WidthOf(o.S);
            if (sw >= 24f) p.StreetClass = "major arterial"; else if (sw >= 16f) p.StreetClass = "arterial";
            p.RampLanes = RampLanes == 2 ? 2 : RampLanes == 1 ? 1 : sw >= 24f ? 2 : 1;      // 0 = auto
            return p;
        }

        /* the carriageway beyond one edge, following the traffic (forward) or against it (back); segments run with the traffic */
        List<Seg> Follow(Entity start, bool forward, float maxLen)
        {
            var list = new List<Seg>(); Entity cur = start; float total = 0;
            for (int guard = 0; guard < 200 && total < maxLen; guard++)
            {
                var ce = EntityManager.GetComponentData<Edge>(cur); var cc = EntityManager.GetComponentData<Curve>(cur).m_Bezier;
                Entity node = forward ? ce.m_End : ce.m_Start;
                float3 dir = forward ? MathUtils.EndTangent(cc) : -MathUtils.StartTangent(cc);
                Classify(node, m_Hw, m_Other, out _);
                Entity next = Entity.Null; float best = 0.7f;
                foreach (var h in m_Hw)
                {
                    if (h == cur) continue;
                    var he = EntityManager.GetComponentData<Edge>(h); var hc = EntityManager.GetComponentData<Curve>(h).m_Bezier;
                    if (forward ? he.m_Start != node : he.m_End != node) continue;   // must carry the same traffic on
                    float3 hd = forward ? MathUtils.StartTangent(hc) : -MathUtils.EndTangent(hc);
                    float d = math.dot(math.normalizesafe(dir.xz), math.normalizesafe(hd.xz));
                    if (d > best) { best = d; next = h; }
                }
                if (next == Entity.Null) break;
                var seg = MakeSeg(next, EntityManager.GetComponentData<Edge>(next).m_Start);
                list.Add(seg);
                total += seg.Length; cur = next;
            }
            return list;
        }

        float AboveGround(Plan p, float s, ref TerrainHeightData heights)
        {
            float3 q = Position(p, s);
            return q.y - TerrainUtils.SampleHeight(ref heights, q);
        }

        /*
         * Ramps leave and join only where the highway is level (the author, 2026-11-01: "the game hates when you try to
         * ramp to a piece that is elevating ... janky visual glitches"): within LevelRun either way of s it neither
         * climbs off the ground nor rises or falls more than 0.6 m. Following the lie of the land counts as level.
         */
        const float LevelRun = 30f;
        bool HighwayLevel(Plan p, float s, ref TerrainHeightData heights)
        {
            if (s - LevelRun < 1f || s + LevelRun > p.Total - 1f) return false;
            float h = AboveGround(p, s, ref heights), y = Position(p, s).y;
            bool flatAbove = true, flatY = true;
            foreach (float d in new[] { -LevelRun, -LevelRun / 2, LevelRun / 2, LevelRun })
            {
                flatAbove &= math.abs(AboveGround(p, s + d, ref heights) - h) < 0.6f;
                flatY &= math.abs(Position(p, s + d).y - y) < 0.6f;
            }
            return flatAbove || flatY;
        }

        /* ================= ramps ================= */

        public class Attach
        {
            public Entity Entity = Entity.Null; public float Split; public float3 Pos; public float Elevation;
            public Entity Street = Entity.Null; public float StreetT;   // FindJunction: the street piece it lies on (Entity may be that piece's node)
            public float S = float.NaN;                                 // HighwayAttach: where along the plan it ended up
        }

        /*
         * Where a ramp leaves or joins the highway, the game draws a long gore (the junction's footprint),
         * and every highway piece meeting there must be longer than that footprint, or its edges fold over
         * and the game shows "invalid shape" on it, even on an existing piece upstream. So the ramp slides
         * along the highway (preferably away from the crossing, which only lengthens it) to the nearest
         * point where it can split a piece leaving GoreClear on both sides, or meet a plain joint between two
         * long pieces. Null when there is no such point within reach.
         */
        class SideRamps { public Plan P; public Entity Ramp; public float Offset, Approach; public Attach Leave, Join, EndOff, StartOn; public bool CurvedIn; }

        /*
         * A diamond's (or SPUI's) four ramps should be the same length (the author, 2026-10-23). Each ramp first finds its
         * own spot clear of short highway pieces, which on an uneven highway can leave one 60 m shorter or longer
         * than the rest. Then: try each distance one of them ended up at, and use the one nearest the ideal at
         * which all four fit (within a few metres); if none does, each keeps its own.
         */
        void EqualiseRamps(List<SideRamps> sides)
        {
            if (sides.Count == 0) return;
            float ideal = 0; var tries = new List<float>();
            foreach (var r in sides)
            {
                ideal = math.max(ideal, math.max(r.P.Cross - r.P.Diverge, r.P.Merge - r.P.Cross));
                tries.Add(r.P.Cross - r.Leave.S); tries.Add(r.Join.S - r.P.Cross);
            }
            // and every 5 m between and a little beyond them: the level-highway rule (2026-11-01) can leave one ramp
            // just past a short piece, where none of the others' distances fit it
            float lo = float.MaxValue, hi = 0; foreach (float t in tries) { lo = math.min(lo, t); hi = math.max(hi, t); }
            for (float t = lo; t <= hi + 60f; t += 5f) tries.Add(t);
            tries.Sort((a, b) => math.abs(a - ideal).CompareTo(math.abs(b - ideal)));
            foreach (float d in tries)
            {
                var found = new List<(Attach leave, Attach join)>();
                foreach (var r in sides)
                {
                    var l = HighwayAttach(r.P, r.P.Cross - d, 6f); var j = HighwayAttach(r.P, r.P.Cross + d, 6f);
                    if (l == null || j == null) break;
                    found.Add((l, j));
                }
                if (found.Count != sides.Count) continue;
                for (int i = 0; i < sides.Count; i++) { sides[i].Leave = found[i].leave; sides[i].Join = found[i].join; }
                return;
            }
        }

        Attach HighwayAttach(Plan p, float s0, float maxShift = 200f)
        {
            float pref = s0 < p.Cross ? -1f : 1f;
            var heights = m_TerrainSystem.GetHeightData(false);
            // nearest first, both ways (away from the crossing wins a tie, and may go further): sliding only ever
            // away stretched some ramps by up to 200 m and left the four unequal (the author, 2026-10-23)
            var shifts = new List<float> { 0f };
            for (int k = 1; k <= 20; k++) { shifts.Add(pref * 5f * k); if (k <= 6) shifts.Add(-pref * 5f * k); }    // toward the street: 30 m at most (it made short, sharp ramps)
            for (int k = 11; k <= 20; k++) shifts.Add(pref * 10f * k);
            foreach (float d in shifts)
            {
                if (math.abs(d) > maxShift) continue;
                float s = s0 + d;
                if (s < 1f || s > p.Total - 1f) continue;
                if (!HighwayLevel(p, s, ref heights)) continue;
                var sg = SegAt(p, s);
                float tc = TAt(sg, s - sg.S0);
                float param = sg.Forward ? tc : 1 - tc;
                var cv = EntityManager.GetComponentData<Curve>(sg.Edge);
                var ed = EntityManager.GetComponentData<Edge>(sg.Edge);
                float before = param * cv.m_Length, after = cv.m_Length - before;
                if (before >= Splits.GoreClear && after >= Splits.GoreClear)
                    return new Attach { Entity = sg.Edge, Split = param, Pos = MathUtils.Position(cv.m_Bezier, param), S = s };
                Entity n = before < after ? ed.m_Start : ed.m_End;
                if (math.min(before, after) < 15f && PlainLongJoint(n) && HighwayLevel(p, before < after ? s - before : s + after, ref heights))
                    return new Attach { Entity = n, Pos = NodePos(n), S = s };
            }
            return null;
        }

        /* a node where exactly two highway pieces meet, both long enough for a ramp's gore */
        bool PlainLongJoint(Entity n)
        {
            if (!EntityManager.HasBuffer<ConnectedEdge>(n)) return false;
            var legs = EntityManager.GetBuffer<ConnectedEdge>(n, true);
            int hw = 0;
            for (int i = 0; i < legs.Length; i++)
            {
                var e = legs[i].m_Edge;
                if (!IsHighway(e)) return false;
                if (EntityManager.GetComponentData<Curve>(e).m_Length < Splits.GoreClear) return false;
                hw++;
            }
            return hw == 2;
        }

        /* a point on the existing highway as an edge split, or its node when right at one: ramps join like a player-drawn ramp */
        const string ShortPiecesWhy = "the highway is cut into short pieces where the ramps would leave or join it, and the game would fold them (invalid shape); try a nearby crossing, or redraw that stretch of highway as one piece (ramps also need the highway level where they meet it, not climbing onto a bridge)";

        /*
         * Where along a road piece of a given length a new road may split it: at least MinSplit metres from
         * either end, so neither leftover is a sliver. Returns 0 or 1 to mean "use that end's node instead".
         */
        const float MinSplit = Splits.MinSplit;
        static float SafeSplit(float length, float t) => Splits.Safe(length, t);

        // how far out the ramps run beside the highway, near the street: clear of it, as a player would draw them
        // (2026-10-23: 3 m / 12 m made ramps hug the highway; the author's hand-built ones stand 40-60 m out)
        float RampOffset(Plan p, Entity rampPrefab) => p.HighwayHalf + WidthOfPrefab(rampPrefab) * 0.5f + (Cfg.Size == 0 ? 16f : Cfg.Size == 2 ? 36f : 26f);

        /* along the street from parameter tFrom, outwards on the highway's outer side, to the point offset metres out */
        Attach FindJunction(Entity street, float tFrom, float3 x, float3 right, float offset, ref TerrainHeightData heights)
        {
            Entity edge = street; float t = tFrom;
            for (int hop = 0; hop < 4; hop++)
            {
                var cv = EntityManager.GetComponentData<Curve>(edge).m_Bezier;
                float up = math.dot(MathUtils.Position(cv, math.min(1, t + 0.02f)) - x, right);
                float down = math.dot(MathUtils.Position(cv, math.max(0, t - 0.02f)) - x, right);
                int sign = up >= down ? 1 : -1;
                for (int i = 1; i <= 64; i++)
                {
                    float u = t + sign * i / 64f;
                    if (u < 0 || u > 1) break;
                    float3 q = MathUtils.Position(cv, u);
                    if (math.dot(q - x, right) >= offset)
                    {
                        // a junction split must leave no sliver: near a joint, use the joint; otherwise keep 30 m clear
                        float len = EntityManager.GetComponentData<Curve>(edge).m_Length;
                        var en = EntityManager.GetComponentData<Edge>(edge);
                        float ground = TerrainUtils.SampleHeight(ref heights, q);
                        if (u * len < 15f) return new Attach { Entity = en.m_Start, Pos = NodePos(en.m_Start), Elevation = NodeElevation(en.m_Start), Street = edge, StreetT = 0f };
                        if ((1f - u) * len < 15f) return new Attach { Entity = en.m_End, Pos = NodePos(en.m_End), Elevation = NodeElevation(en.m_End), Street = edge, StreetT = 1f };
                        float su = SafeSplit(len, u);
                        if (su <= 0f || su >= 1f)
                        {
                            Entity snap = su <= 0f ? en.m_Start : en.m_End;
                            float3 np = NodePos(snap);
                            if (math.dot(np - x, right) >= math.max(12f, offset * 0.65f))
                                return new Attach { Entity = snap, Pos = np, Elevation = NodeElevation(snap), Street = edge, StreetT = su <= 0f ? 0f : 1f };
                            break;
                        }
                        q = MathUtils.Position(cv, su);
                        float ej = q.y - TerrainUtils.SampleHeight(ref heights, q);
                        if (math.abs(ej) < 0.05f) ej = 0f;
                        return new Attach { Entity = edge, Split = su, Pos = q, Elevation = ej, Street = edge, StreetT = su };
                    }
                }
                var ed = EntityManager.GetComponentData<Edge>(edge);
                Entity node = sign > 0 ? ed.m_End : ed.m_Start;
                float3 dir = sign > 0 ? MathUtils.EndTangent(cv) : -MathUtils.StartTangent(cv);
                Classify(node, m_Hw, m_Other, out _);
                Entity next = Entity.Null; float best = 0.5f;
                foreach (var o in m_Other)
                {
                    if (o == edge) continue;
                    var oc = EntityManager.GetComponentData<Curve>(o).m_Bezier; var oe = EntityManager.GetComponentData<Edge>(o);
                    float3 od = oe.m_Start == node ? MathUtils.StartTangent(oc) : -MathUtils.EndTangent(oc);
                    float d = math.dot(math.normalizesafe(dir.xz), math.normalizesafe(od.xz));
                    if (d > best) { best = d; next = o; }
                }
                if (next == Entity.Null) return null;
                edge = next; t = EntityManager.GetComponentData<Edge>(next).m_Start == node ? 0f : 1f;
            }
            return null;
        }

        /* the street level at a junction: no more than 0.6 m up or down within 15 m along it either way */
        bool StreetLevelAt(Attach a, ref TerrainHeightData heights)
        {
            if (a.Street == Entity.Null) return true;
            var cv = EntityManager.GetComponentData<Curve>(a.Street);
            float len = math.max(1f, cv.m_Length);
            float Elev(float u, ref TerrainHeightData hd) { var q = MathUtils.Position(cv.m_Bezier, math.saturate(u)); return q.y - TerrainUtils.SampleHeight(ref hd, q); }
            float e = Elev(a.StreetT, ref heights);
            foreach (float d in new[] { -15f, -7.5f, 7.5f, 15f })
                if (math.abs(Elev(a.StreetT + d / len, ref heights) - e) > 0.6f) return false;
            return true;
        }

        float3 Beside(Plan p, float s, float offset, ref TerrainHeightData heights)
        {
            float3 c = Position(p, s);
            return Ground(c + Right(p, s) * offset, ref heights);
        }

        /* streets crossing the highway at ground level where ramps run: closed off (local) or a reason to stop */
        bool RampZoneClear(Plan p, float a0, float a1, float b0, float b1, out string why)
        {
            why = "";
            foreach (var sg in p.Segs)
            {
                float at = sg.S0 + sg.Length;
                bool inRamps = (at > a0 && at < a1) || (at > b0 && at < b1);
                if (!inRamps || !IsCrossing(sg.To)) continue;
                float w = 0; foreach (var x in m_Other) w = math.max(w, WidthOf(x));
                if (CloseLocalStreets && w < 16f) { if (!p.Close.Contains(sg.To)) p.Close.Add(sg.To); continue; }
                why = w >= 16f ? $"an arterial crosses the highway where a ramp has to run, {(int)math.abs(at - p.Cross)} m away"
                    : $"a street crosses the highway where a ramp has to run, {(int)math.abs(at - p.Cross)} m away (turn on Close local streets)";
                return false;
            }
            return true;
        }

        /* does any ramp cross another street at ground level? (closed-off streets and the ramps' own street excepted) */
        bool RampsClear(List<Bezier4x3> ramps, HashSet<Entity> ignore, out string why)
        {
            why = "";
            if (ramps.Count == 0) return true;
            float2 rlo = ramps[0].a.xz, rhi = rlo;
            foreach (var r in ramps) { rlo = math.min(rlo, math.min(math.min(r.a.xz, r.b.xz), math.min(r.c.xz, r.d.xz))); rhi = math.max(rhi, math.max(math.max(r.a.xz, r.b.xz), math.max(r.c.xz, r.d.xz))); }
            rlo -= 20f; rhi += 20f;
            foreach (var e in RoadsNear(rlo, rhi))
                {
                    if (!Live(e) || ignore.Contains(e) || IsHighway(e)) continue;
                    var c = EntityManager.GetComponentData<Curve>(e).m_Bezier;
                    foreach (var r in ramps)
                    {
                        if (Cross2D(r, c, out float tr, out float tc) && math.abs(MathUtils.Position(r, tr).y - MathUtils.Position(c, tc).y) < 5f)
                        {
                            why = $"a ramp would cross {NameOf(e) ?? "another street"} at ground level (it would need closing or a bridge)";
                            Log.Info($"Ramp crossing: {NameOf(e)} at {MathUtils.Position(r, tr)}");
                            return false;
                        }
                    }
                }
            foreach (var tr in TracksNear(rlo, rhi))
            {
                if (!Live(tr) || ignore.Contains(tr) || !EntityManager.HasComponent<Curve>(tr)) continue;
                var c = EntityManager.GetComponentData<Curve>(tr).m_Bezier;
                foreach (var r in ramps)
                {
                    if (Cross2D(r, c, out float trT, out float tcT) && math.abs(MathUtils.Position(r, trT).y - MathUtils.Position(c, tcT).y) < 5f)
                    {
                        why = "a ramp would cross a railway track at ground level";
                        Log.Info($"Ramp railway crossing at {MathUtils.Position(r, trT)}");
                        return false;
                    }
                }
            }
            return true;
        }

        /* ================= service interchange styles ================= */

        /// <summary>How far the flat deck of a street bridge reaches past the highway's edge: room for the ramp junctions.</summary>
        float DeckMargin => Mode == ToolMode.Overpass ? 12f : Mode == ToolMode.Dumbbell ? 2f * RingRadius + 30f
            : Mode == ToolMode.Frontage ? WidthOfPrefab(FrontagePrefab()) + (Size == 0 ? 22f : Size == 2 ? 36f : 28f) + 8f : Compact ? 26f : 40f;

        string StyleName(ToolMode m) => m == ToolMode.Frontage ? "frontage-road" : m == ToolMode.Dumbbell ? "dumbbell" : m == ToolMode.Auto ? "best-fit" : m == ToolMode.Spui ? "single-point (SPUI)" : "diamond";

        Preview PreviewFor(ToolMode style, List<Sep> list, float3 pos) => style == ToolMode.Auto ? BestFitPreview(list, pos) : ServicePreview(style, list, pos);

        /* diamond or SPUI: one pair of ramps per carriageway, joining the highway like player-drawn ramps */
        Preview ServicePreview(ToolMode style, List<Sep> list, float3 pos)
        {
            string what = $"Can't build a {StyleName(style)} interchange here";
            var heights = m_TerrainSystem.GetHeightData(false);
            var sides = Carriageways(list, pos);
            var pv = new Preview();
            var deleted = new HashSet<Entity>();
            var ignore = new HashSet<Entity>();
            var curves = new List<Bezier4x3>();
            int ramps = 0, closed = 0; string kind = "";
            bool slopedStreet = false;
            bool streetOver = !sides[0].HighwayOver;
            if (style == ToolMode.Dumbbell && sides.Count != 2)
                return FailFinal(what, "a dumbbell needs both carriageways; enable Both carriageways at a divided highway");
            string existing = ExistingRamps(sides);
            if (existing != null) return FailFinal(what, existing);
            var terminals = new List<float3>();
            var planned = new List<SideRamps>();
            Attach center = null;
            if (style == ToolMode.Spui)
            {
                center = CenterOf(sides, ref heights);
                if (center == null) return Fail(what, "couldn't find the middle of the street over the highway");
                ignore.Add(center.Entity);
            }
            foreach (var o in sides)
            {
                var p = ChainThrough(o, out string why, ref heights);
                if (p == null) return Fail(what, why);
                Entity ramp = RampPrefab(p.RampLanes);
                if (ramp == Entity.Null) return Fail(what, "no highway ramp road type found");
                float offset = RampOffset(p, ramp);
                float approach = p.StreetHalf + 18f;
                // a roundabout's ramps meet it in line, a little before and after the street
                if (style == ToolMode.Dumbbell) approach = RingRadius + 15f;
                // SPUI: start turning in early enough that the ramp sweeps round to the middle instead of kinking into it
                if (style == ToolMode.Spui)
                    approach = math.max(approach, 1.2f * (offset - math.dot(center.Pos - Position(p, p.Cross), Right(p, p.Cross))));
                Attach endOff, startOn;
                bool curvedIn = false;
                if (style == ToolMode.Spui) { endOff = startOn = center; curvedIn = true; }
                else
                {
                    // a roundabout sits close beside the highway (about 12 m clear), not out beyond the ramp line
                    float ringAt = math.max(offset, p.HighwayHalf + RingRadius + 12f);
                    var junction = FindJunction(o.S, o.tS, o.P, Right(p, p.Cross), style == ToolMode.Dumbbell ? ringAt : style == ToolMode.Frontage ? FrontageOffset(p) : offset, ref heights);
                    if (junction == null) return Fail(what, "the street is too short on the outer side for the ramp junction");
                    // the ramps (or frontage) meet the street where it is level: a little further out if it is still sloping there
                    if (style == ToolMode.Exit || style == ToolMode.Frontage)
                    {
                        float want = style == ToolMode.Frontage ? FrontageOffset(p) : offset;
                        for (float add = 8f; add <= 64f && !StreetLevelAt(junction, ref heights); add += 8f)
                        {
                            var c = FindJunction(o.S, o.tS, o.P, Right(p, p.Cross), want + add, ref heights);
                            if (c == null) break;
                            if (StreetLevelAt(c, ref heights)) junction = c;
                        }
                        if (!StreetLevelAt(junction, ref heights)) slopedStreet = true;
                    }
                    ignore.Add(junction.Entity); ignore.Add(junction.Street);
                    if (EntityManager.HasBuffer<ConnectedEdge>(junction.Entity))   // at a joint: every street piece meeting there is ours to touch
                    { var legs = EntityManager.GetBuffer<ConnectedEdge>(junction.Entity, true); for (int k = 0; k < legs.Length; k++) ignore.Add(legs[k].m_Edge); }
                    endOff = startOn = junction;
                    if (style == ToolMode.Dumbbell)
                    {
                        bool placed = false;
                        why = "no safe position for the roundabout terminal";
                        // Move outward rather than creating tiny remnants at existing street nodes.
                        for (int shift = 0; shift <= 6; shift++)
                        {
                            var candidate = FindJunction(o.S, o.tS, o.P, Right(p, p.Cross), ringAt + shift * 12f, ref heights);
                            if (candidate == null) continue;
                            if (terminals.Exists(t => math.distance(t.xz, candidate.Pos.xz) < 2f * RingRadius + 24f)) continue;
                            if (!WriteRoundabout(pv, candidate, Flat(Tangent(p, p.Cross)), deleted, ignore, ref heights, curves, out endOff, out startOn, out why)) continue;
                            junction = candidate;
                            placed = true; break;
                        }
                        if (!placed) return Fail(what, why);
                    }
                    terminals.Add(junction.Pos);
                }
                // frontage: the slip ramps meet the frontage road well before the cross street, where it is level
                if (style == ToolMode.Frontage) approach = FrontageJoin(p, endOff.Elevation);
                float climbTo = style == ToolMode.Frontage ? FrontageElevation(endOff.Elevation, approach) : math.max(endOff.Elevation, startOn.Elevation);
                if (!PlaceRampEnds(p, style == ToolMode.Frontage ? approach + FrontageRampRun(p) - 40f : approach, climbTo, ref heights, out why)) return Fail(what, why);
                if (!RampZoneClear(p, p.Diverge, p.Cross - approach, p.Cross + approach, p.Merge, out why)) return Fail(what, why);
                closed += CloseStreets(pv, p, deleted, ignore);
                var leave = HighwayAttach(p, p.Diverge); var join = HighwayAttach(p, p.Merge);
                if (leave == null || join == null) return Fail(what, ShortPiecesWhy);
                planned.Add(new SideRamps { P = p, Ramp = ramp, Offset = offset, Leave = leave, Join = join, EndOff = endOff, StartOn = startOn, Approach = approach, CurvedIn = curvedIn });
                ignore.Add(o.S);
                kind = p.StreetClass;
            }
            EqualiseRamps(planned);
            foreach (var r in planned)
            {
                if (style == ToolMode.Frontage) WriteFrontage(pv, r.P, r.Ramp, r.Leave, r.Join, r.EndOff, ref heights, curves);
                else WriteRamps(pv, r.P, r.Ramp, r.Offset, r.Leave, r.Join, r.EndOff, r.StartOn, r.Approach, r.CurvedIn, ref heights, curves);
                ramps += 2;
            }
            foreach (var e in deleted) ignore.Add(e);
            if (!RampsClear(curves, ignore, out string blocked)) return Fail(what, blocked);
            string where = style == ToolMode.Dumbbell ? $"at two roundabouts ({RingRadius * 2f:0} m centreline diameter)" : style == ToolMode.Spui ? "at one junction in the middle of the street"
                : style == ToolMode.Frontage ? "by way of a one-way frontage road on each side (its ends are left for you to carry on to the next street)" : "at a junction on each side";
            if (style == ToolMode.Exit && terminals.Count == 2)   // (a frontage stops at both junctions by design)
            {
                float gap = math.distance(terminals[0].xz, terminals[1].xz);
                if (gap < TightDiamond) pv.TightGap = gap;
            }
            pv.Log = $"{StyleName(style)} at a {kind} ({(streetOver ? "street over the highway" : "highway over the street")}), {ramps} ramps, {closed} street(s) closed"
                + (pv.TightGap > 0 ? $", tight: junctions {(int)pv.TightGap} m apart" : "");
            pv.Status = $"{char.ToUpper(StyleName(style)[0]) + StyleName(style).Substring(1)} interchange at this {kind}: {ramps} ramps meeting the street {where}"
                + (closed > 0 ? $", {closed} local street(s) closed off" : "") + ". The highway itself is not rebuilt. Click to build."
                + (pv.TightGap > 0 ? $" Note: the two junctions are only {(int)pv.TightGap} m apart, so traffic will stop twice; a single-point (SPUI) avoids that." : "")
                + (slopedStreet ? " Note: the street is still sloping off its bridge where the ramps meet it, which the game can draw with glitches; a street with a longer flat bridge deck avoids that." : "");
            if (slopedStreet) pv.Log += ", ramps meet the street on its slope";
            return pv;
        }

        /*
         * Where the ramps leave and rejoin the highway. Standard: long and gentle, well clear of the bridge.
         * Compact: as short as the climb to the street allows, swinging out quickly, and leaving even where the
         * highway has begun to rise (the ramp starts at its height and comes down beside it).
         */
        /// <summary>How far from the street a diamond's or SPUI's ramps join the highway, by Size (the author, 2026-10-23: "they still continue on a bit long").</summary>
        float RampReach => Cfg.Size == 0 ? 150f : Cfg.Size == 2 ? 260f : 200f;

        /*
         * Where the ramps leave and rejoin the highway: RampReach from the street, the same both ways (equal ramps),
         * and further out only where a ramp needs the room to change height (the highway up on its bridge, or the
         * street up on its), at about the gradient setting.
         */
        bool PlaceRampEnds(Plan p, float approach, float climbTo, ref TerrainHeightData heights, out string why)
        {
            why = "";
            float grade = math.max(Grade, 0.03f) * 0.9f;
            var hd = heights;                                   // (a local function can't use the ref parameter)
            float Need(int side)
            {
                for (float d = approach + 40f; d < 1500f; d += 5f)
                {
                    float s = p.Cross + side * d;
                    if (s < 5f || s > p.Total - 5f) return float.NaN;
                    float h = AboveGround(p, s, ref hd);
                    if (math.abs(h) < 0.05f) h = 0f;
                    float dh = math.abs(h - climbTo);
                    // reserve the initial highway gore run (~80 m) to stay flat at highway height so embankments never tear the gore
                    float goreFlat = dh > 0.5f ? 80f : 0f;
                    if (dh <= math.max(0f, d - approach - goreFlat) * grade && HighwayLevel(p, s, ref hd)) return d;
                }
                return float.NaN;
            }
            float dOff = Need(-1), dOn = Need(1);
            if (float.IsNaN(dOff) || float.IsNaN(dOn)) { why = "the highway is too short here for the ramps to join it"; return false; }
            float reach = math.max(RampReach, math.max(dOff, dOn));
            while (!HighwayLevel(p, p.Cross - reach, ref heights) || !HighwayLevel(p, p.Cross + reach, ref heights))
                if ((reach += 5f) > 1500f) { why = "the highway never levels out here for the ramps to leave and join it"; return false; }
            p.Diverge = p.Cross - reach; p.Merge = p.Cross + reach;
            if (p.Diverge < 5f || p.Merge > p.Total - 5f) { why = "the highway is too short here for the ramps to join it"; return false; }
            return true;
        }

        /* ramps already meeting this street near the crossing: an interchange is already here */
        string ExistingRamps(List<Sep> sides)
        {
            var o = sides[0];
            if (!Live(o.S)) return null;
            var ed = EntityManager.GetComponentData<Edge>(o.S);
            var seen = new HashSet<Entity>();
            foreach (var start in new[] { ed.m_Start, ed.m_End })
            {
                Entity at = start, prev = o.S; float dist = 0;
                for (int step = 0; step < 8 && dist < 220f; step++)
                {
                    if (!Live(at) || !seen.Add(at)) break;
                    Classify(at, m_Hw, m_Other, out _);
                    if (m_Hw.Count > 0)
                        return $"there is already an interchange here (ramps meet the street {(int)math.max(dist, math.distance(NodePos(at).xz, o.P.xz))} m from the highway). Bulldoze its ramps first to rebuild it in another style";
                    Entity next = Entity.Null;
                    foreach (var x in m_Other) if (x != prev) { next = x; break; }
                    if (next == Entity.Null) break;
                    dist += EntityManager.GetComponentData<Curve>(next).m_Length;
                    at = Other(next, at); prev = next;
                }
            }
            return null;
        }

        /* the ramps of one carriageway; they climb if the street they meet is up on a bridge */
        /*
         * A diamond's (or SPUI's) ramps, the way a player draws them well (2026-10-23 rethink, after the author's own
         * ramps): each leaves the highway angled slightly outwards and sweeps in one smooth arc out to the ramp
         * line, well clear of the highway, then runs straight and square into the street junction. The on-ramp
         * mirrors it. (Before: a parallel S-bend taper, a long straight hugging the highway, and a kink.)
         */
        /// <summary>
        /// Minimum leave/merge angle so a ramp clears the highway pavement within ~80 m instead of stretching into a
        /// 150–190 m single segment (which CS2 rejects as LongDistance or renders with distorted meshes).
        /// </summary>
        static float GoreAngle(float hwHalf, float rampHalf)
        {
            float clear = hwHalf + rampHalf + 1.5f;
            return math.asin(math.clamp(clear * 1.12f / 82f, math.sin(math.radians(10.5f)), math.sin(math.radians(16f))));
        }

        /// <summary>
        /// Builds a smooth, curvature-following chain of Bezier arcs between a highway gore and a target point beside
        /// the highway (diamond/SPUI/dumbbell approach or frontage merge). Keeps the gore piece under ~85 m and tracks
        /// curved highways via intermediate Beside() waypoints so long ramps never bowstring across the freeway.
        /// </summary>
        List<Bezier4x3> BuildRampCurveChain(Plan p, float sHwy, float3 hwyPos, float sTarget, float3 targetPos, float targetLat, float3 targetTan, bool isOff, float hwHalf, float rampHalf, ref TerrainHeightData heights)
        {
            float clear = hwHalf + rampHalf + 1.5f;
            float ang = GoreAngle(hwHalf, rampHalf);
            float3 tH = Flat(Tangent(p, sHwy)), rH = Right(p, sHwy);
            float3 hwyTan = isOff ? math.normalizesafe(tH * math.cos(ang) + rH * math.sin(ang))
                                  : math.normalizesafe(tH * math.cos(ang) - rH * math.sin(ang));
            float span = isOff ? (sTarget - sHwy) : (sHwy - sTarget);
            float goreRun = math.clamp(clear / math.sin(ang) * 1.05f, 65f, 84f);
            if (span < goreRun + 45f)
            {
                float len = math.distance(hwyPos.xz, targetPos.xz);
                float a = math.max(ang, math.clamp(math.atan2(math.max(0f, targetLat - hwHalf) * 1.5f, math.max(1f, len)), math.radians(10.5f), math.radians(18f)));
                float3 ht = isOff ? math.normalizesafe(tH * math.cos(a) + rH * math.sin(a))
                                  : math.normalizesafe(tH * math.cos(a) - rH * math.sin(a));
                return new List<Bezier4x3> { isOff ? NetUtils.FitCurve(hwyPos, ht, targetTan, targetPos) : NetUtils.FitCurve(targetPos, targetTan, ht, hwyPos) };
            }

            float dir = isOff ? 1f : -1f;
            float sGore = sHwy + dir * goreRun;
            float latGore = math.min(targetLat, math.max(clear + 4.5f, math.lerp(clear + 4f, targetLat, 0.30f)));
            float rem = math.max(1f, span - goreRun);
            int mids = math.max(0, (int)math.floor(rem / 120f));

            // collect waypoints ordered from highway gore -> target, then reverse if on-ramp
            var pts = new List<(float3 pos, float3 tan)>();
            pts.Add((hwyPos, hwyTan));
            int totalSteps = mids + 1;
            for (int k = 0; k < totalSteps; k++)
            {
                float u = k / (float)totalSteps;
                float s = math.lerp(sGore, sTarget, u);
                float lat = math.lerp(latGore, targetLat, math.smoothstep(0f, 1f, u));
                float dLatDs = (targetLat - latGore) * (k == 0 ? 1.15f : 6f * u * (1f - u)) / rem;
                float slope = math.clamp(dLatDs, 0f, 0.24f);
                float3 ts = Flat(Tangent(p, s)), rs = Right(p, s);
                float3 tan = math.normalizesafe(ts + rs * (isOff ? slope : -slope));
                pts.Add((Beside(p, s, lat, ref heights), tan));
            }
            pts.Add((targetPos, targetTan));
            if (!isOff) pts.Reverse();

            var parts = new List<Bezier4x3>();
            for (int i = 0; i + 1 < pts.Count; i++)
                parts.Add(NetUtils.FitCurve(pts[i].pos, pts[i].tan, pts[i + 1].tan, pts[i + 1].pos));
            return parts;
        }

        void WriteRamps(Preview pv, Plan p, Entity rampPrefab, float offset, Attach off, Attach on, Attach endOff, Attach startOn, float approach, bool curvedIn, ref TerrainHeightData heights, List<Bezier4x3> curves)
        {
            float sOff = float.IsNaN(off.S) ? p.Diverge : off.S, sOn = float.IsNaN(on.S) ? p.Merge : on.S;
            float rampHalf = WidthOfPrefab(rampPrefab) * 0.5f;
            // a diamond's ramps run straight into their junction, wherever it settled on the street;
            // project each junction along the highway axis too so skewed cross streets never collapse the approach
            float3 cp = Position(p, p.Cross), cr = Right(p, p.Cross), tc = Flat(Tangent(p, p.Cross));
            float latOff = curvedIn ? offset : math.max(p.HighwayHalf + 10f, math.dot(endOff.Pos - cp, cr));
            float latOn = curvedIn ? offset : math.max(p.HighwayHalf + 10f, math.dot(startOn.Pos - cp, cr));
            float sEnd = curvedIn ? p.Cross : math.clamp(p.Cross + math.dot(endOff.Pos - cp, tc), sOff + approach + 40f, p.Total - 10f);
            float sStart = curvedIn ? p.Cross : math.clamp(p.Cross + math.dot(startOn.Pos - cp, tc), 10f, sOn - approach - 40f);
            float sOffNear = sEnd - approach, sOnNear = sStart + approach;
            float3 offNear = Beside(p, sOffNear, latOff, ref heights);
            float3 onNear = Beside(p, sOnNear, latOn, ref heights);
            float3 tOffNear = Flat(Tangent(p, sOffNear)), tOnNear = Flat(Tangent(p, sOnNear));
            offset = math.max(latOff, latOn);
            float e1 = endOff.Elevation, e2 = startOn.Elevation;
            // a ramp leaves at the highway's own height (viaduct, ground, or trench) and changes height evenly to the street
            float eOff = AboveGround(p, sOff, ref heights), eOn = AboveGround(p, sOn, ref heights);
            if (math.abs(eOff) < 0.05f) eOff = 0f;
            if (math.abs(eOn) < 0.05f) eOn = 0f;
            off.Elevation = eOff; on.Elevation = eOn;
            string dir = Bound(tc);

            // Phoenix style (Loop 202): the ramp tapers off the highway, runs straight beside it a couple of metres
            // from its edge, then flares out on a reverse curve to its junction (a SPUI's sweeps in to the middle from
            // there instead). Only where there's room between the gore and the street; otherwise the angled shape.
            float lane = p.HighwayHalf + rampHalf + 2f;
            if (TightRamps && curvedIn && offset - lane > 4f)
            {
                latOff = latOn = lane;
                offNear = Beside(p, sOffNear, lane, ref heights); onNear = Beside(p, sOnNear, lane, ref heights);
            }
            float flareOff = latOff - lane > 4f ? math.clamp(2.5f * (latOff - lane), 50f, 120f) : 0f;
            float flareOn = latOn - lane > 4f ? math.clamp(2.5f * (latOn - lane), 50f, 120f) : 0f;
            float runOff = (sOffNear - flareOff) - sOff, runOn = sOn - (sOnNear + flareOn);
            bool tightOff = TightRamps && (flareOff > 0f || curvedIn) && runOff > 70f;
            bool tightOn = TightRamps && (flareOn > 0f || curvedIn) && runOn > 70f;
            if (TightRamps && (!tightOff || !tightOn)) Log.Info($"Beside-highway ramps: not enough room for the {(tightOff ? "on" : "off")}-ramp ({(int)runOff} m / {(int)runOn} m between the gore and the flare; it needs 70), so it keeps the angled shape");

            BeginRamp(pv, $"the {dir} off-ramp");
            float3 tA = Flat(Tangent(p, sOff)), rA = Right(p, sOff);
            if (tightOff)
            {
                float sT = sOff + math.min(82f, 0.6f * runOff), sF = sOffNear - flareOff;
                var parts = new List<Bezier4x3>();
                float3 T = Beside(p, sT, lane, ref heights);
                parts.Add(NetUtils.FitCurve(off.Pos, math.normalizesafe(tA + rA * 0.08f), Flat(Tangent(p, sT)), T));
                int steps = math.max(1, (int)math.ceil((sF - sT) / 110f));
                float prevS = sT; float3 prevP = T;
                for (int k = 1; k <= steps; k++)
                {
                    float sk = math.lerp(sT, sF, k / (float)steps);
                    float3 pk = k == steps && flareOff <= 0f ? offNear : Beside(p, sk, lane, ref heights);
                    parts.Add(NetUtils.FitCurve(prevP, Flat(Tangent(p, prevS)), Flat(Tangent(p, sk)), pk));
                    prevS = sk; prevP = pk;
                }
                if (flareOff > 0f) parts.Add(NetUtils.FitCurve(prevP, Flat(Tangent(p, sF)), tOffNear, offNear));
                RampChain(pv, rampPrefab, parts, off, null, eOff, e1, tA, p.HighwayHalf, ref heights, curves);
            }
            else
            {
                var parts = BuildRampCurveChain(p, sOff, off.Pos, sOffNear, offNear, latOff, tOffNear, isOff: true, p.HighwayHalf, rampHalf, ref heights);
                RampChain(pv, rampPrefab, parts, off, null, eOff, e1, tA, p.HighwayHalf, ref heights, curves);
            }
            Ramp(pv, rampPrefab, Lift(curvedIn ? NetUtils.FitCurve(offNear, tOffNear, Flat(endOff.Pos - offNear), endOff.Pos) : Line(offNear, endOff.Pos), e1, e1, ref heights, endOff.Pos.y), null, endOff, e1, e1, curves);

            BeginRamp(pv, $"the {dir} on-ramp");
            float3 tB = Flat(Tangent(p, sOn)), rB = Right(p, sOn);
            Ramp(pv, rampPrefab, Lift(curvedIn ? NetUtils.FitCurve(startOn.Pos, Flat(onNear - startOn.Pos), tOnNear, onNear) : Line(startOn.Pos, onNear), e2, e2, ref heights, startOn.Pos.y), startOn, null, e2, e2, curves);
            if (tightOn)
            {
                float sT = sOn - math.min(82f, 0.6f * runOn), sF = sOnNear + flareOn;
                var parts = new List<Bezier4x3>();
                float3 F = flareOn > 0f ? Beside(p, sF, lane, ref heights) : onNear;
                if (flareOn > 0f) parts.Add(NetUtils.FitCurve(onNear, tOnNear, Flat(Tangent(p, sF)), F));
                int steps = math.max(1, (int)math.ceil((sT - sF) / 110f));
                float prevS = sF; float3 prevP = F;
                for (int k = 1; k <= steps; k++)
                {
                    float sk = math.lerp(sF, sT, k / (float)steps);
                    float3 pk = Beside(p, sk, lane, ref heights);
                    parts.Add(NetUtils.FitCurve(prevP, Flat(Tangent(p, prevS)), Flat(Tangent(p, sk)), pk));
                    prevS = sk; prevP = pk;
                }
                parts.Add(NetUtils.FitCurve(prevP, Flat(Tangent(p, sT)), math.normalizesafe(tB - rB * 0.08f), on.Pos));
                RampChain(pv, rampPrefab, parts, null, on, e2, eOn, tB, p.HighwayHalf, ref heights, curves);
            }
            else
            {
                var parts = BuildRampCurveChain(p, sOn, on.Pos, sOnNear, onNear, latOn, tOnNear, isOff: false, p.HighwayHalf, rampHalf, ref heights);
                RampChain(pv, rampPrefab, parts, null, on, e2, eOn, tB, p.HighwayHalf, ref heights, curves);
            }
            EndRamp();
        }

        static float3 Flat(float3 t) { t.y = 0; return math.normalizesafe(t); }

        /* a curve's ends set to the ground plus their elevations, the middle eased between (an exact end, if given, is kept) */
        static Bezier4x3 Lift(Bezier4x3 c, float e0, float e1, ref TerrainHeightData heights, float endY = float.NaN)
        {
            c.a.y = TerrainUtils.SampleHeight(ref heights, c.a) + e0;
            c.d.y = float.IsNaN(endY) ? TerrainUtils.SampleHeight(ref heights, c.d) + e1 : endY;
            if (math.abs(e0) < 0.05f && math.abs(e1) < 0.05f && float.IsNaN(endY))
            {
                c.b.y = TerrainUtils.SampleHeight(ref heights, c.b);
                c.c.y = TerrainUtils.SampleHeight(ref heights, c.c);
            }
            else
            {
                c.b.y = math.lerp(c.a.y, c.d.y, 1f / 3f);
                c.c.y = math.lerp(c.a.y, c.d.y, 2f / 3f);
            }
            return c;
        }

        /* a ramp made of several curves end to end: holds the highway gore piece completely flat at highway elevation
           so retaining walls / embankments never tear terrain at the gore, then changes height smoothly along the rest */
        void RampChain(Preview pv, Entity prefab, List<Bezier4x3> parts, Attach from, Attach to, float e0, float e1, float3 hwDir, float hwHalf, ref TerrainHeightData heights, List<Bezier4x3> curves)
        {
            var lens = new List<float>(); float total = 0;
            foreach (var c in parts) { float l = MathUtils.Length(c); lens.Add(l); total += l; }
            bool flatStart = parts.Count >= 2 && hwHalf > 0f && from != null && from.Entity != Entity.Null;
            bool flatEnd = parts.Count >= 2 && hwHalf > 0f && to != null && to.Entity != Entity.Null;
            float climbLen = math.max(1f, total - (flatStart ? lens[0] : 0f) - (flatEnd ? lens[parts.Count - 1] : 0f));
            float done = 0;
            for (int i = 0; i < parts.Count; i++)
            {
                float ea, eb;
                if (flatStart && i == 0) { ea = e0; eb = e0; }
                else if (flatEnd && i == parts.Count - 1) { ea = e1; eb = e1; }
                else
                {
                    ea = math.lerp(e0, e1, math.saturate(done / climbLen));
                    eb = math.lerp(e0, e1, math.saturate((done + lens[i]) / climbLen));
                    done += lens[i];
                }
                bool atHighway = from != null && i == 0 || to != null && i == parts.Count - 1;
                RampArc(pv, prefab, parts[i], i == 0 ? from : null, i == parts.Count - 1 ? to : null, ea, eb, hwDir, atHighway ? hwHalf : 0f, ref heights, curves);
            }
        }

        /* one long arc as pieces of at most MaxPiece, its height changing evenly along it; the ends keep their attachments */
        void RampArc(Preview pv, Entity prefab, Bezier4x3 arc, Attach from, Attach to, float e0, float e1, float3 hwDir, float hwHalf, ref TerrainHeightData heights, List<Bezier4x3> curves)
        {
            float len = MathUtils.Length(arc);
            // the highway end is the one attached to an existing road (a frontage end is only a meeting point)
            bool atStart = from != null && from.Entity != Entity.Null || to == null || to.Entity == Entity.Null;
            // Where the ramp has fully left the highway's pavement. No joint goes before that: the game fuses a joint
            // on the pavement into the highway as a junction (the author, 2026-10-31: "it spawned an extra joint").
            float3 root = atStart ? arc.a : arc.d, side = new float3(hwDir.z, 0, -hwDir.x);
            float clear = hwHalf + WidthOfPrefab(prefab) * 0.5f + 1f, tClear = atStart ? 1f : 0f;
            if (hwHalf <= 0f) tClear = atStart ? 0f : 1f;     // a piece away from the highway (a Phoenix flare)
            else for (int k = 0; k <= 64; k++)
            {
                float t = atStart ? k / 64f : 1f - k / 64f;
                if (math.abs(math.dot(MathUtils.Position(arc, t) - root, side)) >= clear) { tClear = t; break; }
            }
            // Until then the ramp keeps the highway's height (climbing straight away cut a notch of ground between
            // them at the gore); then it changes height evenly to the street's, no steeper than about MaxGrade.
            float run = len - math.abs(e1 - e0) / (MaxGrade * 0.8f);
            float hold = math.abs(e1 - e0) < 0.5f ? 0f : math.clamp((atStart ? tClear : 1f - tClear) * len, 0f, math.max(0f, run));
            float hStart = atStart ? hold / len : 0f, hEnd = atStart ? 1f : 1f - hold / len;
            float At(float t) => math.lerp(e0, e1, math.saturate((t - hStart) / (hEnd - hStart)));
            // joints: the first where the ramp is clear of the pavement, then pieces of at most MaxPiece (never leaving a < 14 m sliver)
            float first = atStart ? tClear : 1f - tClear;
            var cuts = new List<float> { 0f };
            void Span(float a, float b) { int m = math.max(1, (int)math.ceil((b - a) * len / MaxPiece)); for (int j = 1; j <= m; j++) cuts.Add(math.lerp(a, b, j / (float)m)); }
            if (hwHalf > 0f && (1f - first) * len < 14f)
            {
                if (len <= 105f) cuts.Add(1f); else Span(0f, 1f);
            }
            else if (first <= 0.02f || first >= 0.98f) Span(0f, 1f);
            else if (atStart) { cuts.Add(first); Span(first, 1f); }
            else { Span(0f, 1f - first); cuts.Add(1f); }
            int n = cuts.Count - 1;
            for (int i = 0; i < n; i++)
            {
                float t0 = cuts[i], t1 = cuts[i + 1];
                var piece = MathUtils.Cut(arc, new float2(t0, t1));
                if (i == 0) piece.a = arc.a;
                if (i == n - 1) piece.d = arc.d;
                float pe0 = At(t0), pe1 = At(t1);
                piece = Lift(piece, pe0, pe1, ref heights);
                if (i == 0 && from != null) piece.a.y = arc.a.y;       // exactly on the highway where it leaves
                if (i == n - 1 && to != null) piece.d.y = arc.d.y;     // ... and where it joins
                if (math.abs(pe0) >= 0.05f || math.abs(pe1) >= 0.05f)
                { piece.b.y = math.lerp(piece.a.y, piece.d.y, 1f / 3f); piece.c.y = math.lerp(piece.a.y, piece.d.y, 2f / 3f); }
                Ramp(pv, prefab, piece, i == 0 ? from : null, i == n - 1 ? to : null, pe0, pe1, curves);
            }
        }

        /* "eastbound" and so on: the way traffic runs along a direction */
        static string Bound(float3 travel) => Compass(travel) + "bound";

        /* SPUI: the point on the street midway between the carriageways (or over the highway's middle) */
        Attach CenterOf(List<Sep> sides, ref TerrainHeightData heights)
        {
            float3 mid = sides.Count > 1 ? (sides[0].P + sides[1].P) * 0.5f : sides[0].P;
            // the street pieces here, and their neighbours (the middle may sit right on a node between two of them)
            var cands = new HashSet<Entity>();
            foreach (var o in sides)
            {
                if (!Live(o.S)) continue;
                cands.Add(o.S);
                var ed = EntityManager.GetComponentData<Edge>(o.S);
                foreach (var n in new[] { ed.m_Start, ed.m_End })
                {
                    Classify(n, m_Hw, m_Other, out _);
                    foreach (var x in m_Other) cands.Add(x);
                }
            }
            Attach best = null; float bd = 20f;
            foreach (var e in cands)
            {
                if (!Live(e) || IsHighway(e)) continue;
                var cv = EntityManager.GetComponentData<Curve>(e).m_Bezier;
                float d = MathUtils.Distance(cv.xz, mid.xz, out float t);
                if (d >= bd) continue;
                bd = d;
                if (t < 0.03f || t > 0.97f)
                {
                    var ed = EntityManager.GetComponentData<Edge>(e);
                    Entity n = t < 0.5f ? ed.m_Start : ed.m_End;
                    best = new Attach { Entity = n, Pos = NodePos(n), Elevation = NodeElevation(n) };
                }
                else
                {
                    float3 q = MathUtils.Position(cv, t);
                    float ej = q.y - TerrainUtils.SampleHeight(ref heights, q);
                    if (math.abs(ej) < 0.05f) ej = 0f;
                    best = new Attach { Entity = e, Split = t, Pos = q, Elevation = ej };
                }
            }
            return best;
        }

        void Ramp(Preview pv, Entity prefab, Bezier4x3 curve, Attach from, Attach to, float e0, float e1, List<Bezier4x3> curves)
        {
            pv.Specs.Add(new Spec
            {
                Prefab = prefab, Curve = curve, E0 = e0, E1 = e1, Group = m_Group,
                StartEntity = from?.Entity ?? Entity.Null, StartSplit = from?.Split ?? 0, EndEntity = to?.Entity ?? Entity.Null, EndSplit = to?.Split ?? 0,
            });
            curves.Add(curve);
        }

        static Bezier4x3 Line(float3 a, float3 b) => NetUtils.StraightCurve(a, b);

        /*
         * Local streets that would cross a ramp are cut back to dead ends short of the highway, the way
         * real local streets end at a freeway. The short piece between two carriageways goes entirely.
         */
        int CloseStreets(Preview pv, Plan p, HashSet<Entity> deleted, HashSet<Entity> ignore)
        {
            int n = 0;
            Entity ramp = RampPrefab(p.RampLanes);
            float cut = p.HighwayHalf + (ramp != Entity.Null ? WidthOfPrefab(ramp) : 8f) + 14f;
            foreach (var node in p.Close)
            {
                Classify(node, m_Hw, m_Other, out _);
                foreach (var st in new List<Entity>(m_Other))
                {
                    if (!deleted.Add(st)) continue;
                    pv.Specs.Add(new Spec { Delete = true, Original = st });
                    var cv = EntityManager.GetComponentData<Curve>(st);
                    var ed = EntityManager.GetComponentData<Edge>(st);
                    Entity far = ed.m_Start == node ? ed.m_End : ed.m_Start;
                    Classify(far, m_Hw, m_Other, out _);
                    if (m_Hw.Count > 0 || cv.m_Length < cut + 15f) continue;
                    var sg = MakeSeg(st, far);
                    float tEnd = TAt(sg, cv.m_Length - cut);
                    var stub = MathUtils.Cut(sg.Curve, new float2(0, tEnd));
                    float ef = NodeElevation(far);
                    var spec = new Spec { Prefab = PrefabOf(st) };
                    if (sg.Forward) { spec.Curve = stub; spec.StartEntity = far; spec.E0 = ef; spec.E1 = ef; }
                    else { spec.Curve = MathUtils.Invert(stub); spec.EndEntity = far; spec.E0 = ef; spec.E1 = ef; }
                    if (EntityManager.HasComponent<Upgraded>(st)) { spec.HasUpgrade = true; spec.Upgrade = EntityManager.GetComponentData<Upgraded>(st).m_Flags; }
                    pv.Specs.Add(spec);
                }
                n++;
            }
            return n;
        }

        Entity RampPrefab(int lanes)
        {
            if (m_Ramp1 == Entity.Null || !EntityManager.Exists(m_Ramp1))
            {
                using (var ents = m_RoadPrefabs.ToEntityArray(Allocator.Temp))
                {
                    foreach (var e in ents)
                    {
                        string n = m_PrefabSystem.GetPrefabName(e);
                        if (n == null || !n.Contains("Highway") || !n.Contains("Oneway")) continue;
                        if (n.Contains("1 lane") && m_Ramp1 == Entity.Null) m_Ramp1 = e;
                        if (n.Contains("2 lanes") && m_Ramp2 == Entity.Null) m_Ramp2 = e;
                    }
                    if (m_Ramp1 == Entity.Null) m_Ramp1 = m_Ramp2;
                    if (m_Ramp2 == Entity.Null) m_Ramp2 = m_Ramp1;
                }
            }
            return lanes >= 2 ? m_Ramp2 : m_Ramp1;
        }

        /* ================= repairing stretches laid the wrong way by an earlier version ================= */

        bool IsOneway(Entity e) { string n = m_PrefabSystem.GetPrefabName(PrefabOf(e)); return n != null && n.Contains("Oneway"); }

        float NodeElevation(Entity n) => EntityManager.HasComponent<Elevation>(n) ? math.csum(EntityManager.GetComponentData<Elevation>(n).m_Elevation) * 0.5f : 0f;

        /* ================= names ================= */

        string NameOf(Entity edge)
        {
            if (!EntityManager.HasComponent<Aggregated>(edge)) return null;
            var agg = EntityManager.GetComponentData<Aggregated>(edge).m_Aggregate;
            return agg != Entity.Null && EntityManager.Exists(agg) ? m_NameSystem.GetRenderedLabelName(agg) : null;
        }


        /* ================= definitions ================= */

        public class Spec
        {
            public bool Delete; public Entity Original;
            public Entity Prefab; public Bezier4x3 Curve;
            public Entity StartEntity = Entity.Null, EndEntity = Entity.Null; public float StartSplit, EndSplit, E0, E1;
            public bool HasUpgrade; public CompositionFlags Upgrade;
            public bool JoinStart, JoinEnd;      // this end continues straight into another new piece
            public int Group;                    // 0: the core (bridge, street changes); 1+: one ramp, which can be left out on its own
            public Spec Clone() => (Spec)MemberwiseClone();
        }

        public class Preview
        {
            public List<Spec> Specs = new List<Spec>();
            public List<(float3 pos, string name, bool highway)> Names = new List<(float3, string, bool)>();
            public string Status = "", Log;
            public bool NextStep; public float3 NextPos; public ToolMode NextMode;
            public float TightGap;   // a diamond whose junctions are this close (0 = not tight)
            public bool NoFit;       // a failure no setting can fix (autofit doesn't try)
            public List<string> GroupNames = new List<string> { "" };   // ramp groups by number (Spec.Group)
        }

        /*
         * New pieces that meet end to end must meet at exactly the same point, and the meeting point must
         * not be flagged as the start or end of a course, or the game builds them as separate roads that
         * merely overlap (red, or with Anarchy, dead ends between every piece). This joins them the way the
         * game's own road tool joins the pieces of one drag.
         */
        public static void JoinPieces(Preview pv)
        {
            var pts = new List<(int spec, bool end)>();
            for (int i = 0; i < pv.Specs.Count; i++)
            {
                var s = pv.Specs[i]; if (s.Delete) continue;
                if (s.StartEntity == Entity.Null) pts.Add((i, false));
                if (s.EndEntity == Entity.Null) pts.Add((i, true));
            }
            float3 P(int k) { var s = pv.Specs[pts[k].spec]; return pts[k].end ? s.Curve.d : s.Curve.a; }
            float E(int k) { var s = pv.Specs[pts[k].spec]; return pts[k].end ? s.E1 : s.E0; }
            var root = new int[pts.Count]; for (int k = 0; k < root.Length; k++) root[k] = -1;
            var count = new int[pts.Count];
            for (int i = 0; i < pts.Count; i++)
            {
                if (root[i] >= 0) continue;
                root[i] = i; count[i] = 1;
                for (int j = i + 1; j < pts.Count; j++)
                    if (root[j] < 0 && math.distance(P(i), P(j)) < 0.75f) { root[j] = i; count[i]++; }
            }
            for (int k = 0; k < pts.Count; k++)
            {
                var s = pv.Specs[pts[k].spec]; float3 target = P(root[k]); float targetE = E(root[k]);
                if (pts[k].end) { float3 d = target - s.Curve.d; s.Curve.d = target; s.Curve.c += d; s.E1 = targetE; if (count[root[k]] == 2) s.JoinEnd = true; }
                else { float3 d = target - s.Curve.a; s.Curve.a = target; s.Curve.b += d; s.E0 = targetE; if (count[root[k]] == 2) s.JoinStart = true; }
            }
        }


    }
}
