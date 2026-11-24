"""New France builder: five 1x3 pilot buildings, real-scale tiled textures, LOD0/1/2 + _Win meshes, FBX round-trip check.

Kit and conventions come from GPT's New Holland build.py (Mesh/Face/Opening/House, room-grid windows, export settings).
What is new:
  * tile-clipped UVs: every face is cut on the atlas cell's real-world grid (atlas_layout.json from nf_atlas.py), so
    a 15 m wall shows brick at true size instead of one cell stretched over the whole wall
  * New France kit: mansard, firewall, dormer (segmental / pediment), iron stair, gallery, pavilion + lantern, bellcast hip
Coordinates: Blender metres, lot centred, street edge at y = -12 (front = -Y). Specs from GPT use lot X 0..8 / Y 0..24
from the front-left corner, converted with X() and Y().
Run: blender -b --factory-startup -P nf_build.py
"""
import json, math, sys
from dataclasses import dataclass
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
LAYOUT = json.loads((HERE / "atlas_layout.json").read_text())
LODKEY = ("main", "_LOD1", "_LOD2")
LOT_D = 6                   # lot depth in cells; models are built in the old 1x3 frame and moved forward at export
YSHIFT = -(LOT_D * 4.0 - 12.0)
OWNER = f"NA_NewFrancePlex_L1_1x{LOT_D}"
MAPS = ("BaseColor", "Normal", "MaskMap", "ControlMask", "Emissive")
ROOMS = [i for i in range(25) if i not in (0, 4, 20, 24)]
UP, DOWN = (0, 0, 1), (0, 0, -1)
REMAP = {}
W = 8.0
XMAP = None                 # optional widening map (spec x -> spec x) for the near-touching low-density houses
LACE_K = 1.0                # lace motif spacing multiplier (round 5: broad motifs, GPT's budget note)
LITE = 0                    # budget fallback level (round 4/5): 1 = lighter iron and louvres, 2 = lightest
def X(a): return (XMAP(a) if XMAP else a) - W / 2
def Y(b): return b - 12.0

# ------------------------------------------------------------------ 2D helpers for the tile clipper
def area2d(p): return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(p, p[1:] + p[:1])) / 2
def cross3(a, b, c): return (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])

def is_convex(p):
    return all(cross3(p[i - 1], p[i], p[(i + 1) % len(p)]) >= -1e-9 for i in range(len(p)))

def ear_clip(p):
    """CCW simple polygon -> triangles"""
    idx, tris = list(range(len(p))), []
    while len(idx) > 3:
        n = len(idx)
        for k in range(n):
            a, b, c = p[idx[k - 1]], p[idx[k]], p[idx[(k + 1) % n]]
            if cross3(a, b, c) <= 1e-12:
                continue
            if any(cross3(a, b, p[j]) > 1e-12 and cross3(b, c, p[j]) > 1e-12 and cross3(c, a, p[j]) > 1e-12
                   for j in idx if j not in (idx[k - 1], idx[k], idx[(k + 1) % n])):
                continue
            tris.append([a, b, c]); idx.pop(k); break
        else:                                   # only degenerate corners left: drop the flattest one
            idx.pop(min(range(n), key=lambda k: abs(cross3(p[idx[k - 1]], p[idx[k]], p[idx[(k + 1) % n]]))))
    tris.append([p[i] for i in idx])
    return tris

def clip(poly, axis, value, keep_above):
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
    center=points[0]
    offsets=[p-center for p in points]
    normal=Vector((0,0,0))
    for a,b in zip(offsets,offsets[1:]+offsets[:1]):
        normal+=a.cross(b)
    return normal

def projected_area(points):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1])) / 2

# ------------------------------------------------------------------ mesh
class Mesh:
    def __init__(self, lod):
        self.lodkey = LODKEY[lod]
        self.vertices, self.faces, self.uvs, self.lookup = [], [], [], {}

    def _add(self, pts, uv):
        ids, uvs = [], []
        for p, t in zip(pts, uv):
            key = tuple(round(c, 5) for c in p)
            if key not in self.lookup:
                self.lookup[key] = len(self.vertices); self.vertices.append(tuple(p))
            i = self.lookup[key]
            if ids and ids[-1] == i:
                continue
            ids.append(i); uvs.append(t)
        if len(ids) > 2 and ids[0] == ids[-1]:
            ids.pop(); uvs.pop()
        if len(set(ids)) >= 3 and len(set(ids)) == len(ids):
            self.faces.append(ids); self.uvs.append(uvs)

    def polygon(self, points, direction, material, room=None):
        material = material[1:] if material.startswith("=") else REMAP.get(material, material)   # '=' pins a colour (foliage)
        pts = [Vector(p) for p in points]
        nrm = newell(pts)
        if nrm.length < 1e-9:
            raise ValueError(f"Degenerate face {points}")
        if nrm.dot(Vector(direction)) < 0:
            pts.reverse(); nrm.negate()
        n = nrm.normalized()
        if room is not None:                            # GPT's room-grid window UVs
            tangent = Vector((0, 0, 1)).cross(n).normalized()
            xs = [p.dot(tangent) for p in pts]; zs = [p.z for p in pts]
            ext = max(max(xs) - min(xs), max(zs) - min(zs))
            u, v = .1 + room % 5 * .2, .1 + room // 5 * .2
            mx, mz = (max(xs) + min(xs)) / 2, (max(zs) + min(zs)) / 2
            self._add(pts, [(u + .148 * (a - mx) / ext, v + .148 * (b - mz) / ext) for a, b in zip(xs, zs)])
            return
        u = Vector((1, 0, 0)) if Vector((n.x, n.y, 0)).length < 1e-4 else Vector((0, 0, 1)).cross(n).normalized()
        v = n.cross(u)                                  # walls: u along the wall, v straight up; roofs: v up the slope
        d = sum(p.dot(n) for p in pts) / len(pts)
        if len(pts) > 3 and max(abs(p.dot(n) - d) for p in pts) > 2e-4:  # not flat: fan it
            for i in range(1, len(pts) - 1):
                self.polygon([pts[0], pts[i], pts[i + 1]], n, material)
            return
        flat = [(p.dot(u), p.dot(v)) for p in pts]
        # Far atlas keeps its metre scale; put the repeat origin at the face minimum
        # to avoid needless tile seams through tiny details at world zero.
        ou, ov = (min(a for a,b in flat), min(b for a,b in flat)) if self.lodkey == '_LOD2' else (0,0)
        flat = [(a-ou,b-ov) for a,b in flat]
        cell = LAYOUT["lods"][self.lodkey][material]
        u0, v0, u1, v1 = cell["uv"]; mw, mh = cell["metres"]
        for piece in ([flat] if is_convex(flat) else ear_clip(flat)):
            s = [q[0] for q in piece]; t = [q[1] for q in piece]
            for i in range(math.floor(min(s) / mw + 1e-7), math.ceil(max(s) / mw - 1e-7)):
                col = clip(clip(piece, 0, i * mw, True), 0, (i + 1) * mw, False)
                if len(col) < 3:
                    continue
                for j in range(math.floor(min(t) / mh + 1e-7), math.ceil(max(t) / mh - 1e-7)):
                    part = clip(clip(col, 1, j * mh, True), 1, (j + 1) * mh, False)
                    if len(part) < 3 or area2d(part) < 1e-6:
                        continue
                    span=max(max(v[axis] for v in part)-min(v[axis] for v in part) for axis in (0,1))
                    if area2d(part)<span*.000019:
                        continue
                    self._add([(a+ou) * u + (b+ov) * v + d * n for a, b in part],
                              [(u0 + min(1, max(0, (a - i * mw) / mw)) * (u1 - u0),
                                v0 + min(1, max(0, (b - j * mh) / mh)) * (v1 - v0)) for a, b in part])

    def box(self, x0, x1, y0, y1, z0, z1, material, top=None, bottom=True):
        if min(x1 - x0, y1 - y0, z1 - z0) < 1e-5:
            return
        ring = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        if bottom:
            self.polygon([(x, y, z0) for x, y in ring], DOWN, material)
        self.polygon([(x, y, z1) for x, y in ring], UP, top or material)
        for a, b in zip(ring, ring[1:] + ring[:1]):
            Face(a, b).quad(self, 0, Face(a, b).length, z0, z1, 0, material)

    def object(self, name, material=None):
        data = bpy.data.meshes.new(name)
        data.from_pydata([(v[0], v[1] + YSHIFT, v[2]) for v in self.vertices], [], self.faces)
        data.update()
        layer = data.uv_layers.new(name="UVMap")
        for poly, uv in zip(data.polygons, self.uvs):
            for index, coord in zip(poly.loop_indices, uv):
                layer.data[index].uv = coord
        if material:
            data.materials.append(material)
        ob = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(ob)
        return ob

