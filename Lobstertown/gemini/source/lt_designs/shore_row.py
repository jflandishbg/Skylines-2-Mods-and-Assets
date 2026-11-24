"""Lobstertown L1 "Shore Rows": tall, narrow shingle row houses shoulder to shoulder on 1-wide lots (8 m).
Deep lots fill up like a Maine connected farm: big house, little house (an ell down the left party wall),
back house, barn across the back, round a paved yard walk that links every yard door.

    build(lod, D, **variant)    D = lot depth in cells (2..6)

Variant keys:
  storeys  2 | 3 | 4 (gambrel and saltbox are always 2)
  roof     'gable' (front gable) | 'gambrel' | 'saltbox' (side gable, long rear slope) | 'flat' (deep cornice) |
           'mansard' (steep front and rear slopes, flat top, dormers on both slopes)
  front    'shop' (Main Street: a painted shopfront at the sidewalk, the flats' own street door beside it, a fascia
           with the shop's sign; the house stands SHOP_SET from the lot front) | 'porch' | 'bay' | 'double' | 'hood' | 'stoop' | 'turret' | 'triple' | 'quad' (stacked porches up to the
           cornice; flat roofs) | 'oriel' (full porch, a two-storey oriel above it)
  rear     'farm' (2-storey ell, back house, barn) | 'cape' (a 1.5-storey ell, then 2-storey back house and barn) |
           'tall' (an ell as tall as a 3-storey house, then a 2-storey back house and barn)
  hand     'L' (ell on the left, as seen from the street) | 'R' (mirrored: ell on the right)
  corner   False | True: a LeftCorner building. The street side is the left (x = XL, set in 0.4 m so the eave
           stays on the lot): windows down the house, the ell and the barn; eaves overhang that side.
  turret_side  1 (right) | -1 (left: the corner)
  dormers  False | True
  upper    None | 'oriel' (shop fronts: a two-storey oriel over the fascia)
  sign     shop fronts: the atlas sign key without 'Sign_' (HarborHardware, ...); None = a plain painted fascia
  wall, gable_mat, roof_mat, door, shutters, lites ('2' | '6'), back_mat (the back house), barn_mat.

the author 2026-11-14 (in game): the widow's walk is gone; the yard gets a walk door to door; corners; more height
variety front and rear ("this on steroids").
"""
import math
from lt_kit import (Mesh, Wall, party, chimney, finish, wall, style, gable_wall, gable_roof, porch, bay, wbox,
                    lbox, E, TRIM)
from lt_shapes import slab, dormer, side_dormers, turret, cornice_roof

X = 3.99                      # party walls on the side lot lines
CI = .40                      # corner buildings: the street-side wall stands this far in (its eave overhangs .35)
BX = 1.0                      # the ell runs from the left wall to BX, leaving a 3 m side yard
DEPTH = 11.0                  # main house depth
SET = 3.6                     # main front wall back from the lot front (porch and steps in front)
SHOP_SET = 1.0                # Main Street: the shopfront stands at the sidewalk (room for the cornice overhang)
SHOP_HEAD = 3.25              # shopfront head; the fascia runs 3.30-4.12 with its cap above, under the 2nd floor sills
SIGN_W, SIGN_H = 3.0, .58     # a sign slot maps once onto a plate this size, on a tile boundary (lt_atlas.SIGN_M)
WIN1 = [(.9, 1.0, 2.7)]                                              # one storey (the cape ell)
WIN2 = [(.9, 1.55, 3.25), (.9, 4.4, 5.9)]                            # two storeys
WIN3 = [(.9, 1.55, 3.25), (.9, 4.55, 6.25), (.9, 7.5, 8.95)]        # three storeys (rule 4/5 checked)
WIN4 = WIN3 + [(.9, 10.5, 11.95)]                                    # four storeys
TOPS = {2: 6.7, 3: 9.9, 4: 12.9}
BELTS = {2: (3.75,), 3: (3.75, 6.85), 4: (3.75, 6.85, 9.85)}
WINS = {2: WIN2, 3: WIN3, 4: WIN4}
ELL, CAPE = 6.5, 3.6
SALT_RIDGE, SALT_PITCH = 4.0, .85   # saltbox: ridge 4 m behind the front wall, both slopes at 0.85
MANS_RUN, MANS_RISE = 1.2, 3.0      # mansard: the steep slope climbs 3 m in 1.2 m, then a flat deck
DEFAULT = dict(storeys=3, roof="gable", front="porch", rear="farm", hand="L", corner=False, turret_side=1,
               wall="ShingleSilver", gable_mat=None, roof_mat="SlateDark", door="Oxblood", shutters=None, lites="2",
               back_mat="Clapboard", barn_mat="ShingleGrey", dormers=False,
               decks=False, upper=None, sign=None)
