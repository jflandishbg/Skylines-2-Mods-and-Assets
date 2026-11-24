"""Lobstertown Shipyard Bungalows (ZL2, Maritime Boom 1910s-1930s): Working-class Craftsman SFR.

Inspired by Portsmouth's Atlantic Heights (1918), Bath's shipyard workers' tracts, and Portland's Deering/Woodfords
catalog kit homes. Low-slung Arts & Crafts massing (1.5-2 storeys) on strict coastal palette (no red/brown brick
walls or piers; rubble/greystone bases, weathered coastal shingles & muted Craftsman clapboard, dark/green slate
roofs, stone chimneys). Every design has its own distinct footprint (porch side/width, main depth, rear ell side,
garage position & depth) so no two designs share a 0.5 m occupancy footprint at any lot size (rule 21).

    build(lod, W=2, D=3, **variant)      free-standing SFR (1 hh) on 2x2..3x4 lots; LeftCorner wraps entry left

Variant keys:
  kind        'craftsman' | 'foursquare' | 'dutch' | 'gable_front'
  porch_side  'L' (left recessed porch) | 'R' (right recessed porch) | 'full' (full-width Foursquare porch)
              | 'none' (flush Dutch Colonial front with centered hooded entry stoop)
  porch_frac  width fraction of recessed porch when porch_side in ('L', 'R') (0.46..0.60)
  md_off      main-house depth offset in m (-0.8..+1.0) for footprint variety
  ell_side    'L' | 'R' | 'C' | 'twin' (rear wing / sunroom / ell placement)
  ell_w       ell width fraction (0.42..0.62)
  gar_align   'full' | 'L' | 'R' (rear alley garage alignment; 'L'/'R' leaves an open rear garden corner >= 3.2 m)
  gar_w       garage width fraction when gar_align in ('L', 'R') (0.72..0.82)
  cd_off      garage depth offset in m (-0.4..+0.6)
  sun_w       D=2 rear sunroom width fraction (0.54..0.88)
  wall        'ShingleGrey' | 'ShingleSilver' | 'Clapboard' | 'ClapSage'
  base        'Rubble' | 'Greystone' | 'StoneBase'
  roof_mat    'SlateDark' | 'SlateGreen'
  door        'Oxblood' | 'Green' | 'Black' | 'GreyBlue'
  gar         'gable' | 'hip'
  corner      False | True (LeftCorner, no lettering)
"""
import math
from lt_kit import Mesh, Wall, chimney, finish, wall, style, gable_wall, gable_roof, wbox, E, TRIM, roof_check
from lt_shapes import slab, dormer, pavilion_roof
from lt_designs.shore_row import WIN1, WIN2
from lt_designs.cottage import spread, nearest, cupola

SET = 1.0                     # front wall & porch pier line strictly at 1.00 m (Rule 29)
SM = 1.0                      # side yards
LOW = 3.6                     # 1.5-storey bungalow eave
TWO = 6.6                     # 2-storey Foursquare eave
GAR_H = 3.55                  # rear alley garage / workshop eave
PITCH = .55
GF_P = .48
HIP_P = .50
GAM_RUN, GAM_RISE, GAM_UP = 1.6, 2.3, .40
DEFAULT = dict(kind="craftsman", porch_side="L", porch_frac=.56, md_off=0.0, ell_side="L", ell_w=.48,
               gar_align="full", gar_w=.78, cd_off=0.0, sun_w=.72,
               wall="ShingleGrey", base="Rubble", roof_mat="SlateDark", door="Oxblood", lites="6",
               gar="gable", corner=False)
CRAFT_W = {"balance": "Craftsman bungalow asymmetric porch and living-room bay front"}


def _shed_dormer(m, g, x0, x1, y_face, z_sill, z_eave, slope_y, roof_top_fn, lod, mat, roof_mat, trim):
    w_len = x1 - x0
    A, B = (x0, y_face), (x1, y_face)
    k = max(2, min(4, int(w_len / 2.2)))
    bays = [x0 + .95 + (w_len - 1.9) * j / max(1, k - 1) for j in range(k)] if k > 1 else [(x0 + x1) / 2]
    st = style(z_eave, [(z_sill, z_eave, mat)], [(.65, z_sill + .25, z_eave - .42)],
               belts=(), plinth=None, corners=False, frieze=.18)
    wall(m, g, st, A, B, "x", "x", bays, lod, z0=z_sill, trim=dict(trim, simple=True),
         waive={"balance": "Craftsman shed dormer bank of windows", "corners": "dormer cheek piers",
                "rhythm": "grouped Craftsman dormer windows", "glass": "grouped dormer windows"})
    y_back = y_face + 2.8
    while y_back < y_face + 6.0 and roof_top_fn(y_back) < z_eave + (y_back - y_face) * .14 + .05:
        y_back += .25
    z_back = z_eave + (y_back - y_face) * .14
    for xx, sg in ((x0, -1), (x1, 1)):
        m.facing([(xx, y_face, z_sill - .08), (xx, y_face, z_eave), (xx, y_back, z_back), (xx, y_back, z_sill - .08)],
                 (sg, 0, 0), mat)
    prof = [(y_face - .28, z_eave - .28 * .14), (y_back + .25, z_back + .25 * .14)]
    slab(m, prof, x0 - .22, x1 + .22, lambda a, q, z: (a, q, z), lod, roof_mat, end=TRIM, eave=TRIM, th=.12,
         what="Craftsman shed dormer roof")


