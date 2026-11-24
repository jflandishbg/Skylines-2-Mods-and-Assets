"""Lobstertown silhouette pieces (Claude, 2026-11-14, after the Toronto study): the shapes that make a row of
narrow houses read as different houses from the street and from above.

  slab           any closed roof slab: a profile extruded along an axis (saltbox, dormer roofs)
  dormer         a gable dormer standing on a roof slope, cheeks sunk into the slope
  turret         an octagonal corner turret with a broad cone, stopping at the main eave
  widows_walk    a railed lookout deck straddling a ridge
  cornice_roof   a flat roof behind a deep bracketed cornice (triple-decker)
  pavilion_roof  a steep hipped (pavilion) roof over a square or oblong tower, closed, with a crest and finials
  dome           an octagonal drum and a bell dome, closed, its flat crown ready for a lantern (château crowns)

Same frame and rules as lt_kit: lot centre origin, street at -Y, z up; every roof is a closed solid (rule 15).
"""
import math
from lt_kit import Mesh, Wall, wbox, band, surface, gable_wall, roof_check, E, TRIM


def _vec(P, da, dq, dz):
    o, p = P(0.0, 0.0, 0.0), P(da, dq, dz)
    return tuple(b - a for a, b in zip(o, p))


def slab(m, prof, a0, a1, P, lod, mat, end=TRIM, eave=TRIM, th=.16, what="roof"):
    """A closed roof slab: the profile prof [(q, z), ...] (the underside outline, eave to eave) extruded along a
    from a0 to a1. P(a, q, z) -> world point. end: material of the two cut ends; eave: the two eave edges."""
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


def dormer(m, g, P, roof_top, f, c, w, lod, mat, roof_mat, trim, rise=.8, height=1.55, lites="2"):
    """A gable dormer on a roof slope. Local frame: o runs outward (down the slope, towards the eave), t along
    the dormer face, z up; P(o, t, z) -> world. roof_top(o): height of the main roof's top surface.
    f: where the face stands (o); c, w: its centre and width along t. The cheeks run back into the slope and
    sink 5 cm into it, so nothing shows daylight; the dormer roof runs on into the main roof."""
    rate = roof_top(f - 1.0) - roof_top(f)                  # the slope climbs this much per metre inward
    zb = roof_top(f) - .05
    zt = zb + height
    zr = zt + rise
    ob = f - (zt + .05 - roof_top(f)) / rate                # where the cheek top meets the slope
    orr = f - (zr + .3 - roof_top(f)) / rate                # the dormer ridge runs in this far
    A, B = P(f, c - w / 2, 0)[:2], P(f, c + w / 2, 0)[:2]
    wl = Wall(A, B)
    out = _vec(P, 1, 0, 0)
    if wl.n[0] * out[0] + wl.n[1] * out[1] < 0:
        A, B = B, A
        wl = Wall(A, B)
    trim = dict(dict(so=.16, key=False, lites=lites), **(trim or {}))
    ww = min(.75, w - .5)
    holes = [(w / 2 - ww / 2, w / 2 + ww / 2, zb + .35, zt - .3, "win")]
    surface(m, g, wl, zb, zt, [(zb, zt, mat)], holes, lod, trim)
    gable_wall(m, g, A, B, zt, zr, lod, mat, trim=trim)
    for tt, d in ((c - w / 2, -1), (c + w / 2, 1)):          # the cheeks
        m.facing([P(f, tt, zb), P(f, tt, zt), P(ob, tt, zt)], _vec(P, 0, d, 0), mat)
    h = w / 2 + .15
    k = rise / (w / 2)
    prof = [(c - h, zt - .15 * k), (c, zr), (c + h, zt - .15 * k)]
    slab(m, prof, orr, f + .2, P, lod, roof_mat, th=.12, what=f"dormer roof at t {c:.2f}")


def side_dormers(m, g, X, ze, zr, th, ys, lod, mat, roof_mat, trim, inset=1.0, w=1.5, sides=(1, -1), xc=0.0):
    """Dormers on both slopes of a front-gable roof (eaves at x = xc +- X, ridge on x = xc)."""
    s = (zr - ze) / X
    top = lambda o: ze + th + (X - o) * s
    for sd in sides:
        P = (lambda o, t, z, sd=sd: (xc + sd * o, t, z))
        for y in ys:
            dormer(m, g, P, top, X - inset, y, w, lod, mat, roof_mat, trim)


