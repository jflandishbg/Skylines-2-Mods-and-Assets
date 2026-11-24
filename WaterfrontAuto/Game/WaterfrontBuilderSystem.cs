using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text;
using Colossal.Mathematics;
using Colossal.Serialization.Entities;
using Game;
using Game.Areas;
using Game.Buildings;
using Game.City;
using Game.Common;
using Game.Net;
using Game.Objects;
using Game.Prefabs;
using Game.Simulation;
using Game.Tools;
using Unity.Collections;
using Unity.Entities;
using Unity.Mathematics;
using UnityEngine;
using WaterfrontAuto.Core;

namespace WaterfrontAuto.GameAdapter
{
    /// <summary>
    /// WaterfrontAuto v4 Builder System:
    /// - Runs BEFORE GenerateObjectsSystem/GenerateNodesSystem/GenerateAreasSystem in Modification1.
    /// - Zero idle CPU (watches ONLY Created/Deleted buildings + structural building fingerprint).
    /// - Persists owned entities in a vanilla-safe sidecar manifest (manifest-<cityKey>.txt) and adopts on load.
    /// - Spatial-hash dedupe fallback on emit so pre-v4 saves never stack duplicate surfaces/props.
    /// - Tight consume-once exact-prefab capture in ModificationEnd (never claims Owner or Temp entities).
    /// </summary>
    public partial class WaterfrontBuilderSystem : GameSystemBase
    {
        private PrefabSystem m_Prefabs;
        private TerrainSystem m_Terrain;
        private WaterSystem m_Water;
        private CityConfigurationSystem m_CityConfig;
        private PrefabCatalog m_Catalog;
        private WorldScanner m_Scanner;

        private EntityQuery m_BuildingStructuralDeltaQuery;
        private EntityQuery m_AllBuildingsQuery;
        private EntityQuery m_CreatedEdgesQuery;
        private EntityQuery m_CreatedAreasQuery;
        private EntityQuery m_CreatedObjectsQuery;

        private readonly HashSet<Entity> m_OwnedEdges = new HashSet<Entity>();
        private readonly HashSet<Entity> m_OwnedAreas = new HashSet<Entity>();
        private readonly HashSet<Entity> m_OwnedObjects = new HashSet<Entity>();
        private readonly List<OverrideZone> m_Overrides = new List<OverrideZone>();

        // Tight pending expectations (exact prefab name + position, consumed once!)
        private readonly List<PendingItem> m_PendingItems = new List<PendingItem>();
        internal bool ExpectingCapture;

        // Opt-in gradual terrain slope passes
        private readonly List<PlannedBeachGrade> m_PendingGrades = new List<PlannedBeachGrade>();
        private int m_GradePassesLeft;
        private Texture2D m_BeachBrushTex;

        // Lifecycle & structural change guard
        private bool m_GameLoaded;
        private bool m_ManifestAdopted;
        private bool m_Dirty;
        private bool m_ForceRebuild;
        private bool m_PendingClearOnly;
        private bool m_PendingRebuild;
        private bool m_PendingAdopt;
        private ulong m_LastBuildingFingerprint;
        private ulong m_LastPlanHash;
        private ulong m_LastGradedHash;
        private int m_DebounceFrames;
        private int m_DebounceElapsed;
        private int m_WarmupFrames;
        private int m_ClearWaitFrames;
        private bool m_RebuildAfterClear;
        private int m_LastUnmatchedCount;

        public WaterfrontConfig Config { get; private set; } = new WaterfrontConfig();
        public WaterfrontPlan LastPlan { get; private set; }
        public string StatusText { get; private set; } = "Idle";
        public string PerfText { get; private set; } = "Idle (0 ms)";
        public bool PlacemakerDetected => m_Scanner?.PlacemakerDetected ?? false;
        public int OverrideCount => m_Overrides.Count;
        public int LiveEdgesCount => m_OwnedEdges.Count;
        public int LiveAreasCount => m_OwnedAreas.Count;
        public int LiveObjectsCount => m_OwnedObjects.Count;
        public int TrackedEntityCount => m_OwnedEdges.Count + m_OwnedAreas.Count + m_OwnedObjects.Count;
        public int LastBeachCurls => LastPlan?.BeachCurls ?? 0;

        private static string DataDir => Path.Combine(Application.persistentDataPath, "ModsData", "WaterfrontAuto");
        private string OverridesPath => Path.Combine(DataDir, $"overrides-{GetCityKey()}.txt");
        private static string LegacyOverridesPath => Path.Combine(DataDir, "overrides.txt");

        protected override void OnCreate()
        {
            base.OnCreate();
            m_Prefabs = World.GetOrCreateSystemManaged<PrefabSystem>();
            m_Terrain = World.GetOrCreateSystemManaged<TerrainSystem>();
            m_Water = World.GetOrCreateSystemManaged<WaterSystem>();
            m_CityConfig = World.GetOrCreateSystemManaged<CityConfigurationSystem>();
            m_Catalog = new PrefabCatalog(EntityManager, m_Prefabs);
            m_Scanner = new WorldScanner(EntityManager, m_Prefabs, m_Terrain, m_Water);

            m_BuildingStructuralDeltaQuery = GetEntityQuery(new EntityQueryDesc
            {
                All = new[] { ComponentType.ReadOnly<Building>() },
                Any = new[] { ComponentType.ReadOnly<Created>(), ComponentType.ReadOnly<Deleted>() },
                None = new[] { ComponentType.ReadOnly<Temp>() },
            });

            m_AllBuildingsQuery = GetEntityQuery(new EntityQueryDesc
            {
                All = new[] { ComponentType.ReadOnly<Building>(), ComponentType.ReadOnly<Game.Objects.Transform>(), ComponentType.ReadOnly<PrefabRef>() },
                None = new[] { ComponentType.ReadOnly<Temp>(), ComponentType.ReadOnly<Deleted>() },
            });

            m_CreatedEdgesQuery = GetEntityQuery(ComponentType.ReadOnly<Edge>(), ComponentType.ReadOnly<Curve>(), ComponentType.ReadOnly<PrefabRef>(), ComponentType.ReadOnly<Created>(), ComponentType.Exclude<Temp>());
            m_CreatedAreasQuery = GetEntityQuery(ComponentType.ReadOnly<Area>(), ComponentType.ReadOnly<Game.Areas.Node>(), ComponentType.ReadOnly<PrefabRef>(), ComponentType.ReadOnly<Created>(), ComponentType.Exclude<Temp>());
            m_CreatedObjectsQuery = GetEntityQuery(ComponentType.ReadOnly<Game.Objects.Object>(), ComponentType.ReadOnly<Game.Objects.Transform>(), ComponentType.ReadOnly<PrefabRef>(), ComponentType.ReadOnly<Created>(), ComponentType.Exclude<Temp>());
        }

