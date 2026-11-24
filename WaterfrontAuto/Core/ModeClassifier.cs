using System;
using System.Collections.Generic;

namespace WaterfrontAuto.Core
{
    /// <summary>
    /// Classifies buildings into Beach (homes), Boardwalk (commercial/office/high-res/mixed/civic),
    /// or Industrial Pier (industrial), applies user override zones, and marks smooth transition zones
    /// between all three mode pairs along each continuous chain.
    /// </summary>
    public static class ModeClassifier
    {
        public static WaterfrontMode DefaultModeForZone(BuildingZoneKind kind)
        {
            switch (kind)
            {
                case BuildingZoneKind.LowRes:
                case BuildingZoneKind.MedRes:
                    return WaterfrontMode.Beach;
                case BuildingZoneKind.Industrial:
                    return WaterfrontMode.Industrial;
                case BuildingZoneKind.HighRes:
                case BuildingZoneKind.Mixed:
                case BuildingZoneKind.Commercial:
                case BuildingZoneKind.Office:
                case BuildingZoneKind.CivicOrPark:
                default:
                    return WaterfrontMode.Boardwalk;
            }
        }

        public static WaterfrontMode ResolveMode(Vec2 position, BuildingZoneKind zoneKind, IReadOnlyList<OverrideZone> overrides)
        {
            if (overrides != null)
            {
                // Latest matching override wins (like a paint brush)
                for (int i = overrides.Count - 1; i >= 0; i--)
                {
                    var ov = overrides[i];
                    if (Vec2.Distance(position, ov.Center) <= ov.Radius)
                    {
                        if (ov.Mode == WaterfrontMode.Auto) break;
                        return ov.Mode;
                    }
                }
            }
            return DefaultModeForZone(zoneKind);
        }

        public static void ClassifyEdges(List<WaterfrontEdge> edges, IReadOnlyList<OverrideZone> overrides)
        {
            for (int i = edges.Count - 1; i >= 0; i--)
            {
                var e = edges[i];
                Vec2 mid = (e.A + e.B) * 0.5f;
                var mode = ResolveMode(mid, e.Building.ZoneKind, overrides);
                if (mode == WaterfrontMode.Off)
                {
                    edges.RemoveAt(i);
                    continue;
                }
                e.Mode = mode;
            }
        }

        public static TransitionKind TransitionBetween(WaterfrontMode a, WaterfrontMode b)
        {
            if (a == b) return TransitionKind.None;
            if ((a == WaterfrontMode.Boardwalk && b == WaterfrontMode.Beach) ||
                (a == WaterfrontMode.Beach && b == WaterfrontMode.Boardwalk))
                return TransitionKind.BoardwalkToBeach;

            if ((a == WaterfrontMode.Boardwalk && b == WaterfrontMode.Industrial) ||
                (a == WaterfrontMode.Industrial && b == WaterfrontMode.Boardwalk))
                return TransitionKind.BoardwalkToIndustrial;

            if ((a == WaterfrontMode.Beach && b == WaterfrontMode.Industrial) ||
                (a == WaterfrontMode.Industrial && b == WaterfrontMode.Beach))
                return TransitionKind.BeachToIndustrial;

            return TransitionKind.None;
        }

        /// <summary>
        /// Marks transition zones on spine vertices within TransitionHalfLength of every mode change.
        /// </summary>
        public static void MarkTransitions(WaterfrontChain chain, WaterfrontConfig cfg)
        {
            var spine = chain.Spine;
            if (spine == null || spine.Count < 2) return;

            var cumDist = new float[spine.Count];
            for (int i = 1; i < spine.Count; i++)
                cumDist[i] = cumDist[i - 1] + Vec2.Distance(spine[i - 1].Pos, spine[i].Pos);

            for (int i = 0; i < spine.Count; i++)
                spine[i].Transition = TransitionKind.None;

            float halfLen = Math.Max(6f, cfg.TransitionHalfLength);
            for (int i = 0; i < spine.Count - 1; i++)
            {
                var tk = TransitionBetween(spine[i].Mode, spine[i + 1].Mode);
                if (tk == TransitionKind.None) continue;

                float boundaryS = (cumDist[i] + cumDist[i + 1]) * 0.5f;
                for (int j = 0; j < spine.Count; j++)
                {
                    if (Math.Abs(cumDist[j] - boundaryS) <= halfLen)
                        spine[j].Transition = tk;
                }
            }
        }
    }
}
