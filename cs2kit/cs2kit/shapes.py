"""Pack-agnostic roof silhouettes, turrets, dormers, domes, and rounded architectural relief."""
import math
from .math_compat import Vector, E, UP
from .kit import Mesh, Wall, wbox, band, surface, gable_wall, roof_check, TRIM


def _vec(P, da, dq, dz):
    o, p = P(0.0, 0.0, 0.0), P(da, dq, dz)
    return tuple(b - a for a, b in zip(o, p))


def slab(m, prof, a0, a1, P, lod, mat, end=TRIM, eave=TRIM, th=0.16, what="roof"):
    """Closed extruded roof slab (Rule 15) along `a` from `a0` to `a1` using underside profile `prof` [(q, z)]."""
    t = Mesh()
    sa = 1 if a1 > a0 else -1
    for (qa, za), (qb, zb) in zip(prof, prof[1:]):
        nq, nz = -(zb - za), (qb - qa)
        if nz < 0:
            nq, nz = -nq, -nz
        t.facing([P(a0, qa, za + th), P(a0, qb, zb + th), P(a1, qb, zb + th), P(a1, qa, za + th)], _vec(P, 0, nq, nz), mat)
        t.facing([P(a0, qa, za), P(a0, qb, zb), P(a1, qb, zb), P(a1, qa, za)], _vec(P, 0, -nq, -nz), mat)
        for a, d in ((a0, -sa), (a1, sa)):
            t.facing([P(a, qa, za), P(a, qb, zb), P(a, qb, zb + th), P(a, qa, za + th)], _vec(P, d, 0, 0), end)
    for (q, z), (q2, _) in ((prof[0], prof[1]), (prof[-1], prof[-2])):
        sg = 1 if q > q2 else -1
        t.facing([P(a0, q, z), P(a1, q, z), P(a1, q, z + th), P(a0, q, z + th)], _vec(P, 0, sg, 0), eave)
    roof_check(m, t, what)


def dormer(m, g, P, roof_top, f, c, w, lod, mat, roof_mat, trim, rise=0.8, height=1.55, lites="2", trim_mat=TRIM):
    """Gable dormer standing on a roof slope with cheeks sunk into the slope."""
    rate = roof_top(f - 1.0) - roof_top(f)
    zb = roof_top(f) - 0.05
    zt = zb + height
    zr = zt + rise
    ob = f - (zt + 0.05 - roof_top(f)) / rate
    orr = f - (zr + 0.3 - roof_top(f)) / rate
    A, B = P(f, c - w / 2, 0)[:2], P(f, c + w / 2, 0)[:2]
    wl = Wall(A, B)
    out = _vec(P, 1, 0, 0)
    if wl.n[0] * out[0] + wl.n[1] * out[1] < 0:
        A, B = B, A
        wl = Wall(A, B)
    trim = dict(dict(so=0.16, key=False, lites=lites), **(trim or {}))
    ww = min(0.75, w - 0.5)
    holes = [(w / 2 - ww / 2, w / 2 + ww / 2, zb + 0.35, zt - 0.3, "win")]
    surface(m, g, wl, zb, zt, [(zb, zt, mat)], holes, lod, trim)
    gable_wall(m, g, A, B, zt, zr, lod, mat, trim=trim)
    for tt, d in ((c - w / 2, -1), (c + w / 2, 1)):
        m.facing([P(f, tt, zb), P(f, tt, zt), P(ob, tt, zt)], _vec(P, 0, d, 0), mat)
    h = w / 2 + 0.15
    k = rise / (w / 2)
    prof = [(c - h, zt - 0.15 * k), (c, zr), (c + h, zt - 0.15 * k)]
    slab(m, prof, orr, f + 0.2, P, lod, roof_mat, end=trim_mat, eave=trim_mat, th=0.12, what=f"dormer roof at t {c:.2f}")