        protected override void OnDestroy()
        {
            if (m_BeachBrushTex != null)
            {
                UnityEngine.Object.Destroy(m_BeachBrushTex);
                m_BeachBrushTex = null;
            }
            base.OnDestroy();
        }

        protected override void OnGameLoadingComplete(Purpose purpose, GameMode mode)
        {
            base.OnGameLoadingComplete(purpose, mode);
            m_OwnedEdges.Clear();
            m_OwnedAreas.Clear();
            m_OwnedObjects.Clear();
            m_PendingItems.Clear();
            m_PendingGrades.Clear();
            m_GradePassesLeft = 0;
            ExpectingCapture = false;
            m_ClearWaitFrames = 0;
            m_RebuildAfterClear = false;
            m_PendingClearOnly = false;
            m_PendingRebuild = false;
            m_PendingAdopt = false;
            m_LastBuildingFingerprint = 0;
            m_LastPlanHash = 0;
            m_LastGradedHash = 0;
            m_DebounceElapsed = 0;
            m_LastUnmatchedCount = 0;
            m_ForceRebuild = false;
            m_ManifestAdopted = false;
            m_Catalog.Reset();
            LastPlan = null;

            m_GameLoaded = (mode & GameMode.Game) != 0;
            if (m_GameLoaded)
            {
                if (Mod.Settings != null) Config = Mod.Settings.ToConfig();
                LoadOverrides();
                m_WarmupFrames = 120;
                m_Dirty = Config.AutoEnabled;
                m_ForceRebuild = Config.AutoEnabled;
                StatusText = Config.AutoEnabled ? "Waiting for city to settle..." : "Auto paused (click Build / Refresh)";
                PerfText = "Idle (0 ms)";
            }
        }

        public void ApplyConfig(Func<WaterfrontConfig, WaterfrontConfig> mutator, bool triggerRebuild = true)
        {
            Config = mutator(Config.Clone());
            Mod.Settings?.From(Config);
            Mod.Settings?.ApplyAndSave();
            if (triggerRebuild && m_GameLoaded)
                RequestRebuild();
        }

        public void AddOverride(Vec2 center, float radius, WaterfrontMode mode)
        {
            m_Overrides.Add(new OverrideZone { Center = center, Radius = radius, Mode = mode });
            SaveOverrides();
            StatusText = $"Painted {mode} zone ({m_Overrides.Count} override(s))";
            RequestRebuild();
        }

        public void UndoLastOverride()
        {
            if (m_Overrides.Count == 0) return;
            m_Overrides.RemoveAt(m_Overrides.Count - 1);
            SaveOverrides();
            StatusText = $"Undid last override ({m_Overrides.Count} remaining)";
            RequestRebuild();
        }

        public void ClearOverrides()
        {
            m_Overrides.Clear();
            SaveOverrides();
            StatusText = "Cleared all shoreline overrides";
            RequestRebuild();
        }

        /// <summary>UI-safe: queues a rebuild to execute in Modification1 (never mutates ECS from UIUpdate).</summary>
        public void RequestRebuild()
        {
            if (!m_GameLoaded) return;
            m_PendingClearOnly = false;
            m_PendingRebuild = true;
            m_ForceRebuild = true;
            StatusText = "Refreshing waterfronts...";
        }

        /// <summary>UI-safe: queues a full clear to execute in Modification1 (never mutates ECS from UIUpdate).</summary>
        public void RequestClearAll()
        {
            if (!m_GameLoaded) return;
            m_PendingRebuild = false;
            m_PendingAdopt = false;
            m_PendingClearOnly = true;
            m_Dirty = false;
            m_ForceRebuild = false;
            m_RebuildAfterClear = false;
            StatusText = "Clearing generated waterfronts...";
        }

        /// <summary>UI-safe: queues Adopt/Clean to execute in Modification1.</summary>
        public void RequestAdoptOrClean()
        {
            if (!m_GameLoaded) return;
            m_PendingAdopt = true;
            StatusText = "Scanning for pre-v4 waterfront pieces...";
        }

        private void SyncDeckWidths()
        {
            m_Catalog.EnsureIndexed();
            Entity bw = Config.BoardwalkUseTimberPier
                ? (m_Catalog.Nets.TryGetValue(NetRole.Boardwalk, out var b) ? b : Entity.Null)
                : (m_Catalog.Nets.TryGetValue(NetRole.IndustrialQuay, out var q) ? q : Entity.Null);
            Entity qy = m_Catalog.Nets.TryGetValue(NetRole.IndustrialQuay, out var iq) ? iq : Entity.Null;
            Entity wk = m_Catalog.Nets.TryGetValue(NetRole.AccessSpur, out var sp) ? sp : Entity.Null;
            Config.BoardwalkDeckWidth = m_Catalog.WidthOf(bw, 8.0f);
            Config.QuayDeckWidth = m_Catalog.WidthOf(qy, 6.0f);
            Config.WalkwayWidth = m_Catalog.WidthOf(wk, 4.0f);
        }

