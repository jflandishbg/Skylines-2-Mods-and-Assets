"""Audit baked Gemini buildings:  blender -b --python audit_gemini.py -- <run folder> <name> [<name> ...]
Writes <run folder>/audit-gemini.json. Hard checks fail the building; the rest are measurements for the report.
  bounds     every vertex of every LOD inside the lot (+-2 mm)
  island     one connected building above 2.5 m (pieces >= 4 m2)
  floating   no room more than 0.75 m beyond walls that reach the ground
  blank      wall planes of 30 m2 or more with no window glass on them (today's lesson: no blank brick boxes)
  front_m / occupied_pct   reported, not enforced
"""
import bpy, sys, json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

args = sys.argv[sys.argv.index("--") + 1:]
OUT = Path(args[0]); NAMES = args[1:]
C = .5

def load(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path), axis_forward="-Z", axis_up="Y")
    ob = bpy.context.selected_objects[0]
    M = ob.matrix_world; N = M.to_3x3().inverted().transposed()
    V = [M @ v.co for v in ob.data.vertices]
    F = [(list(p.vertices), (N @ p.normal).normalized(), p.area * M.median_scale ** 2) for p in ob.data.polygons]
    return V, F

def cells_of(ps):
    x0, x1 = min(v.x for v in ps), max(v.x for v in ps); y0, y1 = min(v.y for v in ps), max(v.y for v in ps)
    return [(i, j) for i in range(int(x0 // C), int(x1 // C) + 1) for j in range(int(y0 // C), int(y1 // C) + 1)]

def groups(cells):
    seen = set(); out = []
    nb = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0)]
    for c in cells:
        if c in seen: continue
        st = [c]; seen.add(c); mem = []
        while st:
            a = st.pop(); mem.append(a)
            for di, dj in nb:
                b = (a[0] + di, a[1] + dj)
                if b in cells and b not in seen: seen.add(b); st.append(b)
        out.append(mem)
    return out

def party_sides(name):
    """Row houses declare PARTY_WALLS = ("left", "right"): those side walls touch the neighbours and may be blank."""
    import re
    p = OUT.parents[1] / "scripts" / f"{name}.py"
    m = re.search(r"^PARTY_WALLS\s*=\s*\(([^)]*)\)", p.read_text(encoding="utf8"), re.M) if p.exists() else None
    return {x.strip(" '\"").lower() for x in m[1].split(",") if x.strip(" '\"")} if m else set()

def blank_walls(V, F, Vw, party=(), W=0):
    """Group vertical faces by plane; a plane of >= 30 m2 with no glass within 0.6 m of it, inside its extent, is blank."""
    planes = {}
    for f, n, area in F:
        if abs(n.z) > .2 or area < 1e-4: continue
        h = Vector((n.x, n.y, 0)).normalized()
        d = sum(V[i].dot(h) for i in f) / len(f)
        key = (round(h.x, 2), round(h.y, 2), round(d / .1))
        e = planes.setdefault(key, dict(h=h, d=d, area=0, pts=[]))
        e["area"] += area; e["pts"] += [V[i] for i in f]
    bad = []
    tree = BVHTree.FromPolygons(V, [f for f, _, _ in F])
    def board(e, us, zs):
        """A false front's back or a parapet: a board, not a room's wall (rule 28 forbids glass in it).
        Inward from the face, the building's own other face is met within 1 m at most of five points."""
        h, t = e["h"], Vector((-e["h"].y, e["h"].x, 0))
        u0, u1, z0, z1 = min(us), max(us), min(zs), max(zs)
        pts = [h * e["d"] + t * (u0 + (u1 - u0) * a) + Vector((0, 0, z0 + (z1 - z0) * c))
               for a, c in ((.5, .5), (.25, .3), (.75, .3), (.25, .7), (.75, .7))]
        thin = sum(1 for q in pts if (lambda r: r[0] is not None and r[3] < 1.0)(tree.ray_cast(q - h * .02, -h, 5.0)))
        return thin >= 3
    for e in planes.values():
        if e["area"] < 30: continue
        h = e["h"]; t = Vector((-h.y, h.x, 0))
        us = [p.dot(t) for p in e["pts"]]; zs = [p.z for p in e["pts"]]
        if e["area"] < .5 * (max(us) - min(us)) * (max(zs) - min(zs)): continue   # an open frame (a verandah's posts,
                                     # rails and deck edges), not a wall: a wall plane is at least half solid
        glass = [p for p in Vw if abs(p.dot(h) - e["d"]) < .6 and min(us) <= p.dot(t) <= max(us) and min(zs) <= p.z <= max(zs)]
        if not glass and not board(e, us, zs):
            side = "front" if h.y < -.7 else "rear" if h.y > .7 else "right side" if h.x > .7 else "left side" if h.x < -.7 else "angled"
            if side in ("left side", "right side") and side.split()[0] in party and abs(abs(e["d"]) - W / 2) < .6:
                continue                     # a declared party wall on the side lot line
            bad.append(dict(side=side, area_m2=round(e["area"], 1), width_m=round(max(us) - min(us), 1), height_m=round(max(zs) - min(zs), 1)))
    return sorted(bad, key=lambda b: -b["area_m2"])

def slits(grid):
    """Empty runs of 1-3 cells (0.5-1.5 m) with building on both ends, along x or y: the air slits between blocks."""
    NI, NJ = len(grid), len(grid[0]); bad = set()
    lines = [[(i, j) for i in range(NI)] for j in range(NJ)] + [[(i, j) for j in range(NJ)] for i in range(NI)]
    for line in lines:
        k = 0
        while k < len(line):
            if grid[line[k][0]][line[k][1]]: k += 1; continue
            e = k
            while e < len(line) and not grid[line[e][0]][line[e][1]]: e += 1
            if k > 0 and e < len(line) and e - k <= 3: bad.update(line[k:e])
            k = e
    return round(len(bad) * .25, 2)

CROWN_ZONES = ("ZC2", "ZP3")          # rule 11b (the author 2026-11-16): château towers and turrets are a crown
CROWN_M2 = 150.0

def zone_of(name):
    import re
    p = OUT.parents[1] / "scripts" / f"{name}.py"
    m = re.search(r"^ZONE\s*=\s*['\"](\w+)['\"]", p.read_text(encoding="utf8"), re.M) if p.exists() else None
    return m[1] if m else None

def blind_windows(V, F, Vw, Fw):
    """Rule 28: a window needs a room behind it. Half a metre behind the head of each pane (three points across
    it), a ray straight up must meet the building's own roof or ceiling; a pane where two of the three see open
    sky stands in a parapet, a false front over nothing, or above a roof valley. Roof seams (12 mm gaps between
    slabs) let one ray through, which is why it takes two."""
    tree = BVHTree.FromPolygons(V, [f for f, _, _ in F])
    up, bad = Vector((0, 0, 1)), []
    for f, nrm, _ in Fw:
        if abs(nrm.z) > .5: continue                 # skylights and roof glass
        c = sum((Vw[i] for i in f), Vector()) / len(f)
        hd = Vector((c.x, c.y, max(Vw[i].z for i in f) - .1))
        tan = Vector((-nrm.y, nrm.x, 0)).normalized()
        if sum(tree.ray_cast(hd - nrm * .5 + tan * s, up, 300)[0] is None for s in (-.25, 0, .25)) >= 2:
            bad.append((round(c.x, 1), round(c.y, 1), round(c.z, 1)))
    return sorted(set(bad))

def crown_cells(height, S=.25, limit=CROWN_M2, eps=.3):
    """Rule 11b, block by block: a cell is crown when the connected mass standing at or above its height
    (less eps) covers under `limit` m2 in plan: a tower, pavilion, turret, dome or ridge crest judged on its
    own, whatever else on the building stands taller. Union-find, sweeping the cells from the top down."""
    NI, NJ = len(height), len(height[0])
    cells = sorted(((height[i][j], i, j) for i in range(NI) for j in range(NJ) if height[i][j] is not None), reverse=True)
    if len(cells) * S * S < limit:
        return set()                     # the whole building is small: no crown, all of it counts
    par, size = {}, {}
    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]; a = par[a]
        return a
    crown, k, cap = set(), 0, limit / (S * S)
    for h, i, j in cells:
        while k < len(cells) and cells[k][0] > h - eps:          # add every cell above this one's height, less eps
            _, a, b2 = cells[k]; c = (a, b2); par[c] = c; size[c] = 1; k += 1
            for n in ((a + 1, b2), (a - 1, b2), (a, b2 + 1), (a, b2 - 1)):
                if n in par:
                    r1, r2 = find(c), find(n)
                    if r1 != r2:
                        if size[r1] < size[r2]: r1, r2 = r2, r1
                        par[r2] = r1; size[r1] += size[r2]
        if size[find((i, j))] < cap:
            crown.add((i, j))
    return crown

