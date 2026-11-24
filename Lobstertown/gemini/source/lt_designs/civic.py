"""Lobstertown civic and service buildings (ZS1, Claude 2026-11-17, the author picked "fieldstone and shingle").

The town's public buildings in the H. H. Richardson manner of the 1880s Maine coast: a rough granite fieldstone
ground storey with round-arched windows and doors on dressed stone voussoirs, weathered shingle above, deep
hipped slate roofs with paired chimneys, octagonal stair turrets, a hose tower, a belfry or clock stage on the
ridge, and a lower fieldstone back wing to the rear line (rule 17). Its own family (rule 20): no other district
uses fieldstone, and the shingle sits on a stone storey instead of a granite water table.

    build(lod, W=3, D=4, **variant)        free-standing: side yards, a front walk, a back wing

Variant keys:
  storeys  1 | 2 | 3: the fieldstone storey (4.4 m) and shingle storeys (3.4 m) above it (1 = all stone)
  depth    depth of the main block (m)
  ground   'arch' (round-arched windows in the stone) | 'square' (stone-lintelled sashes)
  engines  0 | n: a fire station's open arched engine bays across the ground floor (with one side door)
  turret   None | 'left' | 'right': an octagonal stair turret on that front corner, up to the main eave
  tower    None | 'hose' (a tall square stone hose tower on the turret side) | 'belfry' (a square belfry stage on the
           ridge) | 'clock' (a taller one) | 'lookout' (an octagonal shingled stage rising past the eave at a corner)
  roof     'hip' | 'steep' (a tall Richardson hip) | 'gable' (a big shingled front gable, attic windows in it)
  cupola   True: a louvred ventilator on the ridge
  vbays    0 | n: closed carriage doors (2.6 m) in the ground floor at the end away from the turret, for patrol
           cars, ambulances or mail vans (the setup's vehicle spawn points sit behind them)
  porch    True: a verandah across the front (the cottage hospital)
  wing     None | 'low' (one storey) | 'mid' (two storeys) | 'twin' (two one-storey wings round a court)
  stacks   0 | n: tall square chimney stacks behind the main block (waterworks, powerhouse, incinerator)
  wall     shingle of the upper storeys ; door ; lites
"""
import math
from lt_kit import Mesh, Wall, wall, style, chimney, finish, wbox, porch, gable_wall, gable_roof, band, holes_for, E, TRIM
from lt_shapes import pavilion_roof, slab
from lt_designs.mainst import tower
from lt_designs.cottage import cupola

SM = 1.2                      # side yards
# street line: the front wall stands `set` (1.0 m) in from the lot front, like Main Street and Exchange Row, so the cornice,
# eaves and turret fronts stay on the lot and the building meets the sidewalk (the author 2026-11-18: services were set back)
G = 4.4                       # the fieldstone storey
F = 3.4                       # each shingle storey
STONE = "Greystone"           # rough fieldstone (reads as rubble on purpose)
DRESSED = "Dressed"           # voussoirs, string course, sills
ROOF = "SlateDark"
HIP = .55
STEEP = .85                   # a Richardson hip
PITCH = .6                    # a front gable
EDGE = 2.1                    # corner pier to the first bay centre (rule 1 with a 1.5 m arch)
POINTS = {}                   # the last build's door and vehicle bay centres (world x, y), for the service json
DROP = .012                   # back wings sit this far under the main block's levels: nf_kit.band only pulls a 'c'
                              # end back at the far end, so a wing course level with the main one would overlap it
COURSE, RISE, PROUD = .42, .55, .02   # rock-faced coursing on the fieldstone (Richardson), LOD0 only
BLOCK, JOINT = 1.1, .03               # its stones: length and the joint between them
DEFAULT = dict(storeys=2, depth=12.0, set=1.0, ground="arch", engines=0, roof="hip", turret=None, tower=None, cupola=False,
               vbays=0, porch=False, wing="low", stacks=0, wall="ShingleSilver", door="Oxblood", lites="2")


def spread(a, b, step=3.2, odd=True, edge=EDGE):
    """bay centres from a + edge to b - edge, about `step` apart (odd: an odd count, a middle bay for the door)"""
    span = b - a - 2 * edge
    k = max(0, round(span / step))
    if odd and k % 2:
        k = k + 1 if span / (k + 1) >= .75 * step else k - 1
    if k == 0:
        return [(a + b) / 2]
    return [a + edge + span * i / k for i in range(k + 1)]