        /// <summary>
        /// Manifest-less adoption / cleanup for pre-v4 saves: finds ALL untracked, unowned Edges, Areas, and Objects
        /// matching our prefab set within 8 m of detected chains/planned items and adopts them into tracking.
        /// </summary>
        public void AdoptOrCleanOldWaterfront()
        {
            if (!m_GameLoaded) return;
            var sw = Stopwatch.StartNew();
            try
            {
                SyncDeckWidths();
                EnsureManifestAdopted();
                PruneDeadTracked();

                var buildings = m_Scanner.ScanBuildings();
                var nets = m_Scanner.ScanNets(m_OwnedEdges);
                var beaches = m_Scanner.ScanExistingBeaches(m_OwnedAreas);
                var sampler = m_Scanner.CreateSampler();
                var plan = WaterfrontPlanner.Plan(buildings, nets, m_Overrides, sampler, Config, beaches);

                var dedupe = BuildDedupeIndex(includeEdges: true);
                int adoptedEdges = 0, adoptedAreas = 0, adoptedProps = 0;
                var matches = new List<long>(16);

                // 1. Adopt all untracked unowned WA edges near planned nets or chain spines (within 8 m)
                const float AdoptRadius = 8.0f;
                for (int i = 0; i < plan.Nets.Count; i++)
                {
                    var n = plan.Nets[i];
                    NetRole lookupRole = (n.Role == NetRole.Boardwalk && !Config.BoardwalkUseTimberPier) ? NetRole.IndustrialQuay : n.Role;
                    if (!m_Catalog.Nets.TryGetValue(lookupRole, out Entity pf) || pf == Entity.Null) continue;
                    Vec2 mid = (n.A.XZ + n.D.XZ) * 0.5f;
                    foreach (var knownNet in m_Catalog.KnownNetPrefabNames)
                    {
                        matches.Clear();
                        if (dedupe.FindAllWithin(TrackedKind.Edge, knownNet, mid, AdoptRadius, matches) == 0) continue;
                        for (int m = 0; m < matches.Count; m++)
                        {
                            Entity e = WorldScanner.DecodeEntity(matches[m]);
                            if (e != Entity.Null && EntityManager.Exists(e) && !EntityManager.HasComponent<Owner>(e) && m_OwnedEdges.Add(e))
                                adoptedEdges++;
                        }
                    }
                }

                // 2. Adopt ALL stacked untracked Areas matching our surface prefabs within 8 m
                for (int i = 0; i < plan.Surfaces.Count; i++)
                {
                    var s = plan.Surfaces[i];
                    if (s.Ring == null || s.Ring.Length < 3) continue;
                    Vec2 c = RingCentroid(s.Ring);
                    foreach (var knownSurf in m_Catalog.KnownSurfacePrefabNames)
                    {
                        matches.Clear();
                        if (dedupe.FindAllWithin(TrackedKind.Area, knownSurf, c, AdoptRadius, matches) == 0) continue;
                        for (int m = 0; m < matches.Count; m++)
                        {
                            Entity e = WorldScanner.DecodeEntity(matches[m]);
                            if (e != Entity.Null && EntityManager.Exists(e) && !EntityManager.HasComponent<Owner>(e) && m_OwnedAreas.Add(e))
                                adoptedAreas++;
                        }
                    }
                }

                // 3. Adopt ALL stacked untracked Objects matching our prop prefabs within 8 m
                for (int i = 0; i < plan.Props.Count; i++)
                {
                    var p = plan.Props[i];
                    Entity pf = m_Catalog.PickProp(p.Role, p.Seed);
                    if (pf == Entity.Null) continue;
                    string pfName = m_Catalog.NameOf(pf);
                    matches.Clear();
                    if (dedupe.FindAllWithin(TrackedKind.Object, pfName, p.Position.XZ, AdoptRadius, matches) > 0)
                    {
                        for (int m = 0; m < matches.Count; m++)
                        {
                            Entity e = WorldScanner.DecodeEntity(matches[m]);
                            if (e != Entity.Null && EntityManager.Exists(e) && !EntityManager.HasComponent<Owner>(e) && m_OwnedObjects.Add(e))
                                adoptedProps++;
                        }
                    }
                }

                WriteManifest();
                sw.Stop();
                int total = adoptedEdges + adoptedAreas + adoptedProps;
                StatusText = total > 0
                    ? $"Adopted {adoptedEdges} edge(s), {adoptedAreas} surface(s) & {adoptedProps} prop(s) into tracking"
                    : "No untracked pre-v4 waterfront pieces found";
                PerfText = $"Audit took {sw.ElapsedMilliseconds} ms · Idle (0 ms/frame)";
                Mod.Log.Info($"WaterfrontAuto Adopt/Clean: {StatusText} ({sw.ElapsedMilliseconds} ms).");
            }
            catch (Exception ex)
            {
                sw.Stop();
                StatusText = "Adopt/clean error (see log)";
                Mod.Log.Error(ex, "AdoptOrCleanOldWaterfront failed");
            }
        }

        protected override void OnUpdate()
        {
            if (!m_GameLoaded) return;

            if (m_GradePassesLeft > 0 && m_PendingGrades.Count > 0)
            {
                ApplyBeachGradePass();
                m_GradePassesLeft--;
                if (m_GradePassesLeft == 0)
                    m_PendingGrades.Clear();
            }

            if (m_WarmupFrames > 0)
            {
                m_WarmupFrames--;
                if (m_WarmupFrames == 0)
                    EnsureManifestAdopted();
                return;
            }

            // P0-1: All entity deletions & adoptions execute strictly in Modification1 (never UIUpdate)
            if (m_PendingClearOnly)
            {
                m_PendingClearOnly = false;
                EnsureManifestAdopted();
                m_PendingGrades.Clear();
                m_GradePassesLeft = 0;
                int removed = ClearGeneratedEntities();
                m_LastPlanHash = 0;
                WriteManifest();
                LastPlan = null;
                StatusText = removed > 0 ? $"Cleared {removed} generated pieces" : "Nothing generated to clear";
                PerfText = "Idle (0 ms)";
                return;
            }

            if (m_PendingAdopt)
            {
                m_PendingAdopt = false;
                AdoptOrCleanOldWaterfront();
                return;
            }

            if (m_PendingRebuild)
            {
                m_PendingRebuild = false;
                EnsureManifestAdopted();
                if (TrackedEntityCount > 0)
                {
                    ClearGeneratedEntities();
                    m_LastPlanHash = 0;
                    m_RebuildAfterClear = true;
                    m_ClearWaitFrames = 3;
                    StatusText = "Refreshing waterfronts...";
                    return;
                }
                m_Dirty = true;
                m_DebounceFrames = 1;
                m_DebounceElapsed = 0;
                StatusText = "Planning waterfronts...";
            }

            if (m_ClearWaitFrames > 0)
            {
                m_ClearWaitFrames--;
                if (m_ClearWaitFrames == 0 && m_RebuildAfterClear)
                {
                    m_RebuildAfterClear = false;
                    m_Dirty = true;
                    m_DebounceFrames = 1;
                    m_DebounceElapsed = 0;
                }
                return;
            }

            if (Config.AutoEnabled && !m_BuildingStructuralDeltaQuery.IsEmptyIgnoreFilter)
            {
                if (!m_Dirty) { m_Dirty = true; m_DebounceElapsed = 0; m_DebounceFrames = 90; }
                else if (m_DebounceElapsed < 240) m_DebounceFrames = 90;
            }

            if (!m_Dirty) return;

            if (m_DebounceFrames > 0)
            {
                m_DebounceFrames--;
                m_DebounceElapsed++;
                return;
            }

            if (Config.RespectPlacemaker && m_Scanner.IsPlacemakerBusy(World))
            {
                m_DebounceFrames = 30;
                return;
            }

            m_Dirty = false;
            m_DebounceElapsed = 0;
            EnsureManifestAdopted();

            ulong fp = ComputeBuildingFingerprint();
            if (!m_ForceRebuild && fp == m_LastBuildingFingerprint)
                return;

            bool forced = m_ForceRebuild;
            m_ForceRebuild = false;
            m_LastBuildingFingerprint = fp;

            // P0-2: On auto-triggers with existing waterfronts, check if the planned waterfront actually changed before clearing!
            if (!forced && TrackedEntityCount > 0)
            {
                SyncDeckWidths();
                PruneDeadTracked();
                var bld = m_Scanner.ScanBuildings();
                var nts = m_Scanner.ScanNets(m_OwnedEdges);
                var bch = m_Scanner.ScanExistingBeaches(m_OwnedAreas);
                var smp = m_Scanner.CreateSampler();
                var probePlan = WaterfrontPlanner.Plan(bld, nts, m_Overrides, smp, Config, bch);
                ulong probeHash = probePlan.ComputePlanHash();
                if (m_LastPlanHash != 0 && probeHash == m_LastPlanHash)
                    return;
            }

            if (TrackedEntityCount > 0)
            {
                ClearGeneratedEntities();
                m_LastPlanHash = 0;
                m_RebuildAfterClear = true;
                m_ForceRebuild = true;
                m_ClearWaitFrames = 3;
                return;
            }

            ExecutePlanAndEmit();
        }

