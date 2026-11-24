"""Lobstertown Cannery Row (Claude 2026-11-15, the author: "do whatever you want"): Eastport and Lubec waterfront industry
in Maine shingle and clapboard. Long sheds shoulder to shoulder, one front gable per 8 m cell running front to back,
a raised loading dock under a shed canopy along the street, ridge ventilators (monitors or louvred cupolas), and
on some a brick stack on the ridge. The firm's name is painted on the canopy beam.

    build(lod, W=2, D=4, **variant)

Built on the Boardwalk frame (boardwalk.py): every lot is a row building (party walls both sides), each gable spans
one 8 m cell, so the roof stands at the same height on any lot depth, and the block fills the lot to .6 m off its
rear line. Green industry only: setup lets each building make one clean product (Food, Textiles, Vehicles, Furniture).

Variant keys:
  storeys  1 .. 3: the ground storey is a 4.6 m work floor, the rest 3.0 m lofts
  roofs    a string, one letter per cell from the left: 'g' gable, 'm' gambrel (repeats to fill the lot)
  vents    None | 'monitor' (a long louvred ventilator on every ridge) | 'cupola' (one louvred cupola a cell)
  stack    True | False: a brick stack on the ridge of the left-hand cell, toward the rear
  back     'full' (gables to the rear line) | 'store' (a lower flat-roofed warehouse behind)
  bigdoor  (width, head) of the loading door in the middle of the front; default (2.4, 3.6)
  base     None | a stone for the work floor
  wall, gable_mat, roof_mat, door (doors and louvres), lites, sign (atlas key without 'Sign_')
"""
import math
from lt_kit import Mesh, Wall, surface, finish, wall, style, gable_wall, gable_roof, porch, party, wbox, lbox, chimney, E, TRIM, roof_check
from lt_shapes import cornice_roof
from nf_kit import mansard_row
from lt_designs.shore_row import SIGN_W, SIGN_H
from lt_designs.cottage import cupola
from lt_designs.boardwalk import GAM_KNEE, GAM_IN, PITCH

DOCK = 2.6                    # loading dock depth (in front of the wall)
DECK = .2                     # the walk in front: one sidewalk step up (the author 2026-11-16: entrances at grade)
FRONT = .35                   # the canopy's front edge stays this far inside the lot front (with its .25 overhang)
GROUND = 4.6                  # the work floor
FLOOR = 3.0                   # lofts above it
CANOPY = 4.15                 # canopy beam (same line as the boardwalk arcade, so the sign sits on the same grid)
DEFAULT = dict(storeys=2, roofs="g", vents=None, stack=False, back="full", bigdoor=(2.4, 3.6), base=None,
               wall="ShingleSilver", gable_mat=None, roof_mat="SlateDark", door="Green", lites="2", sign=None)
PICTURESQUE = {"balance": "a working shed: the loading door goes where the work is (Lobstertown standing waiver)"}


def rows(n):
    """(width, sill, head) of the ground storey and each loft above it, and the eave."""
    win = [(.9, 1.55, 3.25)] + [(.9, 5.2 + FLOOR * j, 6.7 + FLOOR * j) for j in range(n - 1)]
    return win, (6.7 + FLOOR * (n - 2) + .95) if n > 1 else 5.2     # a one-storey shed stands tall, clear of the canopy


def monitor(m, g, cx, y0, y1, zr, slope, lod, mat, roof_mat, louvre, rake=TRIM):
    """A long ridge ventilator: a box sunk into the ridge (down to the roof slope at its sides), a clerestory along
    both long faces (a louvre board low in each bay, a glazed light above it, so the long sides are not blank walls,
    rule 13), and its own small gable cap with open eaves. A closed solid like every roof (rule 15)."""
    a = 1.0
    z0, z1 = zr - a * slope - .3, zr + 1.1
    wbox(m, cx - a, cx + a, y0, y1, z0, z1 - E, mat, ("z-", "z+"))
    if lod == 0:                                              # louvres and lights: close view only (LOD1 budget)
        k = max(1, int((y1 - y0 - .6) / 1.6))
        zg = zr + .55                                         # louvre below, glass above
        for i in range(k):                                    # bays between posts
            pa = y0 + .3 + (y1 - y0 - .6) * i / k + .1
            pb = y0 + .3 + (y1 - y0 - .6) * (i + 1) / k - .1
            for x0, x1 in ((cx - a - .03, cx - a), (cx + a, cx + a + .03)):
                wbox(m, x0, x1, pa, pb, zr + .25, zg - .05, louvre, ())
            for s in (-1, 1):                                 # the light: 6 mm proud of the box face (rule 22)
                x = cx + s * (a + .006)
                q = [(x, pa, zg), (x, pb, zg), (x, pb, z1 - .2), (x, pa, z1 - .2)]
                g.facing(q if s > 0 else q[::-1], (s, 0, 0), "Glass")
    gable_roof(m, cx - a, cx + a, y0, y1, z1, z1 + .55, lod, roof_mat, over=(.25, .25), sides=("e", "e"), th=.12, rake=rake)