# ------------------------------------------------------------------ walls and openings
@dataclass
class Opening:
    center: float
    width: float
    bottom: float
    top: float
    kind: str = "sash"          # sash, pair, small, door, french, shop, shopdoor
    shutter: str = None
    stone: bool = True
    shutter_w: float = None     # set by the builder when neighbours leave less room than the default

    @property
    def left(self): return self.center - self.width / 2
    @property
    def right(self): return self.center + self.width / 2


class Face:
    def __init__(self, a, b):
        self.a = Vector((*a, 0))
        axis = Vector((*b, 0)) - self.a
        self.length = axis.length
        self.tangent = axis.normalized()
        self.out = self.tangent.cross(Vector(UP))

    def point(self, x, z, depth=0):
        return self.a + x * self.tangent + z * Vector(UP) + depth * self.out

    def quad(self, mesh, a, b, low, high, depth, material, room=None):
        if b - a < 1e-5 or high - low < 1e-5:
            return
        p = self.point
        mesh.polygon([p(a, low, depth), p(b, low, depth), p(b, high, depth), p(a, high, depth)], self.out, material, room)

    def trim(self, mesh, a, b, low, high, near, far, material):
        if min(b - a, high - low, far - near) < 1e-5:
            return
        self.quad(mesh, a, b, low, high, far, material)
        p = self.point
        for x, n in ((a, -self.tangent), (b, self.tangent)):
            mesh.polygon([p(x, low, near), p(x, low, far), p(x, high, far), p(x, high, near)], n, material)
        for z, n in ((low, DOWN), (high, UP)):
            mesh.polygon([p(a, z, near), p(a, z, far), p(b, z, far), p(b, z, near)], n, material)

    def wall(self, house, low, high, openings, material):
        mesh = house.body
        if house.lod == 2:
            self.quad(mesh, 0, self.length, low, high, 0, material)
        else:
            cuts = sorted({low, high, *(v for o in openings for v in (o.bottom, o.top))})
            for z0, z1 in zip(cuts, cuts[1:]):
                mid = (z0 + z1) / 2
                x = 0
                for o in sorted((o for o in openings if o.bottom < mid < o.top), key=lambda o: o.left):
                    self.quad(mesh, x, o.left, z0, z1, 0, material)
                    x = o.right
                self.quad(mesh, x, self.length, z0, z1, 0, material)
        for o in openings:
            house.opening(self, o, material)


class House:
    def __init__(self, lod):
        self.lod = lod
        self.body, self.windows = Mesh(lod), Mesh(lod)
        self.doors, self.panes = [], 0
        self.frame, self.door, self.shop, self.sill, self.lintel = "Cream", "Green", "Green", "Dressed", True

    def pane(self, f, a, b, z, t, d):
        """room cell from the pane's place on the building (not creation order), so every LOD shows the same room"""
        c = f.point((a + b) / 2, z)
        key = int(round(c.x * 10)) * 7919 + int(round(c.y * 10)) * 104729 + int(round(z * 10)) * 31
        f.quad(self.windows, a, b, z, t, d, "Cream", room=ROOMS[key % len(ROOMS)])
        self.panes += 1

    def opening(self, f, o, reveal):
        m, lod = self.body, self.lod
        fine = lod == 0 and LITE < 6                          # LITE 6: no panel, keystone or architrave detail
        bare = LITE >= 6 and lod == 1                         # LITE 6 near: frames only
        if o.kind == "void":                                  # round 4: a hole only (recesses, notches)
            return
        a, b, z, t = o.left, o.right, o.bottom, o.top
        d = .018 if lod == 2 else -.12
        p = f.point
        if lod != 2:
            for x, n in ((a, f.tangent), (b, -f.tangent)):
                m.polygon([p(x, z, 0), p(x, z, d), p(x, t, d), p(x, t, 0)], n, reveal)
            for hgt, n in ((z, UP), (t, DOWN)):
                m.polygon([p(a, hgt, 0), p(b, hgt, 0), p(b, hgt, d), p(a, hgt, d)], n, reveal)
        k = o.kind
        frame = self.shop if k in ("shop", "shopdoor") else self.frame
        bar = .075 if k in ("shop", "shopdoor") else .06
        if k in ("door", "french", "shopdoor"):
            self.doors.append([round(c, 4) for c in p(o.center, z, 0)])
        if k == "door":
            leaf_top = t - .42 if t - z > 2.25 else t
            f.quad(m, a, b, z, leaf_top, d, self.door)
            if leaf_top < t:
                self.pane(f, a, b, leaf_top, t, d)
            if fine:
                for lo, hi in ((.12, .42), (.52, .92)):
                    f.trim(m, a + .14, b - .14, z + lo * (leaf_top - z), z + hi * (leaf_top - z), d, d + .025, self.door)
                if leaf_top < t:                                  # sunburst fanlight muntins
                    cx, r = o.center, min((b - a) / 2 - .06, t - leaf_top - .06)
                    for ang in (20, 55, 90, 125, 160):
                        c, s_ = math.cos(math.radians(ang)), math.sin(math.radians(ang))
                        nx, nz = -s_ * .014, c * .014
                        pts = [p(cx + nx, leaf_top + nz, d + .03), p(cx - nx, leaf_top - nz, d + .03),
                               p(cx + c * r - nx, leaf_top + s_ * r - nz, d + .03), p(cx + c * r + nx, leaf_top + s_ * r + nz, d + .03)]
                        m.polygon(pts, f.out, self.frame)
        elif k in ("french", "shopdoor"):
            panel = z + (.42 if k == "french" else .62)
            f.quad(m, a, b, z, panel, d, self.door if k == "french" else self.shop)
            self.pane(f, a, b, panel, t, d)
            if fine:
                for x0, x1 in ((a + .10, o.center - .08), (o.center + .08, b - .10)):
                    f.trim(m, x0, x1, z + .09, panel - .08, d, d + .022, self.door if k == "french" else self.shop)
        else:
            self.pane(f, a, b, z, t, d)
        if lod == 2:
            return
        if k != "door":                                       # frames
            for x in (a, b - bar):
                f.trim(m, x, x + bar, z, t, d, d + .055, frame)
            for hgt in (z, t - bar):
                f.trim(m, a, b, hgt, hgt + bar, d, d + .055, frame)
        else:
            for x in (a, b - bar):
                f.trim(m, x, x + bar, z, t, d, d + .045, frame)
            f.trim(m, a, b, t - bar, t, d, d + .045, frame)
            if t - z > 2.25:
                f.trim(m, a, b, t - .42 - bar / 2, t - .42 + bar / 2, d, d + .05, frame)
        if bare:
            return
        if k in ("sash", "pair", "small"):
            meet = (z + t) / 2
            if k != "small":
                f.trim(m, a, b, meet - bar / 2, meet + bar / 2, d, d + .058, frame)
            if k == "pair":
                f.trim(m, o.center - .05, o.center + .05, z, t, d, d + .062, frame)
            elif fine:
                f.trim(m, o.center - .02, o.center + .02, z, t, d, d + .061, frame)
        if k in ("french", "shopdoor"):
            f.trim(m, o.center - .035, o.center + .035, z, t, d, d + .058, frame)
            f.trim(m, a, b, t - .45, t - .45 + bar, d, d + .058, frame)
        if k == "shop":
            f.trim(m, a, b, z + (t - z) * .78, z + (t - z) * .78 + bar, d, d + .058, frame)
        if o.stone and self.sill and k in ("sash", "pair", "small", "french"):
            if k != "french":
                f.trim(m, a - .08, b + .08, z - .09, z, 0, .08, self.sill)
            if self.lintel:
                f.trim(m, a - .10, b + .10, t, t + .20, 0, .035, self.sill)
                if fine and k in ("sash", "pair", "french"):        # keystone
                    f.trim(m, o.center - .09, o.center + .09, t - .04, t + .25, 0, .065, self.sill)
            if fine and not o.shutter and k != "small":             # architrave
                for x0 in (a - .09, b):
                    f.trim(m, x0, x0 + .09, z, t, 0, .028, self.sill)
        if o.shutter and not (lod == 1 and LITE >= 2) and not (LITE >= 3 and k != "french"):
            sw = o.shutter_w if o.shutter_w is not None else min(.55, o.width / 2)
            if sw >= .2:
                for x0, x1 in ((a - .03 - sw, a - .03), (b + .03, b + .03 + sw)):
                    f.trim(m, x0, x1, z, t, 0, .04, o.shutter)
                    if fine:                                        # raised panels (louvred upper on tall leaves)
                        mid = z + (t - z) * .42
                        f.trim(m, x0 + .055, x1 - .055, z + .07, mid - .035, .04, .055, o.shutter)
                        f.trim(m, x0 + .055, x1 - .055, mid + .035, t - .07, .04, .055, o.shutter)
                        if t - z > 1.6 and LITE < 2:
                            n = int((t - .07 - mid - .035) / (.16 if not LITE else .3))
                            for i in range(1, n):
                                zz = mid + .035 + i * .16
                                f.trim(m, x0 + .07, x1 - .07, zz - .012, zz + .012, .055, .066, o.shutter)

