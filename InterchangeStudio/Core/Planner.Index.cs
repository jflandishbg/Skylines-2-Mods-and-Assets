// Ported from ClaudeInterchanges (OverpassToolSystem) by Build/port.py, then kept by hand.
// Pure planning code: it reads the road network through the NetWorld look-alike (Core/Ecs.cs) and never
// touches the game. Settings come from the immutable PlanConfig (Core/Config.cs).
using System.Collections.Generic;
using Colossal.Mathematics;
using Unity.Mathematics;

namespace InterchangeStudio.Core
{
    /*
     * A coarse grid of road and railway pieces by area. Looking for "roads near here" then only touches a
     * few cells instead of every road in the city, which is what made hovering stutter in big cities.
     * The grid is rebuilt when the number of pieces changes, after every build, and every so often.
     */
    public partial class Planner
    {
        const float GridCell = 128f;
        private readonly Dictionary<long, List<Entity>> m_RoadGrid = new Dictionary<long, List<Entity>>();
        private readonly Dictionary<long, List<Entity>> m_TrackGrid = new Dictionary<long, List<Entity>>();
        private int m_GridRoads = -1, m_GridTracks = -1, m_GridAge;
        private bool m_GridDirty = true;

        static long CellKey(int x, int z) => ((long)x << 32) | (uint)z;

        void IndexEdges(EntityQuery q, Dictionary<long, List<Entity>> grid)
        {
            grid.Clear();
            using (var ents = q.ToEntityArray(Allocator.Temp))
                foreach (var e in ents)
                {
                    var cv = EntityManager.GetComponentData<Curve>(e).m_Bezier;
                    float2 lo = math.min(math.min(cv.a.xz, cv.b.xz), math.min(cv.c.xz, cv.d.xz));
                    float2 hi = math.max(math.max(cv.a.xz, cv.b.xz), math.max(cv.c.xz, cv.d.xz));
                    int x0 = (int)math.floor(lo.x / GridCell), x1 = (int)math.floor(hi.x / GridCell);
                    int z0 = (int)math.floor(lo.y / GridCell), z1 = (int)math.floor(hi.y / GridCell);
                    for (int x = x0; x <= x1; x++)
                        for (int z = z0; z <= z1; z++)
                        {
                            long k = CellKey(x, z);
                            if (!grid.TryGetValue(k, out var list)) grid[k] = list = new List<Entity>();
                            list.Add(e);
                        }
                }
        }

        void FreshGrid()
        {
            int nr = m_RoadEdges.CalculateEntityCount(), nt = m_TrackEdges.CalculateEntityCount();
            if (!m_GridDirty && nr == m_GridRoads && nt == m_GridTracks && ++m_GridAge < 2000) return;
            IndexEdges(m_RoadEdges, m_RoadGrid); IndexEdges(m_TrackEdges, m_TrackGrid);
            m_GridRoads = nr; m_GridTracks = nt; m_GridAge = 0; m_GridDirty = false;
        }

        /* road pieces whose bounding box may overlap the area lo..hi (each once) */
        List<Entity> RoadsNear(float2 lo, float2 hi) => InCells(m_RoadGrid, lo, hi);

        /* railway track pieces whose bounding box may overlap the area lo..hi (each once) */
        List<Entity> TracksNear(float2 lo, float2 hi) => InCells(m_TrackGrid, lo, hi);

        List<Entity> InCells(Dictionary<long, List<Entity>> grid, float2 lo, float2 hi)
        {
            FreshGrid();
            var seen = new HashSet<Entity>(); var list = new List<Entity>();
            int x0 = (int)math.floor(lo.x / GridCell), x1 = (int)math.floor(hi.x / GridCell);
            int z0 = (int)math.floor(lo.y / GridCell), z1 = (int)math.floor(hi.y / GridCell);
            for (int x = x0; x <= x1; x++)
                for (int z = z0; z <= z1; z++)
                    if (grid.TryGetValue(CellKey(x, z), out var cell))
                        foreach (var e in cell) if (seen.Add(e)) list.Add(e);
            return list;
        }
    }
}