def _porch_piers(m, x0, x1, yF, yP, z_beam, lod, base_mat, door_x, open_left=True, open_right=False):
    """Solid grounded Craftsman stone half-wall & tapered piers along yF + open end return(s)."""
    za = .92
    zc = za + .09
    xa0 = x0 if open_left else (x0 + E)
    xa1 = x1 if open_right else (x1 - E)
    segs = [(xa0, max(xa0, door_x - .72)), (min(xa1, door_x + .72), xa1)]
    for a, b in segs:
        if b - a > .25:
            wbox(m, a, b, yF, yF + .34, 0.0, za, base_mat, ("z-",))
            if lod < 2:
                wbox(m, a - .03, b + .03, yF - .03, yF + .37, za + E, zc, "Dressed", ("z-",))
    if open_left:
        wbox(m, x0, x0 + .34, yF + .34 + E, yP - E, 0.0, za, base_mat, ("z-",))
        if lod < 2:
            wbox(m, x0 - .03, x0 + .37, yF + .37 + E, yP - .02, za + E, zc, "Dressed", ("z-",))
    if open_right:
        wbox(m, x1 - .34, x1, yF + .34 + E, yP - E, 0.0, za, base_mat, ("z-",))
        if lod < 2:
            wbox(m, x1 - .37, x1 + .03, yF + .37 + E, yP - .02, za + E, zc, "Dressed", ("z-",))
    if lod < 2:
        for i in range(3):
            wbox(m, door_x - .70, door_x + .70, yF - (i + 1) * .26, yF - i * .26 - E, 0.0, .66 - i * .20, "Greystone", ("z-",))
    fx0 = (x0 + .34 + E) if open_left else (x0 + E)
    fx1 = (x1 - .34 - E) if open_right else (x1 - E)
    wbox(m, fx0, fx1, yF + .34 + E, yP - E, 0.0, .68, base_mat, ("z-",))
    wbox(m, fx0 + .02, fx1 - .02, yF + .36, yP - .02, .68 + E, .76, "Deck", ("z-",))
    k = max(2, round((x1 - x0) / 3.4))
    pxs = [x0 + .30 + (x1 - x0 - .60) * j / k for j in range(k + 1)]
    for px in pxs:
        if abs(px - door_x) < .65:
            continue
        wbox(m, px - .20, px + .20, yF + .02, yF + .32, zc + E, 1.32, base_mat, ("z-",))
        if lod < 2:
            wbox(m, px - .23, px + .23, yF - .01, yF + .35, 1.32 + E, 1.40, "Dressed", ("z-",))
        wbox(m, px - .14, px + .14, yF + .05, yF + .29, 1.40 + E, z_beam - .24 - E, TRIM, ("z-", "z+"))
    wbox(m, x0 + E, x1 - E, yF + E, yF + .34, z_beam - .24, z_beam - E, TRIM)