SIDE_HALL = {"balance": "side-hall row house: the door takes one side bay, as on every narrow New England row"}


def plan(D, rear, setback=SET):
    """Where each part of the connected farm sits for a lot D cells deep: (main front, main rear, pieces)."""
    y0 = -4.0 * D
    yF = y0 + setback
    yR = yF + DEPTH
    end = 4.0 * D - .6                           # keep .6 m to the rear line
    room = end - yR
    pieces = []
    # the author 2026-11-15: every lot is built out to .6 m from its rear line. An empty strip inside the lot is dead
    # ground: Placemaker can't landscape it and it reads as a lot too big for its house.
    if room < 6.5:                               # a short lot: the main house runs on to the rear
        return yF, end, pieces
    if rear == "tall":                           # a tall ell, then a lower back house, then the barn
        ell = room if room < 9 else 5.0
        left = room - ell
        back = left if left < 12 else max(6.0, left - 14.0)
        lens = [("ell", ell), ("back", back), ("barn", left - back)]
    elif room < 13:
        lens = [("ell", room)]
    elif room < 21:
        lens = [("ell", 7.0), ("barn", room - 7.0)]
    else:
        x = room - 21.0
        ell, back = 7.0 + min(2.0, x * .25), 6.0 + min(3.0, x * .4)
        lens = [("ell", ell), ("back", back), ("barn", room - ell - back)]
    y = yR
    for k, L in lens:
        if L > .5:
            pieces.append((k, y, y + L))
            y += L
    return yF, yR, pieces


def rear_decks(m, x0, x1, yw, depth, levels, lod):
    """Stacked wooden decks on a rear wall at yw (facing +Y), each a porch floor with rail and posts, the lowest
    carried down to the ground on posts. Built as front porches in a scratch mesh, then turned to face the back."""
    t = Mesh()
    posts = [x0 + .15, x1 - .15]
    for zf, zt in levels:
        porch(t, x0, x1, -yw, depth, lod, zf=zf, zt=zt, posts=posts, roof=False, open_sides=("l", "r"))
    for px in posts:                                 # the legs under the lowest deck
        wbox(t, px - .09, px + .09, -yw - depth + .06, -yw - depth + .24, 0.0, levels[0][0] - .12 - E, TRIM, ("z-",))
    for p, f, k in zip([None] * len(t.f), t.f, t.m):  # turn round: mirror y, keep faces outward
        pts = [(x, -y, z) for x, y, z in (t.v[i] for i in f)][::-1]
        mat = t.mats[k]
        if mat not in m.mats:
            m.mats.append(mat)
        i = len(m.v)
        m.v += pts
        m.f.append(list(range(i, i + len(pts))))
        m.m.append(m.mats.index(mat))


def pstyle(h, mat):
    """Facade style of a rear piece by its eave height: one, two or three storeys of windows."""
    win = WIN1 if h < 4.5 else WIN2 if h < 7.5 else WIN3
    belts = () if h < 4.5 else (3.75,) if h < 7.5 else (3.75, 6.85)
    return style(h, [(0.0, h, mat)], win, belts=belts)