# ------------------------------------------------------------------ kit
def rectangle(l, r, f, b): return [(l, f), (r, f), (r, b), (l, b)]
def edges(plan): return [Face(a, b) for a, b in zip(plan, plan[1:] + plan[:1])]

def extrude(mesh, prof, axis, a0, a1, mats, caps=(None, None)):
    """Closed prism; signed profile winding also handles concave arcade spandrels."""
    P = (lambda a,p,q:(a,p,q)) if axis=='x' else (lambda a,p,q:(p,a,q))
    sign = 1 if area2d(prof)>0 else -1
    for i in range(len(prof)):
        (p0,q0),(p1,q1)=prof[i],prof[(i+1)%len(prof)]
        mat=mats[i] if isinstance(mats,(list,tuple)) else mats
        if not mat or abs(p1-p0)+abs(q1-q0)<1e-6: continue
        nx,ny=sign*(q1-q0),sign*-(p1-p0)
        mesh.polygon([P(a0,p0,q0),P(a1,p0,q0),P(a1,p1,q1),P(a0,p1,q1)],
                     (0,nx,ny) if axis=='x' else (nx,0,ny),mat)
    for a,sgn,mat in [(a0,-1,caps[0]),(a1,1,caps[1])]:
        if mat: mesh.polygon([P(a,p,q) for p,q in prof],(sgn,0,0) if axis=='x' else (0,sgn,0),mat)

def bar(mesh, axis, p0, q0, p1, q1, a0, a1, th, mat):
    """sloped bar/stringer/ramp: the line (p0,q0)-(p1,q1) with depth th below it, extruded a0..a1"""
    extrude(mesh, [(p0, q0 - th), (p1, q1 - th), (p1, q1), (p0, q0)], axis, a0, a1, mat, (mat, mat))

def offset_plan(plan, dists):
    """move each edge of a convex CCW plan outward by its own distance"""
    lines = []
    for (ax, ay), (bx, by), dd in zip(plan, plan[1:] + plan[:1], dists):
        L = math.hypot(bx - ax, by - ay); nx, ny = (by - ay) / L, -(bx - ax) / L
        lines.append(((ax + nx * dd, ay + ny * dd), (bx - ax, by - ay)))
    pts = []
    for (p, r), (q, s) in zip(lines[-1:] + lines[:-1], lines):
        den = r[0] * s[1] - r[1] * s[0]
        t = ((q[0] - p[0]) * s[1] - (q[1] - p[1]) * s[0]) / den
        pts.append((p[0] + t * r[0], p[1] + t * r[1]))
    return pts

def prism(mesh, plan, z0, z1, mat, bottom=True):
    mesh.polygon([(x, y, z1) for x, y in plan], UP, mat)
    if bottom:
        mesh.polygon([(x, y, z0) for x, y in plan], DOWN, mat)
    for f in edges(plan):
        f.quad(mesh, 0, f.length, z0, z1, 0, mat)

def profile_z(prof, y):
    for (a, v), (b, w) in zip(prof, prof[1:]):
        if a - 1e-6 <= y <= b + 1e-6 and b > a:
            return v + (w - v) * (y - a) / (b - a)
    raise ValueError(y)

def profile_y(prof, z):
    for (a, v), (b, w) in zip(prof, prof[1:]):
        if v - 1e-6 <= z <= w + 1e-6 and w > v:
            return a + (b - a) * (z - v) / (w - v)
    return prof[-1][0]

def mansard(h, x0, x1, yf, yb, eave, angle, brk, ridge, ridge_y, roof, end, oh=.22, caps=True):
    run = (brk - eave) / math.tan(math.radians(angle))
    prof = [(yf - oh, eave), (yf - oh + run, brk), (ridge_y, ridge), (yb + oh - run, brk), (yb + oh, eave)]
    extrude(h.body, prof, "x", x0, x1, [roof, roof, roof, roof, end], (end, end) if caps else (None, None))
    return prof

def firewall(h, prof, x0, x1, side, front_mat, coping="Dressed", rise=.24):
    (yf, eave), (yb, _) = prof[0], prof[-1]
    fw = [(yf, eave), (yf, eave + rise)] + [(y, z + rise) for y, z in prof[1:-1]] + [(yb, eave + rise), (yb, eave)]
    mats = [front_mat] + [coping] * (len(fw) - 3) + [side, side]
    extrude(h.body, fw, "x", x0, x1, mats, (side, side))

def dormer(h, xc, w, wh, prof, kind, roof, cheek, face):
    """dormer on the front roof slope; prof = the front slope (y,z) points from its eave upward"""
    m, lod = h.body, h.lod
    yd = prof[0][0] + .04
    zb = profile_z(prof, yd)
    sill = zb + .10; top = sill + wh; zde = top + .14
    half, oh = w / 2 + .20, .08
    if kind == "pediment":
        cap = [(-half - oh, 0), (0, (half + oh) * math.tan(math.radians(36))), (half + oh, 0)]
    else:
        n = 6 if lod < 2 else 3
        rise = .14 * (2 * half)
        cap = [(-(half + oh) * math.cos(math.pi * i / n), rise * math.sin(math.pi * i / n)) for i in range(n + 1)]
    peak = zde + max(z for _, z in cap)
    yend = profile_y(prof, peak) + .05
    front = Face((xc - half, yd), (xc + half, yd))
    front.wall(h, zb, zde, [Opening(half, w, sill, top, "sash", stone=False)], face)
    m.polygon([(xc + x, yd, zde + z) for x, z in cap], (0, -1, 0), face)          # tympanum
    for (xa, za), (xb, zb2) in zip(cap, cap[1:]):
        quad = [(xc + xa, yd - oh, zde + za), (xc + xb, yd - oh, zde + zb2), (xc + xb, yend, zde + zb2), (xc + xa, yend, zde + za)]
        m.polygon(quad, (-(zb2 - za), 0, xb - xa), roof)
        m.polygon([(x, y, z - .05) for x, y, z in quad], ((zb2 - za), 0, -(xb - xa)), face)
        if lod < 2:
            m.polygon([(xc + xa, yd - oh, zde + za - .05), (xc + xb, yd - oh, zde + zb2 - .05),
                       (xc + xb, yd - oh, zde + zb2), (xc + xa, yd - oh, zde + za)], (0, -1, 0), face)
    m.polygon([(xc + x, yend, zde + z) for x, z in cap], (0, 1, 0), roof)
    for s, (x, z) in ((-1, cap[0]), (1, cap[-1])):
        m.polygon([(xc + x, yd - oh, zde + z - .05), (xc + x, yend, zde + z - .05), (xc + x, yend, zde + z),
                   (xc + x, yd - oh, zde + z)], (s, 0, 0), face)
    yc = profile_y(prof, zde)
    inner = [(y, z) for y, z in reversed(prof) if yd + 1e-4 < y < yc - 1e-4]
    for s in (-1, 1):
        x = xc + s * half
        m.polygon([(x, yd, zb), (x, yd, zde), (x, yc, zde)] + [(x, y, z) for y, z in inner], (s, 0, 0), cheek)

