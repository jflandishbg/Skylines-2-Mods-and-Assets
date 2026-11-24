"""Lobstertown "Prestige Cottages": Bar Harbor summer cottages, the Gilded Age Shingle Style palaces of Mount Desert
Island, on 2- and 3-wide lots 4 to 6 deep. the author 2026-11-15: palatial prestige homes for the Low zone, and the lot
filled to its rear line, Toronto big-house style. Nothing is left to props.

    build(lod, W=2, D=5, **variant)

The house stands back SET behind a lawn strip with a verandah across its front. Behind it a two-storey service wing
runs down one side (the kitchen and servants' wing) to a carriage house across the back of the lot, .6 m off the
rear line, round a paved service court. The house is detached: every wall has windows.

Variant keys:
  storeys  2 | 3
  roof     'gable' (side gable, ridge along the street) | 'gambrel' (side gambrel, steep lower slopes)
  turret   True | False: an octagonal tower at the front left corner
  cross    True | False: a front cross gable wing on the front right, projecting CROSS_P
  base     None | a material for a granite (or fieldstone) ground storey, as on many Bar Harbor cottages
  dormers  True | False: gable dormers on the front slope
  hand     'L' | 'R' (mirrored: tower right, wing on the right)
  wall, gable_mat, roof_mat, door, shutters, lites, wing_mat, car_mat
Back of the lot (the author 2026-11-15: the backs looked samey):
  car      'gable' (ridge across the lot) | 'gambrel' | 'cross' (gable across with a cross gable on its rear front)
  cupola   True | False: a louvred ventilator cupola on the carriage house ridge
  lofts    True | False: hay-loft dormers on the carriage house's rear slope (gable or cross roofs)
  car_base None | a stone for the carriage house's ground storey
  wing     'near' (service wing on the tower side) | 'far' (on the other side of the lot) | 'twin' (wings down
           both sides round a middle court; 4-wide lots only, narrower lots fall back to 'far')
Cottage Flats (Medium zone; the author 2026-11-15, "lean into" Boardwalk Empire's Atlantic City):
  flats    True: the wing and the carriage block rise to three storeys of flats, the court doors are flat entrances,
           and the verandah is an Atlantic City double-decker with the house's name board on its deck fascia
  sign     the name board's atlas key without 'Sign_' (TheVentnor, ...)
Grand Hotels (High zone; the author 2026-11-15, the brief "on steroids": Brazil's beachfront towers in Maine shingle):
  hotel    True: the main house becomes a shingle tower `storeys` high (any number above 4) over the flats' double-
           decker verandah, with a balcony on every floor above it, the turret running the full height under a tall
           cone, and a four-storey court block behind (wings and back range). Implies flats.
  lantern  True: a broad louvred lantern on the main ridge (the brief: "a lantern on the very top")
Château crowns (the author 2026-11-16, CHATEAU_PLAN.md; rule 11b: crown blocks under 150 m2 don't count as eaves):
  pavilions ((frac, k, cap), ...): 8 m square-fronted pavilions rising through the main roof, k storeys past the
           eave (raised until a window row clears the ridge), at frac 0..1 along the free front between the turret
           and the cross gable. cap 'hip' (steep pavilion roof), 'hipl' (with a lantern), 'dome' (drum, dome, lantern)
  spire    storeys the corner turret rises past the eave, under a needle cone
  Above the 10th storey the street front uses light windows at LOD0 (budget, option (a) of the plan).
"""
import math
from lt_kit import Mesh, chimney, finish, wall, style, gable_wall, gable_roof, porch, wbox, E, TRIM, roof_check
from lt_shapes import slab, dormer, turret, pavilion_roof, dome, cornice_roof
from lt_designs.shore_row import WINS, TOPS, BELTS, WIN2, WIN3, SIGN_W, SIGN_H

SET = 4.6                     # main front wall back from the lot front: a lawn strip, the verandah and its steps
SM = 1.2                      # side yards: the walls stand this far in from the side lot lines (eaves .35, rakes .3)
MAIN_D = {2: 12.0, 3: 13.0, 4: 14.0, 5: 15.0, 6: 16.0}   # main house depth by lot width
PITCH = .85                   # side-gable slopes
GAM_RUN, GAM_RISE, GAM_UP = 1.8, 2.7, .45    # gambrel: a steep lower slope (2.7 m up in 1.8 m, 56 deg), then .45
CROSS_W = {2: 5.6, 3: 7.2, 4: 8.8, 5: 9.6, 6: 10.4}  # the front cross gable wing
CROSS_P = 2.4                 # ... and how far it stands forward of the main front
TA = 1.4                      # turret apothem
WING_W = {2: 6.0, 3: 7.6, 4: 8.0, 5: 8.4, 6: 8.8}   # the service wing
WING_IN = .6                  # ... set in from the main side wall, so its eave stays inside the house line
WING_H = 6.7                  # two storeys, level with a two-storey main eave (no 20 cm step of frieze)
CAR_H, CAR_P = 6.7, .75       # the carriage house: eave, roof pitch (ridge across the lot)
VER_D = 2.6                   # verandah depth
DEFAULT = dict(storeys=2, roof="gable", turret=True, cross=False, base=None, dormers=True, hand="L",
               wall="ShingleSilver", gable_mat=None, roof_mat="SlateDark", door="Oxblood", shutters=None, lites="6",
               wing_mat=None, car_mat="ShingleGrey", car="gable", cupola=False, lofts=False, car_base=None, wing="near",
               flats=False, sign=None, hotel=False, lantern=False, pavilions=(), spire=0, corner=False)