def build(lod, W=2, D=3, **variant):
    for k in ("lots", "palette"):
        variant.pop(k, None)
    v = dict(DEFAULT, **variant)
    kind = v["kind"]
    corner = v["corner"]
    pside = v["porch_side"]
    wm = v["wall"]
    bm = v["base"]
    rm = v["roof_mat"]
    XL, XH = -4.0 * W + SM, 4.0 * W - SM
    yF = -4.0 * D + SET
    end = 4.0 * D - .6
    totW = XH - XL

    base_md = 9.8 if D == 2 else (11.2 if D == 3 else 12.2)
    MD = base_md + v["md_off"]
    yR = yF + MD
    ym = (yF + yR) / 2

    two = kind == "foursquare"
    top = TWO if two else LOW
    win = WIN2 if two else WIN1
    ftrim = dict(door=v["door"], lites=v["lites"], lean="bare" if lod else True)
    strim = dict(ftrim, simple=bool(lod))
    gtrim = dict(ftrim, simple=bool(lod))
    mats = [(0.0, .95, bm), (.95, top, wm)]
    belts = (3.70,) if two else ()
    main = style(top, mats, win, belts=belts, plinth=None, frieze=.28)
    gst_p = style(LOW, [(0.0, .95, bm), (.95, LOW, wm)], WIN1, belts=(), plinth=None, frieze=.22)
    ust = style(TWO, [(LOW, TWO, wm)], [WIN2[1]], belts=(3.70,), plinth=None, frieze=.28) if two else None
    m, g = Mesh(), Mesh()

    porch_d = 1.8
    yP = yF + porch_d

    # ---- Front Facade (4 distinct front configurations: left porch, right porch, full Foursquare porch, or flush Dutch)
    if pside == "none":
        fb = spread(XL, XH, pier=1.35, step=3.0)
        dx = nearest(fb, 0.0)
        wall(m, g, main, (XL, yF), (XH, yF), "x", "x", fb, lod, door=(dx, 1.05, 2.75), trim=ftrim, waive=CRAFT_W)
        # Compact Dutch Colonial stone entry stoop + bracketed door hood (stays 0.35 m inside -4*D)
        if lod < 2:
            wbox(m, dx - .95, dx + .95, yF - .62, yF - E, 0.0, .28, "Greystone", ("z-",))
            wbox(m, dx - 1.15, dx + 1.15, yF - .58, yF - E, 2.95, 3.12, TRIM, ("y+",))
            gable_roof(m, dx - 1.15, dx + 1.15, yF - .58, yF - 2 * E, 3.12, 3.55, lod, rm, over=(.12, -2 * E), sides=("e", "e"))
        yL_g, yR_g = yF, yF
    elif pside == "full":
        pb_g = spread(XL, XH, pier=1.35, step=3.0)
        dx = nearest(pb_g, 0.0)
        wall(m, g, gst_p, (XL, yP), (XH, yP), "c", "c", pb_g, lod, door=(dx, 1.05, 2.75), trim=ftrim, waive=CRAFT_W)
        _porch_piers(m, XL, XH, yF, yP, LOW, lod, bm, dx, open_left=True, open_right=True)
        m.facing([(XL + E, yF + .34 + E, LOW - .02), (XH - E, yF + .34 + E, LOW - .02),
                  (XH - E, yP - E, LOW - .02), (XL + E, yP - E, LOW - .02)], (0, 0, -1), TRIM)
        if two:
            wall(m, g, ust, (XL, yF), (XH, yF), "x", "x", spread(XL, XH, 1.35, 3.0), lod, z0=LOW, trim=ftrim, waive=CRAFT_W)
        yL_g, yR_g = yP, yP
    elif pside == "R":
        x_split = XH - totW * v["porch_frac"]
        lb_g = spread(XL, x_split, pier=1.2, step=2.8)
        wall(m, g, gst_p if two else main, (XL, yF), (x_split, yF), "x", "x", lb_g, lod, trim=ftrim, waive=CRAFT_W)
        wall(m, g, gst_p, (x_split, yF), (x_split, yP), "x", "c", [], lod, trim=ftrim, waive=CRAFT_W)
        pb_g = spread(x_split, XH, pier=1.25, step=3.0)
        dx = nearest(pb_g, (x_split + XH) / 2)
        wall(m, g, gst_p, (x_split, yP), (XH, yP), "c", "c", pb_g, lod, door=(dx, 1.05, 2.75), trim=ftrim, waive=CRAFT_W)
        _porch_piers(m, x_split, XH, yF, yP, LOW, lod, bm, dx, open_left=False, open_right=True)
        m.facing([(x_split + E, yF + .34 + E, LOW - .02), (XH - E, yF + .34 + E, LOW - .02),
                  (XH - E, yP - E, LOW - .02), (x_split + E, yP - E, LOW - .02)], (0, 0, -1), TRIM)
        if two:
            wall(m, g, ust, (XL, yF), (XH, yF), "x", "x", spread(XL, XH, 1.35, 3.0), lod, z0=LOW, trim=ftrim, waive=CRAFT_W)
        yL_g, yR_g = yF, yP
    else:                                                 # pside == 'L'
        x_split = XL + totW * v["porch_frac"]
        pb_g = spread(XL, x_split, pier=1.25, step=3.0)
        dx = nearest(pb_g, (XL + x_split) / 2)
        wall(m, g, gst_p, (XL, yP), (x_split, yP), "c", "c", pb_g, lod, door=(dx, 1.05, 2.75), trim=ftrim, waive=CRAFT_W)
        wall(m, g, gst_p, (x_split, yP), (x_split, yF), "c", "x", [], lod, trim=ftrim, waive=CRAFT_W)
        lb_g = spread(x_split, XH, pier=1.2, step=2.8)
        wall(m, g, gst_p if two else main, (x_split, yF), (XH, yF), "x", "x", lb_g, lod, trim=ftrim, waive=CRAFT_W)
        _porch_piers(m, XL, x_split, yF, yP, LOW, lod, bm, dx, open_left=True, open_right=False)
        m.facing([(XL + E, yF + .34 + E, LOW - .02), (x_split - E, yF + .34 + E, LOW - .02),
                  (x_split - E, yP - E, LOW - .02), (XL + E, yP - E, LOW - .02)], (0, 0, -1), TRIM)
        if two:
            wall(m, g, ust, (XL, yF), (XH, yF), "x", "x", spread(XL, XH, 1.35, 3.0), lod, z0=LOW, trim=ftrim, waive=CRAFT_W)
        yL_g, yR_g = yP, yF

    # ---- Side walls of main house
    sb_l = spread(yL_g, yR, pier=1.25, step=3.0)
    if corner:
        sdx = nearest(sb_l, (yL_g + yR) / 2)
        wall(m, g, gst_p if two else main, (XL, yR), (XL, yL_g), "x", "c" if yL_g > yF else "x", sb_l, lod,
             door=(sdx, 1.0, 2.75), trim=ftrim, waive=CRAFT_W)
    else:
        wall(m, g, gst_p if two else main, (XL, yR), (XL, yL_g), "x", "c" if yL_g > yF else "x", sb_l, lod,
             trim=strim, waive=CRAFT_W)
    if two:
        wall(m, g, ust, (XL, yR), (XL, yF), "x", "x", spread(yF, yR, 1.35, 3.0), lod, z0=LOW,
             trim=ftrim if corner else strim, waive=CRAFT_W)
    sb_r = spread(yR_g, yR, pier=1.25, step=3.0)
    wall(m, g, gst_p if two else main, (XH, yR_g), (XH, yR), "c" if yR_g > yF else "x", "x", sb_r, lod,
         trim=strim, waive=CRAFT_W)
    if two:
        wall(m, g, ust, (XH, yF), (XH, yR), "x", "x", spread(yF, yR, 1.35, 3.0), lod, z0=LOW, trim=strim, waive=CRAFT_W)

    # ---- Main Roof (stone chimneys in Greystone -- zero red brick!)
    o = .42
    if kind == "foursquare":
        rise = (MD / 2 + o) * HIP_P
        zr = pavilion_roof(m, XL - o, XH + o, yF - o, yR + o, top, rise, lod, rm, finial=False)
        rear_slope = HIP_P
        top_f = lambda q: top + (q - yF + o) * HIP_P + .12
        dormer(m, g, lambda o_, t, z: (t, -o_, z), lambda o_: top_f(-o_), -(yF + 1.25), 0.0, 2.4, lod,
               wm, rm, gtrim, rise=.75, height=1.35, lites=v["lites"])
        chimney(m, XH - 2.0, ym, .48, .48, top - .2, zr + .9, lod, "Greystone")
    elif kind == "gable_front":
        half = totW / 2
        zr = top + half * GF_P
        prof_g = [(XL - o, top - o * GF_P), (0.0, zr), (XH + o, top - o * GF_P)]
        slab(m, prof_g, yF - o, yR + o, lambda a, q, z: (q, a, z), lod, rm, end=TRIM, eave=TRIM, what="Craftsman front gable")
        if lod == 0:
            wbox(m, -.09, .09, yF - o + 3 * E, yR + o - 3 * E, zr + .14, zr + .23, rm, ("z-",))
        gw_f = [(-1.2, .8, top + .55, top + 1.75), (1.2, .8, top + .55, top + 1.75)] if totW > 14 else [(0.0, .9, top + .55, top + 1.75)]
        gable_wall(m, g, (XL, yF), (XH, yF), top, zr, lod, wm, wins=gw_f, trim=gtrim)
        gable_wall(m, g, (XH, yR), (XL, yR), top, zr, lod, wm, wins=[(0.0, .85, top + .55, top + 1.75)], trim=gtrim)
        if lod == 0:
            for s in (-1, 1):
                bx = (XH if s > 0 else XL) - s * 1.4
                bz = top + (half - 1.4) * GF_P - .35
                wbox(m, bx - .08, bx + .08, yF - .38, yF - E, bz - .22, bz + .18, TRIM, ("y+",))
        chimney(m, XH - 1.6, ym, .50, .45, top - .2, zr + 1.1, lod, "Greystone")
        rear_slope = None
    elif kind == "dutch":
        k1 = GAM_RISE / GAM_RUN
        zk = top + GAM_RISE
        zr = zk + (MD / 2 - GAM_RUN) * GAM_UP
        prof = [(yF - o, top - o * k1), (yF + GAM_RUN, zk), (ym, zr), (yR - GAM_RUN, zk), (yR + o, top - o * k1)]
        shape = (zk, GAM_RUN)
        front_top = lambda q: top + min(q - yF, GAM_RUN) * k1 + max(0.0, q - yF - GAM_RUN) * GAM_UP + .16
        gw_s = [(ym, .85, top + .7, top + 2.0)]
        gable_wall(m, g, (XL, yR), (XL, yF), top, zr, lod, wm, wins=gw_s, trim=gtrim, shape=shape)
        gable_wall(m, g, (XH, yF), (XH, yR), top, zr, lod, wm, wins=gw_s, trim=gtrim, shape=shape)
        slab(m, prof, XL - .35, XH + .35, lambda a, q, z: (a, q, z), lod, rm, end=TRIM, eave=TRIM, what="Dutch gambrel roof")
        if lod == 0:
            wbox(m, XL - .32, XH + .32, ym - .09, ym + .09, zr + .14, zr + .23, rm, ("z-",))
        _shed_dormer(m, g, XL + 1.8, XH - 1.8, yF + 1.1, top + 1.30, top + 3.05, GAM_UP, front_top, lod, wm, rm, gtrim)
        if lod == 0:
            x_r = XL + .35
            while x_r < XH - .30:
                wbox(m, x_r - .04, x_r + .04, yF - o + .04, yF - .12, top - o * k1 - .14, top - o * k1 - E, TRIM)
                wbox(m, x_r - .04, x_r + .04, yR + .12, yR + o - .04, top - o * k1 - .14, top - o * k1 - E, TRIM)
                x_r += .55
        chimney(m, XH - 1.2, ym, .48, .48, top - .2, zr + 1.0, lod, "Greystone")
        rear_slope = k1
    elif kind == "capecod":
        CAPE_P = .72
        zr = top + MD / 2 * CAPE_P
        prof = [(yF - o, top - o * CAPE_P), (ym, zr), (yR + o, top - o * CAPE_P)]
        front_top = lambda o_: top + (-o_ - yF) * CAPE_P + .14
        gw_s = [(ym, .85, top + .7, top + 2.05)]
        gable_wall(m, g, (XL, yR), (XL, yF), top, zr, lod, wm, wins=gw_s, trim=gtrim)
        gable_wall(m, g, (XH, yF), (XH, yR), top, zr, lod, wm, wins=gw_s, trim=gtrim)
        slab(m, prof, XL - .35, XH + .35, lambda a, q, z: (a, q, z), lod, rm, end=TRIM, eave=TRIM, what="Cape Cod gable roof")
        if lod == 0:
            wbox(m, XL - .32, XH + .32, ym - .09, ym + .09, zr + .14, zr + .23, rm, ("z-",))
        dxs = (-totW * .25, totW * .25) if W == 2 else (-totW * .30, 0.0, totW * .30)
        for dcx in dxs:
            dormer(m, g, lambda o_, t, z: (t, -o_, z), front_top, -(yF + 1.4), dcx, 1.85, lod,
                   wm, rm, gtrim, rise=.68, height=1.45, lites=v["lites"])
        chimney(m, 0.0, ym, .52, .48, top - .2, zr + 1.0, lod, "Greystone")
        rear_slope = CAPE_P
    elif kind == "saltbox":
        SALT_H = 5.9
        y_ridge = yF + MD * .34
        k_f = .62
        zr = SALT_H + (y_ridge - yF) * k_f
        k_r = (zr - top) / (yR - y_ridge)
        salt_ust = style(SALT_H, [(top, SALT_H, wm)], [(.95, top + .45, SALT_H - .52)], belts=(3.70,), plinth=None, frieze=.24)
        wall(m, g, salt_ust, (XL, yF), (XH, yF), "x", "x", spread(XL, XH, 1.35, 3.0), lod, z0=top, trim=ftrim, waive=CRAFT_W)
        # Upper side-wall rectangular strip (yF..y_ridge) + asymmetric catslide gable triangles
        sw_u = [(yF + y_ridge) / 2]
        wall(m, g, salt_ust, (XL, y_ridge), (XL, yF), "x", "x", sw_u, lod, z0=top, trim=ftrim if corner else strim, waive=CRAFT_W)
        wall(m, g, salt_ust, (XH, yF), (XH, y_ridge), "x", "x", sw_u, lod, z0=top, trim=strim, waive=CRAFT_W)
        for xx, sg in ((XL, -1), (XH, 1)):
            m.facing([(xx, yF, SALT_H), (xx, y_ridge, zr), (xx, y_ridge, SALT_H)], (sg, 0, 0), wm)
            m.facing([(xx, y_ridge, top), (xx, y_ridge, zr), (xx, yR, top)], (sg, 0, 0), wm)
        prof = [(yF - o, SALT_H - o * k_f), (y_ridge, zr), (yR + o, top - o * k_r)]
        slab(m, prof, XL - .35, XH + .35, lambda a, q, z: (a, q, z), lod, rm, end=TRIM, eave=TRIM, what="New England saltbox roof")
        if lod == 0:
            wbox(m, XL - .32, XH + .32, y_ridge - .09, y_ridge + .09, zr + .14, zr + .23, rm, ("z-",))
        chimney(m, 0.0, y_ridge, .52, .48, top - .2, zr + 1.0, lod, "Greystone")
        rear_slope = k_r
    elif kind == "jerkinhead":
        zr = top + MD / 2 * PITCH
        clip = 1.65
        zc_end = top + (zr - top) * .68
        dy_c = (zc_end - top) / PITCH
        y_c0, y_c1 = yF + dy_c, yR - dy_c
        ze = top - o * PITCH
        # Closed trapezoidal end gable walls (XL & XH)
        for xx, sg in ((XL, -1), (XH, 1)):
            m.facing([(xx, yF, top), (xx, y_c0, zc_end), (xx, y_c1, zc_end), (xx, yR, top)], (sg, 0, 0), wm)
        # Watertight clipped-gable roof solid (top shell + bottom shell + perimeter fascia)
        th = .14
        per = [
            (XL - o, yF - o, ze), (XH + o, yF - o, ze), (XH + o, y_c0, zc_end), (XH + o, y_c1, zc_end),
            (XH + o, yR + o, ze), (XL - o, yR + o, ze), (XL - o, y_c1, zc_end), (XL - o, y_c0, zc_end),
        ]
        R0, R1 = (XL + clip, ym, zr), (XH - clip, ym, zr)
        pt = [(x, y, z + th) for x, y, z in per]
        pb = list(per)
        r0t, r1t = (R0[0], R0[1], R0[2] + th), (R1[0], R1[1], R1[2] + th)
        rt = Mesh()
        for pts_, h_, mat_ in (
            ([pt[0], pt[1], pt[2], pt[7]], (0, -1, 1), rm),
            ([pt[7], pt[2], r1t, r0t], (0, -1, 1), rm),
            ([pt[4], pt[5], pt[6], pt[3]], (0, 1, 1), rm),
            ([pt[3], pt[6], r0t, r1t], (0, 1, 1), rm),
            ([pt[2], pt[3], r1t], (1, 0, 1), rm),
            ([pt[6], pt[7], r0t], (-1, 0, 1), rm),
            ([pb[0], pb[7], pb[2], pb[1]], (0, 1, -1), TRIM),
            ([pb[7], R0, R1, pb[2]], (0, 1, -1), TRIM),
            ([pb[4], pb[3], pb[6], pb[5]], (0, -1, -1), TRIM),
            ([pb[3], R1, R0, pb[6]], (0, -1, -1), TRIM),
            ([pb[2], R1, pb[3]], (-1, 0, -1), TRIM),
            ([pb[6], R0, pb[7]], (1, 0, -1), TRIM),
        ):
            rt.facing(pts_, h_, mat_)
        for i in range(8):
            j = (i + 1) % 8
            mx_ = (per[i][0] + per[j][0]) / 2
            my_ = (per[i][1] + per[j][1]) / 2
            rt.facing([pb[i], pb[j], pt[j], pt[i]], (mx_, my_ - ym, 0), TRIM)
        roof_check(m, rt, "Jerkinhead roof")
        if lod == 0:
            wbox(m, XL + clip + .05, XH - clip - .05, ym - .09, ym + .09, zr + th, zr + th + .09, rm, ("z-",))
        front_top = lambda q: top + (q - yF) * PITCH + .16
        dw_ = max(4.2, totW * .50)
        _shed_dormer(m, g, -dw_ / 2, dw_ / 2, yF + 1.4, top + .82, top + 2.55, PITCH, front_top, lod, wm, rm, gtrim)
        chimney(m, XH - 1.5, ym, .50, .48, top - .2, zr + 1.0, lod, "Greystone")
        rear_slope = PITCH
    else:                                                 # 'craftsman'
        zr = top + MD / 2 * PITCH
        prof = [(yF - o, top - o * PITCH), (ym, zr), (yR + o, top - o * PITCH)]
        front_top = lambda q: top + (q - yF) * PITCH + .16
        gw_s = [(ym, .85, top + .65, top + 1.9)]
        gable_wall(m, g, (XL, yR), (XL, yF), top, zr, lod, wm, wins=gw_s, trim=gtrim)
        gable_wall(m, g, (XH, yF), (XH, yR), top, zr, lod, wm, wins=gw_s, trim=gtrim)
        slab(m, prof, XL - .35, XH + .35, lambda a, q, z: (a, q, z), lod, rm, end=TRIM, eave=TRIM, what="Craftsman side gable")
        if lod == 0:
            wbox(m, XL - .32, XH + .32, ym - .09, ym + .09, zr + .14, zr + .23, rm, ("z-",))
            x_r = XL + .35
            while x_r < XH - .30:
                wbox(m, x_r - .04, x_r + .04, yF - o + .04, yF - .02, top - o * PITCH - .14, top - o * PITCH - E, TRIM)
                wbox(m, x_r - .04, x_r + .04, yR + .02, yR + o - .04, top - o * PITCH - .14, top - o * PITCH - E, TRIM)
                x_r += .55
        dw_ = max(4.4, totW * .55)
        _shed_dormer(m, g, -dw_ / 2, dw_ / 2, yF + 1.4, top + .82, top + 2.58, PITCH, front_top, lod, wm, rm, gtrim)
        chimney(m, XL + 1.4, ym, .50, .48, top - .2, zr + 1.0, lod, "Greystone")
        rear_slope = PITCH

    # ---- Rear Massing (unique per design: sunroom position on D=2; ell side + garage alignment/depth on D>=3)
    est = style(GAR_H, [(0.0, .6, bm), (.6, GAR_H, wm)], [(.85, 1.1, 2.55)], belts=(), plinth=None, frieze=.22)
    es = v["ell_side"]
    if D == 2:
        sw = totW * v["sun_w"]
        if es == "L":
            wa, wb = XL + .5, min(XH - 2.6, XL + .5 + sw)
        elif es == "R":
            wb, wa = XH - .5, max(XL + 2.6, XH - .5 - sw)
        else:                                             # centered sunroom
            wa, wb = -sw / 2, sw / 2
            if wa - XL < .5:
                wa, wb = XL + .5, XH - .5
        # Main rear wall segments left & right of sunroom (windows if >= 2.6 m wide)
        if XH - wb > 2.6:
            wall(m, g, gst_p if two else main, (XH, yR), (wb, yR), "x", "c", spread(wb, XH, 1.1, 2.8), lod, trim=strim, waive=CRAFT_W)
        else:
            wall(m, g, gst_p if two else main, (XH, yR), (wb, yR), "x", "c", [], lod, trim=strim, waive=CRAFT_W)
        if wa - XL > 2.6:
            wall(m, g, gst_p if two else main, (wa, yR), (XL, yR), "c", "x", spread(XL, wa, 1.1, 2.8), lod, trim=strim, waive=CRAFT_W)
        else:
            wall(m, g, gst_p if two else main, (wa, yR), (XL, yR), "c", "x", [], lod, trim=strim, waive=CRAFT_W)
        if two:
            wall(m, g, ust, (XH, yR), (XL, yR), "x", "x", spread(XL, XH, 1.35, 3.0), lod, z0=LOW, trim=strim, waive=CRAFT_W)
        ey2 = [(yR + end) / 2] if (end - yR < 4.5) else spread(yR, end, 1.1, 2.8)
        wall(m, g, est, (wb, yR), (wb, end), "c", "x", ey2, lod, trim=strim, waive=CRAFT_W)
        wall(m, g, est, (wa, end), (wa, yR), "x", "c", ey2, lod, trim=strim, waive=CRAFT_W)
        rb_2 = spread(wa, wb, pier=1.25, step=3.0)
        wall(m, g, est, (wb, end), (wa, end), "x", "x", rb_2, lod, door=(nearest(rb_2, (wa + wb) / 2), 1.0, 2.6),
             trim=strim, waive=CRAFT_W)
        pavilion_roof(m, wa - .3, wb + .3, yR - .4, end + .3, GAR_H, min(1.5, (end - yR) * .45), lod, rm, finial=False)
    else:
        twin = (es == "twin" and W >= 3)
        if es == "twin" and W < 3:
            es = "R"
        # Garage bounds gx0..gx1
        ga = v["gar_align"]
        if ga == "L" and not twin:
            gx0 = XL
            gx1 = min(XH - 3.2, XL + totW * v["gar_w"])
        elif ga == "R" and not twin:
            gx1 = XH
            gx0 = max(XL + 3.2, XH - totW * v["gar_w"])
        else:
            gx0, gx1 = XL, XH
        gW = gx1 - gx0
        CD = (6.8 if D == 3 else 8.4) + v["cd_off"]
        yC = end - CD
        yk = (yC + end) / 2

        # Ell bounds (always anchored cleanly inside both [XL, XH] and [gx0, gx1]!)
        if twin:
            ww = min(7.2, (totW - 5.2) / 2)
            wa, wb = XL + .5, XL + .5 + ww
            rwa, rwb = XH - .5 - ww, XH - .5
        elif es == "R":
            ww = min(7.8, max(5.2, totW * v["ell_w"]))
            wb = gx1 - .5
            wa = max(gx0 + .5, wb - ww)
            if wa - XL < 3.4:
                wa = XL + 3.4
            ww = wb - wa
        elif es == "C":
            ww = min(8.2, max(5.4, totW * v["ell_w"]))
            cx_g = (gx0 + gx1) / 2
            wa, wb = cx_g - ww / 2, cx_g + ww / 2
        else:                                             # 'L'
            ww = min(7.8, max(5.2, totW * v["ell_w"]))
            wa = gx0 + .5
            wb = min(gx1 - .5, wa + ww)
            if XH - wb < 3.4:
                wb = XH - 3.4
            ww = wb - wa

        ell_p = .45
        zw = GAR_H + ww / 2 * ell_p

        # Main rear wall
        if twin:
            cb_m = spread(wb, rwa, pier=1.25, step=3.0)
            wall(m, g, gst_p if two else main, (XH, yR), (rwb, yR), "x", "c", [], lod, trim=strim, waive=CRAFT_W)
            wall(m, g, gst_p if two else main, (rwa, yR), (wb, yR), "c", "c", cb_m, lod,
                 door=(nearest(cb_m, (wb + rwa) / 2), 1.0, 2.7), trim=strim, waive=CRAFT_W)
            wall(m, g, gst_p if two else main, (wa, yR), (XL, yR), "c", "x", [], lod, trim=strim, waive=CRAFT_W)
        elif es == "C":
            rb_l = spread(XL, wa, pier=1.1, step=2.8)
            rb_r = spread(wb, XH, pier=1.1, step=2.8)
            wall(m, g, gst_p if two else main, (XH, yR), (wb, yR), "x", "c", rb_r, lod,
                 door=(nearest(rb_r, (wb + XH) / 2), 1.0, 2.7), trim=strim, waive=CRAFT_W)
            wall(m, g, gst_p if two else main, (wa, yR), (XL, yR), "c", "x", rb_l, lod, trim=strim, waive=CRAFT_W)
        elif es == "R":
            cb_m = spread(XL, wa, pier=1.2, step=3.0)
            wall(m, g, gst_p if two else main, (XH, yR), (wb, yR), "x", "c", [], lod, trim=strim, waive=CRAFT_W)
            wall(m, g, gst_p if two else main, (wa, yR), (XL, yR), "c", "x", cb_m, lod,
                 door=(nearest(cb_m, (XL + wa) / 2), 1.0, 2.7), trim=strim, waive=CRAFT_W)
        else:
            cb_m = spread(wb, XH, pier=1.2, step=3.0)
            wall(m, g, gst_p if two else main, (XH, yR), (wb, yR), "x", "c", cb_m, lod,
                 door=(nearest(cb_m, (wb + XH) / 2), 1.0, 2.7), trim=strim, waive=CRAFT_W)
            wall(m, g, gst_p if two else main, (wa, yR), (XL, yR), "c", "x", [], lod, trim=strim, waive=CRAFT_W)
        if two:
            wall(m, g, ust, (XH, yR), (XL, yR), "x", "x", spread(XL, XH, 1.35, 3.0), lod, z0=LOW, trim=strim, waive=CRAFT_W)

        # Ell(s) connecting main house to rear garage/workshop
        ey = spread(yR, yC, pier=1.15, step=3.0)
        fwd = (zw + .16 - top) / rear_slope + .45 if (rear_slope and zw + .16 > top - .05) else -2 * E
        if v["gar"] == "hip":
            gp = .52
            zc = GAR_H + (CD / 2 + .35) * gp
            aft = (zw + .16 - GAR_H) / gp + .45
        else:
            gp = max(.55, (zw + .45 - GAR_H) / (CD / 2))
            zc = GAR_H + CD / 2 * gp
            aft = (zw + .16 - GAR_H) / gp + .45
        ell_list = ((wa, wb, "L"), (rwa, rwb, "R")) if twin else ((wa, wb, es),)
        for xa_, xb_, sd in ell_list:
            if sd == "R":
                wall(m, g, est, (xa_, yC), (xa_, yR), "c", "c", ey, lod, door=(ey[0], .95, 2.6), trim=strim, waive=CRAFT_W)
                wall(m, g, est, (xb_, yR), (xb_, yC), "c", "c", ey, lod, trim=strim, waive=CRAFT_W)
            else:
                wall(m, g, est, (xb_, yR), (xb_, yC), "c", "c", ey, lod, door=(ey[0], .95, 2.6), trim=strim, waive=CRAFT_W)
                wall(m, g, est, (xa_, yC), (xa_, yR), "c", "c", ey, lod, trim=strim, waive=CRAFT_W)
            gable_roof(m, xa_, xb_, yR, yC, GAR_H, zw, lod, rm, over=(fwd, aft), sides=("e", "e"))

        # Rear alley garage / workshop across gx0..gx1, yC..end
        gst = style(GAR_H, [(0.0, .45, bm), (.45, GAR_H, wm)], [(.85, 1.25, 2.55)], belts=(), plinth=None, frieze=.22)
        if twin:
            gcb = [(wb + rwa) / 2] if (rwa - wb < 9.2) else spread(wb, rwa, pier=1.4, step=3.4)
            wall(m, g, gst, (wb, yC), (rwa, yC), "c", "c", gcb, lod, door=(nearest(gcb, (wb + rwa) / 2), 2.1, 2.85), trim=strim, waive=CRAFT_W)
            wall(m, g, gst, (gx0, yC), (wa, yC), "x", "c", [], lod, trim=strim, waive=CRAFT_W)
            wall(m, g, gst, (rwb, yC), (gx1, yC), "c", "x", [], lod, trim=strim, waive=CRAFT_W)
        elif es == "C":
            gcb_r = [(wb + gx1) / 2] if (gx1 - wb < 9.2) else spread(wb, gx1, pier=1.4, step=3.4)
            gcb_l = [(gx0 + wa) / 2] if (wa - gx0 < 4.5) else spread(gx0, wa, pier=1.1, step=2.8)
            wall(m, g, gst, (wb, yC), (gx1, yC), "c", "x", gcb_r, lod,
                 door=(nearest(gcb_r, (wb + gx1) / 2), 2.1, 2.85) if (gx1 - wb >= 4.8) else None, trim=strim, waive=CRAFT_W)
            wall(m, g, gst, (gx0, yC), (wa, yC), "x", "c", gcb_l, lod, trim=strim, waive=CRAFT_W)
        elif es == "R":
            gcb = [(gx0 + wa) / 2] if (wa - gx0 < 9.2) else spread(gx0, wa, pier=1.4, step=3.4)
            wall(m, g, gst, (gx0, yC), (wa, yC), "x", "c", gcb, lod,
                 door=(nearest(gcb, (gx0 + wa) / 2), 2.1, 2.85) if (wa - gx0 >= 4.8) else None, trim=strim, waive=CRAFT_W)
            wall(m, g, gst, (wb, yC), (gx1, yC), "c", "x", [], lod, trim=strim, waive=CRAFT_W)
        else:
            gcb = [(wb + gx1) / 2] if (gx1 - wb < 9.2) else spread(wb, gx1, pier=1.4, step=3.4)
            wall(m, g, gst, (wb, yC), (gx1, yC), "c", "x", gcb, lod,
                 door=(nearest(gcb, (wb + gx1) / 2), 2.1, 2.85) if (gx1 - wb >= 4.8) else None, trim=strim, waive=CRAFT_W)
            wall(m, g, gst, (gx0, yC), (wa, yC), "x", "c", [], lod, trim=strim, waive=CRAFT_W)
        gsb = spread(yC, end, pier=1.2, step=2.8)
        wall(m, g, gst, (gx0, end), (gx0, yC), "x", "x", gsb, lod, trim=strim, waive=CRAFT_W)
        wall(m, g, gst, (gx1, yC), (gx1, end), "x", "x", gsb, lod, trim=strim, waive=CRAFT_W)
        wall(m, g, gst, (gx1, end), (gx0, end), "x", "x", spread(gx0, gx1, 1.3, 2.9), lod, trim=strim, waive=CRAFT_W)
        gxm = (gx0 + gx1) / 2
        if v["gar"] == "hip":
            pavilion_roof(m, gx0 - .35, gx1 + .35, yC - .32, end + .32, GAR_H, zc - GAR_H, lod, rm, finial=False)
        else:
            gable_wall(m, g, (gx0, end), (gx0, yC), GAR_H, zc, lod, wm, wins=[(yk, .7, GAR_H + .45, GAR_H + 1.45)], trim=gtrim)
            gable_wall(m, g, (gx1, yC), (gx1, end), GAR_H, zc, lod, wm, wins=[(yk, .7, GAR_H + .45, GAR_H + 1.45)], trim=gtrim)
            gprof = [(yC - .35, GAR_H - .35 * gp), (yk, zc), (end + .32, GAR_H - .32 * gp)]
            slab(m, gprof, gx0 - .3, gx1 + .3, lambda a, q, z: (a, q, z), lod, rm, end=TRIM, eave=TRIM, what="Craftsman garage roof")
            if lod == 0:
                wbox(m, gx0 - .27, gx1 + .27, yk - .08, yk + .08, zc + .14, zc + .22, rm, ("z-",))
        if lod == 0:
            cupola(m, gxm, yk, zc + .12, lod, wm, rm, v["door"], a=.55, sink=.45, h=.85)
        if lod < 2:
            if twin:                                         # Lot review fix: walk along left ell so rear court stays open for planting
                wbox(m, wb + .15, wb + 1.20, yR + .06, yC - .06, 0.0, .05, "Paving", ("z-",))
            elif es == "R":
                wbox(m, wa - 1.4, wa - .3, yR + .06, yC - .06, 0.0, .05, "Paving", ("z-",))
            else:
                wbox(m, wb + .3, wb + 1.4, yR + .06, yC - .06, 0.0, .05, "Paving", ("z-",))

    finish(m, g)
