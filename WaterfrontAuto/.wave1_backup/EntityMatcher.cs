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
            var claimed = new List<long>();
            unmatchedPending = 0;
            if (pending == null || pending.Count == 0) return claimed;
            if (candidates == null || candidates.Count == 0)
            {
                unmatchedPending = pending.Count;
                return claimed;
            }

            // Build spatial hash of eligible candidates keyed by cell (4m cells)
            const float cellSize = 4f;
            var grid = new Dictionary<long, List<int>>();
            for (int i = 0; i < candidates.Count; i++)
            {
                var c = candidates[i];
                if (c.HasOwner || c.IsTemp || string.IsNullOrEmpty(c.PrefabName)) continue;
                long key = CellKey(c.Pos, cellSize);
                if (!grid.TryGetValue(key, out var list))
                    grid[key] = list = new List<int>(4);
                list.Add(i);
            }

            var usedCandidate = new bool[candidates.Count];

            for (int pIdx = pending.Count - 1; pIdx >= 0; pIdx--)
            {
                var p = pending[pIdx];
                if (string.IsNullOrEmpty(p.PrefabName)) { unmatchedPending++; continue; }

                float tol = ToleranceForCapture(p.Kind);
                float tolSq = tol * tol;
                int bestIdx = -1;
                float bestDistSq = tolSq;

                int cx = (int)Math.Floor(p.Pos.X / cellSize);
                int cz = (int)Math.Floor(p.Pos.Z / cellSize);

                for (int dx = -1; dx <= 1; dx++)
                {
                    for (int dz = -1; dz <= 1; dz++)
                    {
                        long key = PackCell(cx + dx, cz + dz);
                        if (!grid.TryGetValue(key, out var bucket)) continue;
                        for (int b = 0; b < bucket.Count; b++)
                        {
                            int ci = bucket[b];
                            if (usedCandidate[ci]) continue;
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
                    usedCandidate[bestIdx] = true;
                    claimed.Add(candidates[bestIdx].EntityId);
                    pending.RemoveAt(pIdx); // consume once!
                }
                else
                {
                    unmatchedPending++;
                }
            }

            return claimed;
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

        public static List<long> MatchWithTolerance(
            List<PendingItem> pending,
            IReadOnlyList<LiveCandidate> candidates,
            float tolerance,
            out int unmatched)
        {
            var claimed = new List<long>();
            unmatched = 0;
            if (pending == null || pending.Count == 0) return claimed;
            if (candidates == null || candidates.Count == 0) { unmatched = pending.Count; return claimed; }

            const float cellSize = 4f;
            var grid = new Dictionary<long, List<int>>();
            for (int i = 0; i < candidates.Count; i++)
            {
                var c = candidates[i];
                if (c.HasOwner || c.IsTemp || string.IsNullOrEmpty(c.PrefabName)) continue;
                long key = CellKey(c.Pos, cellSize);
                if (!grid.TryGetValue(key, out var list))
                    grid[key] = list = new List<int>(4);
                list.Add(i);
            }

            var used = new bool[candidates.Count];
            float tolSq = tolerance * tolerance;

            for (int i = pending.Count - 1; i >= 0; i--)
            {
                var p = pending[i];
                int cx = (int)Math.Floor(p.Pos.X / cellSize);
                int cz = (int)Math.Floor(p.Pos.Z / cellSize);
                int bestIdx = -1;
                float bestDistSq = tolSq;

                for (int dx = -1; dx <= 1; dx++)
                {
                    for (int dz = -1; dz <= 1; dz++)
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
                    pending.RemoveAt(i);
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
            if (string.IsNullOrEmpty(prefabName) || m_Grid.Count == 0) return false;
            float tolSq = tolerance * tolerance;
            int cx = (int)Math.Floor(pos.X / CellSize);
            int cz = (int)Math.Floor(pos.Z / CellSize);
            for (int dx = -1; dx <= 1; dx++)
            {
                for (int dz = -1; dz <= 1; dz++)
                {
                    if (!m_Grid.TryGetValue(EntityMatcher.PackCell(cx + dx, cz + dz), out var bucket)) continue;
                    for (int i = 0; i < bucket.Count; i++)
                    {
                        var c = bucket[i];
                        if (c.Kind != kind) continue;
                        if (!string.Equals(c.PrefabName, prefabName, StringComparison.Ordinal)) continue;
                        if (Vec2.DistanceSq(c.Pos, pos) <= tolSq)
                        {
                            existingEntityId = c.EntityId;
                            return true;
                        }
                    }
                }
            }
            return false;
        }
    }

    /// <summary>Generic 2D spatial hash grid for fast O(1) neighborhood lookups (eliminates O(N^2) scans).</summary>
    public sealed class SpatialGrid2D<T>
    {
        private readonly float m_CellSize;
        private readonly Dictionary<long, List<T>> m_Cells = new Dictionary<long, List<T>>();

        public SpatialGrid2D(float cellSize) { m_CellSize = cellSize; }

        public void AddPoint(Vec2 p, T item)
        {
            long key = EntityMatcher.CellKey(p, m_CellSize);
            if (!m_Cells.TryGetValue(key, out var list))
                m_Cells[key] = list = new List<T>(4);
            list.Add(item);
        }

        public void AddBounds(Vec2 min, Vec2 max, T item)
        {
            int x0 = (int)Math.Floor(min.X / m_CellSize);
            int x1 = (int)Math.Floor(max.X / m_CellSize);
            int z0 = (int)Math.Floor(min.Z / m_CellSize);
            int z1 = (int)Math.Floor(max.Z / m_CellSize);
            // Clamp pathological huge segments
            if (x1 - x0 > 16) x1 = x0 + 16;
            if (z1 - z0 > 16) z1 = z0 + 16;
            for (int x = x0; x <= x1; x++)
                for (int z = z0; z <= z1; z++)
                {
                    long key = EntityMatcher.PackCell(x, z);
                    if (!m_Cells.TryGetValue(key, out var list))
                        m_Cells[key] = list = new List<T>(4);
                    list.Add(item);
                }
        }

        public void QueryRadius(Vec2 center, float radius, List<T> into)
        {
            into.Clear();
            int x0 = (int)Math.Floor((center.X - radius) / m_CellSize);
            int x1 = (int)Math.Floor((center.X + radius) / m_CellSize);
            int z0 = (int)Math.Floor((center.Z - radius) / m_CellSize);
            int z1 = (int)Math.Floor((center.Z + radius) / m_CellSize);
            for (int x = x0; x <= x1; x++)
                for (int z = z0; z <= z1; z++)
                    if (m_Cells.TryGetValue(EntityMatcher.PackCell(x, z), out var list))
                        for (int i = 0; i < list.Count; i++)
                            into.Add(list[i]);
        }
    }
}
