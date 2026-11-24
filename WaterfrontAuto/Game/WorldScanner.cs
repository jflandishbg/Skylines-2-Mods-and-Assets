using System;
using System.Collections.Generic;
using System.Reflection;
using Colossal.Mathematics;
using Game.Buildings;
using Game.Common;
using Game.Net;
using Game.Objects;
using Game.Prefabs;
using Game.Simulation;
using Game.Tools;
using Game.Zones;
using Unity.Collections;
using Unity.Entities;
using Unity.Jobs;
using Unity.Mathematics;
using WaterfrontAuto.Core;

namespace WaterfrontAuto.GameAdapter
{
    /// <summary>
    /// Reads live CS2 buildings, zones, roads/pathways/quays, terrain, and water into pure Core structures.
    /// Also detects Placemaker entities safely via dynamic ComponentType reflection (zero DLL dependency).
    /// </summary>
    public sealed class WorldScanner
    {
        private readonly EntityManager m_EM;
        private readonly PrefabSystem m_Prefabs;
        private readonly TerrainSystem m_Terrain;
        private readonly WaterSystem m_Water;

        private readonly EntityQuery m_BuildingsQuery;
        private readonly EntityQuery m_NetsQuery;
        private readonly EntityQuery m_AreasQuery;
        private readonly EntityQuery m_ObjectsQuery;

        // Optional Placemaker interop (resolved lazily without referencing Placemaker.dll)
        private bool m_PlacemakerChecked;
        private bool m_PlacemakerPresent;
        private ComponentType m_PlacemakerMemberType;
        private bool m_HasPlacemakerMemberType;
        private Type m_PlacemakerBuildServiceType;
        private PropertyInfo m_PlacemakerStatusProp;

        public bool PlacemakerDetected { get { EnsurePlacemakerInterop(); return m_PlacemakerPresent; } }

        public WorldScanner(EntityManager em, PrefabSystem prefabs, TerrainSystem terrain, WaterSystem water)
        {
            m_EM = em;
            m_Prefabs = prefabs;
            m_Terrain = terrain;
            m_Water = water;

            m_BuildingsQuery = em.CreateEntityQuery(new EntityQueryDesc
            {
                All = new[]
                {
                    ComponentType.ReadOnly<Building>(),
                    ComponentType.ReadOnly<Game.Objects.Transform>(),
                    ComponentType.ReadOnly<PrefabRef>(),
                },
                None = new[]
                {
                    ComponentType.ReadOnly<Temp>(),
                    ComponentType.ReadOnly<Deleted>(),
                }
            });

            m_NetsQuery = em.CreateEntityQuery(new EntityQueryDesc
            {
                All = new[]
                {
                    ComponentType.ReadOnly<Edge>(),
                    ComponentType.ReadOnly<Curve>(),
                    ComponentType.ReadOnly<PrefabRef>(),
                },
                None = new[]
                {
                    ComponentType.ReadOnly<Temp>(),
                    ComponentType.ReadOnly<Deleted>(),
                }
            });

            m_AreasQuery = em.CreateEntityQuery(new EntityQueryDesc
            {
                All = new[]
                {
                    ComponentType.ReadOnly<Game.Areas.Area>(),
                    ComponentType.ReadOnly<Game.Areas.Node>(),
                    ComponentType.ReadOnly<PrefabRef>(),
                },
                None = new[]
                {
                    ComponentType.ReadOnly<Temp>(),
                    ComponentType.ReadOnly<Deleted>(),
                }
            });

            m_ObjectsQuery = em.CreateEntityQuery(new EntityQueryDesc
            {
                All = new[]
                {
                    ComponentType.ReadOnly<Game.Objects.Object>(),
                    ComponentType.ReadOnly<Game.Objects.Transform>(),
                    ComponentType.ReadOnly<PrefabRef>(),
                },
                None = new[]
                {
                    ComponentType.ReadOnly<Building>(),
                    ComponentType.ReadOnly<Temp>(),
                    ComponentType.ReadOnly<Deleted>(),
                }
            });
        }

