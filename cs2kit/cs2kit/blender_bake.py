"""Single-pass Blender baker + FBX validator + full architectural auditor worker.

Invoked by runner.py:
  blender.exe -b --python-exit-code 2 --python blender_bake.py -- <worker_plan.json>
"""
from collections import Counter
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from cs2kit.mesh import capture_meshes
from cs2kit.tile_mesh import (
    LODKEY,
    ROOMS,
    atlas_partition,
    build_tiled_meshes,
    export_fbx,
    material_uvs,
    newell,
    optimize_far,
    overlaps,
    smooth_export,
    verify_raw_fbx,
)


SUFFIXES = ("", "_LOD1", "_LOD2")


def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for col in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
        for item in list(col):
            if not item.users:
                col.remove(item)


def mesh_stats(ob):
    me = ob.data
    me.calc_loop_triangles()
    pts = [ob.matrix_world @ v.co for v in me.vertices]
    if not pts:
        return {"triangles": 0, "vertices": 0, "bounds_m": [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]}
    return {
        "triangles": len(me.loop_triangles),
        "vertices": len(me.vertices),
        "bounds_m": [
            [round(min(p[k] for p in pts), 5) for k in range(3)],
            [round(max(p[k] for p in pts), 5) for k in range(3)],
        ],
    }


def mesh_bvh(ob):
    vs = [ob.matrix_world @ v.co for v in ob.data.vertices]
    faces = [tuple(p.vertices) for p in ob.data.polygons]
    return BVHTree.FromPolygons(vs, faces), vs


def envelope_area(ob, skip=()):
    """Sum the 5 exterior orthographic projections (excusing declared party walls) for LOD0 density."""
    tree, vertices = mesh_bvh(ob)
    if not vertices:
        return 1.0
    lo = [min(v[k] for v in vertices) for k in range(3)]
    hi = [max(v[k] for v in vertices) for k in range(3)]
    lo[2] = 0.34
    spacing = 0.38
    skip_set = {tuple(x) for x in skip}
    area = 0.0
    for axis, sign in ((0, 1), (0, -1), (1, 1), (1, -1), (2, -1)):
        if (axis, sign) in skip_set:
            continue
        direction = Vector([sign if k == axis else 0.0 for k in range(3)])
        u, v = [k for k in range(3) if k != axis]
        nu = max(1, int((hi[u] - lo[u]) / spacing))
        nv = max(1, int((hi[v] - lo[v]) / spacing))
        for i in range(nu):
            for j in range(nv):
                pt = [0.0, 0.0, 0.0]
                pt[axis] = lo[axis] - 1.0 if sign > 0 else hi[axis] + 1.0
                pt[u] = lo[u] + (i + 0.5) * spacing
                pt[v] = lo[v] + (j + 0.5) * spacing
                hit = tree.ray_cast(Vector(pt), direction, 120.0)[0]
                if hit is not None and hit.z >= 0.34:
                    area += spacing * spacing
    return max(1.0, area)


def _load_module(designs_dir: Path, module_name: str, pack_id: str, cache: dict):
    if module_name in cache:
        return cache[module_name]
    designs_dir = designs_dir.resolve()
    dstr = str(designs_dir)
    if dstr not in sys.path:
        sys.path.insert(0, dstr)
    pkg_name = f"_cs2kit_bake_{pack_id}"
    if pkg_name not in sys.modules:
        init_py = designs_dir / "__init__.py"
        pkg_spec = importlib.util.spec_from_file_location(
            pkg_name,
            init_py if init_py.exists() else None,
            submodule_search_locations=[dstr],
        )
        if pkg_spec is not None:
            pkg_mod = importlib.util.module_from_spec(pkg_spec)
            pkg_mod.__path__ = [dstr]
            sys.modules[pkg_name] = pkg_mod
            if pkg_spec.loader is not None and init_py.exists():
                pkg_spec.loader.exec_module(pkg_mod)
    full_name = f"{pkg_name}.{module_name}"
    spec = importlib.util.spec_from_file_location(full_name, designs_dir / f"{module_name}.py")
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load design module {module_name!r} from {designs_dir}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = mod
    spec.loader.exec_module(mod)
    cache[module_name] = mod
    return mod


