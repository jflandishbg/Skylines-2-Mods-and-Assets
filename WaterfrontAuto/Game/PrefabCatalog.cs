using System;
using System.Collections.Generic;
using Game.Prefabs;
using Unity.Collections;
using Unity.Entities;
using WaterfrontAuto.Core;

namespace WaterfrontAuto.GameAdapter
{
    /// <summary>
    /// Dynamically discovers 100% vanilla Cities: Skylines II prefabs at runtime
    /// (wide timber boardwalk piers, quays, pathways, sand/paving/concrete surfaces,
    /// Atlantic City kiosks/gazebos/lamps/benches/life-buoys, beach umbrellas/chairs,
    /// industrial bollards, transition rocks, and soft terrain brushes).
    /// </summary>
    public sealed class PrefabCatalog
    {
        private readonly EntityManager m_EM;
        private readonly PrefabSystem m_Prefabs;

        public readonly Dictionary<NetRole, Entity> Nets = new Dictionary<NetRole, Entity>();
        public readonly Dictionary<SurfaceRole, Entity> Surfaces = new Dictionary<SurfaceRole, Entity>();
        public readonly Dictionary<PropRole, List<Entity>> Props = new Dictionary<PropRole, List<Entity>>();
        public readonly HashSet<string> KnownNetPrefabNames = new HashSet<string>(StringComparer.Ordinal);
        public readonly HashSet<string> KnownSurfacePrefabNames = new HashSet<string>(StringComparer.Ordinal);
        public readonly HashSet<string> KnownPropPrefabNames = new HashSet<string>(StringComparer.Ordinal);
        public Entity SoftBrushPrefab { get; private set; }
        public UnityEngine.Texture SoftBrushTexture { get; private set; }
        public bool Indexed { get; private set; }

        public float WidthOf(Entity prefab, float fallback)
        {
            if (prefab != Entity.Null && m_EM.Exists(prefab) && m_EM.HasComponent<NetGeometryData>(prefab))
            {
                float w = m_EM.GetComponentData<NetGeometryData>(prefab).m_DefaultWidth;
                if (w > 0.5f && w < 64f) return w;
            }
            return fallback;
        }

        public PrefabCatalog(EntityManager em, PrefabSystem prefabs)
        {
            m_EM = em;
            m_Prefabs = prefabs;
        }

        public void EnsureIndexed()
        {
            if (Indexed) return;
            Index();
        }

        public void Reset()
        {
            Indexed = false;
            Nets.Clear();
            Surfaces.Clear();
            Props.Clear();
            KnownNetPrefabNames.Clear();
            KnownSurfacePrefabNames.Clear();
            KnownPropPrefabNames.Clear();
            SoftBrushPrefab = Entity.Null;
            SoftBrushTexture = null;
        }

        public string NameOf(Entity e) => e != Entity.Null ? (m_Prefabs.GetPrefabName(e) ?? "") : "";