        private void EnsurePlacemakerInterop()
        {
            if (m_PlacemakerChecked) return;
            m_PlacemakerChecked = true;
            try
            {
                foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
                {
                    string name = asm.GetName().Name;
                    if (!string.Equals(name, "Placemaker", StringComparison.OrdinalIgnoreCase)) continue;
                    m_PlacemakerPresent = true;
                    var memberType = asm.GetType("Placemaker.Game.Groups.PlacemakerMember");
                    if (memberType != null)
                    {
                        m_PlacemakerMemberType = ComponentType.ReadOnly(memberType);
                        m_HasPlacemakerMemberType = true;
                    }
                    m_PlacemakerBuildServiceType = asm.GetType("Placemaker.Game.Build.BuildService");
                    if (m_PlacemakerBuildServiceType != null)
                        m_PlacemakerStatusProp = m_PlacemakerBuildServiceType.GetProperty("Status", BindingFlags.Public | BindingFlags.Instance);
                    Mod.Log.Info("WaterfrontAuto: Placemaker detected — compatibility mode active.");
                    break;
                }
            }
            catch (Exception ex)
            {
                Mod.Log.Warn("WaterfrontAuto: Placemaker reflection check skipped: " + ex.Message);
            }
        }

        /// <summary>Returns true if Placemaker's BuildService is currently mid-build so we politely wait a moment.</summary>
        public bool IsPlacemakerBusy(World world)
        {
            EnsurePlacemakerInterop();
            if (!m_PlacemakerPresent || m_PlacemakerBuildServiceType == null || m_PlacemakerStatusProp == null)
                return false;
            try
            {
                var sys = world.GetExistingSystemManaged(m_PlacemakerBuildServiceType);
                if (sys == null) return false;
                var status = m_PlacemakerStatusProp.GetValue(sys);
                if (status == null) return false;
                var phaseProp = status.GetType().GetProperty("Phase") ?? (MemberInfo)status.GetType().GetField("Phase");
                object phaseVal = phaseProp is PropertyInfo pi ? pi.GetValue(status) : phaseProp is FieldInfo fi ? fi.GetValue(status) : null;
                if (phaseVal == null) return false;
                string s = phaseVal.ToString();
                return s != "Idle" && s != "Done" && s != "None" && s != "Failed" && s != "Cancelled";
            }
            catch
            {
                return false;
            }
        }

        public bool IsPlacemakerEntity(Entity e)
        {
            EnsurePlacemakerInterop();
            if (!m_HasPlacemakerMemberType || e == Entity.Null || !m_EM.Exists(e)) return false;
            try
            {
                if (m_EM.HasComponent(e, m_PlacemakerMemberType)) return true;
                if (m_EM.HasComponent<Owner>(e))
                {
                    Entity owner = m_EM.GetComponentData<Owner>(e).m_Owner;
                    if (owner != Entity.Null && m_EM.Exists(owner) && m_EM.HasComponent(owner, m_PlacemakerMemberType))
                        return true;
                }
            }
            catch { }
            return false;
        }

        public List<BuildingLot> ScanBuildings()
        {
            var result = new List<BuildingLot>();
            using (var entities = m_BuildingsQuery.ToEntityArray(Allocator.Temp))
            {
                for (int i = 0; i < entities.Length; i++)
                {
                    Entity e = entities[i];
                    // Skip sub-buildings/extensions owned by another building
                    if (m_EM.HasComponent<Owner>(e))
                    {
                        Entity owner = m_EM.GetComponentData<Owner>(e).m_Owner;
                        if (owner != Entity.Null && m_EM.Exists(owner) && m_EM.HasComponent<Building>(owner))
                            continue;
                    }

                    Entity prefab = m_EM.GetComponentData<PrefabRef>(e).m_Prefab;
                    if (prefab == Entity.Null || !m_EM.HasComponent<BuildingData>(prefab)) continue;

                    var bData = m_EM.GetComponentData<BuildingData>(prefab);
                    if (bData.m_LotSize.x <= 0 || bData.m_LotSize.y <= 0) continue;

                    var tr = m_EM.GetComponentData<Game.Objects.Transform>(e);
                    Quad3 quad = BuildingUtils.CalculateCorners(tr, bData.m_LotSize);

                    result.Add(new BuildingLot
                    {
                        EntityId = EncodeEntity(e),
                        Center = new Vec3(tr.m_Position.x, tr.m_Position.y, tr.m_Position.z),
                        Corners = new[]
                        {
                            new Vec2(quad.a.x, quad.a.z),
                            new Vec2(quad.b.x, quad.b.z),
                            new Vec2(quad.c.x, quad.c.z),
                            new Vec2(quad.d.x, quad.d.z),
                        },
                        Width = bData.m_LotSize.x * 8f,
                        Depth = bData.m_LotSize.y * 8f,
                        LotElevation = tr.m_Position.y,
                        ZoneKind = ClassifyBuildingZone(prefab),
                        UnderConstruction = m_EM.HasComponent<UnderConstruction>(e),
                        IsPlacemakerOwned = IsPlacemakerEntity(e),
                        IsMaritimeBuilding = IsMaritimeBuilding(e, prefab),
                        DebugName = m_Prefabs.GetPrefabName(prefab),
                    });
                }
            }
            return result;
        }