        private ulong ComputeBuildingFingerprint()
        {
            ulong h = 1469598103934665603UL;
            using (var ents = m_AllBuildingsQuery.ToEntityArray(Allocator.Temp))
            {
                h += (ulong)ents.Length * 0x9E3779B97F4A7C15UL;
                for (int i = 0; i < ents.Length; i++)
                {
                    Entity e = ents[i];
                    var tr = EntityManager.GetComponentData<Game.Objects.Transform>(e);
                    Entity pf = EntityManager.GetComponentData<PrefabRef>(e).m_Prefab;
                    unchecked
                    {
                        ulong x = ((ulong)(uint)e.Index << 32) ^ (uint)pf.Index;
                        x ^= ((ulong)(uint)(int)math.round(tr.m_Position.x) << 16) ^ (uint)(int)math.round(tr.m_Position.z);
                        x ^= x >> 33; x *= 0xff51afd7ed558ccdUL; x ^= x >> 33;
                        h += x;
                    }
                }
            }
            return h;
        }

        private SpatialDedupeIndex BuildDedupeIndex(bool includeEdges = true)
        {
            var idx = new SpatialDedupeIndex();
            var live = m_Scanner.ScanLiveCandidates(
                includeEdges: includeEdges,
                includeAreas: true,
                includeObjects: true,
                skipEdges: m_OwnedEdges,
                skipAreas: m_OwnedAreas,
                skipObjects: m_OwnedObjects,
                filterSurfaceNames: m_Catalog.KnownSurfacePrefabNames,
                filterObjectNames: m_Catalog.KnownPropPrefabNames,
                filterNetNames: m_Catalog.KnownNetPrefabNames);
            for (int i = 0; i < live.Count; i++)
                idx.Add(live[i]);
            return idx;
        }

        private void ExecutePlanAndEmit()
        {
            var sw = Stopwatch.StartNew();
            m_PendingItems.Clear();
            try
            {
                SyncDeckWidths();
                PruneDeadTracked();

                var buildings = m_Scanner.ScanBuildings();
                var nets = m_Scanner.ScanNets(m_OwnedEdges);
                var beaches = m_Scanner.ScanExistingBeaches(m_OwnedAreas);
                var sampler = m_Scanner.CreateSampler();

                var plan = WaterfrontPlanner.Plan(buildings, nets, m_Overrides, sampler, Config, beaches);
                LastPlan = plan;
                m_LastPlanHash = plan.ComputePlanHash();

                if (plan.Nets.Count == 0 && plan.Surfaces.Count == 0 && plan.Props.Count == 0)
                {
                    sw.Stop();
                    WriteManifest();
                    StatusText = plan.SkippedPlacemaker > 0
                        ? $"No bare waterfront cliffs ({plan.SkippedPlacemaker} Placemaker lot(s) respected)"
                        : "No bare waterfront cliffs detected";
                    PerfText = $"Scanned in {sw.ElapsedMilliseconds} ms · Idle (0 ms/frame)";
                    return;
                }

                // Seaward beach grading (opt-in cliff slope OR automatic Placemaker beach extension) — runs at most once per unique plan hash
                m_PendingGrades.Clear();
                if (plan.BeachGrades.Count > 0 && m_LastPlanHash != m_LastGradedHash)
                {
                    bool hasPmExt = false;
                    for (int g = 0; g < plan.BeachGrades.Count; g++)
                        if (plan.BeachGrades[g].IsPlacemakerExtension) { hasPmExt = true; break; }
                    if (Config.EnableBeachTerrain || hasPmExt)
                    {
                        m_LastGradedHash = m_LastPlanHash;
                        m_PendingGrades.AddRange(plan.BeachGrades);
                        m_GradePassesLeft = hasPmExt ? 5 : 3;
                        ApplyBeachGradePass();
                        m_GradePassesLeft--;
                    }
                }

                var dedupe = BuildDedupeIndex(includeEdges: true);

                int netsEmitted = EmitNets(plan, dedupe, out int skippedDupNets);
                int surfacesEmitted = EmitSurfaces(plan, sampler, dedupe, out int skippedDupSurfaces);
                int propsEmitted = EmitProps(plan, sampler, dedupe, out int skippedDupProps);

                sw.Stop();
                PerfText = $"Built in {sw.ElapsedMilliseconds} ms · Idle (0 ms/frame)";
                StatusText = $"{plan.Chains.Count} waterfront(s): {plan.BeachSegments} home, {plan.BoardwalkSegments} boardwalk, {plan.IndustrialSegments} ind ({plan.BeachCurls} beach curls, {plan.FingerPiers} piers, {plan.AccessSpurs} access)";
                Mod.Log.Info($"WaterfrontAuto built in {sw.ElapsedMilliseconds} ms: {StatusText} | queued {netsEmitted} nets ({skippedDupNets} dup), {surfacesEmitted} surfaces ({skippedDupSurfaces} dup), {propsEmitted} props ({skippedDupProps} dup).");
            }
            catch (Exception ex)
            {
                sw.Stop();
                StatusText = "Build error (see WaterfrontAuto.log)";
                PerfText = "Error";
                Mod.Log.Error(ex, "WaterfrontAuto failed during ExecutePlanAndEmit");
            }
            finally
            {
                ExpectingCapture = m_PendingItems.Count > 0;
            }
        }

