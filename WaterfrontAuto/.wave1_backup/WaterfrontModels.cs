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
    }
}
