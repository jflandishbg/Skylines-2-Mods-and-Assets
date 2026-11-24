// =====================================================================================================
// Interchange Studio - Core/Ecs.cs
//
// A small, pure look-alike of the parts of the game API the planner reads: the same type and member
// names (Entity, Edge, Curve, Node, EntityManager.GetComponentData<T>, TerrainUtils.SampleHeight,
// NetUtils.FitCurve...), backed by plain dictionaries. In the game, the adapter fills a NetWorld from
// the live ECS world; in tests, a synthetic city builder fills it. The planning code runs unchanged
// on either, which is what makes every interchange style testable without the game.
//
// Pure: BCL + Unity.Mathematics + Colossal.Mathematics only (checked by Build/CorePurity).
// =====================================================================================================
using System;
using System.Collections;
using System.Collections.Generic;
using Colossal.Mathematics;
using Unity.Mathematics;

namespace InterchangeStudio.Core
{
    /// <summary>Mirrors Unity.Entities.Entity (Index, Version) one-to-one, so the adapter converts without a table.</summary>
    public readonly struct Entity : IEquatable<Entity>
    {
        public readonly int Index, Version;
        public Entity(int index, int version) { Index = index; Version = version; }
        public static readonly Entity Null = default;
        public bool Equals(Entity o) => Index == o.Index && Version == o.Version;
        public override bool Equals(object o) => o is Entity e && Equals(e);
        public override int GetHashCode() => (Index * 397) ^ Version;
        public static bool operator ==(Entity a, Entity b) => a.Equals(b);
        public static bool operator !=(Entity a, Entity b) => !a.Equals(b);
        public override string ToString() => "Entity(" + Index + ":" + Version + ")";
    }

    // ---- component look-alikes (field names match the game's) ----
    public struct Edge { public Entity m_Start, m_End; }
    public struct Curve { public Bezier4x3 m_Bezier; public float m_Length; }
    public struct Node { public float3 m_Position; }
    public struct Elevation { public float2 m_Elevation; }
    public struct Aggregated { public Entity m_Aggregate; }
    public struct ConnectedEdge { public Entity m_Edge; }
    public struct PrefabRef { public Entity m_Prefab; }
    public struct NetGeometryData { public float m_DefaultWidth; }
    [Flags] public enum RoadFlags : uint { None = 0, UseHighwayRules = 1 }
    public struct RoadData { public RoadFlags m_Flags; }
    public struct Road { }
    public struct TrainTrack { }
    public struct Temp { public Entity m_Original; }
    public struct Deleted { }

    /// <summary>Raw copy of the game's CompositionFlags (General, Left, Right) so upgrades survive a rebuild.</summary>
    public struct CompositionFlags : IEquatable<CompositionFlags>
    {
        public uint m_General, m_Left, m_Right;
        public bool Equals(CompositionFlags o) => m_General == o.m_General && m_Left == o.m_Left && m_Right == o.m_Right;
        public override bool Equals(object o) => o is CompositionFlags c && Equals(c);
        public override int GetHashCode() => (int)(m_General * 31 + m_Left * 17 + m_Right);
    }
    public struct Upgraded { public CompositionFlags m_Flags; }

    public sealed class DynamicBuffer<T>
    {
        readonly List<T> m_Items;
        public DynamicBuffer(List<T> items) { m_Items = items; }
        public int Length => m_Items.Count;
        public T this[int i] => m_Items[i];
    }

    public enum Allocator { Temp, TempJob, Persistent }

    /// <summary>What ToEntityArray hands back: enumerable and disposable, so `using (var ents = q.ToEntityArray(...))` ports as-is.</summary>
    public sealed class EntityArray : IEnumerable<Entity>, IDisposable
    {
        readonly List<Entity> m_Items;
        public EntityArray(List<Entity> items) { m_Items = items; }
        public int Length => m_Items.Count;
        public Entity this[int i] => m_Items[i];
        public IEnumerator<Entity> GetEnumerator() => m_Items.GetEnumerator();
        IEnumerator IEnumerable.GetEnumerator() => m_Items.GetEnumerator();
        public void Dispose() { }
    }