        private bool IsMaritimeBuilding(Entity buildingEntity, Entity prefab)
        {
            // 1. PlacementFlags: every CS2 port, harbor, marina, ferry terminal, water pump, sewage outlet, dam, bridge pier
            if (m_EM.HasComponent<PlaceableObjectData>(prefab))
            {
                var pf = m_EM.GetComponentData<PlaceableObjectData>(prefab).m_Flags;
                const Game.Objects.PlacementFlags maritimeFlags = Game.Objects.PlacementFlags.Shoreline | Game.Objects.PlacementFlags.Floating | Game.Objects.PlacementFlags.Underwater | Game.Objects.PlacementFlags.Waterway;
                if ((pf & maritimeFlags) != 0) return true;
            }

            // 2. Water utilities & stations with waterway sub-nets
            if (m_EM.HasComponent<WaterPumpingStationData>(prefab) || m_EM.HasComponent<SewageOutletData>(prefab))
                return true;

            if (m_EM.HasBuffer<Game.Net.SubNet>(buildingEntity))
            {
                var subNets = m_EM.GetBuffer<Game.Net.SubNet>(buildingEntity, true);
                for (int i = 0; i < subNets.Length; i++)
                {
                    Entity sn = subNets[i].m_SubNet;
                    if (sn != Entity.Null && m_EM.Exists(sn) && m_EM.HasComponent<PrefabRef>(sn))
                    {
                        Entity sp = m_EM.GetComponentData<PrefabRef>(sn).m_Prefab;
                        if (sp != Entity.Null && m_EM.HasComponent<WaterwayData>(sp))
                            return true;
                    }
                }
            }

            // 3. Name safety net for custom/DLC ports, harbors, marinas, ferries, and docks
            string lower = (m_Prefabs.GetPrefabName(prefab) ?? "").ToLowerInvariant();
            if (lower.Contains("harbor") || lower.Contains("harbour") || lower.Contains("seaport") ||
                lower.Contains("marina") || lower.Contains("ferry") || lower.Contains("waterpump") ||
                lower.Contains("sewage") || lower.Contains("hydroelectric") || lower.Contains("shipyard") ||
                lower.Contains("quay") || lower.Contains("pier"))
                return true;

            if ((m_EM.HasComponent<CargoTransportStationData>(prefab) || m_EM.HasComponent<PublicTransportStationData>(prefab)) &&
                (lower.Contains("port") || lower.Contains("ship") || lower.Contains("dock") || lower.Contains("boat")))
                return true;

            return false;
        }