def _shed(lod, W=2, D=4, **variant):
    v = dict(DEFAULT, **variant)
    n = v["storeys"]
    assert 1 <= n <= 3 and not (n == 1 and v["back"] == "store"), "storeys 1-3; a one-storey shed has no warehouse"
    win, top = rows(n)
    belts = tuple(5.2 + FLOOR * j - .6 for j in range(1, n - 1))          # loft floors above the canopy line
    X = 4.0 * W - .01
    XL = -X
    cw = 2 * X / W                                   # one cell per 8 m of frontage
    cells = [(XL + cw * i, XL + cw * (i + 1)) for i in range(W)]
    yF = -4.0 * D + FRONT + .25 + DOCK              # the front wall, behind the dock
    end = 4.0 * D - .6
    trim = dict(door=v["door"], lites=v["lites"], lean="bare" if n > 2 else True)
    gtrim = dict(trim, simple=True)
    gmat = v["gable_mat"] or v["wall"]
    mats = [(0.0, GROUND if n > 1 else top, v["base"])] + ([(GROUND, top, v["wall"])] if n > 1 else []) \
        if v["base"] else [(0.0, top, v["wall"])]
    main = style(top, mats, win, belts=belts)
    m, g = Mesh(), Mesh()

    # ---- the front: three bays a cell, the loading door on the bay nearest the middle
    bays = [c for a, b in cells for c in ((a + b) / 2 - 2.6, (a + b) / 2, (a + b) / 2 + 2.6)]
    dw, dh = v["bigdoor"]
    dx = min(bays, key=abs)
    wall(m, g, main, (XL, yF), (X, yF), "-", "-", bays, lod, door=(dx, dw, dh), trim=trim, waive=dict(PICTURESQUE))

    # ---- the loading dock and its canopy, the firm's name on the beam
    ax0, ax1 = XL + E, X - E
    span = ax1 - ax0 - .3
    k = max(1, math.ceil(span / 3.2))
    posts = [ax0 + .15 + span * j / k for j in range(k + 1)]
    if lod == 2:
        posts = [posts[0], posts[-1]]
    porch(m, ax0, ax1, yF, DOCK, lod, zf=DECK, zt=CANOPY, posts=posts, mat=v["roof_mat"], rail=False, open_sides=(),
          skirt=False)
    if v["sign"]:                                    # on the beam face, on the atlas tile grid (rule 26)
        yf = yF - DOCK
        sx = min(max(0.0, SIGN_W * math.ceil((ax0 + .2) / SIGN_W)), SIGN_W * math.floor((ax1 - .2) / SIGN_W) - SIGN_W)
        z0 = 6 * SIGN_H                              # 3.48-4.06
        wbox(m, sx - .04, sx + SIGN_W + .04, yf - .03, yf - .004, z0 - .03, z0 + SIGN_H + .03, TRIM, ("y+",))
        ys = yf - .035
        m.facing([(sx, ys, z0), (sx + SIGN_W, ys, z0), (sx + SIGN_W, ys, z0 + SIGN_H), (sx, ys, z0 + SIGN_H)],
                 (0, -1, 0), "Sign_" + v["sign"])

    # ---- the body: front gables (or a warehouse behind), party walls, the rear
    store = v["back"] == "store"
    zS = GROUND if n <= 2 else GROUND + FLOOR        # the warehouse eave
    yR = max(yF + (12.0 if n <= 2 else 16.0), end - (16.0 if n <= 2 else 20.0)) \
        if store and end - yF > (18.0 if n <= 2 else 22.0) else end      # the warehouse stays at most 16-20 m deep
    store = yR < end - .1
    party(m, (X, yF), (X, yR), 0.0, top, v["wall"])
    party(m, (-X, yR), (-X, yF), 0.0, top, v["wall"])
    rb = list(bays)
    rdx = min(rb, key=abs)
    if store:
        rst = style(zS, [(0.0, zS, v["wall"])], [w_ for w_ in win if w_[2] < zS - .3], belts=())
        party(m, (X, yR), (X, end), 0.0, zS, v["wall"])
        party(m, (-X, end), (-X, yR), 0.0, zS, v["wall"])
        wall(m, g, rst, (X, end), (XL, end), "-", "-", rb, lod, door=(rdx, 2.4, 3.2), trim=trim,
             waive={"balance": "the warehouse's loading door"})
        cornice_roof(m, XL + E, X - E, yR + .01, end + .3, zS, lod, deep=.45, ends=v["wall"], front=False)
        if lod < 2:
            wbox(m, XL + E, X - E, end + .3 + E, end + .34, zS + .35, zS + .47, TRIM, ("y-",))   # rear crown
        if n > 1:
            wall(m, g, main, (X, yR), (XL, yR), "-", "-", rb, lod, z0=zS + .45, trim=trim)
    else:
        wall(m, g, main, (X, yR), (XL, yR), "-", "-", rb, lod, door=(rdx, 1.2, 2.95), trim=trim,
             waive={"balance": "the back door to the yard lane"})

    pat = (v["roofs"] * W)[:W]
    for i, ((a, b), kind) in enumerate(zip(cells, pat)):
        cx = (a + b) / 2
        if kind == "m":
            zk, zr = top + GAM_KNEE, top + GAM_KNEE + (cw / 2 - GAM_IN) * .55
            shape, knee, slope = (zk, GAM_IN), (zk, GAM_IN), .55
            fwins = [(cx - 1.4, .8, top + .8, top + 2.15), (cx + 1.4, .8, top + .8, top + 2.15),
                     (cx, .7, zk + .25, zk + 1.1)]
        else:
            zr = top + cw / 2 * PITCH
            shape, knee, slope = None, None, PITCH
            fwins = [(cx, .8, top + .8, top + 2.3)] + ([(cx, .6, top + 2.8, top + 3.5)] if lod < 2 else [])
        gable_wall(m, g, (a, yF), (b, yF), top, zr, lod, gmat, wins=fwins, trim=gtrim, shape=shape)
        gable_wall(m, g, (b, yR), (a, yR), top, zr, lod, gmat, wins=fwins[:1] if kind == "g" else fwins[:2],
                   trim=gtrim, shape=shape)
        gable_roof(m, a + E, b - E, yF, yR, top, zr, lod, v["roof_mat"], over=(.45, .3),
                   sides=("p", "p"), knee=knee)
        th = .16
        sy = yR - max(3.0, (yR - yF) / 4)            # the stack's place on the ridge, toward the rear
        stack = v["stack"] and i == 0
        my1 = (sy - 1.6) if stack else yR - 2.0       # a monitor stops short of the stack
        if v["vents"] == "monitor" and my1 - (yF + 2.0) > 5:
            monitor(m, g, cx, yF + 2.0, my1, zr + th, slope, lod, v["wall"], v["roof_mat"], v["door"])
        elif v["vents"] == "cupola":                 # one ventilator per ~9 m of ridge, evenly spaced
            k = max(1, round((yR - yF) / 9.0))
            for j in range(k):
                cy = yF + (yR - yF) * (j + .5) / k
                if stack and abs(cy - sy) < 2.6:
                    continue
                cupola(m, cx, cy, zr + th, lod, v["wall"], v["roof_mat"], v["door"], a=1.0,
                       sink=1.0 * slope + .3, h=1.6)
        if stack:                                    # rule 12: on the ridge, rising well clear of it
            chimney(m, cx, sy, .55, .55, zr - .55 * slope - .2, zr + 7.0, lod)

    finish(m, g)


