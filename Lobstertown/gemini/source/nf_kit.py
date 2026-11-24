"""New France building kit (Claude, 2026-11-13), pulled out of Hôtel Brique et Pierre, the benchmark building.

Every piece leaves a 4 mm air gap (E) wherever it touches another, so no two faces share a plane and flicker.
Coordinates: lot centre origin, street at -Y, z up. A wall runs from A to B with its outside on the right.

  Mesh, Wall               polygons with outward winding; wall frame (u along, z up, d outward)
  wall(...)                a whole facade: cut openings, plinth/cap, belts, rustication, quoins, cornice
  surface, opening, band   the parts wall() is made of, for odd pieces
  mansard, lucarne, pediment, pilasters, steps, chimney
  finish(m, g)             hand the meshes to the runner as 'Body' and 'Windows'
"""
import bpy
import bmesh
from mathutils import Vector
import nf_rules

E = 0.004
UP = Vector((0, 0, 1))


class Mesh:
    def __init__(self):
        self.v, self.f, self.m, self.mats = [], [], [], []

    def facing(self, pts, hint, mat):
        """Add a polygon, wound so its normal points along hint."""
        n = Vector((0, 0, 0))
        for i in range(len(pts)):
            a, b = Vector(pts[i]), Vector(pts[(i + 1) % len(pts)])
            n += Vector(((a.y - b.y) * (a.z + b.z), (a.z - b.z) * (a.x + b.x), (a.x - b.x) * (a.y + b.y)))
        if n.dot(Vector(hint)) < 0:
            pts = pts[::-1]
        if mat not in self.mats:
            self.mats.append(mat)
        i = len(self.v)
        self.v += [tuple(p) for p in pts]
        self.f.append(list(range(i, i + len(pts))))
        self.m.append(self.mats.index(mat))

    def make(self, name):
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
    nf_rules.verdict(m)                      # the rulebook: raise if any rule was broken
    for name, mesh in (("Body", m), ("Windows", g)):
        old = bpy.data.objects.get(name)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)
        mesh.make(name)


class Wall:
    """A straight wall line from A to B (plan points); the outside is on the right when walking A -> B."""
    def __init__(self, A, B):
        self.A = Vector((A[0], A[1], 0))
        d = Vector((B[0] - A[0], B[1] - A[1], 0))
        self.L = d.length
        self.t = d / self.L
        self.n = Vector((self.t.y, -self.t.x, 0))

    def P(self, u, z, d=0.0):
        p = self.A + self.t * u + self.n * d
        return (p.x, p.y, z)

    def u_of(self, c):
        """Distance along the wall of a world x (walls along x) or y (walls along y)."""
        return (c - self.A.x) * self.t.x if abs(self.t.x) > .5 else (c - self.A.y) * self.t.y


def lbox(m, w, u0, u1, z0, z1, d0, d1, mat, skip=("in",)):
    """Box in wall coordinates: u along the wall, z up, d out from the wall face."""
    if u1 - u0 < 1e-4 or z1 - z0 < 1e-4 or d1 - d0 < 1e-4:
        return
    P = w.P
    F = {"out": ([P(u0, z0, d1), P(u1, z0, d1), P(u1, z1, d1), P(u0, z1, d1)], w.n),
         "in": ([P(u0, z0, d0), P(u1, z0, d0), P(u1, z1, d0), P(u0, z1, d0)], -w.n),
         "r": ([P(u1, z0, d0), P(u1, z0, d1), P(u1, z1, d1), P(u1, z1, d0)], w.t),
         "l": ([P(u0, z0, d0), P(u0, z0, d1), P(u0, z1, d1), P(u0, z1, d0)], -w.t),
         "top": ([P(u0, z1, d0), P(u1, z1, d0), P(u1, z1, d1), P(u0, z1, d1)], UP),
         "bot": ([P(u0, z0, d0), P(u1, z0, d0), P(u1, z0, d1), P(u0, z0, d1)], -UP)}
    for k, (pts, h) in F.items():
        if k not in skip:
            m.facing(pts, h, mat)


def wbox(m, x0, x1, y0, y1, z0, z1, mat, skip=()):
    """Axis-aligned box in world coordinates; skip names faces as x-, x+, y-, y+, z-, z+."""
    F = {"x-": ([(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)], (-1, 0, 0)),
         "x+": ([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], (1, 0, 0)),
         "y-": ([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], (0, -1, 0)),
         "y+": ([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], (0, 1, 0)),
         "z-": ([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)], (0, 0, -1)),
         "z+": ([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], (0, 0, 1))}
    for k, (pts, h) in F.items():
        if k not in skip:
            m.facing(pts, h, mat)


