"""Lobstertown Hydrostone Courts (ZR1, Maritime Boom 1918-1930): Coastal Low-Rent Housing.

Inspired by Halifax's 1918 Hydrostone District (crushed-stone concrete block garden-court walk-ups built after the
Halifax Explosion) and 1920s Portland garden-court apartments. Strict coastal palette (rule 20: crushed-stone
Greystone, Dressed stone, Cream, weathered Silver shingle; dark slate, green slate & blue-grey slate roofs -- zero
TinOxide/red roofs). Every design has its own distinct footprint at EVERY lot size (W=2, 3, 4: U-rear, deep U-rear,
U-front / L-front-right, L-front-left, H / C-right, T / L-right, L-left, C-left) so no two designs share a 0.5 m
occupancy footprint (rule 21).

    build(lod, W=3, D=4, **variant)      free-standing garden-court apartments (18-46 hh) on 2x3..4x5 lots

Variant keys:
  storeys   3 | 4 (3.7 m ground storey + 3.0 m upper flat storeys)
  plan      'U_rear' | 'U_front' | 'U_front_L' | 'H' | 'T' | 'L_left' | 'C_left'
  depth_f   main-bar depth fraction (0.24..0.58)
  court_f   court width fraction (0.20..0.44)
  roof      'hip' | 'gable' | 'flat'
  upper     material of top storey ('Cream', 'Dressed', 'Greystone', 'ShingleSilver')
  roof_mat  'SlateDark' | 'SlateGreen' | 'Slate'
  door      'Green' | 'Oxblood' | 'Black' | 'GreyBlue'
  dormers   True | False
  corner    False | True (LeftCorner, no lettering)
"""
import math
from lt_kit import Mesh, Wall, chimney, finish, wall, style, gable_wall, wbox, lbox, holes_for, E, TRIM
from lt_shapes import slab, dormer, pavilion_roof, cornice_roof
from lt_designs.cottage import nearest
from lt_designs.civic import rough as stone_coursing

SET = 1.0                     # front wall 1.00 m inside lot front (Rule 29; eave 0.32 -> front_m = 0.62..0.68 m)
SM = 1.0                      # side yards
G = 3.7                       # ground storey
F = 3.0                       # upper flat storey
STONE = "Greystone"           # Hydrostone crushed-stone block
DRESSED = "Dressed"           # stone lintels, sills, belt course, quoins
PITCH = .58                   # Hydrostone gable/hip pitch
DEFAULT = dict(storeys=3, plan="U_rear", depth_f=.46, court_f=.30, roof="gable", upper="Cream",
               roof_mat="SlateDark", door="Green", lites="6", dormers=True, corner=False)
HYDRO_W = {"balance": "Hydrostone garden-court rhythmic facade", "corners": "stone-quoin Hydrostone corner bay"}


def _h_floors(n):
    wins = [(1.15, .95, 2.85)] + [(1.0, G + F * (j - 1) + .80, G + F * (j - 1) + 2.35) for j in range(1, n)]
    return wins, G + F * (n - 1)


def _quoins(m, A, B, z0, z1, lod):
    if lod != 0:
        return
    w = Wall(A, B)
    z, k = z0 + .12, 0
    while z + .38 < z1 - .45:
        wq = .52 if k % 2 == 0 else .32
        for a0, a1 in ((0.0, wq), (w.L - wq, w.L)):
            lbox(m, w, a0 + E, a1 - E, z, z + .35, E, .04, DRESSED)
        z += .40
        k += 1


def _bays(a, b, pier=1.45, step=3.2, min_p=2.05):
    """Evenly spaced window bays with pitch strictly in [min_p, 3.40] (Rule 2 safe for 1.00..1.15 m windows)."""
    L = b - a
    if L < 2 * 1.10 + min_p:
        return [(a + b) / 2]
    for k in range(1, 30):
        for p in (pier, 1.35, 1.55, 1.25, 1.65, 1.15, 1.75, 1.85, 1.05, 1.95):
            s = (L - 2 * p) / k
            if min_p <= s <= 3.40:
                return [a + p + s * i for i in range(k + 1)]
    k = max(1, round((L - 2 * pier) / 2.8))
    return [a + pier + (L - 2 * pier) * i / k for i in range(k + 1)]


