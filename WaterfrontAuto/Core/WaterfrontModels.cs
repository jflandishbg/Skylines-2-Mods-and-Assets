using System;
using System.Collections.Generic;

namespace WaterfrontAuto.Core
{
    public enum WaterfrontMode
    {
        Auto = 0,
        Beach = 1,
        Boardwalk = 2,
        Industrial = 3,
        Off = 4,
    }

    public enum BuildingZoneKind
    {
        Other = 0,
        LowRes = 1,
        MedRes = 2,
        HighRes = 3,
        Mixed = 4,
        Commercial = 5,
        Office = 6,
        Industrial = 7,
        CivicOrPark = 8,
    }

    public enum TransitionKind
    {
        None = 0,
        BoardwalkToBeach = 1,
        BoardwalkToIndustrial = 2,
        BeachToIndustrial = 3,
    }

    public enum NetRole
    {
        Boardwalk = 0,
        IndustrialQuay = 1,
        IndustrialPier = 2,
        BeachPath = 3,
        BeachBoardwalkFallback = 4,
        TransitionRamp = 5,
        AccessSpur = 6,
        BoardwalkOverlook = 7,
    }

    public enum SurfaceRole
    {
        Sand = 0,
        BoardwalkDeck = 1,
        IndustrialConcrete = 2,
        TransitionPaving = 3,
    }

    public enum PropRole
    {
        BeachChair = 0,
        BeachParasol = 1,
        BoardwalkBench = 2,
        BoardwalkLamp = 3,
        BoardwalkBollard = 4,
        IndustrialBollard = 5,
        IndustrialBarrier = 6,
        TransitionRock = 7,
        TransitionRubble = 8,
        BoardwalkKiosk = 9,
        BoardwalkGazebo = 10,
        BoardwalkLifeBuoy = 11,
    }

    public sealed class BuildingLot
    {
        public long EntityId;
        public Vec3 Center;
        /// <summary>
        /// CS2 BuildingUtils.CalculateCorners order:
        /// [0] Back-Right, [1] Back-Left, [2] Front-Left, [3] Front-Right.
        /// </summary>
        public Vec2[] Corners;
        public float Width;
        public float Depth;
        public float LotElevation;
        public BuildingZoneKind ZoneKind;
        public bool UnderConstruction;
        public bool IsPlacemakerOwned;
        public bool IsMaritimeBuilding;
        public string DebugName;
    }

    public sealed class ExistingNetSegment
    {
        public long EntityId;
        public Vec3 Start;
        public Vec3 Mid;
        public Vec3 End;
        public float Width;
        public bool IsRoad;
        public bool IsPathway;
        public bool IsQuayOrPier;
        public bool IsWaterway;
        /// <summary>Train / tram / subway track. Treated exactly like a road: never covered, crossed or bridged over.</summary>
        public bool IsRail;
        public bool IsGeneratedByUs;
        public bool IsPlacemakerOwned;
    }

    /// <summary>An existing sand/beach Area placed by Placemaker (or the player) so boardwalks curl smoothly into it.</summary>
    public sealed class ExistingBeachArea
    {
        public long EntityId;
        public Vec2 Center;
        public float Radius;
        public Vec2[] Ring;
        public bool IsPlacemakerOwned;
    }

    public sealed class OverrideZone
    {
        public Vec2 Center;
        public float Radius;
        public WaterfrontMode Mode;
    }

    public interface IWorldSampler
    {
        float TerrainHeight(Vec2 p);
        float WaterDepth(Vec2 p);
        float WaterSurfaceHeight(Vec2 p);
    }

    public sealed class WaterfrontConfig
    {
        public bool AutoEnabled = true;
        public bool BoardwalkUseTimberPier = true;    // true = Grand Timber Boardwalk (LeisurePierLarge/Med), false = Wide Stone Quay
        public bool HomesUseBoardwalk = true;         // true = Atlantic City boardwalk + seaward beach behind homes; false = compact flush stone quay
        public bool StraightenBlocks = true;          // true = even outer promenade line across staggered building depths (no U-dips!)
        public bool AtlanticCityBeach = true;         // true = sandy beach + umbrellas/chairs SEAWARD of boardwalk where water allows
        public bool EnableBeachTerrain = false;       // opt-in seaward-only beach slope grading (strictly outside boardwalk, never under buildings)
        public bool EnableStreetSpurs = true;
        public bool EnableIndustrialPiers = true;
        public bool EnableProps = true;
        public bool RespectPlacemaker = true;