        public List<ExistingNetSegment> ScanNets(HashSet<Entity> ownEdges)
        {
            var result = new List<ExistingNetSegment>();
            using (var entities = m_NetsQuery.ToEntityArray(Allocator.Temp))
            {
                for (int i = 0; i < entities.Length; i++)
                {
                    Entity e = entities[i];
                    Entity prefab = m_EM.GetComponentData<PrefabRef>(e).m_Prefab;
                    if (prefab == Entity.Null) continue;

                    bool isRoad = m_EM.HasComponent<RoadData>(prefab);
                    bool isPath = m_EM.HasComponent<PathwayData>(prefab);
                    bool isWaterway = m_EM.HasComponent<WaterwayData>(prefab);
                    bool isRail = !isRoad && (m_EM.HasComponent<TrackData>(prefab) || m_EM.HasComponent<TrainTrack>(e) || m_EM.HasComponent<TramTrack>(e));
                    if (!isRoad && !isPath && !isWaterway && !isRail) continue;

                    string name = m_Prefabs.GetPrefabName(prefab) ?? "";
                    string lower = name.ToLowerInvariant();
                    if (!isWaterway && !isRail && (lower.Contains("invisible") || lower.Contains("marker"))) continue;

                    bool isQuayOrPier = !isWaterway && !isRail && (lower.Contains("quay") || lower.Contains("pier") || lower.Contains("boardwalk"));
                    float width = m_EM.HasComponent<NetGeometryData>(prefab)
                        ? m_EM.GetComponentData<NetGeometryData>(prefab).m_DefaultWidth
                        : (isWaterway ? 32f : isRoad ? 12f : isRail ? 10f : 4f);

                    var bez = m_EM.GetComponentData<Curve>(e).m_Bezier;
                    float3 mid = MathUtils.Position(bez, 0.5f);

                    result.Add(new ExistingNetSegment
                    {
                        EntityId = EncodeEntity(e),
                        Start = new Vec3(bez.a.x, bez.a.y, bez.a.z),
                        Mid = new Vec3(mid.x, mid.y, mid.z),
                        End = new Vec3(bez.d.x, bez.d.y, bez.d.z),
                        Width = width,
                        IsRoad = isRoad,
                        IsRail = isRail,
                        IsPathway = isPath,
                        IsQuayOrPier = isQuayOrPier,
                        IsWaterway = isWaterway,
                        IsGeneratedByUs = ownEdges != null && ownEdges.Contains(e),
                        IsPlacemakerOwned = IsPlacemakerEntity(e),
                    });
                }
            }
            return result;
        }

        /// <summary>
        /// Scans existing sand/beach Areas (including Placemaker Beach builds) so boardwalks curl smoothly into them
        /// and never paint redundant sand inside a Placemaker beach.
        /// </summary>
        public List<ExistingBeachArea> ScanExistingBeaches(HashSet<Entity> ownAreas)
        {
            var result = new List<ExistingBeachArea>();
            using (var entities = m_AreasQuery.ToEntityArray(Allocator.Temp))
            {
                for (int i = 0; i < entities.Length; i++)
                {
                    Entity e = entities[i];
                    if (ownAreas != null && ownAreas.Contains(e)) continue;
                    Entity prefab = m_EM.GetComponentData<PrefabRef>(e).m_Prefab;
                    if (prefab == Entity.Null) continue;
                    string lower = (m_Prefabs.GetPrefabName(prefab) ?? "").ToLowerInvariant();
                    if (!lower.Contains("sand") && !lower.Contains("beach")) continue;

                    var nodes = m_EM.GetBuffer<Game.Areas.Node>(e, true);
                    if (nodes.Length < 3) continue;

                    // Ignore tiny surface patches (< 80 m²) so only real beaches act as curl targets
                    int n = nodes.Length;
                    var ring = new Vec2[n];
                    Vec2 center = new Vec2(0f, 0f);
                    for (int k = 0; k < n; k++)
                    {
                        ring[k] = new Vec2(nodes[k].m_Position.x, nodes[k].m_Position.z);
                        center = center + ring[k];
                    }
                    center = center / n;
                    if (Math.Abs(Geom2D.SignedArea(ring)) < 80f) continue;

                    float maxR = 0f;
                    for (int k = 0; k < n; k++)
                    {
                        float d = Vec2.Distance(center, ring[k]);
                        if (d > maxR) maxR = d;
                    }

                    result.Add(new ExistingBeachArea
                    {
                        EntityId = EncodeEntity(e),
                        Center = center,
                        Radius = maxR,
                        Ring = ring,
                        IsPlacemakerOwned = IsPlacemakerEntity(e),
                    });
                }
            }
            return result;
        }