def build(lod, D=3, **variant):
    v = dict(DEFAULT, **variant)
    kind = v["roof"]
    gam, salt, flat, mans = kind == "gambrel", kind == "saltbox", kind == "flat", kind == "mansard"
    corner = v["corner"]
    rear = "farm" if salt else v["rear"]
    n = 2 if (gam or salt) else v["storeys"]
    top = TOPS[n]
    win, belts = WINS[n], BELTS[n]
    XL = -X + CI if corner else -X              # the left wall: a party line, or the street side of a corner
    xm = (XL + X) / 2
    trim = dict(door=v["door"], shutters=v["shutters"], lites=v["lites"])
    gmat = v["gable_mat"] or v["wall"]
    gtrim = dict(trim, shutters=None)          # gables and the plainer back wings carry no shutters
    m, g = Mesh(), Mesh()
    shop = v["front"] == "shop"
    yF, yR, pieces = plan(D, rear, SHOP_SET if shop else SET)
    if salt:
        yr = yF + SALT_RIDGE + (yR - yF - DEPTH)       # a short lot runs the house on: the ridge moves back with it
        zr = top + SALT_RIDGE * SALT_PITCH
        rtop = zr - (yR - yr) * SALT_PITCH        # the long rear slope comes down to a one-storey eave
    else:
        rtop = top
    base = top if gam else rtop if salt else ELL  # back house and barn: wings meet a gambrel or saltbox at its eave
    H = {"ell": CAPE if rear == "cape" else min(top, TOPS[3]) if rear == "tall" else base, "back": base, "barn": base}
    main = style(top, [(0.0, top, v["wall"])], win, belts=belts)
    back = style(rtop, [(0.0, rtop, v["wall"])], WIN2, belts=(3.75,) if rtop > 4.5 else ())
    sx = "x" if corner else "-"                  # what the left end of a cross wall is: a street corner or a party end
    lside = ("e" if corner else "p")             # roofs: an open eave over the street, or closed on the party line

    # ---- the street front
    front, omit, waive = v["front"], [], dict(SIDE_HALL)
    tsd = v["turret_side"]
    dx = 2.5 if (corner and front != "turret") or (front == "turret" and tsd < 0) else -2.5   # the door bay
    stair = (dx - .6, dx + .6)
    bays = [-2.1, xm, 2.5] if corner else [-2.5, 0.0, 2.5]
    if front == "bay":
        omit = [(2.0, 0), (2.0, 1)]
        bays = [-2.5, 2.0]
        waive["glass"] = "the canted bay carries the glass of the two lower floors"
        waive["rhythm"] = "two bays, door and canted bay, as on a bay-and-gable house"
    elif front == "turret":
        bays = [-2.5, 0.0] if tsd > 0 else [.3, 2.5]
        waive["glass"] = "the corner turret carries the glass of its bay"
        waive["rhythm"] = "two bays beside a corner turret, as on a Queen Anne row house"
    elif front == "baytriple":
        bays = [-2.5, -.6, 2.45]
        omit = [(2.45, f) for f in range(len(win))]
        waive["glass"] = "the full-height bay carries the glass of the right-hand bay"
        waive["rhythm"] = "two bays of porch beside a full-height bay, as on a Portland triple-decker"
    elif front == "oriel":
        c = xm
        omit = [(c, 1), (c, 2)]
        waive["glass"] = "the oriel carries the glass of the middle bay on the second and third floors"
        waive["rhythm"] = "the oriel fills the middle bay on the second and third floors"
    fst, ftrim, holes = main, trim, ()
    if shop:                                        # Main Street: flats' door on one side, the shopfront beside it
        dx = 2.5 if corner else -2.5
        stair = (dx - .6, dx + .6)
        bays = [-2.1, xm, 2.5] if corner else [-2.5, 0.0, 2.5]
        sa, sb = (XL + .75, 1.45) if corner else (-1.45, X - .64)   # clear of the door surround (rule 8)
        sm = (sa + sb) / 2
        holes = [(sa - XL, sb - XL, 0.0, SHOP_HEAD, "shop")]
        ftrim = dict(trim, shopdoor=(sm - .55 - XL, sm + .55 - XL))
        fst = style(top, [(0.0, top, v["wall"])], win, belts=belts[1:])     # the fascia takes the first belt's place
        omit = [(c, 0) for c in bays if c != dx]
        if corner:
            waive["corners"] = "the corner shop's window runs to a corner pier, as on a New England commercial block"
        if v["upper"] == "oriel":
            omit += [(xm, 1), (xm, 2)]
            waive["glass"] = "the oriel carries the glass of the middle bay on the second and third floors"
            waive["rhythm"] = "the oriel fills the middle bay on the second and third floors"
    fw_ = wall(m, g, fst, (XL, yF), (X, yF), sx, "-", bays, lod, door=(dx, 1.0, 2.95), trim=ftrim, waive=waive,
               omit=omit, plinth_cuts=[stair], holes=holes)
    if shop and lod < 2:                            # shop pilasters, the fascia and its cap, the sign
        ua, ub = sa - XL, sb - XL
        paint = v["door"]
        for u0, u1 in ((ua - .3, ua), (ub, ub + .3)):
            lbox(m, fw_, u0, u1, 0.0, 3.30 - E, E, .14, paint, ("in", "bot"))
        lbox(m, fw_, ua - .3, ub + .3, 3.30, 4.12, E, .16, paint, ("in",))
        lbox(m, fw_, ua - .36, ub + .36, 4.12 + E, 4.18, E, .22, TRIM)
    if shop and v["sign"]:
        z0 = 6 * SIGN_H                               # 3.48-4.06, on the tile grid; x 0-3 m (the hand R mirror: -3-0)
        ys = yF - .16 - E
        m.facing([(0.0, ys, z0), (SIGN_W, ys, z0), (SIGN_W, ys, z0 + SIGN_H), (0.0, ys, z0 + SIGN_H)], (0, -1, 0),
                 "Sign_" + v["sign"])
    po = ("l",) if corner else ()
    if front in ("porch", "oriel"):
        porch(m, XL + E, X - E, yF, 2.3, lod, stair=stair, mat=v["roof_mat"], open_sides=po)
    elif front == "double":
        porch(m, XL + E, X - E, yF, 2.3, lod, zt=3.7, stair=stair, roof=False, open_sides=po)
        porch(m, XL + E, X - E, yF, 2.3, lod, zf=3.88, zt=ELL + .02, mat=v["roof_mat"], open_sides=po)
    elif front in ("triple", "quad", "baytriple"):  # stacked decks; a flat roof's cornice runs out over the top one,
        # under a gable or mansard the top deck carries its own shed roof, kept under the main eave
        roofed = not flat
        if front == "quad":
            decks = [(.79, 3.7), (3.88, 6.7), (6.88, 9.7), (9.88, top - .01)]
        else:
            decks = [(.79, 3.7), (3.88, 6.95), (7.13, 9.2 if roofed else top - .01)]
        px1 = 1.15 if front == "baytriple" else X - E          # beside a full-height bay the decks stop short of it
        pos = ("r",) if front == "baytriple" else po
        for k, (zf, zt) in enumerate(decks):
            last = k == len(decks) - 1
            porch(m, XL + E, px1, yF, 2.3, lod, zf=zf, zt=zt, stair=stair if k == 0 else None,
                  roof=roofed and last, mat=v["roof_mat"], open_sides=pos)
        if front == "baytriple":                    # a canted bay the full height of the house, under the cornice
            bay(m, g, 2.45, yF, 1.2, .6, 0.0, top - .6, lod, v["wall"], [(a, b) for _, a, b in win], trim,
                v["roof_mat"], v["lites"])
    elif front in ("hood", "bay"):
        porch(m, -X + E, -1.25, yF, 2.0, lod, stair=stair, mat=v["roof_mat"], open_sides=("r",),
              posts=[-X + .2, -1.4])
    elif front == "stoop":                          # a small covered stoop, too small to count as a roof level
        porch(m, -3.25, -1.75, yF, .7, lod, stair=stair, mat=v["roof_mat"], open_sides=(), posts=[-3.1, -1.9])
    elif front == "turret":
        if tsd > 0:
            porch(m, -X + E, .8, yF, 2.0, lod, stair=stair, mat=v["roof_mat"], open_sides=("r",),
                  posts=[-X + .2, .65])
            tx = 2.3
        else:                                       # the turret takes the street corner, the porch the party side
            porch(m, -.8, X - E, yF, 2.0, lod, stair=stair, mat=v["roof_mat"], open_sides=("l",),
                  posts=[-.65, X - .2])
            tx = XL + 1.3 + .02
        turret(m, g, tx, yF, 1.3, 0.0, top, 3.9, lod, v["wall"], [(a, b) for _, a, b in win], gtrim,
               v["roof_mat"], belts=belts, lites=v["lites"])
    if front == "bay":
        bay(m, g, 2.0, yF, 1.5, .75, 0.0, top - .45 if gam else 6.75, lod, v["wall"],
            [(1.55, 3.25), (4.55 if not gam else 4.4, 6.25 if not gam else 5.9)], trim, v["roof_mat"], v["lites"])
    if front == "oriel" or v["upper"] == "oriel":   # a two-storey oriel on brackets above the porch roof (or fascia)
        z0, z1, wd, pj = 4.4 if shop else 4.0, 9.4, 1.9 if corner else 2.2, .6
        bay(m, g, xm, yF, wd, pj, z0, z1, lod, v["wall"], [(4.55, 6.25), (7.5, 8.95)], trim, v["roof_mat"],
            v["lites"])
        a = wd / 2 + pj
        m.facing([(xm - a, yF, z0), (xm - wd / 2, yF - pj, z0), (xm + wd / 2, yF - pj, z0), (xm + a, yF, z0)],
                 (0, 0, -1), TRIM)

    # ---- side walls and the main roof
    if corner:                                      # the side street: three rows of windows down the house
        wall(m, g, main, (XL, yR), (XL, yF), "-" if pieces else "x", "x", [yF + 1.6, yF + 4.2, yF + 6.8, yF + 9.4], lod,
             trim=trim)
    if salt:
        for xx, d in ((X, 1), (-X, -1)):            # the saltbox gables stand on the party lines
            m.facing([(xx, yF, 0.0), (xx, yR, 0.0), (xx, yR, rtop - .03), (xx, yr, zr - .03), (xx, yF, top - .03)],
                     (d, 0, 0), v["wall"])   # 3 cm under the slab, not flush with its end
        o = .35
        prof = [(yF - o, top - o * SALT_PITCH), (yr, zr), (yR + o, rtop - o * SALT_PITCH)]
        slab(m, prof, -X + E, X - E, lambda a, q, z: (a, q, z), lod, v["roof_mat"], end=v["roof_mat"],
             what="saltbox roof")
        if lod == 0:
            wbox(m, -X + 3 * E, X - 3 * E, yr - .09, yr + .09, zr + .14, zr + .23, v["roof_mat"], ("z-",))   # ridge cap
        if v["dormers"]:                            # two dormers on the short front slope
            th = .16
            top_of = lambda o_: top + th + (-o_ - yF) * SALT_PITCH
            P = lambda o_, t, z: (t, -o_, z)
            for cx in (-1.7, 1.7):
                dormer(m, g, P, top_of, -(yF + 1.0), cx, 1.4, lod, v["wall"], v["roof_mat"], gtrim, rise=.6,
                       height=1.3, lites=v["lites"])
    elif mans:
        zt_ = top + MANS_RISE
        for xx, d in ((X, 1), (-X, -1)):            # the party walls rise into the mansard, 3 cm under the slab
            m.facing([(xx, yF, 0.0), (xx, yR, 0.0), (xx, yR, top - .03), (xx, yR - MANS_RUN, zt_ - .03),
                      (xx, yF + MANS_RUN, zt_ - .03), (xx, yF, top - .03)], (d, 0, 0), v["wall"])
        prof = [(yF - .35, top - .12), (yF, top), (yF + MANS_RUN, zt_), (yR - MANS_RUN, zt_), (yR, top),
                (yR + .35, top - .12)]
        slab(m, prof, -X + E, X - E, lambda a, q, z: (a, q, z), lod, v["roof_mat"], end=v["roof_mat"],
             what="mansard roof")
        th, k = .16, MANS_RISE / MANS_RUN
        fr = lambda o_: top + th + (-o_ - yF) * k            # front slope, o = -y
        rr = lambda o_: top + th + (yR - o_) * k             # rear slope, o = y
        for cx in (-2.3, 0.0, 2.3):
            dormer(m, g, lambda o_, t, z: (t, -o_, z), fr, -(yF + .25), cx, 1.2, lod, v["wall"], v["roof_mat"], gtrim,
                   rise=.5, height=1.4, lites=v["lites"])
        for cx in (-1.5, 1.5):
            dormer(m, g, lambda o_, t, z: (t, o_, z), rr, yR - .25, cx, 1.2, lod, v["wall"], v["roof_mat"], gtrim,
                   rise=.5, height=1.4, lites=v["lites"])
    else:
        party(m, (X, yF), (X, yR), 0.0, top, v["wall"])
        if not corner:
            party(m, (-X, yR), (-X, yF), 0.0, top, v["wall"])
    if gam:
        zk, ridge, knee = top + 3.3, top + 5.3, (top + 3.3, 1.0)
        gable_wall(m, g, (-X, yF), (X, yF), top, ridge, lod, gmat,
                   wins=[(-1.3, .8, top + .8, top + 2.15), (1.3, .8, top + .8, top + 2.15), (0.0, .7, top + 3.6, top + 4.5)],
                   trim=gtrim, shape=(zk, 1.0))
        gable_wall(m, g, (X, yR), (-X, yR), top, ridge, lod, gmat,
                   wins=[(1.3, .8, top + .8, top + 2.15), (0.0, .7, top + 3.6, top + 4.5)], trim=gtrim, shape=(zk, 1.0))
        # the ell meets a gambrel at its own eave: the main roof stops flush at the back wall instead of
        # overhanging into the ell roof (a low cape ell leaves the back gable free to overhang)
        flush = pieces and H["ell"] > top - .1
        gable_roof(m, -X, X, yF, yR, top, ridge, lod, v["roof_mat"], over=(.45, 0.0 if flush else .3), knee=knee)
    elif flat:
        stacked = front in ("triple", "quad", "baytriple")
        y0 = yF - 2.55 if stacked else yF - .6
        cornice_roof(m, XL, X, y0, yR + .3, top, lod, deep=.5, ends=None if corner else v["wall"],
                     brackets=() if stacked else (-3.4, -1.15, 1.15, 3.4))
    elif not (salt or mans):
        ridge = top + 4.3
        fw = [(xm - .8, .75, top + .9, top + 2.2)] if front == "turret" else \
             [(xm - .7, .7, top + .9, top + 2.15), (xm + .7, .7, top + .9, top + 2.15)]
        gable_wall(m, g, (XL, yF), (X, yF), top, ridge, lod, gmat, wins=fw, trim=gtrim)
        bw = [] if (pieces and H["ell"] > top - .1) else [(xm, .75, top + .9, top + 2.2)]   # a tall wing covers it
        gable_wall(m, g, (X, yR), (XL, yR), top, ridge, lod, gmat, wins=bw, trim=gtrim)
        flush = pieces and H["ell"] > top - .1        # a tall wing: the main roof stops flush at the back wall
        gable_roof(m, XL, X, yF, yR, top, ridge, lod, v["roof_mat"], over=(.45, 0.0 if flush else .3), sides=(lside, "p"))
        if v["dormers"] or corner:                  # a corner always dormers its street slope
            side_dormers(m, g, (X - XL) / 2, top, ridge, .16, [yF + 3.0, yF + 7.6], lod, v["wall"], v["roof_mat"],
                         gtrim, sides=(1, -1) if v["dormers"] else (-1,), xc=xm)

    # ---- the rear: the yard part full height with the back door, the rest above the ell (or all of it)
    rear_st = back if salt else main
    ydx = (BX + X) / 2                              # the back door, in the middle of the yard
    decks = []
    if pieces and v["decks"] and not salt and n >= 3:  # stacked rear decks over the yard (Toronto's backs)
        zfs = [3.88, 6.88, 9.88][:n - 1]
        decks = [(zf, zfs[k + 1] - .18 if k + 1 < len(zfs) else zf + 1.1) for k, zf in enumerate(zfs)]
    if pieces:
        wall(m, g, rear_st, (X, yR), (BX, yR), "-", "c", [ydx], lod, door=(ydx, 1.0, 2.95), trim=trim,
             waive={"balance": "the back door opens onto the yard walk"})
        if decks:
            rear_decks(m, BX + .1, X - E, yR, 1.8, decks, lod)
        if H["ell"] < rtop - .1:
            wall(m, g, rear_st, (BX, yR), (XL, yR), "-", sx, [], lod, z0=H["ell"], trim=trim)
    else:
        wall(m, g, rear_st, (X, yR), (XL, yR), "-", sx, [2.5, -.5], lod, door=(-.5, 1.0, 2.95), trim=trim,
             waive={"rhythm": "kitchen door and one window on the back wall"})
        wbox(m, -1.1, .1, yR + E, yR + .55, 0, .3, "StoneBase", ("z-", "y-"))

    # ---- the connected farm
    last = None
    for i, (pk, ya, yb) in enumerate(pieces):
        h = H[pk]
        prv = pieces[i - 1][0] if i else None
        ph = H[prv] if prv else rtop
        nxt = pieces[i + 1][0] if i + 1 < len(pieces) else None
        nh = H[nxt] if nxt else None
        if pk in ("ell", "back"):
            mat = v["wall"] if pk == "ell" else v["back_mat"]
            st = pstyle(h, mat)
            span = yb - ya
            k = max(1, round(span / 2.6))
            ys = [ya + span * (j + .5) / k for j in range(k)]
            if span / k - .9 > 2.25:                # rule 2 (at most 2.25 m blank): more bays, kept 1.1 m off the ends
                k = math.ceil((span - 2.2) / 3.15) + 1
                ys = [ya + 1.1 + (span - 2.2) * j / (k - 1) for j in range(k)]
            door = (ys[0], 1.0, 2.95) if pk == "ell" else (ys[-1], 1.0, 2.95)
            s = "c" if pk == "ell" else "-"
            wall(m, g, st, (BX, ya), (BX, yb), s, "x" if nxt is None else "c" if nxt == "barn" else "-", ys, lod,
                 door=door, trim=gtrim)
            if corner:                              # the side street: windows, the door stays on the yard
                wall(m, g, st, (XL, yb), (XL, ya), "x" if nxt is None else "-", "-", ys, lod, trim=gtrim)
            else:
                party(m, (XL, yb), (XL, ya), 0.0, h, mat)
            if prv and ph < h - .1:                 # this piece stands taller than the one in front: its front end
                wall(m, g, st, (XL, ya), (BX, ya), sx, "x", [], lod, z0=ph, trim=gtrim)
                gable_wall(m, g, (XL, ya), (BX, ya), h, h + 2.4, lod, mat, trim=gtrim)
            if nh is not None and nh < h - .1:      # ... or taller than the one behind: its rear end
                wall(m, g, st, (BX, yb), (XL, yb), "x", sx, [], lod, z0=nh, trim=gtrim)
                gable_wall(m, g, (BX, yb), (XL, yb), h, h + 2.4, lod, mat, trim=gtrim)
            # behind a saltbox the ell roof runs on under the long rear slope, so its front end is covered
            # (that run-on would lie flush with the saltbox gable on the party line, so it stands 12 mm off it)
            fwd = 3.0 if (salt and pk == "ell") else .25 if (prv and ph < h - .1) else -2 * E
            aft = .25 if (nxt is None or nh < h - .1) else -2 * E
            rise = 2.6 if h < 4.5 else 2.4
            if nxt == "barn" and not corner and h + rise > nh - .1:
                aft = 3.8                           # dies into the barn's front slope (a barn ridge runs across)
            gable_roof(m, XL + 3 * E if (fwd > 2 or aft > 2) else XL, BX, ya, yb, h, h + rise, lod, v["roof_mat"],
                       over=(fwd, aft), sides=(lside, "e"))
            if pk == "back":
                chimney(m, XL + 2.5, ya + .5, .35, .35, h + 1.5, h + 3.3, lod)
            last = (pk, ya, yb, mat)
        elif pk == "barn":
            bwin = [(.8, 1.6, 2.9)] if h < 4.5 else [(.8, 1.6, 2.9), (.9, 4.1, 5.5)]
            bst = style(h, [(0.0, h, v["barn_mat"])], bwin, belts=())
            # barn front shows over the side yard
            wall(m, g, bst, (BX, ya), (X, ya), "c", "-", [2.5], lod, door=(2.5, 1.2, 2.9), trim=gtrim,
                 waive={"balance": "barn door onto the yard"})
            if ph < h - .1:                         # over a lower ell: the barn front runs on across it
                wall(m, g, bst, (XL, ya), (BX, ya), sx, "-", [], lod, z0=ph, trim=gtrim)
            wall(m, g, bst, (X, yb), (XL, yb), "-", sx, [-2.5, 0.0, 2.5], lod, door=(0.0, 2.6, 3.4), trim=gtrim)
            if corner:                              # a carriage door and windows onto the side street
                party(m, (X, ya), (X, yb), 0.0, h, v["barn_mat"])
                L = yb - ya
                k = max(2, round(L / 2.6))
                bys = [ya + L * (j + .5) / k for j in range(k)]
                wall(m, g, bst, (XL, yb), (XL, ya), "x", "-", bys, lod, door=(bys[1], 2.2, 2.9), trim=gtrim,
                     waive={"balance": "carriage door onto the side street"})
                ridge_b = h + (4.8 if h < 4.5 else 3.6)
                gable_wall(m, g, (XL, ya), (X, ya), h, ridge_b, lod, v["barn_mat"], trim=gtrim)
                gable_wall(m, g, (X, yb), (XL, yb), h, ridge_b, lod, v["barn_mat"],
                           wins=[(xm, 1.0, h + .5, h + 1.9)], trim=gtrim)
                gable_roof(m, XL, X, ya, yb, h, ridge_b, lod, v["roof_mat"], over=(-2 * E, .3), sides=(lside, "p"))
            else:                                   # ridge across the lot: gables on the party lines, eaves front and back
                ym, pb, o = (ya + yb) / 2, .75, .35
                zr = h + (yb - ya) / 2 * pb
                for xx, d in ((X, 1), (-X, -1)):
                    m.facing([(xx, ya, 0.0), (xx, yb, 0.0), (xx, yb, h - .03), (xx, ym, zr - .03), (xx, ya, h - .03)],
                             (d, 0, 0), v["barn_mat"])
                slab(m, [(ya - o, h - o * pb), (ym, zr), (yb + o, h - o * pb)], -X + E, X - E,
                     lambda a, q, z: (a, q, z), lod, v["roof_mat"], end=v["roof_mat"], what="barn roof")
                if lod == 0:
                    wbox(m, -X + 3 * E, X - 3 * E, ym - .09, ym + .09, zr + .14, zr + .23, v["roof_mat"], ("z-",))
            last = ("barn", ya, yb, None)
    if last and last[0] in ("ell", "back"):
        _, ya, yb, mat = last
        h = H[last[0]]
        st = pstyle(h, mat)
        wall(m, g, st, (BX, yb), (XL, yb), "x", sx, [-.4, -2.4] if not corner else [-.2, -2.2], lod, trim=gtrim)
        gable_wall(m, g, (BX, yb), (XL, yb), h, h + (2.6 if h < 4.5 else 2.4), lod, mat,
                   wins=[((BX + XL) / 2, .6, h + .5, h + 1.5)], trim=gtrim)
    # ell front gable faces nothing (it butts the main house); a barn behind an ell hides the ell's rear

    # ---- the yard walk: back door -> along the ell (its door, the back house door) -> barn door
    if pieces:
        barn = next((p for p in pieces if p[0] == "barn"), None)
        yend = barn[1] - .06 if barn else 4.0 * D - .3
        xa, xs, xb, z = BX + .25, BX + 1.35, min(X - .3, ydx + .7), .05
        wbox(m, xa, xb, yR + .06, yR + 1.2, 0.0, z, "Paving", ("z-",))          # landing at the back door
        wbox(m, xa, xs, yR + 1.2 + E, (yend - 1.2 - E) if barn else yend, 0.0, z, "Paving", ("z-",))
        if barn:                                                                   # landing at the barn door
            wbox(m, xa, xb, yend - 1.2, yend, 0.0, z, "Paving", ("z-",))

    if salt:                                        # one big central chimney on the ridge, as on a first-period house
        chimney(m, 0.0, yr, .55, .45, zr - 1.0, zr + 1.3, lod)
    elif mans:
        chimney(m, X - .5, yF + DEPTH * .55, .35, .45, top + MANS_RISE - .1, top + MANS_RISE + 1.3, lod)
    else:
        chimney(m, X - .5, yF + DEPTH * .55, .35, .45, top - .1, top + (2.6 if gam else 1.9), lod)

    if v["hand"] == "R" and not corner:             # mirrored: the ell and yard swap sides
        for mm in (m, g):
            mm.v = [(-x, y, zz) for x, y, zz in mm.v]
            mm.f = [f[::-1] for f in mm.f]
    finish(m, g)
