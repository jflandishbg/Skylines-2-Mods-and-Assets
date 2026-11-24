using System;
using System.Collections.Generic;

namespace WaterfrontAuto.Core
{
    /// <summary>
    /// Full pure-C# Atlantic City Waterfront Planner (v4):
    /// - O(N) spatial-hashed planning (1000x faster than v3 on large cities)
    /// - Even outer promenade alignment across blocks (zero U-dips behind shorter lots)
    /// - Real Atlantic City cross-section: Buildings -> Grand Timber Boardwalk (lamps, benches, kiosks/gazebos) -> Sandy Beach -> Ocean
    /// - Smooth boardwalk curls into adjacent Placemaker beaches
    /// - Industrial Quays + channel-safe working piers
    /// - Road-safe surfaces & LocalConnect street-end access spurs
    /// </summary>
    public static class WaterfrontPlanner
    {
        public static WaterfrontPlan Plan(
            IReadOnlyList<BuildingLot> buildings,
            IReadOnlyList<ExistingNetSegment> existingNets,
            IReadOnlyList<OverrideZone> overrides,
            IWorldSampler sampler,
            WaterfrontConfig cfg,
            IReadOnlyList<ExistingBeachArea> existingBeaches = null)
        {
            var plan = new WaterfrontPlan();
            if (buildings == null || buildings.Count == 0 || sampler == null) return plan;

            var buildingGrid = ShorelineDetector.BuildBuildingGrid(buildings);
            var netGrid = ShorelineDetector.BuildNetGrid(existingNets);

            // 1. Detect all water-facing edges (fast water-first + spatial hash)
            var edges = ShorelineDetector.DetectEdges(buildings, existingNets, sampler, cfg, out int skippedPm, buildingGrid, netGrid);
            plan.SkippedPlacemaker = skippedPm;

            // 2. Classify edges by zone + user override brushes
            ModeClassifier.ClassifyEdges(edges, overrides);
            plan.DetectedEdges = edges.Count;
            if (edges.Count == 0) return plan;

            // 3. Build continuous ordered shoreline chains
            var chains = ShorelineDetector.BuildChains(edges, buildingGrid, sampler, cfg);
            plan.Chains = chains;

            // 4. Plan each chain
            foreach (var chain in chains)
            {
                ShorelineDetector.BuildSpine(chain, buildingGrid, sampler, cfg);
                if (chain.Spine.Count < 2) continue;

                ModeClassifier.MarkTransitions(chain, cfg);
                ComputeElevations(chain, cfg);

                EmitSpineNets(chain, plan, sampler, cfg);
                EmitPocketAndAtlanticCityBeachSurfaces(chain, netGrid, existingBeaches, plan, cfg);
                if (cfg.EnableBeachTerrain)
                    EmitSeawardBeachGrades(chain, existingBeaches, plan, cfg);
                if (cfg.EnableIndustrialPiers)
                    EmitIndustrialFingerPiers(chain, netGrid, plan, sampler, cfg);
                if (cfg.EnableStreetSpurs)
                    EmitStreetAccessSpurs(chain, buildingGrid, netGrid, plan, sampler, cfg);
                if (existingBeaches != null && existingBeaches.Count > 0)
                    EmitPlacemakerBeachCurls(chain, buildingGrid, netGrid, existingBeaches, plan, sampler, cfg);
                if (cfg.EnableProps)
                    EmitProps(chain, existingBeaches, plan, sampler, cfg);
            }

            return plan;
        }

        private static void ComputeElevations(WaterfrontChain chain, WaterfrontConfig cfg)
        {
            var spine = chain.Spine;
            int n = spine.Count;

            for (int i = 0; i < n; i++)
            {
                var v = spine[i];
                float drop = v.LotY - v.WaterY;

                // Seaward beach grading is ONLY applied seaward of the boardwalk/path (never under houses!)
                v.BeachCanGrade = cfg.EnableBeachTerrain
                    && (v.Mode == WaterfrontMode.Beach || (v.Mode == WaterfrontMode.Boardwalk && cfg.AtlanticCityBeach))
                    && drop <= cfg.MaxBeachCliffDrop
                    && v.OpenWaterDist >= cfg.MinBeachChannelWidth;

                switch (v.Mode)
                {
                    case WaterfrontMode.Beach:
                        if (cfg.HomesUseBoardwalk)
                            v.TargetY = Math.Max(v.WaterY + 2.0f, v.LotY - 0.05f);
                        else if (drop <= 3.0f)
                            v.TargetY = Math.Max(v.WaterY + 1.2f, v.LotY);
                        else
                            v.TargetY = Math.Max(v.WaterY + 1.8f, v.LotY - 0.05f);
                        break;

                    case WaterfrontMode.Industrial:
                        v.TargetY = Math.Max(v.WaterY + 2.0f, v.LotY - 0.05f);
                        break;

                    default: // Boardwalk
                        v.TargetY = Math.Max(v.WaterY + 2.0f, v.LotY - 0.05f);
                        break;
                }
            }

            // Smooth grade-limiting pass across transitions
            float maxGrade = Math.Max(0.06f, cfg.MaxPedestrianGrade);
            for (int pass = 0; pass < 4; pass++)
            {
                for (int i = 1; i < n; i++)
                {
                    float d = Math.Max(1f, Vec2.Distance(spine[i - 1].Pos, spine[i].Pos));
                    float maxDelta = d * maxGrade;
                    if (spine[i].TargetY > spine[i - 1].TargetY + maxDelta)
                        spine[i].TargetY = spine[i - 1].TargetY + maxDelta;
                    else if (spine[i].TargetY < spine[i - 1].TargetY - maxDelta)
                        spine[i].TargetY = spine[i - 1].TargetY - maxDelta;
                }
                for (int i = n - 2; i >= 0; i--)
                {
                    float d = Math.Max(1f, Vec2.Distance(spine[i].Pos, spine[i + 1].Pos));
                    float maxDelta = d * maxGrade;
                    if (spine[i].TargetY > spine[i + 1].TargetY + maxDelta)
                        spine[i].TargetY = spine[i + 1].TargetY + maxDelta;
                    else if (spine[i].TargetY < spine[i + 1].TargetY - maxDelta)
                        spine[i].TargetY = spine[i + 1].TargetY - maxDelta;
                }
                for (int i = 0; i < n; i++)
                    spine[i].TargetY = Math.Max(spine[i].TargetY, spine[i].WaterY + 1.15f);
            }
        }