def _wing_roof(m, g, x0, x1, y0, y1, top, roof, rm, upper_mat, lod, trim, dormers=False, axis="x",
               inset_y0=False, inset_y1=False, z_off=0.0):
    zt = top + max(0.0, z_off)
    o = .32
    ox = (o - .025) if (inset_y0 or inset_y1) else o
    if roof == "flat":
        oy0 = -(o + E) if inset_y0 else o
        oy1 = -(o + E) if inset_y1 else o
        cornice_roof(m, x0 - ox, x1 + ox, y0 - oy0, y1 + oy1, zt, lod, deep=.48, side=DRESSED, ends=DRESSED,
                     front=not inset_y0)
        return zt + .48
    elif roof == "hip":
        oy0 = -2 * E if inset_y0 else o
        oy1 = -2 * E if inset_y1 else o
        span = min(x1 - x0, y1 - y0)
        rise = (span / 2 + ox) * PITCH
        return pavilion_roof(m, x0 - ox, x1 + ox, y0 - oy0, y1 + oy1, zt, rise, lod, rm, finial=False)
    else:
        oy0 = -2 * E if inset_y0 else o
        oy1 = -2 * E if inset_y1 else o
        if axis == "x":
            ym = (y0 + y1) / 2
            zr = zt + (y1 - y0) / 2 * PITCH
            prof = [(y0 - oy0, zt - oy0 * PITCH), (ym, zr), (y1 + oy1, zt - oy1 * PITCH)]
            gw_ = [(ym, .75, top + .55, top + 1.65)] if (zr - top > 1.85) else []
            gable_wall(m, g, (x0, y1), (x0, y0), top, zr, lod, upper_mat, wins=gw_, trim=trim)
            gable_wall(m, g, (x1, y0), (x1, y1), top, zr, lod, upper_mat, wins=gw_, trim=trim)
            slab(m, prof, x0 - ox, x1 + ox, lambda a, q, z: (a, q, z), lod, rm, end=DRESSED, eave=DRESSED, what="Hydrostone gable")
            if lod == 0:
                wbox(m, x0 - ox + 3 * E, x1 + ox - 3 * E, ym - .08, ym + .08, zr + .14, zr + .22, rm, ("z-",))
                if dormers and (x1 - x0) >= 8.0 and not inset_y0:
                    top_f = lambda o_: zt + (-o_ - y0) * PITCH + .16
                    k = max(2, int((x1 - x0 - 3.0) / 4.2))
                    for j in range(k):
                        cx = x0 + 2.2 + (x1 - x0 - 4.4) * j / max(1, k - 1)
                        dormer(m, g, lambda o_, t, z: (t, -o_, z), top_f, -(y0 + 1.1), cx, 1.35, lod,
                               upper_mat, rm, trim, rise=.52, height=1.25, lites="6")
            return zr
        else:
            xm = (x0 + x1) / 2
            zr = zt + (x1 - x0) / 2 * PITCH
            prof = [(x0 - ox, zt - ox * PITCH), (xm, zr), (x1 + ox, zt - ox * PITCH)]
            gw_ = [(xm, .75, top + .55, top + 1.65)] if (zr - top > 1.85) else []
            if not inset_y0:
                gable_wall(m, g, (x0, y0), (x1, y0), top, zr, lod, upper_mat, wins=gw_, trim=trim)
            if not inset_y1:
                gable_wall(m, g, (x1, y1), (x0, y1), top, zr, lod, upper_mat, wins=gw_, trim=trim)
            ya = y0 - (2.4 if inset_y0 else o)
            yb = y1 + (2.4 if inset_y1 else o)
            slab(m, prof, ya, yb, lambda a, q, z: (q, a, z), lod, rm, end=DRESSED, eave=DRESSED, what="Hydrostone wing gable")
            return zr


