using System;
using System.Collections.Generic;
using Colossal.Mathematics;
using Game.Common;
using Game.Net;
using Game.Prefabs;
using Game.Simulation;
using Game.Tools;
using Game.UI;
using Unity.Collections;
using Unity.Entities;
using Unity.Jobs;
using Unity.Mathematics;
using Core = InterchangeStudio.Core;

namespace InterchangeStudio.Adapter
{
    /// <summary>
    /// The tool. Every frame: read the cursor, the click and what the game shows in red, hand them to the
    /// pure planner (Core.Planner.Frame), and write back what it says: preview definitions, apply, close.
    /// All the interchange logic is in Core; this file only talks to the game.
    /// </summary>
    public partial class StudioToolSystem : ToolBaseSystem
    {
        public override string toolID => "Interchange Studio";

        private ToolOutputBarrier m_Barrier;
        private DefaultToolSystem m_DefaultTool;
        private TerrainSystem m_Terrain;
        private PrefabSystem m_Prefabs;
        private NameSystem m_Names;
        private EntityQuery m_DefinitionQuery, m_RedQuery, m_Roads;
        private WorldMirror m_Mirror;
        private StudioErrorsOff m_ErrorsOff;
        private Core.Planner m_Planner;
        private int m_Frame, m_SettleFrames;
        private float3 m_LastHover;

        public Core.Planner Planner => m_Planner;
        public string StatusText => m_Planner?.StatusText ?? "";
        public int StatusKind => m_Planner?.StatusKind ?? 0;
        public string PreviewSummary => m_Planner?.PreviewSummary ?? "";
        public bool CanUndo => m_Planner?.CanUndo ?? false;
        public string UndoLabel => m_Planner?.UndoLabel ?? "";

        protected override void OnCreate()
        {
            base.OnCreate();
            m_Barrier = World.GetOrCreateSystemManaged<ToolOutputBarrier>();
            m_DefaultTool = World.GetOrCreateSystemManaged<DefaultToolSystem>();
            m_Terrain = World.GetOrCreateSystemManaged<TerrainSystem>();
            m_Prefabs = World.GetOrCreateSystemManaged<PrefabSystem>();
            m_Names = World.GetOrCreateSystemManaged<NameSystem>();
            m_DefinitionQuery = GetDefinitionQuery();
            m_RedQuery = GetEntityQuery(ComponentType.ReadOnly<Temp>(), ComponentType.ReadOnly<Game.Tools.Error>());
            m_Roads = GetEntityQuery(ComponentType.ReadOnly<Edge>(), ComponentType.ReadOnly<Curve>(), ComponentType.ReadOnly<Road>(),
                ComponentType.Exclude<Temp>(), ComponentType.Exclude<Deleted>());
            var tracks = GetEntityQuery(ComponentType.ReadOnly<Edge>(), ComponentType.ReadOnly<Curve>(), ComponentType.ReadOnly<TrainTrack>(),
                ComponentType.Exclude<Road>(), ComponentType.Exclude<Temp>(), ComponentType.Exclude<Deleted>());
            var roadPrefabs = GetEntityQuery(ComponentType.ReadOnly<PrefabData>(), ComponentType.ReadOnly<RoadData>(), ComponentType.ReadOnly<NetGeometryData>());
            var others = GetEntityQuery(ComponentType.ReadOnly<Edge>(), ComponentType.ReadOnly<Curve>(), ComponentType.ReadOnly<PrefabRef>(),
                ComponentType.Exclude<Road>(), ComponentType.Exclude<TrainTrack>(), ComponentType.Exclude<Temp>(), ComponentType.Exclude<Deleted>());
            var cityConfig = World.GetOrCreateSystemManaged<Game.City.CityConfigurationSystem>();
            m_Mirror = new WorldMirror(EntityManager, m_Prefabs, cityConfig, m_Roads, tracks, roadPrefabs, others);
            m_ErrorsOff = World.GetOrCreateSystemManaged<StudioErrorsOff>();
        }

        public override PrefabBase GetPrefab() => null;
        public override bool TrySetPrefab(PrefabBase prefab) => false;

        public override void InitializeRaycast()
        {
            base.InitializeRaycast();
            m_ToolRaycastSystem.typeMask = TypeMask.Net | TypeMask.Terrain;
            m_ToolRaycastSystem.netLayerMask = Layer.Road | Layer.TrainTrack;
        }