        /// <summary>
        /// Scans live non-Temp, non-Deleted Edges/Areas/Objects as LiveCandidates for manifest adoption or dedupe.
        /// </summary>
        public List<LiveCandidate> ScanLiveCandidates(
            bool includeEdges,
            bool includeAreas,
            bool includeObjects,
            HashSet<Entity> skipEdges = null,
            HashSet<Entity> skipAreas = null,
            HashSet<Entity> skipObjects = null,
            HashSet<string> filterSurfaceNames = null,
            HashSet<string> filterObjectNames = null,
            HashSet<string> filterNetNames = null)
        {
            var list = new List<LiveCandidate>(256);

            if (includeEdges)
            {
                using (var ents = m_NetsQuery.ToEntityArray(Allocator.Temp))
                {
                    for (int i = 0; i < ents.Length; i++)
                    {
                        Entity e = ents[i];
                        if (skipEdges != null && skipEdges.Contains(e)) continue;
                        Entity pf = m_EM.GetComponentData<PrefabRef>(e).m_Prefab;
                        if (pf == Entity.Null || !m_EM.HasComponent<PathwayData>(pf)) continue;
                        string name = m_Prefabs.GetPrefabName(pf) ?? "";
                        if (filterNetNames != null && !filterNetNames.Contains(name)) continue;
                        float3 mid = MathUtils.Position(m_EM.GetComponentData<Curve>(e).m_Bezier, 0.5f);
                        list.Add(new LiveCandidate
                        {
                            EntityId = EncodeEntity(e),
                            Kind = TrackedKind.Edge,
                            PrefabName = name,
                            Pos = new Vec2(mid.x, mid.z),
                            HasOwner = m_EM.HasComponent<Owner>(e),
                            IsTemp = false,
                        });
                    }
                }
            }

            if (includeAreas)
            {
                using (var ents = m_AreasQuery.ToEntityArray(Allocator.Temp))
                {
                    for (int i = 0; i < ents.Length; i++)
                    {
                        Entity e = ents[i];
                        if (skipAreas != null && skipAreas.Contains(e)) continue;
                        Entity pf = m_EM.GetComponentData<PrefabRef>(e).m_Prefab;
                        if (pf == Entity.Null) continue;
                        string name = m_Prefabs.GetPrefabName(pf) ?? "";
                        if (filterSurfaceNames != null && !filterSurfaceNames.Contains(name)) continue;

                        var nodes = m_EM.GetBuffer<Game.Areas.Node>(e, true);
                        if (nodes.Length < 3) continue;
                        float2 c = float2.zero;
                        for (int k = 0; k < nodes.Length; k++) c += nodes[k].m_Position.xz;
                        c /= nodes.Length;

                        list.Add(new LiveCandidate
                        {
                            EntityId = EncodeEntity(e),
                            Kind = TrackedKind.Area,
                            PrefabName = name,
                            Pos = new Vec2(c.x, c.y),
                            HasOwner = m_EM.HasComponent<Owner>(e),
                            IsTemp = false,
                        });
                    }
                }
            }

            if (includeObjects)
            {
                using (var ents = m_ObjectsQuery.ToEntityArray(Allocator.Temp))
                {
                    for (int i = 0; i < ents.Length; i++)
                    {
                        Entity e = ents[i];
                        if (skipObjects != null && skipObjects.Contains(e)) continue;
                        Entity pf = m_EM.GetComponentData<PrefabRef>(e).m_Prefab;
                        if (pf == Entity.Null) continue;
                        string name = m_Prefabs.GetPrefabName(pf) ?? "";
                        if (filterObjectNames != null && !filterObjectNames.Contains(name)) continue;

                        float3 pos = m_EM.GetComponentData<Game.Objects.Transform>(e).m_Position;
                        list.Add(new LiveCandidate
                        {
                            EntityId = EncodeEntity(e),
                            Kind = TrackedKind.Object,
                            PrefabName = name,
                            Pos = new Vec2(pos.x, pos.z),
                            HasOwner = m_EM.HasComponent<Owner>(e),
                            IsTemp = false,
                        });
                    }
                }
            }

            return list;
        }