def _extract_vf(ob):
    M = ob.matrix_world
    N = M.to_3x3().inverted().transposed()
    V = [M @ v.co for v in ob.data.vertices]
    F = [(list(p.vertices), (N @ p.normal).normalized(), p.area * M.median_scale**2) for p in ob.data.polygons]
    return V, F


def _cells_of(ps, cell=0.5):
    x0, x1 = min(v.x for v in ps), max(v.x for v in ps)
    y0, y1 = min(v.y for v in ps), max(v.y for v in ps)
    return [(i, j) for i in range(int(x0 // cell), int(x1 // cell) + 1) for j in range(int(y0 // cell), int(y1 // cell) + 1)]


def _groups(cells):
    seen, out = set(), []
    nb = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0)]
    for c in cells:
        if c in seen:
            continue
        st, mem = [c], []
        seen.add(c)
        while st:
            a = st.pop()
            mem.append(a)
            for di, dj in nb:
                b = (a[0] + di, a[1] + dj)
                if b in cells and b not in seen:
                    seen.add(b)
                    st.append(b)
        out.append(mem)
    return out


def _slits(grid):
    NI, NJ = len(grid), len(grid[0])
    bad = set()
    lines = [[(i, j) for i in range(NI)] for j in range(NJ)] + [[(i, j) for j in range(NJ)] for i in range(NI)]
    for line in lines:
        k = 0
        while k < len(line):
            if grid[line[k][0]][line[k][1]]:
                k += 1
                continue
            e = k
            while e < len(line) and not grid[line[e][0]][line[e][1]]:
                e += 1
            if k > 0 and e < len(line) and e - k <= 3:
                bad.update(line[k:e])
            k = e
    return round(len(bad) * 0.25, 2)


def _crown_cells(height, S=0.25, limit=150.0, eps=0.3):
    NI, NJ = len(height), len(height[0])
    cells = sorted(
        ((height[i][j], i, j) for i in range(NI) for j in range(NJ) if height[i][j] is not None),
        reverse=True,
    )
    if len(cells) * S * S < limit:
        return set()
    par, size = {}, {}

    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a

    crown, k, cap = set(), 0, limit / (S * S)
    for h, i, j in cells:
        while k < len(cells) and cells[k][0] > h - eps:
            _, a, b2 = cells[k]
            c = (a, b2)
            par[c] = c
            size[c] = 1
            k += 1
            for n in ((a + 1, b2), (a - 1, b2), (a, b2 + 1), (a, b2 - 1)):
                if n in par:
                    r1, r2 = find(c), find(n)
                    if r1 != r2:
                        if size[r1] < size[r2]:
                            r1, r2 = r2, r1
                        par[r2] = r1
                        size[r1] += size[r2]
        if size[find((i, j))] < cap:
            crown.add((i, j))
    return crown


def _roof_levels(height, party, S=0.25, crown=()):
    NI, NJ = len(height), len(height[0])
    edge = {}
    near = int(0.6 / S)
    for i in range(NI):
        if ("left" in party and i < near) or ("right" in party and i >= NI - near):
            continue
        for j in range(NJ):
            if height[i][j] is None:
                continue
            nb = [(i + a, j + b) for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))]
            if any(not (0 <= a < NI and 0 <= b < NJ) or height[a][b] is None for a, b in nb):
                edge[(i, j)] = height[i][j]
    seen, runs = set(), []
    for c in edge:
        if c in seen:
            continue
        st, mem = [c], []
        seen.add(c)
        while st:
            a = st.pop()
            if a not in crown:
                mem.append(edge[a])
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    b = (a[0] + di, a[1] + dj)
                    if b in edge and b not in seen and abs(edge[b] - edge[a]) < 0.4:
                        seen.add(b)
                        st.append(b)
        if len(mem) >= 12:
            runs.append(min(mem))
    levels = []
    for z in sorted(runs):
        if not levels or z - levels[-1] > 0.4:
            levels.append(z)
    return [round(z, 1) for z in levels]