def rough(m, w, H, z_top, lod, s="x", e="x", cuts=()):
    """Rock-faced courses standing proud of a fieldstone wall up to z_top, cut round each opening and its arch.
    s='c': the wall starts at an inside corner, so the courses are cut back clear of the neighbour's."""
    if lod:
        return
    extra = list(cuts) + ([(-.01, PROUD + 2 * E)] if s == "c" else [])
    z, i = .12, 0
    while z + COURSE < z_top - .2:
        cut = [(h[0] - .28, h[1] + .28) for h in H if h[2] - .12 < z + COURSE and z < h[3] + .3]
        u = BLOCK * (.5 + .5 * (i % 2))                 # broken joints: each course's stones staggered half a block
        joints = []
        while u < w.L - .3:
            joints.append((u - JOINT / 2, u + JOINT / 2))
            u += BLOCK
        band(m, w, z, z + COURSE, PROUD, STONE, "-" if s == "c" else s, e, cut + extra + joints)
        z += RISE
        i += 1


def floors(n, ground):
    """(width, sill, head[, kind]) per storey and the eave line"""
    win = [(1.5, .9, 3.6, "bay") if ground == "arch" else (1.2, .9, 3.0)]
    win += [(1.0, G + F * (j - 1) + .85, G + F * (j - 1) + 2.6) for j in range(1, n)]
    return win, G + F * (n - 1)


