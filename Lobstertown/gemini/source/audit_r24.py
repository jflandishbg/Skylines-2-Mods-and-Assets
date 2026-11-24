"""R24 audit (second-pass standard): run with  blender -b --python source/audit_r24.py [-- import_dir]
Per model, LOD0 body + glass:
  bounds  inside the lot on all four sides
  front   something taller than 2 m within 0.7 m of the lot front
  occupied  >= 90% of the lot has building above 2 m over it (0.25 m samples, straight down)
  islands  one connected mass above 2.5 m (pieces >= 4 m2)
  floating no room (walls >= 1.2 m tall, starting above 1 m) more than 0.75 m beyond ground-reaching walls, >= 2 m2
  props    the import declares no props
"""
import bpy, sys, os, json, math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = Path(args[0]) if args else ROOT / "import_Z1B"
C = .5

def load(path):
    bpy.ops.import_scene.fbx(filepath=str(path), axis_forward="-Z", axis_up="Y")
    ob = bpy.context.selected_objects[0]
    M = ob.matrix_world; N = M.to_3x3().inverted().transposed()
    V = [M @ v.co for v in ob.data.vertices]
    F = [(list(p.vertices), (N @ p.normal).normalized()) for p in ob.data.polygons]
    return V, F

def cells_of(ps):
    x0, x1 = min(v.x for v in ps), max(v.x for v in ps); y0, y1 = min(v.y for v in ps), max(v.y for v in ps)
    return [(i, j) for i in range(int(x0 // C), int(x1 // C) + 1) for j in range(int(y0 // C), int(y1 // C) + 1)]

def groups(cells, eight=True):
    seen = set(); out = []
    nb = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0)] if eight else [(1, 0), (-1, 0), (0, 1), (0, -1)]
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

def audit(folder, rec):
    n = folder.name
    W, D = (8 * v for v in rec["lot"])
    V, F = load(folder / (n + ".fbx"))
    Vw, Fw = load(folder / (n + "_Win.fbx"))
    row = {}
    lo = [min(v[k] for v in V + Vw) for k in range(3)]; hi = [max(v[k] for v in V + Vw) for k in range(3)]
    assert lo[0] >= -W / 2 - .002 and hi[0] <= W / 2 + .002 and lo[1] >= -D / 2 - .002 and hi[1] <= D / 2 + .002, (n, "outside the lot", lo, hi)
    front = min(v.y for v in V if v.z > 2.0) + D / 2
    row["front_m"] = round(front, 2)
    assert front <= .7, (n, "not at the curb", round(front, 2))
    tree = BVHTree.FromPolygons(V + Vw, [f for f, _ in F] + [[len(V) + i for i in f] for f, _ in Fw])
    hit = tot = 0
    for i in range(int(W / .25)):
        for j in range(int(D / .25)):
            tot += 1
            loc = tree.ray_cast(Vector(((i + .5) * .25 - W / 2, (j + .5) * .25 - D / 2, 300)), Vector((0, 0, -1)), 300.1)[0]
            if loc is not None and loc.z > 2.0: hit += 1
    row["occupied_pct"] = round(100 * hit / tot, 1)
    assert row["occupied_pct"] >= 90, (n, "lot not filled", row["occupied_pct"])
    tall = set(); ground = set(); walls = set()
    for f, nrm in F:
        ps = [V[i] for i in f]; z0 = min(p.z for p in ps); z1 = max(p.z for p in ps)
        cs = cells_of(ps)
        if z1 > 2.5: tall.update(cs)
        if z0 < .6 and abs(nrm.z) < .3 and z1 - z0 > .25: ground.update(cs)
        if abs(nrm.z) < .2 and z1 - z0 >= 1.2 and z0 > 1.0: walls.update(cs)
    isl = [m for m in groups(tall) if len(m) * C * C >= 4]
    row["islands"] = len(isl)
    assert len(isl) == 1, (n, "pieces", [round(len(m) * C * C, 1) for m in isl])
    I = [c[0] for c in ground | tall]; J = [c[1] for c in ground | tall]
    i0, i1, j0, j1 = min(I) - 1, max(I) + 1, min(J) - 1, max(J) + 1
    outside = set(); st = [(i0, j0)]
    while st:
        a = st.pop()
        if a in outside or a in ground or not (i0 <= a[0] <= i1 and j0 <= a[1] <= j1): continue
        outside.add(a); st += [(a[0] + 1, a[1]), (a[0] - 1, a[1]), (a[0], a[1] + 1), (a[0], a[1] - 1)]
    near = set()
    for i in range(i0, i1 + 1):
        for j in range(j0, j1 + 1):
            if (i, j) not in outside:
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1): near.add((i + di, j + dj))
    over = {c for c in tall if c not in near}
    rooms = [m for m in groups(over) if len(m) * C * C >= 2 and sum(1 for c in m if c in walls) >= 3]
    row["floating_rooms"] = [round(len(m) * C * C, 1) for m in rooms]
    assert not rooms, (n, "room hanging off the building", row["floating_rooms"])
    assert not rec.get("props"), (n, "props declared")
    return row

man = json.loads((OUT / "manifest.json").read_text(encoding="utf8"))
recs = {a["name"]: a for a in man["assets"]}
results = {}
for n in sorted(recs):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    try:
        results[n] = audit(OUT / n, recs[n])
        print("ROW", n, json.dumps(results[n]), flush=True)
    except AssertionError as e:
        results[n] = None
        print("AUDIT_FAIL", e.args[0] if e.args else n, flush=True)
(OUT / "r24-audit.json").write_text(json.dumps(results, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
bad = [n for n, r in results.items() if r is None]
print("R24_AUDIT", len(results) - len(bad), "of", len(results), flush=True)
assert not bad, bad