# ---------------------------------------------------------------- openings and wall faces

def opening(m, g, w, h, lod, trim):
    """Window or door: reveals, glass or door leaves, and (by detail level) casement bars and a stone surround.
    trim: dep (reveal depth), jamb, so (sill/lintel overhang), key (keystone), door (door material)."""
    u0, u1, zb, zt, kind = h
    P, n, t = w.P, w.n, w.t
    if kind == "shop":
        return shop_opening(m, g, w, h, lod, trim)
    door = kind == "door"
    dmat = trim.get("door", "Green")
    if lod == 2:                              # far view: no cut, the pane sits just proud of the wall
        pane = [P(u0, zb, .02), P(u1, zb, .02), P(u1, zt, .02), P(u0, zt, .02)]
        if door:
            m.facing(pane, n, dmat)
        else:
            g.facing(pane, n, "Glass")
        return
    dep = trim.get("dep", .25) if lod == 0 else .12
    m.facing([P(u0, zb, 0), P(u0, zb, -dep), P(u0, zt, -dep), P(u0, zt, 0)], t, "RevealStone")
    m.facing([P(u1, zb, 0), P(u1, zb, -dep), P(u1, zt, -dep), P(u1, zt, 0)], -t, "RevealStone")
    m.facing([P(u0, zt, 0), P(u1, zt, 0), P(u1, zt, -dep), P(u0, zt, -dep)], -UP, "RevealStone")
    if not door:
        m.facing([P(u0, zb, 0), P(u1, zb, 0), P(u1, zb, -dep), P(u0, zb, -dep)], UP, "RevealStone")
    pane = [P(u0, zb, -dep), P(u1, zb, -dep), P(u1, zt, -dep), P(u0, zt, -dep)]
    if door:
        m.facing(pane, n, dmat)
    else:
        g.facing(pane, n, "Glass")
    jw, so = trim.get("jamb", .18), trim.get("so", .28)
    um = (u0 + u1) / 2
    if lod == 0:
        b0 = -dep + .005
        if not door:                          # French casement: frame, meeting stile, three glazing bars
            a, c, z0, z1 = u0 + .003, u1 - .003, zb + .003, zt - .003
            lbox(m, w, a, a + .07, z0, z1, b0, b0 + .045, "Cream")
            lbox(m, w, c - .07, c, z0, z1, b0, b0 + .045, "Cream")
            lbox(m, w, a + .072, c - .072, z0, z0 + .07, b0, b0 + .045, "Cream")
            lbox(m, w, a + .072, c - .072, z1 - .07, z1, b0, b0 + .045, "Cream")
            lbox(m, w, um - .035, um + .035, z0 + .072, z1 - .072, b0, b0 + .041, "Cream")
            for k in (1, 2, 3):
                zk = z0 + (z1 - z0) * k / 4
                lbox(m, w, a + .072, c - .072, zk - .02, zk + .02, b0, b0 + .037, "Cream")
        else:                                 # two panelled leaves
            lbox(m, w, um - .03, um + .03, 0, zt - .003, b0, b0 + .05, dmat, ("in", "bot"))
            for l0, l1 in ((u0, um - .03), (um + .03, u1)):
                for p0, p1 in ((.3, zt * .42), (zt * .5, zt - .3)):
                    lbox(m, w, l0 + .14, l1 - .14, p0, p1, b0, b0 + .035, dmat)
        lbox(m, w, u0 - jw, u0, 0 if door else zb, zt, E, .10, "Dressed", ("in", "top", "bot"))
        lbox(m, w, u1, u1 + jw, 0 if door else zb, zt, E, .10, "Dressed", ("in", "top", "bot"))
        if trim.get("key", True):
            lbox(m, w, um - .15, um + .15, zt - .06, zt + .34, E, .16, "Dressed")
    if not door and kind != "fwin":           # French windows open onto a balcony: no sill
        lbox(m, w, u0 - so, u1 + so, zb - .14, zb, E, .14, "Dressed")
    lbox(m, w, u0 - so, u1 + so, zt, zt + .24, E, .12, "Dressed")