def side_dormers(m, g, X, ze, zr, th, ys, lod, mat, roof_mat, trim, inset=1.0, w=1.5, sides=(1, -1), xc=0.0):
    """Dormers on both slopes of a front-gable roof."""
    s = (zr - ze) / X
    top = lambda o: ze + th + (X - o) * s
    for sd in sides:
        P = lambda o, t, z, sd=sd: (xc + sd * o, t, z)
        for y in ys:
            dormer(m, g, P, top, X - inset, y, w, lod, mat, roof_mat, trim)


def turret(
    m,
    g,
    cx,
    yw,
    a,
    z0,
    z1,
    rise,
    lod,
    mat,
    win,
    trim,
    roof="SlateDark",
    belts=(),
    lites="2",
    trim_mat=TRIM,
    plinth_mat="StoneBase",
):
    """Octagonal corner turret with broad closed cone cap."""
    trim = dict(dict(so=0.16, key=False, lites=lites), **(trim or {}))
    s = 2 * a * math.tan(math.pi / 8)
    pts = [
        (cx - a, yw),
        (cx - a, yw - s / 2),
        (cx - s / 2, yw - a),
        (cx + s / 2, yw - a),
        (cx + a, yw - s / 2),
        (cx + a, yw),
    ]
    for i, (A, B) in enumerate(zip(pts, pts[1:])):
        w = Wall(A, B)
        H = []
        if i in (1, 2, 3):
            ww = min(w.L - 0.4, 0.8 if i == 2 else 0.62)
            H = [(w.L / 2 - ww / 2, w.L / 2 + ww / 2, zb, zt, "win") for zb, zt in win]
        surface(m, g, w, z0, z1, [(z0, z1, mat)], H, lod, trim)
        if lod < 2:
            dz = -0.008 * (1 + i % 2)
            band(m, w, z1 - 0.30 + dz, z1 + dz, 0.07, trim_mat, "-", "-")
            for z in belts:
                band(m, w, z - 0.06 + dz, z + 0.10 + dz, 0.05, trim_mat, "-", "-")
            if z0 < 0.8:
                band(m, w, 0.0, 0.75 + dz, 0.05, plinth_mat, "-", "-", skip=("in", "bot"))
    R = (a + 0.32) / math.cos(math.pi / 8)
    zc = z1 + 0.02
    ring = [
        (cx + R * math.cos(math.radians(-112.5 + 45 * k)), yw + R * math.sin(math.radians(-112.5 + 45 * k)), zc)
        for k in range(8)
    ]
    apex = (cx, yw, zc + rise)
    t = Mesh()
    for k in range(8):
        p, q = ring[k], ring[(k + 1) % 8]
        mx, my = (p[0] + q[0]) / 2 - cx, (p[1] + q[1]) / 2 - yw
        t.facing([p, q, apex], (mx, my, 0.5), roof)
    t.facing(ring, (0, 0, -1), trim_mat)
    roof_check(m, t, f"turret cap at x {cx:.2f}")
    if lod < 2:
        wbox(m, cx - 0.06, cx + 0.06, yw - 0.06, yw + 0.06, zc + rise - 0.3, zc + rise + 0.55, trim_mat, ("z-",))
        if lod == 0:
            wbox(m, cx - 0.12, cx + 0.12, yw - 0.12, yw + 0.12, zc + rise + 0.2, zc + rise + 0.32, trim_mat)


