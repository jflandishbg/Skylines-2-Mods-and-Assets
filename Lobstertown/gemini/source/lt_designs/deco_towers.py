"""Lobstertown Beacon Towers (ZH2, Maritime Boom 1920s-1930s): Coastal Setback / Art Deco Brick & Stone Towers.

The Roaring Twenties wave of Atlantic City (Claridge/Traymore era), Portland (Chapman/Eastland), and Boston/Halifax
pre-war setback apartment towers. Strict coastal palette (rule 20: buff, sand, cream, greige stone/brick, muted
coastal blue-grey and sage painted masonry; reds/browns only on doors; verdigris green copper and dark/green slate
crowns; bronze sashes). Every design has its own podium footprint (U, deep-U, H, deep-H, T, L-left, L-right, C-right)
and setback crown (hip + lantern, stepped ziggurat, copper dome, pyramid) so no two designs share a footprint.

    build(lod, W=4, D=5, **variant)      free-standing on 3x4..5x5 lots; LeftCorner wraps piers & portal to left street

Variant keys:
  base_n    4 | 5 | 6: podium storeys (4.6 m ground storey + 3.2 m upper floors)
  mid_n     4 | 5 | 6: middle setback shaft storeys above the podium
  top_n     2 | 3: penthouse tower storeys above the middle shaft
  plan      'U' | 'H' | 'T' | 'L_left' | 'L_right' | 'C_right'
  depth_f   fraction of total lot depth occupied by the front podium bar (0.36..0.58)
  court_f   fraction of total lot width opened as light court / side court (0.18..0.44)
  cap       'step' | 'hip' | 'pyramid' | 'dome'
  piers     True | False: vertical limestone Art Deco piers rising into stepped parapet pinnacles
  arch      True | False: tall arched lobby windows in the ground floor
  wall      coastal masonry ('BuffBrick', 'Render', 'Cream', 'RevealStone', 'TrimWhite' tinted blue-grey/sage)
  base      ground-storey masonry ('Dressed', 'Greystone')
  roof_mat  penthouse roof / crown material ('TinGreen', 'SlateDark', 'SlateGreen')
  corner    False | True: LeftCorner (left street gets full portal, vertical piers & fenestration; no lettering)
"""
import math
from lt_kit import Mesh, Wall, finish, wall, style, wbox, lbox, E
from lt_shapes import cornice_roof, pavilion_roof, dome
from lt_designs.cottage import cupola, nearest

SET = 1.0                     # main front wall 1.00 m inside lot front (Rule 29; cornice 0.30 -> front_m ~0.64 m)
SM = 1.0                      # side yards
G = 4.6                       # ground lobby storey
F = 3.2                       # standard residential storey
DEEP = .55                    # podium cornice depth
DEEP2 = .45                   # setback shaft cornice depth
STONE = "Dressed"
FRAME = "Iron"
DEFAULT = dict(base_n=5, mid_n=5, top_n=2, plan="U", depth_f=.50, court_f=.28, cap="hip", piers=True, arch=True,
               wall="BuffBrick", base="Dressed", roof_mat="TinGreen", door="Iron", lites="6", corner=False)


def _rows(n, z0=0.0, arched=False, is_ground=False):
    wins = []
    z = z0
    for j in range(n):
        if is_ground and j == 0:
            wins.append((1.4, z + .9, z + 3.8, "bay") if arched else (1.2, .9 + z, z + 3.4))
            z += G
        else:
            wins.append((1.05, z + .85, z + 2.55))
            z += F
    return wins, z