        private int EmitNets(WaterfrontPlan plan, SpatialDedupeIndex dedupe, out int skippedDuplicates)
        {
            int count = 0;
            skippedDuplicates = 0;
            for (int i = 0; i < plan.Nets.Count; i++)
            {
                var n = plan.Nets[i];
                NetRole lookupRole = (n.Role == NetRole.Boardwalk && !Config.BoardwalkUseTimberPier)
                    ? NetRole.IndustrialQuay
                    : n.Role;
                if (!m_Catalog.Nets.TryGetValue(lookupRole, out Entity prefab) || prefab == Entity.Null) continue;

                var curve = new Bezier4x3(
                    new float3(n.A.X, n.A.Y, n.A.Z),
                    new float3(n.B.X, n.B.Y, n.B.Z),
                    new float3(n.C.X, n.C.Y, n.C.Z),
                    new float3(n.D.X, n.D.Y, n.D.Z));

                float3 mid = MathUtils.Position(curve, 0.5f);
                string pfName = m_Catalog.NameOf(prefab);
                if (dedupe.HasDuplicate(TrackedKind.Edge, pfName, new Vec2(mid.x, mid.z), EntityMatcher.EdgeCaptureTolerance, out _))
                {
                    skippedDuplicates++;
                    continue;
                }

                float3 st = MathUtils.StartTangent(curve);
                float3 et = MathUtils.EndTangent(curve);
                if (math.lengthsq(st.xz) < 1e-5f) st = curve.d - curve.a;
                if (math.lengthsq(et.xz) < 1e-5f) et = curve.d - curve.a;

                bool wantQuayWall = !n.Elevated && (lookupRole == NetRole.IndustrialQuay || lookupRole == NetRole.BeachBoardwalkFallback || lookupRole == NetRole.Boardwalk);
                float e0 = n.Elevated ? math.max(0.8f, n.ElevationA) : 0f;
                float e1 = n.Elevated ? math.max(0.8f, n.ElevationB) : 0f;
                float2 startElev = wantQuayWall ? new float2(0f, math.max(2.5f, n.ElevationA)) : new float2(e0, e0);
                float2 endElev = wantQuayWall ? new float2(0f, math.max(2.5f, n.ElevationB)) : new float2(e1, e1);
                float2 courseElev = wantQuayWall ? new float2(0f, math.max(2.5f, (n.ElevationA + n.ElevationB) * 0.5f)) : new float2(e0, e1);
                CoursePosFlags elevFlag = n.Elevated ? (CoursePosFlags.ForceElevatedEdge | CoursePosFlags.ForceElevatedNode) : 0;

                var course = new NetCourse
                {
                    m_Curve = curve,
                    m_Length = MathUtils.Length(curve),
                    m_FixedIndex = -1,
                    m_Elevation = courseElev,
                    m_StartPosition = new CoursePos
                    {
                        m_Entity = Entity.Null,
                        m_Position = curve.a,
                        m_Elevation = startElev,
                        m_CourseDelta = 0f,
                        m_ParentMesh = -1,
                        m_Rotation = NetUtils.GetNodeRotation(st),
                        m_Flags = CoursePosFlags.IsFirst | CoursePosFlags.IsLeft | CoursePosFlags.IsRight | elevFlag,
                    },
                    m_EndPosition = new CoursePos
                    {
                        m_Entity = Entity.Null,
                        m_SplitPosition = 0f,
                        m_Position = curve.d,
                        m_Elevation = endElev,
                        m_CourseDelta = 1f,
                        m_ParentMesh = -1,
                        m_Rotation = NetUtils.GetNodeRotation(et),
                        m_Flags = CoursePosFlags.IsLast | CoursePosFlags.IsLeft | CoursePosFlags.IsRight | elevFlag,
                    },
                };

                Entity def = EntityManager.CreateEntity();
                EntityManager.AddComponentData(def, new CreationDefinition
                {
                    m_Prefab = prefab,
                    m_Flags = CreationFlags.Permanent,
                    m_RandomSeed = Geom2D.DeterministicSeed(curve.a.x, curve.a.z, i),
                });
                EntityManager.AddComponentData(def, course);
                if (wantQuayWall)
                {
                    // Force continuous vertical stone/brickwork quay retaining wall on the seaward (right) side
                    EntityManager.AddComponentData(def, new Upgraded
                    {
                        m_Flags = new CompositionFlags { m_Right = CompositionFlags.Side.Raised },
                    });
                }
                EntityManager.AddComponent<Updated>(def);
                EntityManager.AddComponent<Deleted>(def);

                m_PendingItems.Add(new PendingItem
                {
                    Kind = TrackedKind.Edge,
                    PrefabName = pfName,
                    Pos = new Vec2(mid.x, mid.z),
                });
                count++;
            }
            return count;
        }

        private int EmitSurfaces(WaterfrontPlan plan, LiveWorldSampler sampler, SpatialDedupeIndex dedupe, out int skippedDuplicates)
        {
            int count = 0;
            skippedDuplicates = 0;

            for (int i = 0; i < plan.Surfaces.Count; i++)
            {
                var s = plan.Surfaces[i];
                if (s.Ring == null || s.Ring.Length < 3) continue;
                if (!m_Catalog.Surfaces.TryGetValue(s.Role, out Entity prefab) || prefab == Entity.Null) continue;

                string pfName = m_Catalog.NameOf(prefab);
                Vec2 centroid = RingCentroid(s.Ring);

                // Fix 1B: Dedupe against existing live same-prefab Areas within 0.5m
                if (dedupe.HasDuplicate(TrackedKind.Area, pfName, centroid, EntityMatcher.AreaDedupeTolerance, out _))
                {
                    skippedDuplicates++;
                    continue;
                }

                Entity def = EntityManager.CreateEntity();
                EntityManager.AddComponentData(def, new CreationDefinition
                {
                    m_Prefab = prefab,
                    m_Flags = CreationFlags.Permanent,
                    m_RandomSeed = Geom2D.DeterministicSeed(s.Ring[0].X, s.Ring[0].Z, 500 + i),
                });

                DynamicBuffer<Game.Areas.Node> nodes = EntityManager.AddBuffer<Game.Areas.Node>(def);
                for (int k = 0; k < s.Ring.Length; k++)
                {
                    var p = s.Ring[k];
                    float y = sampler.TerrainHeight(p);
                    nodes.Add(new Game.Areas.Node(new float3(p.X, y, p.Z), float.MinValue));
                }
                nodes.Add(nodes[0]);

                EntityManager.AddComponent<Updated>(def);
                EntityManager.AddComponent<Deleted>(def);

                m_PendingItems.Add(new PendingItem
                {
                    Kind = TrackedKind.Area,
                    PrefabName = pfName,
                    Pos = centroid,
                });
                count++;
            }
            return count;
        }