def turret(m, g, cx, yw, a, z0, z1, rise, lod, mat, win, trim, roof="SlateDark", belts=(), lites="2"):
    """An octagonal corner turret on a street wall at yw (facing -Y), flat face to the street, apothem a,
    walls from z0 to z1 (it stops at the main eave so it adds no roof level), then a broad octagonal cone
    `rise` high. win: [(sill, head)] per floor; the three street faces carry windows."""
    trim = dict(dict(so=.16, key=False, lites=lites), **(trim or {}))
    s = 2 * a * math.tan(math.pi / 8)
    pts = [(cx - a, yw), (cx - a, yw - s / 2), (cx - s / 2, yw - a), (cx + s / 2, yw - a), (cx + a, yw - s / 2), (cx + a, yw)]
    for i, (A, B) in enumerate(zip(pts, pts[1:])):
        w = Wall(A, B)
        H = []
        if i in (1, 2, 3):
            ww = min(w.L - .4, .8 if i == 2 else .62)
            H = [(w.L / 2 - ww / 2, w.L / 2 + ww / 2, zb, zt, "win") for zb, zt in win]
        surface(m, g, w, z0, z1, [(z0, z1, mat)], H, lod, trim)
        if lod < 2:
            dz = -.008 * (1 + i % 2)
            band(m, w, z1 - .30 + dz, z1 + dz, .07, TRIM, "-", "-")
            for z in belts:
                band(m, w, z - .06 + dz, z + .10 + dz, .05, TRIM, "-", "-")
            if z0 < .8:
                band(m, w, 0.0, .75 + dz, .05, "StoneBase", "-", "-", skip=("in", "bot"))
    # the cap: a closed octagonal cone with a white soffit under its overhang
    R = (a + .32) / math.cos(math.pi / 8)
    zc = z1 + .02
    ring = [(cx + R * math.cos(math.radians(-112.5 + 45 * k)), yw + R * math.sin(math.radians(-112.5 + 45 * k)), zc)
            for k in range(8)]
    apex = (cx, yw, zc + rise)
    t = Mesh()
    for k in range(8):
        p, q = ring[k], ring[(k + 1) % 8]
        mx, my = (p[0] + q[0]) / 2 - cx, (p[1] + q[1]) / 2 - yw
        t.facing([p, q, apex], (mx, my, .5), roof)
    t.facing(ring, (0, 0, -1), TRIM)
    roof_check(m, t, f"turret cap at x {cx:.2f}")
    if lod < 2:                                               # a finial
        wbox(m, cx - .06, cx + .06, yw - .06, yw + .06, zc + rise - .3, zc + rise + .55, TRIM, ("z-",))
        if lod == 0:
            wbox(m, cx - .12, cx + .12, yw - .12, yw + .12, zc + rise + .2, zc + rise + .32, TRIM)