def _blank_walls(V, F, Vw, tree, party, W):
    planes = {}
    for f, n, area in F:
        if abs(n.z) > 0.2 or area < 1e-4:
            continue
        h = Vector((n.x, n.y, 0.0)).normalized()
        d = sum(V[i].dot(h) for i in f) / len(f)
        key = (round(h.x, 2), round(h.y, 2), round(d / 0.1))
        e = planes.setdefault(key, {"h": h, "d": d, "area": 0.0, "pts": []})
        e["area"] += area
        e["pts"] += [V[i] for i in f]

    def is_thin_board(e, us, zs):
        h, t = e["h"], Vector((-e["h"].y, e["h"].x, 0.0))
        u0, u1, z0, z1 = min(us), max(us), min(zs), max(zs)
        pts = [
            h * e["d"] + t * (u0 + (u1 - u0) * a) + Vector((0.0, 0.0, z0 + (z1 - z0) * c))
            for a, c in ((0.5, 0.5), (0.25, 0.3), (0.75, 0.3), (0.25, 0.7), (0.75, 0.7))
        ]
        thin = 0
        for q in pts:
            r = tree.ray_cast(q - h * 0.02, -h, 5.0)
            if r[0] is not None and r[3] < 1.0:
                thin += 1
        return thin >= 3

    bad = []
    for e in planes.values():
        if e["area"] < 30.0:
            continue
        h = e["h"]
        t = Vector((-h.y, h.x, 0.0))
        us = [p.dot(t) for p in e["pts"]]
        zs = [p.z for p in e["pts"]]
        if e["area"] < 0.5 * max(0.01, max(us) - min(us)) * max(0.01, max(zs) - min(zs)):
            continue
        glass = [p for p in Vw if abs(p.dot(h) - e["d"]) < 0.6 and min(us) <= p.dot(t) <= max(us) and min(zs) <= p.z <= max(zs)]
        if not glass and not is_thin_board(e, us, zs):
            side = (
                "front"
                if h.y < -0.7
                else "rear"
                if h.y > 0.7
                else "right side"
                if h.x > 0.7
                else "left side"
                if h.x < -0.7
                else "angled"
            )
            if side in ("left side", "right side") and side.split()[0] in party and abs(abs(e["d"]) - W / 2.0) < 0.6:
                continue
            bad.append(
                {
                    "side": side,
                    "area_m2": round(e["area"], 1),
                    "width_m": round(max(us) - min(us), 1),
                    "height_m": round(max(zs) - min(zs), 1),
                }
            )
    return sorted(bad, key=lambda b: -b["area_m2"])


def _blind_windows(tree, Vw, Fw):
    """Rule 28: ray straight up 0.5 m behind pane head must hit own roof/ceiling."""
    up = Vector((0.0, 0.0, 1.0))
    bad = []
    for f, nrm, _ in Fw:
        if abs(nrm.z) > 0.5:
            continue
        c = sum((Vw[i] for i in f), Vector()) / len(f)
        hd = Vector((c.x, c.y, max(Vw[i].z for i in f) - 0.1))
        tan = Vector((-nrm.y, nrm.x, 0.0)).normalized()
        misses = sum(tree.ray_cast(hd - nrm * 0.5 + tan * s, up, 300.0)[0] is None for s in (-0.25, 0.0, 0.25))
        if misses >= 2:
            bad.append((round(c.x, 1), round(c.y, 1), round(c.z, 1)))
    return sorted(set(bad))


