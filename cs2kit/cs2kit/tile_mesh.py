"""Blender-side tile-clipped UV mapper, coplanar overlap detector, and raw FBX verifier.

Must be imported inside Blender's Python environment (uses bpy, bmesh, mathutils, io_scene_fbx).
"""
from collections import defaultdict
from itertools import combinations
import math

import bpy
import bmesh
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
from io_scene_fbx import parse_fbx


LODKEY = ("main", "_LOD1", "_LOD2")
ROOMS = [i for i in range(25) if i not in (0, 4, 20, 24)]
UP = (0.0, 0.0, 1.0)
DOWN = (0.0, 0.0, -1.0)

DISTANCE_TOL = 0.00025
AREA_TOL = 0.000025


def area2d(p):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(p, p[1:] + p[:1])) / 2.0


def cross3(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])


def is_convex(p):
    return all(cross3(p[i - 1], p[i], p[(i + 1) % len(p)]) >= -1e-9 for i in range(len(p)))


def ear_clip(p):
    """Clip a simple 2D polygon into CCW triangles."""
    idx, tris = list(range(len(p))), []
    while len(idx) > 3:
        n = len(idx)
        for k in range(n):
            a, b, c = p[idx[k - 1]], p[idx[k]], p[idx[(k + 1) % n]]
            if cross3(a, b, c) <= 1e-12:
                continue
            if any(
                cross3(a, b, p[j]) > 1e-12 and cross3(b, c, p[j]) > 1e-12 and cross3(c, a, p[j]) > 1e-12
                for j in idx
                if j not in (idx[k - 1], idx[k], idx[(k + 1) % n])
            ):
                continue
            tris.append([a, b, c])
            idx.pop(k)
            break
        else:
            idx.pop(min(range(n), key=lambda k: abs(cross3(p[idx[k - 1]], p[idx[k]], p[idx[(k + 1) % n]]))))
    tris.append([p[i] for i in idx])
    return tris


def clip_poly(poly, axis, value, keep_above):
    """Sutherland-Hodgman half-plane clip on a 2D polygon."""
    out = []
    for i in range(len(poly)):
        cur, prev = poly[i], poly[i - 1]
        cin = cur[axis] >= value - 1e-9 if keep_above else cur[axis] <= value + 1e-9
        pin = prev[axis] >= value - 1e-9 if keep_above else prev[axis] <= value + 1e-9
        if cin != pin:
            t = (value - prev[axis]) / (cur[axis] - prev[axis])
            out.append((prev[0] + t * (cur[0] - prev[0]), prev[1] + t * (cur[1] - prev[1])))
        if cin:
            out.append(cur)
    clean = []
    for q in out:
        if not clean or abs(q[0] - clean[-1][0]) + abs(q[1] - clean[-1][1]) > 1e-6:
            clean.append(q)
    if len(clean) > 1 and abs(clean[0][0] - clean[-1][0]) + abs(clean[0][1] - clean[-1][1]) <= 1e-6:
        clean.pop()
    return clean


def newell(points):
    center = points[0]
    offsets = [p - center for p in points]
    normal = Vector((0.0, 0.0, 0.0))
    for a, b in zip(offsets, offsets[1:] + offsets[:1]):
        normal += a.cross(b)
    return normal


