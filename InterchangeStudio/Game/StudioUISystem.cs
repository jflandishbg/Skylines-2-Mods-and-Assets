using System;
using Colossal.UI.Binding;
using Game.Tools;
using Game.UI;
using Core = InterchangeStudio.Core;

namespace InterchangeStudio.Adapter
{
    /// <summary>
    /// Connects the toolbar button and panel (InterchangeStudio.mjs) to the tool. Every value the panel shows
    /// is read from the planner's config each frame, and every change goes through StudioToolSystem.Configure,
    /// which swaps in a new config and saves it. There is no second copy of a setting to fall out of step.
    /// </summary>
    public class StudioUISystem : UISystemBase
    {
        const string NS = "InterchangeStudio";
        private ToolSystem m_ToolSystem;
        private StudioToolSystem m_Tool;
        private ValueBinding<bool> m_Active, m_Both, m_Close, m_LiftStreet, m_Compact, m_Autofit, m_Dig, m_Keep, m_Tight, m_CanUndo;
        private ValueBinding<int> m_Mode, m_RampLanes, m_Size, m_StatusKind, m_NewStreet, m_EndRoad;
        private ValueBinding<float> m_Clearance, m_Grade;
        private ValueBinding<string> m_Status, m_Summary, m_UndoLabel;

        static float Clamp(float v, float lo, float hi) => v < lo ? lo : v > hi ? hi : v;

        protected override void OnCreate()
        {
            base.OnCreate();
            m_ToolSystem = World.GetOrCreateSystemManaged<ToolSystem>();
            m_Tool = World.GetOrCreateSystemManaged<StudioToolSystem>();
            var c = Mod.Settings?.ToConfig() ?? new Core.PlanConfig();

            AddBinding(m_Active = new ValueBinding<bool>(NS, "TOOL_ACTIVE", false));
            AddBinding(m_Status = new ValueBinding<string>(NS, "STATUS", ""));
            AddBinding(m_Summary = new ValueBinding<string>(NS, "PREVIEW_SUMMARY", ""));
            AddBinding(m_StatusKind = new ValueBinding<int>(NS, "STATUS_KIND", 0));
            AddBinding(m_Mode = new ValueBinding<int>(NS, "MODE", (int)c.Mode));
            AddBinding(m_Clearance = new ValueBinding<float>(NS, "CLEARANCE", c.Clearance));
            AddBinding(m_Grade = new ValueBinding<float>(NS, "GRADE", c.Grade * 100f));
            AddBinding(m_Both = new ValueBinding<bool>(NS, "BOTH", c.BothCarriageways));
            AddBinding(m_Close = new ValueBinding<bool>(NS, "CLOSE", c.CloseLocalStreets));
            AddBinding(m_LiftStreet = new ValueBinding<bool>(NS, "LIFT_STREET", c.LiftStreet));
            AddBinding(m_Dig = new ValueBinding<bool>(NS, "DIG", c.Dig));
            AddBinding(m_Keep = new ValueBinding<bool>(NS, "KEEP_ELEVATED", c.KeepElevated));
            AddBinding(m_Compact = new ValueBinding<bool>(NS, "COMPACT", c.Compact));
            AddBinding(m_Autofit = new ValueBinding<bool>(NS, "AUTOFIT", c.Autofit));
            AddBinding(m_Tight = new ValueBinding<bool>(NS, "TIGHT_RAMPS", c.TightRamps));
            AddBinding(m_RampLanes = new ValueBinding<int>(NS, "RAMP_LANES", c.RampLanes));
            AddBinding(m_Size = new ValueBinding<int>(NS, "SIZE", c.Size));
            AddBinding(m_NewStreet = new ValueBinding<int>(NS, "NEW_STREET", c.NewStreet));
            AddBinding(m_EndRoad = new ValueBinding<int>(NS, "END_ROAD", c.EndRoad));
            AddBinding(m_CanUndo = new ValueBinding<bool>(NS, "CAN_UNDO", false));
            AddBinding(m_UndoLabel = new ValueBinding<string>(NS, "UNDO_LABEL", ""));

            AddBinding(new TriggerBinding(NS, "TOGGLE_TOOL", () => m_Tool.Toggle()));
            AddBinding(new TriggerBinding(NS, "FIND_NEXT", () => m_Tool.FindNext()));
            AddBinding(new TriggerBinding(NS, "UNDO_LAST", () => m_Tool.UndoLast()));
            AddBinding(new TriggerBinding(NS, "SELF_TEST", () => m_Tool.StartSelfTest(auto: false)));
            Set<int>("SET_MODE", (x, v) => (x with { Mode = (Core.Planner.ToolMode)v }).Supported());
            Set<float>("SET_CLEARANCE", (x, v) => x with { Clearance = Clamp(v, 6f, 20f) });
            Set<float>("SET_GRADE", (x, v) => x with { Grade = Clamp(v, 3f, 8f) / 100f });
            Set<bool>("SET_BOTH", (x, v) => x with { BothCarriageways = v });
            Set<bool>("SET_CLOSE", (x, v) => x with { CloseLocalStreets = v });
            Set<bool>("SET_LIFT_STREET", (x, v) => x with { LiftStreet = v });
            Set<bool>("SET_KEEP_ELEVATED", (x, v) => x with { KeepElevated = v });
            Set<int>("SET_CROSSING", (x, v) => x with { LiftStreet = v != 1, Dig = v == 2 });    // 0 street over, 1 highway over, 2 street under
            Set<bool>("SET_COMPACT", (x, v) => x with { Compact = v });
            Set<bool>("SET_AUTOFIT", (x, v) => x with { Autofit = v });
            Set<bool>("SET_TIGHT_RAMPS", (x, v) => x with { TightRamps = v });
            Set<int>("SET_RAMP_LANES", (x, v) => x with { RampLanes = v >= 0 && v <= 2 ? v : 0 });
            Set<int>("SET_SIZE", (x, v) => x.WithSize(v));
            Set<int>("SET_NEW_STREET", (x, v) => x with { NewStreet = v >= 0 && v <= 2 ? v : 1 });
            Set<int>("SET_END_ROAD", (x, v) => x with { EndRoad = v >= 0 && v <= 3 ? v : 2 });
        }