# ======================================================================== brick and granite (the author 2026-11-15)
# "very samey with everything else": the brick works get their own material family (rule 20). A granite work
# storey with open loading bays at tailboard height, red brick lofts with granite lintels and sills, granite string
# course and cornice band, dark slate, granite gable copings: no white trim. A granite quay along the street (it
# carries the front outline, so towers and gables behind it never count as extra eave heights).

BG = 4.7            # granite work storey: the material changes under the string course
STRING = 4.76       # granite string course (band 4.70-4.86); the sign board sits under it (4.06-4.64)
TW, TP = 3.4, .6    # stair tower: width, how far it stands forward of the street wall
PW, PP = 6.6, .6    # cross-gabled pavilion: width, projection
XP = 1.0            # side-ridge piles: pitch (steep slate, 45 degrees)
BRICK = dict(storeys=2, roof="front", roofs="g", cross=(), tower=None, stack=False, back="full", arch=True,
             vents="ridge", wall="Brick085", base="Greystone", roof_mat="Slate", door="Black", lites="6", sign=None,
             corner=False, dock=None)


def brick_rows(n, bay=1.9, sill=DECK):
    """The granite storey's loading bays (sill at tailboard height) and the lofts' windows, and the eave."""
    win = [(bay, sill, 3.6, "bay")] + [(1.2, 5.2 + FLOOR * j, 6.9 + FLOOR * j) for j in range(n - 1)]
    return win, 6.9 + FLOOR * (n - 2) + 1.0        # room for the corbel table between the lintels and the cornice


def brick_style(top, v, win, z_from=0.0):
    mats = [(0.0, BG, v["base"]), (BG, top, v["wall"])] if top > BG + .3 else [(0.0, top, v["base"])]
    return style(top, mats, win, belts=(STRING,), plinth=None, corners=False, frieze=.30, belt_mat="Dressed")


def xpile(m, x0, x1, y0, y1, ze, zr, lod, mat, front="e", back="e", th=.16):
    """A gable slab with its ridge along x (across the lot), ends 4 mm in from the party lines (rule 22). front/back:
    'e' an open eave overhanging .35 m, 'v' a valley (the slab runs on .15 m under its neighbour: no crack, no
    shared plane). One closed solid (rule 15)."""
    ym = (y0 + y1) / 2
    s = (zr - ze) / (ym - y0)
    prof = [(y0, ze), (ym, zr), (y1, ze)]
    for idx, kind, d in ((0, front, -1), (-1, back, 1)):
        run = .35 if kind == "e" else .15
        y, z = prof[idx]
        prof[idx] = (y + d * run, z - run * s)
    t = Mesh()
    for (ya, za), (yb, zb) in zip(prof, prof[1:]):
        ny, nz = -(zb - za), (yb - ya)
        if nz < 0:
            ny, nz = -ny, -nz
        t.facing([(x0, ya, za + th), (x0, yb, zb + th), (x1, yb, zb + th), (x1, ya, za + th)], (0, ny, nz), mat)
        t.facing([(x0, ya, za), (x0, yb, zb), (x1, yb, zb), (x1, ya, za)], (0, -ny, -nz), mat)
        for xx, d in ((x0, -1), (x1, 1)):
            t.facing([(xx, ya, za), (xx, yb, zb), (xx, yb, zb + th), (xx, ya, za + th)], (d, 0, 0), mat)
    for idx, d in ((0, -1), (-1, 1)):
        yo, zo = prof[idx]
        t.facing([(x0, yo, zo), (x1, yo, zo), (x1, yo, zo + th), (x0, yo, zo + th)], (0, d, 0), mat)
    roof_check(m, t, f"pile roof y {y0:.2f}..{y1:.2f}")
    if lod == 0:
        wbox(m, x0 + E, x1 - E, ym - .09, ym + .09, zr + th - .02, zr + th + .07, mat, ("z-",))   # ridge roll