def cornice_profile(h, f, a, b, z_top, cp, ch, mat, brackets=False, plain=False):
    """classical cornice on face f between a and b: bed mould, corona, cymatium; LOD0 adds modillion brackets
    or a dentil course. LOD2 is one block."""
    m = h.body
    p = f.point                                        # back face: closes the cornice where it runs past the wall
    m.polygon([p(a, z_top - ch, 0), p(b, z_top - ch, 0), p(b, z_top, 0), p(a, z_top, 0)],
              tuple(-c for c in f.out), mat)
    if h.lod == 2 or cp < .06:
        f.trim(m, a, b, z_top - ch, z_top, 0, max(cp, .04), mat)
        return
    zb, zc, zy = z_top - ch, z_top - ch * .55, z_top - ch * .18
    f.trim(m, a, b, zb, zc, 0, cp * .40, mat)
    f.trim(m, a, b, zc, zy, 0, cp * .85, mat)
    f.trim(m, a, b, zy, z_top, 0, cp, mat)
    if h.lod == 0 and not plain:
        L = b - a
        if brackets:
            n = max(2, round(L / .75))
            for i in range(n + 1):
                u = a + .09 + (L - .18) * i / n
                f.trim(m, u - .05, u + .05, zb - .26, zc, cp * .40, cp * .78, mat)
                f.trim(m, u - .05, u + .05, zb - .26, zb, 0, cp * .40, mat)
                m.polygon([p(u - .05, zb - .26, 0), p(u + .05, zb - .26, 0), p(u + .05, zb, 0), p(u - .05, zb, 0)],
                          tuple(-c for c in f.out), mat)
        else:
            n = max(3, round(L / .17))
            for i in range(n):
                u = a + (i + .5) * L / n
                f.trim(m, u - .045, u + .045, zc - .10, zc, cp * .40, cp * .62, mat)

def cornice(h, x0, x1, y, out, z0, z1, mat, brackets=True):
    """front (out<0 means toward the street) or rear cornice along x, profiled"""
    f = Face((x0, y), (x1, y)) if out < 0 else Face((x1, y), (x0, y))
    cornice_profile(h, f, 0, f.length, z1, abs(out), z1 - z0, mat, brackets)

def ngon(cx, cy, r, n=8):
    return [(cx + r * math.cos(2 * math.pi * (i + .5) / n), cy + r * math.sin(2 * math.pi * (i + .5) / n)) for i in range(n)]

def chimney(h, x, y, z0, z1, mat="Chimney", sx=.34, sy=.42):
    if h.lod == 2:
        return
    m = h.body
    m.box(x - sx, x + sx, y - sy, y + sy, z0, z1, mat)
    m.box(x - sx - .045, x + sx + .045, y - sy - .045, y + sy + .045, z1 - .30, z1 - .20, mat)        # corbel
    m.box(x - sx - .06, x + sx + .06, y - sy - .06, y + sy + .06, z1, z1 + .10, "Dressed")
    if h.lod == 0:                                                      # clay pots
        k = 2 if max(sx, sy) > .3 else 1
        long_y = sy >= sx
        for i in range(k):
            off = (i - (k - 1) / 2) * (sy if long_y else sx)
            px, py = (x, y + off) if long_y else (x + off, y)
            prism(m, ngon(px, py, .10), z1 + .10, z1 + .40, "Chimney", bottom=False)
            prism(m, ngon(px, py, .125), z1 + .40, z1 + .46, "Chimney", bottom=True)

# ------------------------------------------------------------------ cast iron (French Quarter)
def dquad(mesh, pts, n, mat):
    """double-sided flat plate (iron lace is open work, seen from both sides)"""
    L = math.sqrt(sum(c * c for c in n))
    o = [c / L * .001 for c in n]                      # 2 mm apart, so each side is unambiguously in front
    mesh.polygon([tuple(p[i] + o[i] for i in range(3)) for p in pts], n, mat)
    mesh.polygon([tuple(p[i] - o[i] for i in range(3)) for p in pts], tuple(-c for c in n), mat)

def obar(mesh, p0, p1, w, z0, z1, mat, bottom=True):
    """horizontal bar of width w along any 2D segment p0->p1, from z0 to z1"""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy)
    if L < 1e-5 or z1 - z0 < 1e-5:
        return
    nx, ny = -dy / L * w / 2, dx / L * w / 2
    ring = [(p0[0] - nx, p0[1] - ny), (p1[0] - nx, p1[1] - ny), (p1[0] + nx, p1[1] + ny), (p0[0] + nx, p0[1] + ny)]
    if area2d(ring) < 0:
        ring.reverse()
    prism(mesh, ring, z0, z1, mat, bottom)

def lace_ring(mesh, P, s, cz, ro, ri, n, mat, segs=8):
    for i in range(segs):
        a0, a1 = 2 * math.pi * i / segs, 2 * math.pi * (i + 1) / segs
        dquad(mesh, [P(s + ro * math.cos(a0), cz + ro * math.sin(a0)), P(s + ro * math.cos(a1), cz + ro * math.sin(a1)),
                     P(s + ri * math.cos(a1), cz + ri * math.sin(a1)), P(s + ri * math.cos(a0), cz + ri * math.sin(a0))], n, mat)

def lace(h, x0, y0, x1, y1, z, height, mat="Iron", lite=False):
    """New Orleans cast-iron railing along any line: handrail, bottom rail, panel posts, pickets and a frieze
    of interlaced rings under the handrail, rosettes low down. LOD1: rails, posts, sparse pickets."""
    m = h.body
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    if L < .05 or h.lod == 2:
        return
    tx, ty = dx / L, dy / L
    n = (ty, -tx, 0)
    P = lambda s, zz: (x0 + tx * s, y0 + ty * s, zz)
    ztop = z + height
    obar(m, (x0, y0), (x1, y1), .065, ztop - .06, ztop, mat)
    obar(m, (x0, y0), (x1, y1), .04, z + .05, z + .10, mat)
    npost = max(1, math.ceil(L / (1.5 if LITE < 3 or h.lod == 0 else 4.0)))
    posts = [L * i / npost for i in range(npost + 1)]
    for s in posts:
        c = P(min(max(s, .025), L - .025), 0)
        m.box(c[0] - .025, c[0] + .025, c[1] - .025, c[1] + .025, z, ztop - .06, mat, bottom=False)
    if (h.lod == 1 and LITE >= 2) or LITE >= 5:                 # lightest: rails and panel posts only
        return
    if h.lod == 1 or lite or LITE:
        k = max(2, round(L / ((.45 if h.lod == 1 else .2) * (1 + LITE))))
        for i in range(1, k):
            s = L * i / k
            dquad(m, [P(s - .01, z + .10), P(s + .01, z + .10), P(s + .01, ztop - .06), P(s - .01, ztop - .06)], n, mat)
        return
    zf = ztop - .06 - .22                                       # frieze band
    obar(m, (x0, y0), (x1, y1), .025, zf - .025, zf, mat)
    k = max(2, round(L / (.13 * LACE_K ** .5)))
    for i in range(1, k):
        s = L * i / k
        if min(abs(s - q) for q in posts) < .04:
            continue
        dquad(m, [P(s - .009, z + .10), P(s + .009, z + .10), P(s + .009, zf - .025), P(s - .009, zf - .025)], n, mat)
    r = (ztop - .06 - zf) / 2
    nr = max(1, round(L / (1.6 * r * LACE_K)))
    for i in range(nr):
        lace_ring(m, P, (i + .5) * L / nr, zf + r, r, r - .018, n, mat, 6)
    for i in range(1, nr - 1, 2):                               # rosettes low down at every other joint
        lace_ring(m, P, (i + 1) * L / nr, z + .48, .07, .052, n, mat, 6)