        private static void EmitSpineNets(WaterfrontChain chain, WaterfrontPlan plan, IWorldSampler sampler, WaterfrontConfig cfg)
        {
            var spine = chain.Spine;
            int n = spine.Count;

            for (int i = 0; i < n - 1; i++)
            {
                var v0 = spine[i];
                var v1 = spine[i + 1];
                float len = Vec2.Distance(v0.Pos, v1.Pos);
                if (len < 1.5f) continue;

                bool isTransition = v0.Transition != TransitionKind.None || v1.Transition != TransitionKind.None;
                WaterfrontMode segMode = v0.Mode;
                NetRole role;
                bool elevated;

                if (isTransition && v0.Mode != v1.Mode)
                {
                    role = NetRole.TransitionRamp;
                    elevated = cfg.BoardwalkUseTimberPier && (v0.Mode == WaterfrontMode.Boardwalk || v1.Mode == WaterfrontMode.Boardwalk);
                    plan.TransitionSegments++;
                }
                else
                {
                    switch (segMode)
                    {
                        case WaterfrontMode.Beach:
                            if (cfg.HomesUseBoardwalk)
                            {
                                // Atlantic City style: full timber boardwalk (or stone quay) behind homes, with beach seaward!
                                role = NetRole.Boardwalk;
                                elevated = cfg.BoardwalkUseTimberPier;
                            }
                            else if (v0.LotY - v0.WaterY <= 3.0f && v1.LotY - v1.WaterY <= 3.0f)
                            {
                                role = NetRole.BeachPath;
                                elevated = false;
                            }
                            else
                            {
                                role = NetRole.BeachBoardwalkFallback;
                                elevated = false;
                            }
                            plan.BeachSegments++;
                            break;

                        case WaterfrontMode.Industrial:
                            role = NetRole.IndustrialQuay;
                            elevated = false;
                            plan.IndustrialSegments++;
                            break;

                        default: // Boardwalk
                            role = NetRole.Boardwalk;
                            elevated = cfg.BoardwalkUseTimberPier;
                            plan.BoardwalkSegments++;
                            break;
                    }
                    if (isTransition) plan.TransitionSegments++;
                }

                Vec2 tan0 = i > 0 ? (v1.Pos - spine[i - 1].Pos).Normalized() : (v1.Pos - v0.Pos).Normalized();
                Vec2 tan1 = i + 2 < n ? (spine[i + 2].Pos - v0.Pos).Normalized() : (v1.Pos - v0.Pos).Normalized();
                Vec2 segDir = (v1.Pos - v0.Pos).Normalized();
                if (Vec2.Dot(tan0, segDir) < 0.65f) tan0 = segDir;
                if (Vec2.Dot(tan1, segDir) < 0.65f) tan1 = segDir;

                float handle = len / 3f;
                Vec3 pA = new Vec3(v0.Pos, v0.TargetY);
                Vec3 pD = new Vec3(v1.Pos, v1.TargetY);
                Vec3 pB = new Vec3(v0.Pos + tan0 * handle, v0.TargetY + (v1.TargetY - v0.TargetY) / 3f);
                Vec3 pC = new Vec3(v1.Pos - tan1 * handle, v0.TargetY + (v1.TargetY - v0.TargetY) * 2f / 3f);

                float groundA = sampler.TerrainHeight(v0.Pos);
                float groundB = sampler.TerrainHeight(v1.Pos);
                float elevA = elevated ? Math.Max(0.8f, v0.TargetY - groundA) : Math.Max(0f, v0.TargetY - groundA);
                float elevB = elevated ? Math.Max(0.8f, v1.TargetY - groundB) : Math.Max(0f, v1.TargetY - groundB);

                plan.Nets.Add(new PlannedNet
                {
                    A = pA, B = pB, C = pC, D = pD,
                    Role = role,
                    Mode = segMode,
                    Elevated = elevated,
                    ElevationA = elevA,
                    ElevationB = elevB,
                    ChainId = chain.ChainId,
                });
            }
        }