def round_stack(m, x, y, z0, z1, lod, mat="Brick074"):
    """A mill chimney: a tapering round brick shaft standing on the ridge (rule 12), a granite cap band, sooty top."""
    k = 12 if lod == 0 else 8 if lod == 1 else 6
    r0, r1 = .85, .62
    ring = lambda r, z: [(x + r * math.cos(2 * math.pi * i / k), y + r * math.sin(2 * math.pi * i / k), z) for i in range(k)]
    a, b = ring(r0, z0), ring(r1, z1 - .45)
    for i in range(k):
        j = (i + 1) % k
        c = ((a[i][0] + a[j][0]) / 2 - x, (a[i][1] + a[j][1]) / 2 - y, .1)
        m.facing([a[i], a[j], b[j], b[i]], c, mat)
    c0, c1 = ring(r1 + .12, z1 - .45), ring(r1 + .12, z1)
    for i in range(k):
        j = (i + 1) % k
        c = ((c0[i][0] + c0[j][0]) / 2 - x, (c0[i][1] + c0[j][1]) / 2 - y, 0)
        m.facing([c0[i], c0[j], c1[j], c1[i]], c, "Dressed")
    m.facing(c0, (0, 0, -1), "Dressed")
    m.facing(c1, (0, 0, 1), "Black")


def pyramid_cap(m, x0, x1, y0, y1, z, lod, mat, over=(.3, .3, .3, .3)):
    """A pyramid roof over a tower: a closed solid (rule 15). over: overhang at x0, x1, y0, y1."""
    a, b, c, d = x0 - over[0], x1 + over[1], y0 - over[2], y1 + over[3]
    ring = [(a, c, z), (b, c, z), (b, d, z), (a, d, z)]
    apex = ((x0 + x1) / 2, (y0 + y1) / 2, z + .95 * (x1 - x0))
    t = Mesh()
    for i in range(4):
        p0, p1 = ring[i], ring[(i + 1) % 4]
        t.facing([p0, p1, apex], ((p0[0] + p1[0]) / 2 - apex[0], (p0[1] + p1[1]) / 2 - apex[1], .6), mat)
    t.facing(ring, (0, 0, -1), "Dressed")
    roof_check(m, t, f"tower cap at x {x0:.2f}")


def corbels(m, w, z_hi, lod, mat, u0=.15, u1=None, step=.4):
    """A corbel table under the cornice band (close view only): two tiers of brick corbels, the upper one bolder,
    4 mm under the band (rule 22). w: the wall (nf_kit Wall); z_hi: the band's underside."""
    if lod:
        return
    u1 = w.L - .15 if u1 is None else u1
    for tier, proud in ((0, .055), (1, .03)):
        zt = z_hi - .004 - tier * .18
        c = u0 + .06 + tier * step / 2
        while c + .06 <= u1:
            lbox(m, w, c - .06, c + .06, zt - .14, zt, E, proud, mat)
            c += step


def rake_corbels(m, A, B, ze, rise, lod, mat, step=.5):
    """Corbels stepping up both rakes of a plain gable (A to B at the eave ze, apex ze + rise), under the coping."""
    if lod:
        return
    w = Wall(A, B)
    half = w.L / 2
    u = .45
    while u <= half - .55:
        z = ze + rise * u / half - .25
        for c in (u, w.L - u):
            lbox(m, w, c - .06, c + .06, z - .14, z, E, .05, mat)
        u += step


def vent(m, cx, cy, zr, sink, lod, wood, louvre, roof_mat, a=.55, h=1.0):
    """A small louvred ridge ventilator: a weathered board box sunk into the ridge, louvre slats on its four faces
    (close view), a slate pyramid cap. No white trim (rule 20: the brick works' family)."""
    z0, z1 = zr - sink, zr + h
    wbox(m, cx - a, cx + a, cy - a, cy + a, z0, z1 - E, wood, ("z-",))
    if lod == 0:
        for j in range(3):
            za = zr + .2 + j * .24
            for x0, x1, y0, y1, sk in ((cx - a + .1, cx + a - .1, cy - a - .03, cy - a - E, "y+"),
                                       (cx - a + .1, cx + a - .1, cy + a + E, cy + a + .03, "y-"),
                                       (cx - a - .03, cx - a - E, cy - a + .1, cy + a - .1, "x+"),
                                       (cx + a + E, cx + a + .03, cy - a + .1, cy + a - .1, "x-")):
                wbox(m, x0, x1, y0, y1, za, za + .09, louvre, (sk,))
    pyramid_cap(m, cx - a, cx + a, cy - a, cy + a, z1, lod, roof_mat, over=(.15, .15, .15, .15))