    /// <summary>A fixed set of edges (all roads, or all tracks), like the tool's EntityQuery fields.</summary>
    public sealed class EntityQuery
    {
        readonly Func<IReadOnlyList<Entity>> m_Source;
        public EntityQuery(Func<IReadOnlyList<Entity>> source) { m_Source = source; }
        public EntityArray ToEntityArray(Allocator allocator) => new EntityArray(new List<Entity>(m_Source()));
        public int CalculateEntityCount() => m_Source().Count;
    }

    /// <summary>
    /// The road and rail network the planner sees: the EntityManager look-alike. Everything is live
    /// (nothing Temp or Deleted). Node legs come from edge endpoints only, never from pass-through edges.
    /// </summary>
    public sealed class NetWorld
    {
        sealed class EdgeRec { public Edge Edge; public Curve Curve; public Entity Prefab; public bool HasUpgrade; public Upgraded Upgrade; public Entity Aggregate; public bool Track; }
        sealed class NodeRec { public float3 Pos; public bool HasElevation; public float2 Elev; public readonly List<ConnectedEdge> Legs = new List<ConnectedEdge>(); }
        sealed class PrefabRec { public string Name; public float Width; public bool Highway; public bool Road; }

        readonly Dictionary<Entity, EdgeRec> m_Edges = new Dictionary<Entity, EdgeRec>();
        readonly Dictionary<Entity, NodeRec> m_Nodes = new Dictionary<Entity, NodeRec>();
        readonly Dictionary<Entity, PrefabRec> m_Prefabs = new Dictionary<Entity, PrefabRec>();
        readonly List<Entity> m_RoadList = new List<Entity>(), m_TrackList = new List<Entity>(), m_PrefabList = new List<Entity>();
        int m_NextSynthetic = -1;

        /// <summary>Bumped on every change; the planner's spatial index rebuilds when it moves.</summary>
        public long Version { get; private set; }

        // ---- building (adapter mirror or synthetic test city) ----
        public Entity NewId() => new Entity(m_NextSynthetic--, 1);

        public Entity AddPrefab(Entity id, string name, float width, bool highway, bool road = true)
        {
            m_Prefabs[id] = new PrefabRec { Name = name, Width = width, Highway = highway, Road = road };
            if (road && !m_PrefabList.Contains(id)) m_PrefabList.Add(id);
            Version++;
            return id;
        }

        public Entity AddNode(Entity id, float3 position, float2? elevation = null)
        {
            m_Nodes[id] = new NodeRec { Pos = position, HasElevation = elevation.HasValue, Elev = elevation ?? float2.zero };
            Version++;
            return id;
        }

        public Entity AddEdge(Entity id, Entity start, Entity end, Bezier4x3 curve, float length, Entity prefab, bool track = false,
            CompositionFlags? upgrade = null, Entity aggregate = default)
        {
            if (aggregate != Entity.Null) m_Aggregates.Add(aggregate);
            var rec = new EdgeRec
            {
                Edge = new Edge { m_Start = start, m_End = end }, Curve = new Curve { m_Bezier = curve, m_Length = length },
                Prefab = prefab, HasUpgrade = upgrade.HasValue, Upgrade = new Upgraded { m_Flags = upgrade ?? default }, Aggregate = aggregate, Track = track,
            };
            m_Edges[id] = rec;
            (track ? m_TrackList : m_RoadList).Add(id);
            if (m_Nodes.TryGetValue(start, out var s)) s.Legs.Add(new ConnectedEdge { m_Edge = id });
            if (end != start && m_Nodes.TryGetValue(end, out var e)) e.Legs.Add(new ConnectedEdge { m_Edge = id });
            Version++;
            return id;
        }

        public IReadOnlyList<Entity> RoadEdges => m_RoadList;
        public IReadOnlyList<Entity> TrackEdges => m_TrackList;

        /// <summary>
        /// Footpaths: kept apart from the road network (nothing routes over them), only so new bridges keep their
        /// pillars off them (2026-10-23 self-test: pillars on "PedestrianPathWide01" and "Pavement Path").
        /// </summary>
        public readonly List<(Entity Id, Bezier4x3 Curve, string Name, float Width)> Paths = new List<(Entity, Bezier4x3, string, float)>();
        public void AddPath(Bezier4x3 curve, string name, float width) => Paths.Add((NewId(), curve, name, width));
        public IReadOnlyList<Entity> RoadPrefabs => m_PrefabList;
        public string PrefabName(Entity prefab) => m_Prefabs.TryGetValue(prefab, out var p) ? p.Name : null;