def _backface_sweep(bv_body, bv_win, W, D, zmax):
    """Check exterior visibility rays across 5 directions at 0.25 m pitch."""
    bad = 0
    samples = []
    step = 0.25
    grid = lambda n: [-n / 2.0 + (i + 0.5) * step for i in range(max(1, round(n / step)))]
    zs = [0.05 + i * step for i in range(max(1, round(zmax / step)) + 1)]
    views = (
        ("top", lambda x, y: Vector((x, y, zmax + 9.0)), Vector((0.0, 0.0, -1.0)), grid(W), grid(D)),
        ("front", lambda x, z: Vector((x, -100.0, z)), Vector((0.0, 1.0, 0.0)), grid(W), zs),
        ("rear", lambda x, z: Vector((x, 100.0, z)), Vector((0.0, -1.0, 0.0)), grid(W), zs),
        ("left", lambda y, z: Vector((-100.0, y, z)), Vector((1.0, 0.0, 0.0)), grid(D), zs),
        ("right", lambda y, z: Vector((100.0, y, z)), Vector((-1.0, 0.0, 0.0)), grid(D), zs),
    )

    def first(start, ray):
        b = bv_body.ray_cast(start, ray)
        if b[0] is None:
            return None
        w = bv_win.ray_cast(start, ray)
        if w[0] is not None and w[3] <= b[3] + 1e-6:
            return None
        return b

    for vname, pt_fn, ray, aa, bb in views:
        u = Vector((1.0, 0.0, 0.0)) if abs(ray.x) < 0.5 else Vector((0.0, 1.0, 0.0))
        v = ray.cross(u)
        shifts = [u * (sgn * 0.00037) + v * (o * 0.00071) for sgn in (-1, 1) for o in (-1, 1)]
        for a in aa:
            for b in bb:
                origin = pt_fn(a, b)
                hit = first(origin, ray)
                if hit is None:
                    continue
                if hit[1].dot(ray) > 1e-6:
                    if any(t is not None and t[1].dot(ray) > 1e-6 for t in (first(origin + s, ray) for s in shifts)):
                        bad += 1
                        if len(samples) < 6:
                            samples.append({"view": vname, "point": [round(x, 3) for x in hit[0]]})
    return {"backface_hits": bad, "samples": samples}


def _validate_single_fbx(path: Path, lot: list, layout: dict, lod_key: str, buckets: dict, expected_bounds: list):
    """Import an exported FBX strictly once and run all geometry/UV/coplanar checks."""
    is_win = path.stem.endswith("_Win")
    raw_info = verify_raw_fbx(path, expected_bounds)
    clear_scene()
    bpy.ops.import_scene.fbx(filepath=str(path), axis_forward="-Z", axis_up="Y")
    obs = [o for o in bpy.context.selected_objects if o.type == "MESH"]
    assert len(obs) == 1, f"{path.name}: expected 1 mesh, found {len(obs)}"
    ob = obs[0]
    me = ob.data
    assert ob.name == path.stem, f"{path.name}: object name {ob.name!r} != {path.stem!r}"
    assert len(me.uv_layers) == 1, f"{path.name}: expected 1 UVMap, got {len(me.uv_layers)}"
    if is_win:
        assert len(me.materials) == 0, f"{path.name}: _Win mesh must have 0 materials, got {len(me.materials)}"
    else:
        assert len(me.materials) == 1 and me.materials[0].name == path.stem, (
            f"{path.name}: expected 1 material named {path.stem!r}"
        )

    stats = mesh_stats(ob)
    lo, hi = stats["bounds_m"]
    w, d = lot[0] * 8.0, lot[1] * 8.0
    if lo[0] < -w / 2.0 - 0.002 or hi[0] > w / 2.0 + 0.002:
        raise AssertionError(f"{path.name}: X bounds [{lo[0]:.3f}, {hi[0]:.3f}] outside lot +/-{w/2:.2f}")
    if lo[1] < -d / 2.0 - 0.002 or hi[1] > d / 2.0 + 0.002:
        raise AssertionError(f"{path.name}: Y bounds [{lo[1]:.3f}, {hi[1]:.3f}] outside lot +/-{d/2:.2f}")
    if lo[2] < -0.002:
        raise AssertionError(f"{path.name}: Z min {lo[2]:.4f} below ground")

    uv_layer = me.uv_layers[0].data
    for p in me.polygons:
        assert p.area > 1e-9, f"{path.name}: zero-area polygon {p.index}"
        vs = [ob.matrix_world @ me.vertices[i].co for i in p.vertices]
        if len(vs) > 3:
            local = [pt - vs[0] for pt in vs]
            nrm = newell(local).normalized()
            assert max(abs(pt.dot(nrm)) for pt in local) < 0.0003, f"{path.name}: nonplanar face {p.index}"
        uvs = [uv_layer[i].uv for i in p.loop_indices]
        assert all(-1e-5 <= c <= 1.00001 for uv in uvs for c in uv), f"{path.name}: UV out of [0, 1]"
        if is_win:
            cells = {(min(4, int(uv.x * 5)), min(4, int(uv.y * 5))) for uv in uvs}
            assert len(cells) == 1 and not any(c in {(0, 0), (4, 0), (0, 4), (4, 4)} for c in cells), (
                f"{path.name}: illegal _Win room cell {cells}"
            )

    used_mats = []
    if not is_win:
        ov = overlaps(ob)
        if ov:
            pt = ov[0]["point"]
            nrm = ov[0]["normal"]
            raise AssertionError(
                f"{path.name}: {len(ov)} coplanar overlap(s), e.g. {ov[0]['overlap_m2']} m2 at ({pt[0]:.3f}, {pt[1]:.3f}, {pt[2]:.3f}) normal {nrm}"
            )
        used_mats = material_uvs(ob, buckets)

    return ob, {**stats, "raw_fbx": raw_info, "materials_used": used_mats}