        protected override void OnStartRunning()
        {
            base.OnStartRunning();
            applyAction.shouldBeEnabled = true;
            cancelAction.shouldBeEnabled = true;
            EnsurePlanner(force: true);
            m_Planner.Abandon();
        }

        public void Toggle()
        {
            bool on = m_ToolSystem.activeTool != this;
            m_ToolSystem.activeTool = on ? (ToolBaseSystem)this : m_DefaultTool;
            Mod.log.Info("Interchange Studio " + (on ? "on" : "off"));
        }

        /// <summary>Change a setting. The planner gets a new config as a whole; the change is saved.</summary>
        public void Configure(Func<Core.PlanConfig, Core.PlanConfig> change)
        {
            EnsurePlanner(force: false);
            bool wasStage2 = m_Planner.Stage2Waiting;
            m_Planner.Cfg = change(m_Planner.Cfg).Supported();
            m_Planner.Abandon();
            if (wasStage2)
            {
                m_Planner.StatusKind = 2;
                m_Planner.StatusText = "Settings changed; automatic ramps cancelled. Hover the crossing to add ramps with the new settings.";
            }
            Mod.Settings?.From(m_Planner.Cfg);
            Mod.Settings?.ApplyAndSave();
        }

        public void UndoLast()
        {
            EnsurePlanner(force: true);
            m_Planner.RequestUndo();
        }

        void EnsurePlanner(bool force)
        {
            if (m_Planner == null)
            {
                var names = new Core.NameSystem { Lookup = e => { var u = WorldMirror.U(e); return EntityManager.Exists(u) ? m_Names.GetRenderedLabelName(u) : null; } };
                var water = new GameWater(World.GetOrCreateSystemManaged<WaterSystem>());
                var terrain = new Core.TerrainSystem { Terrain = new GameTerrain(m_Terrain), WaterDepth = water.Depth };
                m_Planner = new Core.Planner(new Core.NetWorld(), terrain, names, new GameLog()) { Cfg = Mod.Settings?.ToConfig() ?? new Core.PlanConfig() };
                force = true;
            }
            var fresh = m_Mirror.Refresh(force);
            if (fresh != null) m_Planner.SetWorld(fresh);
        }

        protected override JobHandle OnUpdate(JobHandle inputDeps)
        {
            applyMode = ApplyMode.Clear;
            m_Frame++;
            m_ErrorsOff.Arm();      // this frame's preview is judged on collisions only (Game/ErrorGate.cs)
            try
            {
                // keep the mirror current: every frame right after a build or while Stage 2 waits for the new bridge, rarely otherwise
                if (m_Planner == null || m_SettleFrames > 0 || m_Planner.Stage2Waiting || m_Frame % 30 == 0) { EnsurePlanner(force: false); if (m_SettleFrames > 0) m_SettleFrames--; }
            }
            catch (Exception e) { Mod.log.Error(e, "Reading the road network"); }

            var input = new Core.FrameInput
            {
                Apply = applyAction.WasPressedThisFrame(),
                Cancel = cancelAction.WasPressedThisFrame(),
                AllowApply = GetAllowApply(),
            };
            if (GetRaycastResult(out Entity hitEntity, out RaycastHit hit))
            {
                bool isNet = EntityManager.HasComponent<Edge>(hitEntity) || EntityManager.HasComponent<Game.Net.Node>(hitEntity);
                if (isNet)
                {
                    input.HasHit = true;
                    // a road the mirror hasn't seen yet (just drawn by the player): catch up now, not in half a second
                    if (!m_Planner.EntityManager.Exists(WorldMirror.C(hitEntity)))
                        try { EnsurePlanner(force: false); } catch (Exception e) { Mod.log.Error(e, "Reading the road network"); }
                    input.Hit = new Core.RaycastHit { m_HitEntity = WorldMirror.C(hitEntity), m_HitPosition = hit.m_HitPosition, m_CurvePosition = hit.m_CurvePosition };
                }
                else
                {
                    input.HasTerrainHit = true;
                    input.TerrainPos = hit.m_HitPosition;
                }
                m_LastHover = hit.m_HitPosition;
            }
            ReadRed(input.Red);

            if (m_Test != null) return SelfTestFrame(input, inputDeps);

            Core.FrameOutput o;
            try { o = m_Planner.Frame(input); }
            catch (Exception e) { Mod.log.Error(e, "Interchange Studio"); o = new Core.FrameOutput(); }

            if (o.Close) { m_ToolSystem.activeTool = m_DefaultTool; return DestroyDefinitions(m_DefinitionQuery, m_Barrier, inputDeps); }
            if (o.ApplyNow) { applyMode = ApplyMode.Apply; m_SettleFrames = 40; return DestroyDefinitions(m_DefinitionQuery, m_Barrier, inputDeps); }
            inputDeps = DestroyDefinitions(m_DefinitionQuery, m_Barrier, inputDeps);
            if (o.Emit != null)
            {
                try { Emit(o.Emit, m_Barrier.CreateCommandBuffer()); }
                catch (Exception e) { Mod.log.Error(e, "Drawing the preview"); }
            }
            return inputDeps;
        }

