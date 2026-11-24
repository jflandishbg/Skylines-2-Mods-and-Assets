using System;
using System.Collections.Generic;
using System.Linq;
using WaterfrontAuto.Core;

namespace WaterfrontAuto.Tests
{
    internal sealed class MockWorld : IWorldSampler
    {
        public Func<Vec2, float> TerrainFn;
        public Func<Vec2, float> DepthFn;
        public float SeaLevel = 10f;

        public float TerrainHeight(Vec2 p) => TerrainFn(p);
        public float WaterDepth(Vec2 p) => DepthFn(p);
        public float WaterSurfaceHeight(Vec2 p) => TerrainHeight(p) + WaterDepth(p);
    }

    internal static class Program
    {
        private static int _passed;
        private static int _failed;

        private static void Assert(bool cond, string msg)
        {
            if (cond) { _passed++; }
            else { _failed++; Console.WriteLine("FAIL: " + msg); }
        }

        /// <summary>Creates a lot with Front facing +Z (road at z+depth/2) and Back facing -Z (water at z-depth/2).</summary>
        private static BuildingLot MakeLotFacingNorth(long id, float centerX, float backZ, float width, float depth, BuildingZoneKind zone, float lotY = 17f, bool placemaker = false)
        {
            float halfW = width * 0.5f;
            float frontZ = backZ + depth;
            float centerZ = backZ + depth * 0.5f;
            // BuildingUtils.CalculateCorners order: [0] Back-Right (+X,-Z), [1] Back-Left (-X,-Z), [2] Front-Left (-X,+Z), [3] Front-Right (+X,+Z)
            return new BuildingLot
            {
                EntityId = id,
                Center = new Vec3(centerX, lotY, centerZ),
                Corners = new[]
                {
                    new Vec2(centerX + halfW, backZ),
                    new Vec2(centerX - halfW, backZ),
                    new Vec2(centerX - halfW, frontZ),
                    new Vec2(centerX + halfW, frontZ),
                },
                Width = width,
                Depth = depth,
                LotElevation = lotY,
                ZoneKind = zone,
                IsPlacemakerOwned = placemaker,
            };
        }

        /// <summary>Creates a lot with Front facing -X (road to west) and Back facing +X (water to east).</summary>
        private static BuildingLot MakeLotFacingWest(long id, float backX, float centerZ, float width, float depth, BuildingZoneKind zone, float lotY = 17f)
        {
            float halfW = width * 0.5f;
            float frontX = backX - depth;
            float centerX = backX - depth * 0.5f;
            return new BuildingLot
            {
                EntityId = id,
                Center = new Vec3(centerX, lotY, centerZ),
                Corners = new[]
                {
                    new Vec2(backX, centerZ + halfW),
                    new Vec2(backX, centerZ - halfW),
                    new Vec2(frontX, centerZ - halfW),
                    new Vec2(frontX, centerZ + halfW),
                },
                Width = width,
                Depth = depth,
                LotElevation = lotY,
                ZoneKind = zone,
            };
        }

        public static int Main()
        {
            Test1_SawtoothResidentialBeachCliff();
            Test2_ExposedSideEdgeWrap();
            Test3_Industrial90DegreeBayWithIsland();
            Test4_GapCoveBridgeAndStreetAccessSpur();
            Test5_AllThreeModesAndTransitionsContinuousWalk();
            Test6_PlacemakerExclusionAndExistingQuayRespect();
            Test7_OverrideBrushModesAndNaturalCliff();
            Test8_CargoHarborAndWaterwayProtection();
            Test9_NoSurfaceOverlapOnRoad();
            Test10_StraightAtlanticCityBoardwalkAndSeawardBeach();
            Test11_PlacemakerBeachCurl();
            Test12_EntityMatcherTightOwnershipAndConsumeOnce();
            Test13_SpatialDedupeAndManifestRoundtrip();
            Test14_LargeCitySpeedBenchmark();
            Test15_LongShippingLaneProtection();
            Test16_SpurStopsAtSidewalkAndRespectsGrade();
            Test17_CanalBanksAndRailwayProtection();
            Test18_PlanHashDeterminismAndStackedAdopt();
            Test19_PlacemakerBeachExtensionAndSafeDeckProps();

            Console.WriteLine($"Tests completed: {_passed} passed, {_failed} failed.");
            return _failed == 0 ? 0 : 1;
        }