        /// <summary>
        /// Emits:
        /// 1. Clean terrace/plaza pocket fills in the recessed gaps behind shorter buildings (when StraightenBlocks runs).
        /// 2. Atlantic City sandy beach strips SEAWARD of the boardwalk (Buildings -> Boardwalk -> Beach -> Ocean!),
        ///    skipping roads and existing Placemaker beach areas so nothing overlaps.
        /// </summary>
        private static void EmitPocketAndAtlanticCityBeachSurfaces(
            WaterfrontChain chain,
            SpatialGrid2D<ExistingNetSegment> netGrid,
            IReadOnlyList<ExistingBeachArea> existingBeaches,
            WaterfrontPlan plan,
            WaterfrontConfig cfg)
        {
            var spine = chain.Spine;
            int n = spine.Count;
            var nearNets = new List<ExistingNetSegment>(16);

            for (int i = 0; i < n - 1; i++)
            {
                var v0 = spine[i];
                var v1 = spine[i + 1];
                float len = Vec2.Distance(v0.Pos, v1.Pos);
                if (len < 3f) continue;
                if (v0.IsGapBridge && v1.IsGapBridge) continue;

                Vec2 mid = (v0.Pos + v1.Pos) * 0.5f;
                netGrid.QueryRadius(mid, len * 0.5f + 22f, nearNets);

                // A. Landward terrace pocket fill behind straightened boardwalk/quay where shorter lots recessed
                float pocket = Math.Max(v0.PocketDepth, v1.PocketDepth);
                if (pocket > 1.2f || (v0.Mode == WaterfrontMode.Boardwalk && cfg.BoardwalkUseTimberPier))
                {
                    float landReach = Math.Min(16f, Math.Max(3.2f, pocket + 3.2f));
                    Vec2 l0 = v0.Pos - v0.Seaward * landReach;
                    Vec2 l1 = v1.Pos - v1.Seaward * landReach;
                    Vec2 s1 = v1.Pos - v1.Seaward * 1.2f;
                    Vec2 s0 = v0.Pos - v0.Seaward * 1.2f;

                    if (!OverlapsAnyRoad(l0, l1, (l0 + l1 + s0 + s1) * 0.25f, nearNets))
                    {
                        var ring = Geom2D.EnsureCcw(new[] { l0, l1, s1, s0 });
                        if (Math.Abs(Geom2D.SignedArea(ring)) >= 6f)
                        {
                            SurfaceRole pocketRole = v0.Mode == WaterfrontMode.Industrial
                                ? SurfaceRole.IndustrialConcrete
                                : SurfaceRole.BoardwalkDeck;
                            plan.Surfaces.Add(new PlannedSurface { Ring = ring, Role = pocketRole, ChainId = chain.ChainId });
                        }
                    }
                }

                // B. Atlantic City sandy beach SEAWARD of the boardwalk (Buildings -> Boardwalk -> Sand Beach -> Ocean!)
                bool wantBeachSeaward = (v0.Mode == WaterfrontMode.Beach)
                    || (v0.Mode == WaterfrontMode.Boardwalk && cfg.AtlanticCityBeach);
                if (!wantBeachSeaward) continue;
                if (v0.OpenWaterDist < 12f) continue;

                // Don't paint duplicate sand on top of an existing Placemaker beach
                Vec2 beachCheck = mid + v0.Seaward * 8f;
                if (InsideAnyBeach(beachCheck, existingBeaches)) continue;

                float startSea = 2.5f; // starts just under outer boardwalk edge -> never creeps inland onto streets!
                float endSea = Math.Min(16f, Math.Max(7f, v0.OpenWaterDist * 0.45f));

                Vec2 bL0 = v0.Pos + v0.Seaward * startSea;
                Vec2 bL1 = v1.Pos + v1.Seaward * startSea;
                Vec2 bS1 = v1.Pos + v1.Seaward * endSea;
                Vec2 bS0 = v0.Pos + v0.Seaward * endSea;

                if (OverlapsAnyRoad(bL0, bL1, (bL0 + bL1 + bS0 + bS1) * 0.25f, nearNets))
                    continue;

                var beachRing = Geom2D.EnsureCcw(new[] { bL0, bL1, bS1, bS0 });
                if (Math.Abs(Geom2D.SignedArea(beachRing)) >= 8f)
                    plan.Surfaces.Add(new PlannedSurface { Ring = beachRing, Role = SurfaceRole.Sand, ChainId = chain.ChainId });
            }
        }

        private static bool OverlapsAnyRoad(Vec2 p0, Vec2 p1, Vec2 center, List<ExistingNetSegment> nearNets)
        {
            for (int i = 0; i < nearNets.Count; i++)
            {
                var net = nearNets[i];
                if (!net.IsRoad || net.IsGeneratedByUs) continue;
                float margin = net.Width * 0.5f + 1.8f;
                if (Geom2D.PointToSegmentDist(p0, net.Start.XZ, net.End.XZ, out _, out _) < margin) return true;
                if (Geom2D.PointToSegmentDist(p1, net.Start.XZ, net.End.XZ, out _, out _) < margin) return true;
                if (Geom2D.PointToSegmentDist(center, net.Start.XZ, net.End.XZ, out _, out _) < margin) return true;
            }
            return false;
        }