def shop_opening(m, g, w, h, lod, trim):
    """Shopfront in a wide ground-floor opening: panelled stallrisers, plate glass with mullions and a transom,
    a glazed shop door (trim['shopdoor'] = (u0, u1)). Frame colour is trim['door']."""
    u0, u1, zb, zt, _ = h
    P, n, t = w.P, w.n, w.t
    frame = trim.get("door", "Green")
    if lod == 2:
        g.facing([P(u0, 0, .02), P(u1, 0, .02), P(u1, zt, .02), P(u0, zt, .02)], n, "Glass")
        return
    dep = .30 if lod == 0 else .12
    m.facing([P(u0, 0, 0), P(u0, 0, -dep), P(u0, zt, -dep), P(u0, zt, 0)], t, "RevealStone")
    m.facing([P(u1, 0, 0), P(u1, 0, -dep), P(u1, zt, -dep), P(u1, zt, 0)], -t, "RevealStone")
    m.facing([P(u0, zt, 0), P(u1, zt, 0), P(u1, zt, -dep), P(u0, zt, -dep)], -UP, "RevealStone")
    da, db = trim.get("shopdoor", ((u0 + u1) / 2 - .5, (u0 + u1) / 2 + .5))
    sr, tr = .65, zt - .6
    pane = lambda a, b, z0, z1, d: [P(a, z0, d), P(b, z0, d), P(b, z1, d), P(a, z1, d)]
    for a, b, z0 in ((u0, da, sr), (db, u1, sr), (da, db, tr)):
        if b - a > .01:
            g.facing(pane(a, b, z0, zt, -dep), n, "Glass")
    m.facing(pane(da, db, 0, tr, -dep), n, frame)
    b0 = -dep
    post = .06 if lod == 0 else 0
    for a, b in ((u0 + E, da - post - E), (db + post + E, u1 - E)):
        lbox(m, w, a, b, 0, sr, b0, b0 + .10, frame, ("in", "bot"))
    if lod == 0:
        for c in (da - .03, db + .03):                       # door posts
            lbox(m, w, c - .03, c + .03, 0, zt - E, b0, b0 + .07, frame, ("in", "bot"))
        for a, b in ((u0, da), (db, u1)):                    # mullions
            k = max(1, round((b - a) / 1.3))
            for i in range(1, k):
                c = a + (b - a) * i / k
                lbox(m, w, c - .035, c + .035, sr + E, zt - E, b0, b0 + .065, frame, ("in",))
        lbox(m, w, u0 + E, u1 - E, tr - .04, tr + .04, b0, b0 + .05, frame, ("in",))
        for a, b in ((da + .12, db - .12),):                 # glazed door: kick panel and a glass light
            lbox(m, w, a, b, .15, .95, b0, b0 + .035, frame)
            g.facing(pane(a, b, 1.1, tr - .15, b0 + .03), n, "Glass")


def surface(m, g, w, z0, z1, mats, holes, lod, trim=None):
    """Wall face from z0 to z1 with the openings cut out. mats: [(z_from, z_to, material)];
    holes: (u0, u1, sill, head, 'win' or 'door') in wall coordinates."""
    trim = trim or {}
    cut = [] if lod == 2 else holes
    zs = {z0, z1} | {z for a, b, _ in mats for z in (a, b) if z0 < z < z1} | {z for h in cut for z in h[2:4] if z0 < z < z1}
    zs = sorted(zs)
    for za, zb in zip(zs, zs[1:]):
        mid = (za + zb) / 2
        mat = next(mm for a, b, mm in mats if a <= mid <= b)
        u = 0.0
        for a, b in sorted((h[0], h[1]) for h in cut if h[2] <= mid <= h[3]):
            if a > u:
                m.facing([w.P(u, za), w.P(a, za), w.P(a, zb), w.P(u, zb)], w.n, mat)
            u = b
        if u < w.L:
            m.facing([w.P(u, za), w.P(w.L, za), w.P(w.L, zb), w.P(u, zb)], w.n, mat)
    for h in holes:
        opening(m, g, w, h, lod, trim)


def band(m, w, z0, z1, proud, mat, s="x", e="x", cuts=(), shrink=None, skip=("in",)):
    """A course standing proud of the wall. Ends: 'x' an outside corner (the course wraps round it),
    'c' an inside corner (it stops short of the neighbour's course), '-' a plain end. cuts: (u0, u1) gaps."""
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
        if x1 - x0 > .02:
            lbox(m, w, x0, x1, z0, z1, E, proud, mat, skip)


def quoins(m, w, zlo, zhi, at):
    """Long-and-short stone quoins at an outside corner; the end of one wall pairs with the start of the next."""
    k_n = max(1, int((zhi - zlo + .04) / .54))
    h = (zhi - zlo - .04 * (k_n - 1)) / k_n
    for k in range(k_n):
        z0 = zlo + k * (h + .04)
        if at == "end":
            q = .85 if k % 2 == 0 else .45
            lbox(m, w, w.L - q, w.L + .08, z0, z0 + h, E, .08, "Dressed")
        else:
            q = .45 if k % 2 == 0 else .85
            lbox(m, w, 0, q, z0, z0 + h, E, .08, "Dressed")