        private static void Test1_SawtoothResidentialBeachCliff()
        {
            // Mirrors Image 1: staggered-depth houses backing onto a 7m cliff into open water (SeaLevel=10, LotY=17)
            Func<Vec2, float> tFn = p => p.Z >= 0f ? 17f : (p.Z > -4f ? 17f + p.Z * 3.0f : 5f);
            var world = new MockWorld
            {
                SeaLevel = 10f,
                TerrainFn = tFn,
                DepthFn = p => Math.Max(0f, 10f - tFn(p)),
            };
            var buildings = new List<BuildingLot>
            {
                MakeLotFacingNorth(1, 0f, 0f, 16f, 24f, BuildingZoneKind.LowRes),
                MakeLotFacingNorth(2, 16f, 6f, 16f, 18f, BuildingZoneKind.LowRes), // recessed 6m!
                MakeLotFacingNorth(3, 32f, 0f, 16f, 24f, BuildingZoneKind.LowRes),
                MakeLotFacingNorth(4, 48f, 4f, 16f, 20f, BuildingZoneKind.LowRes),
            };
            var roads = new List<ExistingNetSegment>
            {
                new ExistingNetSegment { EntityId = 900, Start = new Vec3(-20, 17, 30), End = new Vec3(80, 17, 30), Width = 12, IsRoad = true }
            };

            // Default mode: Atlantic City boardwalk + seaward sand behind cliff homes (no terrain trenches!)
            var plan = WaterfrontPlanner.Plan(buildings, roads, null, world, new WaterfrontConfig());

            Assert(plan.Chains.Count == 1, "T1: should form 1 continuous chain");
            Assert(plan.BeachSegments > 0 && plan.BoardwalkSegments == 0 && plan.IndustrialSegments == 0, "T1: all segments should be Beach/Home mode");
            Assert(plan.BeachGrades.Count == 0, "T1: default config must NOT carve terrain trenches under cliffs");
            Assert(!plan.Surfaces.Any(s => s.Role == SurfaceRole.Sand), "T1: must NOT paint Sand underwater off a steep cliff");
            Assert(plan.Nets.Any(n => n.Role == NetRole.Boardwalk), "T1: default HomesUseBoardwalk should emit grand timber boardwalk");

            // Flush stone quay option for homes (HomesUseBoardwalk = false)
            var quayPlan = WaterfrontPlanner.Plan(buildings, roads, null, world, new WaterfrontConfig { HomesUseBoardwalk = false });
            Assert(quayPlan.Nets.Any(n => n.Role == NetRole.BeachBoardwalkFallback && !n.Elevated), "T1b: HomesUseBoardwalk=false should emit flush narrow quay behind cliff homes");

            // Opt-in seaward Beach terrain grading
            var carvedPlan = WaterfrontPlanner.Plan(buildings, roads, null, world, new WaterfrontConfig { EnableBeachTerrain = true });
            Assert(carvedPlan.BeachGrades.Count > 0, "T1c: opt-in EnableBeachTerrain should emit seaward Beach terrain grading patches");

            // Ensure spine never clips inside any building footprint
            foreach (var v in plan.Chains[0].Spine)
                foreach (var b in buildings)
                    Assert(!Geom2D.PointInConvexQuad(v.Pos, b.Corners, 0.5f), $"T1: spine {v.Pos} must not clip building {b.EntityId}");
        }

        private static void Test2_ExposedSideEdgeWrap()
        {
            // Mirrors Image 2: corner house with water along BOTH back (z<0) and west side (x<-8)
            var world = new MockWorld
            {
                SeaLevel = 10f,
                TerrainFn = p => (p.Z >= 0f && p.X >= -8f) ? 17f : 6f,
                DepthFn = p => (p.Z < -1f || p.X < -9f) ? 4f : 0f,
            };
            var buildings = new List<BuildingLot>
            {
                MakeLotFacingNorth(10, 0f, 0f, 16f, 24f, BuildingZoneKind.LowRes),
                MakeLotFacingNorth(11, 16f, 0f, 16f, 24f, BuildingZoneKind.LowRes),
            };

            var plan = WaterfrontPlanner.Plan(buildings, null, null, world, new WaterfrontConfig());
            Assert(plan.DetectedEdges >= 3, $"T2: expected >=3 detected edges (2 backs + 1 exposed side), got {plan.DetectedEdges}");
            Assert(plan.Chains.Count == 1, $"T2: exposed side + backs should wrap into 1 continuous chain, got {plan.Chains.Count}");
        }

        private static void Test3_Industrial90DegreeBayWithIsland()
        {
            // Mirrors Image 3: 90-degree industrial bay with a small island 14m out in one spot and open water elsewhere
            var world = new MockWorld
            {
                SeaLevel = 10f,
                TerrainFn = p =>
                {
                    // Bay water is in x > 0 AND z < 0, except a small island around (18, -30) radius 8
                    bool inBay = p.X > 0f && p.Z < 0f;
                    bool onIsland = Vec2.Distance(p, new Vec2(18f, -30f)) < 8f;
                    return (inBay && !onIsland) ? 4f : 17f;
                },
                DepthFn = p =>
                {
                    bool inBay = p.X > 1f && p.Z < -1f;
                    bool onIsland = Vec2.Distance(p, new Vec2(18f, -30f)) < 8.5f;
                    return (inBay && !onIsland) ? 6f : 0f;
                },
            };

            var buildings = new List<BuildingLot>
            {
                // West wing facing west, backs on x=0 (water to +X)
                MakeLotFacingWest(20, 0f, -60f, 24f, 24f, BuildingZoneKind.Industrial),
                MakeLotFacingWest(21, 0f, -36f, 24f, 24f, BuildingZoneKind.Industrial),
                MakeLotFacingWest(22, 0f, -12f, 24f, 24f, BuildingZoneKind.Industrial),
                // North wing facing north, backs on z=0 (water to -Z)
                MakeLotFacingNorth(23, 18f, 0f, 24f, 24f, BuildingZoneKind.Industrial),
                MakeLotFacingNorth(24, 42f, 0f, 24f, 24f, BuildingZoneKind.Industrial),
                MakeLotFacingNorth(25, 66f, 0f, 24f, 24f, BuildingZoneKind.Industrial),
            };
            var roads = new List<ExistingNetSegment>
            {
                new ExistingNetSegment { EntityId = 901, Start = new Vec3(-30, 17, 30), End = new Vec3(90, 17, 30), Width = 12, IsRoad = true },
                new ExistingNetSegment { EntityId = 902, Start = new Vec3(-30, 17, -80), End = new Vec3(-30, 17, 30), Width = 12, IsRoad = true },
            };

            var plan = WaterfrontPlanner.Plan(buildings, roads, null, world, new WaterfrontConfig());
            Assert(plan.Chains.Count == 1, $"T3: 90-degree industrial bay should form 1 continuous chain, got {plan.Chains.Count}");
            Assert(plan.IndustrialSegments > 0, "T3: should emit IndustrialQuay segments");
            Assert(plan.FingerPiers >= 1, $"T3: should emit at least 1 finger pier into open water, got {plan.FingerPiers}");

            // Verify NO finger pier endpoint lands on the island!
            foreach (var pier in plan.Nets.Where(n => n.Role == NetRole.IndustrialPier))
            {
                float distToIsland = Vec2.Distance(pier.D.XZ, new Vec2(18f, -30f));
                Assert(distToIsland > 8.5f, $"T3: finger pier end {pier.D.XZ} must not hit island (dist={distToIsland:F1})");
            }
        }