def _deco_piers(m, A, B, bays, z0, z1, lod, mat=STONE, finial=.6):
    """LOD0/1 vertical Art Deco limestone piers between window bays, rising `finial` past the cornice."""
    if lod == 2 or len(bays) < 2:
        return
    w = Wall(A, B)
    us = sorted(w.u_of(c) for c in bays)
    mids = [(a + b) / 2 for a, b in zip(us, us[1:]) if b - a >= 2.2]
    pts = [0.42] + mids + [w.L - 0.42]
    pw = .20
    proj = .14
    for u in pts:
        lbox(m, w, u - pw, u + pw, z0, z1 + finial, E, proj, mat)
        if lod == 0 and finial > .2:
            lbox(m, w, u - pw * .65, u + pw * .65, z1 + finial + E, z1 + finial + .32, E, proj * .75, mat)


def _spandrels(m, A, B, bays, wins, lod, belts=(), mat="Greystone"):
    """LOD0 recessed Art Deco spandrel panels & fluted mullions between stacked window rows."""
    if lod != 0 or len(wins) < 2:
        return
    w = Wall(A, B)
    us = [w.u_of(c) for c in bays]
    for prev, nxt in zip(wins[:-1], wins[1:]):
        z0, z1 = prev[2] + .22, nxt[1] - .22
        if z1 - z0 < .25 or any(z0 - .18 < b < z1 + .18 for b in belts):
            continue
        hw = min(prev[0], nxt[0]) * .44
        for u in us:
            lbox(m, w, u - hw, u + hw, z0, z1, E, .045, mat)
            lbox(m, w, u - .06, u + .06, z0 + .06, z1 - .06, .045 + E, .075, STONE)


def _portal(m, cx, yw, lod, side="front", mat=STONE):
    """Stepped Art Deco limestone entrance surround at street grade."""
    if lod == 2:
        return
    if side == "front":
        for s in (-1, 1):
            wbox(m, cx + s * .82 - .22, cx + s * .82 + .22, yw - .24, yw - E, 0.0, 3.9, mat, ("y+", "z-"))
            if lod == 0:
                wbox(m, cx + s * 1.12 - .14, cx + s * 1.12 + .14, yw - .14, yw - E, 0.0, 3.4, mat, ("y+", "z-"))
        wbox(m, cx - 1.15, cx + 1.15, yw - .28, yw - E, 3.85, 4.35, mat, ("y+",))
        if lod == 0:
            wbox(m, cx - .80, cx + .80, yw - .22, yw - E, 4.35 + E, 4.65, mat, ("y+",))
    else:
        xw = cx
        for s in (-1, 1):
            wbox(m, xw - .24, xw - E, yw + s * .82 - .22, yw + s * .82 + .22, 0.0, 3.9, mat, ("x+", "z-"))
        wbox(m, xw - .28, xw - E, yw - 1.15, yw + 1.15, 3.85, 4.35, mat, ("x+",))


def _bays(a, b, pier=1.55, step=3.3, min_p=2.45):
    """Evenly spaced bays with pitch strictly in [min_p, 3.55] (Rule 2 safe for 1.05..1.40 m windows)."""
    L = b - a
    if L < 2 * 1.15 + min_p:
        return [(a + b) / 2]
    for k in range(1, 30):
        for p in (pier, 1.45, 1.65, 1.35, 1.75, 1.25, 1.85, 1.15, 1.95, 2.1):
            s = (L - 2 * p) / k
            if min_p <= s <= 3.55:
                return [a + p + s * i for i in range(k + 1)]
    k = max(1, round((L - 2 * pier) / 3.0))
    return [a + pier + (L - 2 * pier) * i / k for i in range(k + 1)]


