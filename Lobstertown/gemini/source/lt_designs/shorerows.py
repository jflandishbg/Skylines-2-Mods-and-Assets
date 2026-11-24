"""Lobstertown L1 "Shore Rows", second edition (the author 2026-11-17, Direction B): painted ladies on 1-wide row lots.
Late-Victorian Carpenter Gothic and its cousins, every house in a strong period paint with a contrasting trim:

  gothic     Gothic Revival cottages: a steep centre gable on a side-gabled house, or a steep front gable, with
             sawn bargeboards, a finial and pendant, lancet attic windows, board-and-batten
  queenanne  Queen Anne: a small WOODEN turret or tower (never stone, never the chateau's), fishscale gables and
             upper storeys, spindle friezes on the porches, canted bays, cross-gabled roofs, a wraparound porch on a corner
  stick      Stick style: steep gables with a king-post truss, stickwork boards over the clapboard, a square tower
  triple     painted triple-deckers: stacked porches under a gabled porch tower, a diamond band

Behind, every house has its own rear: an ell (gabled, cross-gabled or a lean-to), a one- or two-storey back porch,
a woodshed, a back house, a carriage house (across-gable, gambrel or hipped, some with a cupola), in clapboard or
board-and-batten, each roofed in its own material. Rear pieces are fitted to the lot depth (rule 17: built out to
.6 m from the rear line) and kept to the porch (LOW) or the two-storey (MID) eave level, so with the main eave and a
tower at most three roof levels show.

    build(lod, D, **variant)    D = lot depth in cells (2..6); variant keys below (DEFAULT)

Paint: Clapboard is colour 1 (the body), Fishscale / DiamondBand / BoardBatten are colour 0 (the accent), TrimWhite
is colour 2 (the trim): lt_roster PALETTES['victorian'] gives every set all three.
"""
import math
from lt_kit import (Mesh, Wall, party, chimney, finish, wall, style, gable_wall, gable_roof, shed_roof, porch, bay,
                    wbox, lbox, band, holes_for, surface, E, TRIM)
from lt_shapes import slab, side_dormers, turret, cornice_roof, pavilion_roof

X = 3.99                      # party walls on the side lot lines
CI = .40                      # a corner building's street-side wall stands this far in
BX = 1.0                      # narrow rear pieces run from the left wall to BX, leaving a 3 m yard
SET = 3.6                     # main front wall back from the lot front (porch and steps in front)
WIN1 = [(.9, 1.0, 2.7)]
WIN2 = [(.9, 1.55, 3.25), (.9, 4.4, 5.9)]
WIN3 = [(.9, 1.55, 3.25), (.9, 4.55, 6.25), (.9, 7.5, 8.95)]
WIN4 = WIN3 + [(.9, 10.5, 11.95)]
TOPS = {2: 6.7, 3: 9.9, 4: 12.9}
BELTS = {2: (3.75,), 3: (3.75, 6.85), 4: (3.75, 6.85, 9.85)}
WINS = {2: WIN2, 3: WIN3, 4: WIN4}
BAND = (8 * .4668, 9 * .4668)  # the diamond band: one tile high, on the atlas grid (lt_atlas VIC_RENAME)
LOW, MID = 3.55, 6.7          # rear eave levels: with the porches, and with a two-storey house
SIDE_HALL = {"balance": "side-hall row house: the door takes one side bay, as on every narrow New England row"}

DEFAULT = dict(storeys=3, roof="gable", rise=4.3, depth=11.0, pitch=1.0, xgables=(), xpitch=1.4, corner=False,
               ci=CI, hand="L", wall="Clapboard", upper=None, band=False, gable_mat="Fishscale", gwin="pair",
               roof_mat="SlateDark", door="Oxblood", shutters=None, lites="2", door_x=-2.5, bays=None,
               porch="full", porch_x=None, spindles=True, bay=None, tower=None, oriel=False, dormers=False,
               barge=False, finial=False, truss=False, stick=False, backporch=0, chimney=1, rear=(),
               wrap_len=6.0, side_bays=None)

# a rear piece: k 'ell' (narrow, XL..BX) | 'carriage' (full width, always last); h eave; roof 'gable' (ridge along
# the lot) | 'cross' (ridge across: a gable to the yard) | 'shed' (lean-to, high on the party line) | carriage roofs
# 'across' | 'gambrel' | 'hip'; L preferred and min length; grow takes the slack; piazza 0/1/2 storeys of porch along
# the yard wall; cupola on a carriage roof; barge: a sawn bargeboard on the yard gable
PIECE = dict(k="ell", h=LOW, roof="gable", mat="Clapboard", rmat="SlateDark", L=7.0, min=3.0, grow=False, piazza=0,
             cupola=False, barge=False, rise=None)


# ---------------------------------------------------------------- helpers

def layers(top, *spans):
    """Wall materials by height, (z0, z1, mat) bands; later spans paint over earlier ones."""
    zs = sorted({0.0, top} | {z for a, b, _ in spans for z in (a, b) if 0 < z < top})
    out = []
    for a, b in zip(zs, zs[1:]):
        mid = (a + b) / 2
        mat = [mm for z0, z1, mm in spans if z0 <= mid <= z1][-1]
        if out and out[-1][2] == mat:
            out[-1] = (out[-1][0], b, mat)
        else:
            out.append((a, b, mat))
    return out


def turn(m, t, fn):
    """Copy the faces of scratch mesh t into m, every point mapped by fn (a rotation; winding kept, or reversed when
    fn mirrors: pass a mirror as (fn, True))."""
    flip = False
    if isinstance(fn, tuple):
        fn, flip = fn
    for f, k in zip(t.f, t.m):
        pts = [fn(*t.v[i]) for i in f]
        if flip:
            pts = pts[::-1]
        mat = t.mats[k]
        if mat not in m.mats:
            m.mats.append(mat)
        i = len(m.v)
        m.v += pts
        m.f.append(list(range(i, i + len(pts))))
        m.m.append(m.mats.index(mat))


def rake_pts(x0, x1, ze, zr, sides=("p", "p"), knee=None):
    """The underside outline of a gable_roof (x, z), eave to eave, as lt_kit builds it."""
    xm = (x0 + x1) / 2
    if knee:
        zk, ik = knee
        prof = [(x0, ze), (x0 + ik, zk), (xm, zr), (x1 - ik, zk), (x1, ze)]
    else:
        prof = [(x0, ze), (xm, zr), (x1, ze)]
    for idx, sd in ((0, sides[0]), (-1, sides[1])):
        if sd == "e":
            (xa, za), (xb, zb) = (prof[0], prof[1]) if idx == 0 else (prof[-1], prof[-2])
            f = .35 / abs(xb - xa)
            prof[idx] = (xa - (xb - xa) * f, za - (zb - za) * f)
    return prof


