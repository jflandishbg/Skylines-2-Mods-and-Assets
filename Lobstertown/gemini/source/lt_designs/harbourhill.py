"""Lobstertown Harbour Hill (ZH1, the author 2026-11-18): the dense hillside tenements of Portland and Fall River.

Narrow, tall brick and shingle flat blocks, 4-5 storeys, shoulder to shoulder on 8 m lots (a 2-wide lot is a double
block with two stair halls), a street door at grade, stacked canted bays or a slate mansard with dormers. Behind each
block the tiers of wooden porches (rear_decks) climb the back wall above a one-storey wash-house and yard building
that fills the lot to 0.6 m off the rear line (rule 17).

    build(lod, W=1, D=4, **variant)      W = lot width in cells (1 or 2), D = lot depth in cells (4..6)

Variant keys:
  storeys   4 | 5 (ground floor included)
  roof      'flat' (deep cornice) | 'mansard' (slate, dormers both slopes)
  cornice   flat roofs: 'corbel' (brick corbel table) | 'bracket' (painted bracketed frieze)
  upper     None | 'bays' (canted bays on every flat floor, at the outer bays of a 1-wide lot, the 2nd and 5th of a 2-wide)
  hood      None | 'cap' | 'pediment'   window heads
  base      None | 'granite' (a dressed granite ground storey)
  quoins    True: dressed quoins up both ends of the front
  corner    False | True: a LeftCorner block (the street side is the left; windows down the side street, a belfry)
  wall, back_mat, roof_mat, door, lites
"""
import math
from lt_kit import Mesh, Wall, finish, wall, style, gable_wall, gable_roof, party, wbox, lbox, bay, E, TRIM, chimney
from lt_shapes import slab, dormer, cornice_roof
from nf_kit import mansard_row
from lt_designs.shore_row import rear_decks
from lt_designs.cannery import corbels, _brick_dormer_side
from lt_designs.mainst import (lz, floors, piece_top, plan, tower, G, DEEP, MANS_RUN, MANS_RISE, STREET, CI)

DEFAULT = dict(storeys=4, roof="mansard", cornice="corbel", upper=None, hood=None, base=None, quoins=False,
               corner=False, back=(1,), wall="Brick074", back_mat=None, roof_mat="Slate", door="Green", lites="2")
DOOR = (1.1, 2.95)


def bay_xs(a, b, W):
    n = 3 * W
    return [a + 1.4 + (b - a - 2.8) * j / (n - 1) for j in range(n)]