        /* ================= the self-test (Core/SelfTest.cs): preview only, never builds ================= */

        private Core.SelfTestRun m_Test;
        private bool m_TestAuto, m_AutoChecked;
        private int m_TestCase = -1, m_GameFrames;
        public bool TestRunning => m_Test != null;

        static string DataDir => System.IO.Path.Combine(UnityEngine.Application.persistentDataPath, "ModsData", "InterchangeStudio");

        /// <summary>Start the self-test on the loaded city (from the panel, or automatically when the flag file is there).</summary>
        public void StartSelfTest(bool auto)
        {
            if (m_Test != null) return;
            try
            {
                EnsurePlanner(force: true);
                m_Test = new Core.SelfTestRun(m_Planner);
                m_TestAuto = auto; m_TestCase = -1;
                Mod.log.Info($"Self-test started ({(auto ? "automatically" : "from the panel")}): {m_Test.Count} cases, about {m_Test.Count * Core.SelfTestRun.FramesPerCase / 60 + 1} s");
                if (m_Test.Done) { FinishSelfTest(); return; }
                m_ToolSystem.activeTool = this;
            }
            catch (Exception e) { Mod.log.Error(e, "Starting the self-test"); m_Test = null; }
        }

        JobHandle SelfTestFrame(Core.FrameInput real, JobHandle inputDeps)
        {
            inputDeps = DestroyDefinitions(m_DefinitionQuery, m_Barrier, inputDeps);
            if (real.Cancel || real.Apply) { m_Test.Abort(); FinishSelfTest(); return inputDeps; }     // the player takes over
            try
            {
                if (m_Test.Index != m_TestCase) { m_TestCase = m_Test.Index; Look(m_Test.Focus); }
                var o = m_Planner.Frame(m_Test.Input(real.Red, real.AllowApply));
                m_Test.Observe(o);
                if (m_Test.Done) { FinishSelfTest(); return inputDeps; }
                if (o.Emit != null) Emit(o.Emit, m_Barrier.CreateCommandBuffer());
            }
            catch (Exception e) { Mod.log.Error(e, "Self-test"); m_Test.Abort(); FinishSelfTest(); }
            return inputDeps;
        }

        void FinishSelfTest()
        {
            var test = m_Test; m_Test = null;
            if (test == null) return;
            string report = test.Report(), path = "";
            try
            {
                System.IO.Directory.CreateDirectory(DataDir);
                path = System.IO.Path.Combine(DataDir, $"selftest-{test.Started:yyyy-MM-dd_HHmm}.txt");
                System.IO.File.WriteAllText(path, report);
            }
            catch (Exception e) { Mod.log.Error(e, "Saving the self-test report"); }
            foreach (var line in report.Split('\n')) if (line.Trim().Length > 0) Mod.log.Info("Self-test: " + line.TrimEnd());
            if (m_Planner != null) { m_Planner.StatusText = $"Self-test finished: {report.Split('\n')[2].Trim()} Report saved to {path}"; m_Planner.StatusKind = 3; }
            if (m_TestAuto && m_ToolSystem.activeTool == this) m_ToolSystem.activeTool = m_DefaultTool;
        }

        /// <summary>Called every UI frame: once per session, half a minute into a loaded city, run the self-test if its flag file is there.</summary>
        public void TickAutoSelfTest()
        {
            if (m_AutoChecked) return;
            if ((Game.SceneFlow.GameManager.instance.gameMode & Game.GameMode.Game) == 0) { m_GameFrames = 0; return; }
            if (++m_GameFrames < 1800) return;
            m_AutoChecked = true;
            try
            {
                string flag = System.IO.Path.Combine(DataDir, "selftest.flag");
                if (!System.IO.File.Exists(flag)) return;
                System.IO.File.Delete(flag);                       // one run per flag
                if (m_Roads.CalculateEntityCount() < 10) { Mod.log.Info("Self-test flag found, but this city has almost no roads; skipped"); return; }
                StartSelfTest(auto: true);
            }
            catch (Exception e) { Mod.log.Error(e, "Self-test flag"); }
        }