        // ---- the EntityManager surface the planner uses ----
        // aggregates (a named road's identity) exist in the game too; they carry no data here, only the name lookup
        readonly HashSet<Entity> m_Aggregates = new HashSet<Entity>();
        public bool Exists(Entity e) => m_Edges.ContainsKey(e) || m_Nodes.ContainsKey(e) || m_Prefabs.ContainsKey(e) || m_Aggregates.Contains(e);

        public bool HasComponent<T>(Entity e)
        {
            var t = typeof(T);
            if (m_Edges.TryGetValue(e, out var ed))
            {
                if (t == typeof(Edge) || t == typeof(Curve) || t == typeof(PrefabRef)) return true;
                if (t == typeof(Road)) return !ed.Track && m_Prefabs.TryGetValue(ed.Prefab, out var p) && p.Road;
                if (t == typeof(TrainTrack)) return ed.Track;
                if (t == typeof(Upgraded)) return ed.HasUpgrade;
                if (t == typeof(Aggregated)) return ed.Aggregate != Entity.Null;
                return false;
            }
            if (m_Nodes.TryGetValue(e, out var nd))
            {
                if (t == typeof(Node)) return true;
                if (t == typeof(Elevation)) return nd.HasElevation;
                return false;
            }
            if (m_Prefabs.TryGetValue(e, out var pr))
            {
                if (t == typeof(NetGeometryData)) return true;
                if (t == typeof(RoadData)) return pr.Road;
                return false;
            }
            return false;
        }

        public T GetComponentData<T>(Entity e) where T : struct
        {
            var t = typeof(T);
            if (m_Edges.TryGetValue(e, out var ed))
            {
                if (t == typeof(Edge)) return (T)(object)ed.Edge;
                if (t == typeof(Curve)) return (T)(object)ed.Curve;
                if (t == typeof(PrefabRef)) return (T)(object)new PrefabRef { m_Prefab = ed.Prefab };
                if (t == typeof(Upgraded)) return (T)(object)ed.Upgrade;
                if (t == typeof(Aggregated)) return (T)(object)new Aggregated { m_Aggregate = ed.Aggregate };
            }
            else if (m_Nodes.TryGetValue(e, out var nd))
            {
                if (t == typeof(Node)) return (T)(object)new Node { m_Position = nd.Pos };
                if (t == typeof(Elevation)) return (T)(object)new Elevation { m_Elevation = nd.Elev };
            }
            else if (m_Prefabs.TryGetValue(e, out var pr))
            {
                if (t == typeof(NetGeometryData)) return (T)(object)new NetGeometryData { m_DefaultWidth = pr.Width };
                if (t == typeof(RoadData)) return (T)(object)new RoadData { m_Flags = pr.Highway ? RoadFlags.UseHighwayRules : RoadFlags.None };
            }
            throw new ArgumentException($"{e} has no {t.Name}");
        }

        public bool HasBuffer<T>(Entity e) => typeof(T) == typeof(ConnectedEdge) && m_Nodes.ContainsKey(e);

        public DynamicBuffer<T> GetBuffer<T>(Entity e, bool isReadOnly = false)
        {
            if (typeof(T) != typeof(ConnectedEdge) || !m_Nodes.TryGetValue(e, out var nd)) throw new ArgumentException($"{e} has no {typeof(T).Name} buffer");
            return (DynamicBuffer<T>)(object)new DynamicBuffer<ConnectedEdge>(nd.Legs);
        }

        // ---- city settings ----

        /// <summary>The city drives on the left (the adapter copies the game's setting). The planner plans right-hand traffic only.</summary>
        public bool LeftHandTraffic { get; set; }

        // ---- copies and what-if ----