        private int EmitProps(WaterfrontPlan plan, LiveWorldSampler sampler, SpatialDedupeIndex dedupe, out int skippedDuplicates)
        {
            int count = 0;
            skippedDuplicates = 0;

            for (int i = 0; i < plan.Props.Count; i++)
            {
                var p = plan.Props[i];
                Entity prefab = m_Catalog.PickProp(p.Role, p.Seed);
                if (prefab == Entity.Null) continue;

                string pfName = m_Catalog.NameOf(prefab);

                // Fix 1B: Dedupe against existing live same-prefab Objects within 1.0m
                if (dedupe.HasDuplicate(TrackedKind.Object, pfName, p.Position.XZ, EntityMatcher.ObjectDedupeTolerance, out _))
                {
                    skippedDuplicates++;
                    continue;
                }

                // Always use m_Elevation = 0f so CS2 snaps props flush to the quay/boardwalk/terrain surface
                // without double-elevating them into midair above the deck!
                float3 pos = new float3(p.Position.X, p.Position.Y, p.Position.Z);
                float groundY = sampler.TerrainHeight(p.Position.XZ);
                bool onDeck = p.Role == PropRole.BoardwalkBench || p.Role == PropRole.BoardwalkLamp ||
                              p.Role == PropRole.BoardwalkBollard || p.Role == PropRole.BoardwalkKiosk ||
                              p.Role == PropRole.BoardwalkGazebo || p.Role == PropRole.BoardwalkLifeBuoy ||
                              p.Role == PropRole.IndustrialBollard;
                if (!onDeck) pos.y = groundY;
                float elev = 0f;

                quaternion rot = quaternion.RotateY(p.Yaw);
                Entity def = EntityManager.CreateEntity();
                EntityManager.AddComponentData(def, new CreationDefinition
                {
                    m_Prefab = prefab,
                    m_Flags = CreationFlags.Permanent,
                    m_RandomSeed = p.Seed,
                });
                EntityManager.AddComponentData(def, new ObjectDefinition
                {
                    m_Position = pos,
                    m_LocalPosition = pos,
                    m_Rotation = rot,
                    m_LocalRotation = rot,
                    m_Scale = new float3(1f, 1f, 1f),
                    m_Elevation = elev,
                    m_Intensity = 1f,
                    m_Probability = 100,
                    m_ParentMesh = -1,
                    m_GroupIndex = -1,
                    m_PrefabSubIndex = -1,
                });
                EntityManager.AddComponent<Updated>(def);
                EntityManager.AddComponent<Deleted>(def);

                m_PendingItems.Add(new PendingItem
                {
                    Kind = TrackedKind.Object,
                    PrefabName = pfName,
                    Pos = new Vec2(pos.x, pos.z),
                });
                count++;
            }
            return count;
        }

        private void ApplyBeachGradePass()
        {
            Texture brushTex = m_Catalog.SoftBrushTexture ?? EnsureFallbackBrushTex();
            if (brushTex == null) return;

            for (int i = 0; i < m_PendingGrades.Count; i++)
            {
                var g = m_PendingGrades[i];
                // Keep brush circle strictly seaward of g.LandEdgeMid (never carves under buildings)
                float size = g.IsPlacemakerExtension
                    ? math.clamp(g.SlopeWidth * 0.95f, 12f, 24f)
                    : math.clamp(g.SlopeWidth * 0.9f, 8f, 18f);
                int steps = math.max(1, (int)math.ceil(g.Length / (size * 0.45f)));

                for (int s = 0; s < steps; s++)
                {
                    float frac = steps == 1 ? 0f : ((float)s / (steps - 1) - 0.5f);
                    Vec2 alongOffset = g.AlongDir * (frac * g.Length);
                    Vec2 startXZ = g.LandEdgeMid + g.SeawardDir * (size * 0.45f) + alongOffset;
                    Vec2 targetXZ = startXZ + g.SeawardDir * math.max(4f, g.SlopeWidth - size * 0.45f);
                    Vec2 midXZ = (startXZ + targetXZ) * 0.5f;

                    float3 start3 = new float3(startXZ.X, g.LandY, startXZ.Z);
                    float3 target3 = new float3(targetXZ.X, g.WaterY - (g.IsPlacemakerExtension ? 0.30f : 0.75f), targetXZ.Z);
                    float3 pos3 = new float3(midXZ.X, (start3.y + target3.y) * 0.5f, midXZ.Z);

                    var brush = new Game.Tools.Brush
                    {
                        m_Tool = Entity.Null,
                        m_Position = pos3,
                        m_Start = start3,
                        m_Target = target3,
                        m_Angle = 0f,
                        m_Size = size,
                        m_Strength = g.IsPlacemakerExtension ? 0.75f : 0.45f,
                        m_Opacity = 1f,
                    };
                    Bounds2 area = new Bounds2(
                        new float2(midXZ.X - size * 0.6f, midXZ.Z - size * 0.6f),
                        new float2(midXZ.X + size * 0.6f, midXZ.Z + size * 0.6f));

                    m_Terrain.ApplyBrush(TerraformingType.Slope, area, brush, brushTex);
                }
            }
        }

        private Texture2D EnsureFallbackBrushTex()
        {
            if (m_BeachBrushTex != null) return m_BeachBrushTex;
            const int N = 32;
            var tex = new Texture2D(N, N, TextureFormat.RGBA32, false, true);
            tex.wrapMode = TextureWrapMode.Clamp;
            tex.filterMode = FilterMode.Bilinear;
            var px = new UnityEngine.Color[N * N];
            for (int y = 0; y < N; y++)
                for (int x = 0; x < N; x++)
                {
                    float u = (x + 0.5f) / N * 2f - 1f;
                    float v = (y + 0.5f) / N * 2f - 1f;
                    float r = math.sqrt(u * u + v * v);
                    float a = math.saturate(1f - r);
                    a = a * a * (3f - 2f * a);
                    px[y * N + x] = new UnityEngine.Color(a, a, a, a);
                }
            tex.SetPixels(px);
            tex.Apply(false, false);
            m_BeachBrushTex = tex;
            return m_BeachBrushTex;
        }