def bake_asset(asset: dict, designs_dir: Path, out_dir: Path, layout: dict, pack_id: str, mod_cache: dict, partitions: dict):
    name = asset["name"]
    folder = out_dir / name
    folder.mkdir(parents=True, exist_ok=True)
    lot = asset["lot"]
    limits = asset["budget"]
    mod = _load_module(designs_dir, asset["module"], pack_id, mod_cache)

    lods_info = {}
    exported = []
    area_env = 1.0

    for lod, suffix in enumerate(SUFFIXES):
        clear_scene()
        kwargs = dict(asset["params"])
        kwargs["W"] = lot[0]
        kwargs["D"] = lot[1]
        with capture_meshes() as captured:
            mod.build(lod, **kwargs)
        assert len(captured) == 1, f"{name} LOD{lod}: finish(m, g) was called {len(captured)} times"
        body_m, win_m = captured[0]

        t_body, t_win = build_tiled_meshes(body_m, win_m, lod, layout)
        body_tag = name + suffix
        win_tag = name + suffix + "_Win"

        body_ob = optimize_far(t_body.to_object(body_tag, bpy.data.materials.new(body_tag)), lod)
        win_ob = optimize_far(t_win.to_object(win_tag, None), lod)

        b_stats = mesh_stats(body_ob)
        w_stats = mesh_stats(win_ob)
        total_tris = b_stats["triangles"] + w_stats["triangles"]
        if total_tris > limits[lod]:
            raise AssertionError(f"LOD{lod} has {total_tris:,} triangles (limit {limits[lod]:,})")

        if lod == 0:
            area_env = envelope_area(body_ob, asset.get("party_skip", ()))
            density = total_tris / area_env
            if density < asset["density_floor"]:
                raise AssertionError(
                    f"LOD0 too plain: {total_tris:,} triangles / {area_env:.0f} m2 = {density:.1f} per m2 (< {asset['density_floor']})"
                )

        ov_pre = overlaps(body_ob)
        if ov_pre:
            pt = ov_pre[0]["point"]
            raise AssertionError(
                f"LOD{lod}: {len(ov_pre)} coplanar overlap(s), e.g. at ({pt[0]:.3f}, {pt[1]:.3f}, {pt[2]:.3f})"
            )

        smooth_export(body_ob)
        b_path = folder / f"{body_tag}.fbx"
        w_path = folder / f"{win_tag}.fbx"
        export_fbx(body_ob, b_path)
        export_fbx(win_ob, w_path)
        exported.append((lod, suffix, b_path, b_stats["bounds_m"], w_path, w_stats["bounds_m"]))

    meshes_info = {}
    audit_info = {}
    for lod, suffix, b_path, b_bounds, w_path, w_bounds in exported:
        lod_key = suffix or "main"
        b_ob, b_rec = _validate_single_fbx(b_path, lot, layout, lod_key, partitions[lod_key], b_bounds)
        # Keep LOD0 Body alive in a separate temp name? Simpler: extract V/F on b_ob before importing win!
        if lod == 0:
            V0, F0 = _extract_vf(b_ob)
        w_ob, w_rec = _validate_single_fbx(w_path, lot, layout, lod_key, partitions[lod_key], w_bounds)
        if lod == 0:
            Vw0, Fw0 = _extract_vf(w_ob)
            # Re-attach LOD0 audit directly from extracted (V0, F0, Vw0, Fw0)
            audit_info = _audit_lod0_vf(V0, F0, Vw0, Fw0, asset)
        meshes_info[b_path.stem] = b_rec
        meshes_info[w_path.stem] = w_rec
        total = b_rec["triangles"] + w_rec["triangles"]
        if total > limits[lod]:
            raise AssertionError(f"Post-export LOD{lod} has {total:,} triangles (limit {limits[lod]:,})")
        lods_info[lod_key] = {"triangles": total, "bounds_m": b_rec["bounds_m"], "materials_used": b_rec["materials_used"]}

    if audit_info.get("fails"):
        raise AssertionError(" | ".join(audit_info["fails"]))

    return {
        "name": name,
        "design": asset["design"],
        "zone_key": asset["zone_key"],
        "lot": lot,
        "budget": limits,
        "lods": lods_info,
        "envelope_m2": round(area_env, 2),
        "tris_per_m2": round(lods_info["main"]["triangles"] / area_env, 2),
        "audit": audit_info,
        "meshes": meshes_info,
        "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.glob("*.fbx"))},
    }