        protected override void OnStopRunning()
        {
            if (m_Test != null) { m_Test.Abort(); FinishSelfTest(); }
            m_Planner?.Abandon();                // nothing unfinished may build after the tool is closed
            base.OnStopRunning();
        }

        void Look(Unity.Mathematics.float3 at)
        {
            try { if (Game.CameraController.TryGet(out var cam) && cam != null) { cam.pivot = at; cam.zoom = 420f; } } catch { }
        }

        /* ================= writing a plan as preview definitions ================= */

        bool Live(Entity e) => e != Entity.Null && EntityManager.Exists(e) && !EntityManager.HasComponent<Temp>(e) && !EntityManager.HasComponent<Deleted>(e);

        void Emit(Core.Planner.Preview pv, EntityCommandBuffer cb)
        {
            // the mirror can be a moment behind the game: never emit a plan that refers to something gone
            foreach (var s in pv.Specs)
            {
                if (s.Delete ? !Live(WorldMirror.U(s.Original)) :
                    (s.StartEntity != Core.Entity.Null && !Live(WorldMirror.U(s.StartEntity))) || (s.EndEntity != Core.Entity.Null && !Live(WorldMirror.U(s.EndEntity))))
                { m_SettleFrames = 5; return; }
            }
            foreach (var s in pv.Specs)
            {
                if (s.Delete) { DeleteDef(cb, WorldMirror.U(s.Original)); continue; }
                var c = s.Curve;
                float3 st = MathUtils.StartTangent(c), et = MathUtils.EndTangent(c);
                if (math.lengthsq(st.xz) < 1e-6f) st = c.d - c.a;
                if (math.lengthsq(et.xz) < 1e-6f) et = c.d - c.a;
                var course = new NetCourse { m_Curve = c, m_Length = MathUtils.Length(c), m_FixedIndex = -1, m_Elevation = new float2(s.E0, s.E1) };
                course.m_StartPosition = new CoursePos
                {
                    m_Entity = WorldMirror.U(s.StartEntity), m_SplitPosition = s.StartSplit, m_Position = c.a, m_Elevation = new float2(s.E0, s.E0),
                    m_CourseDelta = 0f, m_ParentMesh = -1, m_Rotation = NetUtils.GetNodeRotation(st),
                    m_Flags = (s.JoinStart ? 0 : CoursePosFlags.IsFirst) | CoursePosFlags.IsRight | CoursePosFlags.IsLeft,
                };
                course.m_EndPosition = new CoursePos
                {
                    m_Entity = WorldMirror.U(s.EndEntity), m_SplitPosition = s.EndSplit, m_Position = c.d, m_Elevation = new float2(s.E1, s.E1),
                    m_CourseDelta = 1f, m_ParentMesh = -1, m_Rotation = NetUtils.GetNodeRotation(et),
                    m_Flags = (s.JoinEnd ? 0 : CoursePosFlags.IsLast) | CoursePosFlags.IsRight | CoursePosFlags.IsLeft,
                };
                Entity e = cb.CreateEntity();
                cb.AddComponent(e, new CreationDefinition { m_Prefab = WorldMirror.U(s.Prefab), m_RandomSeed = (int)(math.hash(c.a) & 0x7fffffff) });
                cb.AddComponent(e, default(Updated));
                cb.AddComponent(e, course);
                if (s.HasUpgrade)
                    cb.AddComponent(e, new Upgraded { m_Flags = new CompositionFlags { m_General = (CompositionFlags.General)s.Upgrade.m_General, m_Left = (CompositionFlags.Side)s.Upgrade.m_Left, m_Right = (CompositionFlags.Side)s.Upgrade.m_Right } });
            }
        }

        void DeleteDef(EntityCommandBuffer cb, Entity edge)
        {
            var ed = EntityManager.GetComponentData<Edge>(edge);
            var cv = EntityManager.GetComponentData<Curve>(edge);
            Entity e = cb.CreateEntity();
            cb.AddComponent(e, new CreationDefinition { m_Original = edge, m_Flags = CreationFlags.Delete });
            cb.AddComponent(e, default(Updated));
            cb.AddComponent(e, new NetCourse
            {
                m_Curve = cv.m_Bezier, m_Length = cv.m_Length, m_FixedIndex = -1,
                m_StartPosition = new CoursePos { m_Entity = ed.m_Start, m_Position = cv.m_Bezier.a, m_Rotation = NetUtils.GetNodeRotation(MathUtils.StartTangent(cv.m_Bezier)), m_CourseDelta = 0f },
                m_EndPosition = new CoursePos { m_Entity = ed.m_End, m_Position = cv.m_Bezier.d, m_Rotation = NetUtils.GetNodeRotation(MathUtils.EndTangent(cv.m_Bezier)), m_CourseDelta = 1f },
            });
        }