        private static bool InsideAnyBeach(Vec2 p, IReadOnlyList<ExistingBeachArea> beaches)
        {
            if (beaches == null) return false;
            for (int i = 0; i < beaches.Count; i++)
            {
                var b = beaches[i];
                if (Vec2.Distance(p, b.Center) <= b.Radius + 2f)
                    return true;
            }
            return false;
        }

        /// <summary>
        /// Opt-in seaward-only beach slope grading: starts +4m SEAWARD of the boardwalk centerline
        /// so it builds a smooth sandy beach outside the boardwalk without EVER disturbing building foundations!
        /// </summary>
        private static void EmitSeawardBeachGrades(
            WaterfrontChain chain,
            IReadOnlyList<ExistingBeachArea> existingBeaches,
            WaterfrontPlan plan,
            WaterfrontConfig cfg)
        {
            var spine = chain.Spine;
            for (int i = 0; i < spine.Count - 1; i++)
            {
                var v0 = spine[i];
                var v1 = spine[i + 1];
                if (!v0.BeachCanGrade && !v1.BeachCanGrade) continue;

                float len = Vec2.Distance(v0.Pos, v1.Pos);
                if (len < 3f) continue;

                Vec2 mid = (v0.Pos + v1.Pos) * 0.5f;
                Vec2 along = (v1.Pos - v0.Pos).Normalized();
                Vec2 sea = (v0.Seaward + v1.Seaward).Normalized();
                if (sea.LengthSq < 0.01f) sea = along.RightPerp().Normalized();

                if (InsideAnyBeach(mid + sea * 8f, existingBeaches)) continue;

                float open = Math.Min(v0.OpenWaterDist, v1.OpenWaterDist);
                float slopeW = Math.Min(cfg.BeachSlopeWidth, Math.Max(8f, open * 0.45f));

                // Start strictly seaward of the boardwalk outer edge (+4m) so building lots stay 100% untouched!
                float beachTopY = Math.Min((v0.TargetY + v1.TargetY) * 0.5f - 0.8f, (v0.WaterY + v1.WaterY) * 0.5f + 2.2f);
                plan.BeachGrades.Add(new PlannedBeachGrade
                {
                    LandEdgeMid = mid + sea * 4.0f,
                    AlongDir = along,
                    SeawardDir = sea,
                    Length = len + 3.0f,
                    SlopeWidth = slopeW,
                    LandY = beachTopY,
                    WaterY = (v0.WaterY + v1.WaterY) * 0.5f,
                    ChainId = chain.ChainId,
                });
            }
        }

        /// <summary>
        /// Curls the start/end of a boardwalk smoothly down onto an adjacent Placemaker beach (like Images 1 & 3!)
        /// instead of stopping abruptly as a cliff stub.
        /// </summary>
        private static void EmitPlacemakerBeachCurls(
            WaterfrontChain chain,
            SpatialGrid2D<BuildingLot> buildingGrid,
            SpatialGrid2D<ExistingNetSegment> netGrid,
            IReadOnlyList<ExistingBeachArea> beaches,
            WaterfrontPlan plan,
            IWorldSampler sampler,
            WaterfrontConfig cfg)
        {
            var spine = chain.Spine;
            if (spine.Count < 2) return;

            var localBldgs = new List<BuildingLot>(16);
            var nearNets = new List<ExistingNetSegment>(16);
            float maxSearch = Math.Max(16f, cfg.BeachCurlSearchDist);

            // Check both ends of the chain: index 0 (backward tangent) and index n-1 (forward tangent)
            int[] endIndices = { 0, spine.Count - 1 };
            for (int eIdx = 0; eIdx < 2; eIdx++)
            {
                int idx = endIndices[eIdx];
                var endV = spine[idx];
                if (endV.Mode == WaterfrontMode.Industrial) continue;

                Vec2 outwardAlong = idx == 0
                    ? (spine[0].Pos - spine[1].Pos).Normalized()
                    : (spine[spine.Count - 1].Pos - spine[spine.Count - 2].Pos).Normalized();

                // Find nearest dry point on any Placemaker beach in the forward direction of this chain end
                Vec2 bestTarget = default;
                float bestDist = maxSearch;
                bool found = false;

                for (int b = 0; b < beaches.Count; b++)
                {
                    var beach = beaches[b];
                    if (Vec2.Distance(endV.Pos, beach.Center) > maxSearch + beach.Radius) continue;

                    // Sample ring vertices + slightly inset dry points toward beach center
                    if (beach.Ring == null || beach.Ring.Length < 3) continue;
                    for (int k = 0; k < beach.Ring.Length; k++)
                    {
                        Vec2 pt = Vec2.Lerp(beach.Ring[k], beach.Center, 0.25f);
                        float d = Vec2.Distance(endV.Pos, pt);
                        if (d < 5f || d >= bestDist) continue;

                        // Must extend generally forward from the chain end (not curling backward behind itself!)
                        Vec2 dir = (pt - endV.Pos).Normalized();
                        if (Vec2.Dot(dir, outwardAlong) < 0.1f) continue;

                        // Target point must be on dry sand (not deep water)
                        if (sampler.WaterDepth(pt) > 0.25f) continue;

                        // Must not slice through any building or road
                        Vec2 mid = (endV.Pos + pt) * 0.5f;
                        buildingGrid.QueryRadius(mid, d * 0.5f + 16f, localBldgs);
                        if (CrossesAnyBuilding(endV.Pos, pt, localBldgs)) continue;

                        netGrid.QueryRadius(mid, d * 0.5f + 12f, nearNets);
                        if (OverlapsAnyRoad(pt, mid, mid, nearNets)) continue;

                        bestDist = d;
                        bestTarget = pt;
                        found = true;
                    }
                }

                if (!found) continue;

                float targetY = Math.Max(endV.WaterY + 0.6f, sampler.TerrainHeight(bestTarget));
                // Smooth curving Bezier curling from boardwalk tangent gently onto the Placemaker beach
                float handle = bestDist * 0.38f;
                Vec2 toBeach = (bestTarget - endV.Pos).Normalized();
                Vec3 pA = new Vec3(endV.Pos, endV.TargetY);
                Vec3 pD = new Vec3(bestTarget, targetY);
                Vec3 pB = new Vec3(endV.Pos + outwardAlong * handle, endV.TargetY + (targetY - endV.TargetY) * 0.3f);
                Vec3 pC = new Vec3(bestTarget - toBeach * handle, endV.TargetY + (targetY - endV.TargetY) * 0.75f);

                plan.Nets.Add(new PlannedNet
                {
                    A = pA, B = pB, C = pC, D = pD,
                    Role = NetRole.TransitionRamp,
                    Mode = WaterfrontMode.Beach,
                    Elevated = false,
                    ElevationA = Math.Max(0f, endV.TargetY - sampler.TerrainHeight(endV.Pos)),
                    ElevationB = 0f,
                    ChainId = chain.ChainId,
                });

                plan.BeachCurls++;
            }
        }