def bargeboard(m, prof, pt, n, lod, deep=.36):
    """A sawn bargeboard under the rakes of a gable: prof [(a, z), ...] the slab's underside outline along the
    gable, pt(a, z) -> the world point on the board's plane, n its outward normal. A board .16 deep with a
    scalloped drop under every bay (close up); a plain board at LOD1."""
    if lod == 2:
        return
    for (xa, za), (xb, zb) in zip(prof, prof[1:]):
        L = math.hypot(xb - xa, zb - za)
        k = max(3, round(L / .42)) if lod == 0 else 1
        for i in range(k):
            a0, a1 = xa + (xb - xa) * i / k, xa + (xb - xa) * (i + 1) / k
            z0, z1 = za + (zb - za) * i / k, za + (zb - za) * (i + 1) / k
            m.facing([pt(a0, z0 - .16), pt(a1, z1 - .16), pt(a1, z1), pt(a0, z0)], n, TRIM)
            if lod == 0:
                m.facing([pt(a0, z0 - .16), pt((a0 + a1) / 2, (z0 + z1) / 2 - deep), pt(a1, z1 - .16)], n, TRIM)


def finial(m, x, y_spike, y_drop, zr, lod, th=.16):
    """A turned finial standing on a gable apex, and a pendant hanging under the apex of the bargeboard."""
    if lod == 2:
        return
    wbox(m, x - .05, x + .05, y_spike - .05, y_spike + .05, zr + th - .04, zr + th + 1.0, TRIM, ("z-",))
    if lod == 0:
        wbox(m, x - .1, x + .1, y_spike - .1, y_spike + .1, zr + th + .5, zr + th + .62, TRIM)
        wbox(m, x - .06, x + .06, y_drop - .06, y_drop + .06, zr - .95, zr - .04, TRIM, ("z+",))