def widows_walk(m, x0, x1, y0, y1, z0, z1, lod, mat, deck="Deck"):
    """A railed lookout deck straddling a ridge: a low shingled box rising out of the roof (z0 is inside the
    roof) with a deck on top at z1 and a white balustrade round it."""
    wbox(m, x0, x1, y0, y1, z0, z1, mat, ("z-", "z+"))
    m.facing([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], (0, 0, 1), deck)
    if lod < 2:
        wbox(m, x0 - .05, x1 + .05, y0 - .05, y1 + .05, z1 - .18, z1 - .02, TRIM, ("z-",))    # cap moulding
    if lod == 2:
        return
    zr = z1 + .9
    corners = [(x0 + .06, y0 + .06), (x1 - .06, y0 + .06), (x1 - .06, y1 - .06), (x0 + .06, y1 - .06)]
    for k, (ax, ay) in enumerate(corners):
        bx, by = corners[(k + 1) % 4]
        lo_x, hi_x, lo_y, hi_y = min(ax, bx) - .04, max(ax, bx) + .04, min(ay, by) - .04, max(ay, by) + .04
        dz = 0.0
        if k % 2:                                     # along y: between the x rails, a touch lower
            lo_y, hi_y, dz = lo_y + .08 + E, hi_y - .08 - E, -.008
        wbox(m, lo_x, hi_x, lo_y, hi_y, zr - .07 + dz, zr + dz, TRIM)                          # top rail
        wbox(m, ax - .07, ax + .07, ay - .07, ay + .07, z1 + E, zr + .12, TRIM, ("z-",))       # corner post
        if lod == 0:
            n = int(math.hypot(bx - ax, by - ay) / .16)
            for i in range(1, n):
                px, py = ax + (bx - ax) * i / n, ay + (by - ay) * i / n
                wbox(m, px - .02, px + .02, py - .02, py + .02, z1 + E, zr - .07 - E, TRIM, ("z-", "z+"))
        else:
            wbox(m, lo_x, hi_x, lo_y, hi_y, z1 + E, z1 + .12 + dz, TRIM, ("z-",))             # bottom rail


def cornice_roof(m, x0, x1, y0, y1, z, lod, deep=.45, top="TinFlat", side=TRIM, ends=None, brackets=(), front=True):
    """A flat roof behind a deep bracketed cornice, as on a Portland triple-decker: a closed box from the wall
    top z up `deep`, white fascia and soffit, roofing on top. ends: material of the two x ends (party lines).
    brackets: x of each scroll bracket under the front edge. front=False: the y0 edge butts a taller wall (no crown
    moulding there: hidden trim reads as a blank band)."""
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
        wbox(m, x0 + E, x1 - E, y0 - .06, y0 - E, z1 - .14, z1 + .04, side, ("y+",))          # crown moulding
    if lod == 0:
        for bx in brackets:                                   # scroll brackets under the front edge
            wbox(m, bx - .07, bx + .07, y0 + .05, y0 + .6, z - .55, z - E, side, ("z+",))
            wbox(m, bx - .09, bx + .09, y0 + .35, y0 + .6, z - .9, z - .55, side)


def pavilion_roof(m, x0, x1, y0, y1, ze, rise, lod, mat, finial=True):
    """A château pavilion roof: a steep hip over the rectangle x0..x1, y0..y1 (eaves included) from ze up `rise`,
    the ridge along the longer side (a pyramid on a square). One closed solid (rule 15): four slopes and a white
    soffit. A ridge crest and finials at the ridge ends close up. Returns the ridge height."""
    w, d = x1 - x0, y1 - y0
    zr = ze + rise
    xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
    c = [(x0, y0, ze), (x1, y0, ze), (x1, y1, ze), (x0, y1, ze)]
    t = Mesh()
    if abs(w - d) < .05:                                  # a pyramid
        apex = (xm, ym, zr)
        ends = [apex]
        for k in range(4):
            p_, q = c[k], c[(k + 1) % 4]
            t.facing([p_, q, apex], ((p_[0] + q[0]) / 2 - xm, (p_[1] + q[1]) / 2 - ym, .5), mat)
    elif w > d:                                           # ridge along x
        h = d / 2
        r0, r1 = (x0 + h, ym, zr), (x1 - h, ym, zr)
        ends = [r0, r1]
        t.facing([c[0], c[1], r1, r0], (0, -1, 1), mat)
        t.facing([c[2], c[3], r0, r1], (0, 1, 1), mat)
        t.facing([c[3], c[0], r0], (-1, 0, 1), mat)
        t.facing([c[1], c[2], r1], (1, 0, 1), mat)
    else:                                                 # ridge along y
        h = w / 2
        r0, r1 = (xm, y0 + h, zr), (xm, y1 - h, zr)
        ends = [r0, r1]
        t.facing([c[1], c[2], r1, r0], (1, 0, 1), mat)
        t.facing([c[3], c[0], r0, r1], (-1, 0, 1), mat)
        t.facing([c[0], c[1], r0], (0, -1, 1), mat)
        t.facing([c[2], c[3], r1], (0, 1, 1), mat)
    t.facing(c, (0, 0, -1), TRIM)
    roof_check(m, t, f"pavilion roof x {x0:.2f}..{x1:.2f}")
    if lod < 2 and len(ends) == 2:                        # an iron crest along the ridge
        (ax, ay, _), (bx, by, _) = ends
        wbox(m, min(ax, bx) - .05, max(ax, bx) + .05, min(ay, by) - .05, max(ay, by) + .05, zr - .1, zr + .12,
             TRIM, ("z-",))
    if lod < 2 and finial:                                # needle finials at the ridge ends
        for ex, ey, _ in ends:
            wbox(m, ex - .06, ex + .06, ey - .06, ey + .06, zr - .3, zr + .9, TRIM, ("z-",))
            if lod == 0:
                wbox(m, ex - .13, ex + .13, ey - .13, ey + .13, zr + .3, zr + .42, TRIM)
    return zr


