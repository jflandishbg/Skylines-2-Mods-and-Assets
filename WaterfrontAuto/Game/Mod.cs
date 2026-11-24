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
using WaterfrontAuto.Core;

namespace WaterfrontAuto.GameAdapter
{
    public class Mod : IMod
    {
        public const string DisplayName = "Waterfront Auto";
        public static readonly ILog Log = LogManager.GetLogger("WaterfrontAuto").SetShowsErrorsInUI(false);
        public static WaterfrontSettings Settings { get; private set; }

        private WaterfrontUISystem m_UI;
        private ProxyAction m_Toggle;

        public void OnLoad(UpdateSystem updateSystem)
        {
            Settings = new WaterfrontSettings(this);
            Settings.RegisterInOptionsUI();
            AssetDatabase.global.LoadSettings("WaterfrontAuto", Settings, new WaterfrontSettings(this));
            Settings.RegisterKeyBindings();
            try
            {
                GameManager.instance.localizationManager.AddSource("en-US", new LocaleSource(Settings.Strings()));
            }
            catch (Exception e) { Log.Warn("Could not add localization: " + e.Message); }

            // CRITICAL: Run BEFORE GenerateObjects/GenerateNodes/GenerateAreas in Modification1
            // so permanent CreationDefinition entities are materialized on the exact same frame!
            updateSystem.UpdateBefore<WaterfrontBuilderSystem, Game.Tools.GenerateObjectsSystem>(SystemUpdatePhase.Modification1);
            // Capture materialized Created edges/areas/objects in ModificationEnd before CleanUpSystem strips Created
            updateSystem.UpdateAt<WaterfrontCaptureSystem>(SystemUpdatePhase.ModificationEnd);
            updateSystem.UpdateAt<WaterfrontToolSystem>(SystemUpdatePhase.ToolUpdate);
            updateSystem.UpdateAt<WaterfrontUISystem>(SystemUpdatePhase.UIUpdate);

            m_UI = updateSystem.World.GetOrCreateSystemManaged<WaterfrontUISystem>();
            m_Toggle = Settings.GetAction(WaterfrontSettings.ToggleAction);
            m_Toggle.shouldBeEnabled = true;
            m_Toggle.onInteraction += OnToggle;
            Log.Info("Waterfront Auto loaded — Ctrl+Shift+W (or top-left toolbar button) opens controls.");
        }

        private void OnToggle(ProxyAction action, InputActionPhase phase)
        {
            if (phase != InputActionPhase.Performed) return;
            try
            {
                if ((GameManager.instance.gameMode & GameMode.Game) != 0)
                    m_UI?.TogglePanel();
            }
            catch (Exception e) { Log.Error(e, "Could not toggle Waterfront Auto panel"); }
        }

        public void OnDispose()
        {
            if (m_Toggle != null) m_Toggle.onInteraction -= OnToggle;
            Settings?.UnregisterInOptionsUI();
        }
    }

    [FileLocation("ModsSettings/WaterfrontAuto/WaterfrontAuto")]
    [SettingsUITabOrder(Tab)]
    [SettingsUIGroupOrder(Keys)]
    [SettingsUIShowGroupName(Keys)]
    public class WaterfrontSettings : ModSetting
    {
        public const string Tab = "Main", Keys = "Keybindings", ToggleAction = "ToggleWaterfrontAuto";

        [SettingsUIKeyboardBinding(BindingKeyboard.W, ToggleAction, false, true, true)]
        [SettingsUISection(Tab, Keys)]
        public ProxyBinding ToggleBinding { get; set; }

        [SettingsUIHidden] public bool AutoEnabled { get; set; }
        [SettingsUIHidden] public bool EnableBeachTerrain { get; set; }
        [SettingsUIHidden] public bool BoardwalkUseTimberPier { get; set; }
        [SettingsUIHidden] public bool HomesUseBoardwalk { get; set; }
        [SettingsUIHidden] public bool StraightenBlocks { get; set; }
        [SettingsUIHidden] public bool AtlanticCityBeach { get; set; }
        [SettingsUIHidden] public bool EnableStreetSpurs { get; set; }
        [SettingsUIHidden] public bool EnableIndustrialPiers { get; set; }
        [SettingsUIHidden] public bool EnableProps { get; set; }
        [SettingsUIHidden] public bool RespectPlacemaker { get; set; }

        public WaterfrontSettings(IMod mod) : base(mod) { SetDefaults(); }

        public override void SetDefaults() => From(new WaterfrontConfig());

        public WaterfrontConfig ToConfig()
        {
            return new WaterfrontConfig
            {
                AutoEnabled = AutoEnabled,
                EnableBeachTerrain = EnableBeachTerrain,
                BoardwalkUseTimberPier = BoardwalkUseTimberPier,
                HomesUseBoardwalk = HomesUseBoardwalk,
                StraightenBlocks = StraightenBlocks,
                AtlanticCityBeach = AtlanticCityBeach,
                EnableStreetSpurs = EnableStreetSpurs,
                EnableIndustrialPiers = EnableIndustrialPiers,
                EnableProps = EnableProps,
                RespectPlacemaker = RespectPlacemaker,
            };
        }

        public void From(WaterfrontConfig c)
        {
            AutoEnabled = c.AutoEnabled;
            EnableBeachTerrain = c.EnableBeachTerrain;
            BoardwalkUseTimberPier = c.BoardwalkUseTimberPier;
            HomesUseBoardwalk = c.HomesUseBoardwalk;
            StraightenBlocks = c.StraightenBlocks;
            AtlanticCityBeach = c.AtlanticCityBeach;
            EnableStreetSpurs = c.EnableStreetSpurs;
            EnableIndustrialPiers = c.EnableIndustrialPiers;
            EnableProps = c.EnableProps;
            RespectPlacemaker = c.RespectPlacemaker;
        }

        public Dictionary<string, string> Strings() => new Dictionary<string, string>
        {
            { GetSettingsLocaleID(), Mod.DisplayName },
            { GetOptionTabLocaleID(Tab), "Main" },
            { GetOptionGroupLocaleID(Keys), "Key bindings" },
            { GetOptionLabelLocaleID(nameof(ToggleBinding)), "Open Waterfront Auto panel" },
            { GetOptionDescLocaleID(nameof(ToggleBinding)), "Opens the Waterfront Auto control panel (also on the top-left toolbar)." },
            { GetBindingKeyLocaleID(ToggleAction), "Open Waterfront Auto panel" },
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
