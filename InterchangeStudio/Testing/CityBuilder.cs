// Interchange Studio - Testing/CityBuilder.cs
// Builds synthetic road networks for the planner, with the vanilla prefab names and widths the planner
// looks for. Roads are laid as chains of straight pieces (at most 80 m) and share a node wherever two
// roads cross at the same height, exactly like the game does at an at-grade crossing.
using System.Collections.Generic;
using Colossal.Mathematics;
using InterchangeStudio.Core;
using Unity.Mathematics;

namespace InterchangeStudio.Testing
{
    public sealed class CityBuilder
    {
        public readonly NetWorld World = new NetWorld();
        public readonly TestLog Log = new TestLog();
        public readonly Dictionary<string, Entity> Prefabs = new Dictionary<string, Entity>();
        readonly List<(float3 pos, Entity id)> m_Nodes = new List<(float3, Entity)>();
        readonly Dictionary<Entity, string> m_AggNames = new Dictionary<Entity, string>();

        public CityBuilder()
        {
            Prefab("Highway Oneway - 2 lanes", 15f, highway: true);
            Prefab("Highway Oneway - 1 lane", 8f, highway: true);
            Prefab("Highway Twoway - 2 lanes", 20f, highway: true);
            Prefab("Large Road", 30f, highway: false);
            Prefab("Medium Road", 20f, highway: false);
            Prefab("Small Road", 12f, highway: false);
            Prefab("Small Road Oneway", 8f, highway: false);
            Prefab("Alley Oneway", 8f, highway: false);
            Prefab("Medium Road Oneway", 14f, highway: false);
            Prefab("HarborGateRoadOneway02", 16f, highway: false);     // an add-on road (the author's game picked it for frontage)
            Prefab("Highway Oneway - 3 lanes", 12f, highway: true);
            Prefab("Highway Oneway - 4 lanes", 22f, highway: true);
            Prefab("Twoway Train Track", 10f, highway: false, road: false);
        }

        void Prefab(string name, float width, bool highway, bool road = true) => Prefabs[name] = World.AddPrefab(World.NewId(), name, width, highway, road);

        /// <summary>The node at a position (shared with any road already there), creating it if needed.</summary>
        public Entity NodeAt(float3 p, float elevation)
        {
            foreach (var n in m_Nodes) if (math.distance(n.pos, p) < 0.5f) return n.id;
            var id = World.AddNode(World.NewId(), p, math.abs(elevation) > 0.01f ? new float2(elevation) : (float2?)null);
            m_Nodes.Add((p, id));
            return id;
        }

        /// <summary>
        /// A road along a polyline (x, z, elevation above flat ground at y = 0), split into pieces at most
        /// maxPiece long plus a node at every extra break point given. One-way roads flow along the points.
        /// </summary>
        public List<Entity> Road(string prefab, string name, IReadOnlyList<float3> points, float maxPiece = 80f, IReadOnlyList<float2> breaks = null, bool track = false)
        {
            var agg = World.NewId();
            m_AggNames[agg] = name;
            var stations = new List<float3>();
            for (int i = 0; i + 1 < points.Count; i++)
            {
                float3 a = points[i], b = points[i + 1];
                float len = math.distance(a.xz, b.xz);
                var cuts = new List<float> { 0f, 1f };
                int n = (int)math.ceil(len / maxPiece);
                for (int k = 1; k < n; k++) cuts.Add(k / (float)n);
                if (breaks != null)
                    foreach (var br in breaks)
                    {
                        float2 ab = b.xz - a.xz; float u = math.dot(br - a.xz, ab) / math.lengthsq(ab);
                        if (u > 0.001f && u < 0.999f && math.distance(a.xz + ab * u, br) < 0.5f) cuts.Add(u);
                    }
                cuts.Sort();
                for (int k = 0; k < cuts.Count; k++)
                {
                    if (k > 0 && cuts[k] - cuts[k - 1] < 1e-4f) continue;
                    if (i > 0 && k == 0) continue;
                    stations.Add(math.lerp(a, b, cuts[k]));
                }
            }
            var edges = new List<Entity>();
            for (int i = 0; i + 1 < stations.Count; i++)
            {
                float3 a = stations[i], b = stations[i + 1];
                var na = NodeAt(new float3(a.x, a.y, a.z), a.y); var nb = NodeAt(new float3(b.x, b.y, b.z), b.y);
                var curve = NetUtils.StraightCurve(a, b);
                edges.Add(World.AddEdge(World.NewId(), na, nb, curve, MathUtils.Length(curve), Prefabs[prefab], track, null, agg));
            }
            return edges;
        }