def holes_for(w, bays, spec, door=None):
    """One opening per floor at each bay (world x or y); door = (bay, width, head) replaces that ground window."""
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


# ---------------------------------------------------------------- facades by style

def style(top, mats, win, belts=(), cornice=None, plinth=None, cap=None, rust=None, quoin_from=None, low=()):
    """A facade style. top: cornice top. mats: wall materials by height. win: (width, sill, head) per floor.
    belts: floor heights with a stone belt course. cornice: dict(fascia=(below_top, to_below_top, proud),
    corona=(below_top, proud), dentils=bool). plinth: (height, proud, mat). cap: (z0, z1, proud, mat).
    rust: heights of rustication joints. quoin_from: lowest quoin course (None = no quoins).
    low: indexes of low storeys (entresol, attic) whose windows are squarer (rulebook rule 4)."""
    return dict(top=top, mats=mats, win=win, belts=tuple(belts), cornice=cornice, plinth=plinth, cap=cap,
                rust=rust, quoin_from=quoin_from, low=tuple(low))


def cornice(m, w, st, s, e, lod, dentils=True, waive=None):
    c = st["cornice"]
    if not c:
        return
    top = st["top"]
    fb, ft, fp = c["fascia"]
    cb, cp = c["corona"]
    if lod == 0:
        nf_rules.check_cornice(m, w, top, cp, waive)
    if lod:
        band(m, w, top - fb, top, cp, "Dressed", s, e)
        return
    band(m, w, top - fb, top - ft, fp, "Dressed", s, e, shrink=cp + E if e == "c" else None, skip=("in", "top"))
    band(m, w, top - cb, top, cp, "Dressed", s, e)
    if dentils and c.get("dentils"):
        a = .45 if s == "c" else .3
        b = w.L - (.45 if e == "c" else .3)
        u = a
        while u + .12 <= b:
            lbox(m, w, u, u + .12, top - fb + .06, top - cb - E, fp + E, fp + .12, "Dressed")
            u += .3


def quoin_zones(st):
    lo = st["quoin_from"]
    hi = st["top"] - st["cornice"]["fascia"][0] - E if st["cornice"] else st["top"]
    zones = []
    for z in sorted(st["belts"]):
        b0, b1 = z - .08, z + .14
        if b1 <= lo:
            continue
        zones.append((lo, b0 - E))
        lo = b1 + E
    zones.append((lo, hi))
    return [zz for zz in zones if zz[1] - zz[0] > .5]