def mansard_dormer(m, g, cx, y0, d, ze, lod, mat, roof_mat, trim, w=1.3, dz=(.45, 2.2), depth=1.4):
    """A gabled dormer on a mansard's steep slope: its face just behind the slope line at the foot (so the slope
    seals it), a window in it, brick cheeks running back into the roof, a small slate gable cap.
    d = 1: on the street side (faces -y), d = -1: on the rear (faces +y)."""
    x0, x1 = cx - w / 2, cx + w / 2
    zb, zt = ze + dz[0], ze + dz[1]
    A, B = ((x0, y0), (x1, y0)) if d > 0 else ((x1, y0), (x0, y0))
    fw = Wall(A, B)
    surface(m, g, fw, zb, zt, [(zb, zt, mat)], [(w / 2 - .4, w / 2 + .4, zb + .2, zb + 1.5, "win")], lod, trim)
    ya, yb = sorted((y0, y0 + d * depth))
    wbox(m, x0, x1, ya, yb, zb, zt, mat, ("y-" if d > 0 else "y+", "y+" if d > 0 else "y-", "z-", "z+"))
    gable_wall(m, g, A, B, zt, zt + .6, lod, mat)
    gable_roof(m, x0, x1, ya, yb, zt, zt + .6, lod, roof_mat, over=(.15, 0.0) if d > 0 else (0.0, .15),
               sides=("e", "e"), rake="Dressed", th=.1)


def _brick_side_bays(y0, y1, margin=2.1, max_p=4.15):
    """Evenly spaced bay Y-centres along a brick corner's side-street wall (y0..y1), pitch in [3.25, 4.15]."""
    L = y1 - y0
    if L < 6.0:
        return [(y0 + y1) / 2]
    for k in range(2, 30):
        for p in (2.1, 2.0, 2.2, 1.85, 2.4, 2.6, 1.7, 2.8):
            s = (L - 2 * p) / (k - 1)
            if 3.25 <= s <= max_p:
                return [y0 + p + s * i for i in range(k)]
    inner = L - 2 * margin
    k = max(2, math.ceil(inner / max_p) + 1)
    return [y0 + margin + inner * i / (k - 1) for i in range(k)]


def _brick_dormer_side(m, g, x0, cy, ze, lod, mat, roof_mat, trim, w=1.3, dz=(.45, 2.2), depth=1.4):
    """A gabled dormer on the left side-street mansard slope (facing -X)."""
    from lt_shapes import slab
    y0, y1 = cy - w / 2, cy + w / 2
    zb, zt = ze + dz[0], ze + dz[1]
    A, B = (x0, y1), (x0, y0)
    sw = Wall(A, B)
    surface(m, g, sw, zb, zt, [(zb, zt, mat)], [(w / 2 - .4, w / 2 + .4, zb + .2, zb + 1.5, "win")], lod, trim)
    wbox(m, x0, x0 + depth, y0, y1, zb, zt, mat, ("x-", "x+", "z-", "z+"))
    gable_wall(m, g, A, B, zt, zt + .6, lod, mat)
    h, k_ = w / 2 + .12, .6 / (w / 2)
    prof = [(cy - h, zt - .12 * k_), (cy, zt + .6), (cy + h, zt - .12 * k_)]
    slab(m, prof, x0 - .15, x0 + depth, lambda a, q, z: (a, q, z), lod, roof_mat, end="Dressed", eave="Dressed",
         th=.1, what=f"brick side dormer roof at y {cy:.2f}")


