using System.Collections.Generic;
using Game;
using Game.Prefabs;
using Game.Tools;
using Unity.Collections;
using Unity.Entities;

namespace InterchangeStudio.Adapter
{
    /// <summary>
    /// The game's geometry checks (invalid shape, tight curve, short or long piece, steep slope, low
    /// elevation) are stricter than the roads need: they turn whole interchanges red over a folded gore or a
    /// slope a few tenths over the limit, and the roads work fine when built anyway (that's what Anarchy
    /// players do). While the tool is previewing, those checks are switched off for the frame and back on
    /// before the frame ends. Collisions (overlaps, clearance) are never switched off.
    ///
    /// The idea comes from the InterchangeBuilder mod; this is our own implementation of it.
    /// Off runs in Modification5, before the game validates the preview; On runs at ModificationEnd.
    /// </summary>
    public partial class StudioErrorsOff : GameSystemBase
    {
        public static readonly ErrorType[] Cosmetic =
        {
            ErrorType.InvalidShape, ErrorType.TightCurve, ErrorType.ShortDistance,
            ErrorType.LongDistance, ErrorType.SteepSlope, ErrorType.LowElevation,
        };
        const ToolErrorFlags Hidden = ToolErrorFlags.DisableInGame | ToolErrorFlags.DisableInEditor;

        private EntityQuery m_ErrorPrefabs;
        private StudioErrorsOn m_On;
        private bool m_Armed;

        /// <summary>Switch the cosmetic checks off for the current frame only.</summary>
        public void Arm() { m_Armed = true; Enabled = true; }

        protected override void OnCreate()
        {
            base.OnCreate();
            m_On = World.GetOrCreateSystemManaged<StudioErrorsOn>();
            m_ErrorPrefabs = GetEntityQuery(ComponentType.ReadWrite<ToolErrorData>());
            Enabled = false;
        }

        protected override void OnUpdate()
        {
            Enabled = false;
            if (!m_Armed) return;
            m_Armed = false;
            using (var prefabs = m_ErrorPrefabs.ToEntityArray(Allocator.Temp))
                foreach (var e in prefabs)
                {
                    var d = EntityManager.GetComponentData<ToolErrorData>(e);
                    if (System.Array.IndexOf(Cosmetic, d.m_Error) < 0) continue;
                    var added = Hidden & ~d.m_Flags;      // only what we set, so we only undo what we set
                    if (added == 0) continue;
                    d.m_Flags |= added;
                    EntityManager.SetComponentData(e, d);
                    m_On.Remember(e, added);
                }
        }
    }

    /// <summary>Puts back exactly the flags StudioErrorsOff added, at the end of the same frame.</summary>
    public partial class StudioErrorsOn : GameSystemBase
    {
        private readonly Dictionary<Entity, ToolErrorFlags> m_Added = new Dictionary<Entity, ToolErrorFlags>();

        public void Remember(Entity prefab, ToolErrorFlags added)
        {
            m_Added[prefab] = m_Added.TryGetValue(prefab, out var f) ? f | added : added;
            Enabled = true;
        }

        protected override void OnCreate() { base.OnCreate(); Enabled = false; }

        protected override void OnUpdate()
        {
            foreach (var kv in m_Added)
            {
                if (!EntityManager.Exists(kv.Key) || !EntityManager.HasComponent<ToolErrorData>(kv.Key)) continue;
                var d = EntityManager.GetComponentData<ToolErrorData>(kv.Key);
                d.m_Flags &= ~kv.Value;
                EntityManager.SetComponentData(kv.Key, d);
            }
            m_Added.Clear();
            Enabled = false;
        }
    }
}