        /// <summary>A deep copy: prefabs, nodes, edges, footpaths, aggregates, settings and the synthetic id counter.</summary>
        public NetWorld Clone()
        {
            var w = new NetWorld { LeftHandTraffic = LeftHandTraffic, m_NextSynthetic = m_NextSynthetic, Version = Version };
            foreach (var kv in m_Prefabs)
                w.m_Prefabs[kv.Key] = new PrefabRec { Name = kv.Value.Name, Width = kv.Value.Width, Highway = kv.Value.Highway, Road = kv.Value.Road };
            foreach (var kv in m_Nodes)
            {
                var n = new NodeRec { Pos = kv.Value.Pos, HasElevation = kv.Value.HasElevation, Elev = kv.Value.Elev };
                n.Legs.AddRange(kv.Value.Legs);
                w.m_Nodes[kv.Key] = n;
            }
            foreach (var kv in m_Edges)
            {
                var r = kv.Value;
                w.m_Edges[kv.Key] = new EdgeRec { Edge = r.Edge, Curve = r.Curve, Prefab = r.Prefab, HasUpgrade = r.HasUpgrade, Upgrade = r.Upgrade, Aggregate = r.Aggregate, Track = r.Track };
            }
            w.m_RoadList.AddRange(m_RoadList);
            w.m_TrackList.AddRange(m_TrackList);
            w.m_PrefabList.AddRange(m_PrefabList);
            w.Paths.AddRange(Paths);
            foreach (var a in m_Aggregates) w.m_Aggregates.Add(a);
            return w;
        }

        /// <summary>A local deep copy containing only edges/paths within <paramref name="radius"/> of <paramref name="center"/> (plus anything referenced by <paramref name="pv"/>).</summary>
        NetWorld CloneNear(float2 center, float radius, Planner.Preview pv)
        {
            var w = new NetWorld { LeftHandTraffic = LeftHandTraffic, m_NextSynthetic = m_NextSynthetic, Version = Version };
            foreach (var kv in m_Prefabs)
                w.m_Prefabs[kv.Key] = new PrefabRec { Name = kv.Value.Name, Width = kv.Value.Width, Highway = kv.Value.Highway, Road = kv.Value.Road };
            w.m_PrefabList.AddRange(m_PrefabList);

            var mustKeep = new HashSet<Entity>();
            if (pv != null)
                foreach (var s in pv.Specs)
                {
                    if (s.Delete) mustKeep.Add(s.Original);
                    else
                    {
                        if (s.StartEntity != Entity.Null) mustKeep.Add(s.StartEntity);
                        if (s.EndEntity != Entity.Null) mustKeep.Add(s.EndEntity);
                    }
                }

            float r2 = radius * radius;
            foreach (var kv in m_Edges)
            {
                var r = kv.Value;
                var b = r.Curve.m_Bezier;
                bool near = mustKeep.Contains(kv.Key) || mustKeep.Contains(r.Edge.m_Start) || mustKeep.Contains(r.Edge.m_End)
                    || math.distancesq(b.a.xz, center) <= r2 || math.distancesq(b.d.xz, center) <= r2
                    || math.distancesq((b.a.xz + b.d.xz) * 0.5f, center) <= r2;
                if (!near) continue;
                foreach (var nid in new[] { r.Edge.m_Start, r.Edge.m_End })
                {
                    if (w.m_Nodes.ContainsKey(nid) || !m_Nodes.TryGetValue(nid, out var nd)) continue;
                    w.m_Nodes[nid] = new NodeRec { Pos = nd.Pos, HasElevation = nd.HasElevation, Elev = nd.Elev };
                }
                w.AddEdge(kv.Key, r.Edge.m_Start, r.Edge.m_End, b, r.Curve.m_Length, r.Prefab, r.Track,
                    r.HasUpgrade ? r.Upgrade.m_Flags : (CompositionFlags?)null, r.Aggregate);
            }
            foreach (var p in Paths)
                if (math.distancesq(p.Curve.a.xz, center) <= r2 || math.distancesq(p.Curve.d.xz, center) <= r2)
                    w.Paths.Add(p);
            w.Version = Version;
            return w;
        }

        /// <summary>Takes an edge out of the network (its node legs too). False when there was no such edge.</summary>
        bool RemoveEdge(Entity id)
        {
            if (!m_Edges.TryGetValue(id, out var rec)) return false;
            m_Edges.Remove(id);
            (rec.Track ? m_TrackList : m_RoadList).Remove(id);
            foreach (var n in new[] { rec.Edge.m_Start, rec.Edge.m_End })
                if (m_Nodes.TryGetValue(n, out var nd)) nd.Legs.RemoveAll(l => l.m_Edge == id);
            Version++;
            return true;
        }