def truss(m, prof, y, lod):
    """Stick style: a king-post truss in the gable end under the overhang - collar tie, king post, two struts."""
    if lod == 2:
        return
    (x0, ze), (xm, zr), (x1, _) = prof[0], prof[len(prof) // 2], prof[-1]
    zc = ze + .42 * (zr - ze)
    f = (zc - ze) / (zr - ze)
    xl, xr = x0 + f * (xm - x0), x1 - f * (x1 - xm)
    wbox(m, xl + .05, xr - .05, y, y + .1, zc - .09, zc + .09, TRIM)
    wbox(m, xm - .07, xm + .07, y, y + .1, zc + .09 + E, zr - .03, TRIM, ("z+",))
    if lod == 0:
        for s, xe in ((-1, xl), (1, xr)):
            t = .5                                       # the strut meets the rafter half way up
            xs, zs = xe + (xm - xe) * t, zc + (zr - zc) * t - .05
            q = [(xm + s * .07, y - E, zc + .12), (xm + s * .07, y - E, zc + .32), (xs, y - E, zs), (xs + s * .16, y - E, zs - .12)]
            m.facing(q, (0, -1, 0), TRIM)


def lancet(m, w, u0, u1, zb, zt, lod):
    """Turn a cut window into a lancet: two white spandrels fill the corners of its head, leaving a pointed arch."""
    if lod == 2:
        return
    um, hw = (u0 + u1) / 2, (u1 - u0) / 2
    zs = zt - 1.3 * hw                               # the springing line
    for s in (-1, 1):
        ue = um + s * hw
        A, B, C, D = (ue, zs), (ue, zt), (um, zt), (um + s * hw * .45, zs + 1.3 * hw * .72)
        for tri in ((A, B, D), (B, C, D)):
            m.facing([w.P(u, z, -.03) for u, z in tri], w.n, TRIM)


def frieze(m, x0, x1, yf, zt, posts, lod):
    """A spindle frieze under the porch beam between the posts (Queen Anne), with stepped sawn brackets."""
    if lod == 2:
        return
    zb = zt - .2                                     # underside of the porch beam
    ps = sorted(posts)
    for a, b in zip(ps, ps[1:]):
        a, b = a + .09 + E, b - .09 - E
        if b - a < .4:
            continue
        wbox(m, a, b, yf + .12, yf + .18, zb - .42, zb - .36, TRIM)
        if lod == 0:
            k = int((b - a) / .15)
            for i in range(1, k):
                c = a + (b - a) * i / k
                wbox(m, c - .02, c + .02, yf + .135, yf + .165, zb - .36 + E, zb - E, TRIM, ("z-", "z+"))
    if lod == 0:
        for px in ps:
            for s in (-1, 1):
                if not (x0 + .3 < px + s * .4 < x1 - .3):
                    continue
                xa, xb = sorted((px + s * (.09 + E), px + s * .38))
                wbox(m, xa, xb, yf + .12, yf + .18, zb - .1, zb - E, TRIM)
                xa, xb = sorted((px + s * (.09 + E), px + s * .2))
                wbox(m, xa, xb, yf + .12, yf + .18, zb - .3, zb - .1 - E, TRIM)


def veranda(m, x0, x1, yw, depth, lod, spindles=False, **kw):
    """A front porch (lt_kit.porch), with a spindle frieze for the Queen Anne houses."""
    porch(m, x0, x1, yw, depth, lod, **kw)
    if spindles:
        frieze(m, x0, x1, yw - depth, kw.get("zt", 3.35), kw.get("posts") or [x0 + .15, x1 - .15], lod)


def stickwork(m, w, us, zones, rails, cuts, lod):
    """Stick style: flat boards over the clapboard - an upright between every two window columns in each zone
    between the trim belts, and a rail under each row of sills, broken round openings (cuts: u ranges)."""
    if lod == 2:
        return
    us = sorted(us)
    for u in [(a + b) / 2 for a, b in zip(us, us[1:])]:
        if any(c0 < u < c1 for c0, c1, _, _ in cuts):
            continue
        for za, zb in zones:
            lbox(m, w, u - .06, u + .06, za + E, zb - E, E, .04, TRIM, ("in", "top", "bot"))
    for z in rails:
        segs = [(.3, w.L - .3)]
        for c0, c1, z0, z1 in cuts:
            if not (z0 - .05 < z < z1 + .05):
                continue
            nxt = []
            for a, b in segs:
                if c1 <= a or c0 >= b:
                    nxt.append((a, b))
                    continue
                if c0 > a:
                    nxt.append((a, c0))
                if c1 < b:
                    nxt.append((c1, b))
            segs = nxt
        for a, b in segs:
            if b - a > .3:
                lbox(m, w, a, b, z - .04, z + .04, E, .045, TRIM)


def octagon_soffit(m, cx, yw, a, z):
    """The underside of a corbelled turret: its half octagon in front of the wall."""
    s = 2 * a * math.tan(math.pi / 8)
    pts = [(cx - a, yw), (cx - a, yw - s / 2), (cx - s / 2, yw - a), (cx + s / 2, yw - a), (cx + a, yw - s / 2), (cx + a, yw)]
    m.facing([(x, y, z) for x, y in pts], (0, 0, -1), TRIM)
    for k, (p, q) in enumerate(zip(pts, pts[1:])):        # a shallow corbel under each face
        m.facing([(p[0], p[1], z), (q[0], q[1], z), ((q[0] + cx) / 2, (q[1] + yw) / 2, z - .45),
                  ((p[0] + cx) / 2, (p[1] + yw) / 2, z - .45)], ((p[0] + q[0]) / 2 - cx, (p[1] + q[1]) / 2 - yw, -1), TRIM)


def square_tower(m, g, cx, yw, a, z0, z1, rise, lod, mat, rows, top_rows, trim, roof, belts=()):
    """A square wooden tower centred on the street wall at yw (half of it in front, half in the house), 2a wide, walls
    from z0 to z1, a steep pyramid cap with a finial (pavilion_roof). rows: (sill, head) of the front windows; top_rows:
    the storey above the main eave, windowed on all four sides (the room under the cap)."""
    trim = dict(dict(so=.16, key=False), **(trim or {}))
    yf, yb = yw - a, yw + a
    corners = [(cx - a, yb), (cx - a, yf), (cx + a, yf), (cx + a, yb)]
    faces = list(zip(corners, corners[1:] + corners[:1]))      # left, front, right, back
    for i, (A, B) in enumerate(faces):
        w = Wall(A, B)
        H = []
        ww = .62
        if i == 1:
            H = [(w.L / 2 - .4, w.L / 2 + .4, zb, zt, "win") for zb, zt in rows if zb > z0 + .3]
        H += [(w.L / 2 - ww / 2, w.L / 2 + ww / 2, zb, zt, "win") for zb, zt in top_rows]
        lo = z0
        surface(m, g, w, lo, z1, [(lo, z1, mat)], H, lod, trim)
        if lod < 2:
            dz = -.008 * (1 + i % 2)
            band(m, w, z1 - .30 + dz, z1 + dz, .07, TRIM, "-", "-")
            for z in belts:
                if lo + .2 < z < z1 - .3:
                    band(m, w, z - .06 + dz, z + .10 + dz, .05, TRIM, "-", "-")
            if lo < .8:
                band(m, w, 0.0, .75 + dz, .05, "StoneBase", "-", "-", skip=("in", "bot"))
    if z0 > .1:                                              # corbelled out over the porch: its floor
        m.facing([(cx - a, yf, z0), (cx + a, yf, z0), (cx + a, yb, z0), (cx - a, yb, z0)], (0, 0, -1), TRIM)
    o = .3
    pavilion_roof(m, cx - a - o, cx + a + o, yf - o, yb + o, z1 + .02, rise, lod, roof)


# ---------------------------------------------------------------- the plan

def plan(D, depth, rear):
    """Main front, main rear and the rear pieces [(spec, ya, yb)] for a lot D cells deep. Pieces are taken in order
    while their minimum lengths fit, grown towards their preferred lengths, and the slack goes to the 'grow' pieces
    (or the last), so the lot is built out to .6 m from its rear line. A short lot runs the main house on."""
    y0 = -4.0 * D
    yF = y0 + SET
    yR = yF + depth
    end = 4.0 * D - .6
    room = end - yR
    specs = [dict(PIECE, **p) for p in rear]
    take, need = [], 0.0
    for p in specs:
        if p["k"] == "carriage" and take and take[-1]["k"] == "carriage":
            continue
        if need + p["min"] <= room + 1e-6:
            take.append(p)
            need += p["min"]
    while take and take[-1]["k"] != "carriage" and any(p["k"] == "carriage" for p in take):
        take.pop()                                         # a carriage house is always the last piece
    if not take or room < 2.5:
        return yF, end, []
    L = [p["min"] for p in take]
    left = room - sum(L)
    for i, p in enumerate(take):
        add = max(0.0, min(left, p["L"] - p["min"]))
        L[i] += add
        left -= add
    grow = [i for i, p in enumerate(take) if p["grow"]] or [len(take) - 1]
    for i in grow:
        L[i] += left / len(grow)
    out, y = [], yR
    for p, l in zip(take, L):
        out.append((p, y, y + l))
        y += l
    return yF, yR, out


def pstyle(h, mat):
    win = WIN1 if h < 4.5 else WIN2
    return style(h, [(0.0, h, mat)], win, belts=() if h < 4.5 else (3.75,))


def top_of(p, ya, yb, x0):
    """The highest point of a narrow piece's roof, its pitch along y (for a roof dying into it) and its kind."""
    h = p["h"]
    if p["roof"] == "cross":
        k = .9
        return h + (yb - ya) / 2 * k, k
    if p["roof"] == "shed":
        return h + (p["rise"] or 1.5), None
    if p["k"] == "carriage":
        k = .9 if p["roof"] != "hip" else 1.0
        return h + (yb - ya) / 2 * k, k
    return h + (p["rise"] or (2.6 if h < 4.5 else 2.4)), None


# ---------------------------------------------------------------- the building

def build(lod, D=3, **variant):
    if variant.get("wide_corner"):
        from lt_designs.wide_corners import build_corner
        return build_corner(lod, D, variant)
    v = dict(DEFAULT, **variant)
    n = v["storeys"]
    kind = v["roof"]
    gam, flat, side = kind == "gambrel", kind == "flat", kind == "side"
    if gam:
        n = 2
    top = TOPS[n]
    win, belts = WINS[n], BELTS[n]
    corner = v["corner"]
    XL = -X + v["ci"] if corner else -X
    xm = (XL + X) / 2
    trim = dict(door=v["door"], shutters=v["shutters"], lites=v["lites"])
    gtrim = dict(trim, shutters=None)
    gmat = v["gable_mat"]
    rmat = v["roof_mat"]
    m, g = Mesh(), Mesh()
    yF, yR, pieces = plan(D, v["depth"], v["rear"])
    spans = [(0.0, top, v["wall"])]
    if v["upper"]:
        spans.append((v["upper"][0], top, v["upper"][1]))
    if v["band"]:
        spans.append((BAND[0], BAND[1], "DiamondBand"))
    mats = layers(top, *spans)
    main = style(top, mats, win, belts=belts)
    sx = "x" if corner else "-"
    lside = "e" if corner else "p"

    # ---- the street front: bays, door, towers, bays and porches
    front_bays = v["bays"] or ([-2.1, xm, 2.5] if corner and v["ci"] < 1 else [-2.5, 0.0, 2.5])
    dx = v["door_x"]
    stair = (dx - .6, dx + .6)
    omit, waive = [], dict(SIDE_HALL)
    tw = v["tower"]
    tcut = []                                              # u ranges of the facade a tower or bay covers
    if tw:
        a = tw.get("a", 1.15)
        tx = tw["x"]
        tcut.append((tx - a - .3 - XL, tx + a + .3 - XL, 0.0, 99.0))
        waive["glass"] = "the tower carries the glass of its bay"
        waive["rhythm"] = "two bays beside the tower, as on a Queen Anne row house"
    by = v["bay"]
    if by:
        bxx, bz1 = by["x"], by.get("z1", 6.75)
        omit += [(bxx, f) for f, (_, zb, _) in enumerate(win) if zb < bz1]
        tcut.append((bxx - 1.4 - XL, bxx + 1.4 - XL, 0.0, bz1))
        waive["glass"] = "the canted bay carries the glass of its column"
        waive["rhythm"] = "door and windows beside a canted bay, as on a bay-and-gable house"
    if v["oriel"]:
        omit += [(xm, 1), (xm, 2)]
        waive["glass"] = "the oriel carries the glass of the middle bay on the second and third floors"
    fw_ = wall(m, g, main, (XL, yF), (X, yF), sx, "-", front_bays, lod, door=(dx, 1.0, 2.95), trim=trim, waive=waive,
               omit=omit, plinth_cuts=[stair])
    if v["stick"]:
        zs = [(.75, belts[0] - .06)] + [(a_ + .10, b_ - .06) for a_, b_ in zip(belts, belts[1:])] + [(belts[-1] + .10, top - .30)]
        rails = [zb - .36 for _, zb, _ in win]
        H = holes_for(fw_, front_bays, win, (dx, 1.0, 2.95))
        cuts = [(h[0] - .3, h[1] + .3, h[2], h[3]) for h in H if h[4] == "door"] + tcut
        stickwork(m, fw_, [fw_.u_of(c) for c in front_bays], zs, rails, cuts, lod)

    pk = v["porch"]
    po = ("l",) if corner else ()
    sp = v["spindles"] and lod < 2
    street_entry = corner and v["hand"] == "R"
    def front_porch(*args, **kw):
        if street_entry and kw.get("stair") and kw.get("zf", .79) < 1:
            kw["zf"] = .14
        veranda(*args, **kw)
    if pk == "full":
        front_porch(m, XL + E, X - E, yF, 2.3, lod, spindles=sp, stair=stair, mat=rmat, open_sides=po)
    elif pk == "half":
        x0, x1 = v["porch_x"]
        front_porch(m, x0, x1, yF, 2.1, lod, spindles=sp, stair=stair, mat=rmat,
                open_sides=tuple(s for s, xx in (("l", x0), ("r", x1)) if abs(abs(xx) - X) > .1 or (s == "l" and corner)),
                posts=[x0 + .2, x1 - .15] if x0 < -3 else [x0 + .15, x1 - .2])
    elif pk == "double":                               # a two-storey porch, the upper one under the shed roof
        front_porch(m, XL + E, X - E, yF, 2.3, lod, spindles=False, zt=3.7, stair=stair, roof=False, open_sides=po)
        front_porch(m, XL + E, X - E, yF, 2.3, lod, spindles=sp, zf=3.88, zt=MID + .02, mat=rmat, open_sides=po)
    elif pk == "wrap":                                 # a corner: round the front and down the side street
        d = 1.7
        x0 = XL - d
        front_porch(m, x0 + E, X - E, yF, 2.3, lod, spindles=sp, stair=stair, mat=rmat, open_sides=(),
                posts=[x0 + .2, XL - .1, X - .15])
        t = Mesh()
        ya, yb = yF + E, yF + v["wrap_len"]
        veranda(t, -yb, -ya, 0.0, d, lod, spindles=sp, mat=rmat, zf=.14 if street_entry else .79,
                open_sides=("l",))
        turn(m, t, lambda a, b, z: (XL + b, -a, z))
    elif pk in ("stack", "stack4"):                    # stacked porches; a flat roof gets a gabled porch tower
        x0, x1 = v["porch_x"] or (XL + E, X - E)
        if pk == "stack4":
            decks = [(.79, 3.7), (3.88, 6.7), (6.88, 9.7), (9.88, top - .01 if flat else top - .7)]
        else:
            decks = [(.79, 3.7), (3.88, 6.95), (7.13, top - .01 if flat else 9.2)]
        opn = tuple(s for s, xx in (("l", x0), ("r", x1)) if abs(abs(xx) - X) > .1)
        for i_, (zf, zt) in enumerate(decks):
            last = i_ == len(decks) - 1
            front_porch(m, x0, x1, yF, 2.3, lod, spindles=sp and (last or i_ == 0), zf=zf, zt=zt,
                    stair=stair if i_ == 0 else None, roof=(not flat) and last, mat=rmat, open_sides=opn)
        if flat:                                       # the gable over the porch stack, running back into the roof
            prise = v.get("prise", 2.4)
            ya, yb = yF - 2.3 - .3, yF + .6
            gable_roof(m, x0, x1, ya + .3, yb, top, top + prise, lod, rmat, over=(.3, 0.0))
            gw = gable_wall(m, g, (x0, yF - 2.3 + .02), (x1, yF - 2.3 + .02), top, top + prise, lod, gmat, trim=gtrim)
            hw = (x1 - x0) / 2 * (top + prise - (top + .5)) / prise          # the back of it, above the cornice
            xc = (x0 + x1) / 2
            gable_wall(m, g, (xc + hw, yb - .02), (xc - hw, yb - .02), top + .5, top + prise, lod, gmat, trim=gtrim)
            prof = rake_pts(x0, x1, top, top + prise)
            if v["barge"]:
                bargeboard(m, prof, lambda a_, z: (a_, ya - .015, z), (0, -1, 0), lod)
            if v["finial"]:
                finial(m, xc, ya + .15, ya - .07, top + prise, lod)
            v["_porch_gable"] = (x0, x1, yb)
    elif pk == "stoop":
        front_porch(m, dx - .75, dx + .75, yF, .9, lod, stair=stair, mat=rmat, open_sides=(), posts=[dx - .6, dx + .6])
    if street_entry:
        # A paneled storm lobby brings the actual front door to the sidewalk under the porch.
        yy = -4*D + .87
        left, right = dx - 1.13, dx + 1.13
        height = 3.19
        lobby = style(height, [(0,height,v["wall"])], [(.73,1.06,2.33)],
                      corners=False, plinth=None, frieze=None)
        wall(m,g,lobby,(left,yy),(right,yy),"x","x",[dx],lod,door=(dx,1.0,2.36),trim=trim)
        for A,B in (((right,yy),(right,yF-.012)),((left,yF-.012),(left,yy))):
            wall(m,g,lobby,A,B,"c","c",[(yy+yF)/2],lod,trim=trim)
        slab(m,[(yy-.12,height),(yF-.012,height+.20)],left-.09,right+.09,
             lambda a,q,z:(a,q,z),lod,rmat,what="storm lobby roof")
    if by:                                             # a canted bay
        bwin = [(a_, b_) for _, a_, b_ in win if b_ < by.get("z1", 6.75)]
        bay(m, g, by["x"], yF, by.get("w", 1.5), by.get("proj", .75), 0.0, by.get("z1", 6.75), lod, by.get("mat", v["wall"]),
            bwin, trim, rmat, v["lites"])
    if v["oriel"]:                                     # a two-storey oriel over the porch roof
        z0, z1, wd, pj = 4.0, 9.4, 2.2, .6
        bay(m, g, xm, yF, wd, pj, z0, z1, lod, gmat, [(4.55, 6.25), (7.5, 8.95)], trim, rmat, v["lites"])
        a_ = wd / 2 + pj
        m.facing([(xm - a_, yF, z0), (xm - wd / 2, yF - pj, z0), (xm + wd / 2, yF - pj, z0), (xm + a_, yF, z0)],
                 (0, 0, -1), TRIM)
    if tw:                                             # the small wooden tower
        a = tw.get("a", 1.15)
        z0 = tw.get("z0", 0.0)
        z1 = top + tw.get("above", 0.0)
        rows = [(a_, b_) for _, a_, b_ in win]
        extra = [(top + .65, top + 1.75)] if tw.get("above", 0) > 2.0 else []
        tmat = tw.get("mat", gmat)
        if tw["kind"] == "oct":
            turret(m, g, tw["x"], yF, a, z0, z1, tw.get("rise", 3.6), lod, tmat, [r for r in rows + extra if r[0] > z0 + .3],
                   gtrim, tw.get("roof", rmat), belts=[z for z in belts + ((top,) if extra else ()) if z > z0 + .3],
                   lites=v["lites"])
            if z0 > .1:
                octagon_soffit(m, tw["x"], yF, a, z0)
        else:
            square_tower(m, g, tw["x"], yF, a, z0, z1, tw.get("rise", 3.4), lod, tmat, rows, extra, gtrim,
                         tw.get("roof", rmat), belts=belts + ((top,) if extra else ()))

    # ---- the main roof, the side walls
    th = .16
    rtop = top                                         # the main rear wall's height
    main_across, main_k = False, None
    if corner:                                         # the side street: windows down the house
        cb = [yF + 1.6, yF + 4.2, yF + 6.8, yF + 9.4] if v["depth"] > 10 else [yF + 1.6, yF + 4.2, yF + 6.8]
        if kind == "side":
            cb = [yF + 1.8, yF + 4.25, yF + 6.7]
        cb = v["side_bays"] and [yF + c for c in v["side_bays"]] or cb
        wall(m, g, main, (XL, yR), (XL, yF), "-" if pieces else "x", "x", cb, lod, trim=trim,
             waive={"rhythm": "windows down the side street, the rooms in a row"})
    if side:                                           # a side-gabled cottage: eaves front and back, gables on the lines
        dep = yR - yF
        p = v["pitch"]
        ym = (yF + yR) / 2
        zr = top + dep / 2 * p
        main_across, main_k = True, p
        for xx, d_ in ((X, 1),) + (() if corner else ((-X, -1),)):
            m.facing([(xx, yF, 0.0), (xx, yR, 0.0), (xx, yR, top - .03), (xx, ym, zr - .03), (xx, yF, top - .03)],
                     (d_, 0, 0), v["wall"])
        if corner:
            gable_wall(m, g, (XL, yR), (XL, yF), top, zr, lod, gmat, wins=[(ym, .7, top + .9, top + 2.3)], trim=gtrim)
        o = .35
        a0 = XL - .3 if corner else -X + E
        slab(m, [(yF - o, top - o * p), (ym, zr), (yR + o, top - o * p)], a0, X - E, lambda a_, q, z: (a_, q, z), lod,
             rmat, end=rmat if not corner else TRIM, what="side-gabled roof")
        if lod == 0:
            wbox(m, a0 + 3 * E, X - 3 * E, ym - .09, ym + .09, zr + th - .02, zr + th + .07, rmat, ("z-",))
        if corner and v["barge"]:
            bargeboard(m, [(yF - o, top - o * p), (ym, zr), (yR + o, top - o * p)], lambda a_, z: (a0 - .015, a_, z),
                       (-1, 0, 0), lod)
        for cx_, cw in v["xgables"]:                   # steep cross gables on the front slope, walls flush with the front
            pc = v["xpitch"]
            hr = cw / 2 * pc
            zc = top + hr
            yE = yF + hr / p + .5
            gwin = [(cx_, .62, top + .55, top + 1.95)] if cw > 2.8 else [(cx_, .55, top + .45, top + 1.6)]
            gw = gable_wall(m, g, (cx_ - cw / 2, yF), (cx_ + cw / 2, yF), top, zc, lod, gmat, wins=gwin, trim=gtrim)
            for wx, ww_, zb_, zt_ in gwin:
                u = gw.u_of(wx)
                lancet(m, gw, u - ww_ / 2, u + ww_ / 2, zb_, zt_, lod)
            gable_roof(m, cx_ - cw / 2, cx_ + cw / 2, yF, yE, top, zc, lod, rmat, over=(.4, 0.0), sides=("e", "e"))
            prof = rake_pts(cx_ - cw / 2, cx_ + cw / 2, top, zc, ("e", "e"))
            if v["barge"]:
                bargeboard(m, prof, lambda a_, z: (a_, yF - .4 - .015, z), (0, -1, 0), lod, deep=.3)
            if v["finial"]:
                finial(m, cx_, yF - .4 + .12, yF - .4 - .08, zc, lod)
    else:
        party(m, (X, yF), (X, yR), 0.0, top, v["wall"])
        if not corner:
            party(m, (-X, yR), (-X, yF), 0.0, top, v["wall"])
    first = pieces[0] if pieces else None
    covered = first is not None and first[0]["h"] > top - .1           # a wing as tall as the house behind it
    if gam:
        zk, ridge, knee = top + 3.3, top + 5.3, (top + 3.3, 1.0)
        gable_wall(m, g, (XL, yF), (X, yF), top, ridge, lod, gmat,
                   wins=[(-1.3, .8, top + .8, top + 2.15), (1.3, .8, top + .8, top + 2.15), (0.0, .7, top + 3.6, top + 4.5)],
                   trim=gtrim, shape=(zk, 1.0))
        gable_wall(m, g, (X, yR), (XL, yR), top, ridge, lod, gmat,
                   wins=[] if covered else [(1.3, .8, top + .8, top + 2.15), (0.0, .7, top + 3.6, top + 4.5)],
                   trim=gtrim, shape=(zk, 1.0))
        gable_roof(m, XL, X, yF, yR, top, ridge, lod, rmat, over=(.45, 0.0 if covered else .3), knee=knee,
                   sides=(lside, "p"))
        prof = rake_pts(XL, X, top, ridge, (lside, "p"), knee)
        if v["barge"]:
            bargeboard(m, prof, lambda a_, z: (a_, yF - .45 - .015, z), (0, -1, 0), lod, deep=.28)
        if v["finial"]:
            finial(m, xm, yF - .45 + .12, yF - .45 - .08, ridge, lod)
    elif flat:
        pg = v.get("_porch_gable")
        stacked = pk in ("stack", "stack4")
        if pg and pg[1] < X - .5:                      # the cornice beside the porch tower, then behind it
            cornice_roof(m, pg[1] + .012, X, yF - .6, yR + .3, top, lod, deep=.5, ends=v["wall"],
                         brackets=tuple(b_ for b_ in (pg[1] + .5, X - .4) if not (by and by.get("z1", 6.75) > top - 1.2
                                        and abs(b_ - by["x"]) < by.get("w", 1.5) / 2 + by.get("proj", .75) + .2)))
            cornice_roof(m, XL, pg[1], pg[2] + .012, yR + .3, top, lod, deep=.5, ends=v["wall"], front=False)
        elif pg:
            cornice_roof(m, XL, X, pg[2] + .012, yR + .3, top, lod, deep=.5, ends=None if corner else v["wall"], front=False)
        else:
            y0c = yF - 2.55 if stacked else yF - .6
            cornice_roof(m, XL, X, y0c, yR + .3, top, lod, deep=.5, ends=None if corner else v["wall"],
                         brackets=() if stacked else (-3.4, -1.15, 1.15, 3.4))
    elif not side:
        ridge = top + v["rise"]
        gw_ = v["gwin"]
        if tw and tw.get("above", 0) > 2.0:            # a tall tower takes one side: one window off-centre
            fw = [(xm - .9 * (1 if tw["x"] > 0 else -1), .7, top + .9, top + 2.15)]
        elif gw_ == "lancet":
            fw = [(xm - .7, .6, top + .9, top + 2.5), (xm + .7, .6, top + .9, top + 2.5)]
        elif gw_ == "single":
            fw = [(xm, .75, top + .9, top + 2.3)]
        elif gw_ == "triple":
            fw = [(xm - 1.15, .6, top + .8, top + 1.9), (xm, .75, top + .8, top + 2.3), (xm + 1.15, .6, top + .8, top + 1.9)]
        else:
            fw = [(xm - .7, .7, top + .9, top + 2.15), (xm + .7, .7, top + .9, top + 2.15)]
        gw = gable_wall(m, g, (XL, yF), (X, yF), top, ridge, lod, gmat, wins=fw, trim=gtrim)
        if gw_ == "lancet":
            for wx, ww_, zb_, zt_ in fw:
                u = gw.u_of(wx)
                lancet(m, gw, u - ww_ / 2, u + ww_ / 2, zb_, zt_, lod)
        bw = [] if covered else [(xm, .75, top + .9, top + 2.2)]
        gable_wall(m, g, (X, yR), (XL, yR), top, ridge, lod, gmat, wins=bw, trim=gtrim)
        rear_over = 0.0 if covered else .3
        gable_roof(m, XL, X, yF, yR, top, ridge, lod, rmat, over=(.45, rear_over), sides=(lside, "p"))
        prof = rake_pts(XL, X, top, ridge, (lside, "p"))
        if v["barge"]:
            bargeboard(m, prof, lambda a_, z: (a_, yF - .45 - .015, z), (0, -1, 0), lod)
            if rear_over > 0:
                bargeboard(m, prof, lambda a_, z: (a_, yR + rear_over + .015, z), (0, 1, 0), lod)
        if v["truss"]:
            truss(m, prof, yF - .45 + .12, lod)
        if v["finial"]:
            finial(m, xm, yF - .45 + .12, yF - .45 - .08, ridge, lod)
        if v["dormers"] or corner:                     # gabled dormers: cross gables on the slopes
            side_dormers(m, g, (X - XL) / 2, top, ridge, th, [yF + 3.0, yF + 7.6], lod, gmat, rmat, gtrim,
                         sides=(1, -1) if v["dormers"] else (-1,), xc=xm)

    # ---- the rear of the main house
    ydx = (BX + X) / 2
    rear_st = main
    if pieces:
        p0, ya0, yb0 = first
        full0 = p0["k"] == "carriage"
        h0 = p0["h"]
        if not full0:
            wall(m, g, rear_st, (X, yR), (BX, yR), "-", "c", [ydx], lod, door=(ydx, 1.0, 2.95), trim=trim,
                 waive={"balance": "the back door opens onto the yard"})
        if h0 < rtop - .1:                             # the house wall above the first piece, windows clear of its roof
            pt_, _ = top_of(p0, ya0, yb0, XL)
            x1s = X if full0 else BX
            cb = (XL + x1s) / 2
            om = [(cb, f) for f, (_, zb_, _) in enumerate(rear_st["win"]) if zb_ < pt_ + .25 or zb_ < h0]
            bays_ = [cb] if len(om) < len(rear_st["win"]) else []
            wall(m, g, rear_st, (x1s, yR), (XL, yR), "c" if not full0 else "-", sx, bays_, lod, z0=h0, trim=trim,
                 omit=om if bays_ else (),
                 waive={"rhythm": "one column of windows above the wing", "glass": "the wing covers the lower floors",
                        "shape": "the wing covers the lower floors"})
        bp = v["backporch"]
        if bp and not full0:                           # a one- or two-storey back porch over the yard
            t = Mesh()
            lv = [(.79, 3.7 if bp == 2 else 3.35)] + ([(3.88, MID + .02)] if bp == 2 else [])
            for i_, (zf, zt) in enumerate(lv):
                last = i_ == len(lv) - 1
                porch(t, BX + .02, X - E, -yR, 2.0, lod, zf=zf, zt=zt, roof=last, mat=v.get("bp_mat", rmat),
                      stair=(X - 1.1, X - .35) if i_ == 0 else None, open_sides=("l",) if False else (),
                      posts=[BX + .2, X - .2])
                if last and v["spindles"]:
                    frieze(t, BX + .02, X - E, -yR - 2.0, zt, [BX + .2, X - .2], lod)
            turn(m, t, (lambda x, y, z: (x, -y, z), True))
    else:
        wall(m, g, rear_st, (X, yR), (XL, yR), "-", sx, [2.5, -.5], lod, door=(-.5, 1.0, 2.95), trim=trim,
             waive={"rhythm": "kitchen door and one window on the back wall"})
        wbox(m, -1.1, .1, yR + E, yR + .55, 0, .3, "StoneBase", ("z-", "y-"))

    # ---- the rear pieces
    prev = dict(k="main", x1=X, h=rtop, top=rtop + 99, across=main_across, kk=main_k)
    for i, (p, ya, yb) in enumerate(pieces):
        nxt = pieces[i + 1] if i + 1 < len(pieces) else None
        if p["k"] == "carriage":
            carriage(m, g, p, ya, yb, prev, lod, XL, corner, sx, gtrim)
            prev = dict(k="carriage", x1=X, h=p["h"])
            continue
        if i == 0 and v["backporch"]:
            p = dict(p, _clear=yR + 2.0 + 3 * E)      # the piazza runs on from the back porch
        prev = ell(m, g, p, ya, yb, prev, nxt, lod, XL, corner, sx, lside, gtrim)

    # ---- the yard walk: back door -> along the wing -> the carriage house
    if pieces and first[0]["k"] != "carriage":
        carr = next((q for q in pieces if q[0]["k"] == "carriage"), None)
        yend = carr[1] - .06 if carr else 4.0 * D - .3
        piaz = any(q[0]["piazza"] for q in pieces)
        xa, xb = (BX + 2.05, BX + 2.85) if piaz else (BX + .25, BX + 1.35)
        ys = yR + (2.0 + 1.2 if v["backporch"] else .06)
        z = .05
        if not v["backporch"]:
            wbox(m, BX + .25, min(X - .3, ydx + .7), yR + .06, yR + 1.2, 0.0, z, "Paving", ("z-",))
            ys = yR + 1.2 + E
        if yend - 1.2 - E > ys + .5:
            wbox(m, xa, xb, ys, (yend - 1.2 - E) if carr else yend, 0.0, z, "Paving", ("z-",))
        if carr:
            wbox(m, BX + .25, min(X - .3, ydx + .7), yend - 1.2, yend, 0.0, z, "Paving", ("z-",))

    # ---- chimneys
    if v["chimney"]:
        if side:
            chimney(m, X - .55, (yF + yR) / 2 + .6, .35, .4, top + 1.0, (top + (yR - yF) / 2 * v["pitch"]) + 1.0, lod)
        elif flat:
            chimney(m, X - .5, yF + v["depth"] * .6, .35, .45, top + .3, top + 1.6, lod)
        else:
            zr_ = top + (5.3 if gam else v["rise"])
            yc = yF + v["depth"] * (.62 if v["chimney"] == 1 else .35)
            chimney(m, X - .5, yc, .35, .45, top - .1, top + (2.6 if gam else min(v["rise"] * .55, 3.0)), lod)

    if v["hand"] == "R":             # mirrored: the wing and yard swap sides
        for mm in (m, g):
            mm.v = [(-x, y, zz) for x, y, zz in mm.v]
            mm.f = [f[::-1] for f in mm.f]
    finish(m, g)


# ---------------------------------------------------------------- rear pieces

def ell(m, g, p, ya, yb, prev, nxt, lod, XL, corner, sx, lside, gtrim):
    """A narrow rear piece (XL..BX) with its yard wall, party (or street) wall, the ends it owns and its roof.
    Returns what the next piece needs to know about it."""
    h, mat, rm, roof = p["h"], p["mat"], p["rmat"], p["roof"]
    st = pstyle(h, mat)
    span = yb - ya
    k_ = max(1, round(span / 2.6))
    ys = [ya + span * (j + .5) / k_ for j in range(k_)]
    if span / k_ - .9 > 2.25:
        k_ = math.ceil((span - 2.2) / 3.15) + 1
        ys = [ya + 1.1 + (span - 2.2) * j / (k_ - 1) for j in range(k_)]
    if span < 4.6:                                            # a short wing: one bay
        ys = [(ya + yb) / 2]
    nk = nxt[0]["k"] if nxt else None
    nh = nxt[0]["h"] if nxt else None
    full_next = nk == "carriage"
    top_, kk = top_of(p, ya, yb, XL)
    if roof == "shed":
        p = dict(p, rise=p["rise"] or 1.5)
        top_ = h + p["rise"]
    # who owns the ends: the taller piece draws the wall above the lower one
    own_front = prev["k"] != "main" and prev["h"] < h - .1
    own_rear = nxt is None or (nh < h - .1)
    # roofs that rise above a neighbour's eave die into its slope when it is roofed across the lot
    fwd = .25 if own_front else -2 * E
    if not own_front and prev.get("across") and top_ > prev["h"] and prev.get("kk"):
        fwd = (top_ - prev["h"]) / prev["kk"] + .3
    aft = .25 if own_rear else -2 * E
    if nxt and not own_rear and top_ > nh and (full_next or nxt[0]["roof"] == "cross"):
        kn = .9 if (full_next and nxt[0]["roof"] != "hip") or nxt[0]["roof"] == "cross" else 1.0
        aft = (top_ - nh) / kn + .3
    if nxt and not own_rear and abs(nh - h) <= .1 and not full_next and nxt[0]["roof"] != "cross" and roof != "cross":
        same = roof == nxt[0]["roof"] == "gable" and (p["rise"] or 0) == (nxt[0]["rise"] or 0)
        if not same:                                          # nothing would close the step between the two roofs
            raise ValueError(f"rear pieces {roof} then {nxt[0]['roof']} at the same eave: give them one roof "
                             "profile, or step one down, or put a cross-gabled wing or the carriage house between")
    e_end = "x" if nxt is None else "c" if full_next else "-"
    door = (ys[0], 1.0, 2.95) if p.get("door", "front") == "front" else (ys[-1], 1.0, 2.95)
    s_ = "c" if prev["k"] == "main" else "-"
    wall(m, g, st, (BX, ya), (BX, yb), s_, e_end, ys, lod, door=door, trim=gtrim,
         waive={"balance": "the wing's door opens onto the yard walk", "rhythm": "the wing's windows follow its rooms"})
    hp = h + (p["rise"] if roof == "shed" else 0.0)          # height on the party line
    if corner:
        wall(m, g, st, (XL, yb), (XL, ya), "x" if nxt is None else "-", "-", ys, lod, trim=gtrim,
             waive={"rhythm": "the wing's windows follow its rooms"})
        if roof == "shed":
            m.facing([(XL, ya, h), (XL, yb, h), (XL, yb, hp - .03), (XL, ya, hp - .03)], (-1, 0, 0), mat)
    else:
        party(m, (XL, yb), (XL, ya), 0.0, hp - (.03 if roof == "shed" else 0.0), mat)
    pw = prev["h"]
    if own_front:                                             # the end wall above the lower piece in front
        wall(m, g, st, (XL, ya), (BX, ya), sx, "x", [], lod, z0=pw, trim=gtrim)
    if own_rear:
        z0r = nh if nxt else 0.0
        bays_ = [] if nxt else ([(XL + BX) / 2 + 1.0, (XL + BX) / 2 - 1.0] if BX - XL > 4.2 else [(XL + BX) / 2])
        wall(m, g, st, (BX, yb), (XL, yb), "x", sx, bays_, lod, z0=z0r, trim=gtrim,
             waive={"rhythm": "the wing's end windows", "balance": "a back wall"})
    x0r = XL + 3 * E if (fwd > 1 or aft > 1) and not corner else XL
    if p["piazza"] and h > 4.5:                               # a porch along the yard wall (two storeys: a deck on top)
        t = Mesh()
        lv = [(.79, 3.35)] if p["piazza"] == 1 else [(.79, 3.7), (3.88, 3.88 + 1.1)]
        a0 = max(ya + .02, p.get("_clear", -99))              # tight to the house (or its back porch) and to
        a1 = yb - .02 if yb - ya - 9.0 < 2.2 else ya + 9.0    # the next piece: no slit of yard between them
        if a1 - a0 > 2.5:
            for i_, (zf, zt) in enumerate(lv):
                porch(t, a0, a1, 0.0, 1.8, lod, zf=zf, zt=zt, roof=(p["piazza"] == 1), mat=rm, open_sides=("l", "r"),
                      stair=(a1 - 1.3, a1 - .3) if i_ == 0 else None, posts=[a0 + .15, (a0 + a1) / 2, a1 - .15])
            turn(m, t, lambda a_, b_, z: (BX - b_, a_, z))
    ym = (ya + yb) / 2
    if roof == "gable":
        rise = p["rise"] or (2.6 if h < 4.5 else 2.4)
        gable_roof(m, x0r, BX, ya, yb, h, h + rise, lod, rm, over=(fwd, aft), sides=(lside, "e"))
        if own_front:
            gable_wall(m, g, (XL, ya), (BX, ya), h, h + rise, lod, mat, trim=gtrim)
        if own_rear:
            gw = [((XL + BX) / 2, .6, h + .5, h + 1.5)] if nxt is None else []
            gable_wall(m, g, (BX, yb), (XL, yb), h, h + rise, lod, mat, wins=gw, trim=gtrim)
            if p["barge"] and nxt is None:
                prof = rake_pts(x0r, BX, h, h + rise, (lside, "e"))
                bargeboard(m, prof, lambda a_, z: (a_, yb + aft + .015, z), (0, 1, 0), lod, deep=.28)
        if nxt is None and lod < 2 and h > 4.5:
            chimney(m, XL + 1.2, yb - 1.2, .3, .3, h + 1.0, h + rise + .9, lod)
        return dict(k="ell", x1=BX, h=h, across=False)
    if roof == "shed":
        rise = p["rise"]
        kx = rise / (BX - XL)
        prof = [(XL + 7 * E, h + rise), (BX + .3 - 3 * E, h - .3 * kx)]   # rims clear of the neighbours' roof ends
        slab(m, prof, ya - fwd, yb + aft, lambda a_, q, z: (q, a_, z),
             lod, rm, end=rm, what="lean-to roof")
        tri = lambda yy, d_: m.facing([(BX, yy, h), (XL, yy, h), (XL, yy, h + rise - .03)], (0, d_, 0), mat)
        if own_front:
            tri(ya, -1)
        if own_rear:
            tri(yb, 1)
        return dict(k="ell", x1=BX, h=h, across=False)
    # cross: the ridge across the lot, a gable to the yard (and the party line)
    k = .9
    rise = span / 2 * k
    front = (ya + 2 * E, h) if not own_front else (ya - .3, h - .3 * k)
    back = (yb + .3, h - .3 * k) if nxt is None else (yb - 2 * E, h)
    a0 = XL - (.3 if corner else 0.0) + (0 if corner else 5 * E)   # off the carriage roof's party end (XL + E)
    slab(m, [front, (ym, h + rise), back], a0, BX + .3, lambda a_, q, z: (a_, q, z), lod, rm, end=rm,
         what="cross-gabled wing roof")
    if lod == 0:
        wbox(m, a0 + 3 * E, BX + .3 - 3 * E, ym - .09, ym + .09, h + rise + .14, h + rise + .23, rm, ("z-",))
    gwin = [(ym, .7, h + .6, h + 1.8)] if rise > 2.2 else []
    gable_wall(m, g, (BX, ya), (BX, yb), h, h + rise, lod, mat, wins=gwin, trim=gtrim)
    if corner:
        gable_wall(m, g, (XL, yb), (XL, ya), h, h + rise, lod, mat, trim=gtrim)
    else:
        m.facing([(XL, ya, h), (XL, yb, h), (XL, ym, h + rise - .03)], (-1, 0, 0), mat)
    if p["barge"]:
        prof = [front, (ym, h + rise), back]
        bargeboard(m, prof, lambda a_, z: (BX + .3 + .015, a_, z), (1, 0, 0), lod, deep=.28)
    return dict(k="ell", x1=BX, h=h, across=True, kk=k)


def carriage(m, g, p, ya, yb, prev, lod, XL, corner, sx, gtrim):
    """A full-width carriage house across the back of the lot: a carriage door to the yard (and to the side street on
    a corner), doors and windows to the lane, roofed across the lot (gable or gambrel, gables on the party lines) or
    hipped, maybe with a louvred cupola."""
    h, mat, rm, roof = p["h"], p["mat"], p["rmat"], p["roof"]
    bst = style(h, [(0.0, h, mat)], [(.8, 1.6, 2.9)], belts=())
    xm = (XL + X) / 2
    after_main = prev["k"] == "main"
    narrow_before = not after_main
    pw = prev["h"]
    if narrow_before:                                       # the front: the yard part, and above the wing in front
        wall(m, g, bst, (BX, ya), (X, ya), "c", "-", [2.5], lod, door=(2.5, 1.9, 2.9), trim=gtrim,
             waive={"balance": "carriage door onto the yard", "corners": "the carriage door fills the yard bay"})
        if pw < h - .1:
            wall(m, g, bst, (XL, ya), (BX, ya), sx, "-", [], lod, z0=pw, trim=gtrim)
    sp_ = min(2.4, (X - XL - 2.1) / 2)
    wall(m, g, bst, (X, yb), (XL, yb), "-", sx, [xm - sp_, xm, xm + sp_], lod,
         door=(xm, 1.0, 2.6), trim=gtrim, waive={"balance": "the lane side"})
    if corner:
        L = yb - ya
        kq = max(2, round(L / 2.6))
        bys = [ya + L * (j + .5) / kq for j in range(kq)]
        wall(m, g, bst, (XL, yb), (XL, ya), "x", "-" if narrow_before else "x", bys, lod, door=(bys[min(1, kq - 1)], 2.2, 2.9),
             trim=gtrim, waive={"balance": "carriage door onto the side street", "rhythm": "the carriage bays",
                                "corners": "the carriage door takes the end bay of the side street wall"})
    ym = (ya + yb) / 2
    o = .35
    front_free = narrow_before and pw <= h + .1
    zr = h
    if roof in ("across", "gambrel"):
        k = .9
        if roof == "across":
            zr = h + (yb - ya) / 2 * k
            prof_u = [(ya - o, h - o * k) if front_free else (ya + 2 * E, h), (ym, zr), (yb + o, h - o * k)]
            ends = [(ya, h), (ym, zr), (yb, h)]
        else:
            run = (yb - ya) / 2
            ik, zk = min(1.4, run * .35), h + min(2.4, run * .55)
            zr = zk + (run - ik) * .45
            prof_u = [(ya - o, h - o * 1.6) if front_free else (ya + 2 * E, h), (ya + ik, zk), (ym, zr), (yb - ik, zk),
                      (yb + o, h - o * 1.6)]
            ends = [(ya, h), (ya + ik, zk), (ym, zr), (yb - ik, zk), (yb, h)]
        for xx, d_ in ((X, 1), (XL, -1)):
            if xx == XL and corner:
                continue
            m.facing([(xx, ya, 0.0), (xx, yb, 0.0)] + [(xx, q, z - .03) for q, z in ends[::-1]], (d_, 0, 0), mat)
        if corner:                                          # the gable to the side street
            w_ = Wall((XL, yb), (XL, ya))
            up = [(yb - q, z) for q, z in ends[::-1]][:len(ends) // 2 + 1]

            def left(z, up=up):
                for (u0, z0), (u1, z1) in zip(up, up[1:]):
                    if z <= z1 + 1e-9:
                        return u0 + (u1 - u0) * (z - z0) / (z1 - z0)
                return up[-1][0]
            surface(m, g, w_, h, zr, [(h, zr, mat)], [], lod, dict(gtrim, knees=tuple(sorted({z for _, z in up[1:-1]}))),
                    left=left, right=lambda z: w_.L - left(z))
        a0 = XL - (.3 if corner else 0.0) + (0 if corner else E)
        slab(m, prof_u, a0, X - E, lambda a_, q, z: (a_, q, z), lod, rm, end=rm, what="carriage house roof")
        if lod == 0:
            wbox(m, a0 + 3 * E, X - 3 * E, ym - .09, ym + .09, zr + .14, zr + .23, rm, ("z-",))
    else:                                                   # hipped: all four slopes, an eave all round
        party(m, (X, ya), (X, yb), 0.0, h, mat)
        if not corner:
            party(m, (XL, yb), (XL, ya), 0.0, h, mat)
        oy0 = -o if front_free else 2 * E
        x0h = XL - (o if corner else 0.0) + (0 if corner else E)
        zr = pavilion_roof(m, x0h, X - E, ya + oy0 - 0.0, yb + o, h, min(3.2, (X - x0h) / 2 * .95), lod, rm, finial=False)
    if p["cupola"] and lod < 2:                             # a louvred cupola on the ridge
        cx, cy = xm, ym
        zb = zr - .25
        wbox(m, cx - .45, cx + .45, cy - .45, cy + .45, zb, zr + .9, mat, ("z-", "z+"))
        if lod == 0:
            for sgn in (-1, 1):
                m.facing([(cx - .25, cy + sgn * (.45 + E), zr + .25), (cx + .25, cy + sgn * (.45 + E), zr + .25),
                          (cx + .25, cy + sgn * (.45 + E), zr + .75), (cx - .25, cy + sgn * (.45 + E), zr + .75)],
                         (0, sgn, 0), "Black")
        pavilion_roof(m, cx - .62, cx + .62, cy - .62, cy + .62, zr + .92, .8, lod, rm)