        /* ================= what the game shows in red ================= */

        void ReadRed(List<Core.RedItem> into)
        {
            if (m_RedQuery.IsEmptyIgnoreFilter) return;
            using (var ents = m_RedQuery.ToEntityArray(Allocator.Temp))
                for (int i = 0; i < ents.Length && into.Count < 40; i++)
                    into.Add(new Core.RedItem { What = DescribeRed(ents[i], out float3 at), At = at });
        }

        string DescribeRed(Entity e, out float3 at)
        {
            at = m_LastHover;
            Entity subject = e; string role = "";
            if (!EntityManager.HasComponent<Edge>(e) && !EntityManager.HasComponent<Game.Net.Node>(e) && EntityManager.HasComponent<Owner>(e))
            {
                if (EntityManager.HasComponent<Game.Objects.Transform>(e)) at = EntityManager.GetComponentData<Game.Objects.Transform>(e).m_Position;
                subject = EntityManager.GetComponentData<Owner>(e).m_Owner; role = "a pillar or part of ";
            }
            if (EntityManager.HasComponent<Edge>(subject) && EntityManager.HasComponent<Curve>(subject)) { if (role == "") at = MathUtils.Position(EntityManager.GetComponentData<Curve>(subject).m_Bezier, 0.5f); }
            else if (EntityManager.HasComponent<Game.Net.Node>(subject)) { if (role == "") at = EntityManager.GetComponentData<Game.Net.Node>(subject).m_Position; }
            else if (EntityManager.HasComponent<Game.Objects.Transform>(subject) && role == "") at = EntityManager.GetComponentData<Game.Objects.Transform>(subject).m_Position;
            bool existing = EntityManager.HasComponent<Temp>(subject) && EntityManager.GetComponentData<Temp>(subject).m_Original != Entity.Null;
            string name = EntityManager.HasComponent<PrefabRef>(subject) ? m_Prefabs.GetPrefabName(EntityManager.GetComponentData<PrefabRef>(subject).m_Prefab) : "something";
            string kind = EntityManager.HasComponent<Game.Net.Node>(subject) ? "a junction" : EntityManager.HasComponent<Edge>(subject) ? (existing ? "the existing " : "a new ") + name : name;
            string why = Why(e);
            if (why == "" && subject != e) why = Why(subject);
            return role + kind + why;
        }

        /// <summary>Why the game shows it red, from its warning icons (each icon's prefab carries the error type).</summary>
        string Why(Entity e)
        {
            if (!EntityManager.HasBuffer<Game.Notifications.IconElement>(e)) return "";
            var reasons = new List<string>();
            var icons = EntityManager.GetBuffer<Game.Notifications.IconElement>(e, true);
            for (int i = 0; i < icons.Length; i++)
            {
                var icon = icons[i].m_Icon;
                if (!EntityManager.HasComponent<PrefabRef>(icon)) continue;
                var prefab = EntityManager.GetComponentData<PrefabRef>(icon).m_Prefab;
                if (!EntityManager.HasComponent<ToolErrorData>(prefab)) continue;
                string r = Words(EntityManager.GetComponentData<ToolErrorData>(prefab).m_Error);
                if (!reasons.Contains(r)) reasons.Add(r);
            }
            return reasons.Count == 0 ? "" : " (" + string.Join(", ", reasons) + ")";
        }

        static string Words(ErrorType t)
        {
            switch (t)
            {
                case ErrorType.OverlapExisting: return "overlaps something already there";
                case ErrorType.NotEnoughClearance: return "not enough clearance";
                case ErrorType.NotEnoughMoney: return "not enough money";
                case ErrorType.InWater: return "in water";
                case ErrorType.ExceedsCityLimits: return "outside the city limits";
                case ErrorType.AlreadyExists: return "already exists";
                case ErrorType.SteepSlope: return "too steep";
                case ErrorType.InvalidShape: return "invalid shape";
                default: return t.ToString();
            }
        }