        private static void Test4_GapCoveBridgeAndStreetAccessSpur()
        {
            // Mirrors Image 4: 22m gap cove between two commercial buildings with a road behind
            var world = new MockWorld
            {
                SeaLevel = 10f,
                TerrainFn = p => p.Z >= 0f ? 16f : 5f,
                DepthFn = p => p.Z < -1f ? 5f : 0f,
            };
            var buildings = new List<BuildingLot>
            {
                MakeLotFacingNorth(30, 0f, 0f, 16f, 20f, BuildingZoneKind.Commercial),
                // 22m unzoned gap between x=8 and x=30!
                MakeLotFacingNorth(31, 38f, 0f, 16f, 20f, BuildingZoneKind.Commercial),
            };
            var roads = new List<ExistingNetSegment>
            {
                new ExistingNetSegment { EntityId = 910, Start = new Vec3(-20, 16, 26), End = new Vec3(60, 16, 26), Width = 12, IsRoad = true }
            };

            var plan = WaterfrontPlanner.Plan(buildings, roads, null, world, new WaterfrontConfig());
            Assert(plan.Chains.Count == 1, $"T4: 22m gap should bridge into 1 continuous chain, got {plan.Chains.Count}");
            Assert(plan.AccessSpurs >= 1, $"T4: should spawn at least 1 street-end access spur, got {plan.AccessSpurs}");
        }

        private static void Test5_AllThreeModesAndTransitionsContinuousWalk()
        {
            // Full mixed coastline: Homes (Beach) -> Commercial/HighRes/Office (Boardwalk) -> Industrial (Pier) -> Homes (Beach)
            // Tests ALL THREE transition pairs: Boardwalk<->Beach, Boardwalk<->Industrial, Beach<->Industrial!
            var world = new MockWorld
            {
                SeaLevel = 10f,
                TerrainFn = p => p.Z >= 0f ? 16.5f : 5f,
                DepthFn = p => p.Z < -1f ? 5f : 0f,
            };
            var buildings = new List<BuildingLot>
            {
                MakeLotFacingNorth(40, 0f,   0f, 16f, 20f, BuildingZoneKind.LowRes),
                MakeLotFacingNorth(41, 16f,  0f, 16f, 20f, BuildingZoneKind.MedRes),
                MakeLotFacingNorth(42, 32f,  0f, 16f, 20f, BuildingZoneKind.Commercial),
                MakeLotFacingNorth(43, 48f,  0f, 16f, 20f, BuildingZoneKind.Office),
                MakeLotFacingNorth(44, 64f,  0f, 16f, 20f, BuildingZoneKind.HighRes),
                MakeLotFacingNorth(45, 80f,  0f, 16f, 20f, BuildingZoneKind.Industrial),
                MakeLotFacingNorth(46, 96f,  0f, 16f, 20f, BuildingZoneKind.Industrial),
                MakeLotFacingNorth(47, 112f, 0f, 16f, 20f, BuildingZoneKind.Industrial),
                MakeLotFacingNorth(48, 128f, 0f, 16f, 20f, BuildingZoneKind.LowRes),
                MakeLotFacingNorth(49, 144f, 0f, 16f, 20f, BuildingZoneKind.LowRes),
            };
            var cfg = new WaterfrontConfig();
            var plan = WaterfrontPlanner.Plan(buildings, null, null, world, cfg);

            Assert(plan.Chains.Count == 1, $"T5: full 3-zone coastline must be 1 continuous chain, got {plan.Chains.Count}");
            Assert(plan.BeachSegments > 0 && plan.BoardwalkSegments > 0 && plan.IndustrialSegments > 0,
                $"T5: must contain all 3 modes (beach={plan.BeachSegments}, bw={plan.BoardwalkSegments}, ind={plan.IndustrialSegments})");

            var spine = plan.Chains[0].Spine;
            Assert(spine.Any(v => v.Transition == TransitionKind.BoardwalkToBeach), "T5: missing Boardwalk<->Beach transition");
            Assert(spine.Any(v => v.Transition == TransitionKind.BoardwalkToIndustrial), "T5: missing Boardwalk<->Industrial transition");
            Assert(spine.Any(v => v.Transition == TransitionKind.BeachToIndustrial), "T5: missing Beach<->Industrial transition");

            // Verify continuous bit-identical endpoint stitching and safe pedestrian grade across the whole spine
            var spineNets = plan.Nets.Where(n => n.Role != NetRole.IndustrialPier && n.Role != NetRole.AccessSpur).ToList();
            Assert(spineNets.Count >= 8, $"T5: expected >=8 continuous spine segments, got {spineNets.Count}");
            for (int i = 1; i < spineNets.Count; i++)
            {
                Assert(spineNets[i - 1].D.Equals(spineNets[i].A), $"T5: spine segment {i - 1}->{i} must share exact endpoint for CS2 node welding");
            }
            for (int i = 1; i < spine.Count; i++)
            {
                float horiz = Math.Max(0.5f, Vec2.Distance(spine[i - 1].Pos, spine[i].Pos));
                float grade = Math.Abs(spine[i].TargetY - spine[i - 1].TargetY) / horiz;
                Assert(grade <= cfg.MaxPedestrianGrade + 0.02f, $"T5: excessive grade {grade:F3} between spine[{i - 1}] and spine[{i}]");
            }
            Assert(plan.Props.Any(p => p.Role == PropRole.TransitionRock), "T5: expected transition rock groins/riprap");
        }