class TileMesh:
    """Clips polygons onto atlas tile cells at true real-world metre scale (lot-centred coordinates)."""

    def __init__(self, lod: int, layout: dict):
        self.lod = lod
        self.lodkey = LODKEY[lod]
        self.layout = layout
        self.vertices = []
        self.faces = []
        self.uvs = []
        self.lookup = {}

    def _add(self, pts, uv):
        ids, uvs = [], []
        for p, t in zip(pts, uv):
            key = tuple(round(c, 5) for c in p)
            if key not in self.lookup:
                self.lookup[key] = len(self.vertices)
                self.vertices.append(tuple(p))
            i = self.lookup[key]
            if ids and ids[-1] == i:
                continue
            ids.append(i)
            uvs.append(t)
        if len(ids) > 2 and ids[0] == ids[-1]:
            ids.pop()
            uvs.pop()
        if len(set(ids)) >= 3 and len(set(ids)) == len(ids):
            self.faces.append(ids)
            self.uvs.append(uvs)

    def polygon(self, points, direction, material, room=None):
        pts = [Vector(p) for p in points]
        nrm = newell(pts)
        if nrm.length < 1e-9:
            raise ValueError(f"Degenerate face {points}")
        if nrm.dot(Vector(direction)) < 0:
            pts.reverse()
            nrm.negate()
        n = nrm.normalized()
        if room is not None:
            tangent = Vector((0.0, 0.0, 1.0)).cross(n).normalized()
            xs = [p.dot(tangent) for p in pts]
            zs = [p.z for p in pts]
            ext = max(1e-4, max(max(xs) - min(xs), max(zs) - min(zs)))
            u, v = 0.1 + (room % 5) * 0.2, 0.1 + (room // 5) * 0.2
            mx, mz = (max(xs) + min(xs)) / 2.0, (max(zs) + min(zs)) / 2.0
            self._add(pts, [(u + 0.148 * (a - mx) / ext, v + 0.148 * (b - mz) / ext) for a, b in zip(xs, zs)])
            return

        u = Vector((1.0, 0.0, 0.0)) if Vector((n.x, n.y, 0.0)).length < 1e-4 else Vector((0.0, 0.0, 1.0)).cross(n).normalized()
        v = n.cross(u)
        d = sum(p.dot(n) for p in pts) / len(pts)
        if len(pts) > 3 and max(abs(p.dot(n) - d) for p in pts) > 2e-4:
            for i in range(1, len(pts) - 1):
                self.polygon([pts[0], pts[i], pts[i + 1]], n, material)
            return

        flat = [(p.dot(u), p.dot(v)) for p in pts]
        ou, ov = (min(a for a, _ in flat), min(b for _, b in flat)) if self.lodkey == "_LOD2" else (0.0, 0.0)
        flat = [(a - ou, b - ov) for a, b in flat]
        cell = self.layout["lods"][self.lodkey][material]
        u0, v0, u1, v1 = cell["uv"]
        mw, mh = cell["metres"]

        for piece in ([flat] if is_convex(flat) else ear_clip(flat)):
            s = [q[0] for q in piece]
            t = [q[1] for q in piece]
            for i in range(math.floor(min(s) / mw + 1e-7), math.ceil(max(s) / mw - 1e-7)):
                col = clip_poly(clip_poly(piece, 0, i * mw, True), 0, (i + 1) * mw, False)
                if len(col) < 3:
                    continue
                for j in range(math.floor(min(t) / mh + 1e-7), math.ceil(max(t) / mh - 1e-7)):
                    part = clip_poly(clip_poly(col, 1, j * mh, True), 1, (j + 1) * mh, False)
                    if len(part) < 3 or area2d(part) < 1e-6:
                        continue
                    span = max(max(q[axis] for q in part) - min(q[axis] for q in part) for axis in (0, 1))
                    if area2d(part) < span * 0.000019:
                        continue
                    self._add(
                        [(a + ou) * u + (b + ov) * v + d * n for a, b in part],
                        [
                            (
                                u0 + min(1.0, max(0.0, (a - i * mw) / mw)) * (u1 - u0),
                                v0 + min(1.0, max(0.0, (b - j * mh) / mh)) * (v1 - v0),
                            )
                            for a, b in part
                        ],
                    )

    def to_object(self, name: str, material=None):
        data = bpy.data.meshes.new(name)
        data.from_pydata(self.vertices, [], self.faces)
        data.update()
        layer = data.uv_layers.new(name="UVMap")
        for poly, uv in zip(data.polygons, self.uvs):
            for index, coord in zip(poly.loop_indices, uv):
                layer.data[index].uv = coord
        if material is not None:
            data.materials.append(material)
        ob = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(ob)
        return ob


def room_for_pane(pts) -> int:
    """Deterministic room index from pane centroid so LOD0/1/2 always show the same interior."""
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    cz = sum(p[2] for p in pts) / len(pts)
    key = abs(int(round(cx * 10)) * 7919 + int(round(cy * 10)) * 104729 + int(round(cz * 10)) * 31)
    return ROOMS[key % len(ROOMS)]


def build_tiled_meshes(body_mesh, win_mesh, lod: int, layout: dict, strict_mats: set[str] | None = None):
    """Pour pure-Python (body_mesh, win_mesh) into (TileMesh body, TileMesh windows)."""
    lod_key = LODKEY[lod]
    cells = layout["lods"][lod_key]
    allowed = strict_mats if strict_mats is not None else set(cells.keys())

    t_body = TileMesh(lod, layout)
    t_win = TileMesh(lod, layout)

    bad_mats = {}
    for f, mat_idx in zip(body_mesh.f, body_mesh.m):
        mat = body_mesh.mats[mat_idx]
        if mat not in allowed or mat not in cells:
            bad_mats[mat] = bad_mats.get(mat, 0) + 1
            continue
        pts = [Vector(body_mesh.v[i]) for i in f]
        n = newell(pts)
        if n.length < 1e-9:
            continue
        try:
            t_body.polygon(pts, n.normalized(), mat)
        except ValueError:
            pass
    if bad_mats:
        raise ValueError(f"LOD{lod}: unknown material(s) not in atlas: {bad_mats}")

    for f in win_mesh.f:
        pts = [Vector(win_mesh.v[i]) for i in f]
        n = newell(pts)
        if n.length < 1e-9:
            continue
        nn = n.normalized()
        if abs(nn.z) > 0.9:
            continue
        try:
            t_win.polygon(pts, nn, "Glass", room=room_for_pane(pts))
        except ValueError:
            pass

    return t_body, t_win


def optimize_far(ob, lod: int):
    if lod != 2 or not len(ob.data.polygons):
        return ob
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.dissolve_limit(
        bm,
        angle_limit=0.00001,
        use_dissolve_boundaries=False,
        verts=list(bm.verts),
        edges=list(bm.edges),
        delimit={"UV"},
    )
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return ob


def smooth_export(obj):
    mesh = obj.data
    for p in mesh.polygons:
        p.use_smooth = True
    mesh.set_sharp_from_angle(angle=math.radians(40))
    mesh.update()


def export_fbx(ob, path):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(
        filepath=str(path),
        use_selection=True,
        object_types={"MESH"},
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_NONE",
        axis_forward="-Z",
        axis_up="Y",
        bake_space_transform=True,
        mesh_smooth_type="EDGE",
        add_leaf_bones=False,
        path_mode="STRIP",
        embed_textures=False,
    )


def _pieces(points):
    if area2d(points) < 0:
        points = points[::-1]
    if is_convex(points):
        return [points]
    return [
        [points[v] if isinstance(v, int) else tuple(v[:2]) for v in t]
        for t in tessellate_polygon([[Vector((*q, 0.0)) for q in points]])
    ]


def _intersect2d(subject, clip):
    if area2d(clip) < 0:
        clip = clip[::-1]
    result = subject
    for i, b in enumerate(clip):
        a = clip[i - 1]
        previous = result
        result = []
        if not previous:
            break
        for j, q in enumerate(previous):
            p = previous[j - 1]
            margin = 0.000035 * math.hypot(b[0] - a[0], b[1] - a[1])
            s, t = cross3(a, b, p) - margin, cross3(a, b, q) - margin
            if (s >= 0) != (t >= 0):
                k = s / (s - t)
                result.append((p[0] + k * (q[0] - p[0]), p[1] + k * (q[1] - p[1])))
            if t >= 0:
                result.append(q)
    return abs(area2d(result)) if len(result) > 2 else 0.0


def overlaps(obj):
    """Detect coplanar same-facing body polygons whose overlap exceeds AREA_TOL."""
    positions = [obj.matrix_world @ v.co for v in obj.data.vertices]
    basis = obj.matrix_world.to_3x3().inverted().transposed()
    groups = defaultdict(list)
    for poly in obj.data.polygons:
        pts = [positions[i] for i in poly.vertices]
        n = (basis @ poly.normal).normalized()
        if n.length_squared < 0.9:
            continue
        axis = max(range(3), key=lambda i: abs(n[i]))
        other = [i for i in range(3) if i != axis]
        points = [(p[other[0]], p[other[1]]) for p in pts]
        lo, hi = min(p[0] for p in points), max(p[0] for p in points)
        bottom, top = min(p[1] for p in points), max(p[1] for p in points)
        groups[(axis, n[axis] > 0)].append((lo, hi, bottom, top, n, n.dot(pts[0]), poly.index, points, pts))

    violations = []
    for group in groups.values():
        active = []
        for entry in sorted(group, key=lambda e: e[0]):
            lo, hi, bottom, top, n, d, idx, points, pts = entry
            active = [prior for prior in active if prior[1] > lo + 0.00002]
            for x0, x1, y0, y1, n2, d2, idx2, poly, pts2 in active:
                if min(top, y1) - max(bottom, y0) <= 0.00002 or n.dot(n2) < 0.9999998:
                    continue
                if abs(d - d2) > 0.006:
                    continue
                if max(abs(n.dot(p) - d) for p in pts2) > DISTANCE_TOL:
                    continue
                if max(abs(n2.dot(p) - d2) for p in pts) > DISTANCE_TOL:
                    continue
                area = sum(_intersect2d(a, b) for a in _pieces(points) for b in _pieces(poly))
                if area > AREA_TOL:
                    violations.append(
                        {
                            "faces": [idx2, idx],
                            "overlap_m2": round(area, 6),
                            "normal": [round(x, 3) for x in n],
                            "point": [round(x, 4) for x in pts[0]],
                        }
                    )
            active.append(entry)
    return violations


def _fbx_children(node, key):
    return [n for n in node.elems if n.id == key]


def _fbx_properties(node):
    parts = _fbx_children(node, b"Properties70")
    return {p.props[0]: p.props[4:] for part in parts for p in part.elems}


def verify_raw_fbx(path, bounds):
    """Inspect exported FBX binary/ASCII node data directly without Blender re-import."""
    tree, _ = parse_fbx.parse(str(path))
    (header,) = _fbx_children(tree, b"GlobalSettings")
    assert _fbx_properties(header)[b"UnitScaleFactor"] == [1.0], str(path)
    (nodes,) = _fbx_children(tree, b"Objects")
    (model,) = _fbx_children(nodes, b"Model")
    (geometry,) = _fbx_children(nodes, b"Geometry")
    assert model.props[2] == b"Mesh", str(path)
    values = _fbx_properties(model)
    for key, expected in (
        (b"Lcl Translation", 0),
        (b"Lcl Rotation", 0),
        (b"Lcl Scaling", 1),
        (b"GeometricTranslation", 0),
        (b"GeometricRotation", 0),
        (b"GeometricScaling", 1),
        (b"PreRotation", 0),
        (b"PostRotation", 0),
    ):
        assert all(abs(x - expected) < 1e-6 for x in values.get(key, [expected] * 3)), (str(path), key, values.get(key))
    (vert,) = _fbx_children(geometry, b"Vertices")
    v = vert.props[0]
    if v:
        raw = [v[0::3], v[2::3], v[1::3]]
        low = [min(raw[0]), -max(raw[1]), min(raw[2])]
        high = [max(raw[0]), -min(raw[1]), max(raw[2])]
        assert max(abs(cm - m * 100.0) for pair, ref in zip((low, high), bounds) for cm, m in zip(pair, ref)) < 0.01, (
            str(path),
            low,
            high,
            bounds,
        )
    return {"units": "centimetres", "model_transform": "identity"}


def atlas_partition(layout: dict, lod_key: str):
    tiles = {name: tuple(cell["uv"]) for name, cell in layout["lods"][lod_key].items()}
    for (k, (l, b, r, t)), (j, (ll, bb, rr, tt)) in combinations(tiles.items(), 2):
        assert min(r, rr) <= max(l, ll) or min(t, tt) <= max(b, bb), (lod_key, k, j, "overlapping material tiles")
    buckets = {}
    for key, rect in tiles.items():
        l, b, r, t = rect
        for u in range(int(l * 7), int(r * 7) + 1):
            for v in range(int(b * 7), int(t * 7) + 1):
                buckets.setdefault((u, v), []).append((key, rect))
    return buckets


def material_uvs(obj, buckets: dict):
    """Verify every polygon's UVs lie strictly within exactly one atlas tile rectangle."""
    uv = obj.data.uv_layers.active.data
    names = {}
    eps = 2e-6
    for f in obj.data.polygons:
        us, vs = zip(*(tuple(uv[i].uv) for i in f.loop_indices))
        l, r, b, t = min(us), max(us), min(vs), max(vs)
        owners = [
            n
            for n, (a0, b0, a1, b1) in buckets.get((int((l + r) * 3.5), int((b + t) * 3.5)), ())
            if a0 - eps <= l and r <= a1 + eps and b0 - eps <= b and t <= b1 + eps
        ]
        assert len(owners) == 1, (obj.name, f.index, "material UV outside single tile", l, b, r, t, owners)
        tag = owners[0]
        names[tag] = names.get(tag, 0) + 1
    return sorted(names)