        private static void EmitIndustrialFingerPiers(
            WaterfrontChain chain,
            SpatialGrid2D<ExistingNetSegment> netGrid,
            WaterfrontPlan plan,
            IWorldSampler sampler,
            WaterfrontConfig cfg)
        {
            var spine = chain.Spine;
            float distSincePier = cfg.PierSpacing * 0.55f;
            float spacing = Math.Max(36f, cfg.PierSpacing);
            var nearNets = new List<ExistingNetSegment>(16);

            for (int i = 1; i < spine.Count - 1; i++)
            {
                distSincePier += Vec2.Distance(spine[i - 1].Pos, spine[i].Pos);
                var v = spine[i];
                if (v.Mode != WaterfrontMode.Industrial || v.Transition != TransitionKind.None)
                    continue;
                if (distSincePier < spacing)
                    continue;

                float openWater = ShorelineDetector.MeasureOpenWater(v.Pos, v.Seaward, sampler, cfg, cfg.MaxPierLength + 20f);
                if (openWater < 28f)
                    continue;

                float pierLen = Math.Min(cfg.MaxPierLength, openWater - 12f);
                if (pierLen < 16f) continue;

                Vec2 endXZ = v.Pos + v.Seaward * pierLen;
                netGrid.QueryRadius((v.Pos + endXZ) * 0.5f, pierLen + 28f, nearNets);
                if (CrossesOrNearWaterway(v.Pos, endXZ, nearNets, 24f))
                    continue;

                float deckY = Math.Min(v.TargetY, v.WaterY + 4.5f);
                Vec3 pA = new Vec3(v.Pos, v.TargetY);
                Vec3 pD = new Vec3(endXZ, deckY);
                Vec3 pB = Vec3.Lerp(pA, pD, 1f / 3f);
                Vec3 pC = Vec3.Lerp(pA, pD, 2f / 3f);

                float groundA = sampler.TerrainHeight(v.Pos);
                float groundD = sampler.TerrainHeight(endXZ);

                plan.Nets.Add(new PlannedNet
                {
                    A = pA, B = pB, C = pC, D = pD,
                    Role = NetRole.IndustrialPier,
                    Mode = WaterfrontMode.Industrial,
                    Elevated = true,
                    ElevationA = Math.Max(1.0f, v.TargetY - groundA),
                    ElevationB = Math.Max(1.5f, deckY - groundD),
                    ChainId = chain.ChainId,
                });

                if (cfg.EnableProps)
                {
                    Vec2 side = v.Seaward.LeftPerp().Normalized();
                    float yaw = Geom2D.YawFromDir(v.Seaward);
                    for (float d = 7f; d <= pierLen - 2f; d += 9f)
                    {
                        Vec2 c = v.Pos + v.Seaward * d;
                        float py = v.TargetY + (deckY - v.TargetY) * (d / pierLen);
                        plan.Props.Add(new PlannedProp { Position = new Vec3(c + side * 2.4f, py), Yaw = yaw, Role = PropRole.IndustrialBollard, Seed = Geom2D.DeterministicSeed(c.X, c.Z, 1), ChainId = chain.ChainId });
                        plan.Props.Add(new PlannedProp { Position = new Vec3(c - side * 2.4f, py), Yaw = yaw, Role = PropRole.IndustrialBollard, Seed = Geom2D.DeterministicSeed(c.X, c.Z, 2), ChainId = chain.ChainId });
                    }
                }

                plan.FingerPiers++;
                distSincePier = 0f;
            }
        }