def iron_post(h, x, y, z0, z1, mat="Iron"):
    """cast-iron gallery column: plinth, octagonal shaft with a collar, flared capital"""
    m = h.body
    if h.lod == 2:
        m.box(x - .05, x + .05, y - .05, y + .05, z0, z1, mat, bottom=False)
        return
    if h.lod == 1 or LITE >= 4:
        m.box(x - .06, x + .06, y - .06, y + .06, z0, z1, mat, bottom=False)
        return
    m.box(x - .09, x + .09, y - .09, y + .09, z0, z0 + .22, mat, bottom=False)
    prism(m, ngon(x, y, .062), z0 + .22, z1 - .20, mat, bottom=False)
    prism(m, ngon(x, y, .075), z0 + .22, z0 + .30, mat, bottom=False)
    prism(m, ngon(x, y, .085), z1 - .20, z1 - .12, mat, bottom=True)
    m.box(x - .11, x + .11, y - .11, y + .11, z1 - .12, z1, mat)

def iron_frieze(h, pts, z_top, mat="Iron"):
    """lace frieze + spandrel brackets hung between columns at the top of a gallery storey.
    pts: column positions along the line (2D points, in order)"""
    m = h.body
    if h.lod == 2 or len(pts) < 2 or (h.lod == 1 and LITE >= 4):
        return
    a, b = pts[0], pts[-1]
    obar(m, a, b, .05, z_top - .05, z_top, mat)
    obar(m, a, b, .035, z_top - .34, z_top - .30, mat)
    if h.lod == 1 or LITE >= 2:
        return
    L = math.dist(a, b)  # (LITE>=2 already stops here)
    tx, ty = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    n = (ty, -tx, 0)
    P = lambda s, zz: (a[0] + tx * s, a[1] + ty * s, zz)
    r = .125
    nr = max(1, round(L / (1.7 * r * LACE_K)))
    for i in range(nr):
        lace_ring(m, P, (i + .5) * L / nr, z_top - .175, r, r - .018, n, mat, 6)
    for q in pts:                                               # spandrel brackets either side of each column
        s0 = (q[0] - a[0]) * tx + (q[1] - a[1]) * ty
        for sg in (-1, 1):
            s1 = s0 + sg * .42
            if not (-.01 <= s1 <= L + .01):
                continue
            dquad(m, [P(s0, z_top - .34), P(s1, z_top - .34), P(s0, z_top - .80)], n, mat)

def walk(h, x0, x1, y1, y0=-12.0):
    h.body.box(x0, x1, y0 + .01, y1, 0, .04, "Paving", bottom=False)

def balusters(h, x0, y0, x1, y1, z0, z1, spacing, s, mat):
    L = math.hypot(x1 - x0, y1 - y0)
    n = max(1, round(L / spacing))
    for i in range(1, n):
        x, y = x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n
        h.body.box(x - s, x + s, y - s, y + s, z0, z1, mat, bottom=False)

def railing(h, x0, y0, x1, y1, z, height, mat, spacing=.14):
    """straight railing from (x0,y0) to (x1,y1) standing on z; iron ones are cast-iron lace"""
    if h.lod == 2:
        return
    if mat == "Iron":
        lace(h, x0, y0, x1, y1, z, height, mat, lite=spacing >= .2)
        return
    t = .03
    xa, xb = sorted((x0, x1)); ya, yb = sorted((y0, y1))
    h.body.box(xa - t, xb + t, ya - t, yb + t, z + height - .06, z + height, mat)
    h.body.box(xa - t * .6, xb + t * .6, ya - t * .6, yb + t * .6, z + .08, z + .13, mat)
    balusters(h, x0, y0, x1, y1, z + .13, z + height - .06, spacing if h.lod == 0 else .5, .012, mat)

def stringer(mesh, x_top, z_top, x_bot, y0, y1, th, mat):
    """sloped slab from (x_top, z_top) down to the ground at x_bot, th deep, cut off flat at the ground"""
    x_c = x_top + (x_bot - x_top) * (z_top - th) / z_top
    extrude(mesh, [(x_top, z_top - th), (x_c, 0.0), (x_bot, 0.0), (x_top, z_top)], "y", y0, y1, mat, (mat, mat))

def iron_stair(h, x_top, x_bot, y0, y1, z_top, risers):
    """straight exterior stair running along x, descending from x_top (z_top) to x_bot (ground)"""
    m = h.body
    if h.lod == 2:
        stringer(m, x_top, z_top, x_bot, y0, y1, .35, "Iron")
        return
    n = risers if h.lod == 0 else 6
    rise, sgn = z_top / n, (1 if x_bot > x_top else -1)
    g = (x_bot - x_top) / (n - 1)
    for y in (y0, y1 - .05):
        stringer(m, x_top, z_top, x_bot + sgn * .15, y, y + .05, .26, "Iron")
    for k in range(1, n):
        a, b = sorted((x_bot - (k - 1) * g, x_bot - k * g))
        m.box(a, b, y0 + .05, y1 - .05, k * rise - .045, k * rise, "Iron")
    bar(m, "y", x_top, z_top + .95, x_bot, .95, y0, y0 + .05, .05, "Iron")
    step = 2 if h.lod == 0 else 3
    for k in range(1, n, step):
        x = x_bot - (k - .5) * g
        m.box(x - .015, x + .015, y0 + .01, y0 + .04, k * rise, k * rise + .9, "Iron", bottom=False)

def gable_kick(h, inner, outer, z_in, top_mats, under="Cream"):
    """bellcast skirt: quads from the wall-top outline (inner, z_in) out to `outer` [(x, y, z)], with soffit + fascia"""
    m = h.body
    for i in range(4):
        j = (i + 1) % 4
        quad = [(*inner[i], z_in), (*inner[j], z_in), outer[j], outer[i]]
        m.polygon(quad, UP, top_mats[i])
        m.polygon([(x, y, z - .05) for x, y, z in quad], DOWN, under)
        a, b = outer[i], outer[j]
        m.polygon([(a[0], a[1], a[2] - .05), (b[0], b[1], b[2] - .05), b, a],
                  ((b[1] - a[1]), -(b[0] - a[0]), 0), under)

# ------------------------------------------------------------------ the five pilot designs
def plex(h):
    """Montreal plex: two stacked flats, iron stair to the upper door, tin mansard with two segmental dormers"""
    m = h.body
    h.door, h.frame = "GreyBlue", "Cream"
    yf, yb, eave = Y(3.00), Y(17.20), 6.42
    plan = rectangle(-4, 4, yf, yb)
    front, right, rear, left = edges(plan)
    B = "Brick097"
    front.wall(h, 0, eave, [Opening(1.38, 1.08, .30, 2.52, "door"), Opening(4.22, 1.15, .78, 2.48),
                            Opening(6.53, 1.15, .78, 2.48), Opening(1.38, 1.08, 3.30, 5.71, "door"),
                            Opening(4.05, 1.16, 3.83, 5.62), Opening(6.38, 1.16, 3.83, 5.62)], B)
    rear.wall(h, 0, eave, [Opening(8 - 1.40, 1.08, .30, 2.49, "door"), Opening(8 - 4.02, 1.08, .82, 2.49),
                           Opening(8 - 6.54, 1.08, .82, 2.49), Opening(8 - 1.40, 1.08, 3.82, 5.58),
                           Opening(8 - 4.02, 1.08, 3.82, 5.58), Opening(8 - 6.54, 1.08, 3.82, 5.58)], B)
    for side in (left, right):
        side.wall(h, 0, eave, [], B)
    m.polygon([(x, y, .02) for x, y in plan], DOWN, "StoneBase")
    if h.lod < 2:
        for f in (front, rear):
            f.trim(m, 0, 8, 0, .30, 0, .035, "StoneBase")
        front.trim(m, 0, 8, 3.12, 3.24, 0, .05, "Dressed")              # floor band
    cornice(h, -4, 4, yf, -.24, eave - .36, eave, "Cream")
    cornice(h, -4, 4, yb, .22, eave - .30, eave, "Cream", brackets=False)
    prof = mansard(h, -4, 4, yf, yb, eave, 67, 8.52, 9.50, Y(10.10), "Tin", B, oh=.24)
    for x in (4.05, 6.38):
        dormer(h, X(x), .93, 1.43, prof[:3], "segmental", "Tin", "Tin", "Cream")
    chimney(h, X(.50), Y(12.6), 9.0, 10.45)
    # upper landing over the ground-floor door, iron stair down to the right
    ly0, ly1 = Y(1.48), Y(2.90)
    m.box(X(.64), X(2.28), ly0, yf, 3.16, 3.30, "Iron")
    for x in (.70, 2.22):
        m.box(X(x) - .04, X(x) + .04, ly0 + .02, ly0 + .10, 0, 3.16, "Iron", bottom=False)
    railing(h, X(.64), ly0, X(2.28), ly0, 3.30, .95, "Iron")
    railing(h, X(.64), ly0, X(.64), yf - .02, 3.30, .95, "Iron")
    iron_stair(h, X(2.28), X(7.50), Y(1.75), Y(2.85), 3.30, 18)
    walk(h, X(.86), X(1.90), yf)
    walk(h, X(6.95), X(7.92), Y(1.75))
    return {"roof_outline_m2": 8 * (yb - yf), "roof_check_z": eave - .01, "party_sides": ["left", "right"]}