def _brick(lod, W=2, D=4, **variant):
    v = dict(BRICK, **variant)
    n = v["storeys"]
    corner = v["corner"]
    assert 2 <= n <= 3, "the brick works are 2-3 storeys"
    win, top = brick_rows(n)
    X = 4.0 * W - .01
    XL = -4.0 * W + .84 if corner else -X
    sx_ = "x" if corner else "-"
    cw = (X - XL) / W
    cells = [(XL + cw * i, XL + cw * (i + 1)) for i in range(W)]
    if v["dock"] is not None:
        yF = -4.0 * D + v["dock"]
        yD = -4.0 * D + .08
    else:
        yF = -4.0 * D + FRONT + .25 + DOCK              # the street wall, behind the quay
        yD = yF - DOCK                                  # the quay's front edge
    end = 4.0 * D - .6
    trim = dict(door=v["door"], lites=v["lites"], lean="bare" if n > 2 else True, frame=v["door"],
                masonry="Dressed", reveal=v["wall"], bay_wall=v["base"], arch=v["arch"])
    gtrim = dict(trim, simple=True)
    main = brick_style(top, v, win)
    m, g = Mesh(), Mesh()
    bays = [c for a, b in cells for c in ((a + b) / 2 - cw * .24, (a + b) / 2 + cw * .24)]

    # ---- what stands forward of the street wall: a stair tower at one end, cross-gabled pavilions
    tower = v["tower"]
    if tower == "left":
        tx0, tx1, tparty = (XL if corner else XL + .012), (XL if corner else XL + .012) + TW, (XL if corner else XL + .012)
    elif tower == "right":
        tx0, tx1, tparty = X - TW, X - .012, X - .012
    pav = [((cells[i][0] + cells[i][1]) / 2 - PW / 2, (cells[i][0] + cells[i][1]) / 2 + PW / 2) for i in v["cross"]] \
        if v["roof"] == "side" else []
    fronts = sorted(pav + ([(tx0 if tower == "right" else XL, tx1 if tower == "left" else X)] if tower else []))

    # ---- the granite walk: one sidewalk step up from the street, the bays open level off it (the author: at grade)
    ax_lo = -4.0 * W + .08 if corner else XL + E
    wbox(m, ax_lo, X - E, yD, yF - E, 0.0, DECK, v["base"], ("y+", "z+"))
    m.facing([(ax_lo, yD, DECK), (X - E, yD, DECK), (X - E, yF - E, DECK), (ax_lo, yF - E, DECK)], (0, 0, 1), "Paving")
    if corner:                                          # granite walk carries down the side street
        wbox(m, ax_lo, XL - E, yF, end, 0.0, DECK, v["base"], ("x+", "z+"))
        m.facing([(ax_lo, yF, DECK), (XL - E, yF, DECK), (XL - E, end, DECK), (ax_lo, end, DECK)], (0, 0, 1), "Paving")

    # ---- the street wall, in runs between whatever stands forward of it
    runs, x = [], XL
    for a, b in fronts:
        if a - x > .5:
            runs.append((x, a))
        x = b
    if X - x > .5:
        runs.append((x, X))
    fw_waive = dict(PICTURESQUE, **({"corners": "brick mill corner pier"} if corner else {}))
    for a, b in runs:
        rb = [c for c in bays if a + 1.0 <= c <= b - 1.0]
        fw = wall(m, g, main, (a, yF), (b, yF), (sx_ if a == XL else "c"), ("-" if b == X else "c"), rb, lod, trim=trim,
                  waive=fw_waive)
        corbels(m, fw, top - .30, lod, v["wall"])
    zr_max = top + 4.7
    for x0p, x1p in pav:                            # a cross-gabled pavilion: its own front, two short cheeks
        yP, cx = yF - PP, (x0p + x1p) / 2
        pst = brick_style(top, v, brick_rows(n, 1.6, DECK + .03)[0])   # sills 3 cm over the quay it stands on
        pw = wall(m, g, pst, (x0p, yP), (x1p, yP), "x", "x", [cx - 1.5, cx + 1.5], lod, trim=trim, waive=dict(PICTURESQUE))
        corbels(m, pw, top - .30, lod, v["wall"])
        wall(m, g, main, (x0p, yF), (x0p, yP), "c", "x", [], lod, trim=trim)
        wall(m, g, main, (x1p, yP), (x1p, yF), "x", "c", [], lod, trim=trim)
        zc = top + PW / 2
        gable_wall(m, g, (x0p, yP), (x1p, yP), top, zc, lod, v["wall"], wins=[(cx, .9, top + .5, top + 1.9)], trim=gtrim)
        gable_roof(m, x0p, x1p, yP, yF + (zc - top) / XP + .5, top, zc, lod, v["roof_mat"], over=(.3, 0.0),
                   sides=("e", "e"), rake="Dressed")

    # ---- the body: party walls (or corner side-street elevation), the rear (or a lower warehouse behind)
    store = v["back"] == "store"
    zS = GROUND if n <= 2 else GROUND + FLOOR
    yR = max(yF + (12.0 if n <= 2 else 16.0), end - (16.0 if n <= 2 else 20.0)) \
        if store and end - yF > (18.0 if n <= 2 else 22.0) else end
    store = yR < end - .1
    party(m, (X, yF), (X, yR), 0.0, top, v["wall"])
    ys_side = []
    if corner:
        y_s0 = (yF - TP + TW) if tower == "left" else yF
        ys_side = _brick_side_bays(y_s0, yR, margin=2.1, max_p=4.15)
        sw_m = wall(m, g, main, (XL, yR), (XL, y_s0), ("-" if store else "x"), ("c" if tower == "left" else "x"),
                    ys_side, lod, trim=trim, waive=dict(PICTURESQUE, corners="brick mill corner pier"))
        corbels(m, sw_m, top - .30, lod, v["wall"])
    else:
        party(m, (-X, yR), (-X, yF), 0.0, top, v["wall"])
    rdx = min(bays, key=abs)
    if store:
        sw = [w_ for w_ in win if w_[2] < zS - .3]
        rst = style(zS, [(0.0, min(BG, zS), v["base"])] + ([(BG, zS, v["wall"])] if zS > BG + .3 else []), sw,
                    belts=(STRING,), plinth=None, corners=False, frieze=.30, belt_mat="Dressed")
        party(m, (X, yR), (X, end), 0.0, zS, v["wall"])
        if corner:
            ys_w = _brick_side_bays(yR, end, margin=2.1, max_p=4.2)
            sw_s = wall(m, g, rst, (XL, end), (XL, yR), "x", "-", ys_w, lod, trim=trim,
                        waive=dict(PICTURESQUE, corners="warehouse side street"))
            corbels(m, sw_s, zS - (.10 if zS > BG + .3 else .30), lod, v["wall"])
        else:
            party(m, (-X, end), (-X, yR), 0.0, zS, v["wall"])
        sw_ = wall(m, g, rst, (X, end), (XL, end), "-", sx_, bays, lod, door=(rdx, 1.4, 3.0), trim=trim,
                   waive={"balance": "the warehouse's loading door", **({"corners": "warehouse rear corner"} if corner else {})})
        corbels(m, sw_, zS - (.10 if zS > BG + .3 else .30), lod, v["wall"])
        cornice_roof(m, XL - (.3 if corner else -E), X - E, yR + .01, end + .3, zS, lod, deep=.45, side="Dressed",
                     ends="Dressed" if corner else v["wall"], front=False)
        if lod < 2:
            wbox(m, XL - (.3 if corner else -E), X - E, end + .3 + E, end + .34, zS + .35, zS + .47, "Dressed", ("y-",))
        rw = wall(m, g, main, (X, yR), (XL, yR), "-", sx_, bays, lod, z0=zS + .45, trim=trim,
                  waive={"corners": "upper rear corner"} if corner else {})
        corbels(m, rw, top - .30, lod, v["wall"])
    else:
        rw = wall(m, g, main, (X, yR), (XL, yR), "-", sx_, bays, lod, door=(rdx, 1.4, 3.0), trim=trim,
                  waive={"balance": "the back door to the yard lane", **({"corners": "rear lane corner"} if corner else {})})
        corbels(m, rw, top - .30, lod, v["wall"])

    # ---- the roof
    stack_at = None
    scell = cells[-1] if tower == "left" else cells[0]
    if v["roof"] == "side":                         # parallel piles across the lot, valleys between them
        k = max(1, math.ceil((yR - yF) / 12.0))
        edges = [yF + (yR - yF) * i / k for i in range(k + 1)]
        for i, (ya, yb) in enumerate(zip(edges, edges[1:])):
            zr = top + XP * (yb - ya) / 2
            ins = E + (i % 2) * .004                 # neighbouring piles' ends 4 mm apart where they cross (rule 22)
            xpile(m, (XL - .3 + (i % 2) * .004 if corner else XL + ins), X - ins, ya, yb, top, zr, lod, v["roof_mat"],
                  "e" if i == 0 else "v", "e" if i == k - 1 else "v")
            m.facing([(X, ya, top), (X, yb, top), (X, (ya + yb) / 2, zr)], (1, 0, 0), v["wall"])
            if corner:
                ym_ = (ya + yb) / 2
                gw = [(ym_, .9, top + .8, top + 2.2)]
                gable_wall(m, g, (XL, yb), (XL, ya), top, zr, lod, v["wall"], wins=gw, trim=gtrim)
                rake_corbels(m, (XL, yb), (XL, ya), top, zr - top, lod, v["wall"])
            else:
                m.facing([(-X, ya, top), (-X, yb, top), (-X, (ya + yb) / 2, zr)], (-1, 0, 0), v["wall"])
        zr_max = top + XP * (edges[1] - edges[0]) / 2
        stack_at = ((scell[0] + scell[1]) / 2, (edges[-2] + edges[-1]) / 2, zr_max)
        ridges = [((a + b) / 2, (ya + yb) / 2, zr_max, .55 * XP + .3) for a, b in cells
                  for ya, yb in zip(edges, edges[1:])]
    elif v["roof"] == "mansard":                    # the mansard storey: steep slate, a low tin deck
        h1, i1, h2 = 3.0, .9, 1.0
        msides = dict(x0="s", x1="e") if corner else dict(x0="e", x1="e")
        mridge = ("x" if (X - XL) >= (yR - yF) else "y") if corner else "x"
        mansard_row(m, XL + E, X - E, yF, yR, top, h1, i1, h2, lod, sides=msides, ridge=mridge,
                    steep=v["roof_mat"], deck="TinFlat", roll="Iron", end=v["wall"])
        zr_max = top + h1 + h2
        stack_at = ((scell[0] + scell[1]) / 2, (yF + yR) / 2, top + h1)
        ridges = [((a + b) / 2, (yF + yR) / 2, zr_max, .3) for a, b in cells]
        tx = (tx0 - .9, tx1 + .9) if tower else (0, 0)
        for cx in bays:                             # a gabled dormer on every window axis, front and rear (rule 10)
            for y0, d in ((yF + .15, 1), (yR - .15, -1)):
                if d > 0 and tx[0] < cx < tx[1]:
                    continue
                mansard_dormer(m, g, cx, y0, d, top, lod, v["wall"], v["roof_mat"], gtrim)
        if corner:
            for cy in (ys_side[::2] if lod == 2 else ys_side):
                _brick_dormer_side(m, g, XL + .15, cy, top, lod, v["wall"], v["roof_mat"], gtrim)
    else:                                           # a front gable (or gambrel) on every 8 m cell
        pat = (v["roofs"] * W)[:W]
        ridges = []
        for i, ((a, b), kind) in enumerate(zip(cells, pat)):
            cx = (a + b) / 2
            if kind == "m":
                zk, zr = top + GAM_KNEE, top + GAM_KNEE + (cw / 2 - GAM_IN) * .55
                shape, knee, slope = (zk, GAM_IN), (zk, GAM_IN), .55
                fwins = [(cx - 1.4, .8, top + .8, top + 2.15), (cx + 1.4, .8, top + .8, top + 2.15),
                         (cx, .7, zk + .25, zk + 1.1)]
            else:
                zr = top + cw / 2 * PITCH
                shape, knee, slope = None, None, PITCH
                fwins = [(cx, .9, top + .8, top + 2.4)] + ([(cx, .6, top + 2.9, top + 3.5)] if lod < 2 else [])
            zr_max = max(zr_max if i else 0, zr)
            gable_wall(m, g, (a, yF), (b, yF), top, zr, lod, v["wall"], wins=fwins, trim=gtrim, shape=shape)
            if kind != "m":
                rake_corbels(m, (a, yF), (b, yF), top, zr - top, lod, v["wall"])
                rake_corbels(m, (b, yR), (a, yR), top, zr - top, lod, v["wall"])
            gable_wall(m, g, (b, yR), (a, yR), top, zr, lod, v["wall"], wins=fwins[:1] if kind == "g" else fwins[:2],
                       trim=gtrim, shape=shape)
            gable_roof(m, a + E, b - E, yF, yR, top, zr, lod, v["roof_mat"], over=(.25, .25),
                       sides=("e" if corner and i == 0 else "p", "p"), knee=knee, rake="Dressed")
            if v["vents"] == "monitor" and yR - yF > 9:
                monitor(m, g, cx, yF + 2.0, yR - 2.0, zr + .16, slope, lod, "ShingleGrey", v["roof_mat"], v["door"],
                        rake=v["roof_mat"])
            if (a, b) == scell:
                stack_at = (cx, yR - max(3.0, (yR - yF) / 4), zr)
            kv = max(1, round((yR - yF - 6.0) / 9.0))
            ridges += [(cx, yF + 4.0 + (yR - yF - 7.0) * (j + .5) / kv, zr, .55 * slope + .3) for j in range(kv)]
    if v["stack"] and stack_at:
        sx, sy, sz = stack_at
        round_stack(m, sx, sy, sz - 1.0, sz + 9.0, lod)
    if v["vents"] == "ridge":                       # louvred ventilators along the ridges, clear of the stack
        for cx, cy, zr, sink in ridges:
            if v["stack"] and stack_at and abs(cx - stack_at[0]) < 2.5 and abs(cy - stack_at[1]) < 2.5:
                continue
            vent(m, cx, cy, zr + .16, sink, lod, "ShingleGrey", v["door"], v["roof_mat"])

    # ---- the stair tower, standing forward onto the quay and rising clear of the roof
    if tower:
        yT, yB = yF - TP, yF - TP + TW
        xo = tx1 if tower == "left" else tx0         # its open side
        xc = (tx0 + tx1) / 2
        rows = [(1.1, DECK, 3.6)]                    # whole floors, until it stands 1.8 m clear of the ridge
        while rows[-1][2] + .8 < zr_max + 1.8:
            j = len(rows) - 1
            rows.append((.9, 5.2 + FLOOR * j, 6.9 + FLOOR * j))
        Ht = rows[-1][2] + .8
        tst = brick_style(Ht, v, rows)
        se = (("x" if corner else "-"), "x") if tower == "left" else ("x", "-")
        wall(m, g, tst, (tx0, yT), (tx1, yT), se[0], se[1], [xc], lod, door=(xc, 1.1, 3.8), trim=trim,
             waive=dict(PICTURESQUE))
        above = {"glass": "the stair tower above the roof: one window a floor"}
        if tower == "left":
            wall(m, g, tst, (xo, yT), (xo, yF), "x", "c", [], lod, trim=trim, top=top)
            wall(m, g, tst, (xo, yT), (xo, yB), "x", "x", [yT + TW / 2], lod, z0=top, trim=trim, waive=above)
            wall(m, g, tst, (xo, yB), (tparty, yB), "x", ("x" if corner else "-"), [xc], lod, z0=top, trim=trim, waive=above)
            if corner:
                tst_s = brick_style(Ht, v, [(1.1, 1.3, 3.4)] + rows[1:])
                wall(m, g, tst_s, (tparty, yB), (tparty, yT), "c", "x", [yT + TW / 2], lod, trim=trim,
                     waive=dict(PICTURESQUE, **above))
            else:
                party(m, (tparty, yB), (tparty, yT), 0.0, Ht, v["wall"])
        else:
            wall(m, g, tst, (xo, yF), (xo, yT), "c", "x", [], lod, trim=trim, top=top)
            wall(m, g, tst, (xo, yB), (xo, yT), "x", "x", [yT + TW / 2], lod, z0=top, trim=trim, waive=above)
            wall(m, g, tst, (tparty, yB), (xo, yB), "-", "x", [xc], lod, z0=top, trim=trim, waive=above)
            party(m, (tparty, yT), (tparty, yB), 0.0, Ht, v["wall"])
        ov = ((.3 if corner else 0.0), .3, .3, .3) if tower == "left" else (.3, 0.0, .3, .3)
        pyramid_cap(m, tx0, tx1, yT, yB, Ht + E, lod, v["roof_mat"], over=ov)

    # ---- the firm's name, painted on a board on the granite storey under the string course (rule 26: on the grid)
    if v["sign"]:
        for sx in (0.0, -SIGN_W, SIGN_W, -2 * SIGN_W, 2 * SIGN_W):
            hit = [f for f in fronts if f[0] - .2 < sx + SIGN_W and sx < f[1] + .2]
            inside = [f for f in pav if f[0] + .2 <= sx and sx + SIGN_W <= f[1] - .2]
            if XL + .3 <= sx and sx + SIGN_W <= X - .3 and (not hit or (inside and hit == inside)):
                break
        yf = yF - PP if inside else yF
        z0 = 7 * SIGN_H
        wbox(m, sx - .04, sx + SIGN_W + .04, yf - .03, yf - .004, z0 - .03, z0 + SIGN_H + .03, "Dressed", ("y+",))
        ys = yf - .035
        m.facing([(sx, ys, z0), (sx + SIGN_W, ys, z0), (sx + SIGN_W, ys, z0 + SIGN_H), (sx, ys, z0 + SIGN_H)],
                 (0, -1, 0), "Sign_" + v["sign"])

    finish(m, g)


def build(lod, W=2, D=4, **variant):
    """Brick and granite works (masonry=True), or the weathered board sheds (the Lobster Pound, the Smokehouse)."""
    if variant.pop("masonry", False):
        return _brick(lod, W, D, **variant)
    return _shed(lod, W, D, **variant)
