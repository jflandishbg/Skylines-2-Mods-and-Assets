using Colossal.Mathematics;
using Game.City;
using Game.Common;
using Game.Net;
using Game.Prefabs;
using Game.Tools;
using Unity.Collections;
using Unity.Entities;
using Unity.Mathematics;
using Core = InterchangeStudio.Core;

namespace InterchangeStudio.Adapter
{
    /// <summary>
    /// Copies the live road and rail network into a Core.NetWorld for the planner. Rebuilt only when the
    /// set of road pieces changes (a fingerprint of entity ids, checked cheaply), never because of the
    /// tool's own preview pieces (those are Temp and excluded).
    /// </summary>
    public sealed class WorldMirror
    {
        readonly EntityManager m_EM;
        readonly PrefabSystem m_Prefabs;
        readonly CityConfigurationSystem m_CityConfig;
        readonly EntityQuery m_Roads, m_Tracks, m_RoadPrefabs, m_Others;
        ulong m_Print;

        public WorldMirror(EntityManager em, PrefabSystem prefabs, CityConfigurationSystem cityConfig, EntityQuery roads, EntityQuery tracks, EntityQuery roadPrefabs, EntityQuery others)
        {
            m_EM = em; m_Prefabs = prefabs; m_CityConfig = cityConfig; m_Roads = roads; m_Tracks = tracks; m_RoadPrefabs = roadPrefabs; m_Others = others;
        }

        public static Core.Entity C(Entity e) => new Core.Entity(e.Index, e.Version);
        public static Entity U(Core.Entity e) => e == Core.Entity.Null ? Entity.Null : new Entity { Index = e.Index, Version = e.Version };

        /// <summary>Order-independent fingerprint of every live road/track piece, including full Bezier geometry, upgrades, and prefab.</summary>
        ulong Fingerprint()
        {
            ulong h = 1469598103934665603UL;
            if (m_CityConfig != null && m_CityConfig.leftHandTraffic) h ^= 0xA5A5A5A5A5A5A5A5UL;
            h += (ulong)m_Others.CalculateEntityCount() * 0x9E3779B97F4A7C15UL;
            foreach (var q in new[] { m_Roads, m_Tracks })
                using (var ents = q.ToEntityArray(Allocator.Temp))
                {
                    h += (ulong)ents.Length * 0x9E3779B97F4A7C15UL;
                    for (int i = 0; i < ents.Length; i++)
                        unchecked
                        {
                            var e = ents[i];
                            ulong x = (ulong)(uint)e.Index << 32 | (uint)e.Version;
                            if (m_EM.HasComponent<Curve>(e))
                            {
                                var b = m_EM.GetComponentData<Curve>(e).m_Bezier;
                                int ax = (int)math.round(b.a.x * 2f), ay = (int)math.round(b.a.y * 4f), az = (int)math.round(b.a.z * 2f);
                                int bx = (int)math.round(b.b.x * 2f), bz = (int)math.round(b.b.z * 2f);
                                int cx = (int)math.round(b.c.x * 2f), cz = (int)math.round(b.c.z * 2f);
                                int dx = (int)math.round(b.d.x * 2f), dy = (int)math.round(b.d.y * 4f), dz = (int)math.round(b.d.z * 2f);
                                x ^= ((ulong)(uint)(ax * 73856093 ^ ay * 19349663 ^ az * 83492791) << 16) ^ (uint)(dx * 73856093 ^ dy * 19349663 ^ dz * 83492791);
                                x ^= ((ulong)(uint)(bx * 2654435761u ^ bz * 2246822519u) << 8) ^ (uint)(cx * 3266489917u ^ cz * 668265263u);
                                if (m_EM.HasComponent<PrefabRef>(e)) x ^= (ulong)(uint)m_EM.GetComponentData<PrefabRef>(e).m_Prefab.Index * 0x517CC1B727220A95UL;
                                if (m_EM.HasComponent<Upgraded>(e))
                                {
                                    var u = m_EM.GetComponentData<Upgraded>(e).m_Flags;
                                    x ^= ((ulong)(uint)u.m_General << 24) ^ ((ulong)(uint)u.m_Left << 12) ^ (uint)u.m_Right;
                                }
                            }
                            x ^= x >> 33; x *= 0xff51afd7ed558ccdUL; x ^= x >> 33; h += x;
                        }
                }
            return h;
        }