        /// <summary>
        /// The network as it would be after <paramref name="pv"/> is built (this world is left untouched): deleted
        /// pieces go, every road piece a new end splits is cut at all its split points (sorted along it, so several
        /// ramps on one highway piece each get their own joint), coincident free ends are welded into shared joints,
        /// and every new piece is added with its road type, upgrades and end elevations.
        /// </summary>
        public NetWorld Apply(Planner.Preview pv, float2? clipCenter = null, float clipRadius = 0f)
        {
            const float Weld = 0.05f, SameSplit = 0.05f;
            var w = clipCenter.HasValue && clipRadius > 0f ? CloneNear(clipCenter.Value, clipRadius, pv) : Clone();
            if (pv == null) { w.Version++; return w; }
            var touched = new HashSet<Entity>();

            // 1. deletions
            foreach (var s in pv.Specs)
            {
                if (!s.Delete || !w.m_Edges.TryGetValue(s.Original, out var rec)) continue;
                touched.Add(rec.Edge.m_Start); touched.Add(rec.Edge.m_End);
                w.RemoveEdge(s.Original);
            }

            // 2. splits: gather every split point per edge, then cut each edge once
            var ends = new Entity[pv.Specs.Count, 2];         // resolved node for each spec end (Null = free, decided later)
            var splits = new Dictionary<Entity, List<(float t, int spec, int end)>>();
            for (int i = 0; i < pv.Specs.Count; i++)
            {
                var s = pv.Specs[i];
                if (s.Delete) continue;
                for (int k = 0; k < 2; k++)
                {
                    Entity ent = k == 0 ? s.StartEntity : s.EndEntity;
                    if (ent == Entity.Null) continue;
                    if (w.m_Nodes.ContainsKey(ent)) { ends[i, k] = ent; continue; }
                    if (!w.m_Edges.ContainsKey(ent)) continue;      // missing or deleted by this build: a free end
                    float t = math.saturate(k == 0 ? s.StartSplit : s.EndSplit);
                    if (!splits.TryGetValue(ent, out var list)) splits[ent] = list = new List<(float, int, int)>();
                    list.Add((t, i, k));
                }
            }
            foreach (var kv in splits)
            {
                var rec = w.m_Edges[kv.Key];
                var list = kv.Value;
                list.Sort((x, y) => x.t.CompareTo(y.t));
                var bez = rec.Curve.m_Bezier;
                float len = math.max(rec.Curve.m_Length, 0.001f);
                // the cut points, in order: t, node; ends of the edge use its own nodes
                var cuts = new List<(float t, Entity node)> { (0f, rec.Edge.m_Start) };
                foreach (var sp in list)
                {
                    Entity node;
                    if (sp.t * len < SameSplit) node = rec.Edge.m_Start;
                    else if ((1f - sp.t) * len < SameSplit) node = rec.Edge.m_End;
                    else if ((sp.t - cuts[cuts.Count - 1].t) * len < SameSplit && cuts.Count > 1) node = cuts[cuts.Count - 1].node;
                    else
                    {
                        float3 pos = MathUtils.Position(bez, sp.t);
                        float2 e0 = w.m_Nodes.TryGetValue(rec.Edge.m_Start, out var na) ? na.Elev : float2.zero;
                        float2 e1 = w.m_Nodes.TryGetValue(rec.Edge.m_End, out var nb) ? nb.Elev : float2.zero;
                        bool hasElev = (na != null && na.HasElevation) || (nb != null && nb.HasElevation);
                        node = w.NewId();
                        w.m_Nodes[node] = new NodeRec { Pos = pos, HasElevation = hasElev, Elev = math.lerp(e0, e1, sp.t) };
                        cuts.Add((sp.t, node));
                    }
                    ends[sp.spec, sp.end] = node;
                }
                if (cuts.Count == 1) continue;                    // every split fell on an end: nothing to cut
                cuts.Add((1f, rec.Edge.m_End));
                touched.Add(rec.Edge.m_Start); touched.Add(rec.Edge.m_End);
                w.RemoveEdge(kv.Key);
                for (int c = 0; c + 1 < cuts.Count; c++)
                {
                    var piece = MathUtils.Cut(bez, new float2(cuts[c].t, cuts[c + 1].t));
                    w.AddEdge(w.NewId(), cuts[c].node, cuts[c + 1].node, piece, MathUtils.Length(piece), rec.Prefab, rec.Track,
                        rec.HasUpgrade ? rec.Upgrade.m_Flags : (CompositionFlags?)null, rec.Aggregate);
                }
            }

            // 3. free ends: weld those at the same point into one joint, then make a joint for each
            var freeNodes = new List<(float3 pos, Entity node)>();
            for (int i = 0; i < pv.Specs.Count; i++)
            {
                var s = pv.Specs[i];
                if (s.Delete) continue;
                for (int k = 0; k < 2; k++)
                {
                    if (ends[i, k] != Entity.Null) continue;
                    float3 pos = k == 0 ? s.Curve.a : s.Curve.d;
                    float elev = k == 0 ? s.E0 : s.E1;
                    Entity node = Entity.Null;
                    foreach (var f in freeNodes) if (math.distance(f.pos, pos) <= Weld) { node = f.node; break; }
                    if (node == Entity.Null)
                    {
                        node = w.NewId();
                        w.m_Nodes[node] = new NodeRec { Pos = pos, HasElevation = math.abs(elev) > 0.01f, Elev = new float2(elev, elev) };
                        freeNodes.Add((pos, node));
                    }
                    ends[i, k] = node;
                }
            }

            // 4. the new pieces
            for (int i = 0; i < pv.Specs.Count; i++)
            {
                var s = pv.Specs[i];
                if (s.Delete) continue;
                bool track = w.m_Prefabs.TryGetValue(s.Prefab, out var pf) && !pf.Road;
                w.AddEdge(w.NewId(), ends[i, 0], ends[i, 1], s.Curve, MathUtils.Length(s.Curve), s.Prefab, track,
                    s.HasUpgrade ? s.Upgrade : (CompositionFlags?)null);
            }

            // 5. joints left with nothing attached by this build go (pre-existing lone joints are left alone)
            foreach (var n in touched)
                if (w.m_Nodes.TryGetValue(n, out var nd) && nd.Legs.Count == 0) w.m_Nodes.Remove(n);
            w.Version++;
            return w;
        }
    }