def widows_walk(m, x0, x1, y0, y1, z0, z1, lod, mat, deck="Deck", trim_mat=TRIM):
    """Railed lookout deck straddling a ridge."""
    wbox(m, x0, x1, y0, y1, z0, z1, mat, ("z-", "z+"))
    m.facing([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], (0, 0, 1), deck)
    if lod < 2:
        wbox(m, x0 - 0.05, x1 + 0.05, y0 - 0.05, y1 + 0.05, z1 - 0.18, z1 - 0.02, trim_mat, ("z-",))
    if lod == 2:
        return
    zr = z1 + 0.9
    corners = [(x0 + 0.06, y0 + 0.06), (x1 - 0.06, y0 + 0.06), (x1 - 0.06, y1 - 0.06), (x0 + 0.06, y1 - 0.06)]
    for k, (ax, ay) in enumerate(corners):
        bx, by = corners[(k + 1) % 4]
        lo_x, hi_x, lo_y, hi_y = min(ax, bx) - 0.04, max(ax, bx) + 0.04, min(ay, by) - 0.04, max(ay, by) + 0.04
        dz = 0.0
        if k % 2:
            lo_y, hi_y, dz = lo_y + 0.08 + E, hi_y - 0.08 - E, -0.008
        wbox(m, lo_x, hi_x, lo_y, hi_y, zr - 0.07 + dz, zr + dz, trim_mat)
        wbox(m, ax - 0.07, ax + 0.07, ay - 0.07, ay + 0.07, z1 + E, zr + 0.12, trim_mat, ("z-",))
        if lod == 0:
            n = int(math.hypot(bx - ax, by - ay) / 0.16)
            for i in range(1, n):
                px, py = ax + (bx - ax) * i / n, ay + (by - ay) * i / n
                wbox(m, px - 0.02, px + 0.02, py - 0.02, py + 0.02, z1 + E, zr - 0.07 - E, trim_mat, ("z-", "z+"))
        else:
            wbox(m, lo_x, hi_x, lo_y, hi_y, z1 + E, z1 + 0.12 + dz, trim_mat, ("z-",))