        /// <summary>
        /// Fix 3: Tight exact-prefab, consume-once capture in ModificationEnd (never claims Owner or Temp entities).
        /// Persists updated manifest immediately after capture.
        /// </summary>
        internal void CaptureCreatedEntities()
        {
            if (!ExpectingCapture) return;
            ExpectingCapture = false;

            var candidates = new List<LiveCandidate>(m_PendingItems.Count + 32);

            if (!m_CreatedEdgesQuery.IsEmptyIgnoreFilter)
            {
                using (var ents = m_CreatedEdgesQuery.ToEntityArray(Allocator.Temp))
                {
                    for (int i = 0; i < ents.Length; i++)
                    {
                        Entity e = ents[i];
                        if (m_OwnedEdges.Contains(e)) continue;
                        Entity pf = EntityManager.GetComponentData<PrefabRef>(e).m_Prefab;
                        float3 mid = MathUtils.Position(EntityManager.GetComponentData<Curve>(e).m_Bezier, 0.5f);
                        candidates.Add(new LiveCandidate
                        {
                            EntityId = WorldScanner.EncodeEntity(e),
                            Kind = TrackedKind.Edge,
                            PrefabName = m_Catalog.NameOf(pf),
                            Pos = new Vec2(mid.x, mid.z),
                            HasOwner = EntityManager.HasComponent<Owner>(e),
                            IsTemp = EntityManager.HasComponent<Temp>(e),
                        });
                    }
                }
            }

            if (!m_CreatedAreasQuery.IsEmptyIgnoreFilter)
            {
                using (var ents = m_CreatedAreasQuery.ToEntityArray(Allocator.Temp))
                {
                    for (int i = 0; i < ents.Length; i++)
                    {
                        Entity e = ents[i];
                        if (m_OwnedAreas.Contains(e)) continue;
                        Entity pf = EntityManager.GetComponentData<PrefabRef>(e).m_Prefab;
                        var nodes = EntityManager.GetBuffer<Game.Areas.Node>(e, true);
                        if (nodes.Length < 3) continue;
                        float2 c = float2.zero;
                        for (int k = 0; k < nodes.Length; k++) c += nodes[k].m_Position.xz;
                        c /= nodes.Length;
                        candidates.Add(new LiveCandidate
                        {
                            EntityId = WorldScanner.EncodeEntity(e),
                            Kind = TrackedKind.Area,
                            PrefabName = m_Catalog.NameOf(pf),
                            Pos = new Vec2(c.x, c.y),
                            HasOwner = EntityManager.HasComponent<Owner>(e),
                            IsTemp = EntityManager.HasComponent<Temp>(e),
                        });
                    }
                }
            }

            if (!m_CreatedObjectsQuery.IsEmptyIgnoreFilter)
            {
                using (var ents = m_CreatedObjectsQuery.ToEntityArray(Allocator.Temp))
                {
                    for (int i = 0; i < ents.Length; i++)
                    {
                        Entity e = ents[i];
                        if (m_OwnedObjects.Contains(e)) continue;
                        Entity pf = EntityManager.GetComponentData<PrefabRef>(e).m_Prefab;
                        float3 p = EntityManager.GetComponentData<Game.Objects.Transform>(e).m_Position;
                        candidates.Add(new LiveCandidate
                        {
                            EntityId = WorldScanner.EncodeEntity(e),
                            Kind = TrackedKind.Object,
                            PrefabName = m_Catalog.NameOf(pf),
                            Pos = new Vec2(p.x, p.z),
                            HasOwner = EntityManager.HasComponent<Owner>(e),
                            IsTemp = EntityManager.HasComponent<Temp>(e),
                        });
                    }
                }
            }

            var claimed = EntityMatcher.MatchCreated(m_PendingItems, candidates, out int unmatched);
            int newEdges = 0, newAreas = 0, newObjs = 0;

            for (int i = 0; i < claimed.Count; i++)
            {
                Entity e = WorldScanner.DecodeEntity(claimed[i]);
                if (e == Entity.Null || !EntityManager.Exists(e)) continue;
                if (EntityManager.HasComponent<Edge>(e)) { if (m_OwnedEdges.Add(e)) newEdges++; }
                else if (EntityManager.HasComponent<Area>(e)) { if (m_OwnedAreas.Add(e)) newAreas++; }
                else { if (m_OwnedObjects.Add(e)) newObjs++; }
            }

            m_LastUnmatchedCount = unmatched;
            if (unmatched > 0)
            {
                Mod.Log.Info($"WaterfrontAuto capture: {unmatched} pending item(s) unmatched (tight tolerance or culled by game).");
                if (!StatusText.Contains("unmatched"))
                    StatusText += $" · {unmatched} unmatched";
            }

            m_PendingItems.Clear();
            WriteManifest();
            Mod.Log.Info($"WaterfrontAuto materialized: {newEdges} edges, {newAreas} surfaces, {newObjs} props (total live tracked: {TrackedEntityCount}).");
        }

        private string GetCityKey()
        {
            string raw = null;
            try { raw = m_CityConfig?.cityName; } catch { }
            if (string.IsNullOrWhiteSpace(raw)) raw = "default";
            var sb = new StringBuilder(raw.Length);
            for (int i = 0; i < raw.Length; i++)
            {
                char ch = raw[i];
                sb.Append(char.IsLetterOrDigit(ch) || ch == '-' || ch == '_' ? ch : '_');
            }
            string clean = sb.ToString().Trim('_');
            return clean.Length > 0 ? clean : "default";
        }

        private string ManifestPath => Path.Combine(DataDir, $"manifest-{GetCityKey()}.txt");

        private void EnsureManifestAdopted()
        {
            if (m_ManifestAdopted || !m_GameLoaded) return;
            m_ManifestAdopted = true;

            try
            {
                string path = ManifestPath;
                if (!File.Exists(path)) return;
                var rows = EntityMatcher.ParseManifest(File.ReadAllText(path));
                if (rows.Count == 0) return;

                var live = m_Scanner.ScanLiveCandidates(includeEdges: true, includeAreas: true, includeObjects: true);
                var matched = EntityMatcher.MatchManifest(rows, live, out int dropped);

                int eCount = 0, aCount = 0, oCount = 0;
                for (int i = 0; i < matched.Count; i++)
                {
                    Entity e = WorldScanner.DecodeEntity(matched[i]);
                    if (e == Entity.Null || !EntityManager.Exists(e)) continue;
                    if (EntityManager.HasComponent<Edge>(e)) { if (m_OwnedEdges.Add(e)) eCount++; }
                    else if (EntityManager.HasComponent<Area>(e)) { if (m_OwnedAreas.Add(e)) aCount++; }
                    else { if (m_OwnedObjects.Add(e)) oCount++; }
                }

                Mod.Log.Info($"WaterfrontAuto manifest ({GetCityKey()}): adopted {eCount} edges, {aCount} surfaces, {oCount} props ({dropped} stale row(s) dropped).");
            }
            catch (Exception ex)
            {
                Mod.Log.Warn("WaterfrontAuto could not adopt manifest: " + ex.Message);
            }
        }