        public NameSystem Names() => new NameSystem { Lookup = e => m_AggNames.TryGetValue(e, out var s) ? s : null };

        /// <summary>Water depth by position (none unless a scenario adds a lake).</summary>
        public System.Func<float3, float> Water = p => 0f;

        public Planner Planner(PlanConfig cfg)
        {
            var p = new Planner(World, new TerrainSystem { Terrain = new FlatTerrain(0f), WaterDepth = Water }, Names(), Log) { Cfg = cfg };
            return p;
        }

        static float3 P(float x, float z, float e = 0f) => new float3(x, e, z);

        // ---------------------------------------------------------------- scenarios

        /// <summary>A divided highway (carriageways 24 m apart) crossing a Large Road at ground level at the origin.</summary>
        public static CityBuilder AtGradeCrossing()
        {
            var c = new CityBuilder();
            var brk = new[] { new float2(0, -12), new float2(0, 12) };
            c.Road("Highway Oneway - 2 lanes", "Eastbound", new[] { P(-1200, -12), P(1200, -12) }, breaks: new[] { new float2(0, -12) });
            c.Road("Highway Oneway - 2 lanes", "Westbound", new[] { P(1200, 12), P(-1200, 12) }, breaks: new[] { new float2(0, 12) });
            c.Road("Large Road", "Garnet Street", new[] { P(0, -900), P(0, 900) }, breaks: brk);
            return c;
        }

        /// <summary>The same highway already up on a 9 m bridge over the Large Road (no shared nodes).</summary>
        public static CityBuilder SeparatedCrossing(float deck = 9f) => SeparatedCrossing(deck, new[] { -1200f, -420f, -240f, -80f, 80f, 240f, 420f, 1200f });

        /// <summary>
        /// the author's 2026-10-15 case: a 40 m highway piece just upstream of where a diamond's off-ramp leaves
        /// (and just downstream of where its on-ramp joins, on the other carriageway). The gore would fold it.
        /// </summary>
        public static CityBuilder ShortPieceCrossing() => SeparatedCrossing(9f, new[] { -1200f, -400f, -360f, -240f, -80f, 80f, 240f, 360f, 400f, 1200f });

        /// <summary>Like SeparatedCrossing, but only the eastbound carriageway has a 40 m piece where its off-ramp would leave (uneven, as on the author's highways).</summary>
        public static CityBuilder UnevenCrossing() => SeparatedCrossing(9f, new[] { -1200f, -400f, -360f, -240f, -80f, 80f, 240f, 420f, 1200f }, new[] { -1200f, -420f, -240f, -80f, 80f, 240f, 420f, 1200f });

        static CityBuilder SeparatedCrossing(float deck, float[] xs) => SeparatedCrossing(deck, xs, xs);

        static CityBuilder SeparatedCrossing(float deck, float[] xsEast, float[] xsWest)
        {
            var c = new CityBuilder();
            foreach (var (name, z, dir) in new[] { ("Eastbound", -12f, 1f), ("Westbound", 12f, -1f) })
            {
                var pts = new List<float3>();
                foreach (float x in dir > 0 ? xsEast : xsWest)
                {
                    float e = math.abs(x) <= 80f ? deck : math.abs(x) <= 240f ? deck * 0.6f : math.abs(x) <= 420f ? deck * 0.1f : 0f;
                    pts.Add(P(x, z, e));
                }
                if (dir < 0) pts.Reverse();
                c.Road("Highway Oneway - 2 lanes", name, pts);
            }
            c.Road("Large Road", "Garnet Street", new[] { P(0, -900), P(0, 900) });
            return c;
        }