        /// <summary>A panel trigger that changes one setting: the change is a function from old config to new.</summary>
        void Set<T>(string name, Func<Core.PlanConfig, T, Core.PlanConfig> change) =>
            AddBinding(new TriggerBinding<T>(NS, name, v =>
            {
                try { m_Tool.Configure(c => change(c, v)); }
                catch (Exception e) { Mod.log.Error(e, "Changing a setting"); }
            }));

        protected override void OnUpdate()
        {
            bool active = m_ToolSystem.activeTool == m_Tool;
            m_Active.Update(active);
            m_Status.Update(active ? m_Tool.StatusText : "");
            m_Summary.Update(active && !m_Tool.TestRunning ? m_Tool.PreviewSummary : "");
            m_StatusKind.Update(active ? m_Tool.StatusKind : 0);
            m_CanUndo.Update(active && !m_Tool.TestRunning && m_Tool.CanUndo);
            m_UndoLabel.Update(active && !m_Tool.TestRunning ? m_Tool.UndoLabel : "");
            var c = m_Tool.Planner?.Cfg;
            if (c != null)
            {
                m_Mode.Update((int)c.Mode); m_Clearance.Update(c.Clearance); m_Grade.Update(c.Grade * 100f);
                m_Both.Update(c.BothCarriageways); m_Close.Update(c.CloseLocalStreets); m_LiftStreet.Update(c.LiftStreet); m_Dig.Update(c.Dig); m_Keep.Update(c.KeepElevated);
                m_Compact.Update(c.Compact); m_Autofit.Update(c.Autofit); m_Tight.Update(c.TightRamps);
                m_RampLanes.Update(c.RampLanes);
                m_Size.Update(c.Size); m_NewStreet.Update(c.NewStreet); m_EndRoad.Update(c.EndRoad);
            }
            m_Tool.TickNames();
            m_Tool.TickAutoSelfTest();
            base.OnUpdate();
        }
    }
}