        private static bool CrossesOrNearWaterway(Vec2 a, Vec2 b, List<ExistingNetSegment> nearNets, float clearance)
        {
            Vec2 mid = (a + b) * 0.5f;
            for (int i = 0; i < nearNets.Count; i++)
            {
                var net = nearNets[i];
                if (!net.IsWaterway) continue;
                float margin = Math.Max(clearance, net.Width * 0.5f + 12f);
                if (Geom2D.SegmentsIntersect(a, b, net.Start.XZ, net.End.XZ)) return true;
                if (Geom2D.PointToSegmentDist(b, net.Start.XZ, net.End.XZ, out _, out _) < margin) return true;
                if (Geom2D.PointToSegmentDist(mid, net.Start.XZ, net.End.XZ, out _, out _) < margin) return true;
            }
            return false;
        }

        private static void EmitStreetAccessSpurs(
            WaterfrontChain chain,
            SpatialGrid2D<BuildingLot> buildingGrid,
            SpatialGrid2D<ExistingNetSegment> netGrid,
            WaterfrontPlan plan,
            IWorldSampler sampler,
            WaterfrontConfig cfg)
        {
            var spine = chain.Spine;
            var spurPositions = new List<Vec2>();
            var nearNets = new List<ExistingNetSegment>(24);
            var localBldgs = new List<BuildingLot>(24);

            for (int i = 0; i < spine.Count; i++)
            {
                var v = spine[i];
                bool candidate = v.IsEndOfChain || v.IsGapBridge || (v.Transition != TransitionKind.None && i % 2 == 0);
                if (!candidate) continue;

                bool tooClose = false;
                for (int k = 0; k < spurPositions.Count; k++)
                    if (Vec2.Distance(spurPositions[k], v.Pos) < 32f) { tooClose = true; break; }
                if (tooClose) continue;

                netGrid.QueryRadius(v.Pos, 46f, nearNets);
                buildingGrid.QueryRadius(v.Pos, 48f, localBldgs);

                ExistingNetSegment bestRoad = null;
                Vec2 bestPoint = default;
                float bestDist = 44f;

                for (int r = 0; r < nearNets.Count; r++)
                {
                    var net = nearNets[r];
                    if (!net.IsRoad || net.IsGeneratedByUs) continue;
                    float dist = Geom2D.PointToSegmentDist(v.Pos, net.Start.XZ, net.End.XZ, out _, out Vec2 closest);
                    if (dist < 6f || dist >= bestDist) continue;

                    Vec2 toRoad = (closest - v.Pos).Normalized();
                    if (Vec2.Dot(toRoad, v.Seaward) > 0.25f) continue;

                    if (CrossesAnyBuilding(v.Pos, closest, localBldgs)) continue;

                    Vec2 mid = Vec2.Lerp(v.Pos, closest, 0.5f);
                    if (sampler.WaterDepth(mid) > 0.5f) continue;

                    bestDist = dist;
                    bestRoad = net;
                    bestPoint = closest;
                }

                if (bestRoad == null) continue;

                Vec2 dirToRoad = (bestPoint - v.Pos).Normalized();
                float pullback = Math.Max(1.5f, bestRoad.Width * 0.5f - 0.5f);
                Vec2 sidewalkPoint = bestDist > pullback + 4f ? (bestPoint - dirToRoad * pullback) : bestPoint;

                float roadY = sampler.TerrainHeight(sidewalkPoint);
                Vec3 pA = new Vec3(v.Pos, v.TargetY);
                Vec3 pD = new Vec3(sidewalkPoint, roadY);
                Vec3 pB = Vec3.Lerp(pA, pD, 1f / 3f);
                Vec3 pC = Vec3.Lerp(pA, pD, 2f / 3f);

                plan.Nets.Add(new PlannedNet
                {
                    A = pA, B = pB, C = pC, D = pD,
                    Role = NetRole.AccessSpur,
                    Mode = v.Mode,
                    Elevated = false,
                    ElevationA = Math.Max(0f, v.TargetY - sampler.TerrainHeight(v.Pos)),
                    ElevationB = 0f,
                    ChainId = chain.ChainId,
                    SnapEndNetId = 0,
                    SnapEndCurveT = 0f,
                });

                spurPositions.Add(v.Pos);
                plan.AccessSpurs++;
            }
        }

        private static bool CrossesAnyBuilding(Vec2 a, Vec2 b, List<BuildingLot> buildings)
        {
            for (int i = 0; i < buildings.Count; i++)
            {
                var lot = buildings[i];
                if (lot.Corners == null) continue;
                if (Geom2D.SegmentIntersectsQuad(a, b, lot.Corners, 0.35f))
                    return true;
            }
            return false;
        }