        private void Index()
        {
            Nets.Clear();
            Surfaces.Clear();
            Props.Clear();
            KnownNetPrefabNames.Clear();
            KnownSurfacePrefabNames.Clear();
            KnownPropPrefabNames.Clear();
            foreach (PropRole r in Enum.GetValues(typeof(PropRole)))
                Props[r] = new List<Entity>();

            var pathways = new Dictionary<string, Entity>(StringComparer.OrdinalIgnoreCase);
            var surfaces = new Dictionary<string, Entity>(StringComparer.OrdinalIgnoreCase);
            var objects = new Dictionary<string, Entity>(StringComparer.OrdinalIgnoreCase);

            var query = m_EM.CreateEntityQuery(ComponentType.ReadOnly<PrefabData>());
            using (var entities = query.ToEntityArray(Allocator.Temp))
            {
                for (int i = 0; i < entities.Length; i++)
                {
                    Entity e = entities[i];
                    if (!m_Prefabs.TryGetPrefab<PrefabBase>(e, out var prefab) || prefab == null) continue;
                    string name = prefab.name ?? "";
                    if (name.Length == 0) continue;
                    string lower = name.ToLowerInvariant();

                    if (prefab is BrushPrefab bp)
                    {
                        if (SoftBrushPrefab == Entity.Null || lower.Contains("soft"))
                        {
                            SoftBrushPrefab = e;
                            SoftBrushTexture = bp.m_Texture;
                        }
                        continue;
                    }

                    if (m_EM.HasComponent<PathwayData>(e) && m_EM.HasComponent<NetGeometryData>(e))
                    {
                        if (!lower.Contains("invisible") && !lower.Contains("marker") && !lower.Contains("fence"))
                            pathways[name] = e;
                        continue;
                    }

                    if (prefab is SurfacePrefab || m_EM.HasComponent<SurfaceData>(e))
                    {
                        surfaces[name] = e;
                        continue;
                    }

                    if (prefab is StaticObjectPrefab && !m_EM.HasComponent<BuildingData>(e))
                    {
                        if (m_EM.HasComponent<ObjectGeometryData>(e))
                        {
                            var flags = m_EM.GetComponentData<ObjectGeometryData>(e).m_Flags;
                            if ((flags & Game.Objects.GeometryFlags.OccupyZone) != 0) continue;
                        }
                        objects[name] = e;
                    }
                }
            }
            query.Dispose();

            // Resolve Net prefabs (100% vanilla) — prefer widest timber boardwalk pier for true Atlantic City oomph!
            Entity fallbackPath = PickNet(pathways, new[] { "Pavement Path", "PedestrianPathWide01", "PedestrianPath01" }, new[] { "pavement", "pedestrian", "path" }, new[] { "bridge", "quay", "pier", "bike" });
            Entity grandBoardwalk = PickNet(pathways, new[] { "LeisurePier01Large01", "LeisurePier01Medium01", "LeisurePier01Small01", "QuaySmallWide01" }, new[] { "leisurepier01large", "leisurepier", "pier", "boardwalk" }, new[] { "ferry", "marina", "pillar", "boatway" });
            Entity smallPier = PickNet(pathways, new[] { "LeisurePier01Small01", "LeisurePier01Medium01", "Pavement Path" }, new[] { "leisurepier01small", "leisurepier", "pier" }, new[] { "ferry", "marina", "pillar", "boatway" });
            Entity quayNarrow = PickNet(pathways, new[] { "QuaySmall01", "QuaySmall02", "QuaySmall03", "QuaySmallWide01" }, new[] { "quaysmall", "quay" }, new[] { "bike", "cycle" });
            Entity quayWide = PickNet(pathways, new[] { "QuaySmallWide01", "QuaySmall02", "QuaySmall01", "QuaySmall03" }, new[] { "quaysmallwide", "quay" }, new[] { "bike", "cycle" });
            Entity fishingPier = PickNet(pathways, new[] { "Fishing Pier", "LeisurePier01Medium01", "LeisurePier01Large01", "QuaySmallWide01" }, new[] { "fishing pier", "leisurepier", "pier" }, new[] { "ferry", "pillar", "boatway" });
            Entity beachPath = PickNet(pathways, new[] { "Pavement Path", "PedestrianPath01", "PedestrianPathWide01" }, new[] { "sand", "dirt", "gravel", "pavement path", "pedestrian" }, new[] { "bridge", "quay", "pier", "bike" });

            Nets[NetRole.Boardwalk] = grandBoardwalk != Entity.Null ? grandBoardwalk : (quayWide != Entity.Null ? quayWide : fallbackPath);
            Nets[NetRole.BoardwalkOverlook] = smallPier != Entity.Null ? smallPier : Nets[NetRole.Boardwalk];
            Nets[NetRole.IndustrialQuay] = quayWide != Entity.Null ? quayWide : (quayNarrow != Entity.Null ? quayNarrow : fallbackPath);
            Nets[NetRole.IndustrialPier] = fishingPier != Entity.Null ? fishingPier : Nets[NetRole.Boardwalk];
            Nets[NetRole.BeachPath] = beachPath != Entity.Null ? beachPath : fallbackPath;
            Nets[NetRole.BeachBoardwalkFallback] = quayNarrow != Entity.Null ? quayNarrow : (grandBoardwalk != Entity.Null ? grandBoardwalk : fallbackPath);
            Nets[NetRole.TransitionRamp] = smallPier != Entity.Null ? smallPier : fallbackPath;
            Nets[NetRole.AccessSpur] = fallbackPath != Entity.Null ? fallbackPath : Nets[NetRole.BeachPath];
            foreach (var kv in Nets)
                if (kv.Value != Entity.Null) KnownNetPrefabNames.Add(NameOf(kv.Value));

            // Resolve Surface prefabs (100% vanilla)
            Surfaces[SurfaceRole.Sand] = PickSurface(surfaces, new[] { "Sand Surface 01", "Sand Surface 02" }, "sand");
            Surfaces[SurfaceRole.BoardwalkDeck] = PickSurface(surfaces, new[] { "Tiles Surface 01", "Pavement Surface 02", "Pavement Surface 01" }, "tile", "pavement");
            Surfaces[SurfaceRole.IndustrialConcrete] = PickSurface(surfaces, new[] { "Concrete Surface 01", "Concrete Surface 02", "Pavement Surface 01" }, "concrete", "pavement");
            Surfaces[SurfaceRole.TransitionPaving] = PickSurface(surfaces, new[] { "Pavement Surface 02", "Pavement Surface 01", "Concrete Surface 01" }, "pavement", "concrete");
            foreach (var kv in Surfaces)
                if (kv.Value != Entity.Null) KnownSurfacePrefabNames.Add(NameOf(kv.Value));

            // Resolve Prop prefab pools (100% vanilla)
            CollectProps(objects, Props[PropRole.BeachChair], new[] { "DeckChair01", "DeckChair02", "DeckChair03" }, "deckchair");
            CollectProps(objects, Props[PropRole.BeachParasol], new[] { "Parasol01", "Parasol02", "Parasol03" }, "parasol");
            CollectProps(objects, Props[PropRole.BoardwalkBench], new[] { "GardenBench01", "GardenBench02", "GardenBench03", "GardenBench04" }, "gardenbench");
            CollectProps(objects, Props[PropRole.BoardwalkLamp], new[] { "LightpolePark01", "LightpolePark02", "LightpolePark03", "LightpolePark04", "GardenLight01" }, "lightpolepark");
            CollectProps(objects, Props[PropRole.BoardwalkBollard], new[] { "Bollard01", "Bollard02", "Bollard03" }, "bollard");
            CollectProps(objects, Props[PropRole.BoardwalkKiosk], new[] { "Kiosk01", "Kiosk02", "Kiosk03", "FoodCart01", "FoodStall01" }, "kiosk");
            CollectProps(objects, Props[PropRole.BoardwalkGazebo], new[] { "Gazebo01", "Gazebo02", "Gazebo03", "Pergola01" }, "gazebo");
            CollectProps(objects, Props[PropRole.BoardwalkLifeBuoy], new[] { "LifeBuoyStation01", "Bollard01", "Bollard02" }, "lifebuoy");
            CollectProps(objects, Props[PropRole.IndustrialBollard], new[] { "MooringBollard01", "MooringBollard02", "Bollard01", "Bollard02" }, "mooringbollard");
            CollectProps(objects, Props[PropRole.IndustrialBarrier], new[] { "ConcreteBarrier01", "ConcreteBarrier02", "ConcreteBarrier03" }, "concretebarrier");
            CollectProps(objects, Props[PropRole.TransitionRock], new[] { "Rock01", "Rock02", "Rock03", "Rock04", "Rock05" }, "rock0");
            CollectProps(objects, Props[PropRole.TransitionRubble], new[] { "RubblePileConcrete01", "RubblePileConcrete02", "RubblePileConcrete03", "Rock01", "Rock02" }, "rubblepileconcrete");

            foreach (var kv in Props)
                for (int i = 0; i < kv.Value.Count; i++)
                    KnownPropPrefabNames.Add(NameOf(kv.Value[i]));

            Indexed = true;

            Mod.Log.Info($"WaterfrontAuto catalog indexed: " +
                $"Boardwalk={NameOf(Nets[NetRole.Boardwalk])}, " +
                $"HomeQuay={NameOf(Nets[NetRole.BeachBoardwalkFallback])}, " +
                $"IndQuay={NameOf(Nets[NetRole.IndustrialQuay])}, " +
                $"IndPier={NameOf(Nets[NetRole.IndustrialPier])}, " +
                $"Ramp={NameOf(Nets[NetRole.TransitionRamp])}, " +
                $"Sand={NameOf(Surfaces[SurfaceRole.Sand])}, " +
                $"Kiosks={Props[PropRole.BoardwalkKiosk].Count}, " +
                $"Gazebos={Props[PropRole.BoardwalkGazebo].Count}");
        }