def roof_levels(height, party=(), S=.25, crown=()):
    """Eave heights: the top of the building along its outline (cells beside open ground), seen from above,
    grouped within 0.4 m; a height needs 3 m of outline to count (pediments and dormers don't).
    Outline on a declared party wall (within 0.6 m of that side lot line) is skipped: the neighbour covers it."""
    NI, NJ = len(height), len(height[0]); edge = {}
    near = int(.6 / S)
    for i in range(NI):
        if ("left" in party and i < near) or ("right" in party and i >= NI - near): continue
        for j in range(NJ):
            if height[i][j] is None: continue
            nb = [(i + a, j + b) for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))]
            if any(not (0 <= a < NI and 0 <= b < NJ) or height[a][b] is None for a, b in nb): edge[(i, j)] = height[i][j]
    seen, runs = set(), []                   # unbroken stretches of outline at one height (within 0.4 m)
    for c in edge:
        if c in seen: continue
        st, mem = [c], []; seen.add(c)
        while st:                            # crown cells link a run but never set its height (rule 11b)
            a = st.pop()
            if a not in crown: mem.append(edge[a])
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    b = (a[0] + di, a[1] + dj)
                    if b in edge and b not in seen and abs(edge[b] - edge[a]) < .4: seen.add(b); st.append(b)
        if len(mem) >= 12: runs.append(min(mem))     # 3 m of outline
    levels = []
    for z in sorted(runs):
        if not levels or z - levels[-1] > .4: levels.append(z)
    return [round(z, 1) for z in levels]