BAL_D = 1.5                   # tower balconies: depth (inside the verandah's 2.6, so the verandah keeps the outline)
PICTURESQUE = {"balance": "Shingle Style cottage: picturesque and asymmetric on purpose (Lobstertown standing waiver, rule 3)"}


def spread(a, b, pier=1.1, step=3.1):
    """Evenly spaced window bays between a and b, the outer ones `pier` in from the ends, at most `step` apart
    (rule 2: at most 2.5 window widths of blank wall: 3.1 for .9 m windows, 2.75 for the carriage house's .8 m)."""
    L = b - a - 2 * pier
    if L < 1.6:
        return [(a + b) / 2]
    k = math.ceil(L / step)
    return [a + pier + L * j / k for j in range(k + 1)]


def nearest(bays, x):
    return min(bays, key=lambda c: abs(c - x))


def tall(n):
    """Window rows, eave and trim belts for an n-storey tower (Grand Hotels). Above the 4th floor every storey
    repeats the kit's 3.0 m upper floor-to-floor; a white belt marks every third floor (the brief)."""
    win = list(WINS[4]) + [(.9, 10.5 + 3.0 * (j - 3), 11.95 + 3.0 * (j - 3)) for j in range(4, n)]
    belts = (3.75,) + tuple(6.85 + 3.0 * (k - 2) for k in range(3, n, 3))
    return TOPS[4] + 3.0 * (n - 4), win, belts


def cupola(m, cx, cy, zr, lod, mat, roof_mat, louvre, a=.7, sink=.6, h=1.15):
    """A square louvred ventilator on a stable ridge at height zr: a box sunk into the ridge, louvre panels on
    its four faces, a white frieze, and a closed pyramid cap with a finial. sink: how far the box runs down into
    the roof (it must reach the slope at its sides); h: its height above the ridge."""
    z0, z1 = zr - sink, zr + h
    wbox(m, cx - a, cx + a, cy - a, cy + a, z0, z1 - .012, mat, ("z-",))
    if lod == 0:                                     # louvres and frieze: close view only (LOD1 budget)
        i, p = a - .16, .025
        for x0, x1, y0, y1 in ((cx - i, cx + i, cy - a - p, cy - a + .1), (cx - i, cx + i, cy + a - .1, cy + a + p),
                               (cx - a - p, cx - a + .1, cy - i, cy + i), (cx + a - .1, cx + a + p, cy - i, cy + i)):
            wbox(m, x0, x1, y0, y1, zr + .3, z1 - .2, louvre, ("z-",))
        wbox(m, cx - a - .04, cx + a + .04, cy - a - .04, cy + a + .04, z1 - .14, z1, TRIM, ("z-",))
    R, rise, zc = a + .22, max(1.0, a * 1.3), z1 + .01
    ring = [(cx - R, cy - R, zc), (cx + R, cy - R, zc), (cx + R, cy + R, zc), (cx - R, cy + R, zc)]
    apex = (cx, cy, zc + rise)
    t = Mesh()
    for k in range(4):
        p0, p1 = ring[k], ring[(k + 1) % 4]
        t.facing([p0, p1, apex], ((p0[0] + p1[0]) / 2 - cx, (p0[1] + p1[1]) / 2 - cy, .5), roof_mat)
    t.facing(ring, (0, 0, -1), TRIM)
    roof_check(m, t, f"cupola cap at x {cx:.2f}")
    if lod < 2:
        wbox(m, cx - .05, cx + .05, cy - .05, cy + .05, zc + rise - .3, zc + rise + .6, TRIM, ("z-",))