        public float WaterProbeMaxDist = 18f;
        public float MinWaterDepth = 0.25f;
        public float GapBridgeDistance = 42f;
        public float TransitionHalfLength = 10f;
        public float PierSpacing = 64f;
        public float MaxPierLength = 26f;
        public float BeachSlopeWidth = 15f;
        public float MaxBeachCliffDrop = 10.5f;
        public float MinBeachChannelWidth = 22f;
        public float MaxPedestrianGrade = 0.14f;
        public float BeachCurlSearchDist = 40f;

        /// <summary>Full deck width of the Grand Timber Boardwalk net (m). Drives spine offset and building clearance.</summary>
        public float BoardwalkDeckWidth = 8.0f;
        /// <summary>Full deck width of the stone / industrial quay net (m).</summary>
        public float QuayDeckWidth = 6.0f;
        /// <summary>Full width of small pathways: beach paths, curls, ramps and street access spurs (m).</summary>
        public float WalkwayWidth = 4.0f;

        /// <summary>Copies every field (all are value types, so MemberwiseClone includes the deck widths).</summary>
        public WaterfrontConfig Clone() => (WaterfrontConfig)MemberwiseClone();
    }

    /// <summary>One detected water-facing edge of a building lot.</summary>
    public sealed class WaterfrontEdge
    {
        public BuildingLot Building;
        /// <summary>0 = Back, 1 = LeftSide, 2 = RightSide</summary>
        public int SideIndex;
        public Vec2 A;
        public Vec2 B;
        /// <summary>Unit vector pointing seaward out of the lot.</summary>
        public Vec2 Seaward;
        public float LotY;
        public float WaterY;
        public float CliffDrop;
        public float DistToWater;
        public WaterfrontMode Mode;
    }

    public sealed class SpineVertex
    {
        public Vec2 Pos;
        public Vec2 Seaward;
        public float LotY;
        public float WaterY;
        public float TargetY;
        public WaterfrontMode Mode;
        public TransitionKind Transition;
        public bool IsGapBridge;
        public bool IsEndOfChain;
        public bool BeachCanGrade;
        public float OpenWaterDist;
        public WaterfrontEdge SourceEdge;
        /// <summary>Recess distance from the building's back edge out to this straightened promenade vertex.</summary>
        public float PocketDepth;
    }

    public sealed class WaterfrontChain
    {
        public int ChainId;
        public List<WaterfrontEdge> Edges = new List<WaterfrontEdge>();
        public List<SpineVertex> Spine = new List<SpineVertex>();
    }

    public sealed class PlannedNet
    {
        public Vec3 A;
        public Vec3 B;
        public Vec3 C;
        public Vec3 D;
        public NetRole Role;
        public WaterfrontMode Mode;
        public bool Elevated;
        public float ElevationA;
        public float ElevationB;
        public int ChainId;
        public long SnapEndNetId;
        public float SnapEndCurveT;
        /// <summary>True for a curl ramp onto an existing Placemaker beach (lets the validator keep BeachCurls honest).</summary>
        public bool IsBeachCurl;
    }

    public sealed class PlannedSurface
    {
        public Vec2[] Ring;
        public SurfaceRole Role;
        public int ChainId;
    }

    public sealed class PlannedProp
    {
        public Vec3 Position;
        public float Yaw;
        public PropRole Role;
        public int Seed;
        public int ChainId;
    }

    public sealed class PlannedBeachGrade
    {
        public Vec2 LandEdgeMid;
        public Vec2 AlongDir;
        public Vec2 SeawardDir;
        public float Length;
        public float SlopeWidth;
        public float LandY;
        public float WaterY;
        public int ChainId;
        /// <summary>True when raising/extending a beach outward to match an adjacent Placemaker beach.</summary>
        public bool IsPlacemakerExtension;
    }

    public sealed class WaterfrontPlan
    {
        public List<WaterfrontChain> Chains = new List<WaterfrontChain>();
        public List<PlannedNet> Nets = new List<PlannedNet>();
        public List<PlannedSurface> Surfaces = new List<PlannedSurface>();
        public List<PlannedProp> Props = new List<PlannedProp>();
        public List<PlannedBeachGrade> BeachGrades = new List<PlannedBeachGrade>();

        public int DetectedEdges;
        public int BeachSegments;
        public int BoardwalkSegments;
        public int IndustrialSegments;
        public int TransitionSegments;
        public int FingerPiers;
        public int AccessSpurs;
        public int BeachCurls;
        public int SkippedPlacemaker;
        /// <summary>Items removed by PlanValidator.ValidateAndFilter on the last planning pass.</summary>
        public int ValidatorRemoved;

