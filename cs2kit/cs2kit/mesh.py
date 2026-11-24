"""Pure-Python / Blender-compatible core mesh and structural building primitives.

Coordinates: lot-centre origin, street at -Y, +Z up, +X right.
Walls run from A to B with their outward normal on the right.
"""
from contextlib import contextmanager
from .math_compat import Vector, E, UP, DOWN
from . import rules

_MESH_SINK = None


@contextmanager
def capture_meshes():
    """Capture (body_mesh, windows_mesh) in memory from finish(m, g) without requiring bpy."""
    global _MESH_SINK
    captured = []
    prev = _MESH_SINK
    _MESH_SINK = captured
    try:
        yield captured
    finally:
        _MESH_SINK = prev


class Mesh:
    """In-memory polygon soup holding face material names and architectural rule state."""

    def __init__(self):
        self.v, self.f, self.m, self.mats = [], [], [], []
        self.waived_rules = []

    def facing(self, pts, hint, mat):
        """Add a polygon, wound so its Newell normal points along `hint`."""
        n = Vector((0.0, 0.0, 0.0))
        for i in range(len(pts)):
            a, b = Vector(pts[i]), Vector(pts[(i + 1) % len(pts)])
            n += Vector(((a.y - b.y) * (a.z + b.z), (a.z - b.z) * (a.x + b.x), (a.x - b.x) * (a.y + b.y)))
        if n.dot(Vector(hint)) < 0:
            pts = pts[::-1]
        if mat not in self.mats:
            self.mats.append(mat)
        i = len(self.v)
        self.v += [tuple(float(c) for c in p) for p in pts]
        self.f.append(list(range(i, i + len(pts))))
        self.m.append(self.mats.index(mat))

    def make(self, name):
        """Materialize this mesh as a Blender object (only when running inside Blender)."""
        import bpy
        import bmesh

        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        me.update()
        for k, i in enumerate(self.m):
            me.polygons[k].material_index = i
        for mat in self.mats:
            me.materials.append(bpy.data.materials.get(mat) or bpy.data.materials.new(mat))
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(name, me)
        bpy.context.collection.objects.link(ob)
        return ob


def finish(m, g):
    """Validate rules 1-10 & 15, then hand (m, g) to active sink or create Blender objects."""
    waived = rules.verdict(m)
    m.waived_rules = waived
    if _MESH_SINK is not None:
        _MESH_SINK.append((m, g))
        return
    import bpy

    for name, mesh in (("Body", m), ("Windows", g)):
        old = bpy.data.objects.get(name)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)
        mesh.make(name)


class Wall:
    """A straight wall line from A to B (plan points); outside is on the right walking A -> B."""

    def __init__(self, A, B):
        self.A = Vector((A[0], A[1], 0.0))
        d = Vector((B[0] - A[0], B[1] - A[1], 0.0))
        self.L = d.length
        self.t = d / self.L
        self.n = Vector((self.t.y, -self.t.x, 0.0))

    def P(self, u, z, d=0.0):
        p = self.A + self.t * u + self.n * d
        return (p.x, p.y, float(z))

    def u_of(self, c):
        """Distance along the wall of a world x (walls along x) or y (walls along y)."""
        return (c - self.A.x) * self.t.x if abs(self.t.x) > 0.5 else (c - self.A.y) * self.t.y


def lbox(m, w, u0, u1, z0, z1, d0, d1, mat, skip=("in",)):
    """Axis-aligned box in wall coordinates: u along wall, z up, d out from wall face."""
    if u1 - u0 < 1e-4 or z1 - z0 < 1e-4 or d1 - d0 < 1e-4:
        return
    P = w.P
    F = {
        "out": ([P(u0, z0, d1), P(u1, z0, d1), P(u1, z1, d1), P(u0, z1, d1)], w.n),
        "in": ([P(u0, z0, d0), P(u1, z0, d0), P(u1, z1, d0), P(u0, z1, d0)], -w.n),
        "r": ([P(u1, z0, d0), P(u1, z0, d1), P(u1, z1, d1), P(u1, z1, d0)], w.t),
        "l": ([P(u0, z0, d0), P(u0, z0, d1), P(u0, z1, d1), P(u0, z1, d0)], -w.t),
        "top": ([P(u0, z1, d0), P(u1, z1, d0), P(u1, z1, d1), P(u0, z1, d1)], UP),
        "bot": ([P(u0, z0, d0), P(u1, z0, d0), P(u1, z0, d1), P(u0, z0, d1)], DOWN),
    }
    for k, (pts, h) in F.items():
        if k not in skip:
            m.facing(pts, h, mat)