        private static void Test6_PlacemakerExclusionAndExistingQuayRespect()
        {
            var world = new MockWorld
            {
                SeaLevel = 10f,
                TerrainFn = p => p.Z >= 0f ? 17f : 5f,
                DepthFn = p => p.Z < -1f ? 5f : 0f,
            };
            var buildings = new List<BuildingLot>
            {
                MakeLotFacingNorth(60, 0f, 0f, 16f, 20f, BuildingZoneKind.Commercial, placemaker: true),
                MakeLotFacingNorth(61, 24f, 0f, 16f, 20f, BuildingZoneKind.Commercial, placemaker: false),
            };
            // Existing player/Placemaker quay in front of building 61
            var existingNets = new List<ExistingNetSegment>
            {
                new ExistingNetSegment { EntityId = 950, Start = new Vec3(14, 17, -4), End = new Vec3(34, 17, -4), Width = 6, IsPathway = true, IsQuayOrPier = true }
            };

            var plan = WaterfrontPlanner.Plan(buildings, existingNets, null, world, new WaterfrontConfig { RespectPlacemaker = true });
            Assert(plan.SkippedPlacemaker == 1, $"T6: should skip 1 Placemaker lot, got {plan.SkippedPlacemaker}");
            Assert(plan.DetectedEdges == 0, $"T6: existing quay should prevent duplicate waterfront, got {plan.DetectedEdges} edges");
        }

        private static void Test7_OverrideBrushModesAndNaturalCliff()
        {
            var world = new MockWorld
            {
                SeaLevel = 10f,
                TerrainFn = p => p.Z >= 0f ? 16.5f : 5f,
                DepthFn = p => p.Z < -1f ? 5f : 0f,
            };
            var buildings = new List<BuildingLot>
            {
                MakeLotFacingNorth(70, 0f, 0f, 16f, 20f, BuildingZoneKind.LowRes),  // overridden to Boardwalk
                MakeLotFacingNorth(71, 16f, 0f, 16f, 20f, BuildingZoneKind.LowRes), // overridden to Off (Natural Cliff)
            };
            var overrides = new List<OverrideZone>
            {
                new OverrideZone { Center = new Vec2(0f, 0f), Radius = 12f, Mode = WaterfrontMode.Boardwalk },
                new OverrideZone { Center = new Vec2(16f, 0f), Radius = 12f, Mode = WaterfrontMode.Off },
            };

            var plan = WaterfrontPlanner.Plan(buildings, null, overrides, world, new WaterfrontConfig());
            Assert(plan.BoardwalkSegments > 0 && plan.BeachSegments == 0, "T7: override should force LowRes lot to Boardwalk");
            Assert(plan.DetectedEdges == 1, $"T7: Off override should leave second lot as natural cliff, got {plan.DetectedEdges}");
        }

        private static void Test8_CargoHarborAndWaterwayProtection()
        {
            // Mirrors Images 2-4: Cargo/Passenger Harbor + active shipping lane must NEVER be wrapped or blocked!
            Func<Vec2, float> tFn = p => p.Z >= 0f ? 17f : 4f;
            var world = new MockWorld
            {
                SeaLevel = 10f,
                TerrainFn = tFn,
                DepthFn = p => Math.Max(0f, 10f - tFn(p)),
            };
            var harbor = MakeLotFacingNorth(80, 0f, 0f, 120f, 80f, BuildingZoneKind.Industrial);
            harbor.IsMaritimeBuilding = true;
            var normalInd = MakeLotFacingNorth(81, 140f, 0f, 80f, 24f, BuildingZoneKind.Industrial);
            var shipLane = new ExistingNetSegment
            {
                EntityId = 980,
                Start = new Vec3(-50f, 10f, -18f),
                End = new Vec3(220f, 10f, -18f),
                Width = 32f,
                IsWaterway = true,
            };

            var plan = WaterfrontPlanner.Plan(new List<BuildingLot> { harbor, normalInd }, new List<ExistingNetSegment> { shipLane }, null, world, new WaterfrontConfig());
            Assert(plan.DetectedEdges == 0, $"T8: maritime harbor + shipping lane must produce 0 wrapped edges, got {plan.DetectedEdges}");
            Assert(plan.FingerPiers == 0, $"T8: must not spawn finger piers into shipping lane, got {plan.FingerPiers}");
        }