        /// <summary>A divided highway with nothing crossing it, and a Medium Road running alongside 600 m to the north.</summary>
        public static CityBuilder BareHighway()
        {
            var c = new CityBuilder();
            c.Road("Highway Oneway - 2 lanes", "Eastbound", new[] { P(-1200, -12), P(1200, -12) });
            c.Road("Highway Oneway - 2 lanes", "Westbound", new[] { P(1200, 12), P(-1200, 12) });
            c.Road("Medium Road", "Elm Street", new[] { P(-800, 600), P(800, 600) });
            return c;
        }

        /// <summary>
        /// Aspen Street drawn up to a divided highway from both sides, stopping 28 m short of each carriageway
        /// (the south half a little off line). Optionally Birch Lane joins the north half close to the highway.
        /// </summary>
        public static CityBuilder StubsAtHighway(float sideStreetAt = 0f)
        {
            var c = BareHighwayWithRoadAt(float.NaN);
            var brk = sideStreetAt > 0f ? new[] { new float2(0, sideStreetAt) } : null;
            c.Road("Large Road", "Aspen Street", new[] { P(0, 700), P(0, 40) }, breaks: brk);
            c.Road("Large Road", "Aspen Street", new[] { P(10, -40), P(10, -700) });
            if (sideStreetAt > 0f) c.Road("Small Road", "Birch Lane", new[] { P(0, sideStreetAt), P(500, sideStreetAt) });
            return c;
        }

        /// <summary>Aspen Street drawn up to the highway from the north only; Elm Street runs alongside at elmZ (none if NaN).</summary>
        public static CityBuilder OneStub(float elmZ)
        {
            var c = BareHighwayWithRoadAt(elmZ);
            c.Road("Large Road", "Aspen Street", new[] { P(0, 700), P(0, 40) });
            return c;
        }

        /// <summary>Hickory Street (a Large Road) running east-west, with no highway anywhere; optionally Oak Street alongside it at z = oakZ.</summary>
        public static CityBuilder AvenueOnly(float oakZ = float.NaN)
        {
            var c = new CityBuilder();
            c.Road("Large Road", "Hickory Street", new[] { P(-900, 0), P(900, 0) });
            if (!float.IsNaN(oakZ)) c.Road("Medium Road", "Oak Street", new[] { P(-900, oakZ), P(900, oakZ) });
            return c;
        }

        /// <summary>A footpath (for pillar tests): straight, at ground level.</summary>
        public void Path(float3 a, float3 b, float width = 4f) => World.AddPath(NetUtils.StraightCurve(a, b), "Pavement Path", width);

        /// <summary>A divided highway with nothing crossing it, and Elm Street running alongside at z (none if NaN).</summary>
        public static CityBuilder BareHighwayWithRoadAt(float z)
        {
            var c = new CityBuilder();
            c.Road("Highway Oneway - 2 lanes", "Eastbound", new[] { P(-1200, -12), P(1200, -12) });
            c.Road("Highway Oneway - 2 lanes", "Westbound", new[] { P(1200, 12), P(-1200, 12) });
            if (!float.IsNaN(z)) c.Road("Medium Road", "Elm Street", new[] { P(-800, z), P(800, z) });
            return c;
        }

        /// <summary>
        /// What a new cross street looks like once built: a Large Road over the highway on a 9 m deck with
        /// 180 m slopes (5%), the shape Planner.NewStreet lays down, ready for its ramps.
        /// </summary>
        public static CityBuilder StreetOverCrossing()
        {
            var c = new CityBuilder();
            c.Road("Highway Oneway - 2 lanes", "Eastbound", new[] { P(-1200, -12), P(1200, -12) });
            c.Road("Highway Oneway - 2 lanes", "Westbound", new[] { P(1200, 12), P(-1200, 12) });
            c.Road("Large Road", "New Street", new[] { P(0, -700), P(0, -226), P(0, -46, 9), P(0, 46, 9), P(0, 226), P(0, 700) });
            return c;
        }

        /// <summary>A Medium Road crossing a railway at ground level.</summary>
        public static CityBuilder RailCrossing()
        {
            var c = new CityBuilder();
            c.Road("Twoway Train Track", "BNSF", new[] { P(-1000, 0), P(1000, 0) }, breaks: new[] { new float2(0, 0) }, track: true);
            c.Road("Medium Road", "Grand Avenue", new[] { P(0, -800), P(0, 800) }, breaks: new[] { new float2(0, 0) });
            return c;
        }

    }
}