def _audit_lod0_vf(V, F, Vw, Fw, asset: dict):
    """Run full LOD0 architectural audit directly on extracted vertex/face lists."""
    W, D = 8.0 * asset["lot"][0], 8.0 * asset["lot"][1]
    party = set(asset.get("party_walls", ()))
    fails = []
    warnings = []

    height_m = round(max((v.z for v in V), default=0.0), 2)
    tall_front = [v.y for v in V if v.z > 2.0]
    front_m = round(min(tall_front) + D / 2.0, 2) if tall_front else None
    if front_m is not None and front_m > asset["max_front_setback_m"] + 1e-3:
        fails.append(
            f"Rule 29 (front setback): main front wall sits {front_m:.2f} m back from street > max {asset['max_front_setback_m']:.2f} m"
        )

    all_v = V + Vw
    all_f = [f for f, _, _ in F] + [[len(V) + i for i in f] for f, _, _ in Fw]
    tree = BVHTree.FromPolygons(all_v, all_f)
    body_tree = BVHTree.FromPolygons(V, [f for f, _, _ in F])
    win_tree = BVHTree.FromPolygons(Vw, [f for f, _, _ in Fw])

    NI, NJ = int(W / 0.5), int(D / 0.5)
    grid = [[False] * NJ for _ in range(NI)]
    for i in range(NI):
        for j in range(NJ):
            loc = tree.ray_cast(Vector(((i + 0.5) * 0.5 - W / 2.0, (j + 0.5) * 0.5 - D / 2.0, 300.0)), Vector((0.0, 0.0, -1.0)), 300.1)[0]
            grid[i][j] = loc is not None and loc.z > 2.0

    S = 0.25
    height = [[None] * int(D / S) for _ in range(int(W / S))]
    for i in range(len(height)):
        for j in range(len(height[0])):
            loc = tree.ray_cast(Vector(((i + 0.5) * S - W / 2.0, (j + 0.5) * S - D / 2.0, 300.0)), Vector((0.0, 0.0, -1.0)), 300.1)[0]
            if loc is not None and loc.z > 2.0:
                height[i][j] = loc.z

    occupied_pct = round(100.0 * sum(map(sum, grid)) / max(1, NI * NJ), 1)
    if asset.get("min_coverage_pct", 0.0) > 0 and occupied_pct < asset["min_coverage_pct"]:
        warnings.append(f"Rule 17 (lot coverage): {occupied_pct}% < target {asset['min_coverage_pct']}%")

    gaps_m2 = _slits(grid)
    if gaps_m2 >= 1.0:
        fails.append(f"narrow gaps between blocks ({gaps_m2} m2 of slits < 1.5 m wide)")

    crown = _crown_cells(height, S, limit=asset.get("crown_max_m2", 150.0)) if asset.get("crown_allowed") else set()
    roof_levels_m = _roof_levels(height, party, S, crown)
    if len(roof_levels_m) > 3:
        fails.append(f"too many roof heights: eaves at {roof_levels_m} m (max 3)")

    C = 0.5
    tall, ground, walls = set(), set(), set()
    for f, nrm, _ in F:
        ps = [V[i] for i in f]
        z0, z1 = min(p.z for p in ps), max(p.z for p in ps)
        cs = _cells_of(ps, C)
        if z1 > 2.5:
            tall.update(cs)
        if z0 < 0.6 and abs(nrm.z) < 0.3 and z1 - z0 > 0.25:
            ground.update(cs)
        if abs(nrm.z) < 0.2 and z1 - z0 >= 1.2 and z0 > 1.0:
            walls.update(cs)

    isl = [m for m in _groups(tall) if len(m) * C * C >= 4.0]
    if len(isl) != 1:
        fails.append(f"{len(isl)} separate pieces (sizes {[round(len(m)*C*C, 1) for m in isl]} m2): must be 1 building")

    if ground | tall:
        I = [c[0] for c in ground | tall]
        J = [c[1] for c in ground | tall]
        i0, i1, j0, j1 = min(I) - 1, max(I) + 1, min(J) - 1, max(J) + 1
        outside, st = set(), [(i0, j0)]
        while st:
            a = st.pop()
            if a in outside or a in ground or not (i0 <= a[0] <= i1 and j0 <= a[1] <= j1):
                continue
            outside.add(a)
            st += [(a[0] + 1, a[1]), (a[0] - 1, a[1]), (a[0], a[1] + 1), (a[0], a[1] - 1)]
        near = {
            (i + di, j + dj)
            for i in range(i0, i1 + 1)
            for j in range(j0, j1 + 1)
            if (i, j) not in outside
            for di in (-1, 0, 1)
            for dj in (-1, 0, 1)
        }
        rooms = [
            m
            for m in _groups({c for c in tall if c not in near})
            if len(m) * C * C >= 2.0 and sum(1 for c in m if c in walls) >= 3
        ]
        if rooms:
            fails.append(f"room(s) hanging off building with no walls to ground: {[round(len(m)*C*C, 1) for m in rooms]} m2")

    blank = _blank_walls(V, F, Vw, body_tree, party, W)
    if blank:
        fails.append(
            "blank walls: " + "; ".join(f"{b['side']} {b['width_m']} x {b['height_m']} m with no windows" for b in blank[:5])
        )

    blind = _blind_windows(body_tree, Vw, Fw)
    if blind:
        fails.append(f"{len(blind)} window(s) with no room behind them (Rule 28) at {blind[:6]}")

    sweep = _backface_sweep(body_tree, win_tree, W, D, max((v.z for v in V), default=1.0))
    if sweep["backface_hits"] > 0:
        warnings.append(f"backface_sweep flagged {sweep['backface_hits']} ray(s): {sweep['samples'][:3]}")

    return {
        "height_m": height_m,
        "front_m": front_m,
        "occupied_pct": occupied_pct,
        "gaps_m2": gaps_m2,
        "crown_m2": round(len(crown) * S * S, 1) if crown else 0.0,
        "roof_levels_m": roof_levels_m,
        "pieces": len(isl),
        "blank_walls": blank,
        "blind_windows": blind,
        "backface_hits": sweep["backface_hits"],
        "fails": fails,
        "warnings": warnings,
    }