        private static void Test9_NoSurfaceOverlapOnRoad()
        {
            // Mirrors Image 1: road running right near the shoreline must NEVER be covered by a surface slab!
            Func<Vec2, float> tFn = p => p.Z >= 0f ? 16f : 5f;
            var world = new MockWorld
            {
                SeaLevel = 10f,
                TerrainFn = tFn,
                DepthFn = p => Math.Max(0f, 10f - tFn(p)),
            };
            var buildings = new List<BuildingLot>
            {
                MakeLotFacingNorth(90, 0f, 0f, 16f, 12f, BuildingZoneKind.Commercial),
                MakeLotFacingNorth(91, 16f, 0f, 16f, 12f, BuildingZoneKind.Commercial),
            };
            // Road very close to shoreline
            var closeRoad = new ExistingNetSegment
            {
                EntityId = 990,
                Start = new Vec3(-20f, 16f, 1f),
                End = new Vec3(50f, 16f, 1f),
                Width = 10f,
                IsRoad = true,
            };

            var plan = WaterfrontPlanner.Plan(buildings, new List<ExistingNetSegment> { closeRoad }, null, world, new WaterfrontConfig());
            Assert(plan.Surfaces.Count == 0, $"T9: surface near road must be suppressed so road is never covered, got {plan.Surfaces.Count}");
        }

        private static void Test10_StraightAtlanticCityBoardwalkAndSeawardBeach()
        {
            // Mirrors Image 2: two recessed shorter buildings in middle of block must NOT create U-dips!
            // Dry beach band from z=-12 to z=0, open ocean past z=-12 (within 17.5m probe of recessed buildings at z=5)
            Func<Vec2, float> tFn = p => p.Z >= 0f ? 14f : (p.Z > -12f ? 11.2f : 5f);
            var world = new MockWorld
            {
                SeaLevel = 10f,
                TerrainFn = tFn,
                DepthFn = p => p.Z < -12f ? 5f : 0f,
            };
            var buildings = new List<BuildingLot>
            {
                MakeLotFacingNorth(100, 0f,  0f, 16f, 24f, BuildingZoneKind.Commercial, lotY: 14f),
                MakeLotFacingNorth(101, 16f, 5f, 16f, 19f, BuildingZoneKind.Commercial, lotY: 14f), // recessed 5m!
                MakeLotFacingNorth(102, 32f, 5f, 16f, 19f, BuildingZoneKind.Commercial, lotY: 14f), // recessed 5m!
                MakeLotFacingNorth(103, 48f, 0f, 16f, 24f, BuildingZoneKind.Commercial, lotY: 14f),
            };

            var plan = WaterfrontPlanner.Plan(buildings, null, null, world, new WaterfrontConfig { StraightenBlocks = true, AtlanticCityBeach = true });
            Assert(plan.Chains.Count == 1, "T10: block must form 1 chain");

            // Check that the spine stays nearly straight along Z (no 8m U-dip!)
            var zs = plan.Chains[0].Spine.Select(v => v.Pos.Z).ToList();
            float zRange = zs.Max() - zs.Min();
            Assert(zRange < 2.0f, $"T10: StraightenBlocks should keep boardwalk even (zRange={zRange:F2}m, expected <2m)");

            // Atlantic City cross-section: Sand beach must lie SEAWARD (more negative Z) of boardwalk!
            var sand = plan.Surfaces.Where(s => s.Role == SurfaceRole.Sand).ToList();
            Assert(sand.Count > 0, "T10: AtlanticCityBeach should emit sand surfaces seaward of boardwalk");
            float boardwalkZ = zs.Average();
            foreach (var s in sand)
            {
                float sandZ = s.Ring.Average(p => p.Z);
                Assert(sandZ < boardwalkZ - 2f, $"T10: sand ({sandZ:F1}) must sit seaward of boardwalk ({boardwalkZ:F1})");
            }
            Assert(plan.Props.Any(p => p.Role == PropRole.BoardwalkLamp), "T10: boardwalk should have lamps");
            Assert(plan.Props.Any(p => p.Role == PropRole.BoardwalkBench), "T10: boardwalk should have benches");
            Assert(plan.Props.Any(p => p.Role == PropRole.BoardwalkKiosk || p.Role == PropRole.BoardwalkGazebo), "T10: recessed boardwalk terrace should get kiosk/gazebo");
        }

        private static void Test11_PlacemakerBeachCurl()
        {
            // Mirrors Images 1 & 3: Placemaker sand beach sitting right beside end of building row
            Func<Vec2, float> tFn = p => p.Z >= -8f ? 12f : 5f;
            var world = new MockWorld
            {
                SeaLevel = 10f,
                TerrainFn = tFn,
                DepthFn = p => p.Z < -8f ? 5f : (p.X >= 0f && p.Z < -2f ? 1f : 0f),
            };
            var buildings = new List<BuildingLot>
            {
                MakeLotFacingNorth(110, 10f, 0f, 16f, 20f, BuildingZoneKind.Commercial, lotY: 13f),
                MakeLotFacingNorth(111, 26f, 0f, 16f, 20f, BuildingZoneKind.Commercial, lotY: 13f),
            };
            // Placemaker beach just west of x=2 (around x=-15, z=-4)
            var pmBeach = new ExistingBeachArea
            {
                EntityId = 5000,
                Center = new Vec2(-16f, -4f),
                Radius = 14f,
                IsPlacemakerOwned = true,
                Ring = new[] { new Vec2(-28f, 4f), new Vec2(-4f, 4f), new Vec2(-4f, -12f), new Vec2(-28f, -12f) },
            };

            var plan = WaterfrontPlanner.Plan(buildings, null, null, world, new WaterfrontConfig(), new List<ExistingBeachArea> { pmBeach });
            Assert(plan.BeachCurls >= 1, $"T11: boardwalk end adjacent to Placemaker beach should emit curl ramp, got {plan.BeachCurls}");
            Assert(PlanValidator.Audit(plan, buildings, null, world, new WaterfrontConfig()).Count == 0, "T11: PlanValidator audit must be clean");
        }