def wall(m, g, st, A, B, s, e, bays, lod, door=None, steps=None, mats=None, rust=True, belt_cuts=None,
         quoin=True, cornice_on=True, dentils=True, trim=None, belt_shrink=None, z0=0.0, shop=None, waive=None):
    """A whole facade from A to B in style st. s/e: corner type at each end ('x' outside, 'c' inside, '-' plain:
    a party-wall end on the lot line). bays: world x (or y) of each window column. door: (bay, width, head).
    steps: (from, to) world range. belt_cuts: {belt height: [(from, to) world ranges]}; belt_shrink: {belt
    height: shrink at an inside end}. z0: the wall starts higher up (above a lower block that butts in).
    shop: (from, to, head, door_from, door_to) world range of a shopfront that replaces the ground openings.
    waive: {rule key: reason} for a deliberate break of the rulebook (RULEBOOK.md)."""
    w = Wall(A, B)
    H = [h for h in holes_for(w, bays, st["win"], door) if h[2] >= z0 - 1e-6]
    if shop:
        a, b = sorted((w.u_of(shop[0]), w.u_of(shop[1])))
        H = [h for h in H if not (h[2] < 1.5 and h[0] < b and h[1] > a)] + [(a, b, 0.0, shop[2], "shop")]
        trim = dict(trim or {}, shopdoor=tuple(sorted((w.u_of(shop[3]), w.u_of(shop[4])))))
    surface(m, g, w, z0, st["top"], mats or st["mats"], H, lod, trim)
    if lod == 0:                               # the rulebook sees the wall as designed
        bands = []
        if st["plinth"] and z0 == 0:
            bands.append(("plinth", 0.0, st["plinth"][0], cuts_of(H, .25, ("door",)) + cuts_of(H, .30, ("shop",))))
        if st["cap"] and z0 == 0:
            bands.append(("stone cap", st["cap"][0], st["cap"][1], cuts_of(H, .25, ("door",)) + cuts_of(H, .30, ("shop",))))
        for z in st["belts"]:
            if z - .08 > z0 + .2:
                bands.append(("belt course", z - .08, z + .14, world_cuts(w, (belt_cuts or {}).get(z, ()))))
        if cornice_on and st["cornice"]:
            bands.append(("cornice", st["top"] - st["cornice"]["fascia"][0], st["top"], []))
        nf_rules.check_wall(m, w, st, s, e, bays, H, door, z0, trim, quoin, bands, waive)
    frame = (trim or {}).get("door", "Green")
    if lod < 2:
        if st["plinth"] and z0 == 0:
            z1, p, mat = st["plinth"]
            pc = cuts_of(H, .25, ("door",)) + cuts_of(H, .30, ("shop",)) + (world_cuts(w, [steps]) if steps else [])
            band(m, w, 0.0, z1, p, mat, s, e, pc, skip=("in", "bot"))
        if st["cap"] and z0 == 0:
            a, b, p, mat = st["cap"]
            band(m, w, a, b, p, mat, s, e, cuts_of(H, .25, ("door",)) + cuts_of(H, .30, ("shop",)))
        for z in st["belts"]:
            if z - .08 > z0 + .2:
                band(m, w, z - .08, z + .14, .12, "Dressed", s, e, world_cuts(w, (belt_cuts or {}).get(z, ())),
                     shrink=(belt_shrink or {}).get(z))
        if lod == 0 and rust and st["rust"]:
            rc = cuts_of(H, .28) + cuts_of(H, .30, ("shop",))
            for zc in st["rust"]:
                if zc > z0 + .1:
                    band(m, w, zc - .025, zc + .025, .025, (mats or st["mats"])[0][2], s, e, rc)
        if lod == 0 and quoin and st["quoin_from"] is not None:
            for zlo, zhi in quoin_zones(st):
                zlo = max(zlo, z0 + E)
                if zhi - zlo < .5:
                    continue
                if s == "x":
                    quoins(m, w, zlo, zhi, "start")
                if e == "x":
                    quoins(m, w, zlo, zhi, "end")
        if shop:                                   # shop pilasters, fascia board and its cap moulding
            ht = shop[2]
            for u0, u1 in ((a - .30, a), (b, b + .30)):
                lbox(m, w, u0, u1, 0, ht + .05 - E, E, .14, frame, ("in", "bot"))
            lbox(m, w, a - .30, b + .30, ht + .05, ht + .60, E, .16, frame, ("in", "top"))
            lbox(m, w, a - .36, b + .36, ht + .60, ht + .66, E, .22, frame)
    if cornice_on:
        cornice(m, w, st, s, e, lod, dentils, waive)
    return w


def party(m, A, B, z0, z1, mat):
    """A bare party wall on the side lot line: the neighbour's house will stand against it."""
    w = Wall(A, B)
    m.facing([w.P(0, z0), w.P(w.L, z0), w.P(w.L, z1), w.P(0, z1)], w.n, mat)
    return w