def main():
    plan_path = Path(sys.argv[sys.argv.index("--") + 1])
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    designs_dir = Path(plan["designs_dir"])
    out_dir = Path(plan["out_dir"])
    layout = json.loads(Path(plan["atlas_layout_path"]).read_text(encoding="utf-8"))
    pack_id = plan["pack_id"]
    partitions = {lod: atlas_partition(layout, lod) for lod in LODKEY}

    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 1.0

    mod_cache = {}
    results = {}
    for asset in plan["assets"]:
        name = asset["name"]
        try:
            rec = bake_asset(asset, designs_dir, out_dir, layout, pack_id, mod_cache, partitions)
            results[name] = {"pass": True, "record": rec, "fail": []}
            print(
                f"ASSET_PASS {name} tris={rec['lods']['main']['triangles']}/{rec['lods']['_LOD1']['triangles']}/{rec['lods']['_LOD2']['triangles']} "
                f"cov={rec['audit']['occupied_pct']}%",
                flush=True,
            )
        except Exception as exc:
            msg = str(exc) or type(exc).__name__
            results[name] = {"pass": False, "record": None, "fail": [msg]}
            print(f"ASSET_FAIL {name}: {msg}", flush=True)

    Path(plan["result_path"]).write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"WORKER_COMPLETE {len(results)}", flush=True)


if __name__ == "__main__":
    main()