    // ---- system look-alikes ----

    public interface ITerrain { float Height(float3 position); }

    public sealed class FlatTerrain : ITerrain
    {
        readonly float m_Y;
        public FlatTerrain(float y = 0f) { m_Y = y; }
        public float Height(float3 p) => m_Y;
    }

    public sealed class FuncTerrain : ITerrain
    {
        readonly Func<float3, float> m_F;
        public FuncTerrain(Func<float3, float> f) { m_F = f; }
        public float Height(float3 p) => m_F(p);
    }

    public struct TerrainHeightData { public ITerrain Terrain; }

    public sealed class TerrainSystem
    {
        public ITerrain Terrain { get; set; } = new FlatTerrain();
        /// <summary>Water depth at a point (0 on dry land). The adapter reads the game's water; tests draw lakes.</summary>
        public Func<float3, float> WaterDepth { get; set; } = p => 0f;
        public TerrainHeightData GetHeightData(bool waitForPending = false) => new TerrainHeightData { Terrain = Terrain };
    }

    public static class TerrainUtils
    {
        public static float SampleHeight(ref TerrainHeightData data, float3 position) => data.Terrain.Height(position);
    }

    public sealed class PrefabSystem
    {
        readonly NetWorld m_World;
        public PrefabSystem(NetWorld world) { m_World = world; }
        public string GetPrefabName(Entity prefab) => m_World.PrefabName(prefab) ?? "road";
    }

    /// <summary>Road names, read lazily: the adapter supplies the game's NameSystem lookup; tests supply a dictionary.</summary>
    public sealed class NameSystem
    {
        public Func<Entity, string> Lookup { get; set; } = e => null;
        public string GetRenderedLabelName(Entity aggregate) => Lookup(aggregate);
    }

    /// <summary>Raycast result look-alike. The adapter copies the game's hit into this each frame.</summary>
    public struct RaycastHit
    {
        public Entity m_HitEntity;
        public float3 m_HitPosition;
        public float m_CurvePosition;
    }