        private static void Test12_EntityMatcherTightOwnershipAndConsumeOnce()
        {
            // Two planned lamps 0.6m apart + unrelated prefab nearby + owned entity + Temp entity
            var pending = new List<PendingItem>
            {
                new PendingItem { Kind = TrackedKind.Object, PrefabName = "LightpolePark01", Pos = new Vec2(10.0f, 10.0f) },
                new PendingItem { Kind = TrackedKind.Object, PrefabName = "LightpolePark01", Pos = new Vec2(10.6f, 10.0f) },
                new PendingItem { Kind = TrackedKind.Area, PrefabName = "Sand Surface 01", Pos = new Vec2(20.0f, 20.0f) },
            };
            var candidates = new List<LiveCandidate>
            {
                // Unrelated prefab sitting right on top of pending[0] — MUST NOT be claimed!
                new LiveCandidate { EntityId = 1, Kind = TrackedKind.Object, PrefabName = "OakTree01", Pos = new Vec2(10.0f, 10.0f) },
                // Owned entity with matching prefab — MUST NOT be claimed!
                new LiveCandidate { EntityId = 2, Kind = TrackedKind.Object, PrefabName = "LightpolePark01", Pos = new Vec2(10.05f, 10.0f), HasOwner = true },
                // Temp entity with matching prefab — MUST NOT be claimed!
                new LiveCandidate { EntityId = 3, Kind = TrackedKind.Object, PrefabName = "LightpolePark01", Pos = new Vec2(10.05f, 10.0f), IsTemp = true },
                // Genuine created lamp 1
                new LiveCandidate { EntityId = 4, Kind = TrackedKind.Object, PrefabName = "LightpolePark01", Pos = new Vec2(10.1f, 10.0f) },
                // Genuine created lamp 2
                new LiveCandidate { EntityId = 5, Kind = TrackedKind.Object, PrefabName = "LightpolePark01", Pos = new Vec2(10.65f, 10.0f) },
                // Extra third lamp 0.2m away — MUST NOT be claimed because both pending items were consumed!
                new LiveCandidate { EntityId = 6, Kind = TrackedKind.Object, PrefabName = "LightpolePark01", Pos = new Vec2(10.15f, 10.0f) },
                // Area > 1.0m away — MUST NOT be claimed (tests tight 1.0m area tolerance)
                new LiveCandidate { EntityId = 7, Kind = TrackedKind.Area, PrefabName = "Sand Surface 01", Pos = new Vec2(21.5f, 20.0f) },
            };

            var claimed = EntityMatcher.MatchCreated(pending, candidates, out int unmatched);
            Assert(claimed.Count == 2, $"T12: expected exactly 2 claimed entities (consume-once), got {claimed.Count}");
            Assert(claimed.Contains(4) && claimed.Contains(5), "T12: must claim exact unowned non-Temp matching lamps 4 & 5");
            Assert(!claimed.Contains(1) && !claimed.Contains(2) && !claimed.Contains(3) && !claimed.Contains(6) && !claimed.Contains(7), "T12: must reject wrong prefab, Owner, Temp, extra, and out-of-tolerance");
            Assert(unmatched == 1, $"T12: expected 1 unmatched pending area, got {unmatched}");
        }

        private static void Test13_SpatialDedupeAndManifestRoundtrip()
        {
            // Dedupe index catches existing surface within 0.5m and prop within 1.0m
            var dedupe = new SpatialDedupeIndex();
            dedupe.Add(new LiveCandidate { EntityId = 100, Kind = TrackedKind.Area, PrefabName = "Sand Surface 01", Pos = new Vec2(50.0f, -10.0f) });
            dedupe.Add(new LiveCandidate { EntityId = 101, Kind = TrackedKind.Object, PrefabName = "GardenBench01", Pos = new Vec2(52.0f, -4.0f) });

            Assert(dedupe.HasDuplicate(TrackedKind.Area, "Sand Surface 01", new Vec2(50.3f, -10.1f), EntityMatcher.AreaDedupeTolerance, out long aid) && aid == 100, "T13: duplicate surface within 0.5m must be detected");
            Assert(!dedupe.HasDuplicate(TrackedKind.Area, "Tiles Surface 01", new Vec2(50.0f, -10.0f), EntityMatcher.AreaDedupeTolerance, out _), "T13: different surface prefab must not dedupe");
            Assert(dedupe.HasDuplicate(TrackedKind.Object, "GardenBench01", new Vec2(52.7f, -4.2f), EntityMatcher.ObjectDedupeTolerance, out long oid) && oid == 101, "T13: duplicate prop within 1.0m must be detected");

            // Manifest serialize -> parse -> adopt (with 1 live match + 1 stale row with no match)
            var rows = new List<ManifestRow>
            {
                new ManifestRow { Kind = TrackedKind.Edge, PrefabName = "LeisurePier01Large01", X = 12.34f, Z = -45.67f },
                new ManifestRow { Kind = TrackedKind.Object, PrefabName = "GardenBench01", X = 999.0f, Z = 999.0f }, // stale!
            };
            string text = EntityMatcher.SerializeManifest(rows);
            var parsed = EntityMatcher.ParseManifest(text);
            Assert(parsed.Count == 2 && parsed[0].PrefabName == "LeisurePier01Large01", "T13: manifest roundtrip parse");

            var live = new List<LiveCandidate>
            {
                new LiveCandidate { EntityId = 777, Kind = TrackedKind.Edge, PrefabName = "LeisurePier01Large01", Pos = new Vec2(12.4f, -45.6f) },
            };
            var adopted = EntityMatcher.MatchManifest(parsed, live, out int dropped);
            Assert(adopted.Count == 1 && adopted[0] == 777 && dropped == 1, $"T13: manifest must adopt 777 and drop 1 stale row (got {adopted.Count}, dropped={dropped})");
        }