def build(lod, W=3, D=4, **variant):
    for k in ("palette", "lot"):
        variant.pop(k, None)
    v = dict(DEFAULT, **variant)
    n = v["storeys"]
    win, top = floors(n, v["ground"])
    XH = 4.0 * W - SM
    XL = -XH
    yF = -4.0 * D + v["set"]
    end = 4.0 * D - .6
    yR = min(yF + v["depth"], end)
    ym = (yF + yR) / 2
    zs = G - .06 if n > 1 else top - .3                # the coursing stops under the string course or the frieze
    mats = [(0.0, G, STONE), (G, top, v["wall"])] if n > 1 else [(0.0, top, STONE)]
    st = style(top, mats, win, belts=(G,) if n > 1 else (), plinth=None, corners=False, frieze=.3, belt_mat=DRESSED)
    trim = dict(door=v["door"], lites=v["lites"], masonry=DRESSED, reveal=STONE, bay_wall=STONE, frame=TRIM,
                arch=True, glazed=True, lean="bare" if lod else True)
    strim = dict(trim, simple=True)
    m, g = Mesh(), Mesh()
    sw = {"balance": "Richardsonian civic front: picturesque, the stair turret off the axis"}

    # ---- the street front
    tx = None
    if v["turret"]:
        a = 2.0
        tx = XL + a - .3 if v["turret"] == "left" else XH - a + .3
    if v["engines"]:                                   # fire station: a side door and open arched engine bays
        ne = v["engines"]
        eb = [XH - 3.8 - 5.8 * i for i in range(ne)][::-1]       # engine bays from the right corner
        gb = [(XL + eb[0] - 1.7) / 2] + eb                        # the door midway in the solid wall left of them
        ub = spread(XL, XH, 2.9, odd=False)
        gst = style(G, [(0.0, G, STONE)], [(3.4, 0.0, 4.0, "bay")], plinth=None, corners=False, frieze=None)
        etrim = dict(trim, glazed=False)
        fw_ = wall(m, g, gst, (XL, yF), (XH, yF), "x", "x", gb, lod, door=(gb[0], 1.2, 3.0), trim=etrim, top=G,
                   waive=dict(sw, rhythm="engine bays beside the watch-room door"), frieze_on=False)
        rough(m, fw_, holes_for(fw_, gb, gst["win"], (gb[0], 1.2, 3.0)), zs, lod)
        ust = style(top, mats, [None] + win[1:], plinth=None, corners=False, frieze=.3, belt_mat=DRESSED)
        ust["win"] = [(1.0, -9.0, -8.0)] + win[1:]   # no ground row on the upper wall
        wall(m, g, ust, (XL, yF), (XH, yF), "x", "x", ub, lod, z0=G, trim=trim, waive=sw)
        fb = gb
        POINTS.update(ped=(gb[0], yF), veh=[(x, yF + 2.0) for x in eb])
    else:
        fb = spread(XL, XH)
        omit = [(c, f) for c in fb for f in range(n) if tx is not None and abs(c - tx) < 2.6]
        dc = fb[len(fb) // 2]
        if tx is not None and abs(dc - tx) < 2.6:
            dc = fb[len(fb) // 2 + (1 if v["turret"] == "left" else -1)]
        vb = [c for c in (fb[::-1] if v["turret"] != "right" else fb)[1:-1] if abs(c - dc) > 3.5][::2][:v["vbays"]]
        fw_ = Wall((XL, yF), (XH, yF))
        holes = [(fw_.u_of(c) - 1.3, fw_.u_of(c) + 1.3, 0.0, 3.3, "door") for c in vb]
        omit += [(c, 0) for c in vb]
        fws = dict(sw)
        if omit:
            fws["glass"] = "the stair turret stands in front of the corner bays"
        if vb:
            fws["rhythm"] = "carriage doors for the service vehicles at the end of the front"
        wall(m, g, st, (XL, yF), (XH, yF), "x", "x", fb, lod, door=(dc, 1.6, 3.6), trim=trim, omit=omit, holes=holes,
             waive=fws)
        tcut = [tuple(sorted((fw_.u_of(tx - 2.2), fw_.u_of(tx + 2.2))))] if tx is not None else []
        rough(m, fw_, holes_for(fw_, fb, win, (dc, 1.6, 3.6)) + holes, zs, lod, cuts=tcut)
        POINTS.update(ped=(dc, yF), veh=[(c, yF + 2.0) for c in vb])
        if v["porch"]:
            porch(m, XL + .4, XH - .4, yF, v["set"] - 1.1, lod, zf=.16, zt=3.6, mat=ROOF, stair=(dc - .9, dc + .9),
                  skirt=False, posts=[XL + .55 + (XH - XL - 1.1) * j / 6 for j in range(7)] if lod < 2 else None)

    # ---- side walls and the back of the main block
    sb = spread(yF, yR, 3.0, odd=False)
    for A, B in (((XL, yR), (XL, yF)), ((XH, yF), (XH, yR))):
        sw_ = wall(m, g, st, A, B, "x", "x", sb, lod, trim=strim, waive=sw)
        rough(m, sw_, holes_for(sw_, sb, win), zs, lod)
    wings = []
    wk = v["wing"] if end - yR > 5.0 else None
    if wk:
        md = yR - yF
        if wk == "twin":
            ww = min(8.0, (XH - XL - 6.0) / 2)
            wings = [(XL + 1.0, XL + 1.0 + ww), (XH - 1.0 - ww, XH - 1.0)]
        elif wk == "quad":
            ww = min(12.0, (XH - XL - 14.0) / 2)
            wings = [(XL + 1.0, XL + 1.0 + ww), (XH - 1.0 - ww, XH - 1.0)]
        elif wk == "wards":
            ww = min(11.0, (XH - XL - 12.0) / 3)
            wings = [(XL + 1.0, XL + 1.0 + ww), (-ww / 2, ww / 2), (XH - 1.0 - ww, XH - 1.0)]
        else:
            ww = min(8.0 if v["roof"] == "gable" else 12.0, XH - XL - 4.0, md - 2.0)
            wings = [(-ww / 2, ww / 2)]
    w_mid = wk in ("mid", "quad", "wards")
    wtop = (G + F if w_mid else G) - DROP
    wrise = lambda x0, x1: ((x1 - x0) / 2 + .35) * HIP
    rb = spread(XL, XH, 3.0)
    om = []
    for x0, x1 in wings:
        zr_w = wtop + wrise(x0, x1)
        om += [(c, f) for c in rb for f, spec in enumerate(win) if x0 - .9 < c < x1 + .9 and spec[1] < zr_w + .3]
    bw = wall(m, g, st, (XH, yR), (XL, yR), "x", "x", rb, lod, trim=strim, omit=om,
              waive=dict(sw, glass="the back wing covers the lower windows",
                         rhythm="the back wing covers the lower windows") if om else sw)
    wcut = [tuple(sorted((bw.u_of(x0), bw.u_of(x1)))) for x0, x1 in wings]     # the wings cover the back wall there
    bh = [h for h in holes_for(bw, rb, win) if not any(a - .2 < h[0] and h[1] < b + .2 for a, b in wcut)]
    rough(m, bw, bh, zs, lod, cuts=wcut)

    # ---- the main roof
    if v["roof"] == "gable":                           # ridge front to back, a big shingled gable on the street
        zr = top + (XH - XL) / 2 * PITCH
        gable_roof(m, XL, XH, yF, yR, top + .006, zr, lod, ROOF, over=(.45, .35), sides=("e", "e"))
        gm = v["wall"] if n > 1 else "ShingleSilver"
        gable_wall(m, g, (XL, yF), (XH, yF), top, zr, lod, gm, trim=strim,
                   wins=[(x, 1.0, top + .9, top + 2.6) for x in (-2.4, 0.0, 2.4)] + [(0.0, .9, top + 3.4, top + 4.7)])
        zw_ = max([wtop + wrise(x0, x1) for x0, x1 in wings] or [top])
        gable_wall(m, g, (XH, yR), (XL, yR), top, zr, lod, gm, trim=strim,
                   wins=[(x, 1.0, zw_ + .6, zw_ + 2.2) for x in (-1.8, 1.8)])
        for cy in (yF + 2.5, yR - 2.5):
            chimney(m, 0.0, cy, .4, .5, zr - 1.0, zr + 1.0, lod)
    else:
        zr = pavilion_roof(m, XL - .35, XH + .35, yF - .35, yR + .35, top + .006,
                           ((yR - yF) / 2 + .35) * (STEEP if v["roof"] == "steep" else HIP), lod, ROOF, finial=False)
        for cx in (XL + 3.0, XH - 3.0):
            chimney(m, cx, ym, .4, .5, top, zr + .9, lod)

    # ---- back wings: fieldstone, one or two storeys, hipped, running into the main roof
    qRD = 11.0
    q_end = end - .5
    yQ = q_end - qRD
    for wi, (x0, x1) in enumerate(wings):
        wst = style(wtop, [(0.0, G, STONE)] + ([(G, wtop, v["wall"])] if w_mid else []),
                    [(1.2, .9, 3.0)] + ([win[1]] if w_mid else []), belts=(G - DROP,) if w_mid else (),
                    plinth=None, corners=False, frieze=.3, belt_mat=DRESSED)
        yb = spread(yR, end, 3.0, odd=False, edge=1.6)
        zws = min(G - .06, wtop - .3)
        sides_w = [((x0, end), (x0, yR), "x", "c", yb, wk == "quad" and wi == 1),
                   ((x1, yR), (x1, end), "c", "x", yb, wk == "quad" and wi == 0),
                   ((x1, end), (x0, end), "x", "x", spread(x0, x1, 3.0, odd=False, edge=1.6), False)]
        for A, B, s, e, bays, inner_q in sides_w:
            om_w = [(c, f) for c in bays for f in range(len(wst["win"])) if inner_q and yQ - 1.0 < c < q_end + 1.0]
            wv = dict(sw, glass="the rear cloister joins this wall", rhythm="the rear cloister joins this wall") if om_w else sw
            ww_ = wall(m, g, wst, A, B, s, e, bays, lod, trim=strim, omit=om_w, waive=wv)
            qcut = [tuple(sorted((ww_.u_of(yQ), ww_.u_of(q_end))))] if inner_q else []
            wh = [h for h in holes_for(ww_, bays, wst["win"]) if not any(a - .2 < h[0] and h[1] < b + .2 for a, b in qcut)]
            rough(m, ww_, wh, zws, lod, s, e, cuts=qcut)
        hw = (x1 - x0) / 2 + .35
        zw = pavilion_roof(m, x0 - .35, x1 + .35, yR - hw - .5, end + .35, wtop + .006, hw * HIP, lod, ROOF,
                           finial=False)
        assert zw < zr - .3, f"rule 24: the wing ridge {zw:.2f} must stay under the main ridge {zr:.2f}"
        if wk not in ("twin", "quad", "wards") and end - yR > 9:
            chimney(m, (x0 + x1) / 2, (yR + end) / 2 + 1.0, .35, .45, wtop, zw + .8, lod)
    if wk == "quad" and len(wings) == 2:                 # rear 1-storey cloister range closing the quadrangle
        qx0, qx1 = wings[0][1], wings[1][0]
        qtop = G - 2 * DROP
        qst = style(qtop, [(0.0, qtop, STONE)], [(1.5, .9, 3.4, "bay")] if v["ground"] == "arch" else [(1.2, .9, 3.0)],
                    belts=(), plinth=None, corners=False, frieze=.3, belt_mat=DRESSED)
        qb = spread(qx0, qx1, 3.2, odd=True, edge=1.8)
        qdc = qb[len(qb) // 2]
        qf = wall(m, g, qst, (qx0, yQ), (qx1, yQ), "c", "c", qb, lod, door=(qdc, 1.6, 3.4), trim=strim, waive=sw)
        rough(m, qf, holes_for(qf, qb, qst["win"], (qdc, 1.6, 3.4)), qtop - .3, lod, "c", "c")
        qr = wall(m, g, qst, (qx1, q_end), (qx0, q_end), "c", "c", qb, lod, trim=strim, waive=sw)
        rough(m, qr, holes_for(qr, qb, qst["win"]), qtop - .3, lod, "c", "c")
        qym = (yQ + q_end) / 2
        qz = qtop + (qRD / 2) * HIP
        assert qz < wtop - .1, f"quad cloister ridge {qz:.2f} exceeds side wing eave {wtop:.2f}"
        qprof = [(yQ - .35, qtop - .35 * HIP), (qym, qz), (q_end + .35, qtop - .35 * HIP)]
        slab(m, qprof, qx0 + 3 * E, qx1 - 3 * E, lambda a, q, z: (a, q, z), lod, ROOF, end=ROOF, what="quad cloister roof")
        if lod == 0:
            wbox(m, qx0 + 6 * E, qx1 - 6 * E, qym - .09, qym + .09, qz + .14, qz + .23, ROOF, ("z-",))

    # ---- turret, towers, cupola, stacks
    srows = lambda z0, z1: [(f[1], f[2], (0, 1, 7)) for f in win[1:] if z0 < f[1] and f[2] < z1]
    if v["turret"]:
        a = 2.0
        cy = yF + a - .3                                 # the turret front stands .3 m proud of the street wall
        rows = [(.9, 3.0, (0, 1, 7))] + srows(G, top)
        z1 = top
        if v["tower"] == "lookout":                      # the turret rises a stage past the eave
            z1 = top + 3.2
            rows.append((top + .9, top + 2.5, tuple(range(8))))
        tower(m, g, lod, tx, cy, a, 8, 0.0, z1, 4.2, STONE if n == 1 else v["wall"], ROOF, dict(strim), rows,
              DRESSED, crest=True)
    if v["tower"] == "hose":                             # the hose-drying tower, stone, beside the engine bays
        a = 1.7
        hx = XH - a - .2
        z1 = top + 7.0
        hrows = [(z1 - 2.6, z1 - .9, (0, 1, 2, 3))]
        if zr + 2.2 < z1 - 3.0:                          # a lower row only where it clears the top one
            hrows.append((zr + .6, zr + 2.2, (0, 2)))
        tower(m, g, lod, hx, yR - a - .5, a, 4, top - .5, z1, 3.0, STONE, ROOF, dict(strim), hrows, DRESSED)
    elif v["tower"] in ("belfry", "clock"):              # a square stage on the ridge
        a = 1.6 if v["tower"] == "belfry" else 2.1
        z1 = zr + (2.6 if v["tower"] == "belfry" else 4.4)
        tower(m, g, lod, 0.0, ym, a, 4, zr - 1.2, z1, 3.2 if v["tower"] == "belfry" else 4.6, v["wall"], ROOF,
              dict(strim), [(z1 - 2.1, z1 - .5, (0, 1, 2, 3))], DRESSED)
    if v["cupola"]:
        cupola(m, 0.0, ym, zr + .16, lod, v["wall"], ROOF, "Black")
    for k in range(v["stacks"]):                         # tall stacks at the back corners of the main block
        sx = (XL + 2.0) if k == 0 else (XH - 2.0)
        chimney(m, sx, yR - 1.6, .8, .8, top - .5, zr + 9.0 + 2.0 * k, lod, "Greystone")
    finish(m, g)