def build(lod, W=2, D=5, **variant):
    variant.pop("lots", None)
    v = dict(DEFAULT, **variant)
    hotel = v["hotel"]
    corner = v["corner"]
    if corner:
        v["sign"] = None
        v["wing"] = "twin" if hotel else "near"
        v["hand"] = "L"
    flats = v["flats"] or hotel
    WH = CH = TOPS[4] if hotel else TOPS[3] if flats else WING_H   # flats: 3-storey back blocks; hotels: 4
    ta = 2.0 if hotel else TA                        # the hotel tower's turret is broader
    if v["wing"] == "twin" and W < 4:
        v["wing"] = "far"
    n, gam = v["storeys"], v["roof"] == "gambrel"
    if hotel:
        n += 2 * (W - 4)                             # each extra cell of width adds two storeys
    top, win, belts = tall(n) if n > 4 else (TOPS[n], WINS[n], BELTS[n])
    XH = 4.0 * W - SM
    XL = (-4.0 * W + 3.6) if corner else -XH
    MD = MAIN_D[W]
    yF = -4.0 * D + (3.80 if hotel else SET)
    yR = yF + MD
    end = 4.0 * D - .6
    ym = (yF + yR) / 2
    trim = dict(door=v["door"], shutters=v["shutters"], lites=v["lites"],
                lean="bare" if flats else True)   # lean: flat LOD1 windows; bare: no casings either (budget)
    if hotel and lod == 0 and n > 10:                # the château budget: light windows above the 10th storey
        trim["lite_above"] = win[10][1] - .05
    strim = dict(trim, simple=True) if flats else trim
    if hotel:                                        # sides and rear: light windows all the way down (budget)
        strim["lite_above"] = -1   # flats: one-over-one sashes off the street front (budget)
    gtrim = dict(trim, shutters=None)
    gmat = v["gable_mat"] or v["wall"]
    mats = [(0.0, 3.75, v["base"]), (3.75, top, v["wall"])] if v["base"] else [(0.0, top, v["wall"])]
    main = style(top, mats, win, belts=belts)
    m, g = Mesh(), Mesh()

    # ---- the main roof profile (front eave to rear eave) and its gable outline
    o = .35
    if gam:
        k1 = GAM_RISE / GAM_RUN
        zk = top + GAM_RISE
        zr = zk + (MD / 2 - GAM_RUN) * GAM_UP
        prof = [(yF - o, top - o * k1), (yF + GAM_RUN, zk), (ym, zr), (yR - GAM_RUN, zk), (yR + o, top - o * k1)]
        shape = (zk, GAM_RUN)
        front_top = lambda q: top + min(q - yF, GAM_RUN) * k1 + max(0.0, q - yF - GAM_RUN) * GAM_UP   # roof at y = q
        rear_slope = k1
    else:
        zr = top + MD / 2 * PITCH
        prof = [(yF - o, top - o * PITCH), (ym, zr), (yR + o, top - o * PITCH)]
        shape = None
        front_top = lambda q: top + (q - yF) * PITCH
        rear_slope = PITCH

    # ---- the street front: tower, verandah, cross gable
    cross, tower = v["cross"], v["turret"]
    CW = CROSS_W[W]
    x0 = XH - CW if cross else XH                    # the main front wall runs from XL to x0
    xa = (XL + (ta if corner else 2 * ta) + .02) if tower else XL         # windows start clear of the tower
    bays = spread(xa, x0, pier=1.25)
    vx0 = (XL + (.6 if corner else ta + .62)) if tower else XL + E       # the verandah: from inside the tower (no slit at its chamfer) to the cross gable
    vx1 = (x0 - .08) if cross else XH - E           # clear of the cross wing's trim belt
    dx = nearest(bays, (vx0 + vx1) / 2)
    pav = []                                         # château pavilions through the main roof: (x0, x1, k, cap)
    plo, phi = (XL + 2 * ta + 2.0) if tower else XL + 1.0, (x0 - 2.0) if cross else XH - 1.0   # roof shows between: blocks apart (rule 11b)
    PW = min(8.0, 146.0 / (yR - yF + .6) - .6)       # roof plan (PW+.6) x (depth+.6) under 150 m2: a crown (rule 11b)
    if hotel and phi - plo >= PW:
        for frac, k, cap in sorted(v["pavilions"], key=lambda q: -q[1]):
            c = plo + PW / 2 + frac * (phi - plo - PW)
            if all(c + PW / 2 + 1.0 <= q0 or c - PW / 2 - 1.0 >= q1 for q0, q1, _, _ in pav):
                while top + 3.0 * k < zr + 1.0 or not any(top + .6 + 3.0 * j >= zr + .25 and top + 2.25 + 3.0 * j <= top + 3.0 * k
                              for j in range(k)):
                    k += 1
                pav.append((c - PW / 2, c + PW / 2, k, cap))
    in_pav = lambda x, pad=0.0: any(q0 - pad <= x <= q1 + pad for q0, q1, _, _ in pav)
    stair = (dx - .7, dx + .7)
    waive = dict(PICTURESQUE)
    if tower:
        waive["glass"] = "the corner tower carries the glass of its bay"
    wall(m, g, main, (XL, yF), (x0, yF), "x", "c" if cross else "x", bays, lod, door=(dx, 1.1, 2.95), trim=trim,
         waive=waive, plinth_cuts=[stair])
    posts = [vx0 + .15 + (vx1 - vx0 - .3) * j / max(1, math.ceil((vx1 - vx0 - .3) / 3.2))
             for j in range(max(1, math.ceil((vx1 - vx0 - .3) / 3.2)) + 1)]
    if lod == 2:                                     # far view: the end posts carry the outline (LOD2 budget)
        posts = [posts[0], posts[-1]]
    vsides = ("r",) if tower and not cross else ("l",) if cross and not tower else () if tower else ("l", "r")
    if flats:                                        # Atlantic City double-decker: an open upper deck, its own roof
        porch(m, vx0, vx1, yF, VER_D, lod, zt=3.7, stair=stair, roof=False, posts=posts, open_sides=vsides)
        porch(m, vx0, vx1, yF, VER_D, lod, zf=3.88, zt=6.3, mat=v["roof_mat"], posts=posts, open_sides=vsides)
        if v["sign"]:                                # the name board on the deck fascia, on the atlas tile grid
            yf = yF - VER_D
            sx = SIGN_W * round((dx - SIGN_W / 2) / SIGN_W)
            sx = min(max(sx, SIGN_W * math.ceil((vx0 + .2) / SIGN_W)), SIGN_W * math.floor((vx1 - .2) / SIGN_W) - SIGN_W)
            z0 = 6 * SIGN_H                          # 3.48-4.06
            wbox(m, sx - .04, sx + SIGN_W + .04, yf - .03, yf - .004, z0 - .03, z0 + SIGN_H + .03, TRIM, ("y+",))
            ys = yf - .035
            m.facing([(sx, ys, z0), (sx + SIGN_W, ys, z0), (sx + SIGN_W, ys, z0 + SIGN_H), (sx, ys, z0 + SIGN_H)],
                     (0, -1, 0), "Sign_" + v["sign"])
    else:
        porch(m, vx0, vx1, yF, VER_D, lod, stair=stair, mat=v["roof_mat"], posts=posts, open_sides=vsides)
    if hotel:                                        # a balcony on every floor above the verandah roof ("porches
        bx0 = (XL + 2 * ta + .08) if tower else XL + .6   # become balconies on every floor", the brief)
        bx1 = (x0 - .3) if cross else XH - .6       # clear of the side outlines: the verandah keeps the eave line
        yb = yF - BAL_D
        zs = [win[j][1] - .62 for j in range(3, n)]
        pb = [bx0 + .12, bx1 - .12] + [(a + b) / 2 for a, b in zip(bays, bays[1:]) if bx0 + .4 < (a + b) / 2 < bx1 - .4]
        for k, zf in enumerate(zs):
            wbox(m, bx0, bx1, yb, yF - E, zf - .14, zf, "Deck", ("y+",))                      # the deck
            if lod == 2:
                continue
            wbox(m, bx0 + E, bx1 - E, yb + .01, yb + .09, zf + E, zf + .92, v["wall"], ("y+", "z-"))  # shingled apron
            if lod == 0:
                wbox(m, bx0 - .02, bx1 + .02, yb - .02, yb + .12, zf + .92 + E, zf + 1.0, TRIM, ("z-",))  # its rail cap
            if k + 1 < len(zs):                      # posts up to the deck above (the top balcony is open)
                for px in (pb if lod == 0 else pb[:2]):
                    wbox(m, px - .09, px + .09, yb + .16, yb + .34, zf + E, zs[k + 1] - .14 - E, TRIM, ("z-", "z+"))
    if tower:
        ks = v["spire"] if hotel else 0
        z1 = top + 3.0 * ks
        if corner:
            from lt_designs.mainst import tower as oct_tower
            trows = [(a, b, (0, 1, 5, 6, 7)) for _, a, b in win] + \
                    [(top + .6 + 3.0 * j, top + 2.05 + 3.0 * j, tuple(range(8))) for j in range(ks)]
            oct_tower(m, g, lod, XL, yF, ta, 8, 0.0, z1, (11.0 if ks else 7.5) if hotel else 4.6, v["wall"],
                      v["roof_mat"], gtrim, trows, TRIM)
        else:
            tc = XL + ta + .02
            turret(m, g, tc, yF, ta, 0.0, z1, (11.0 if ks else 7.5) if hotel else 4.6, lod, v["wall"],
                   [(a, b) for _, a, b in win] + [(top + .6 + 3.0 * j, top + 2.05 + 3.0 * j) for j in range(ks)], gtrim,
                   v["roof_mat"], belts=belts, lites=v["lites"])
            if ks:                                       # its back, where it rises clear of the roof (rule 13)
                m.facing([(tc + ta, yF + .02, top), (tc - ta, yF + .02, top), (tc - ta, yF + .02, z1),
                          (tc + ta, yF + .02, z1)], (0, 1, 0), v["wall"])
    yS = yF                                          # where the right side wall starts
    if cross:
        yc = yF - CROSS_P
        yS = yc
        cb = spread(x0, XH, pier=1.2)
        wall(m, g, main, (x0, yc), (XH, yc), "x", "x", cb, lod, trim=trim,
             waive={"balance": "the cross gable wing: two bays under its own gable"})
        wall(m, g, main, (x0, yF), (x0, yc), "c", "x", [yF - CROSS_P / 2], lod, trim=trim)
        zrc = top + CW / 2 * .9
        gable_wall(m, g, (x0, yc), (XH, yc), top, zrc, lod, gmat, wins=[((x0 + XH) / 2, .8, top + .8, top + 2.2)],
                   trim=gtrim)
        aft = (zrc + .16 - top) / (k1 if gam else PITCH) + .5      # runs back into the main front slope
        gable_roof(m, x0, XH, yc, yF, top, zrc, lod, v["roof_mat"], over=(.5, aft), sides=("e", "e"))

    # ---- the main house: side walls, gables, roof, dormers, chimneys
    sb = spread(yF + (ta + .8 if corner and tower else 0.0), yR)
    if corner:
        sdx = nearest(sb, (yF + yR) / 2)
        wall(m, g, main, (XL, yR), (XL, yF), "x", "x", sb, lod, door=(sdx, 1.1, 2.95), trim=strim,
             waive=dict(PICTURESQUE, corners="corner turret anchors the side-street intersection",
                        glass="the corner turret carries the glass of its bay"))
        from lt_designs.boardwalk import _side_porch
        sy0 = (yF + .6) if tower else (yF + E)
        sy1 = yR - E
        sspan = sy1 - sy0 - .3
        sposts = [sy0 + .15 + sspan * j / max(1, math.ceil(sspan / 3.2))
                  for j in range(max(1, math.ceil(sspan / 3.2)) + 1)]
        if lod == 2:
            sposts = [sposts[0], sposts[-1]]
        _side_porch(m, XL, sy0, sy1, VER_D, lod, zf=.79, zt=3.7, posts=sposts, roof=False, rail=True)
        _side_porch(m, XL, sy0, sy1, VER_D, lod, zf=3.88, zt=6.3, posts=sposts, mat=v["roof_mat"], roof=True, rail=True)
    else:
        wall(m, g, main, (XL, yR), (XL, yF), "x", "x", sb, lod, trim=strim)
    wall(m, g, main, (XH, yS), (XH, yR), "x", "x", spread(yS, yR), lod, trim=strim)
    gw = [(ym, .8, top + .9, top + 2.3)]
    gable_wall(m, g, (XL, yR), (XL, yF), top, zr, lod, gmat, wins=gw, trim=gtrim, shape=shape)
    gable_wall(m, g, (XH, yF), (XH, yR), top, zr, lod, gmat, wins=gw, trim=gtrim, shape=shape)
    segs, s0 = [], XL - .3                           # the main roof, cut round the pavilions
    for q0, q1, _, _ in sorted(pav):
        segs.append((s0, q0 - .012))
        s0 = q1 + .012
    segs.append((s0, XH + .3))
    for a0, a1 in segs:
        slab(m, prof, a0, a1, lambda a, q, z: (a, q, z), lod, v["roof_mat"], end=v["roof_mat"], what="main roof")
        if lod == 0:
            wbox(m, a0 + 3 * E, a1 - 3 * E, ym - .09, ym + .09, zr + .14, zr + .23, v["roof_mat"], ("z-",))
    for q0, q1, k, cap in pav:
        _pavilion(m, g, lod, v, q0, q1, yF, yR, top, k, cap, trim, strim)
    if v["dormers"]:
        th = .16
        top_of = lambda o_: front_top(-o_) + th
        lo, hi = (xa + .6, (x0 if cross else XH) - 1.2)
        k = max(1, int((hi - lo) / 3.2))
        for j in range(k):
            cx = lo + (hi - lo) * (j + .5) / k
            if in_pav(cx, 1.0):
                continue
            dormer(m, g, lambda o_, t, z: (t, -o_, z), top_of, -(yF + (.25 if gam else 1.0)), cx, 1.4, lod,
                   gmat, v["roof_mat"], gtrim, rise=.55, height=1.35, lites=v["lites"])
    for cx in (XL + 1.9, XH - 1.9):                  # a pair of tall chimneys astride the ridge
        if not in_pav(cx, .8):
            chimney(m, cx, ym, .7, .55, zr - 1.2, zr + 1.9, lod)
    if v["lantern"] and not in_pav(0.0, 1.8):                                 # sunk until it meets the slope at its sides
        la = 1.4
        cupola(m, 0.0, ym, zr + .16, lod, v["wall"], v["roof_mat"], v["shutters"] or v["door"], a=la,
               sink=la * (GAM_UP if gam else PITCH) + .3, h=2.2)

    # ---- the service wing and the carriage house, round a paved service court
    # Laid out with the wing on the tower side (x from XL); a 'far' wing builds the same plan mirrored in x, natively,
    # through these wrappers: every wall keeps its outward normal and its corner handing (mirroring finished
    # geometry instead swaps which wall's corner boards and bands win at each corner, and they collide).
    fx = -1 if v["wing"] == "far" else 1

    def bwall(st, A, B, s, e, bays, door=None, **kw):
        if fx == 1:
            return wall(m, g, st, A, B, s, e, bays, lod, door=door, **kw)
        along_x = abs(A[1] - B[1]) < 1e-9
        bb = [-c for c in bays] if along_x else list(bays)
        dd = None if door is None else ((-door[0] if along_x else door[0]),) + tuple(door[1:])
        return wall(m, g, st, (-B[0], B[1]), (-A[0], A[1]), e, s, bb, lod, door=dd, **kw)

    def bgable(A, B, z0, zr_, mat, wins=(), **kw):
        if fx == -1:
            along_x = abs(A[1] - B[1]) < 1e-9
            A, B = (-B[0], B[1]), (-A[0], A[1])
            wins = [((-c if along_x else c),) + tuple(r) for c, *r in wins]
        gable_wall(m, g, A, B, z0, zr_, lod, mat, wins=wins, **kw)

    def broof(x0, x1, *a, sides=("e", "e"), **kw):
        if fx == -1:
            x0, x1, sides = -x1, -x0, sides[::-1]
        gable_roof(m, x0, x1, *a, sides=sides, **kw)

    def bbox(x0, x1, *a):
        wbox(m, *((x0, x1) if fx == 1 else (-x1, -x0)), *a)

    twin = v["wing"] == "twin"
    ww = {4: 8.6, 5: 10.0, 6: 11.4}.get(W, WING_W[W]) if (corner and hotel) else WING_W[W]
    wa, wb = XL + WING_IN, XL + WING_IN + ww
    rwa, rwb = XH - WING_IN - ww, XH - WING_IN
    gw = {"balance": "the garden door opens onto the service court"}
    if twin:                                         # wings down both sides, the garden door on the middle court
        ydx = nearest(spread(wb, rwa), (wb + rwa) / 2)
        wall(m, g, main, (XH, yR), (rwb, yR), "x", "c", [], lod, trim=strim)
        wall(m, g, main, (rwa, yR), (wb, yR), "c", "c", spread(wb, rwa), lod, door=(ydx, 1.0, 2.95), trim=strim, waive=gw)
        wall(m, g, main, (wa, yR), (XL, yR), "c", "x", [], lod, trim=strim)
        if top > WH + .2:
            ubl = spread(wa, wb, pier=1.2) if hotel else []
            ubr = spread(rwa, rwb, pier=1.2) if hotel else []
            wall(m, g, main, (rwb, yR), (rwa, yR), "-", "-", ubr, lod, z0=WH, trim=strim)
            wall(m, g, main, (wb, yR), (wa, yR), "-", "-", ubl, lod, z0=WH, trim=strim)
    else:
        ydx = nearest(spread(wb, XH), (wb + XH) / 2)    # the garden door
        bwall(main, (XH, yR), (wb, yR), "x", "c", spread(wb, XH), door=(ydx, 1.0, 2.95), trim=strim, waive=gw)
        if top > WH + .2:                            # the main rear wall above the wing roof
            bwall(main, (wb, yR), (wa, yR), "-", "-", spread(wa, wb, pier=1.2) if hotel else [], z0=WH, trim=strim)
        bwall(main, (wa, yR), (XL, yR), "c", "x", [], trim=strim)
    zw = WH + ww / 2 * (.65 if (corner and hotel) else .8)   # the service wing's ridge
    room = end - yR
    CD = 8.0 if room < 20 else (11.5 if (corner and hotel) else 9.5)
    yC = end - CD
    yk = (yC + end) / 2
    o_c = .32 if hotel else o                        # keep carriage rear overhang off the 0.25+0.5n ray centre (19.75)
    if v["car"] == "gambrel":
        ck = GAM_RISE / GAM_RUN
        czk = CH + GAM_RISE
        zc = czk + (CD / 2 - GAM_RUN) * GAM_UP
        cprof = [(yC - o, CH - o * ck), (yC + GAM_RUN, czk), (yk, zc), (end - GAM_RUN, czk), (end + o_c, CH - o_c * ck)]
        cshape = (czk, GAM_RUN)
        car_in = lambda z: (z - CH) / ck if z <= czk else GAM_RUN + (z - czk) / GAM_UP   # in from an eave to height z
    else:
        cp = max(CAR_P, (zw + .5 - CH) / (CD / 2))   # steep enough that the wing roof dies into its slope
        zc = CH + CD / 2 * cp
        cprof = [(yC - o, CH - o * cp), (yk, zc), (end + o_c, CH - o_c * cp)]
        cshape = None
        car_in = lambda z: (z - CH) / cp
    wmat = v["wing_mat"] or v["wall"]
    if flats:                                        # the flats blocks: wide plain one-over-one windows (budget)
        BW = WINS[4] if hotel else [(1.05, a, b) for _, a, b in WIN3]   # (1.05 m x 4 rows breaks rule 4)
        BB = BELTS[4] if hotel else BELTS[3]
        wst = style(WH, [(0.0, WH, wmat)], BW, belts=BB)
        gtrim = dict(gtrim, simple=True, **({"lite_above": -1} if hotel else {}))   # hotel court: light windows
        bstep, bpier = (3.1, 1.1) if hotel else (3.6, 1.2)   # rule 1: .6 x 1.05 m of wall beside the corner bays
    else:
        wst = style(WH, [(0.0, WH, wmat)], WIN2, belts=(3.75,))
        bstep, bpier = 3.1, 1.1
    span = yC - yR
    ys = spread(yR, yC, pier=bpier, step=bstep)
    fwd = -2 * E if zw < top - .1 else (zw + .16 - top) / rear_slope + .5   # under a low main roof it runs on in
    aft = car_in(zw + .16) + .5                                             # and into the carriage house roof
    assert aft < CD / 2 + .3, f"service wing roof would run through the carriage house ridge ({aft:.2f} m)"
    kw = {"balance": "the flats entrance opens onto the court" if flats else "the kitchen door opens onto the service court"}
    if twin:
        wall(m, g, wst, (wb, yR), (wb, yC), "c", "c", ys, lod, door=(ys[0], 1.0, 2.95), trim=gtrim, waive=kw)
        wall(m, g, wst, (wa, yC), (wa, yR), "c", "c", ys, lod, trim=gtrim)
        gable_roof(m, wa, wb, yR, yC, WH, zw, lod, v["roof_mat"], over=(fwd, aft), sides=("e", "e"))
        wall(m, g, wst, (rwa, yC), (rwa, yR), "c", "c", ys, lod, door=(ys[0], 1.0, 2.95), trim=gtrim, waive=kw)
        wall(m, g, wst, (rwb, yR), (rwb, yC), "c", "c", ys, lod, trim=gtrim)
        gable_roof(m, rwa, rwb, yR, yC, WH, zw, lod, v["roof_mat"], over=(fwd, aft), sides=("e", "e"))
        if lod < 2:
            chimney(m, (wa + wb) / 2, yR + span * .6, .45, .45, zw - .8, zw + 1.3, lod)
            chimney(m, (rwa + rwb) / 2, yR + span * .6, .45, .45, zw - .8, zw + 1.3, lod)
    else:
        bwall(wst, (wb, yR), (wb, yC), "c", "c", ys, door=(ys[0], 1.0, 2.95), trim=gtrim, waive=kw)
        bwall(wst, (wa, yC), (wa, yR), "c", "c", ys, trim=gtrim)
        broof(wa, wb, yR, yC, WH, zw, lod, v["roof_mat"], over=(fwd, aft))
        if lod < 2:                              # (LOD2 budget: the wing stacks go)
            chimney(m, fx * (wa + wb) / 2, yR + span * .6, .45, .45, zw - .8, zw + 1.3, lod)

    cmat = v["car_mat"]
    cmats = [(0.0, 3.75, v["car_base"]), (3.75, CH, cmat)] if v["car_base"] else [(0.0, CH, cmat)]
    if flats:                                        # three storeys of flats over the court
        cst = style(CH, cmats, BW, belts=BB)
        cstep, cdoor = bstep, (1.1, 2.95)
    else:
        cst = style(CH, cmats, [(.8, 1.6, 2.9), (.9, 4.1, 5.5)], belts=(3.75,) if v["car_base"] else ())
        cstep, cdoor = 2.75, (2.2, 2.9)
    cwv = {"balance": "the flats entrance opens onto the court" if flats else "carriage doors onto the service court"}
    if twin:
        cb = spread(wb, rwa, pier=bpier, step=cstep)
        cdx = nearest(cb, (wb + rwa) / 2)
        wall(m, g, cst, (wb, yC), (rwa, yC), "c", "c", cb, lod, door=(cdx,) + cdoor, trim=gtrim, waive=cwv)
        wall(m, g, cst, (XL, yC), (wa, yC), "x", "c", [], lod, trim=gtrim)
        wall(m, g, cst, (rwb, yC), (XH, yC), "c", "x", [], lod, trim=gtrim)
    else:
        cb = spread(wb, XH, pier=bpier, step=cstep)
        cdx = nearest(cb, (wb + XH) / 2)
        bwall(cst, (wb, yC), (XH, yC), "c", "x", cb, door=(cdx,) + cdoor, trim=gtrim, waive=cwv)
        bwall(cst, (XL, yC), (wa, yC), "x", "c", [], trim=gtrim)
    sbc = spread(yC, end, pier=bpier, step=cstep)
    bwall(cst, (XL, end), (XL, yC), "x", "x", sbc, trim=gtrim)
    bwall(cst, (XH, yC), (XH, end), "x", "x", sbc, trim=gtrim)
    rb = spread(XL, XH, pier=bpier, step=cstep)
    bwall(cst, (XH, end), (XL, end), "x", "x", rb, trim=gtrim)
    gwc = [(yk, .8, CH + .6, CH + 1.9)]
    bgable((XL, end), (XL, yC), CH, zc, cmat, wins=gwc, trim=gtrim, shape=cshape)
    bgable((XH, yC), (XH, end), CH, zc, cmat, wins=gwc, trim=gtrim, shape=cshape)
    slab(m, cprof, XL - .3, XH + .3, lambda a, q, z: (a, q, z), lod, v["roof_mat"], end=v["roof_mat"],
         what="carriage house roof")
    if lod == 0:
        wbox(m, XL - .3 + 3 * E, XH + .3 - 3 * E, yk - .09, yk + .09, zc + .14, zc + .23, v["roof_mat"], ("z-",))
    xg = nearest(rb, (XL + XH) / 2)                  # the rear front's middle bay
    if v["car"] == "cross":                          # a flush cross gable over the middle bay, with a loft window
        cw = 4.4
        zg = CH + cw / 2 * .9
        bgable((xg + cw / 2, end), (xg - cw / 2, end), CH, zg, cmat, wins=[(xg, .8, CH + .5, CH + 1.45)],
               trim=gtrim)
        broof(xg - cw / 2, xg + cw / 2, end, end, CH, zg, lod, v["roof_mat"], over=(car_in(zg + .16) + .5, .4))
    if v["lofts"] and v["car"] != "gambrel" and lod == 0:   # hay-loft dormers on the rear slope (close view only: LOD1 budget)
        picks = [rb[1], rb[-2]] if W == 2 else [rb[1], rb[len(rb) // 2], rb[-2]]
        if v["car"] == "cross":
            picks = [c for c in picks if abs(c - xg) > 3.2]
        top_of = lambda o_: CH + (end - o_) * cp + .16
        for cx in picks:
            dormer(m, g, lambda o_, t, z: (t, o_, z), top_of, end - .9, fx * cx, 1.3, lod, cmat, v["roof_mat"], gtrim,
                   rise=.45, height=1.2, lites=v["lites"])
    if v["cupola"]:
        cupola(m, (XL + XH) / 2, yk, zc + .16, lod, cmat, v["roof_mat"], v["shutters"] or v["door"])

    # the service court walk: along the left wing edge on twin courts so the central court stays wide open for planting!
    if lod < 2 and twin:
        za = .05
        xs = wb + 1.25
        wbox(m, wb + .15, xs, yR + .06, yC - .06, 0.0, za, "Paving", ("z-",))
        if ydx > xs + .1:
            wbox(m, xs + E, ydx + .75, yR + .06, yR + 1.15, 0.0, za, "Paving", ("z-",))
        if cdx > xs + .1:
            wbox(m, xs + E, cdx + 1.25, yC - 1.25, yC - .06, 0.0, za, "Paving", ("z-",))
    elif lod < 2:
        za = .05
        xs = wb + 1.35
        bbox(wb + .25, ydx + .8, yR + .06, yR + 1.2, 0.0, za, "Paving", ("z-",))
        bbox(wb + .25, xs, yR + 1.2 + E, yC - 1.4 - E, 0.0, za, "Paving", ("z-",))
        bbox(wb + .25, cdx + 1.5, yC - 1.4, yC - .06, 0.0, za, "Paving", ("z-",))

    if v["hand"] == "R":                             # mirrored: tower and wing on the right
        for mm in (m, g):
            mm.v = [(-x, y, zz) for x, y, zz in mm.v]
            mm.f = [f[::-1] for f in mm.f]
    finish(m, g)


def _pavilion(m, g, lod, v, x0, x1, yF, yR, top, k, cap, trim, strim):
    """A château pavilion: a block (8 m at most, under 150 m2 with its eaves) the depth of the main house, rising through its roof k storeys past the
    eave, its front in the street wall, then a steep pavilion roof (lantern optional) or a drum and dome."""
    zP = top + 3.0 * k
    rows = [(.9, top + .6 + 3.0 * j, top + 2.05 + 3.0 * j) for j in range(k)]
    st = style(zP, [(top, zP, v["wall"])], rows, belts=(), plinth=None)
    fb = spread(x0, x1, pier=1.25)
    wall(m, g, st, (x0, yF), (x1, yF), "x", "x", fb, lod, z0=top, trim=trim, waive=dict(PICTURESQUE))
    wall(m, g, st, (x1, yF), (x1, yR), "x", "x", spread(yF, yR), lod, z0=top, trim=strim)
    wall(m, g, st, (x1, yR), (x0, yR), "x", "x", spread(x0, x1, pier=1.2), lod, z0=top, trim=strim)
    wall(m, g, st, (x0, yR), (x0, yF), "x", "x", spread(yF, yR), lod, z0=top, trim=strim)
    cx, ym = (x0 + x1) / 2, (yF + yR) / 2
    if cap in ("hip", "hipl"):
        half = (x1 - x0) / 2 + .3
        rise = 1.45 * half
        zr = pavilion_roof(m, x0 - .3, x1 + .3, yF - .3, yR + .3, zP, rise, lod, v["roof_mat"], finial=cap == "hip")
        if cap == "hipl":
            la = 1.2
            cupola(m, cx, ym, zr + .1, lod, v["wall"], v["roof_mat"], v["shutters"] or v["door"], a=la,
                   sink=la * 1.45 + .3, h=1.9)
    else:
        cornice_roof(m, x0 - .2, x1 + .2, yF - .2, yR + .2, zP, lod, deep=.45, ends=TRIM)
        zc = dome(m, g, cx, ym, (x1 - x0) / 2 - .9, zP + .45, lod, v["roof_mat"], v["wall"])
        cupola(m, cx, ym, zc + .02, lod, v["wall"], v["roof_mat"], v["shutters"] or v["door"], a=.8, sink=.05,
               h=1.5)