def build(lod, W=4, D=5, **variant):
    for k in ("lots", "palette"):
        variant.pop(k, None)
    v = dict(DEFAULT, **variant)
    corner = v["corner"]
    plan = v["plan"]
    wm = v["wall"]
    bm = v["base"]
    rm = v["roof_mat"]
    bn, mn, tn = v["base_n"], v["mid_n"], v["top_n"]
    if W >= 5:
        mn += 1
    XL, XH = -4.0 * W + SM, 4.0 * W - SM
    yF = -4.0 * D + SET
    end = 4.0 * D - .6
    totW = XH - XL
    totD = end - yF

    pwin, zP = _rows(bn, 0.0, arched=v["arch"], is_ground=True)
    pmats = [(0.0, G, bm), (G, zP, wm)]
    pbelts = (G,) + tuple(G + F * j for j in range(2, bn, 2))
    pst = style(zP, pmats, pwin, belts=pbelts, plinth=(.55, .05, "Greystone"), corners=False, frieze=.35, belt_mat=STONE)

    ftrim = dict(door=v["door"], lites=v["lites"], masonry=STONE, reveal=wm, frame=FRAME,
                 arch=v["arch"], glazed=True, lean="bare" if lod else True)
    strim = dict(ftrim, arch=False, simple=bool(lod))
    ctrim = dict(ftrim, arch=v["arch"], simple=bool(lod)) if corner else strim
    waive_s = {"balance": "1920s Deco facade rhythm", "corners": "pier-framed Deco corner bay"}
    m, g = Mesh(), Mesh()

    df = v["depth_f"]
    cf = v["court_f"]

    # Front block depth yM (always >= 11.4 m so the middle setback shaft sits solidly inside its footprint)
    if plan == "H":
        y1 = yF + max(11.6, totD * df)
        y2 = end - max(9.0, totD * (0.68 - df))
        if y2 - y1 < 5.0:
            y2 = y1 + 5.0
        side_c = max(4.2, totW * cf)
        sw = totW - 2 * side_c
        sx_a, sx_b = -sw / 2, sw / 2
        yM = y1
    elif plan == "C_right":
        y1 = yF + max(11.6, totD * df)
        y2 = end - max(9.4, totD * .32)
        if y2 - y1 < 5.2:
            y2 = y1 + 5.2
        court_w = max(5.0, totW * cf)
        cx_in = XH - court_w                              # left connecting wing spans XL..cx_in
        yM = y1
    elif plan in ("L_left", "L_right"):
        yM = yF + max(12.2, totD * df)
        court_w = max(5.4, totW * cf)
        lx_split = (XH - court_w) if plan == "L_left" else (XL + court_w)
    elif plan == "T":
        yM = yF + max(12.6, totD * df)
        side_c = max(3.8, totW * cf)
        tw = totW - 2 * side_c
        tx_a, tx_b = -tw / 2, tw / 2
    else:                                                 # 'U' rear courtyard
        yM = yF + max(11.6, totD * df)
        court_w = max(5.0, totW * cf)
        ww = (totW - court_w) / 2
        uw_l, uw_r = XL + ww, XH - ww

    # ---- Front wall of podium (always XL..XH at yF = 1.00 m)
    fb = _bays(XL, XH, pier=1.65, step=3.2)
    dc = nearest(fb, 0.0)
    wall(m, g, pst, (XL, yF), (XH, yF), "x", "x", fb, lod, door=(dc, 1.5, 3.6), trim=ftrim,
         waive=waive_s, plinth_cuts=[(dc - 1.2, dc + 1.2)])
    _portal(m, dc, yF, lod, "front", STONE)
    _spandrels(m, (XL, yF), (XH, yF), fb, pwin, lod, pbelts)
    if v["piers"]:
        _deco_piers(m, (XL, yF), (XH, yF), fb, G + .15, zP + DEEP, lod, STONE, .55)

    # ---- Side & rear podium walls + cornice roofs by plan type
    zP_r = zP - .015
    if plan == "U":
        sb = _bays(yF, end, pier=1.65, step=3.2)
        if corner:
            sdc = nearest(sb, (yF + yM) / 2)
            wall(m, g, pst, (XL, end), (XL, yF), "x", "x", sb, lod, door=(sdc, 1.5, 3.6), trim=ctrim,
                 waive=waive_s, plinth_cuts=[(sdc - 1.2, sdc + 1.2)])
            _portal(m, XL, sdc, lod, "left", STONE)
            if v["piers"]:
                _deco_piers(m, (XL, end), (XL, yF), sb, G + .15, zP + DEEP, lod, STONE, .55)
        else:
            wall(m, g, pst, (XL, end), (XL, yF), "x", "x", sb, lod, trim=strim, waive=waive_s)
        wall(m, g, pst, (XH, yF), (XH, end), "x", "x", sb, lod, trim=strim, waive=waive_s)
        cb_m = _bays(uw_l, uw_r, pier=1.45, step=3.1)
        wall(m, g, pst, (uw_r, yM), (uw_l, yM), "c", "c", cb_m, lod, trim=strim, waive=waive_s)
        cy = _bays(yM, end, pier=1.45, step=3.1)
        wall(m, g, pst, (uw_l, yM), (uw_l, end), "c", "x", cy, lod, trim=strim, waive=waive_s)
        wall(m, g, pst, (uw_r, end), (uw_r, yM), "x", "c", cy, lod, trim=strim, waive=waive_s)
        wall(m, g, pst, (uw_l, end), (XL, end), "x", "x", _bays(XL, uw_l, 1.45, 3.1), lod, trim=strim, waive=waive_s)
        wall(m, g, pst, (XH, end), (uw_r, end), "x", "x", _bays(uw_r, XH, 1.45, 3.1), lod, trim=strim, waive=waive_s)
        cornice_roof(m, XL - .3, XH + .3, yF - .3, yM + .2, zP, lod, deep=DEEP, side=STONE, ends=STONE)
        cornice_roof(m, XL - .3, uw_l + .25, yM + .2 + E, end + .3, zP_r, lod, deep=DEEP, side=STONE, ends=STONE, front=False)
        cornice_roof(m, uw_r - .25, XH + .3, yM + .2 + E, end + .3, zP_r, lod, deep=DEEP, side=STONE, ends=STONE, front=False)
    elif plan == "H":
        sf = _bays(yF, y1, pier=1.6, step=3.2)
        if corner:
            sdc = nearest(sf, (yF + y1) / 2)
            wall(m, g, pst, (XL, y1), (XL, yF), "x", "x", sf, lod, door=(sdc, 1.5, 3.6), trim=ctrim,
                 waive=waive_s, plinth_cuts=[(sdc - 1.2, sdc + 1.2)])
            _portal(m, XL, sdc, lod, "left", STONE)
            if v["piers"]:
                _deco_piers(m, (XL, y1), (XL, yF), sf, G + .15, zP + DEEP, lod, STONE, .55)
        else:
            wall(m, g, pst, (XL, y1), (XL, yF), "x", "x", sf, lod, trim=strim, waive=waive_s)
        wall(m, g, pst, (XH, yF), (XH, y1), "x", "x", sf, lod, trim=strim, waive=waive_s)
        wall(m, g, pst, (sx_a, y1), (XL, y1), "c", "x", _bays(XL, sx_a, 1.35, 3.0), lod, trim=strim, waive=waive_s)
        wall(m, g, pst, (XH, y1), (sx_b, y1), "x", "c", _bays(sx_b, XH, 1.35, 3.0), lod, trim=strim, waive=waive_s)
        sy_h = _bays(y1, y2, pier=1.35, step=3.0)
        wall(m, g, pst, (sx_a, y2), (sx_a, y1), "c", "c", sy_h, lod, trim=strim, waive=waive_s)
        wall(m, g, pst, (sx_b, y1), (sx_b, y2), "c", "c", sy_h, lod, trim=strim, waive=waive_s)
        wall(m, g, pst, (XL, y2), (sx_a, y2), "x", "c", _bays(XL, sx_a, 1.35, 3.0), lod, trim=strim, waive=waive_s)
        wall(m, g, pst, (sx_b, y2), (XH, y2), "c", "x", _bays(sx_b, XH, 1.35, 3.0), lod, trim=strim, waive=waive_s)
        sr = _bays(y2, end, pier=1.5, step=3.1)
        wall(m, g, pst, (XL, end), (XL, y2), "x", "x", sr, lod, trim=ctrim if corner else strim, waive=waive_s)
        wall(m, g, pst, (XH, y2), (XH, end), "x", "x", sr, lod, trim=strim, waive=waive_s)
        wall(m, g, pst, (XH, end), (XL, end), "x", "x", _bays(XL, XH, 1.6, 3.2), lod, trim=strim, waive=waive_s)
        cornice_roof(m, XL - .3, XH + .3, yF - .3, y1 + .2, zP, lod, deep=DEEP, side=STONE, ends=STONE)
        cornice_roof(m, sx_a - .25, sx_b + .25, y1 + .2 + E, y2 - .2 - E, zP_r, lod, deep=DEEP, side=STONE, ends=STONE, front=False)
        cornice_roof(m, XL - .3, XH + .3, y2 - .2, end + .3, zP, lod, deep=DEEP, side=STONE, ends=STONE, front=False)
    elif plan == "C_right":
        # Full left street wall yF..end + front bar + rear bar + open right-side garden court
        sb = _bays(yF, end, pier=1.65, step=3.2)
        if corner:
            sdc = nearest(sb, (yF + y1) / 2)
            wall(m, g, pst, (XL, end), (XL, yF), "x", "x", sb, lod, door=(sdc, 1.5, 3.6), trim=ctrim,
                 waive=waive_s, plinth_cuts=[(sdc - 1.2, sdc + 1.2)])
            _portal(m, XL, sdc, lod, "left", STONE)
            if v["piers"]:
                _deco_piers(m, (XL, end), (XL, yF), sb, G + .15, zP + DEEP, lod, STONE, .55)
        else:
            wall(m, g, pst, (XL, end), (XL, yF), "x", "x", sb, lod, trim=strim, waive=waive_s)
        wall(m, g, pst, (XH, yF), (XH, y1), "x", "x", _bays(yF, y1, 1.5, 3.1), lod, trim=strim, waive=waive_s)
        wall(m, g, pst, (XH, y1), (cx_in, y1), "x", "c", _bays(cx_in, XH, 1.35, 3.0), lod, trim=strim, waive=waive_s)
        wall(m, g, pst, (cx_in, y1), (cx_in, y2), "c", "c", _bays(y1, y2, 1.35, 3.0), lod, trim=strim, waive=waive_s)
        wall(m, g, pst, (cx_in, y2), (XH, y2), "c", "x", _bays(cx_in, XH, 1.35, 3.0), lod, trim=strim, waive=waive_s)
        wall(m, g, pst, (XH, y2), (XH, end), "x", "x", _bays(y2, end, 1.5, 3.1), lod, trim=strim, waive=waive_s)
        wall(m, g, pst, (XH, end), (XL, end), "x", "x", _bays(XL, XH, 1.6, 3.2), lod, trim=strim, waive=waive_s)
        cornice_roof(m, XL - .3, XH + .3, yF - .3, y1 + .2, zP, lod, deep=DEEP, side=STONE, ends=STONE)
        cornice_roof(m, XL - .3, cx_in + .25, y1 + .2 + E, y2 - .2 - E, zP_r, lod, deep=DEEP, side=STONE, ends=STONE, front=False)
        cornice_roof(m, XL - .3, XH + .3, y2 - .2, end + .3, zP, lod, deep=DEEP, side=STONE, ends=STONE, front=False)
    elif plan == "L_left":
        # Full front bar + wide left-street wing yF..end, open right-rear court
        sb = _bays(yF, end, pier=1.65, step=3.2)
        if corner:
            sdc = nearest(sb, (yF + yM) / 2)
            wall(m, g, pst, (XL, end), (XL, yF), "x", "x", sb, lod, door=(sdc, 1.5, 3.6), trim=ctrim,
                 waive=waive_s, plinth_cuts=[(sdc - 1.2, sdc + 1.2)])
            _portal(m, XL, sdc, lod, "left", STONE)
            if v["piers"]:
                _deco_piers(m, (XL, end), (XL, yF), sb, G + .15, zP + DEEP, lod, STONE, .55)
        else:
            wall(m, g, pst, (XL, end), (XL, yF), "x", "x", sb, lod, trim=strim, waive=waive_s)
        wall(m, g, pst, (XH, yF), (XH, yM), "x", "x", _bays(yF, yM, 1.5, 3.1), lod, trim=strim, waive=waive_s)
        wall(m, g, pst, (XH, yM), (lx_split, yM), "x", "c", _bays(lx_split, XH, 1.35, 3.0), lod, trim=strim, waive=waive_s)
        wall(m, g, pst, (lx_split, yM), (lx_split, end), "c", "x", _bays(yM, end, 1.45, 3.1), lod, trim=strim, waive=waive_s)
        wall(m, g, pst, (lx_split, end), (XL, end), "x", "x", _bays(XL, lx_split, 1.5, 3.1), lod, trim=strim, waive=waive_s)
        cornice_roof(m, XL - .3, XH + .3, yF - .3, yM + .2, zP, lod, deep=DEEP, side=STONE, ends=STONE)
        cornice_roof(m, XL - .3, lx_split + .25, yM + .2 + E, end + .3, zP_r, lod, deep=DEEP, side=STONE, ends=STONE, front=False)
    elif plan == "L_right":
        # Full front bar + wide right rear wing yF..end, open left-rear court
        sf = _bays(yF, yM, pier=1.55, step=3.2)
        wall(m, g, pst, (XL, yM), (XL, yF), "x", "x", sf, lod, trim=strim, waive=waive_s)
        wall(m, g, pst, (XH, yF), (XH, end), "x", "x", _bays(yF, end, 1.65, 3.2), lod, trim=strim, waive=waive_s)
        wall(m, g, pst, (lx_split, yM), (XL, yM), "c", "x", _bays(XL, lx_split, 1.35, 3.0), lod, trim=strim, waive=waive_s)
        wall(m, g, pst, (lx_split, end), (lx_split, yM), "x", "c", _bays(yM, end, 1.45, 3.1), lod, trim=strim, waive=waive_s)
        wall(m, g, pst, (XH, end), (lx_split, end), "x", "x", _bays(lx_split, XH, 1.5, 3.1), lod, trim=strim, waive=waive_s)
        cornice_roof(m, XL - .3, XH + .3, yF - .3, yM + .2, zP, lod, deep=DEEP, side=STONE, ends=STONE)
        cornice_roof(m, lx_split - .25, XH + .3, yM + .2 + E, end + .3, zP_r, lod, deep=DEEP, side=STONE, ends=STONE, front=False)
    else:                                                 # 'T' plan: broad front bar + centered rear wing
        sf = _bays(yF, yM, pier=1.6, step=3.2)
        if corner:
            sdc = nearest(sf, (yF + yM) / 2)
            wall(m, g, pst, (XL, yM), (XL, yF), "x", "x", sf, lod, door=(sdc, 1.5, 3.6), trim=ctrim,
                 waive=waive_s, plinth_cuts=[(sdc - 1.2, sdc + 1.2)])
            _portal(m, XL, sdc, lod, "left", STONE)
            if v["piers"]:
                _deco_piers(m, (XL, yM), (XL, yF), sf, G + .15, zP + DEEP, lod, STONE, .55)
        else:
            wall(m, g, pst, (XL, yM), (XL, yF), "x", "x", sf, lod, trim=strim, waive=waive_s)
        wall(m, g, pst, (XH, yF), (XH, yM), "x", "x", sf, lod, trim=strim, waive=waive_s)
        wall(m, g, pst, (tx_a, yM), (XL, yM), "c", "x", _bays(XL, tx_a, 1.25, 2.8), lod, trim=strim, waive=waive_s)
        wall(m, g, pst, (XH, yM), (tx_b, yM), "x", "c", _bays(tx_b, XH, 1.25, 2.8), lod, trim=strim, waive=waive_s)
        sy_t = _bays(yM, end, pier=1.45, step=3.1)
        wall(m, g, pst, (tx_a, end), (tx_a, yM), "x", "c", sy_t, lod, trim=strim, waive=waive_s)
        wall(m, g, pst, (tx_b, yM), (tx_b, end), "c", "x", sy_t, lod, trim=strim, waive=waive_s)
        wall(m, g, pst, (tx_b, end), (tx_a, end), "x", "x", _bays(tx_a, tx_b, 1.45, 3.1), lod, trim=strim, waive=waive_s)
        cornice_roof(m, XL - .3, XH + .3, yF - .3, yM + .2, zP, lod, deep=DEEP, side=STONE, ends=STONE)
        cornice_roof(m, tx_a - .25, tx_b + .25, yM + .2 + E, end + .3, zP_r, lod, deep=DEEP, side=STONE, ends=STONE, front=False)

    # ---- Middle Setback Shaft (recessed cleanly inside front podium roof so it adds 0 extra outline eaves)
    zM0 = zP + DEEP
    step_x = min(3.0, totW * .14)
    step_y = 1.9
    mx0, mx1 = XL + step_x, XH - step_x
    my0, my1 = yF + step_y, yM - 1.5
    mwin, zM = _rows(mn, zM0, arched=False, is_ground=False)
    mbelts = tuple(zM0 + F * j for j in range(3, mn, 3))
    mst = style(zM, [(zM0, zM, wm)], mwin, belts=mbelts, plinth=None, corners=False, frieze=.32, belt_mat=STONE)
    mtrim_f = dict(ftrim, arch=False)
    mtrim_s = dict(strim, arch=False)
    mfb = _bays(mx0, mx1, pier=1.45, step=3.1)
    msb = _bays(my0, my1, pier=1.45, step=3.1)
    wall(m, g, mst, (mx0, my0), (mx1, my0), "x", "x", mfb, lod, z0=zM0, trim=mtrim_f, waive=waive_s)
    wall(m, g, mst, (mx1, my1), (mx0, my1), "x", "x", mfb, lod, z0=zM0, trim=mtrim_s, waive=waive_s)
    wall(m, g, mst, (mx0, my1), (mx0, my0), "x", "x", msb, lod, z0=zM0, trim=mtrim_f if corner else mtrim_s, waive=waive_s)
    wall(m, g, mst, (mx1, my0), (mx1, my1), "x", "x", msb, lod, z0=zM0, trim=mtrim_s, waive=waive_s)
    _spandrels(m, (mx0, my0), (mx1, my0), mfb, mwin, lod, mbelts)
    _spandrels(m, (mx1, my1), (mx0, my1), mfb, mwin, lod, mbelts)
    _spandrels(m, (mx0, my1), (mx0, my0), msb, mwin, lod, mbelts)
    _spandrels(m, (mx1, my0), (mx1, my1), msb, mwin, lod, mbelts)
    if v["piers"]:
        _deco_piers(m, (mx0, my0), (mx1, my0), mfb, zM0 + .2, zM + DEEP2, lod, STONE, .75)
        if corner:
            _deco_piers(m, (mx0, my1), (mx0, my0), msb, zM0 + .2, zM + DEEP2, lod, STONE, .75)
    cornice_roof(m, mx0 - .25, mx1 + .25, my0 - .25, my1 + .25, zM, lod, deep=DEEP2, side=STONE, ends=STONE)

    # ---- Penthouse Crown (second setback, strictly inside middle shaft roof)
    zT0 = zM + DEEP2
    tx_in = min(2.6, (mx1 - mx0) * .20)
    ty_in = min(1.5, (my1 - my0) * .16)
    px0, px1 = mx0 + tx_in, mx1 - tx_in
    py0, py1 = my0 + ty_in, my1 - ty_in
    if px1 - px0 >= 6.0 and py1 - py0 >= 5.0:
        twin_r, zT = _rows(tn, zT0, arched=False, is_ground=False)
        tst = style(zT, [(zT0, zT, wm)], twin_r, belts=(), plinth=None, corners=False, frieze=.30, belt_mat=STONE)
        pfb = _bays(px0, px1, pier=1.35, step=3.0)
        psb = _bays(py0, py1, pier=1.35, step=3.0)
        wall(m, g, tst, (px0, py0), (px1, py0), "x", "x", pfb, lod, z0=zT0, trim=mtrim_s, waive=waive_s)
        wall(m, g, tst, (px1, py1), (px0, py1), "x", "x", pfb, lod, z0=zT0, trim=mtrim_s, waive=waive_s)
        wall(m, g, tst, (px0, py1), (px0, py0), "x", "x", psb, lod, z0=zT0, trim=mtrim_s, waive=waive_s)
        wall(m, g, tst, (px1, py0), (px1, py1), "x", "x", psb, lod, z0=zT0, trim=mtrim_s, waive=waive_s)
        cx, cy = (px0 + px1) / 2, (py0 + py1) / 2
        cap = v["cap"]
        if cap == "hip":
            rise = min(px1 - px0, py1 - py0) * .55
            zr = pavilion_roof(m, px0 - .25, px1 + .25, py0 - .25, py1 + .25, zT, rise, lod, rm, finial=False)
            cupola(m, cx, cy, zr + .12, lod, STONE, rm, FRAME, a=1.0, sink=1.0 * .9 + .3, h=1.8)
        elif cap == "pyramid":
            cornice_roof(m, px0 - .2, px1 + .2, py0 - .2, py1 + .2, zT, lod, deep=.35, side=STONE, ends=STONE)
            half = min(px1 - px0, py1 - py0) / 2 - .5
            pavilion_roof(m, cx - half, cx + half, cy - half, cy + half, zT + .35, half * 1.45, lod, rm, finial=True)
        elif cap == "dome":
            cornice_roof(m, px0 - .2, px1 + .2, py0 - .2, py1 + .2, zT, lod, deep=.40, side=STONE, ends=STONE)
            r = min(px1 - px0, py1 - py0) / 2 - .9
            zc = dome(m, g, cx, cy, max(1.8, r), zT + .40, lod, rm, STONE, drum=1.6)
            cupola(m, cx, cy, zc + .02, lod, STONE, rm, FRAME, a=.75, sink=.05, h=1.4)
        else:                                             # 'step': classic Art Deco stepped ziggurat crown
            cornice_roof(m, px0 - .22, px1 + .22, py0 - .22, py1 + .22, zT, lod, deep=.42, side=STONE, ends=STONE)
            z1 = zT + .42
            sx_ = min(5.0, max(1.8, (px1 - px0) * .28))
            sy_ = min(4.2, max(1.6, (py1 - py0) * .28))
            wbox(m, cx - sx_, cx + sx_, cy - sy_, cy + sy_, z1 + E, z1 + 2.4, STONE, ("z-",))
            wbox(m, cx - sx_ - .12, cx + sx_ + .12, cy - sy_ - .12, cy + sy_ + .12, z1 + 2.4 + E, z1 + 2.75, rm, ("z-",))
            sx2, sy2 = sx_ * .58, sy_ * .58
            wbox(m, cx - sx2, cx + sx2, cy - sy2, cy + sy2, z1 + 2.75 + E, z1 + 4.4, STONE, ("z-",))
            pavilion_roof(m, cx - sx2 - .12, cx + sx2 + .12, cy - sy2 - .12, cy + sy2 + .12, z1 + 4.4 + E, 1.6, lod, rm, finial=False)

    finish(m, g)