        private static void Test14_LargeCitySpeedBenchmark()
        {
            // Verify O(N) spatial hash handles 4,000 inland + 40 waterfront buildings + 3,000 roads in < 150ms!
            Func<Vec2, float> tFn = p => p.Z >= 0f ? 17f : 5f;
            var world = new MockWorld { SeaLevel = 10f, TerrainFn = tFn, DepthFn = p => p.Z < -2f ? 5f : 0f };
            var buildings = new List<BuildingLot>(4040);
            var nets = new List<ExistingNetSegment>(3000);
            for (int i = 0; i < 40; i++)
                buildings.Add(MakeLotFacingNorth(i + 1, i * 16f, 0f, 16f, 20f, BuildingZoneKind.Commercial));
            for (int i = 0; i < 4000; i++)
                buildings.Add(MakeLotFacingNorth(1000 + i, (i % 100) * 20f, 100f + (i / 100) * 30f, 16f, 16f, BuildingZoneKind.LowRes));
            for (int i = 0; i < 3000; i++)
                nets.Add(new ExistingNetSegment { EntityId = 10000 + i, Start = new Vec3((i % 100) * 20f, 17f, 90f + (i / 100) * 30f), End = new Vec3((i % 100) * 20f + 18f, 17f, 90f + (i / 100) * 30f), Width = 12f, IsRoad = true });

            var sw = System.Diagnostics.Stopwatch.StartNew();
            var plan = WaterfrontPlanner.Plan(buildings, nets, null, world, new WaterfrontConfig());
            sw.Stop();
            Assert(plan.Chains.Count == 1, "T14: benchmark waterfront chain detected");
            Assert(sw.ElapsedMilliseconds < 2000, $"T14: 4,040-building city plan must be fast (<2000ms), took {sw.ElapsedMilliseconds}ms");
        }

        private static void Test15_LongShippingLaneProtection()
        {
            // P0-5: 2 km shipping lane must be indexed across its full length (no 512 m cell clamp!)
            var world = new MockWorld
            {
                SeaLevel = 10f,
                TerrainFn = p => p.Z >= 0f ? 15f : 2f,
                DepthFn = p => p.Z < -1f ? 8f : 0f,
            };
            var buildings = new List<BuildingLot>
            {
                MakeLotFacingNorth(1500, 1500f, 0f, 16f, 20f, BuildingZoneKind.Industrial, lotY: 15f),
            };
            var waterway = new ExistingNetSegment
            {
                EntityId = 15001,
                Start = new Vec3(0f, 10f, -16f),
                Mid = new Vec3(1000f, 10f, -16f),
                End = new Vec3(2000f, 10f, -16f),
                Width = 32f,
                IsWaterway = true,
            };
            var plan = WaterfrontPlanner.Plan(buildings, new List<ExistingNetSegment> { waterway }, null, world, new WaterfrontConfig());
            Assert(plan.DetectedEdges == 0, $"T15: 2 km shipping lane at x=1500 must protect shoreline (detected {plan.DetectedEdges})");
        }

        private static void Test16_SpurStopsAtSidewalkAndRespectsGrade()
        {
            // P0-6: Access spur must stop outside road half-width (never enter carriageway) and pass PlanValidator.Audit
            var world = new MockWorld
            {
                SeaLevel = 10f,
                TerrainFn = p => p.Z >= 0f ? 12.5f : 5f,
                DepthFn = p => p.Z < -2f ? 5f : 0f,
            };
            var buildings = new List<BuildingLot>
            {
                MakeLotFacingNorth(1600, 0f, 0f, 16f, 16f, BuildingZoneKind.Commercial, lotY: 12.5f),
                MakeLotFacingNorth(1601, 40f, 0f, 16f, 16f, BuildingZoneKind.Commercial, lotY: 12.5f),
            };
            var road = new ExistingNetSegment
            {
                EntityId = 16001,
                Start = new Vec3(20f, 12.5f, 30f),
                Mid = new Vec3(20f, 12.5f, 12f),
                End = new Vec3(20f, 12.5f, -4f),
                Width = 20f,
                IsRoad = true,
            };
            var plan = WaterfrontPlanner.Plan(buildings, new List<ExistingNetSegment> { road }, null, world, new WaterfrontConfig());
            var issues = PlanValidator.Audit(plan, buildings, new List<ExistingNetSegment> { road }, world, new WaterfrontConfig());
            Assert(issues.Count == 0, $"T16: PlanValidator audit should be clean (got: {string.Join("; ", issues)})");
        }

