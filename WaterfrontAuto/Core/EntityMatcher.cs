using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace WaterfrontAuto.Core
{
    public enum TrackedKind
    {
        Edge = 0,   // 'E'
        Area = 1,   // 'A'
        Object = 2, // 'O'
    }

    public struct PendingItem
    {
        public TrackedKind Kind;
        public string PrefabName;
        public Vec2 Pos;
    }

    public struct LiveCandidate
    {
        public long EntityId;
        public TrackedKind Kind;
        public string PrefabName;
        public Vec2 Pos;
        public bool HasOwner;
        public bool IsTemp;
    }

    public struct ManifestRow
    {
        public TrackedKind Kind;
        public string PrefabName;
        public float X;
        public float Z;
    }

    /// <summary>
    /// Pure-C# ownership matching, manifest codec, and O(1) spatial-hash dedupe (offline-testable).
    /// Implements Claude's v4 reliability spec: exact prefab match, consume-once, tight tolerances,
    /// zero claiming of owned/Temp entities, and zero duplicate stacking across save/reload.
    /// </summary>
    public static class EntityMatcher
    {
        public const float EdgeCaptureTolerance = 1.0f;
        public const float AreaCaptureTolerance = 1.0f;
        public const float ObjectCaptureTolerance = 0.5f;
        public const float ManifestAdoptTolerance = 0.5f;
        public const float AreaDedupeTolerance = 0.5f;
        public const float ObjectDedupeTolerance = 1.0f;

        private const float MatchCellSize = 4f;

        public static float ToleranceForCapture(TrackedKind kind)
        {
            switch (kind)
            {
                case TrackedKind.Edge: return EdgeCaptureTolerance;
                case TrackedKind.Area: return AreaCaptureTolerance;
                default: return ObjectCaptureTolerance;
            }
        }

        /// <summary>
        /// Matches newly Created live entities against pending emitted definitions.
        /// Rules: exact PrefabName equality, no Owner, no Temp, tight per-kind tolerance,
        /// nearest candidate wins, and each pending item is consumed at most once.
        /// </summary>
        public static List<long> MatchCreated(
            List<PendingItem> pending,
            IReadOnlyList<LiveCandidate> candidates,
            out int unmatchedPending)
        {
            return MatchCore(pending, candidates, -1f, out unmatchedPending);
        }

        /// <summary>
        /// Matches manifest rows against live entities on save load (exact prefab, within 0.5m, no Owner/Temp, consume-once).
        /// </summary>
        public static List<long> MatchManifest(
            IReadOnlyList<ManifestRow> rows,
            IReadOnlyList<LiveCandidate> live,
            out int droppedRows)
        {
            var pending = new List<PendingItem>(rows?.Count ?? 0);
            if (rows != null)
            {
                for (int i = 0; i < rows.Count; i++)
                {
                    pending.Add(new PendingItem
                    {
                        Kind = rows[i].Kind,
                        PrefabName = rows[i].PrefabName,
                        Pos = new Vec2(rows[i].X, rows[i].Z),
                    });
                }
            }
            return MatchWithTolerance(pending, live, ManifestAdoptTolerance, out droppedRows);
        }

        /// <summary>Same rules as <see cref="MatchCreated"/> but with one fixed tolerance for every kind.</summary>
        public static List<long> MatchWithTolerance(
            List<PendingItem> pending,
            IReadOnlyList<LiveCandidate> candidates,
            float tolerance,
            out int unmatched)
        {
            return MatchCore(pending, candidates, Math.Max(0f, tolerance), out unmatched);
        }

        /// <summary>
        /// Shared matcher. <paramref name="fixedTolerance"/> &lt; 0 means "use the per-kind capture tolerance".
        /// Matched pending items are removed from <paramref name="pending"/> (consume-once).
        /// The neighbourhood search widens automatically when a tolerance exceeds one 4 m cell.
        /// </summary>
        private static List<long> MatchCore(
            List<PendingItem> pending,
            IReadOnlyList<LiveCandidate> candidates,
            float fixedTolerance,
            out int unmatched)
        {
            var claimed = new List<long>();
            unmatched = 0;
            if (pending == null || pending.Count == 0) return claimed;
            if (candidates == null || candidates.Count == 0)
            {
                unmatched = pending.Count;
                return claimed;
            }

            var grid = new Dictionary<long, List<int>>();
            for (int i = 0; i < candidates.Count; i++)
            {
                var c = candidates[i];
                if (c.HasOwner || c.IsTemp || string.IsNullOrEmpty(c.PrefabName)) continue;
                long key = CellKey(c.Pos, MatchCellSize);
                if (!grid.TryGetValue(key, out var list))
                    grid[key] = list = new List<int>(4);
                list.Add(i);
            }

            var used = new bool[candidates.Count];

            for (int pIdx = pending.Count - 1; pIdx >= 0; pIdx--)
            {
                var p = pending[pIdx];
                if (string.IsNullOrEmpty(p.PrefabName)) { unmatched++; continue; }

                float tol = fixedTolerance >= 0f ? fixedTolerance : ToleranceForCapture(p.Kind);
                float bestDistSq = tol * tol;
                int bestIdx = -1;
                int reach = Math.Max(1, (int)Math.Ceiling(tol / MatchCellSize));
                int cx = (int)Math.Floor(p.Pos.X / MatchCellSize);
                int cz = (int)Math.Floor(p.Pos.Z / MatchCellSize);

                for (int dx = -reach; dx <= reach; dx++)
                {
                    for (int dz = -reach; dz <= reach; dz++)
                    {
                        if (!grid.TryGetValue(PackCell(cx + dx, cz + dz), out var bucket)) continue;
                        for (int b = 0; b < bucket.Count; b++)
                        {
                            int ci = bucket[b];
                            if (used[ci]) continue;
                            var c = candidates[ci];
                            if (c.Kind != p.Kind) continue;
                            if (!string.Equals(c.PrefabName, p.PrefabName, StringComparison.Ordinal)) continue;
                            float dSq = Vec2.DistanceSq(c.Pos, p.Pos);
                            if (dSq <= bestDistSq)
                            {
                                bestDistSq = dSq;
                                bestIdx = ci;
                            }
                        }
                    }
                }

                if (bestIdx >= 0)
                {
                    used[bestIdx] = true;
                    claimed.Add(candidates[bestIdx].EntityId);
                    pending.RemoveAt(pIdx); // consume once!
                }
                else
                {
                    unmatched++;
                }
            }

            return claimed;
        }

        public static string SerializeManifest(IReadOnlyList<ManifestRow> rows)
        {
            var sb = new StringBuilder();
            var inv = CultureInfo.InvariantCulture;
            if (rows != null)
            {
                for (int i = 0; i < rows.Count; i++)
                {
                    var r = rows[i];
                    if (string.IsNullOrEmpty(r.PrefabName)) continue;
                    char kc = r.Kind == TrackedKind.Edge ? 'E' : r.Kind == TrackedKind.Area ? 'A' : 'O';
                    float rx = (float)Math.Round(r.X * 10f) * 0.1f;
                    float rz = (float)Math.Round(r.Z * 10f) * 0.1f;
                    sb.Append(kc).Append('|')
                      .Append(r.PrefabName.Replace('|', '_')).Append('|')
                      .Append(rx.ToString("0.0", inv)).Append('|')
                      .Append(rz.ToString("0.0", inv)).Append('\n');
                }
            }
            return sb.ToString();
        }

        public static List<ManifestRow> ParseManifest(string text)
        {
            var rows = new List<ManifestRow>();
            if (string.IsNullOrEmpty(text)) return rows;
            var inv = CultureInfo.InvariantCulture;
            var lines = text.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries);
            for (int i = 0; i < lines.Length; i++)
            {
                var parts = lines[i].Split('|');
                if (parts.Length < 4 || parts[0].Length == 0) continue;
                TrackedKind kind;
                switch (parts[0][0])
                {
                    case 'E': kind = TrackedKind.Edge; break;
                    case 'A': kind = TrackedKind.Area; break;
                    case 'O': kind = TrackedKind.Object; break;
                    default: continue;
                }
                if (float.TryParse(parts[2], NumberStyles.Float, inv, out float x) &&
                    float.TryParse(parts[3], NumberStyles.Float, inv, out float z))
                {
                    rows.Add(new ManifestRow { Kind = kind, PrefabName = parts[1], X = x, Z = z });
                }
            }
            return rows;
        }

        public static long CellKey(Vec2 p, float cellSize) =>
            PackCell((int)Math.Floor(p.X / cellSize), (int)Math.Floor(p.Z / cellSize));

        public static long PackCell(int cx, int cz) =>
            ((long)cx << 32) | (uint)cz;
    }

    /// <summary>
    /// Fast O(1) spatial hash index for deduping planned Areas and Objects against live entities
    /// (fallback for pre-v4 saves with no manifest).
    /// </summary>
    public sealed class SpatialDedupeIndex
    {
        private const float CellSize = 4f;
        private readonly Dictionary<long, List<LiveCandidate>> m_Grid = new Dictionary<long, List<LiveCandidate>>();

        public void Add(LiveCandidate item)
        {
            if (item.IsTemp || string.IsNullOrEmpty(item.PrefabName)) return;
            long key = EntityMatcher.CellKey(item.Pos, CellSize);
            if (!m_Grid.TryGetValue(key, out var list))
                m_Grid[key] = list = new List<LiveCandidate>(4);
            list.Add(item);
        }

        public bool HasDuplicate(TrackedKind kind, string prefabName, Vec2 pos, float tolerance, out long existingEntityId)
        {
            existingEntityId = 0;
            return Scan(kind, prefabName, pos, tolerance, null, stopAtFirst: true, ref existingEntityId) > 0;
        }

        /// <summary>
        /// Finds EVERY live entity of the same kind + exact prefab within <paramref name="tolerance"/> of
        /// <paramref name="pos"/> (stacked duplicates from older saves included). <paramref name="results"/> is
        /// cleared first, then filled with the entity ids nearest-first; it may be null when only the count matters.
        /// </summary>
        public int FindAllWithin(TrackedKind kind, string prefabName, Vec2 pos, float tolerance, List<long> results)
        {
            results?.Clear();
            long unused = 0;
            return Scan(kind, prefabName, pos, tolerance, results, stopAtFirst: false, ref unused);
        }

        private int Scan(TrackedKind kind, string prefabName, Vec2 pos, float tolerance, List<long> results, bool stopAtFirst, ref long firstId)
        {
            if (string.IsNullOrEmpty(prefabName) || m_Grid.Count == 0) return 0;
            float tol = Math.Max(0f, tolerance);
            float tolSq = tol * tol;
            int reach = Math.Max(1, (int)Math.Ceiling(tol / CellSize));
            int cx = (int)Math.Floor(pos.X / CellSize);
            int cz = (int)Math.Floor(pos.Z / CellSize);
            int count = 0;
            List<KeyValuePair<float, long>> sortBuf = results != null ? new List<KeyValuePair<float, long>>(4) : null;

            for (int dx = -reach; dx <= reach; dx++)
            {
                for (int dz = -reach; dz <= reach; dz++)
                {
                    if (!m_Grid.TryGetValue(EntityMatcher.PackCell(cx + dx, cz + dz), out var bucket)) continue;
                    for (int i = 0; i < bucket.Count; i++)
                    {
                        var c = bucket[i];
                        if (c.Kind != kind) continue;
                        if (!string.Equals(c.PrefabName, prefabName, StringComparison.Ordinal)) continue;
                        float dSq = Vec2.DistanceSq(c.Pos, pos);
                        if (dSq > tolSq) continue;
                        if (count == 0) firstId = c.EntityId;
                        count++;
                        if (stopAtFirst) return count;
                        sortBuf?.Add(new KeyValuePair<float, long>(dSq, c.EntityId));
                    }
                }
            }

            if (sortBuf != null && sortBuf.Count > 0)
            {
                sortBuf.Sort((a, b) => a.Key != b.Key ? a.Key.CompareTo(b.Key) : a.Value.CompareTo(b.Value));
                for (int i = 0; i < sortBuf.Count; i++) results.Add(sortBuf[i].Value);
            }
            return count;
        }
    }

    /// <summary>Generic 2D spatial hash grid for fast O(1) neighborhood lookups (eliminates O(N^2) scans).</summary>
    public sealed class SpatialGrid2D<T>
    {
        /// <summary>Safety cap on cells per inserted item (a 32 m grid covers ~4 km per axis at this cap).</summary>
        private const int MaxCellsPerAxis = 128;
        private const int MaxCellsPerSegment = 1 << 16;

        private readonly float m_CellSize;
        private readonly Dictionary<long, List<T>> m_Cells = new Dictionary<long, List<T>>();
        private readonly HashSet<long> m_CellScratch = new HashSet<long>();
        private readonly HashSet<T> m_QuerySeen = new HashSet<T>();

        public SpatialGrid2D(float cellSize) { m_CellSize = cellSize > 1e-3f ? cellSize : 1f; }

        public float CellSize => m_CellSize;

        public void AddPoint(Vec2 p, T item)
        {
            AddToCell(EntityMatcher.CellKey(p, m_CellSize), item);
        }

        public void AddBounds(Vec2 min, Vec2 max, T item)
        {
            int x0 = (int)Math.Floor(min.X / m_CellSize);
            int x1 = (int)Math.Floor(max.X / m_CellSize);
            int z0 = (int)Math.Floor(min.Z / m_CellSize);
            int z1 = (int)Math.Floor(max.Z / m_CellSize);
            // Guard against garbage bounds only; real footprints are far below this.
            if (x1 - x0 > MaxCellsPerAxis) x1 = x0 + MaxCellsPerAxis;
            if (z1 - z0 > MaxCellsPerAxis) z1 = z0 + MaxCellsPerAxis;
            for (int x = x0; x <= x1; x++)
                for (int z = z0; z <= z1; z++)
                    AddToCell(EntityMatcher.PackCell(x, z), item);
        }

        /// <summary>
        /// Indexes <paramref name="item"/> in every cell the straight segment a..b passes through
        /// (exact grid traversal, corner touches included). No length clamp: a 2 km shipping lane
        /// is indexed end to end, so a query anywhere along it finds it.
        /// Queries must use a radius that covers the item's half width (cells hold the centreline only).
        /// </summary>
        public void AddSegment(Vec2 a, Vec2 b, T item)
        {
            m_CellScratch.Clear();
            CollectSegmentCells(a, b, m_CellScratch);
            FlushScratch(item);
        }

        /// <summary>
        /// Indexes a curved net as 4 straight sub-segments along the quadratic curve that starts at
        /// <paramref name="a"/>, passes through <paramref name="mid"/> at t = 0.5 (CS2's Bezier midpoint),
        /// and ends at <paramref name="b"/>. Each cell receives the item once.
        /// </summary>
        public void AddCurve(Vec2 a, Vec2 mid, Vec2 b, T item)
        {
            m_CellScratch.Clear();
            Vec2 prev = a;
            for (int k = 1; k <= 4; k++)
            {
                Vec2 next = NetShape.QuadThroughMid(a, mid, b, k * 0.25f);
                CollectSegmentCells(prev, next, m_CellScratch);
                prev = next;
            }
            FlushScratch(item);
        }

        /// <summary>Returns every item in the cells overlapping the query square, each item at most once.</summary>
        public void QueryRadius(Vec2 center, float radius, List<T> into)
        {
            into.Clear();
            int x0 = (int)Math.Floor((center.X - radius) / m_CellSize);
            int x1 = (int)Math.Floor((center.X + radius) / m_CellSize);
            int z0 = (int)Math.Floor((center.Z - radius) / m_CellSize);
            int z1 = (int)Math.Floor((center.Z + radius) / m_CellSize);
            bool multi = x1 > x0 || z1 > z0;
            if (multi) m_QuerySeen.Clear();
            for (int x = x0; x <= x1; x++)
                for (int z = z0; z <= z1; z++)
                    if (m_Cells.TryGetValue(EntityMatcher.PackCell(x, z), out var list))
                        for (int i = 0; i < list.Count; i++)
                        {
                            if (multi && !m_QuerySeen.Add(list[i])) continue;
                            into.Add(list[i]);
                        }
        }

        private void AddToCell(long key, T item)
        {
            if (!m_Cells.TryGetValue(key, out var list))
                m_Cells[key] = list = new List<T>(4);
            list.Add(item);
        }

        private void FlushScratch(T item)
        {
            foreach (long key in m_CellScratch) AddToCell(key, item);
            m_CellScratch.Clear();
        }

        /// <summary>Amanatides-Woo grid walk (supercover at exact corner crossings).</summary>
        private void CollectSegmentCells(Vec2 a, Vec2 b, HashSet<long> into)
        {
            if (!IsFinite(a) || !IsFinite(b)) return;
            double inv = 1.0 / m_CellSize;
            double ax = a.X * inv, az = a.Z * inv, bx = b.X * inv, bz = b.Z * inv;
            int x = (int)Math.Floor(ax), z = (int)Math.Floor(az);
            int xEnd = (int)Math.Floor(bx), zEnd = (int)Math.Floor(bz);
            into.Add(EntityMatcher.PackCell(x, z));

            long steps = (long)Math.Abs(xEnd - x) + Math.Abs(zEnd - z);
            if (steps == 0) return;
            if (steps > MaxCellsPerSegment) return; // garbage coordinates, not a real net

            double dx = bx - ax, dz = bz - az;
            int sx = dx > 0 ? 1 : dx < 0 ? -1 : 0;
            int sz = dz > 0 ? 1 : dz < 0 ? -1 : 0;
            double tDeltaX = sx != 0 ? 1.0 / Math.Abs(dx) : double.PositiveInfinity;
            double tDeltaZ = sz != 0 ? 1.0 / Math.Abs(dz) : double.PositiveInfinity;
            double tMaxX = sx > 0 ? (x + 1 - ax) / dx : sx < 0 ? (ax - x) / -dx : double.PositiveInfinity;
            double tMaxZ = sz > 0 ? (z + 1 - az) / dz : sz < 0 ? (az - z) / -dz : double.PositiveInfinity;

            long guard = steps + 2;
            while ((x != xEnd || z != zEnd) && guard-- > 0)
            {
                if (tMaxX < tMaxZ - 1e-12)
                {
                    x += sx; tMaxX += tDeltaX;
                }
                else if (tMaxZ < tMaxX - 1e-12)
                {
                    z += sz; tMaxZ += tDeltaZ;
                }
                else
                {
                    // Exactly through a grid corner: include both side cells so nothing slips between.
                    if (sx != 0) into.Add(EntityMatcher.PackCell(x + sx, z));
                    if (sz != 0) into.Add(EntityMatcher.PackCell(x, z + sz));
                    if (sx != 0) { x += sx; tMaxX += tDeltaX; }
                    if (sz != 0) { z += sz; tMaxZ += tDeltaZ; }
                }
                into.Add(EntityMatcher.PackCell(x, z));
            }
        }

        private static bool IsFinite(Vec2 v) =>
            !(float.IsNaN(v.X) || float.IsInfinity(v.X) || float.IsNaN(v.Z) || float.IsInfinity(v.Z));
    }
}