def greystone_row(h):
    """Montreal greystone: ashlar front, slate mansard between firewalls, pedimented dormers, stone stoop"""
    m = h.body
    h.door, h.frame = "Oxblood", "Cream"
    yf, yb, eave = Y(2.30), Y(17.30), 6.60
    plan = rectangle(-4, 4, yf, yb)
    front, right, rear, left = edges(plan)
    G, S = "Greystone", "Brick085"
    front.wall(h, 0, eave, [Opening(4.00, 1.16, .48, 2.84, "door"), Opening(1.68, 1.65, .91, 2.77, "pair"),
                            Opening(6.32, 1.65, .91, 2.77, "pair"), Opening(1.70, 1.14, 3.97, 5.88),
                            Opening(4.00, 1.14, 3.97, 5.88), Opening(6.30, 1.14, 3.97, 5.88),
                            Opening(1.68, .95, .12, .44, "small", stone=False),
                            Opening(6.32, .95, .12, .44, "small", stone=False)], G)
    rear.wall(h, 0, eave, [Opening(8 - 1.70, 1.07, .48, 2.72, "door"), Opening(8 - 4.00, 1.07, .96, 2.72),
                           Opening(8 - 6.30, 1.07, .96, 2.72), Opening(8 - 1.70, 1.07, 3.96, 5.80),
                           Opening(8 - 4.00, 1.07, 3.96, 5.80), Opening(8 - 6.30, 1.07, 3.96, 5.80)], S)
    for side in (left, right):
        side.wall(h, 0, eave, [], S)
    m.polygon([(x, y, .02) for x, y in plan], DOWN, "StoneBase")
    if h.lod < 2:
        front.trim(m, 0, 8, 3.42, 3.56, 0, .06, "Dressed")                # string course
        front.trim(m, 0, .30, 0, eave - .36, 0, .03, "Dressed")           # quoin strips at the party lines
        front.trim(m, 7.70, 8, 0, eave - .36, 0, .03, "Dressed")
    cornice(h, -4, 4, yf, -.26, eave - .38, eave, "Dressed")
    cornice(h, -4, 4, yb, .20, eave - .28, eave, "Dressed", brackets=False)
    prof = mansard(h, -3.77, 3.77, yf, yb, eave, 75, 9.29, 10.73, Y(9.80), "Slate", S, oh=.26, caps=False)
    firewall(h, prof, -4, -3.77, S, G)
    firewall(h, prof, 3.77, 4, S, G)
    for x in (1.70, 6.30):
        dormer(h, X(x), 1.05, 1.53, prof[:3], "pediment", "Slate", "Slate", "Dressed")
    chimney(h, -3.60, Y(9.8) + .9, 10.0, 11.55, sx=.30)
    chimney(h, 3.60, Y(9.8) + .9, 10.0, 11.55, sx=.30)
    # stoop: three 0.16 risers, front edge at Y 1.15
    for k in range(3):
        m.box(-.89, .89, Y(1.15) + k * .383, yf, k * .16, (k + 1) * .16, "Dressed", bottom=False)
    if h.lod < 2:
        for s in (-1, 1):
            bar(m, "x", Y(1.20), .16 + .85, yf - .05, .48 + .85, s * .84 - .025, s * .84 + .025, .05, "Iron")
            m.box(s * .84 - .03, s * .84 + .03, Y(1.17), Y(1.17) + .06, .16, 1.05, "Iron", bottom=False)
    walk(h, -.80, .80, Y(1.15))
    return {"roof_outline_m2": 8 * (yb - yf), "roof_check_z": eave - .01, "party_sides": ["left", "right"]}


def creole_cottage(h):
    """narrow Creole cottage (1x): render walls on a rubble base, steep tin hip with a bellcast kick that runs out
    over a deep front gallery, one segmental dormer, board shutters"""
    m = h.body
    h.door, h.frame, h.lintel = "Green", "Cream", False
    x0, x1, yf, yb, eave, floor = X(.8), X(7.2), Y(5.0), Y(14.0), 3.35, .45
    plan = rectangle(x0, x1, yf, yb)
    front, right, rear, left = edges(plan)
    R, Sh = "Render", "Green"
    front.wall(h, 0, eave, [Opening(1.15, .95, floor, 2.75, "french", Sh), Opening(3.20, 1.05, floor, 2.85, "door"),
                            Opening(5.25, .95, floor, 2.75, "french", Sh)], R)
    for side in (right, left):
        side.wall(h, 0, eave, [Opening(2.2, .90, 1.0, 2.55, "sash", Sh), Opening(6.6, .90, 1.0, 2.55, "sash", Sh)], "RenderSide")
    rear.wall(h, 0, eave, [Opening(1.8, .90, 1.0, 2.55, "sash", Sh), Opening(4.4, 1.0, floor, 2.60, "door")], "RenderSide")
    m.polygon([(x, y, .02) for x, y in plan], DOWN, "Rubble")
    if h.lod < 2:
        for f in (front, right, rear, left):
            f.trim(m, 0, f.length, 0, floor, 0, .04, "Rubble")
    # roof: steep hip (52 deg) from the wall tops, bellcast kick around, front kick runs out over the gallery
    inner = [(x0, yf), (x1, yf), (x1, yb), (x0, yb)]
    ridge = eave + 3.2 * math.tan(math.radians(52))
    r0, r1 = (X(4), yf + 3.2), (X(4), yb - 3.2)
    for quad, d in (([(x0, yf, eave), (x1, yf, eave), (*r0, ridge)], (0, -1, 1)),
                    ([(x1, yf, eave), (x1, yb, eave), (*r1, ridge), (*r0, ridge)], (1, 0, 1)),
                    ([(x1, yb, eave), (x0, yb, eave), (*r1, ridge)], (0, 1, 1)),
                    ([(x0, yb, eave), (x0, yf, eave), (*r0, ridge), (*r1, ridge)], (-1, 0, 1))):
        m.polygon(quad, d, "Tin")
    kick, gy = .45, Y(2.80)
    kz = eave - kick * math.tan(math.radians(16))
    outer = [(x0 - kick, yf - kick, kz), (x1 + kick, yf - kick, kz), (x1 + kick, yb + kick, kz), (x0 - kick, yb + kick, kz)]
    gable_kick(h, inner, outer, eave, ["TinFlat", "Tin", "Tin", "Tin"])
    gz = kz - (yf - kick - gy) * math.tan(math.radians(16))           # gallery roof carries the kick on at 16 deg
    sheet = [(x0 - kick, yf - kick, kz), (x1 + kick, yf - kick, kz), (x1 + kick, gy, gz), (x0 - kick, gy, gz)]
    m.polygon(sheet, UP, "TinFlat")
    m.polygon([(x, y, z - .05) for x, y, z in sheet], DOWN, "Cream")
    for a, b, d in ((sheet[2], sheet[3], (0, -1, 0)), (sheet[1], sheet[2], (1, 0, 0)), (sheet[3], sheet[0], (-1, 0, 0))):
        m.polygon([(a[0], a[1], a[2] - .05), (b[0], b[1], b[2] - .05), b, a], d, "Cream")
    hip_front = [(yf, eave), (r0[1], ridge)]
    dormer(h, X(4), .80, 1.00, [(yf, eave)] + [(yf + .5, eave + .5 * math.tan(math.radians(52)))] + hip_front[1:],
           "segmental", "Tin", "Tin", "Cream")
    chimney(h, X(4), Y(9.6), ridge - .6, ridge + 1.0, "Rubble", .30, .36)
    # gallery: rubble base, plank deck, four posts, rails either side of the steps
    gx0, gx1, gy0 = X(.35), X(7.65), Y(2.90)
    m.box(gx0, gx1, gy0, yf, 0, floor - .05, "Rubble", bottom=False)
    m.box(gx0, gx1, gy0, yf, floor - .05, floor, "Deck", bottom=False)
    post_y = gy0 + .10
    post_top = gz + (post_y - gy) / (yf - gy) * (eave - gz) - .03
    for x in (.45, 2.85, 5.15, 7.55):
        m.box(X(x) - .07, X(x) + .07, post_y - .07, post_y + .07, floor, post_top, "Cream", bottom=False)
    for a, b in ((.52, 2.78), (5.22, 7.48)):
        railing(h, X(a), post_y, X(b), post_y, floor, .90, "Cream", .16)
    for x in (.45, 7.55):
        railing(h, X(x), post_y + .07, X(x), yf - .03, floor, .90, "Cream", .16)
    for k, ya in enumerate((Y(2.30), Y(2.60))):
        m.box(X(3.4), X(4.6), ya, gy0, k * .15, (k + 1) * .15, "Dressed", bottom=False)
    m.box(X(4.4) - .6, X(4.4) + .6, yb, yb + .5, 0, .30, "Dressed", bottom=False)    # rear step under the back door
    walk(h, X(3.5), X(4.5), Y(2.30))
    return {"roof_outline_m2": (x1 - x0) * (yb - yf), "roof_check_z": eave - .01, "party_sides": []}