        private static void Test17_CanalBanksAndRailwayProtection()
        {
            // P0-7: Coastal railway must never be bridged across or overlapped
            var world = new MockWorld
            {
                SeaLevel = 10f,
                TerrainFn = p => p.Z >= 0f ? 14f : 5f,
                DepthFn = p => p.Z < -2f ? 5f : 0f,
            };
            var buildings = new List<BuildingLot>
            {
                MakeLotFacingNorth(1700, 0f, 0f, 16f, 16f, BuildingZoneKind.Commercial, lotY: 14f),
                MakeLotFacingNorth(1701, 34f, 0f, 16f, 16f, BuildingZoneKind.Commercial, lotY: 14f),
            };
            var rail = new ExistingNetSegment
            {
                EntityId = 17001,
                Start = new Vec3(17f, 14f, 30f),
                Mid = new Vec3(17f, 14f, 0f),
                End = new Vec3(17f, 14f, -30f),
                Width = 10f,
                IsRail = true,
            };
            var plan = WaterfrontPlanner.Plan(buildings, new List<ExistingNetSegment> { rail }, null, world, new WaterfrontConfig());
            var issues = PlanValidator.Audit(plan, buildings, new List<ExistingNetSegment> { rail }, world, new WaterfrontConfig());
            Assert(issues.Count == 0, $"T17: boardwalk must not cross coastal railway (got: {string.Join("; ", issues)})");
            Assert(plan.Chains.Count == 2, $"T17: railway between buildings should split into 2 chains, got {plan.Chains.Count}");
        }

        private static void Test18_PlanHashDeterminismAndStackedAdopt()
        {
            // P0-2 & P0-9: Identical plans produce identical hash; FindAllWithin finds ALL stacked copies
            var world = new MockWorld
            {
                SeaLevel = 10f,
                TerrainFn = p => p.Z >= 0f ? 14f : 5f,
                DepthFn = p => p.Z < -2f ? 5f : 0f,
            };
            var buildings = new List<BuildingLot>
            {
                MakeLotFacingNorth(1800, 0f, 0f, 16f, 20f, BuildingZoneKind.Commercial, lotY: 14f),
                MakeLotFacingNorth(1801, 16f, 0f, 16f, 20f, BuildingZoneKind.Commercial, lotY: 14f),
            };
            var p1 = WaterfrontPlanner.Plan(buildings, null, null, world, new WaterfrontConfig());
            var p2 = WaterfrontPlanner.Plan(buildings, null, null, world, new WaterfrontConfig());
            Assert(p1.ComputePlanHash() == p2.ComputePlanHash(), "T18: identical inputs must produce identical ComputePlanHash()");

            var idx = new SpatialDedupeIndex();
            idx.Add(new LiveCandidate { EntityId = 101, Kind = TrackedKind.Area, PrefabName = "Sand Surface 01", Pos = new Vec2(10f, 10f) });
            idx.Add(new LiveCandidate { EntityId = 102, Kind = TrackedKind.Area, PrefabName = "Sand Surface 01", Pos = new Vec2(10.2f, 10.1f) });
            idx.Add(new LiveCandidate { EntityId = 103, Kind = TrackedKind.Area, PrefabName = "Sand Surface 01", Pos = new Vec2(10.3f, 9.9f) });
            var found = new List<long>();
            int cnt = idx.FindAllWithin(TrackedKind.Area, "Sand Surface 01", new Vec2(10f, 10f), 1.0f, found);
            Assert(cnt == 3 && found.Count == 3, $"T18: FindAllWithin must return all 3 stacked copies, got {cnt}");
        }

        private static void Test19_PlacemakerBeachExtensionAndSafeDeckProps()
        {
            // Mirrors Image 3: Beachfront towers flanked by a wide Placemaker beach extending seaward
            Func<Vec2, float> tFn = p => p.Z >= 0f ? 13f : 6f;
            var world = new MockWorld
            {
                SeaLevel = 10f,
                TerrainFn = tFn,
                DepthFn = p => p.Z < -1f ? 4f : 0f,
            };
            var buildings = new List<BuildingLot>
            {
                MakeLotFacingNorth(1900, 10f, 0f, 16f, 20f, BuildingZoneKind.HighRes, lotY: 13f),
                MakeLotFacingNorth(1901, 26f, 0f, 16f, 20f, BuildingZoneKind.HighRes, lotY: 13f),
            };
            // Wide Placemaker beach immediately west of the towers extending out to z = -26
            var pmBeach = new ExistingBeachArea
            {
                EntityId = 19500,
                Center = new Vec2(-20f, -12f),
                Radius = 22f,
                IsPlacemakerOwned = true,
                Ring = new[] { new Vec2(-36f, 2f), new Vec2(-4f, 2f), new Vec2(-4f, -26f), new Vec2(-36f, -26f) },
            };

            var cfg = new WaterfrontConfig { AtlanticCityBeach = true, EnableBeachTerrain = false };
            var plan = WaterfrontPlanner.Plan(buildings, null, null, world, cfg, new List<ExistingBeachArea> { pmBeach });

            Assert(plan.BeachGrades.Any(g => g.IsPlacemakerExtension), "T19: beach towers adjacent to Placemaker beach should emit IsPlacemakerExtension terrain fill");
            Assert(plan.Surfaces.Any(s => s.Role == SurfaceRole.Sand), "T19: extended beach should emit matching Sand surface");
            Assert(plan.Props.Any(p => p.Role == PropRole.BeachParasol), "T19: extended beach should emit umbrellas");
            Assert(PlanValidator.Audit(plan, buildings, null, world, cfg).Count == 0, "T19: PlanValidator audit must be clean");
        }
    }
}