        /// <summary>
        /// Atlantic City boardwalk oomph!
        /// - Boardwalk & Home-Boardwalk: park lamps every ~18m, seaward-facing benches every ~20m,
        ///   periodic kiosks / gazebos on recessed terrace pockets, life-buoy stations,
        ///   PLUS umbrellas & deck chairs out on the sandy beach seaward of the boardwalk!
        /// - Industrial: mooring bollards along quay & piers.
        /// - Transitions: coastal rock groins / bollards / lamps.
        /// </summary>
        private static void EmitProps(
            WaterfrontChain chain,
            IReadOnlyList<ExistingBeachArea> existingBeaches,
            WaterfrontPlan plan,
            IWorldSampler sampler,
            WaterfrontConfig cfg)
        {
            var spine = chain.Spine;
            float accum = 0f;
            float nextLamp = 7f;
            float nextBench = 12f;
            float nextFeature = 26f; // kiosk or gazebo on boardwalk stretches!
            float nextBollard = 6f;
            float nextBeachCluster = 10f;

            for (int i = 0; i < spine.Count - 1; i++)
            {
                var v0 = spine[i];
                var v1 = spine[i + 1];
                float segLen = Vec2.Distance(v0.Pos, v1.Pos);
                if (segLen < 2f) continue;

                Vec2 segDir = (v1.Pos - v0.Pos).Normalized();
                Vec2 sea = (v0.Seaward + v1.Seaward).Normalized();
                if (sea.LengthSq < 0.01f) sea = segDir.RightPerp().Normalized();
                float faceSeaYaw = Geom2D.YawFromDir(sea);
                float alongYaw = Geom2D.YawFromDir(segDir);

                var boundaryKind = ModeClassifier.TransitionBetween(v0.Mode, v1.Mode);
                if (boundaryKind == TransitionKind.BoardwalkToBeach || boundaryKind == TransitionKind.BeachToIndustrial)
                {
                    Vec2 mid = (v0.Pos + v1.Pos) * 0.5f;
                    int rockCount = boundaryKind == TransitionKind.BeachToIndustrial ? 5 : 4;
                    for (int r = 0; r < rockCount; r++)
                    {
                        float d = 3.0f + r * 2.1f;
                        int seed = Geom2D.DeterministicSeed(mid.X, mid.Z, 100 + r);
                        float jitter = (Geom2D.Hash01(seed) - 0.5f) * 1.4f;
                        Vec2 rp = mid + sea * d + segDir * jitter;
                        float ry = Math.Max(v0.WaterY - 0.3f, sampler.TerrainHeight(rp));
                        var role = (boundaryKind == TransitionKind.BeachToIndustrial && r % 2 == 1)
                            ? PropRole.TransitionRubble
                            : PropRole.TransitionRock;
                        plan.Props.Add(new PlannedProp { Position = new Vec3(rp, ry), Yaw = Geom2D.Hash01(seed + 7) * 6.283f, Role = role, Seed = seed, ChainId = chain.ChainId });
                    }
                }
                else if (boundaryKind == TransitionKind.BoardwalkToIndustrial)
                {
                    Vec2 mid = (v0.Pos + v1.Pos) * 0.5f;
                    float my = (v0.TargetY + v1.TargetY) * 0.5f;
                    plan.Props.Add(new PlannedProp { Position = new Vec3(mid + sea * 2.6f - segDir * 2f, my), Yaw = faceSeaYaw, Role = PropRole.BoardwalkBollard, Seed = Geom2D.DeterministicSeed(mid.X, mid.Z, 11), ChainId = chain.ChainId });
                    plan.Props.Add(new PlannedProp { Position = new Vec3(mid + sea * 2.6f + segDir * 2f, my), Yaw = faceSeaYaw, Role = PropRole.BoardwalkBollard, Seed = Geom2D.DeterministicSeed(mid.X, mid.Z, 12), ChainId = chain.ChainId });
                    plan.Props.Add(new PlannedProp { Position = new Vec3(mid - sea * 2.4f, my), Yaw = faceSeaYaw, Role = PropRole.BoardwalkLamp, Seed = Geom2D.DeterministicSeed(mid.X, mid.Z, 13), ChainId = chain.ChainId });
                }

                float segStart = accum;
                float segEnd = accum + segLen;
                bool isBoardwalkFeel = v0.Mode == WaterfrontMode.Boardwalk || (v0.Mode == WaterfrontMode.Beach && cfg.HomesUseBoardwalk);

                if (isBoardwalkFeel)
                {
                    // Vintage boardwalk lamps along seaward edge
                    while (nextLamp < segEnd)
                    {
                        float t = (nextLamp - segStart) / segLen;
                        Vec2 p = Vec2.Lerp(v0.Pos, v1.Pos, t) + sea * 2.8f;
                        float y = v0.TargetY + (v1.TargetY - v0.TargetY) * t;
                        plan.Props.Add(new PlannedProp { Position = new Vec3(p, y), Yaw = faceSeaYaw, Role = PropRole.BoardwalkLamp, Seed = Geom2D.DeterministicSeed(p.X, p.Z, 21), ChainId = chain.ChainId });
                        nextLamp += 18f;
                    }
                    // Seaward-facing boardwalk benches
                    while (nextBench < segEnd)
                    {
                        float t = (nextBench - segStart) / segLen;
                        Vec2 p = Vec2.Lerp(v0.Pos, v1.Pos, t) - sea * 2.4f;
                        float y = v0.TargetY + (v1.TargetY - v0.TargetY) * t;
                        plan.Props.Add(new PlannedProp { Position = new Vec3(p, y), Yaw = faceSeaYaw, Role = PropRole.BoardwalkBench, Seed = Geom2D.DeterministicSeed(p.X, p.Z, 22), ChainId = chain.ChainId });
                        nextBench += 20f;
                    }
                    // Boardwalk oomph: kiosks / gazebos / life-buoy stations every ~52m (placed neatly on recessed pocket or wide deck edge!)
                    while (nextFeature < segEnd)
                    {
                        float t = (nextFeature - segStart) / segLen;
                        Vec2 basePos = Vec2.Lerp(v0.Pos, v1.Pos, t);
                        float y = v0.TargetY + (v1.TargetY - v0.TargetY) * t;
                        int seed = Geom2D.DeterministicSeed(basePos.X, basePos.Z, 55);
                        float pocket = Math.Max(v0.PocketDepth, v1.PocketDepth);
                        if (v0.Mode == WaterfrontMode.Boardwalk && pocket >= 3.0f)
                        {
                            // Put a boardwalk kiosk or gazebo right in the paved recessed terrace!
                            Vec2 kp = basePos - sea * Math.Min(pocket * 0.55f + 2.2f, 6.5f);
                            var fRole = (seed % 3 == 0) ? PropRole.BoardwalkGazebo : PropRole.BoardwalkKiosk;
                            plan.Props.Add(new PlannedProp { Position = new Vec3(kp, y), Yaw = faceSeaYaw, Role = fRole, Seed = seed, ChainId = chain.ChainId });
                        }
                        else
                        {
                            // Nautical life-buoy station on seaward rail
                            Vec2 bp = basePos + sea * 3.1f;
                            plan.Props.Add(new PlannedProp { Position = new Vec3(bp, y), Yaw = faceSeaYaw, Role = PropRole.BoardwalkLifeBuoy, Seed = seed, ChainId = chain.ChainId });
                        }
                        nextFeature += 52f;
                    }
                }
                else if (v0.Mode == WaterfrontMode.Industrial)
                {
                    while (nextBollard < segEnd)
                    {
                        float t = (nextBollard - segStart) / segLen;
                        Vec2 p = Vec2.Lerp(v0.Pos, v1.Pos, t) + sea * 2.4f;
                        float y = v0.TargetY + (v1.TargetY - v0.TargetY) * t;
                        plan.Props.Add(new PlannedProp { Position = new Vec3(p, y), Yaw = alongYaw, Role = PropRole.IndustrialBollard, Seed = Geom2D.DeterministicSeed(p.X, p.Z, 31), ChainId = chain.ChainId });
                        nextBollard += 14f;
                    }
                }

                // Atlantic City beach umbrellas & chairs SEAWARD of the boardwalk on dry/shallow sand!
                bool hasBeachSeaward = (v0.Mode == WaterfrontMode.Beach) || (v0.Mode == WaterfrontMode.Boardwalk && cfg.AtlanticCityBeach);
                if (hasBeachSeaward && v0.OpenWaterDist >= 14f)
                {
                    while (nextBeachCluster < segEnd)
                    {
                        float t = (nextBeachCluster - segStart) / segLen;
                        Vec2 baseP = Vec2.Lerp(v0.Pos, v1.Pos, t) + sea * 7.5f;
                        if (!InsideAnyBeach(baseP, existingBeaches) && sampler.WaterDepth(baseP) < 0.15f)
                        {
                            int seed = Geom2D.DeterministicSeed(baseP.X, baseP.Z, 41);
                            float groundY = Math.Max(v0.WaterY + 0.35f, sampler.TerrainHeight(baseP));
                            plan.Props.Add(new PlannedProp { Position = new Vec3(baseP, groundY), Yaw = faceSeaYaw, Role = PropRole.BeachParasol, Seed = seed, ChainId = chain.ChainId });
                            plan.Props.Add(new PlannedProp { Position = new Vec3(baseP + segDir * 1.4f, groundY), Yaw = faceSeaYaw, Role = PropRole.BeachChair, Seed = seed + 1, ChainId = chain.ChainId });
                            plan.Props.Add(new PlannedProp { Position = new Vec3(baseP - segDir * 1.4f, groundY), Yaw = faceSeaYaw, Role = PropRole.BeachChair, Seed = seed + 2, ChainId = chain.ChainId });
                        }
                        nextBeachCluster += 18f;
                    }
                }

                accum = segEnd;
                if (nextLamp < accum) nextLamp = accum + 7f;
                if (nextBench < accum) nextBench = accum + 12f;
                if (nextFeature < accum) nextFeature = accum + 26f;
                if (nextBollard < accum) nextBollard = accum + 6f;
                if (nextBeachCluster < accum) nextBeachCluster = accum + 10f;
            }
        }
    }
}
