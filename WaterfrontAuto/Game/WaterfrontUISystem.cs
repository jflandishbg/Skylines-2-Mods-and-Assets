using System;
using Colossal.UI.Binding;
using Game.Tools;
using Game.UI;
using WaterfrontAuto.Core;

namespace WaterfrontAuto.GameAdapter
{
    public class WaterfrontUISystem : UISystemBase
    {
        private const string NS = "WaterfrontAuto";

        private ToolSystem m_ToolSystem;
        private WaterfrontBuilderSystem m_Builder;
        private WaterfrontToolSystem m_BrushTool;

        private bool m_PanelOpen;
        private ValueBinding<bool> m_Open, m_Auto, m_BeachTerrain, m_TimberBoardwalk, m_HomesBoardwalk, m_Straighten, m_AcBeach, m_Spurs, m_Piers, m_Props, m_RespectPm, m_PmFound, m_BrushActive;
        private ValueBinding<int> m_BrushMode, m_Overrides, m_LiveNets, m_LiveAreas, m_LiveProps, m_BeachCurls;
        private ValueBinding<float> m_BrushRadius;
        private ValueBinding<string> m_Status, m_Perf;

        protected override void OnCreate()
        {
            base.OnCreate();
            m_ToolSystem = World.GetOrCreateSystemManaged<ToolSystem>();
            m_Builder = World.GetOrCreateSystemManaged<WaterfrontBuilderSystem>();
            m_BrushTool = World.GetOrCreateSystemManaged<WaterfrontToolSystem>();

            var c = m_Builder.Config;
            AddBinding(m_Open = new ValueBinding<bool>(NS, "PANEL_OPEN", false));
            AddBinding(m_Auto = new ValueBinding<bool>(NS, "AUTO", c.AutoEnabled));
            AddBinding(m_BeachTerrain = new ValueBinding<bool>(NS, "BEACH_TERRAIN", c.EnableBeachTerrain));
            AddBinding(m_TimberBoardwalk = new ValueBinding<bool>(NS, "TIMBER_BOARDWALK", c.BoardwalkUseTimberPier));
            AddBinding(m_HomesBoardwalk = new ValueBinding<bool>(NS, "HOMES_BOARDWALK", c.HomesUseBoardwalk));
            AddBinding(m_Straighten = new ValueBinding<bool>(NS, "STRAIGHTEN", c.StraightenBlocks));
            AddBinding(m_AcBeach = new ValueBinding<bool>(NS, "AC_BEACH", c.AtlanticCityBeach));
            AddBinding(m_Spurs = new ValueBinding<bool>(NS, "STREET_SPURS", c.EnableStreetSpurs));
            AddBinding(m_Piers = new ValueBinding<bool>(NS, "IND_PIERS", c.EnableIndustrialPiers));
            AddBinding(m_Props = new ValueBinding<bool>(NS, "PROPS", c.EnableProps));
            AddBinding(m_RespectPm = new ValueBinding<bool>(NS, "RESPECT_PM", c.RespectPlacemaker));
            AddBinding(m_PmFound = new ValueBinding<bool>(NS, "PM_FOUND", false));
            AddBinding(m_BrushActive = new ValueBinding<bool>(NS, "BRUSH_ACTIVE", false));
            AddBinding(m_BrushMode = new ValueBinding<int>(NS, "BRUSH_MODE", (int)m_BrushTool.BrushMode));
            AddBinding(m_BrushRadius = new ValueBinding<float>(NS, "BRUSH_RADIUS", m_BrushTool.BrushRadius));
            AddBinding(m_Overrides = new ValueBinding<int>(NS, "OVERRIDE_COUNT", 0));
            AddBinding(m_LiveNets = new ValueBinding<int>(NS, "LIVE_NETS", 0));
            AddBinding(m_LiveAreas = new ValueBinding<int>(NS, "LIVE_AREAS", 0));
            AddBinding(m_LiveProps = new ValueBinding<int>(NS, "LIVE_PROPS", 0));
            AddBinding(m_BeachCurls = new ValueBinding<int>(NS, "BEACH_CURLS", 0));
            AddBinding(m_Status = new ValueBinding<string>(NS, "STATUS", "Idle"));
            AddBinding(m_Perf = new ValueBinding<string>(NS, "PERF", "Idle (0 ms)"));

            AddBinding(new TriggerBinding(NS, "TOGGLE_PANEL", TogglePanel));
            AddBinding(new TriggerBinding(NS, "REBUILD", () => m_Builder.RequestRebuild()));
            AddBinding(new TriggerBinding(NS, "CLEAR_ALL", () => m_Builder.RequestClearAll()));
            AddBinding(new TriggerBinding(NS, "ADOPT_OLD", () => m_Builder.RequestAdoptOrClean()));
            AddBinding(new TriggerBinding(NS, "UNDO_OVERRIDE", () => m_Builder.UndoLastOverride()));
            AddBinding(new TriggerBinding(NS, "CLEAR_OVERRIDES", () => m_Builder.ClearOverrides()));
            AddBinding(new TriggerBinding(NS, "STOP_BRUSH", () => m_BrushTool.DeactivateBrush()));

            AddBinding(new TriggerBinding<bool>(NS, "SET_AUTO", v => m_Builder.ApplyConfig(x => { x.AutoEnabled = v; return x; }, triggerRebuild: v)));
            AddBinding(new TriggerBinding<bool>(NS, "SET_BEACH_TERRAIN", v => m_Builder.ApplyConfig(x => { x.EnableBeachTerrain = v; return x; })));
            AddBinding(new TriggerBinding<bool>(NS, "SET_TIMBER_BOARDWALK", v => m_Builder.ApplyConfig(x => { x.BoardwalkUseTimberPier = v; return x; })));
            AddBinding(new TriggerBinding<bool>(NS, "SET_HOMES_BOARDWALK", v => m_Builder.ApplyConfig(x => { x.HomesUseBoardwalk = v; return x; })));
            AddBinding(new TriggerBinding<bool>(NS, "SET_STRAIGHTEN", v => m_Builder.ApplyConfig(x => { x.StraightenBlocks = v; return x; })));
            AddBinding(new TriggerBinding<bool>(NS, "SET_AC_BEACH", v => m_Builder.ApplyConfig(x => { x.AtlanticCityBeach = v; return x; })));
            AddBinding(new TriggerBinding<bool>(NS, "SET_STREET_SPURS", v => m_Builder.ApplyConfig(x => { x.EnableStreetSpurs = v; return x; })));
            AddBinding(new TriggerBinding<bool>(NS, "SET_IND_PIERS", v => m_Builder.ApplyConfig(x => { x.EnableIndustrialPiers = v; return x; })));
            AddBinding(new TriggerBinding<bool>(NS, "SET_PROPS", v => m_Builder.ApplyConfig(x => { x.EnableProps = v; return x; })));
            AddBinding(new TriggerBinding<bool>(NS, "SET_RESPECT_PM", v => m_Builder.ApplyConfig(x => { x.RespectPlacemaker = v; return x; })));
            AddBinding(new TriggerBinding<int>(NS, "PICK_BRUSH", mode =>
            {
                var wm = (WaterfrontMode)mode;
                if (m_ToolSystem.activeTool == m_BrushTool && m_BrushTool.BrushMode == wm)
                    m_BrushTool.DeactivateBrush();
                else
                    m_BrushTool.ActivateBrush(wm);
            }));
            AddBinding(new TriggerBinding<float>(NS, "SET_BRUSH_RADIUS", r => m_BrushTool.BrushRadius = Math.Max(12f, Math.Min(120f, r))));
        }

