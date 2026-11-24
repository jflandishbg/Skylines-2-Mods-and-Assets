using Game.Common;
using Game.Prefabs;
using Game.Tools;
using Unity.Entities;
using Unity.Jobs;
using WaterfrontAuto.Core;

namespace WaterfrontAuto.GameAdapter
{
    /// <summary>
    /// Optional lightweight shoreline override brush tool.
    /// Click anywhere along a waterfront to force Auto / Beach / Boardwalk / Industrial / Natural Cliff (Off).
    /// Right-click or Esc exits back to normal play.
    /// </summary>
    public partial class WaterfrontToolSystem : ToolBaseSystem
    {
        public override string toolID => "WaterfrontAutoBrush";

        private DefaultToolSystem m_DefaultTool;
        private WaterfrontBuilderSystem m_Builder;

        public WaterfrontMode BrushMode { get; set; } = WaterfrontMode.Beach;
        public float BrushRadius { get; set; } = 36f;

        protected override void OnCreate()
        {
            base.OnCreate();
            m_DefaultTool = World.GetOrCreateSystemManaged<DefaultToolSystem>();
            m_Builder = World.GetOrCreateSystemManaged<WaterfrontBuilderSystem>();
        }

        public override PrefabBase GetPrefab() => null;
        public override bool TrySetPrefab(PrefabBase prefab) => false;

        public override void InitializeRaycast()
        {
            base.InitializeRaycast();
            m_ToolRaycastSystem.typeMask = TypeMask.Terrain | TypeMask.Water;
        }

        protected override void OnStartRunning()
        {
            base.OnStartRunning();
            applyAction.shouldBeEnabled = true;
            cancelAction.shouldBeEnabled = true;
        }

        public void ActivateBrush(WaterfrontMode mode)
        {
            BrushMode = mode;
            m_ToolSystem.activeTool = this;
        }

        public void DeactivateBrush()
        {
            if (m_ToolSystem.activeTool == this)
                m_ToolSystem.activeTool = m_DefaultTool;
        }

        protected override JobHandle OnUpdate(JobHandle inputDeps)
        {
            applyMode = ApplyMode.None;

            if (cancelAction.WasPressedThisFrame())
            {
                m_ToolSystem.activeTool = m_DefaultTool;
                return inputDeps;
            }

            if (applyAction.WasPressedThisFrame() && GetRaycastResult(out Entity _, out RaycastHit hit))
            {
                m_Builder.AddOverride(new Vec2(hit.m_HitPosition.x, hit.m_HitPosition.z), BrushRadius, BrushMode);
            }

            return inputDeps;
        }
    }
}