def build(lod, W=3, D=4, **variant):
    for k in ("lots", "palette"):
        variant.pop(k, None)
    v = dict(DEFAULT, **variant)
    n = v["storeys"]
    plan = v["plan"]
    roof = v["roof"]
    corner = v["corner"]
    upper = v["upper"]
    rm = v["roof_mat"]
    df, cf = v["depth_f"], v["court_f"]
    XL, XH = -4.0 * W + SM, 4.0 * W - SM
    yF = -4.0 * D + SET
    end = 4.0 * D - .6
    totW = XH - XL
    totD = end - yF

    win, top = _h_floors(n)
    z_split = G + F * max(1, n - 2)
    mats = [(0.0, z_split, STONE), (z_split, top, upper)] if upper != STONE else [(0.0, top, STONE)]
    belts = (G, z_split) if upper != STONE else (G,)
    st = style(top, mats, win, belts=belts, plinth=None, corners=False, frieze=.30, belt_mat=DRESSED)
    ftrim = dict(door=v["door"], lites=v["lites"], masonry=DRESSED, reveal=STONE, frame=TRIM,
                 lean="bare" if lod else True)
    strim = dict(ftrim, simple=True)
    gtrim = dict(ftrim, simple=True)
    m, g = Mesh(), Mesh()

    def hwall(A, B, s, e, bays, door=None, trim=strim):
        ww_ = wall(m, g, st, A, B, s, e, bays, lod, door=door, trim=trim, waive=HYDRO_W)
        stone_coursing(m, ww_, holes_for(ww_, bays, win, door), G - .08, lod, s, e)
        return ww_

    narrow = W == 2
    # Adapt wide-court plans cleanly on W=2 while keeping EVERY design on a distinct footprint!
    if narrow and plan == "U_front":
        plan = "L_front_R"                                # left pavilion forward at yF, right front recessed garden court
    elif narrow and plan == "U_front_L":
        plan = "L_front_L"                                # right pavilion forward at yF, left front recessed garden court
    elif narrow and plan == "H":
        plan = "C_right"                                  # front & rear bars + left connecting wing, right side court
    elif narrow and plan == "T":
        plan = "L_right"                                  # front bar + right rear wing, open left rear garden court

    if plan == "L_left":
        # Full front bar + wide left-street rear wing to `end`, open right-rear garden court
        yM = yF + totD * df
        wx = XH - max(4.6, totW * cf)
        fb = _bays(XL, XH, 1.45, 3.1)
        hwall((XL, yF), (XH, yF), "x", "x", fb, door=(nearest(fb, 0.0), 1.3, 2.95), trim=ftrim)
        _quoins(m, (XL, yF), (XH, yF), .5, z_split, lod)
        sl = _bays(yF, end, 1.45, 3.1)
        hwall((XL, end), (XL, yF), "x", "x", sl, door=(nearest(sl, (yF + yM) / 2), 1.3, 2.95) if corner else None,
              trim=ftrim if corner else strim)
        hwall((XH, yF), (XH, yM), "x", "x", _bays(yF, yM, 1.4, 3.1))
        hwall((XH, yM), (wx, yM), "x", "c", _bays(wx, XH, 1.35, 3.0))
        cy_l = _bays(yM, end, 1.35, 3.0)
        hwall((wx, yM), (wx, end), "c", "x", cy_l, door=(nearest(cy_l, (yM + end) / 2), 1.1, 2.9))
        hwall((wx, end), (XL, end), "x", "x", _bays(XL, wx, 1.35, 3.0))
        zr = _wing_roof(m, g, XL, XH, yF, yM, top, roof, rm, upper, lod, gtrim, v["dormers"], axis="x")
        _wing_roof(m, g, XL, wx, yM, end, top, roof, rm, upper, lod, gtrim, False, axis="y", inset_y0=True, z_off=.015)
        if roof != "flat":
            chimney(m, 0.0, (yF + yM) / 2, .45, .45, top, zr + 1.0, lod, "Greystone")
    elif plan == "L_right":
        # Full front bar + wide right rear wing to `end`, open left-rear garden court
        yM = yF + totD * df
        wx = XL + max(4.6, totW * cf)
        fb = _bays(XL, XH, 1.45, 3.1)
        hwall((XL, yF), (XH, yF), "x", "x", fb, door=(nearest(fb, 0.0), 1.3, 2.95), trim=ftrim)
        _quoins(m, (XL, yF), (XH, yF), .5, z_split, lod)
        hwall((XL, yM), (XL, yF), "x", "x", _bays(yF, yM, 1.4, 3.1))
        hwall((XH, yF), (XH, end), "x", "x", _bays(yF, end, 1.45, 3.1))
        hwall((wx, yM), (XL, yM), "c", "x", _bays(XL, wx, 1.35, 3.0))
        cy_r = _bays(yM, end, 1.35, 3.0)
        hwall((wx, end), (wx, yM), "x", "c", cy_r, door=(nearest(cy_r, (yM + end) / 2), 1.1, 2.9))
        hwall((XH, end), (wx, end), "x", "x", _bays(wx, XH, 1.35, 3.0))
        zr = _wing_roof(m, g, XL, XH, yF, yM, top, roof, rm, upper, lod, gtrim, v["dormers"], axis="x")
        _wing_roof(m, g, wx, XH, yM, end, top, roof, rm, upper, lod, gtrim, False, axis="y", inset_y0=True, z_off=.015)
        if roof != "flat":
            chimney(m, 0.0, (yF + yM) / 2, .45, .45, top, zr + 1.0, lod, "Greystone")
    elif plan == "L_front_R":
        # W=2 front-garden-court L: left wing forward at yF=1.00, right front recessed court, full rear body
        y_in = yF + max(5.2, totD * df)
        wx = XH - max(4.8, totW * cf)
        hwall((XL, yF), (wx, yF), "x", "x", _bays(XL, wx, 1.35, 3.0), trim=ftrim)
        _quoins(m, (XL, yF), (wx, yF), .5, z_split, lod)
        hwall((wx, yF), (wx, y_in), "x", "c", _bays(yF, y_in, 1.3, 2.9), trim=ftrim)
        cb_f = _bays(wx, XH, 1.3, 3.0)
        hwall((wx, y_in), (XH, y_in), "c", "x", cb_f, door=(nearest(cb_f, (wx + XH) / 2), 1.3, 3.0), trim=ftrim)
        sl = _bays(yF, end, 1.45, 3.1)
        hwall((XL, end), (XL, yF), "x", "x", sl, door=(nearest(sl, (y_in + end) / 2), 1.3, 3.0) if corner else None,
              trim=ftrim if corner else strim)
        hwall((XH, y_in), (XH, end), "x", "x", _bays(y_in, end, 1.4, 3.1))
        hwall((XH, end), (XL, end), "x", "x", _bays(XL, XH, 1.45, 3.1))
        zr = _wing_roof(m, g, XL, XH, y_in, end, top, roof, rm, upper, lod, gtrim, False, axis="x")
        _wing_roof(m, g, XL, wx, yF, y_in, top, roof, rm, upper, lod, gtrim, False, axis="y", inset_y1=True, z_off=.015)
        if roof != "flat":
            chimney(m, 0.0, (y_in + end) / 2, .45, .45, top, zr + 1.0, lod, "Greystone")
    elif plan == "L_front_L":
        # W=2 mirrored front-garden-court L: right wing forward at yF=1.00, left front recessed court, full rear body
        y_in = yF + max(5.8, totD * df)
        wx = XL + max(4.8, totW * cf)
        hwall((wx, yF), (XH, yF), "x", "x", _bays(wx, XH, 1.35, 3.0), trim=ftrim)
        _quoins(m, (wx, yF), (XH, yF), .5, z_split, lod)
        hwall((wx, y_in), (wx, yF), "c", "x", _bays(yF, y_in, 1.3, 2.9), trim=ftrim)
        cb_f = _bays(XL, wx, 1.3, 3.0)
        hwall((XL, y_in), (wx, y_in), "x", "c", cb_f, door=(nearest(cb_f, (XL + wx) / 2), 1.3, 3.0), trim=ftrim)
        hwall((XL, end), (XL, y_in), "x", "x", _bays(y_in, end, 1.4, 3.1))
        hwall((XH, yF), (XH, end), "x", "x", _bays(yF, end, 1.45, 3.1))
        hwall((XH, end), (XL, end), "x", "x", _bays(XL, XH, 1.45, 3.1))
        zr = _wing_roof(m, g, XL, XH, y_in, end, top, roof, rm, upper, lod, gtrim, False, axis="x")
        _wing_roof(m, g, wx, XH, yF, y_in, top, roof, rm, upper, lod, gtrim, False, axis="y", inset_y1=True, z_off=.015)
        if roof != "flat":
            chimney(m, 0.0, (y_in + end) / 2, .45, .45, top, zr + 1.0, lod, "Greystone")
    elif plan == "C_mirror":
        # Full front bar + full rear bar + RIGHT-side connecting wing enclosing a LEFT side garden court
        y1 = yF + totD * df
        y2 = end - totD * max(.28, .66 - df)
        if y2 - y1 < 4.8:
            y2 = y1 + 4.8
        cx_in = XL + max(4.4, totW * cf)
        fb = _bays(XL, XH, 1.45, 3.1)
        hwall((XL, yF), (XH, yF), "x", "x", fb, door=(nearest(fb, 0.0), 1.35, 3.0), trim=ftrim)
        _quoins(m, (XL, yF), (XH, yF), .5, z_split, lod)
        hwall((XL, y1), (XL, yF), "x", "x", _bays(yF, y1, 1.4, 3.0))
        hwall((cx_in, y1), (XL, y1), "c", "x", _bays(XL, cx_in, 1.3, 2.9))
        hwall((cx_in, y2), (cx_in, y1), "c", "c", _bays(y1, y2, 1.3, 3.0))
        hwall((XL, y2), (cx_in, y2), "x", "c", _bays(XL, cx_in, 1.3, 2.9))
        hwall((XL, end), (XL, y2), "x", "x", _bays(y2, end, 1.4, 3.0))
        hwall((XH, yF), (XH, end), "x", "x", _bays(yF, end, 1.45, 3.1))
        hwall((XH, end), (XL, end), "x", "x", _bays(XL, XH, 1.45, 3.1))
        zr = _wing_roof(m, g, XL, XH, yF, y1, top, roof, rm, upper, lod, gtrim, v["dormers"], axis="x")
        _wing_roof(m, g, XL, XH, y2, end, top, roof, rm, upper, lod, gtrim, False, axis="x")
        _wing_roof(m, g, cx_in, XH, y1, y2, top, roof, rm, upper, lod, gtrim, False, axis="y",
                   inset_y0=True, inset_y1=True, z_off=.015)
        if roof != "flat":
            chimney(m, XH - 2.4, (yF + y1) / 2, .45, .45, top, zr + 1.0, lod, "Greystone")
    elif plan in ("C_right", "C_left"):
        # Full front bar + full rear bar + left-side connecting wing enclosing a right side garden court
        y1 = yF + totD * df
        y2 = end - totD * max(.28, .66 - df)
        if y2 - y1 < 4.8:
            y2 = y1 + 4.8
        cx_in = XH - max(4.4, totW * cf)
        fb = _bays(XL, XH, 1.45, 3.1)
        hwall((XL, yF), (XH, yF), "x", "x", fb, door=(nearest(fb, 0.0), 1.35, 3.0), trim=ftrim)
        _quoins(m, (XL, yF), (XH, yF), .5, z_split, lod)
        sl = _bays(yF, end, 1.45, 3.1)
        hwall((XL, end), (XL, yF), "x", "x", sl, door=(nearest(sl, (yF + y1) / 2), 1.3, 3.0) if corner else None,
              trim=ftrim if corner else strim)
        hwall((XH, yF), (XH, y1), "x", "x", _bays(yF, y1, 1.4, 3.0))
        hwall((XH, y1), (cx_in, y1), "x", "c", _bays(cx_in, XH, 1.3, 2.9))
        hwall((cx_in, y1), (cx_in, y2), "c", "c", _bays(y1, y2, 1.3, 3.0))
        hwall((cx_in, y2), (XH, y2), "c", "x", _bays(cx_in, XH, 1.3, 2.9))
        hwall((XH, y2), (XH, end), "x", "x", _bays(y2, end, 1.4, 3.0))
        hwall((XH, end), (XL, end), "x", "x", _bays(XL, XH, 1.45, 3.1))
        zr = _wing_roof(m, g, XL, XH, yF, y1, top, roof, rm, upper, lod, gtrim, v["dormers"], axis="x")
        _wing_roof(m, g, XL, XH, y2, end, top, roof, rm, upper, lod, gtrim, False, axis="x")
        _wing_roof(m, g, XL, cx_in, y1, y2, top, roof, rm, upper, lod, gtrim, False, axis="y",
                   inset_y0=True, inset_y1=True, z_off=.015)
        if roof != "flat":
            chimney(m, XL + 2.4, (yF + y1) / 2, .45, .45, top, zr + 1.0, lod, "Greystone")
    elif plan == "T":
        # Broad front bar + centered rear wing to `end` (open left & right rear yards >= 3.6 m)
        yM = yF + totD * df
        side_c = max(3.6, totW * cf)
        tx_a, tx_b = XL + side_c, XH - side_c
        fb = _bays(XL, XH, 1.45, 3.1)
        hwall((XL, yF), (XH, yF), "x", "x", fb, door=(nearest(fb, 0.0), 1.4, 3.1), trim=ftrim)
        _quoins(m, (XL, yF), (XH, yF), .5, z_split, lod)
        sf = _bays(yF, yM, 1.4, 3.0)
        hwall((XL, yM), (XL, yF), "x", "x", sf, door=(nearest(sf, (yF + yM) / 2), 1.3, 3.0) if corner else None,
              trim=ftrim if corner else strim)
        hwall((XH, yF), (XH, yM), "x", "x", sf)
        hwall((tx_a, yM), (XL, yM), "c", "x", _bays(XL, tx_a, 1.2, 2.8))
        hwall((XH, yM), (tx_b, yM), "x", "c", _bays(tx_b, XH, 1.2, 2.8))
        sy_t = _bays(yM, end, 1.35, 3.0)
        hwall((tx_a, end), (tx_a, yM), "x", "c", sy_t)
        hwall((tx_b, yM), (tx_b, end), "c", "x", sy_t)
        hwall((tx_b, end), (tx_a, end), "x", "x", _bays(tx_a, tx_b, 1.4, 3.0))
        zr = _wing_roof(m, g, XL, XH, yF, yM, top, roof, rm, upper, lod, gtrim, v["dormers"], axis="x")
        _wing_roof(m, g, tx_a, tx_b, yM, end, top, roof, rm, upper, lod, gtrim, False, axis="y", inset_y0=True, z_off=.015)
        if roof != "flat":
            for cx in (XL + 2.6, XH - 2.6):
                chimney(m, cx, (yF + yM) / 2, .45, .45, top, zr + 1.0, lod, "Greystone")
    elif plan in ("U_front", "U_front_L"):
        court_w = max(5.2, totW * cf)
        if plan == "U_front_L":                           # asymmetric front pavilions (distinct from symmetric U_front)
            ww_l = (totW - court_w) * .42
            ww_r = (totW - court_w) * .58
        else:
            ww_l = ww_r = (totW - court_w) / 2
        wx_l, wx_r = XL + ww_l, XH - ww_r
        y_in = yF + max(5.4, totD * df)
        hwall((XL, yF), (wx_l, yF), "x", "x", _bays(XL, wx_l, 1.35, 3.0), trim=ftrim)
        hwall((wx_r, yF), (XH, yF), "x", "x", _bays(wx_r, XH, 1.35, 3.0), trim=ftrim)
        _quoins(m, (XL, yF), (wx_l, yF), .5, z_split, lod)
        _quoins(m, (wx_r, yF), (XH, yF), .5, z_split, lod)
        cy_f = _bays(yF, y_in, 1.3, 2.9)
        hwall((wx_l, yF), (wx_l, y_in), "x", "c", cy_f, trim=ftrim)
        hwall((wx_r, y_in), (wx_r, yF), "c", "x", cy_f, trim=ftrim)
        cb_f = _bays(wx_l, wx_r, 1.35, 3.0)
        hwall((wx_l, y_in), (wx_r, y_in), "c", "c", cb_f, door=(nearest(cb_f, (wx_l + wx_r) / 2), 1.4, 3.1), trim=ftrim)
        if lod < 2:
            cm_ = (wx_l + wx_r) / 2
            wbox(m, cm_ - 1.2, cm_ + 1.2, yF + .1, y_in - .05, 0.0, .06, "Paving", ("z-",))
        sl = _bays(yF, end, 1.45, 3.1)
        hwall((XL, end), (XL, yF), "x", "x", sl, door=(nearest(sl, (y_in + end) / 2), 1.3, 3.0) if corner else None,
              trim=ftrim if corner else strim)
        hwall((XH, yF), (XH, end), "x", "x", sl)
        hwall((XH, end), (XL, end), "x", "x", _bays(XL, XH, 1.5, 3.1))
        zr = _wing_roof(m, g, XL, XH, y_in, end, top, roof, rm, upper, lod, gtrim, False, axis="x")
        _wing_roof(m, g, XL, wx_l, yF, y_in, top, roof, rm, upper, lod, gtrim, False, axis="y", inset_y1=True, z_off=.015)
        _wing_roof(m, g, wx_r, XH, yF, y_in, top, roof, rm, upper, lod, gtrim, False, axis="y", inset_y1=True, z_off=.015)
        if roof != "flat":
            for cx in (XL + 2.6, XH - 2.6):
                chimney(m, cx, (y_in + end) / 2, .45, .45, top, zr + 1.0, lod, "Greystone")
    elif plan == "U_rear":
        yM = yF + totD * df
        court_w = max(5.0, totW * cf) if not narrow else max(4.4, totW * cf)
        ww = (totW - court_w) / 2
        wx_l, wx_r = XL + ww, XH - ww
        fb = _bays(XL, XH, 1.45, 3.1)
        hwall((XL, yF), (XH, yF), "x", "x", fb, door=(nearest(fb, 0.0), 1.4, 3.1), trim=ftrim)
        _quoins(m, (XL, yF), (XH, yF), .5, z_split, lod)
        sl = _bays(yF, end, 1.45, 3.1)
        hwall((XL, end), (XL, yF), "x", "x", sl, door=(nearest(sl, (yF + yM) / 2), 1.3, 3.0) if corner else None,
              trim=ftrim if corner else strim)
        hwall((XH, yF), (XH, end), "x", "x", sl)
        hwall((wx_r, yM), (wx_l, yM), "c", "c", _bays(wx_l, wx_r, 1.3, 3.0))
        cy_r = _bays(yM, end, 1.35, 3.0)
        hwall((wx_l, yM), (wx_l, end), "c", "x", cy_r)
        hwall((wx_r, end), (wx_r, yM), "x", "c", cy_r)
        hwall((wx_l, end), (XL, end), "x", "x", _bays(XL, wx_l, 1.3, 3.0))
        hwall((XH, end), (wx_r, end), "x", "x", _bays(wx_r, XH, 1.3, 3.0))
        zr = _wing_roof(m, g, XL, XH, yF, yM, top, roof, rm, upper, lod, gtrim, v["dormers"], axis="x")
        _wing_roof(m, g, XL, wx_l, yM, end, top, roof, rm, upper, lod, gtrim, False, axis="y", inset_y0=True, z_off=.015)
        _wing_roof(m, g, wx_r, XH, yM, end, top, roof, rm, upper, lod, gtrim, False, axis="y", inset_y0=True, z_off=.015)
        if roof != "flat":
            for cx in (XL + 2.4, XH - 2.4):
                chimney(m, cx, (yF + yM) / 2, .45, .45, top, zr + 1.0, lod, "Greystone")
    else:                                                 # 'H' court (W >= 3)
        y1 = yF + totD * df
        y2 = end - totD * max(.30, .68 - df)
        side_c = max(4.2, totW * cf)
        sw = totW - 2 * side_c
        sx_a, sx_b = -sw / 2, sw / 2
        fb = _bays(XL, XH, 1.45, 3.1)
        hwall((XL, yF), (XH, yF), "x", "x", fb, door=(nearest(fb, 0.0), 1.4, 3.1), trim=ftrim)
        _quoins(m, (XL, yF), (XH, yF), .5, z_split, lod)
        sf = _bays(yF, y1, 1.4, 3.0)
        hwall((XL, y1), (XL, yF), "x", "x", sf, door=(nearest(sf, (yF + y1) / 2), 1.3, 3.0) if corner else None,
              trim=ftrim if corner else strim)
        hwall((XH, yF), (XH, y1), "x", "x", sf)
        hwall((sx_a, y1), (XL, y1), "c", "x", _bays(XL, sx_a, 1.3, 2.9))
        hwall((XH, y1), (sx_b, y1), "x", "c", _bays(sx_b, XH, 1.3, 2.9))
        sy_h = _bays(y1, y2, 1.3, 3.0)
        hwall((sx_a, y2), (sx_a, y1), "c", "c", sy_h)
        hwall((sx_b, y1), (sx_b, y2), "c", "c", sy_h)
        hwall((XL, y2), (sx_a, y2), "x", "c", _bays(XL, sx_a, 1.3, 2.9))
        hwall((sx_b, y2), (XH, y2), "c", "x", _bays(sx_b, XH, 1.3, 2.9))
        sr = _bays(y2, end, 1.4, 3.0)
        hwall((XL, end), (XL, y2), "x", "x", sr, trim=ftrim if corner else strim)
        hwall((XH, y2), (XH, end), "x", "x", sr)
        hwall((XH, end), (XL, end), "x", "x", _bays(XL, XH, 1.45, 3.1))
        zr = _wing_roof(m, g, XL, XH, yF, y1, top, roof, rm, upper, lod, gtrim, v["dormers"], axis="x")
        _wing_roof(m, g, XL, XH, y2, end, top, roof, rm, upper, lod, gtrim, False, axis="x")
        _wing_roof(m, g, sx_a, sx_b, y1, y2, top, roof, rm, upper, lod, gtrim, False, axis="y",
                   inset_y0=True, inset_y1=True, z_off=.015)
        if roof != "flat":
            for cx in (XL + 2.6, XH - 2.6):
                chimney(m, cx, (yF + y1) / 2, .45, .45, top, zr + 1.0, lod, "Greystone")

    finish(m, g)