def gallery_shop(h):
    """brick shop with a cast-iron gallery over the sidewalk and a tin mansard"""
    m = h.body
    h.door, h.frame, h.shop = "Green", "Cream", "Green"
    yf, yb, eave = Y(2.25), Y(16.65), 6.66
    plan = rectangle(-4, 4, yf, yb)
    front, right, rear, left = edges(plan)
    B = "Brick074"
    front.wall(h, 0, eave, [Opening(4.00, 1.18, .15, 2.77, "shopdoor"), Opening(1.79, 2.24, .53, 2.74, "shop"),
                            Opening(6.21, 2.24, .53, 2.74, "shop"), Opening(1.82, 1.09, 3.97, 5.77),
                            Opening(6.18, 1.09, 3.97, 5.77), Opening(4.00, 1.04, 3.38, 5.79, "french")], B)
    rear.wall(h, 0, eave, [Opening(4.00, 1.0, .15, 2.60, "door"), Opening(8 - 1.82, 1.0, .9, 2.6),
                           Opening(8 - 6.18, 1.0, .9, 2.6), Opening(8 - 1.82, 1.0, 3.97, 5.77),
                           Opening(8 - 6.18, 1.0, 3.97, 5.77)], B)
    for side in (left, right):
        side.wall(h, 0, eave, [], B)
    m.polygon([(x, y, .02) for x, y in plan], DOWN, "StoneBase")
    if h.lod < 2:
        front.trim(m, 0, 8, 0, .15, 0, .03, "StoneBase")
        front.trim(m, 0, 8, 2.86, 3.16, 0, .07, "Green")                  # fascia under the gallery
        for x in (.25, 7.75):                                             # pilasters
            front.trim(m, x - .25, x + .25, 0, 3.16, 0, .05, "Green")
    cornice(h, -4, 4, yf, -.24, eave - .36, eave, "Cream")
    cornice(h, -4, 4, yb, .20, eave - .28, eave, "Cream", brackets=False)
    prof = mansard(h, -4, 4, yf, yb, eave, 70, 9.13, 10.24, Y(9.45), "Tin", B, oh=.24)
    for x in (1.82, 6.18):
        dormer(h, X(x), .95, 1.32, prof[:3], "segmental", "Tin", "Tin", "Cream")
    chimney(h, X(.50), Y(13.0), 9.4, 10.95)
    # gallery: deck over the sidewalk at 3.38, iron posts, tin hood
    gx0, gx1, gy0, deck = X(.14), X(7.86), Y(.18), 3.38
    m.box(gx0, gx1, gy0, yf, deck - .20, deck, "Iron", top="Deck")
    if h.lod < 2:
        m.box(gx0 - .02, gx1 + .02, gy0 - .03, gy0, deck - .24, deck + .02, "Green")
    py = gy0 + .12
    hood = [(yf, 6.40), (Y(.15), 6.06), (Y(.15), 6.00), (yf, 6.34)]
    extrude(m, hood, "x", gx0, gx1, ["TinFlat", "Cream", "Cream", "Cream"], ("Cream", "Cream"))
    hood_z = profile_z([(Y(.15), 6.00), (yf, 6.34)], py)
    for x in (.36, 2.72, 5.28, 7.64):
        m.box(X(x) - .085, X(x) + .085, py - .085, py + .085, 0, deck - .20, "Iron", bottom=False)
        m.box(X(x) - .07, X(x) + .07, py - .07, py + .07, deck, hood_z + .02, "Iron", bottom=False)
    railing(h, gx0 + .05, py, gx1 - .05, py, deck, 1.02, "Iron")
    for x in (gx0 + .05, gx1 - .05):
        railing(h, x, py, x, yf - .03, deck, 1.02, "Iron")
    walk(h, -4, 4, yf)
    return {"roof_outline_m2": 8 * (yb - yf), "roof_check_z": eave - .01, "party_sides": ["left", "right"]}