    /// <summary>The curve helpers from Game.Net.NetUtils the planner uses, ported verbatim from the decompile.</summary>
    public static class NetUtils
    {
        public static Bezier4x3 StraightCurve(float3 startPos, float3 endPos) =>
            new Bezier4x3(startPos, math.lerp(startPos, endPos, 1f / 3f), math.lerp(startPos, endPos, 2f / 3f), endPos);

        public static Bezier4x3 FitCurve(float3 startPos, float3 startTangent, float3 middlePos, float3 endTangent, float3 endPos)
        {
            Bezier4x3 b = FitCurve(startPos, startTangent, endTangent, endPos);
            float3 off = middlePos - MathUtils.Position(b, 0.5f);
            float2 f2 = new float2(math.dot(startTangent.xz, off.xz), math.dot(endTangent.xz, off.xz));
            float2 f3 = f2 * math.dot(startTangent.xz, endTangent.xz);
            f2 *= math.abs(f2) / math.max(1E-06f, 0.375f * (math.abs(f2) + math.abs(f3.yx)));
            b.b += startTangent * math.max(f2.x, math.min(0f, 1f - math.distance(b.a.xz, b.b.xz)));
            b.c += endTangent * math.min(f2.y, math.max(0f, math.distance(b.d.xz, b.c.xz) - 1f));
            return b;
        }

        public static Bezier4x3 FitCurve(float3 startPos, float3 startTangent, float3 endTangent, float3 endPos)
        {
            float num = math.distance(startPos.xz, endPos.xz);
            Line3 line = new Line3(startPos, startPos + startTangent);
            Line3 line2 = new Line3(endPos, endPos - endTangent);
            float2 t = !MathUtils.Intersect(line.xz, line2.xz, out t) ? (float2)(num * 0.75f) : math.clamp(t, num * 0.01f, num);
            float num2 = math.dot(startTangent.xz, endTangent.xz);
            if (num2 > 0f) t = math.lerp(t, num / math.sqrt(2f * num2 + 2f), math.min(1f, num2 * num2));
            else if (num2 < 0f) t = math.lerp(t, num * 1.2071068f, math.min(1f, num2 * num2));
            return FitCurve(MathUtils.Cut(line, new float2(0f, t.x)), MathUtils.Cut(line2, new float2(0f, t.y)));
        }

        public static Bezier4x3 FitCurve(Line3.Segment startLine, Line3.Segment endLine)
        {
            float3 f = MathUtils.Tangent(startLine), g = MathUtils.Tangent(endLine);
            float num = math.length(f.xz), num2 = math.length(g.xz);
            if (num != 0f) f /= num;
            else { f.xz = endLine.b.xz - startLine.a.xz; num = math.length(f.xz); if (num != 0f) f /= num; }
            if (num2 != 0f) g /= num2;
            else { g.xz = startLine.b.xz - endLine.a.xz; num2 = math.length(g.xz); if (num2 != 0f) g /= num2; }
            f.y = math.clamp(f.y, -1f, 1f);
            g.y = math.clamp(g.y, -1f, 1f);
            float num3 = math.acos(math.saturate(0f - math.dot(f.xz, g.xz)));
            float num4 = math.tan(num3 / 2f);
            float num5 = (num + num2) * (1f / 6f);
            num5 = !(num4 >= 0.0001f) ? num5 * 2f : num5 * (4f * math.tan(num3 / 4f) / num4);
            return new Bezier4x3(startLine.a, startLine.a + f * math.min(num, num5), endLine.a + g * math.min(num2, num5), endLine.a);
        }
    }

    /// <summary>Plain log sink. The adapter strips braces and caps length before the game logger sees it.</summary>
    public interface IPlanLog
    {
        void Info(string line);
        void Warn(string line);
        void Error(Exception e, string line);
    }

    public sealed class NullLog : IPlanLog
    {
        public static readonly NullLog Instance = new NullLog();
        public void Info(string line) { }
        public void Warn(string line) { }
        public void Error(Exception e, string line) { }
    }

    /// <summary>One red item the game reported in the preview (adapter: Temp + Error), described in words.</summary>
    public struct RedItem
    {
        public string What;
        public float3 At;
    }
}