def flat_roof(m, x0, x1, y0, y1, z, mat="TinFlat"):
    m.facing([(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], UP, mat)


def balcony(m, w, z, depth, lod, s=.3, e=.3, consoles=(), rail="Iron", slab="Dressed", waive=None):
    """Continuous stone balcony on wall w, slab top at z (the French-window sill), from u=s to u=L-e, with a
    cast-iron railing. consoles: world x (or y) of the stone brackets under the slab."""
    u0, u1 = s, w.L - e
    if lod == 0:
        nf_rules.check_balcony(m, w, [(u0, u1, z - .18, z)] + [(w.u_of(c) - .11, w.u_of(c) + .11, z - .58, z - .18)
                                                             for c in consoles], waive)
    lbox(m, w, u0, u1, z - .18, z, E, depth, slab)
    if lod == 2:
        return
    if lod == 0:
        for c in consoles:
            uc = w.u_of(c)
            lbox(m, w, uc - .11, uc + .11, z - .58, z - .18 - E, E, depth - .18, slab, ("in", "top"))
    f0, f1 = depth - .10, depth - .04
    lbox(m, w, u0 + .04, u1 - .04, z + .92, z + 1.0, f0, f1, rail, ("in",))
    lbox(m, w, u0 + .04, u1 - .04, z + E, z + .07, f0, f1, rail, ("in", "bot"))
    for a in (u0 + .04, u1 - .10):                 # returns back to the wall
        lbox(m, w, a, a + .06, z + .92, z + 1.0, E, f0 - E, rail, ("in", "out"))
        lbox(m, w, a, a + .06, z + .07 + E, z + .92 - E, f0 + .01, f1 - .01, rail, ("in", "top", "bot"))
    step = .16 if lod == 0 else 1.2
    k = int((u1 - u0 - .3) / step)
    for i in range(1, k + 1):
        c = u0 + .10 + (u1 - u0 - .20) * i / (k + 1)
        hw = .012 if lod == 0 else .025
        lbox(m, w, c - hw, c + hw, z + .07 + E, z + .92 - E, f0 + .015, f1 - .015, rail, ("in", "top", "bot"))


def mansard_row(m, x0, x1, y0, y1, zc, h1, i1, h2, lod, sides=None, ridge="x",
                steep="SlateDark", deck="TinFlat", roll="TinOxide", end="Render"):
    """Two-stage mansard for rows and party-wall blocks. sides: {'y0','y1','x0','x1': 's' slope, 'e' end wall
    on a party line (filled in `end`), 'o' open (it runs into a taller block)}. The low deck rises to a ridge
    along `ridge`; it hips over sloped ends and becomes a gable on end walls."""
    sd = {**dict(y0="s", y1="s", x0="s", x1="s"), **(sides or {})}
    if ridge == "x":
        P = lambda p, q, z: (p, q, z)
        H = lambda hp, hq, hz: (hp, hq, hz)
        p0, p1, q0, q1 = x0, x1, y0, y1
        sf, sb, sl, sr = sd["y0"], sd["y1"], sd["x0"], sd["x1"]
        box = lambda pa, pb, qa, qb, za, zb2, sk: wbox(m, pa, pb, qa, qb, za, zb2, roll, sk)
    else:
        P = lambda p, q, z: (q, p, z)
        H = lambda hp, hq, hz: (hq, hp, hz)
        p0, p1, q0, q1 = y0, y1, x0, x1
        sf, sb, sl, sr = sd["x0"], sd["x1"], sd["y0"], sd["y1"]
        box = lambda pa, pb, qa, qb, za, zb2, sk: wbox(m, qa, qb, pa, pb, za, zb2, roll, sk)
    ap0, ap1 = p0 + (i1 if sl == "s" else 0), p1 - (i1 if sr == "s" else 0)
    aq0, aq1 = q0 + (i1 if sf == "s" else 0), q1 - (i1 if sb == "s" else 0)
    zb, zr = zc + h1, zc + h1 + h2
    B = lambda p, q: P(p, q, zc)
    I = lambda p, q: P(p, q, zb)
    for side, pts, (hp, hq) in ((sf, [B(p0, q0), B(p1, q0), I(ap1, aq0), I(ap0, aq0)], (0, -1)),
                                (sb, [B(p1, q1), B(p0, q1), I(ap0, aq1), I(ap1, aq1)], (0, 1)),
                                (sl, [B(p0, q1), B(p0, q0), I(ap0, aq0), I(ap0, aq1)], (-1, 0)),
                                (sr, [B(p1, q0), B(p1, q1), I(ap1, aq1), I(ap1, aq0)], (1, 0))):
        if side == "s":
            m.facing(pts, H(hp, hq, .4), steep)
        elif side == "e":
            m.facing(pts, H(hp, hq, 0), end)
    hw, qm = (aq1 - aq0) / 2, (aq0 + aq1) / 2
    r0 = ap0 + hw if sl == "s" else ap0
    r1 = ap1 - hw if sr == "s" else ap1
    R0, R1 = P(r0, qm, zr), P(r1, qm, zr)
    m.facing([I(ap0, aq0), I(ap1, aq0), R1, R0], H(0, -1, 1), deck)
    m.facing([I(ap1, aq1), I(ap0, aq1), R0, R1], H(0, 1, 1), deck)
    for side, pts, hp in ((sl, [I(ap0, aq1), I(ap0, aq0), R0], -1), (sr, [I(ap1, aq0), I(ap1, aq1), R1], 1)):
        if side == "s":
            m.facing(pts, H(hp, 0, 1), deck)
        elif side == "e":
            m.facing(pts, H(hp, 0, 0), end)
    if lod < 2:
        r = .06
        pa = ap0 - r if sl == "s" else p0 + E
        pb = ap1 + r if sr == "s" else p1 - E
        for side, q in ((sf, aq0), (sb, aq1)):
            if side == "s":
                box(pa, pb, q - r, q + r, zb - r, zb + r, ("z-",))
        qa = aq0 + r + E if sf == "s" else q0 + E
        qb = aq1 - r - E if sb == "s" else q1 - E
        for side, p in ((sl, ap0), (sr, ap1)):
            if side == "s":
                box(p - r, p + r, qa, qb, zb - r, zb + r, ("z-",))


# ---------------------------------------------------------------- roofs and features

def mansard(m, x0, x1, y0, y1, zc, h1, i1, h2, lod, along_y=False, open_front=False,
            steep="SlateDark", deck="TinFlat", roll="TinOxide"):
    """True two-stage mansard: steep brisis, lead roll at the break, low hipped deck (terrasson).
    open_front: no slope on the y0 side (the block runs into a taller one there)."""
    zb, zr = zc + h1, zc + h1 + h2
    ax0, ax1, ay1 = x0 + i1, x1 - i1, y1 - i1
    ay0 = y0 if open_front else y0 + i1
    B = lambda x, y: (x, y, zc)
    I = lambda x, y: (x, y, zb)
    if not open_front:
        m.facing([B(x0, y0), B(x1, y0), I(ax1, ay0), I(ax0, ay0)], (0, -1, .4), steep)
    m.facing([B(x1, y0), B(x1, y1), I(ax1, ay1), I(ax1, ay0)], (1, 0, .4), steep)
    m.facing([B(x1, y1), B(x0, y1), I(ax0, ay1), I(ax1, ay1)], (0, 1, .4), steep)
    m.facing([B(x0, y1), B(x0, y0), I(ax0, ay0), I(ax0, ay1)], (-1, 0, .4), steep)
    if not along_y:
        hw, ym = (ay1 - ay0) / 2, (ay0 + ay1) / 2
        R0, R1 = (ax0 + hw, ym, zr), (ax1 - hw, ym, zr)
        m.facing([I(ax0, ay0), I(ax1, ay0), R1, R0], (0, -1, 1), deck)
        m.facing([I(ax1, ay1), I(ax0, ay1), R0, R1], (0, 1, 1), deck)
        m.facing([I(ax0, ay1), I(ax0, ay0), R0], (-1, 0, 1), deck)
        m.facing([I(ax1, ay0), I(ax1, ay1), R1], (1, 0, 1), deck)
    else:
        hw, xm = (ax1 - ax0) / 2, (ax0 + ax1) / 2
        R0, R1 = (xm, ay0, zr), (xm, ay1 - hw, zr)
        m.facing([I(ax1, ay0), I(ax1, ay1), R1, R0], (1, 0, 1), deck)
        m.facing([I(ax0, ay1), I(ax0, ay0), R0, R1], (-1, 0, 1), deck)
        m.facing([I(ax1, ay1), I(ax0, ay1), R1], (0, 1, 1), deck)
    if lod < 2:
        r = .06
        ys0 = ay0 + E if open_front else ay0 + r + E
        if not open_front:
            wbox(m, ax0 - r, ax1 + r, ay0 - r, ay0 + r, zb - r, zb + r, roll, ("z-",))
        wbox(m, ax0 - r, ax1 + r, ay1 - r, ay1 + r, zb - r, zb + r, roll, ("z-",))
        wbox(m, ax0 - r, ax0 + r, ys0, ay1 - r - E, zb - r, zb + r, roll, ("z-",))
        wbox(m, ax1 - r, ax1 + r, ys0, ay1 - r - E, zb - r, zb + r, roll, ("z-",))


def lucarne(m, g, w, c, zc, width, win, ztop, zap, depth, lod, steep="SlateDark", waive=None):
    """Stone dormer standing on the cornice at the wall line w, centred on bay c. win: (width, sill, head)."""
    if lod == 0:
        nf_rules.check_lucarne(m, w, c, win, waive)
    uc = w.u_of(c)
    dw = Wall(w.P(uc - width / 2, 0, -.02), w.P(uc + width / 2, 0, -.02))
    ww, zb, zt = win
    surface(m, g, dw, zc, ztop, [(zc, ztop, "Dressed")], [(width / 2 - ww / 2, width / 2 + ww / 2, zb, zt, "win")], lod,
            dict(dep=.15, jamb=.12, so=.10, key=False))
    P = dw.P
    m.facing([P(0, zc, 0), P(0, zc, -depth), P(0, ztop, -depth), P(0, ztop, 0)], -dw.t, "Dressed")
    m.facing([P(width, zc, 0), P(width, zc, -depth), P(width, ztop, -depth), P(width, ztop, 0)], dw.t, "Dressed")
    lbox(m, dw, -.06, width + .06, ztop - .08, ztop + .04, E, .10, "Dressed")
    m.facing([P(0, ztop, 0), P(width, ztop, 0), P(width / 2, zap, 0)], dw.n, "Dressed")
    m.facing([P(0, ztop, 0), P(width / 2, zap, 0), P(width / 2, zap, -depth), P(0, ztop, -depth)], -dw.t + UP, steep)
    m.facing([P(width / 2, zap, 0), P(width, ztop, 0), P(width, ztop, -depth), P(width / 2, zap, -depth)], dw.t + UP, steep)


def chimney(m, x, y, sx, sy, z0, z1, lod, mat="Chimney"):
    wbox(m, x - sx, x + sx, y - sy, y + sy, z0, z1, mat, ("z-", "z+"))
    if lod < 2:
        wbox(m, x - sx - .08, x + sx + .08, y - sy - .08, y + sy + .08, z1, z1 + .2, "Dressed")
    if lod == 0:
        for k in (-1, 1):
            px = x + k * sx / 2
            wbox(m, px - .12, px + .12, y - .12, y + .12, z1 + .2, z1 + .6, mat, ("z-",))


def pediment(m, half, wall_y, zb, rise, back_y, lod, over=.35, steep="SlateDark", cx=0.0):
    """Street pediment over a frontispiece of half-width `half` whose wall stands at wall_y (facing -Y).
    Its roof runs back to back_y, which must lie inside the main roof."""
    yF, yT, yb = wall_y - over, wall_y, back_y
    xe, zr = half + over, zb + rise
    if lod == 2:
        m.facing([(cx - half, yT, zb), (cx + half, yT, zb), (cx, yT, zr - .2)], (0, -1, 0), "Dressed")
        m.facing([(cx - half, yT, zb), (cx, yT, zr - .2), (cx, yb, zr - .2), (cx - half, yb, zb)], (-.5, 0, 1), steep)
        m.facing([(cx, yT, zr - .2), (cx + half, yT, zb), (cx + half, yb, zb), (cx, yb, zr - .2)], (.5, 0, 1), steep)
        return
    zt = zr - .3
    xs = xe - .3 * xe / rise                  # where the underside of the raking cornice meets the base
    for k in (-1, 1):
        m.facing([(cx + k * xe, yF, zb), (cx, yF, zr), (cx, yF, zt), (cx + k * xs, yF, zb)], (0, -1, 0), "Dressed")
        m.facing([(cx + k * xs, yF, zb), (cx, yF, zt), (cx, yT, zt), (cx + k * xs, yT, zb)], (k * .5, 0, -1), "Dressed")
        m.facing([(cx + k * xe, yF, zb), (cx, yF, zr), (cx, yb, zr), (cx + k * xe, yb, zb)], (k * .5, 0, 1), steep)
    m.facing([(cx - xs, yT, zb), (cx + xs, yT, zb), (cx, yT, zt)], (0, -1, 0), "Dressed")
    if lod == 0:
        wbox(m, cx - .45, cx + .45, yT - .1, yT - E, zb + .5, zb + 1.3, "Dressed", ("y+",))


def pilasters(m, w, ranges, z0, z1, lod):
    """Colossal stone pilasters (world ranges along wall w) from z0 (just above a belt) to z1 (just under the cornice)."""
    if lod == 2:
        return
    for x0, x1 in ranges:
        u0, u1 = sorted((w.u_of(x0), w.u_of(x1)))
        if lod == 0:
            lbox(m, w, u0 - .06, u1 + .06, z0, z0 + .306, E, .20, "Dressed", ("in", "bot"))
            lbox(m, w, u0, u1, z0 + .306, z1 - .496, E, .15, "Dressed", ("in", "bot", "top"))
            lbox(m, w, u0 - .08, u1 + .08, z1 - .496, z1, E, .22, "Dressed")
        else:
            lbox(m, w, u0, u1, z0, z1, E, .15, "Dressed", ("in", "bot"))


def steps(m, x0, x1, wall_y, lod, mat="StoneBase"):
    """Two stone steps in front of a street door (wall facing -Y)."""
    if lod == 2:
        return
    wbox(m, x0, x1, wall_y - .55, wall_y - E, 0.0, .15, mat, ("z-", "y+"))
    wbox(m, x0, x1, wall_y - .30, wall_y - E, .15, .30, mat, ("z-", "y+"))