        public void TogglePanel()
        {
            m_PanelOpen = !m_PanelOpen;
            if (!m_PanelOpen) m_BrushTool.DeactivateBrush();
        }

        protected override void OnUpdate()
        {
            var c = m_Builder.Config;
            m_Open.Update(m_PanelOpen);
            m_Auto.Update(c.AutoEnabled);
            m_BeachTerrain.Update(c.EnableBeachTerrain);
            m_TimberBoardwalk.Update(c.BoardwalkUseTimberPier);
            m_HomesBoardwalk.Update(c.HomesUseBoardwalk);
            m_Straighten.Update(c.StraightenBlocks);
            m_AcBeach.Update(c.AtlanticCityBeach);
            m_Spurs.Update(c.EnableStreetSpurs);
            m_Piers.Update(c.EnableIndustrialPiers);
            m_Props.Update(c.EnableProps);
            m_RespectPm.Update(c.RespectPlacemaker);
            m_PmFound.Update(m_Builder.PlacemakerDetected);
            m_BrushActive.Update(m_ToolSystem.activeTool == m_BrushTool);
            m_BrushMode.Update((int)m_BrushTool.BrushMode);
            m_BrushRadius.Update(m_BrushTool.BrushRadius);
            m_Overrides.Update(m_Builder.OverrideCount);
            m_LiveNets.Update(m_Builder.LiveEdgesCount);
            m_LiveAreas.Update(m_Builder.LiveAreasCount);
            m_LiveProps.Update(m_Builder.LiveObjectsCount);
            m_BeachCurls.Update(m_Builder.LastBeachCurls);
            m_Status.Update(m_Builder.StatusText ?? "");
            m_Perf.Update(m_Builder.PerfText ?? "");
            base.OnUpdate();
        }
    }
}
