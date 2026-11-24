// Interchange Studio - Core/Config.cs
// Every panel setting in one immutable record. The planner reads it through read-only views with the
// old names, so ported code compiles unchanged; autofit plans with a modified COPY (`cfg with {...}`)
// instead of swapping mutable statics in and out.
#if !NET5_0_OR_GREATER
namespace System.Runtime.CompilerServices
{
    /// <summary>Lets C# 9 records and init accessors compile on netstandard2.1 (net8 has its own).</summary>
    internal static class IsExternalInit { }
}
#endif

namespace InterchangeStudio.Core
{
    public sealed record PlanConfig
    {
        public Planner.ToolMode Mode { get; init; } = Planner.ToolMode.Overpass;
        public float Clearance { get; init; } = 9f;           // metres under every new bridge
        public float Grade { get; init; } = 0.05f;            // steepest ramp, as a fraction
        public bool BothCarriageways { get; init; } = true;
        public bool CloseLocalStreets { get; init; } = true;
        public bool LiftStreet { get; init; } = true;         // at a ground-level crossing: street over (true) or highway over
        public bool Dig { get; init; }                        // Overpass only: the street dips under the highway in a cutting instead
        public bool KeepElevated { get; init; }               // Overpass only: a new road stays up at bridge height end to end, ends left raised
        public bool Compact { get; init; } = true;            // compact ramps (false: long, gentle)
        public int Size { get; init; } = 1;                   // 0 compact, 1 standard, 2 spacious
        public int RampLanes { get; init; }                     // 0 auto (two lanes at a major arterial), 1 or 2
        public bool Autofit { get; init; } = true;
        public bool TightRamps { get; init; }                  // Phoenix style: ramps run close beside the highway and flare out at the street
        public int NewStreet { get; init; } = 1;                // a new cross street (click a bare highway): 0 medium, 1 large, 2 avenue
        public int EndRoad { get; init; } = 2;                  // highway end: 0 two-way highway, 1 medium road, 2 large road, 3 avenue

        /// <summary>Full cache key covering every setting so previews never go stale when any option changes.</summary>
        public string CacheKey() =>
            $"{(int)Mode}|{Clearance:0.##}|{Grade:0.####}|{BothCarriageways}|{CloseLocalStreets}|{LiftStreet}|{Dig}|{KeepElevated}|{Compact}|{Size}|{RampLanes}|{Autofit}|{TightRamps}|{NewStreet}|{EndRoad}";

        /// <summary>
        /// Supported tools include Best fit, explicit Direction repair, and Highway end.
        /// Other retired modes still fall back to Diamond.
        /// </summary>
        public PlanConfig Supported()
        {
            bool ok = Mode == Planner.ToolMode.Exit || Mode == Planner.ToolMode.Spui || Mode == Planner.ToolMode.Overpass
                || Mode == Planner.ToolMode.Auto || Mode == Planner.ToolMode.Repair || Mode == Planner.ToolMode.Dumbbell
                || Mode == Planner.ToolMode.Frontage || Mode == Planner.ToolMode.Ending;
            return ok ? this : this with { Mode = Planner.ToolMode.Exit };
        }

        /// <summary>One choice that sets the steepest gradient and the ramp length together.</summary>
        public PlanConfig WithSize(int size)
        {
            int s = size < 0 ? 0 : size > 2 ? 2 : size;
            return this with { Size = s, Grade = s == 0 ? 0.07f : s == 1 ? 0.05f : 0.04f, Compact = s != 2 };
        }
    }

    public partial class Planner
    {
        /// <summary>The settings in force. Replaced as a whole (never edited in place).</summary>
        public PlanConfig Cfg { get; set; } = new PlanConfig();

        ToolMode Mode => Cfg.Mode;
        float Clearance => Cfg.Clearance;
        float Grade => Cfg.Grade;
        bool BothCarriageways => Cfg.BothCarriageways;
        bool CloseLocalStreets => Cfg.CloseLocalStreets;
        bool LiftStreet => Cfg.LiftStreet;
        /// <summary>The street dips under (a cutting) rather than going over: Overpass mode only, street-over plans only.</summary>
        bool DigUnder => Cfg.Dig && Cfg.LiftStreet && Cfg.Mode == ToolMode.Overpass;
        bool KeepUp => Cfg.KeepElevated && (Cfg.Mode == ToolMode.Overpass || Cfg.Mode == ToolMode.Ending);
        bool Compact => Cfg.Compact;
        int Size => Cfg.Size;
        int RampLanes => Cfg.RampLanes;
        int NewStreet => Cfg.NewStreet;
        int EndRoad => Cfg.EndRoad;
        bool Autofit => Cfg.Autofit;
        bool TightRamps => Cfg.TightRamps;
    }
}