        /// <summary>
        /// Deterministic, order-independent 64-bit hash of everything that would be built
        /// (Nets, Surfaces, Props and BeachGrades). Positions and heights are quantised to 5 cm and yaw
        /// to 0.01 rad, so float noise between two identical passes never forces a rebuild.
        /// Each item is hashed on its own, the item hashes are sorted, then folded, so list order never matters.
        /// ChainId is deliberately excluded: it does not change what is built.
        /// </summary>
        public ulong ComputePlanHash()
        {
            var items = new List<ulong>(Nets.Count + Surfaces.Count + Props.Count + BeachGrades.Count);

            for (int i = 0; i < Nets.Count; i++)
            {
                var n = Nets[i];
                if (n == null) continue;
                ulong h = PlanHash.Begin(1);
                h = PlanHash.Add(h, (int)n.Role);
                h = PlanHash.Add(h, (int)n.Mode);
                h = PlanHash.Add(h, n.Elevated ? 1 : 0);
                h = PlanHash.AddV3(h, n.A);
                h = PlanHash.AddV3(h, n.B);
                h = PlanHash.AddV3(h, n.C);
                h = PlanHash.AddV3(h, n.D);
                h = PlanHash.AddF(h, n.ElevationA);
                h = PlanHash.AddF(h, n.ElevationB);
                h = PlanHash.Add(h, n.SnapEndNetId);
                items.Add(PlanHash.Finish(h));
            }
            for (int i = 0; i < Surfaces.Count; i++)
            {
                var s = Surfaces[i];
                if (s == null || s.Ring == null) continue;
                ulong h = PlanHash.Begin(2);
                h = PlanHash.Add(h, (int)s.Role);
                h = PlanHash.Add(h, s.Ring.Length);
                for (int k = 0; k < s.Ring.Length; k++) h = PlanHash.AddV2(h, s.Ring[k]);
                items.Add(PlanHash.Finish(h));
            }
            for (int i = 0; i < Props.Count; i++)
            {
                var p = Props[i];
                if (p == null) continue;
                ulong h = PlanHash.Begin(3);
                h = PlanHash.Add(h, (int)p.Role);
                h = PlanHash.AddV3(h, p.Position);
                h = PlanHash.Add(h, (long)Math.Round(p.Yaw * 100.0));
                h = PlanHash.Add(h, p.Seed);
                items.Add(PlanHash.Finish(h));
            }
            for (int i = 0; i < BeachGrades.Count; i++)
            {
                var g = BeachGrades[i];
                if (g == null) continue;
                ulong h = PlanHash.Begin(4);
                h = PlanHash.AddV2(h, g.LandEdgeMid);
                h = PlanHash.AddV2(h, g.AlongDir * 100f);
                h = PlanHash.AddV2(h, g.SeawardDir * 100f);
                h = PlanHash.AddF(h, g.Length);
                h = PlanHash.AddF(h, g.SlopeWidth);
                h = PlanHash.AddF(h, g.LandY);
                h = PlanHash.AddF(h, g.WaterY);
                items.Add(PlanHash.Finish(h));
            }

            items.Sort();
            ulong acc = PlanHash.Begin(0x5EED);
            acc = PlanHash.Add(acc, items.Count);
            for (int i = 0; i < items.Count; i++) acc = PlanHash.Add(acc, unchecked((long)items[i]));
            return PlanHash.Finish(acc);
        }
    }

    /// <summary>FNV-1a 64 over quantised integers plus a splitmix64 finaliser. Stable across runs and platforms.</summary>
    internal static class PlanHash
    {
        private const ulong Offset = 14695981039346656037UL;
        private const ulong Prime = 1099511628211UL;
        private const double Quantum = 20.0; // 1 / 0.05 m

        public static ulong Begin(int salt) => Add(Offset, salt);

        public static ulong Add(ulong h, long v)
        {
            unchecked
            {
                ulong u = (ulong)v;
                for (int i = 0; i < 8; i++)
                {
                    h ^= u & 0xFFUL;
                    h *= Prime;
                    u >>= 8;
                }
                return h;
            }
        }

        public static ulong AddF(ulong h, float f)
        {
            if (float.IsNaN(f) || float.IsInfinity(f)) return Add(h, long.MinValue);
            return Add(h, (long)Math.Round(f * Quantum));
        }

        public static ulong AddV2(ulong h, Vec2 v) => AddF(AddF(h, v.X), v.Z);
        public static ulong AddV3(ulong h, Vec3 v) => AddF(AddF(AddF(h, v.X), v.Y), v.Z);

        public static ulong Finish(ulong h)
        {
            unchecked
            {
                h ^= h >> 30; h *= 0xbf58476d1ce4e5b9UL;
                h ^= h >> 27; h *= 0x94d049bb133111ebUL;
                h ^= h >> 31;
                return h;
            }
        }
    }
}