def right_corner_store(h):
    """corner shop: steep tin pavilion with a lantern over the front block, cut corner with the door, windows on
    the side street (the game mirrors it for left corners, so this side always faces the street)"""
    m = h.body
    h.door, h.frame, h.shop = "Green", "Cream", "Green"
    eave, xr = 6.56, X(7.75)
    plan = [(X(0), Y(1.80)), (X(6.45), Y(1.80)), (xr, Y(3.10)), (xr, Y(16.20)), (X(0), Y(16.20))]
    fs = edges(plan)
    B = "Brick054"
    ops = [
        [Opening(1.58, 2.23, .51, 2.82, "shop"), Opening(4.58, 2.23, .51, 2.82, "shop"),
         Opening(1.43, 1.10, 3.95, 5.74), Opening(3.75, 1.10, 3.95, 5.74), Opening(5.94, 1.10, 3.95, 5.74)],
        [Opening(fs[1].length / 2, 1.36, .15, 2.85, "shopdoor"), Opening(fs[1].length / 2, .95, 3.95, 5.74)],
        [Opening(1.9, 1.80, .51, 2.82, "shop"), Opening(5.2, 1.10, .90, 2.60), Opening(8.6, 1.10, .90, 2.60),
         Opening(11.6, 1.0, .15, 2.60, "door"), Opening(1.9, 1.10, 3.95, 5.74), Opening(5.2, 1.10, 3.95, 5.74),
         Opening(8.6, 1.10, 3.95, 5.74), Opening(11.6, 1.10, 3.95, 5.74)],
        [Opening(2.0, 1.0, .90, 2.60), Opening(5.5, 1.0, .90, 2.60), Opening(2.0, 1.0, 3.95, 5.74),
         Opening(5.5, 1.0, 3.95, 5.74)],
        [],
    ]
    for i, f in enumerate(fs):
        f.wall(h, 0, eave, ops[i], "Greystone" if i == 1 else B)
        if h.lod < 2 and i < 3:
            f.trim(m, 0, f.length, 0, .15, 0, .03, "StoneBase")
            f.trim(m, 0, f.length, 3.40, 3.52, 0, .06, "Dressed")
            f.trim(m, 0, min(f.length, 4.0), 2.90, 3.20, 0, .07, "Green")
    m.polygon([(*p, .02) for p in plan], DOWN, "StoneBase")
    # cornice ring (no projection on the party side) and the pavilion that sits on it
    block = [plan[0], plan[1], plan[2], (xr, Y(9.80)), (X(0), Y(9.80))]
    ring = offset_plan(block, [.25, .25, .25, 0, 0])
    if h.lod < 2:
        full = offset_plan(plan, [.25, .25, .25, .20, 0])
        prism(m, full, eave - .34, eave, "Dressed")
    top_z, cx, cy, half = 10.93, (ring[0][0] + ring[2][0]) / 2, Y(5.80), .70
    TL, TR, BR, BL = (cx - half, cy - half, top_z), (cx + half, cy - half, top_z), (cx + half, cy + half, top_z), (cx - half, cy + half, top_z)
    P = [(*p, eave) for p in ring]
    for quad, d in (([P[0], P[1], TR, TL], (0, -1, 1)), ([P[1], P[2], TR], (1, -1, 1)), ([P[2], P[3], BR, TR], (1, 0, 1)),
                    ([P[3], P[4], BL, BR], (0, 1, 1)), ([P[4], P[0], TL, BL], (-1, 0, 1))):
        m.polygon(quad, d, "Tin")
    m.polygon([TL, TR, BR, BL], UP, "TinFlat")
    m.polygon(P, DOWN, "Cream")
    # rear block: low 5-degree shed toward the rear
    rz = eave + 6.4 * math.tan(math.radians(5))
    extrude(m, [(Y(9.80), eave - .2), (Y(9.80), rz), (Y(16.40), eave - .02), (Y(16.40), eave - .14)], "x",
            X(0), xr + .25, [B, "TinFlat", "Cream", "Cream"], (B, "Cream"))
    # lantern: drum with small lights, flared tin cap
    lw, dz = .63, 11.76
    drum = rectangle(cx - lw, cx + lw, cy - lw, cy + lw)
    for f in edges(drum):
        f.wall(h, top_z, dz, [Opening(f.length / 2, .46, 11.12, 11.56, "small", stone=False)] if h.lod < 2 else [], "Cream")
    cap = [(cx - lw - .12, cy - lw - .12), (cx + lw + .12, cy - lw - .12), (cx + lw + .12, cy + lw + .12), (cx - lw - .12, cy + lw + .12)]
    m.polygon([(*p, dz) for p in cap], DOWN, "Cream")
    for a, b in zip(cap, cap[1:] + cap[:1]):
        m.polygon([(*a, dz), (*b, dz), (cx, cy, 12.41)], ((a[1] + b[1]) / 2 - cy and 0, 0, 1) if False else
                  (((a[0] + b[0]) / 2 - cx), ((a[1] + b[1]) / 2 - cy), .8), "TinFlat")
    chimney(h, X(.45), Y(14.6), 6.2, 8.2)
    door = fs[1].point(fs[1].length / 2, 0)
    walk(h, door.x - .7, min(door.x + .7, 3.99), door.y - .3)
    walk(h, X(.5), X(6.0), Y(1.80))
    return {"roof_outline_m2": projected_area(plan), "roof_check_z": eave - .05, "party_sides": ["left"],
            "access": "RightCorner"}


ASSETS = [
    ("Plex", "Napoleon Row Homes Medium", plex),
    ("GreystoneRow", "Napoleon Row Homes Medium", greystone_row),
    ("CreoleCottage", "Napoleon Residential Low", creole_cottage),
    ("GalleryShop", "Napoleon Commercial Low", gallery_shop),
    ("RightCornerStore", "Napoleon Commercial Low", right_corner_store),
]

# ------------------------------------------------------------------ export + round-trip validation (GPT's checks)
def export_fbx(ob, path):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={"MESH"},
                             apply_unit_scale=True, apply_scale_options="FBX_SCALE_NONE", axis_forward="-Z",
                             axis_up="Y", bake_space_transform=True, mesh_smooth_type="EDGE", add_leaf_bones=False,
                             path_mode="STRIP", embed_textures=False)

def clear_objects():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        bpy.data.meshes.remove(me)

def validate_export(path, dims, roof=None, glass=False):
    clear_objects()
    old = bpy.data.materials.get(path.stem)
    if old:
        bpy.data.materials.remove(old)
    bpy.ops.import_scene.fbx(filepath=str(path), axis_forward="-Z", axis_up="Y")
    obs = [o for o in bpy.context.selected_objects if o.type == "MESH"]
    assert len(obs) == 1, path.name
    ob = obs[0]; mesh = ob.data
    assert ob.name == path.stem and len(mesh.uv_layers) == 1, path.name
    assert len(mesh.materials) == (0 if glass else 1), path.name
    assert glass or mesh.materials[0].name == path.stem, (path.name, mesh.materials[0].name)
    pts = [ob.matrix_world @ v.co for v in mesh.vertices]
    bounds = [[min(p[i] for p in pts), max(p[i] for p in pts)] for i in range(3)]
    assert bounds[0][0] >= -dims[0] / 2 - .002 and bounds[0][1] <= dims[0] / 2 + .002, (path.name, bounds)
    assert bounds[1][0] >= -dims[1] / 2 - .002 and bounds[1][1] <= dims[1] / 2 + .002, (path.name, bounds)
    assert bounds[2][0] >= -.002, (path.name, bounds)
    assert all(p.area > 1e-8 for p in mesh.polygons), path.name
    assert all(-1e-6 <= c <= 1.000001 for e in mesh.uv_layers.active.data for c in e.uv), path.name
    area = 0
    if glass:
        uv = mesh.uv_layers.active.data
        for poly in mesh.polygons:
            cells = {(int(uv[i].uv[0] * 5), int(uv[i].uv[1] * 5)) for i in poly.loop_indices}
            assert len(cells) == 1 and next(iter(cells))[0] + 5 * next(iter(cells))[1] in ROOMS, path.name
    elif roof:
        for poly in mesh.polygons:
            pp = [pts[i] for i in poly.vertices]
            if min(p.z for p in pp) >= roof["roof_check_z"]:
                area += max(0, projected_area(pp))
        assert area + .08 >= roof["roof_outline_m2"], (path.name, area, roof["roof_outline_m2"])
    mesh.calc_loop_triangles()
    tris = len(mesh.loop_triangles)
    if path.stem.endswith("_LOD2") and not glass:
        assert tris <= 500, (path.name, tris)
    return {"triangles": tris, "bounds_m": [[round(a, 3), round(b, 3)] for a, b in bounds],
            "upward_projected_area_m2": round(area, 3)}

def run(only=None):
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 1
    manifest = {}
    for design, zone, build in ASSETS:
        if only and design not in only:
            continue
        name = f"NA_NewFrance{design}_L1_1x3"
        folder = OUT / name
        folder.mkdir(parents=True, exist_ok=True)
        rec = {"design": design, "zone": zone, "lot": [1, 3], "level": 1, "access": "Front", "texture_owner": OWNER,
               "meshes": {}}
        for lod, suffix in enumerate(("", "_LOD1", "_LOD2")):
            clear_objects()
            h = House(lod)
            details = build(h)
            if lod == 0:
                rec.update(details)
                rec["entrances_blender_m"] = h.doors
            for mesh, sfx in ((h.body, suffix), (h.windows, suffix + "_Win")):
                tag = name + sfx
                old = bpy.data.materials.get(tag)
                if old:
                    bpy.data.materials.remove(old)
                ob = mesh.object(tag, None if sfx.endswith("_Win") else bpy.data.materials.new(tag))
                export_fbx(ob, folder / (tag + ".fbx"))
        if name != OWNER:
            share = {f"{name}{lod}_{kind}.png": f"../{OWNER}/{OWNER}{lod}_{kind}.png"
                     for lod in ("", "_LOD1", "_LOD2") for kind in MAPS}
            (folder / "settings.json").write_text(json.dumps({"sharedAssets": share}, indent=2), encoding="utf-8")
        for path in sorted(folder.glob("*.fbx")):
            rec["meshes"][path.stem.removeprefix(name) or "Main"] = validate_export(
                path, (W, 24), details, path.stem.endswith("_Win"))
        c = rec["meshes"]
        assert c["Main"]["triangles"] > c["_LOD1"]["triangles"] > c["_LOD2"]["triangles"], name
        manifest[name] = rec
        print(f"VERIFIED {name} {c['Main']['triangles']}/{c['_LOD1']['triangles']}/{c['_LOD2']['triangles']}", flush=True)
    (HERE / "reports" / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("NEW FRANCE FBX ROUND-TRIP PASSED", flush=True)

if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    run(set(argv) or None)