def dome(m, g, cx, cy, r, z0, lod, mat, wall_mat, drum=1.7, sides=8):
    """A château crown: an octagonal drum of apothem r standing on a flat deck at z0 (round windows on four
    faces), then a bell dome rising 1.25 r to a flat octagonal crown where a lantern sits. The dome is one closed
    solid (rule 15). Returns the crown height."""
    R = r / math.cos(math.pi / sides)
    ang = [math.radians(22.5 + 360 / sides * k) for k in range(sides)]
    zd = z0 + drum
    pts = [(cx + R * math.cos(a), cy + R * math.sin(a)) for a in ang]
    for k in range(sides):                                # the drum
        (ax, ay), (bx, by) = pts[k], pts[(k + 1) % sides]
        mx, my = (ax + bx) / 2 - cx, (ay + by) / 2 - cy
        m.facing([(ax, ay, z0), (bx, by, z0), (bx, by, zd), (ax, ay, zd)], (mx, my, 0), wall_mat)
        if lod < 2 and k % 2 == 0:                        # a window on every other face
            nx, ny = mx / r, my / r
            wx, wy = (bx - ax) * .18, (by - ay) * .18
            ox, oy = cx + mx + nx * .02, cy + my + ny * .02
            (g if True else m).facing([(ox - wx, oy - wy, z0 + .45), (ox + wx, oy + wy, z0 + .45),
                                       (ox + wx, oy + wy, zd - .35), (ox - wx, oy - wy, zd - .35)], (nx, ny, 0), "Glass")
    if lod < 2:                                           # a white band where drum meets dome
        for k in range(sides):
            (ax, ay), (bx, by) = pts[k], pts[(k + 1) % sides]
            mx, my = (ax + bx) / 2 - cx, (ay + by) / 2 - cy
            f = 1 + .06 / r
            m.facing([(cx + (ax - cx) * f, cy + (ay - cy) * f, zd - .22), (cx + (bx - cx) * f, cy + (by - cy) * f, zd - .22),
                      (cx + (bx - cx) * f, cy + (by - cy) * f, zd), (cx + (ax - cx) * f, cy + (ay - cy) * f, zd)],
                     (mx, my, 0), TRIM)
    K = 3 if lod == 2 else 6
    H = 1.25 * r
    Ro = R + .15
    rings = []
    for i in range(K + 1):                                # bell profile: a quarter ellipse, stopped at 88 %
        s = .88 * i / K
        rr = Ro * math.cos(s * math.pi / 2)
        rings.append([(cx + rr * math.cos(a), cy + rr * math.sin(a), zd + H * math.sin(s * math.pi / 2)) for a in ang])
    t = Mesh()
    for i in range(K):
        lo, hi = rings[i], rings[i + 1]
        for k in range(sides):
            a_, b_ = lo[k], lo[(k + 1) % sides]
            c_, d_ = hi[(k + 1) % sides], hi[k]
            t.facing([a_, b_, c_, d_], ((a_[0] + b_[0]) / 2 - cx, (a_[1] + b_[1]) / 2 - cy, .4 + i / K), mat)
    t.facing(rings[-1], (0, 0, 1), mat)
    t.facing(rings[0], (0, 0, -1), TRIM)
    roof_check(m, t, f"dome at x {cx:.2f}")
    return rings[-1][0][2]