        /// <summary>A fresh mirror when the network changed (or when forced), else null.</summary>
        public Core.NetWorld Refresh(bool force)
        {
            ulong print = Fingerprint();
            if (!force && print == m_Print) return null;
            m_Print = print;
            return Build();
        }

        Core.NetWorld Build()
        {
            var w = new Core.NetWorld { LeftHandTraffic = m_CityConfig != null && m_CityConfig.leftHandTraffic };
            using (var prefabs = m_RoadPrefabs.ToEntityArray(Allocator.Temp))
                foreach (var p in prefabs) AddPrefab(w, p);
            foreach (var (q, track) in new[] { (m_Roads, false), (m_Tracks, true) })
                using (var ents = q.ToEntityArray(Allocator.Temp))
                    foreach (var e in ents)
                    {
                        var ed = m_EM.GetComponentData<Edge>(e);
                        var cv = m_EM.GetComponentData<Curve>(e);
                        var prefab = m_EM.GetComponentData<PrefabRef>(e).m_Prefab;
                        AddPrefab(w, prefab);
                        AddNode(w, ed.m_Start); AddNode(w, ed.m_End);
                        Core.CompositionFlags? upg = null;
                        if (m_EM.HasComponent<Upgraded>(e))
                        {
                            var f = m_EM.GetComponentData<Upgraded>(e).m_Flags;
                            upg = new Core.CompositionFlags { m_General = (uint)f.m_General, m_Left = (uint)f.m_Left, m_Right = (uint)f.m_Right };
                        }
                        var agg = m_EM.HasComponent<Aggregated>(e) ? C(m_EM.GetComponentData<Aggregated>(e).m_Aggregate) : Core.Entity.Null;
                        w.AddEdge(C(e), C(ed.m_Start), C(ed.m_End), cv.m_Bezier, cv.m_Length, C(prefab), track, upg, agg);
                    }
            // footpaths, for keeping pillars off them (other nets in that query: power lines, pipes, ... are skipped)
            using (var ents = m_Others.ToEntityArray(Allocator.Temp))
                foreach (var e in ents)
                {
                    var prefab = m_EM.GetComponentData<PrefabRef>(e).m_Prefab;
                    if (!m_EM.HasComponent<PathwayData>(prefab)) continue;
                    float width = m_EM.HasComponent<NetGeometryData>(prefab) ? m_EM.GetComponentData<NetGeometryData>(prefab).m_DefaultWidth : 4f;
                    w.AddPath(m_EM.GetComponentData<Curve>(e).m_Bezier, m_Prefabs.GetPrefabName(prefab), width);
                }
            return w;
        }

        void AddPrefab(Core.NetWorld w, Entity p)
        {
            var id = C(p);
            if (w.PrefabName(id) != null) return;
            float width = m_EM.HasComponent<NetGeometryData>(p) ? m_EM.GetComponentData<NetGeometryData>(p).m_DefaultWidth : 8f;
            bool road = m_EM.HasComponent<RoadData>(p);
            bool highway = road && (m_EM.GetComponentData<RoadData>(p).m_Flags & Game.Prefabs.RoadFlags.UseHighwayRules) != 0;
            w.AddPrefab(id, m_Prefabs.GetPrefabName(p), width, highway, road);
        }

        void AddNode(Core.NetWorld w, Entity n)
        {
            var id = C(n);
            if (w.Exists(id)) return;
            float3 pos = m_EM.GetComponentData<Game.Net.Node>(n).m_Position;
            float2? elev = m_EM.HasComponent<Elevation>(n) ? m_EM.GetComponentData<Elevation>(n).m_Elevation : (float2?)null;
            w.AddNode(id, pos, elev);
        }
    }
}