def audit(name, lot):
    W, D = 8 * lot[0], 8 * lot[1]
    row = dict(fail=[])
    for suf in ("", "_LOD1", "_LOD2"):
        for part in ("", "_Win"):
            V, _ = load(OUT / name / f"{name}{suf}{part}.fbx")
            if not V: continue
            lo = [min(v[k] for v in V) for k in range(3)]; hi = [max(v[k] for v in V) for k in range(3)]
            if lo[0] < -W / 2 - .002 or hi[0] > W / 2 + .002 or lo[1] < -D / 2 - .002 or hi[1] > D / 2 + .002 or lo[2] < -.01:
                row["fail"].append(f"outside the lot in LOD{suf[-1] if suf else 0}{' glass' if part else ''}: x {lo[0]:.2f}..{hi[0]:.2f}, y {lo[1]:.2f}..{hi[1]:.2f}, lowest z {lo[2]:.2f} (lot is x ±{W/2}, y ±{D/2})")
    V, F = load(OUT / name / f"{name}.fbx"); Vw, Fw = load(OUT / name / f"{name}_Win.fbx")
    row["height_m"] = round(max(v.z for v in V), 1)
    tall_front = [v.y for v in V if v.z > 2.0]
    row["front_m"] = round(min(tall_front) + D / 2, 2) if tall_front else None
    tree = BVHTree.FromPolygons(V + Vw, [f for f, _, _ in F] + [[len(V) + i for i in f] for f, _, _ in Fw])
    NI, NJ = int(W / .5), int(D / .5)
    grid = [[False] * NJ for _ in range(NI)]
    for i in range(NI):
        for j in range(NJ):
            loc = tree.ray_cast(Vector(((i + .5) * .5 - W / 2, (j + .5) * .5 - D / 2, 300)), Vector((0, 0, -1)), 300.1)[0]
            grid[i][j] = loc is not None and loc.z > 2.0
    S = .25                                   # finer height map for the eaves: the outermost hit is the cornice
    height = [[None] * int(D / S) for _ in range(int(W / S))]
    for i in range(len(height)):
        for j in range(len(height[0])):
            loc = tree.ray_cast(Vector(((i + .5) * S - W / 2, (j + .5) * S - D / 2, 300)), Vector((0, 0, -1)), 300.1)[0]
            if loc is not None and loc.z > 2.0: height[i][j] = loc.z
    row["occupied_pct"] = round(100 * sum(map(sum, grid)) / (NI * NJ), 1)
    row["gaps_m2"] = slits(grid)
    if row["gaps_m2"] >= 1.0:
        row["fail"].append(f"narrow gaps between blocks ({row['gaps_m2']} m² of slits under 1.5 m wide): blocks must touch or overlap, or stand well apart")
    crown = crown_cells(height, S) if zone_of(name) in CROWN_ZONES else set()
    if crown:
        row["crown_m2"] = round(len(crown) * S * S, 1)
    row["roof_levels_m"] = roof_levels(height, party_sides(name), S, crown)
    if len(row["roof_levels_m"]) > 3:
        row["fail"].append(f"too many roof heights: eaves at {row['roof_levels_m']} m; step the wings down deliberately to one or two levels")
    tall = set(); ground = set(); walls = set()
    for f, nrm, _ in F:
        ps = [V[i] for i in f]; z0 = min(p.z for p in ps); z1 = max(p.z for p in ps)
        cs = cells_of(ps)
        if z1 > 2.5: tall.update(cs)
        if z0 < .6 and abs(nrm.z) < .3 and z1 - z0 > .25: ground.update(cs)
        if abs(nrm.z) < .2 and z1 - z0 >= 1.2 and z0 > 1.0: walls.update(cs)
    isl = [m for m in groups(tall) if len(m) * C * C >= 4]
    row["pieces"] = len(isl)
    if len(isl) != 1: row["fail"].append(f"{len(isl)} separate pieces (sizes {[round(len(m)*C*C,1) for m in isl]} m²): it must be one building")
    if ground | tall:
        I = [c[0] for c in ground | tall]; J = [c[1] for c in ground | tall]
        i0, i1, j0, j1 = min(I) - 1, max(I) + 1, min(J) - 1, max(J) + 1
        outside = set(); st = [(i0, j0)]
        while st:
            a = st.pop()
            if a in outside or a in ground or not (i0 <= a[0] <= i1 and j0 <= a[1] <= j1): continue
            outside.add(a); st += [(a[0] + 1, a[1]), (a[0] - 1, a[1]), (a[0], a[1] + 1), (a[0], a[1] - 1)]
        near = {(i + di, j + dj) for i in range(i0, i1 + 1) for j in range(j0, j1 + 1) if (i, j) not in outside for di in (-1, 0, 1) for dj in (-1, 0, 1)}
        rooms = [m for m in groups({c for c in tall if c not in near}) if len(m) * C * C >= 2 and sum(1 for c in m if c in walls) >= 3]
        if rooms: row["fail"].append(f"room(s) hanging off the building with no walls to the ground: {[round(len(m)*C*C,1) for m in rooms]} m²")
    row["blank_walls"] = blank_walls(V, F, Vw, party_sides(name), W)
    row["blind_windows"] = blind_windows(V, F, Vw, Fw)
    if row["blind_windows"]:
        row["fail"].append(f"{len(row['blind_windows'])} window(s) with no room behind them (rule 28: sky or roof slope behind the glass), at x,y,z {row['blind_windows'][:6]}: drop them or build the storey behind")
    if row["blank_walls"]:
        row["fail"].append("blank walls: " + "; ".join(f"{b['side']} {b['width_m']} × {b['height_m']} m with no windows" for b in row["blank_walls"][:5]))
    return row

man = json.loads((OUT / "manifest.json").read_text(encoding="utf8")) if (OUT / "manifest.json").exists() else None
lots = {a["name"]: a["lot"] for a in man["assets"]} if man else {}
res = {}
for n in NAMES:
    lot = lots.get(n) or [int(n[-3]), int(n[-1])]
    try: res[n] = audit(n, lot)
    except Exception as e: res[n] = dict(fail=[f"audit could not run: {type(e).__name__} {e}"])
    print("AUDIT", n, "PASS" if not res[n]["fail"] else "FAIL", json.dumps(res[n], ensure_ascii=False), flush=True)
(OUT / "audit-gemini.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