def build(lod, W=1, D=4, **variant):
    variant.pop("palette", None)
    v = dict(DEFAULT, **variant)
    X = 4.0 * W - .01
    n, kind, corner = v["storeys"], v["roof"], v["corner"]
    flat, mans = kind == "flat", kind == "mansard"
    wm = v["wall"]
    bm = v["back_mat"] or wm
    win = floors(n, False)
    last = win[-1][2]
    top = last + (1.15 if flat else .6)
    XL = -X + CI if corner else -X
    xm = (XL + X) / 2
    yF, yR, pieces = plan(D, v["back"])
    granite = v["base"] == "granite"
    ftrim = dict(door=v["door"], lites=v["lites"], masonry="Dressed", reveal=wm, lean=True)
    if v["hood"]:
        ftrim["hood"] = v["hood"]
    rtrim = dict(door=v["door"], lites=v["lites"], masonry="Dressed", reveal=bm, lean=True)
    m, g = Mesh(), Mesh()
    sx = "x" if corner else "-"

    # ---- the street front: a door at grade for each stair hall, the flats above
    mats = [(0.0, G, "Greystone"), (G, top, wm)] if granite and wm != "Greystone" else [(0.0, top, wm)]
    fwin = [(1.0, 1.0, 3.0)] + win
    st = style(top, mats, fwin, belts=(G,), plinth=(.45, .05, "Greystone"), corners=False, frieze=None,
               belt_mat="Dressed")
    bays = bay_xs(XL, X, W)
    dbays = [bays[1]] if W == 1 else [bays[1], bays[4]]
    fwall = Wall((XL, yF), (X, yF))
    u = fwall.u_of
    holes = [(u(c) - .55, u(c) + .55, 0.0, DOOR[1], "door") for c in dbays]
    omit = [(c, 0) for c in dbays]
    waive = dict(STREET, balance="a stair-hall door at grade, as on every New England tenement")
    ubays = [bays[0], bays[2]] if W == 1 else [bays[1], bays[4]]
    if v["upper"] == "bays":
        omit += [(c, f) for c in ubays for f in range(1, len(fwin))]
        waive["glass"] = "the canted bays carry the glass of their bays on every floor of flats"
        waive["rhythm"] = "canted bays fill their bays on every floor of flats"
    if corner:
        waive["corners"] = "the corner block's window runs to a corner pier"
    fw = wall(m, g, st, (XL, yF), (X, yF), sx, "-", bays, lod, trim=ftrim, waive=waive, omit=omit, holes=holes)
    if lod < 2 and v["quoins"] and lod == 0:
        z, k = G + .12, 0
        while z + .4 < top - .7:
            wq = .55 if k % 2 == 0 else .35
            for a0, a1 in ((0.0, wq), (fw.L - wq, fw.L)):
                lbox(m, fw, a0 + E, a1 - E, z, z + .38, E, .05, "Dressed")
            z += .42
            k += 1
    if v["upper"] == "bays":
        z0, z1 = G + .2, last + .4
        for c in ubays:
            bay(m, g, c, yF, 1.4, .5, z0, z1, lod, wm, [(b, t) for _, b, t in win], ftrim, v["roof_mat"], v["lites"])
            a = .7 + .5
            m.facing([(c - a, yF, z0), (c - .7, yF - .5, z0), (c + .7, yF - .5, z0), (c + a, yF, z0)], (0, 0, -1),
                     "Dressed")

    # ---- the roof of the main block
    z1 = top + DEEP
    if flat:
        bracket = v["cornice"] == "bracket"
        side = v["door"] if bracket else wm
        x0 = XL - .33 if corner else XL + E
        cornice_roof(m, x0, X - E, yF - .4, yR + .25, top, lod, deep=DEEP, side=side, ends=side if corner else wm)
        if corner and lod < 2:
            wbox(m, x0 - .06, x0 - E, yF - .4 + E, yR + .25 - E, z1 - .14, z1 + .04, side, ("x+",))
        if not bracket:
            corbels(m, fw, top, lod, wm)
        elif lod < 2:
            lbox(m, fw, .2, fw.L - .2, top - .45, top - E, E, .06, side)
            if lod == 0:
                c = .3
                while c + .1 < fw.L - .3:
                    lbox(m, fw, c, c + .1, top - .6, top - .45 - E, E, .05, side)
                    c += .25
                for i in range(6 * W):
                    cc0 = XL + .5 + (X - XL - 1.0) * i / (6 * W - 1)
                    for cc in (cc0 - .12, cc0 + .12):
                        wbox(m, cc - .05, cc + .05, yF - .38, yF - .06 - E, top - .6, top - E, side, ("y+", "z+"))
        if lod < 2:
            wbox(m, .6, 1.6, yR - 3.2, yR - 2.2, z1, z1 + .55, "Tin", ("z-",))
        party(m, (X, yF), (X, yR), 0.0, top, wm)
        if not corner:
            party(m, (-X, yR), (-X, yF), 0.0, top, wm)
        for k in range(W):
            chimney(m, X - .45 - 8.0 * k, yF + 4.0, .3, .45, z1 - .1, z1 + 1.5, lod)
        chimney(m, XL + .6, yR - 3.0, .3, .45, z1 - .1, z1 + 1.3, lod)
    else:
        zt_ = top + MANS_RISE
        if corner:
            party(m, (X, yF), (X, yR), 0.0, top, wm)
            mridge = "x" if (X - XL) >= (yR - yF) else "y"
            mansard_row(m, XL + E, X - E, yF, yR, top, MANS_RISE, MANS_RUN, .8, lod,
                        sides=dict(x0="s", x1="e"), ridge=mridge, steep=v["roof_mat"], deck="TinFlat",
                        roll="Iron", end=wm)
            dtrim = dict(door=v["door"], lites=v["lites"], masonry="Dressed", reveal=wm, lean=True)
            from lt_designs.cannery import mansard_dormer
            for cx in bays:
                mansard_dormer(m, g, cx, yF + .15, 1, top, lod, wm, v["roof_mat"], dtrim, w=1.2)
            for cx in (bays[1:3] if W == 1 else (bays[1], bays[4])):
                mansard_dormer(m, g, cx, yR - .15, -1, top, lod, bm, v["roof_mat"], dict(dtrim, reveal=bm), w=1.2)
            for k in range(W):
                chimney(m, X - .5 - 8.0 * k, yF + MANS_RUN + 3.0, .35, .45, zt_ - .1, zt_ + 1.4, lod)
        else:
            for xx, d in ((X, 1), (-X, -1)):
                m.facing([(xx, yF, 0.0), (xx, yR, 0.0), (xx, yR, top - .03), (xx, yR - MANS_RUN, zt_ - .03),
                          (xx, yF + MANS_RUN, zt_ - .03), (xx, yF, top - .03)], (d, 0, 0), wm)
            prof = [(yF - .45, top - .15), (yF, top), (yF + MANS_RUN, zt_), (yR - MANS_RUN, zt_), (yR, top),
                    (yR + .4, top - .13)]
            slab(m, prof, -X + E, X - E, lambda a, q, z: (a, q, z), lod, v["roof_mat"], end=v["roof_mat"],
                 what="mansard roof")
            if lod < 2:
                for yy in (yF + MANS_RUN + .05, yR - MANS_RUN - .1):
                    wbox(m, -X + .2, X - .2, yy, yy + .05, zt_ + .16 + E, zt_ + .5, "Iron", ("z-",))
            th, k = .16, MANS_RISE / MANS_RUN
            fr = lambda o_: top + th + (-o_ - yF) * k
            rr = lambda o_: top + th + (yR - o_) * k
            dtrim = dict(door=v["door"], lites=v["lites"])
            for cx in bays:
                dormer(m, g, lambda o_, t, z: (t, -o_, z), fr, -(yF + .25), cx, 1.2, lod, wm, v["roof_mat"], dtrim,
                       rise=.5, height=1.5, lites=v["lites"])
            for cx in (bays[1:3] if W == 1 else (bays[1], bays[4])):
                dormer(m, g, lambda o_, t, z: (t, o_, z), rr, yR - .25, cx, 1.2, lod, bm, v["roof_mat"], dtrim,
                       rise=.5, height=1.4, lites=v["lites"])
            for k in range(W):
                chimney(m, X - .5 - 8.0 * k, yF + MANS_RUN + 3.0, .35, .45, zt_ - .1, zt_ + 1.4, lod)
                chimney(m, -X + .5 + 8.0 * k, yR - MANS_RUN - 2.5, .35, .45, zt_ - .1, zt_ + 1.2, lod)

    if corner and flat:                             # a belfry over a flat-roof corner, rising out of the roof
        a = 1.45
        tower(m, g, lod, XL + a - .05, yF + a - .05, a, 8, top + DEEP - .1, top + 5.35, 4.6, wm, v["roof_mat"], dict(ftrim),
              [(top + 3.2, top + 4.8, tuple(range(8)))], "Dressed")

    # ---- the side street (corner blocks): windows down every floor
    if corner:
        span = yR - yF
        k = max(3, round((span - 2.0) / 2.6))
        ys = [yF + 1.4 + (span - 2.8) * j / (k - 1) for j in range(k)]
        sst = style(top, mats, fwin, belts=(G,), plinth=(.45, .05, "Greystone"), corners=False, frieze=None,
                    belt_mat="Dressed")
        sw_ = wall(m, g, sst, (XL, yR), (XL, yF), "-" if pieces else "x", "x", ys, lod, trim=ftrim,
                   waive=dict(STREET, corners="the side street runs to a corner pier"))
        if flat:
            corbels(m, sw_, top, lod, wm)
        elif mans:
            dtrim = dict(door=v["door"], lites=v["lites"], masonry="Dressed", reveal=wm, lean=True)
            for cy in (ys[::2] if lod == 2 else ys):
                _brick_dormer_side(m, g, XL + .15, cy, top, lod, wm, v["roof_mat"], dtrim, w=1.2)

    # ---- the back of the main block, and the tiers of porches
    rb = bay_xs(XL, X, W)
    rwin = [(1.0, 1.0, 3.0)] + floors(n, False)
    zc = piece_top(pieces[0][0]) + .45 if pieces else 0.0
    rst = style(top, [(0.0, top, bm)], rwin, plinth=None, corners=False, frieze=None)
    if pieces:
        if zc < top - 1.5:
            rw = wall(m, g, rst, (X, yR), (XL, yR), "-", sx, rb, lod, z0=zc, trim=rtrim)
            if flat:
                corbels(m, rw, top, lod, bm)
    else:
        rw = wall(m, g, rst, (X, yR), (XL, yR), "-", sx, rb, lod, door=(rb[1], 1.1, 2.95), trim=rtrim,
                  waive={"balance": "the back door to the service lane"})
        if flat:
            corbels(m, rw, top, lod, bm)
    exposed = [lz(j) for j in range(1, n) if lz(j) > zc + .2]
    if exposed and pieces:
        lv = [(z - .05, z + 2.9 if i + 1 < len(exposed) else z + 1.1) for i, z in enumerate(exposed)]
        for c in ([rb[1]] if W == 1 else [rb[1], rb[4]]):
            rear_decks(m, c - 1.3, c + 1.4, yR, 1.8, lv, lod)

    # ---- the yard building behind: to 0.6 m off the rear line
    for i, (k, ya, yb) in enumerate(pieces):
        h = piece_top(k)
        pst = style(h, [(0.0, h, bm)], [(1.0, 1.2, 3.2)], belts=(), plinth=(.45, .05, "Greystone"),
                    corners=False, frieze=None, belt_mat="Dressed")
        party(m, (X, ya), (X, yb), 0.0, h, bm)
        if corner:
            span = yb - ya
            kk = max(1, round(span / 2.6))
            ys = [ya + span * (j + .5) / kk for j in range(kk)]
            pw = wall(m, g, pst, (XL, yb), (XL, ya), "x", "-", ys, lod, trim=rtrim, door=(ys[len(ys) // 2], 1.1, 2.95),
                      waive={"balance": "a yard door onto the side street"})
            corbels(m, pw, h, lod, bm)
        else:
            party(m, (-X, yb), (-X, ya), 0.0, h, bm)
        ew = wall(m, g, pst, (X, yb), (XL, yb), "-", sx, rb, lod, door=(rb[1], 1.4, 2.95), trim=rtrim,
                  waive={"balance": "the yard door to the service lane"})
        corbels(m, ew, h, lod, bm)
        x0 = XL - .3 if corner else XL + E
        cornice_roof(m, x0, X - E, ya + E, yb + .3, h, lod, deep=.45, side=bm, ends=bm, front=False)
        if lod < 2 and yb - ya > 9:
            s0, s1 = ya + 2.5, min(ya + 6.5, yb - 1.5)
            zz = h + .45
            for cx in ([0.0] if W == 1 else [-4.0, 4.0]):
                wbox(m, cx - 1.6, cx + 1.6, s0, s1, zz, zz + .35, bm, ("z-",))
                g.facing([(cx - 1.5, s0 + .1, zz + .35 + E), (cx + 1.5, s0 + .1, zz + .35 + E),
                          (cx + 1.5, s1 - .1, zz + 1.1), (cx - 1.5, s1 - .1, zz + 1.1)], (0, -1, 1), "Glass")
                m.facing([(cx - 1.5, s1 - .1, zz + .35 + E), (cx + 1.5, s1 - .1, zz + .35 + E),
                          (cx + 1.5, s1 - .1, zz + 1.1), (cx - 1.5, s1 - .1, zz + 1.1)], (0, 1, 0), "Iron")
                for xx, d in ((cx - 1.5, -1), (cx + 1.5, 1)):
                    m.facing([(xx, s0 + .1, zz + .35 + E), (xx, s1 - .1, zz + .35 + E), (xx, s1 - .1, zz + 1.1)],
                             (d, 0, 0), "Iron")
    finish(m, g)