        public Entity PickProp(PropRole role, int seed)
        {
            if (!Props.TryGetValue(role, out var list) || list.Count == 0) return Entity.Null;
            int idx = (seed & 0x7fffffff) % list.Count;
            return list[idx];
        }

        private static Entity PickNet(Dictionary<string, Entity> map, string[] exactOrder, string[] containsOrder, string[] exclude)
        {
            for (int i = 0; i < exactOrder.Length; i++)
                if (map.TryGetValue(exactOrder[i], out var e)) return e;

            for (int i = 0; i < containsOrder.Length; i++)
            {
                string want = containsOrder[i];
                foreach (var kv in map)
                {
                    string lower = kv.Key.ToLowerInvariant();
                    if (!lower.Contains(want)) continue;
                    bool bad = false;
                    for (int x = 0; x < exclude.Length; x++)
                        if (lower.Contains(exclude[x])) { bad = true; break; }
                    if (!bad) return kv.Value;
                }
            }

            return Entity.Null;
        }

        private static Entity PickSurface(Dictionary<string, Entity> map, string[] exactOrder, params string[] containsOrder)
        {
            for (int i = 0; i < exactOrder.Length; i++)
                if (map.TryGetValue(exactOrder[i], out var e)) return e;
            for (int i = 0; i < containsOrder.Length; i++)
            {
                string want = containsOrder[i];
                foreach (var kv in map)
                    if (kv.Key.ToLowerInvariant().Contains(want)) return kv.Value;
            }
            return Entity.Null;
        }

        private static void CollectProps(Dictionary<string, Entity> map, List<Entity> into, string[] exactNames, string fallbackContains)
        {
            for (int i = 0; i < exactNames.Length; i++)
                if (map.TryGetValue(exactNames[i], out var e) && !into.Contains(e))
                    into.Add(e);
            if (into.Count > 0) return;

            foreach (var kv in map)
            {
                if (kv.Key.ToLowerInvariant().Contains(fallbackContains))
                {
                    into.Add(kv.Value);
                    if (into.Count >= 4) break;
                }
            }
        }
    }
}