        /* ================= names and camera (called from the UI system) ================= */

        /// <summary>Give rebuilt roads their names back, once the game has settled. Must run in the UI update.</summary>
        public void TickNames()
        {
            var jobs = m_Planner?.TakeRenames();
            if (jobs == null || jobs.Count == 0) return;
            try
            {
                using (var ents = m_Roads.ToEntityArray(Allocator.Temp))
                    foreach (var job in jobs)
                    {
                        Entity best = Entity.Null; float bd = 10f;
                        foreach (var e in ents)
                        {
                            var prefab = EntityManager.GetComponentData<PrefabRef>(e).m_Prefab;
                            bool hw = EntityManager.HasComponent<RoadData>(prefab) && (EntityManager.GetComponentData<RoadData>(prefab).m_Flags & Game.Prefabs.RoadFlags.UseHighwayRules) != 0;
                            if (hw != job.highway) continue;
                            var bez = EntityManager.GetComponentData<Curve>(e).m_Bezier;
                            float d = MathUtils.Distance(bez.xz, job.pos.xz, out float t);
                            if (d >= bd) continue;
                            float dy = math.abs(MathUtils.Position(bez, t).y - job.pos.y);
                            if (dy > 5f) continue;
                            bd = d; best = e;
                        }
                        if (best == Entity.Null || !EntityManager.HasComponent<Aggregated>(best)) continue;
                        var agg = EntityManager.GetComponentData<Aggregated>(best).m_Aggregate;
                        if (agg == Entity.Null || !EntityManager.Exists(agg)) continue;
                        if (m_Names.GetRenderedLabelName(agg) != job.name) { m_Names.SetCustomName(agg, job.name); Mod.log.Info($"  renamed rebuilt road back to {job.name}"); }
                    }
            }
            catch (Exception e) { Mod.log.Error(e, "Restoring road names"); }
        }

        public void FindNext()
        {
            EnsurePlanner(force: false);
            Game.CameraController cam = null;
            bool hasCam = Game.CameraController.TryGet(out cam) && cam != null;
            var at = m_Planner.FindNextTarget(hasCam ? (float3)cam.pivot : m_LastHover);
            if (at.HasValue && hasCam) { cam.pivot = at.Value; if (cam.zoom > 700f) cam.zoom = 350f; }
        }
    }

    /// <summary>Water depth for the planner, from the game's water surface (fetched at most once a frame).</summary>
    sealed class GameWater
    {
        readonly WaterSystem m_W;
        WaterSurfaceData<SurfaceWater> m_Data; int m_Frame = -1; bool m_Ok;
        public GameWater(WaterSystem w) { m_W = w; }
        public float Depth(float3 p)
        {
            try
            {
                if (m_Frame != UnityEngine.Time.frameCount)
                {
                    m_Frame = UnityEngine.Time.frameCount;
                    m_Data = m_W.GetSurfaceData(out JobHandle deps);
                    deps.Complete();
                    m_Ok = m_Data.isCreated && m_Data.hasDepths;
                }
                return m_Ok ? WaterUtils.SampleDepth(ref m_Data, p) : 0f;
            }
            catch { return 0f; }
        }
    }

    /// <summary>Terrain height for the planner, read from the game's height map (cached at most once a frame).</summary>
    sealed class GameTerrain : Core.ITerrain
    {
        readonly TerrainSystem m_T;
        TerrainHeightData m_Data; int m_Frame = -1;
        public GameTerrain(TerrainSystem t) { m_T = t; }
        public float Height(float3 p)
        {
            if (m_Frame != UnityEngine.Time.frameCount) { m_Frame = UnityEngine.Time.frameCount; m_Data = m_T.GetHeightData(false); }
            return TerrainUtils.SampleHeight(ref m_Data, p);
        }
    }

    /// <summary>The planner's log, into the game log (braces stripped, long lines capped: the game logger chokes on both).</summary>
    sealed class GameLog : Core.IPlanLog
    {
        static string Safe(string s) { if (s == null) return ""; s = s.Replace("{", "(").Replace("}", ")"); return s.Length > 1500 ? s.Substring(0, 1500) + "..." : s; }
        public void Info(string line) { try { Mod.log.Info(Safe(line)); } catch { } }
        public void Warn(string line) { try { Mod.log.Warn(Safe(line)); } catch { } }
        public void Error(Exception e, string line) { try { Mod.log.Error(e, Safe(line)); } catch { } }
    }
}