        private BuildingZoneKind ClassifyBuildingZone(Entity prefab)
        {
            string pName = (m_Prefabs.GetPrefabName(prefab) ?? "").ToLowerInvariant();

            if (m_EM.HasComponent<SpawnableBuildingData>(prefab))
            {
                Entity zonePrefab = m_EM.GetComponentData<SpawnableBuildingData>(prefab).m_ZonePrefab;
                if (zonePrefab != Entity.Null && m_EM.HasComponent<ZoneData>(zonePrefab))
                {
                    var zd = m_EM.GetComponentData<ZoneData>(zonePrefab);
                    string zName = (m_Prefabs.GetPrefabName(zonePrefab) ?? "").ToLowerInvariant();

                    if (zd.m_AreaType == AreaType.Industrial)
                        return zd.IsOffice() ? BuildingZoneKind.Office : BuildingZoneKind.Industrial;

                    if (zd.m_AreaType == AreaType.Commercial)
                        return BuildingZoneKind.Commercial;

                    if (zd.m_AreaType == AreaType.Residential)
                    {
                        bool hasCommercial = m_EM.HasComponent<BuildingPropertyData>(prefab) &&
                                             m_EM.GetComponentData<BuildingPropertyData>(prefab).m_AllowedSold != Game.Economy.Resource.NoResource;
                        if (hasCommercial || zName.Contains("mixed"))
                            return BuildingZoneKind.Mixed;

                        int households = m_EM.HasComponent<BuildingPropertyData>(prefab)
                            ? m_EM.GetComponentData<BuildingPropertyData>(prefab).m_ResidentialProperties
                            : 1;

                        bool isHigh = zd.m_MaxHeight >= 25
                            || households >= 24
                            || zName.Contains("high")
                            || zName.Contains("tower")
                            || zName.Contains("hotel")
                            || zName.Contains("palace")
                            || zName.Contains("boardwalk");

                        if (isHigh) return BuildingZoneKind.HighRes;
                        if (zName.Contains("medium") || zName.Contains("row") || households >= 4)
                            return BuildingZoneKind.MedRes;
                        return BuildingZoneKind.LowRes;
                    }
                }
            }

            // Ploppables / signature / service / industrial buildings
            if (m_EM.HasComponent<ParkData>(prefab) || m_EM.HasComponent<SignatureBuildingData>(prefab))
                return BuildingZoneKind.CivicOrPark;

            if (pName.Contains("industrial") || pName.Contains("factory") || pName.Contains("warehouse") || pName.Contains("cannery") || pName.Contains("power") || pName.Contains("garbage") || pName.Contains("cargo"))
                return BuildingZoneKind.Industrial;

            if (pName.Contains("office") || pName.Contains("bank") || pName.Contains("exchange"))
                return BuildingZoneKind.Office;

            if (pName.Contains("commercial") || pName.Contains("shop") || pName.Contains("hotel") || pName.Contains("market") || pName.Contains("boardwalk"))
                return BuildingZoneKind.Commercial;

            if (pName.Contains("residential") || pName.Contains("house") || pName.Contains("cottage") || pName.Contains("villa"))
                return BuildingZoneKind.LowRes;

            return BuildingZoneKind.CivicOrPark;
        }

        public LiveWorldSampler CreateSampler() => new LiveWorldSampler(m_Terrain, m_Water);

        public static long EncodeEntity(Entity e) => ((long)e.Index << 32) | (uint)e.Version;
        public static Entity DecodeEntity(long id) => id == 0 ? Entity.Null : new Entity { Index = (int)(id >> 32), Version = (int)(uint)id };
    }

    public sealed class LiveWorldSampler : IWorldSampler
    {
        private TerrainHeightData m_TerrainData;
        private WaterSurfaceData<SurfaceWater> m_WaterData;
        private readonly bool m_HasWater;
        private readonly float m_SeaLevel;

        public LiveWorldSampler(TerrainSystem terrain, WaterSystem water)
        {
            m_TerrainData = terrain.GetHeightData(false);
            m_SeaLevel = water.SeaLevel;
            try
            {
                m_WaterData = water.GetSurfaceData(out JobHandle deps);
                deps.Complete();
                m_HasWater = m_WaterData.isCreated && m_WaterData.hasDepths;
            }
            catch
            {
                m_HasWater = false;
            }
        }

        public float TerrainHeight(Vec2 p) =>
            TerrainUtils.SampleHeight(ref m_TerrainData, new float3(p.X, 0f, p.Z));

        public float WaterDepth(Vec2 p)
        {
            if (!m_HasWater) return 0f;
            return WaterUtils.SampleDepth(ref m_WaterData, new float3(p.X, 0f, p.Z));
        }

        public float WaterSurfaceHeight(Vec2 p)
        {
            float th = TerrainHeight(p);
            if (!m_HasWater) return Math.Max(th, m_SeaLevel);
            float depth = WaterUtils.SampleDepth(ref m_WaterData, new float3(p.X, 0f, p.Z));
            return th + depth;
        }
    }
}
