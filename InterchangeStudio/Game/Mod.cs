using System;
using System.Collections.Generic;
using Colossal;
using Colossal.IO.AssetDatabase;
using Colossal.Logging;
using Game;
using Game.Input;
using Game.Modding;
using Game.SceneFlow;
using Game.Settings;
using UnityEngine.InputSystem;
using Core = InterchangeStudio.Core;

namespace InterchangeStudio.Adapter
{
    /// <summary>
    /// Interchange Studio: highway interchange tools. The planning lives in Core (pure, tested offline);
    /// this adapter mirrors the city into it and writes its plans back to the game.
    /// </summary>
    public class Mod : IMod
    {
        public const string DisplayName = "Interchange Studio";
        public static readonly ILog log = LogManager.GetLogger("InterchangeStudio").SetShowsErrorsInUI(false);
        public static StudioSettings Settings { get; private set; }
        private StudioToolSystem m_Tool;
        private ProxyAction m_Toggle;

        public void OnLoad(UpdateSystem updateSystem)
        {
            Settings = new StudioSettings(this);
            Settings.RegisterInOptionsUI();
            AssetDatabase.global.LoadSettings("InterchangeStudio", Settings, new StudioSettings(this));
            Settings.RegisterKeyBindings();
            try { GameManager.instance.localizationManager.AddSource("en-US", new LocaleSource(Settings.Strings())); }
            catch (Exception e) { log.Warn("Could not add option texts: " + e.Message); }
            updateSystem.UpdateAt<StudioToolSystem>(SystemUpdatePhase.ToolUpdate);
            updateSystem.UpdateAt<StudioUISystem>(SystemUpdatePhase.UIUpdate);
            updateSystem.UpdateAt<StudioErrorsOff>(SystemUpdatePhase.Modification5);
            updateSystem.UpdateAt<StudioErrorsOn>(SystemUpdatePhase.ModificationEnd);
            m_Tool = updateSystem.World.GetOrCreateSystemManaged<StudioToolSystem>();
            m_Toggle = Settings.GetAction(StudioSettings.ToggleAction);
            m_Toggle.shouldBeEnabled = true;
            m_Toggle.onInteraction += OnToggle;
            log.Info("Interchange Studio loaded - Ctrl+Shift+J (rebindable in Options) opens the tools");
        }

        private void OnToggle(ProxyAction action, InputActionPhase phase)
        {
            if (phase != InputActionPhase.Performed) return;
            try { if ((GameManager.instance.gameMode & GameMode.Game) != 0) m_Tool.Toggle(); }
            catch (Exception e) { log.Error(e, "Could not switch the interchange tools"); }
        }

        public void OnDispose()
        {
            if (m_Toggle != null) m_Toggle.onInteraction -= OnToggle;
            Settings?.UnregisterInOptionsUI();
        }
    }

    /// <summary>Options page (the key binding) plus every panel setting, saved between games.</summary>
    [FileLocation("ModsSettings/InterchangeStudio/InterchangeStudio")]
    [SettingsUITabOrder(Tab)]
    [SettingsUIGroupOrder(Keys)]
    [SettingsUIShowGroupName(Keys)]
    public class StudioSettings : ModSetting
    {
        public const string Tab = "Main", Keys = "Keybindings", ToggleAction = "ToggleStudio";

        [SettingsUIKeyboardBinding(BindingKeyboard.J, ToggleAction, false, true, true)]
        [SettingsUISection(Tab, Keys)]
        public ProxyBinding ToggleBinding { get; set; }

        [SettingsUIHidden] public int Mode { get; set; }
        [SettingsUIHidden] public float Clearance { get; set; }
        [SettingsUIHidden] public float GradePercent { get; set; }
        [SettingsUIHidden] public bool BothCarriageways { get; set; }
        [SettingsUIHidden] public bool CloseLocalStreets { get; set; }
        [SettingsUIHidden] public bool LiftStreet { get; set; }
        [SettingsUIHidden] public bool Dig { get; set; }
        [SettingsUIHidden] public bool KeepElevated { get; set; }
        [SettingsUIHidden] public bool Compact { get; set; }
        [SettingsUIHidden] public int Size { get; set; }
        [SettingsUIHidden] public int RampLanes { get; set; }
        [SettingsUIHidden] public bool Autofit { get; set; }
        [SettingsUIHidden] public bool TightRamps { get; set; }
        [SettingsUIHidden] public int NewStreet { get; set; }
        [SettingsUIHidden] public int EndRoad { get; set; }

        public StudioSettings(IMod mod) : base(mod) { SetDefaults(); }

        public override void SetDefaults() => From(new Core.PlanConfig());

        /// <summary>The saved settings as a planner config (values out of range fall back to defaults).</summary>
        public Core.PlanConfig ToConfig()
        {
            var d = new Core.PlanConfig();
            return (d with
            {
                Mode = Mode == 0 || Mode == 1 || Mode == 2 || Mode == 3 || Mode == 4 || Mode == 5 || Mode == 6 || Mode == 9 ? (Core.Planner.ToolMode)Mode : d.Mode,
                Clearance = Clearance >= 6f && Clearance <= 20f ? Clearance : d.Clearance,
                Grade = GradePercent >= 3f && GradePercent <= 8f ? GradePercent / 100f : d.Grade,
                BothCarriageways = BothCarriageways, CloseLocalStreets = CloseLocalStreets, LiftStreet = LiftStreet, Dig = Dig, KeepElevated = KeepElevated, Compact = Compact,
                Size = Size >= 0 && Size <= 2 ? Size : d.Size,
                RampLanes = RampLanes >= 0 && RampLanes <= 2 ? RampLanes : 0,
                Autofit = Autofit, TightRamps = TightRamps,
                NewStreet = NewStreet >= 0 && NewStreet <= 2 ? NewStreet : d.NewStreet,
                EndRoad = EndRoad >= 0 && EndRoad <= 3 ? EndRoad : d.EndRoad,
            }).Supported();
        }

        public void From(Core.PlanConfig c)
        {
            Mode = (int)c.Mode; Clearance = c.Clearance; GradePercent = c.Grade * 100f; BothCarriageways = c.BothCarriageways;
            CloseLocalStreets = c.CloseLocalStreets; LiftStreet = c.LiftStreet; Dig = c.Dig; KeepElevated = c.KeepElevated; Compact = c.Compact; Size = c.Size;
            RampLanes = c.RampLanes; Autofit = c.Autofit; TightRamps = c.TightRamps; NewStreet = c.NewStreet; EndRoad = c.EndRoad;
        }

        public Dictionary<string, string> Strings() => new Dictionary<string, string>
        {
            { GetSettingsLocaleID(), Mod.DisplayName },
            { GetOptionTabLocaleID(Tab), "Main" },
            { GetOptionGroupLocaleID(Keys), "Key bindings" },
            { GetOptionLabelLocaleID(nameof(ToggleBinding)), "Open the interchange tools" },
            { GetOptionDescLocaleID(nameof(ToggleBinding)), "Opens and closes the Interchange Studio panel (also on the toolbar button at the top left)." },
            { GetBindingKeyLocaleID(ToggleAction), "Open the interchange tools" },
            { GetBindingMapLocaleID(), Mod.DisplayName },
        };
    }

    public class LocaleSource : IDictionarySource
    {
        private readonly Dictionary<string, string> m_Entries;
        public LocaleSource(Dictionary<string, string> entries) { m_Entries = entries; }
        public IEnumerable<KeyValuePair<string, string>> ReadEntries(IList<IDictionaryEntryError> errors, Dictionary<string, int> indexCounts) => m_Entries;
        public void Unload() { }
    }
}