def cornice_roof(m, x0, x1, y0, y1, z, lod, deep=0.45, top="TinFlat", side=TRIM, ends=None, brackets=(), front=True):
    """Closed flat roof behind a bracketed cornice."""
    t = Mesh()
    z1 = z + deep
    t.facing([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], (0, 0, 1), top)
    t.facing([(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], (0, 0, -1), side)
    t.facing([(x0, y0, z), (x1, y0, z), (x1, y0, z1), (x0, y0, z1)], (0, -1, 0), side)
    t.facing([(x0, y1, z), (x1, y1, z), (x1, y1, z1), (x0, y1, z1)], (0, 1, 0), side)
    for xx, d in ((x0, -1), (x1, 1)):
        t.facing([(xx, y0, z), (xx, y1, z), (xx, y1, z1), (xx, y0, z1)], (d, 0, 0), ends or side)
    roof_check(m, t, f"cornice roof y {y0:.2f}..{y1:.2f}")
    if lod < 2 and front:
        wbox(m, x0 + E, x1 - E, y0 - 0.06, y0 - E, z1 - 0.14, z1 + 0.04, side, ("y+",))
    if lod == 0:
        for bx in brackets:
            wbox(m, bx - 0.07, bx + 0.07, y0 + 0.05, y0 + 0.6, z - 0.55, z - E, side, ("z+",))
            wbox(m, bx - 0.09, bx + 0.09, y0 + 0.35, y0 + 0.6, z - 0.9, z - 0.55, side)


def pavilion_roof(m, x0, x1, y0, y1, ze, rise, lod, mat, finial=True, trim_mat=TRIM):
    """Steep hipped pavilion roof (closed solid, Rule 15) with ridge crest and optional finials."""
    w, d = x1 - x0, y1 - y0
    zr = ze + rise
    xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
    c = [(x0, y0, ze), (x1, y0, ze), (x1, y1, ze), (x0, y1, ze)]
    t = Mesh()
    if abs(w - d) < 0.05:
        apex = (xm, ym, zr)
        ends = [apex]
        for k in range(4):
            p_, q = c[k], c[(k + 1) % 4]
            t.facing([p_, q, apex], ((p_[0] + q[0]) / 2 - xm, (p_[1] + q[1]) / 2 - ym, 0.5), mat)
    elif w > d:
        h = d / 2
        r0, r1 = (x0 + h, ym, zr), (x1 - h, ym, zr)
        ends = [r0, r1]
        t.facing([c[0], c[1], r1, r0], (0, -1, 1), mat)
        t.facing([c[2], c[3], r0, r1], (0, 1, 1), mat)
        t.facing([c[3], c[0], r0], (-1, 0, 1), mat)
        t.facing([c[1], c[2], r1], (1, 0, 1), mat)
    else:
        h = w / 2
        r0, r1 = (xm, y0 + h, zr), (xm, y1 - h, zr)
        ends = [r0, r1]
        t.facing([c[1], c[2], r1, r0], (1, 0, 1), mat)
        t.facing([c[3], c[0], r0, r1], (-1, 0, 1), mat)
        t.facing([c[0], c[1], r0], (0, -1, 1), mat)
        t.facing([c[2], c[3], r1], (0, 1, 1), mat)
    t.facing(c, (0, 0, -1), trim_mat)
    roof_check(m, t, f"pavilion roof x {x0:.2f}..{x1:.2f}")
    if lod < 2 and len(ends) == 2:
        (ax, ay, _), (bx, by, _) = ends
        wbox(m, min(ax, bx) - 0.05, max(ax, bx) + 0.05, min(ay, by) - 0.05, max(ay, by) + 0.05, zr - 0.1, zr + 0.12, trim_mat, ("z-",))
    if lod < 2 and finial:
        for ex, ey, _ in ends:
            wbox(m, ex - 0.06, ex + 0.06, ey - 0.06, ey + 0.06, zr - 0.3, zr + 0.9, trim_mat, ("z-",))
            if lod == 0:
                wbox(m, ex - 0.13, ex + 0.13, ey - 0.13, ey + 0.13, zr + 0.3, zr + 0.42, trim_mat)
    return zr


def dome(m, g, cx, cy, r, z0, lod, mat, wall_mat, drum=1.7, sides=8, trim_mat=TRIM, glass_mat="Glass"):
    """Octagonal drum and closed bell dome (Rule 15)."""
    R = r / math.cos(math.pi / sides)
    ang = [math.radians(22.5 + 360 / sides * k) for k in range(sides)]
    zd = z0 + drum
    pts = [(cx + R * math.cos(a), cy + R * math.sin(a)) for a in ang]
    for k in range(sides):
        (ax, ay), (bx, by) = pts[k], pts[(k + 1) % sides]
        mx, my = (ax + bx) / 2 - cx, (ay + by) / 2 - cy
        m.facing([(ax, ay, z0), (bx, by, z0), (bx, by, zd), (ax, ay, zd)], (mx, my, 0), wall_mat)
        if lod < 2 and k % 2 == 0:
            nx, ny = mx / r, my / r
            wx, wy = (bx - ax) * 0.18, (by - ay) * 0.18
            ox, oy = cx + mx + nx * 0.02, cy + my + ny * 0.02
            g.facing(
                [(ox - wx, oy - wy, z0 + 0.45), (ox + wx, oy + wy, z0 + 0.45), (ox + wx, oy + wy, zd - 0.35), (ox - wx, oy - wy, zd - 0.35)],
                (nx, ny, 0),
                glass_mat,
            )
    if lod < 2:
        for k in range(sides):
            (ax, ay), (bx, by) = pts[k], pts[(k + 1) % sides]
            mx, my = (ax + bx) / 2 - cx, (ay + by) / 2 - cy
            f = 1 + 0.06 / r
            m.facing(
                [
                    (cx + (ax - cx) * f, cy + (ay - cy) * f, zd - 0.22),
                    (cx + (bx - cx) * f, cy + (by - cy) * f, zd - 0.22),
                    (cx + (bx - cx) * f, cy + (by - cy) * f, zd),
                    (cx + (ax - cx) * f, cy + (ay - cy) * f, zd),
                ],
                (mx, my, 0),
                trim_mat,
            )
    K = 3 if lod == 2 else 6
    H = 1.25 * r
    Ro = R + 0.15
    rings = []
    for i in range(K + 1):
        s = 0.88 * i / K
        rr = Ro * math.cos(s * math.pi / 2)
        rings.append([(cx + rr * math.cos(a), cy + rr * math.sin(a), zd + H * math.sin(s * math.pi / 2)) for a in ang])
    t = Mesh()
    for i in range(K):
        lo, hi = rings[i], rings[i + 1]
        for k in range(sides):
            a_, b_ = lo[k], lo[(k + 1) % sides]
            c_, d_ = hi[(k + 1) % sides], hi[k]
            t.facing([a_, b_, c_, d_], ((a_[0] + b_[0]) / 2 - cx, (a_[1] + b_[1]) / 2 - cy, 0.4 + i / K), mat)
    t.facing(rings[-1], (0, 0, 1), mat)
    t.facing(rings[0], (0, 0, -1), trim_mat)
    roof_check(m, t, f"dome at x {cx:.2f}")
    return rings[-1][0][2]


def tube(m, points, radii, mat, sides=8):
    """Closed polygonal tube swept along `points` with per-point `radii`."""
    rings = []
    for i, p in enumerate(points):
        p = Vector(p)
        direction = Vector(points[min(i + 1, len(points) - 1)]) - Vector(points[max(0, i - 1)])
        direction.normalize()
        ref = Vector((0, 0, 1)) if abs(direction.z) < 0.9 else Vector((0, 1, 0))
        u = direction.cross(ref).normalized()
        v = direction.cross(u).normalized()
        rings.append(
            [tuple(p + radii[i] * (u * math.cos(2 * math.pi * k / sides) + v * math.sin(2 * math.pi * k / sides))) for k in range(sides)]
        )
    for i in range(len(rings) - 1):
        center = (Vector(points[i]) + Vector(points[i + 1])) * 0.5
        for k in range(sides):
            q = [rings[i][k], rings[i][(k + 1) % sides], rings[i + 1][(k + 1) % sides], rings[i + 1][k]]
            m.facing(q, tuple(sum((Vector(v) for v in q), Vector()) / 4 - center), mat)
    m.facing(rings[0], tuple(Vector(points[0]) - Vector(points[1])), mat)
    m.facing(rings[-1], tuple(Vector(points[-1]) - Vector(points[-2])), mat)


def curved_strip(m, P, pts, w0, w1, d0, d1, mat, step=0.004):
    """Continuous Catmull-Rom elliptical relief strip mapped onto wall projector P(u, z, d)."""
    path = []
    for i in range(len(pts) - 1):
        a = Vector(pts[max(0, i - 1)])
        b = Vector(pts[i])
        c = Vector(pts[i + 1])
        d = Vector(pts[min(len(pts) - 1, i + 2)])
        for j in range(3):
            t = j / 3
            v = 0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (-a + 3 * b - 3 * c + d) * t * t * t)
            path.append(v)
    path.append(Vector(pts[-1]))
    rings = []
    depth = (d1 - d0) * 0.5
    for i, p in enumerate(path):
        tangent = path[min(i + 1, len(path) - 1)] - path[max(0, i - 1)]
        tangent.normalize()
        normal = Vector((-tangent.y, tangent.x, 0.0))
        width = (w0 + (w1 - w0) * i / max(1, len(path) - 1)) * 0.5
        rings.append(
            [
                P(
                    p.x + normal.x * width * math.cos(2 * math.pi * k / 6),
                    p.y + normal.y * width * math.cos(2 * math.pi * k / 6),
                    (d0 + d1) * 0.5 + step * i / 3 + depth * math.sin(2 * math.pi * k / 6),
                )
                for k in range(6)
            ]
        )
    for i in range(len(rings) - 1):
        center = Vector(P((path[i].x + path[i + 1].x) * 0.5, (path[i].y + path[i + 1].y) * 0.5, (d0 + d1) * 0.5))
        for k in range(6):
            q = [rings[i][k], rings[i][(k + 1) % 6], rings[i + 1][(k + 1) % 6], rings[i + 1][k]]
            m.facing(q, tuple(sum((Vector(v) for v in q), Vector()) / 4 - center), mat)