def wbox(m, x0, x1, y0, y1, z0, z1, mat, skip=()):
    """Axis-aligned box in world coordinates; skip names faces x-, x+, y-, y+, z-, z+."""
    if x1 - x0 < 1e-5 or y1 - y0 < 1e-5 or z1 - z0 < 1e-5:
        return
    F = {
        "x-": ([(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)], (-1, 0, 0)),
        "x+": ([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], (1, 0, 0)),
        "y-": ([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], (0, -1, 0)),
        "y+": ([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], (0, 1, 0)),
        "z-": ([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)], (0, 0, -1)),
        "z+": ([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], (0, 0, 1)),
    }
    for k, (pts, h) in F.items():
        if k not in skip:
            m.facing(pts, h, mat)


def band(m, w, z0, z1, proud, mat, s="x", e="x", cuts=(), shrink=None, skip=("in",)):
    """Course standing proud of the wall. Ends: 'x' outside, 'c' inside, '-' plain. cuts: [(u0, u1)]."""
    u0 = E if s == "c" else 0.0
    u1 = w.L + proud if e == "x" else w.L - (proud + E if shrink is None else shrink) if e == "c" else w.L
    segs = [(u0, u1)]
    for a, b in sorted(cuts):
        nxt = []
        for x0, x1 in segs:
            if b <= x0 or a >= x1:
                nxt.append((x0, x1))
                continue
            if a > x0:
                nxt.append((x0, a))
            if b < x1:
                nxt.append((b, x1))
        segs = nxt
    for x0, x1 in segs:
        if x1 - x0 > 0.02:
            lbox(m, w, x0, x1, z0, z1, E, proud, mat, skip)


def holes_for(w, bays, spec, door=None):
    """One opening per floor at each bay (world x or y); door = (bay, width, head) replaces ground window."""
    H = []
    for c in bays:
        u = w.u_of(c)
        for f, (wd, zb, zt, *kind) in enumerate(spec):
            if f == 0 and door and abs(c - door[0]) < 1e-6:
                H.append((u - door[1] / 2, u + door[1] / 2, 0.0, door[2], "door"))
            else:
                H.append((u - wd / 2, u + wd / 2, zb, zt, kind[0] if kind else "win"))
    return H


def cuts_of(holes, pad, kinds=("win", "door", "fwin")):
    return [(h[0] - pad - E, h[1] + pad + E) for h in holes if h[4] in kinds]


def world_cuts(w, ranges):
    """World (from, to) ranges along the wall -> (u0, u1) gaps, 4 mm wider each side."""
    out = []
    for a, b in ranges:
        u0, u1 = sorted((w.u_of(a), w.u_of(b)))
        out.append((u0 - E, u1 + E))
    return out


def party(m, A, B, z0, z1, mat):
    """Bare party wall on the side lot line."""
    w = Wall(A, B)
    m.facing([w.P(0, z0), w.P(w.L, z0), w.P(w.L, z1), w.P(0, z1)], w.n, mat)
    return w


def flat_roof(m, x0, x1, y0, y1, z, mat="TinFlat"):
    m.facing([(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], UP, mat)


def chimney(m, x, y, sx, sy, z0, z1, lod, mat="Chimney", cap_mat="Dressed"):
    wbox(m, x - sx, x + sx, y - sy, y + sy, z0, z1, mat, ("z-", "z+"))
    if lod < 2:
        wbox(m, x - sx - 0.08, x + sx + 0.08, y - sy - 0.08, y + sy + 0.08, z1, z1 + 0.2, cap_mat)
    if lod == 0:
        for k in (-1, 1):
            px = x + k * sx / 2
            wbox(m, px - 0.12, px + 0.12, y - 0.12, y + 0.12, z1 + 0.2, z1 + 0.6, mat, ("z-",))


def roof_check(m, t, what):
    """Rule 15 (closed construction): verify `t` is a closed solid and merge into `m`."""
    rules.check_closed_solid(m, t, what)
    for f, k in zip(t.f, t.m):
        pts = [t.v[i] for i in f]
        mat = t.mats[k]
        if mat not in m.mats:
            m.mats.append(mat)
        i = len(m.v)
        m.v += pts
        m.f.append(list(range(i, i + len(pts))))
        m.m.append(m.mats.index(mat))