        private void WriteManifest()
        {
            try
            {
                PruneDeadTracked();
                Directory.CreateDirectory(DataDir);
                var rows = new List<ManifestRow>(TrackedEntityCount);

                foreach (var e in m_OwnedEdges)
                {
                    if (!EntityManager.HasComponent<Curve>(e) || !EntityManager.HasComponent<PrefabRef>(e)) continue;
                    float3 mid = MathUtils.Position(EntityManager.GetComponentData<Curve>(e).m_Bezier, 0.5f);
                    rows.Add(new ManifestRow { Kind = TrackedKind.Edge, PrefabName = m_Catalog.NameOf(EntityManager.GetComponentData<PrefabRef>(e).m_Prefab), X = mid.x, Z = mid.z });
                }
                foreach (var e in m_OwnedAreas)
                {
                    if (!EntityManager.HasBuffer<Game.Areas.Node>(e) || !EntityManager.HasComponent<PrefabRef>(e)) continue;
                    var nodes = EntityManager.GetBuffer<Game.Areas.Node>(e, true);
                    if (nodes.Length < 3) continue;
                    float2 c = float2.zero;
                    for (int k = 0; k < nodes.Length; k++) c += nodes[k].m_Position.xz;
                    c /= nodes.Length;
                    rows.Add(new ManifestRow { Kind = TrackedKind.Area, PrefabName = m_Catalog.NameOf(EntityManager.GetComponentData<PrefabRef>(e).m_Prefab), X = c.x, Z = c.y });
                }
                foreach (var e in m_OwnedObjects)
                {
                    if (!EntityManager.HasComponent<Game.Objects.Transform>(e) || !EntityManager.HasComponent<PrefabRef>(e)) continue;
                    float3 p = EntityManager.GetComponentData<Game.Objects.Transform>(e).m_Position;
                    rows.Add(new ManifestRow { Kind = TrackedKind.Object, PrefabName = m_Catalog.NameOf(EntityManager.GetComponentData<PrefabRef>(e).m_Prefab), X = p.x, Z = p.z });
                }

                string target = ManifestPath;
                string tmp = target + ".tmp";
                File.WriteAllText(tmp, EntityMatcher.SerializeManifest(rows));
                if (File.Exists(target))
                {
                    try { File.Replace(tmp, target, null); }
                    catch { File.Delete(target); File.Move(tmp, target); }
                }
                else
                {
                    File.Move(tmp, target);
                }
            }
            catch (Exception ex)
            {
                Mod.Log.Warn("WaterfrontAuto could not write manifest: " + ex.Message);
            }
        }

        private int ClearGeneratedEntities()
        {
            PruneDeadTracked();
            int removed = 0;
            var touchedNodes = new HashSet<Entity>();

            foreach (var edge in m_OwnedEdges)
            {
                if (!EntityManager.Exists(edge) || EntityManager.HasComponent<Deleted>(edge)) continue;
                if (EntityManager.HasComponent<Edge>(edge))
                {
                    var ed = EntityManager.GetComponentData<Edge>(edge);
                    if (ed.m_Start != Entity.Null) touchedNodes.Add(ed.m_Start);
                    if (ed.m_End != Entity.Null) touchedNodes.Add(ed.m_End);
                }
                EntityManager.AddComponent<Deleted>(edge);
                removed++;
            }
            m_OwnedEdges.Clear();

            foreach (var node in touchedNodes)
            {
                if (!EntityManager.Exists(node) || EntityManager.HasComponent<Deleted>(node)) continue;
                bool hasLiveEdge = false;
                if (EntityManager.HasBuffer<ConnectedEdge>(node))
                {
                    var buf = EntityManager.GetBuffer<ConnectedEdge>(node, true);
                    for (int i = 0; i < buf.Length; i++)
                    {
                        Entity ce = buf[i].m_Edge;
                        if (ce != Entity.Null && EntityManager.Exists(ce) && !EntityManager.HasComponent<Deleted>(ce))
                        {
                            hasLiveEdge = true;
                            EntityManager.AddComponent<Updated>(ce);
                        }
                    }
                }
                if (hasLiveEdge) EntityManager.AddComponent<Updated>(node);
                else EntityManager.AddComponent<Deleted>(node);
            }

            foreach (var area in m_OwnedAreas)
            {
                if (!EntityManager.Exists(area) || EntityManager.HasComponent<Deleted>(area)) continue;
                EntityManager.AddComponent<Deleted>(area);
                removed++;
            }
            m_OwnedAreas.Clear();

            foreach (var obj in m_OwnedObjects)
            {
                if (!EntityManager.Exists(obj) || EntityManager.HasComponent<Deleted>(obj)) continue;
                EntityManager.AddComponent<Deleted>(obj);
                removed++;
            }
            m_OwnedObjects.Clear();

            return removed;
        }

        private void PruneDeadTracked()
        {
            m_OwnedEdges.RemoveWhere(e => !EntityManager.Exists(e) || EntityManager.HasComponent<Deleted>(e));
            m_OwnedAreas.RemoveWhere(e => !EntityManager.Exists(e) || EntityManager.HasComponent<Deleted>(e));
            m_OwnedObjects.RemoveWhere(e => !EntityManager.Exists(e) || EntityManager.HasComponent<Deleted>(e));
        }

        private static Vec2 RingCentroid(Vec2[] ring)
        {
            float sx = 0f, sz = 0f;
            for (int i = 0; i < ring.Length; i++) { sx += ring[i].X; sz += ring[i].Z; }
            return new Vec2(sx / ring.Length, sz / ring.Length);
        }

        private void SaveOverrides()
        {
            try
            {
                Directory.CreateDirectory(DataDir);
                var sb = new StringBuilder();
                for (int i = 0; i < m_Overrides.Count; i++)
                {
                    var o = m_Overrides[i];
                    sb.Append(o.Center.X.ToString("R", System.Globalization.CultureInfo.InvariantCulture)).Append(',')
                      .Append(o.Center.Z.ToString("R", System.Globalization.CultureInfo.InvariantCulture)).Append(',')
                      .Append(o.Radius.ToString("R", System.Globalization.CultureInfo.InvariantCulture)).Append(',')
                      .Append((int)o.Mode).Append('\n');
                }
                File.WriteAllText(OverridesPath, sb.ToString());
            }
            catch (Exception ex) { Mod.Log.Warn("Could not save overrides: " + ex.Message); }
        }

        private void LoadOverrides()
        {
            m_Overrides.Clear();
            try
            {
                string path = File.Exists(OverridesPath) ? OverridesPath : LegacyOverridesPath;
                if (!File.Exists(path)) return;
                var inv = System.Globalization.CultureInfo.InvariantCulture;
                foreach (var line in File.ReadAllLines(path))
                {
                    var parts = line.Split(',');
                    if (parts.Length < 4) continue;
                    if (float.TryParse(parts[0], System.Globalization.NumberStyles.Float, inv, out float x) &&
                        float.TryParse(parts[1], System.Globalization.NumberStyles.Float, inv, out float z) &&
                        float.TryParse(parts[2], System.Globalization.NumberStyles.Float, inv, out float r) &&
                        int.TryParse(parts[3], out int m))
                    {
                        m_Overrides.Add(new OverrideZone { Center = new Vec2(x, z), Radius = r, Mode = (WaterfrontMode)m });
                    }
                }
            }
            catch (Exception ex) { Mod.Log.Warn("Could not load overrides: " + ex.Message); }
        }
    }

    public partial class WaterfrontCaptureSystem : GameSystemBase
    {
        private WaterfrontBuilderSystem m_Builder;

        protected override void OnCreate()
        {
            base.OnCreate();
            m_Builder = World.GetOrCreateSystemManaged<WaterfrontBuilderSystem>();
        }

        protected override void OnUpdate()
        {
            if (m_Builder != null && m_Builder.ExpectingCapture)
                m_Builder.CaptureCreatedEntities();
        }
    }
}
