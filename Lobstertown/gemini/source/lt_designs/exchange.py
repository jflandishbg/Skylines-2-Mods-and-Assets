"""Lobstertown Exchange Row (ZO1, Claude 2026-11-17, the author: "do something newish"): the town's office district.

The money end of a Maine harbour town around 1900-1915: savings banks, a custom house, a merchants' exchange,
marine insurance, a cable office, steamship agents, a trust company and the newspaper. Beaux-Arts and Classical
Revival blocks shoulder to shoulder: a grey granite banking storey (often rusticated, with tall arched windows),
pale limestone ashlar above with stone-trimmed windows, a deep stone cornice, and green copper on top (mansards,
hips, a dome, a clock tower). Dark bronze sashes and doors, no white trim anywhere (rule 20: its own family, the
TrimWhite of soffits and finials is tinted to stone by the 'exchange' palette). Backs are plainer: ashlar or buff
common brick, with a skylit banking hall, stepped back blocks, or two wings round a light court.

    build(lod, W=2, D=3, **variant)           lots W x D cells (8 m); party walls both sides

Variant keys:
  storeys   3 | 4: the banking storey (5.2 m) and the office floors (3.6 m) above it
  ground    'arch' (tall arched windows in the banking storey) | 'square'
  rust      True: the granite storey is rusticated (raised courses, close view)
  order     None | 'columns' (engaged giant columns between the bays of the office floors) | 'pilasters'
  hood      None | 'cap' | 'pediment' (on the office windows and the door)
  oriels    True: bronze oriels on the second and second-last bays of the office floors
  roof      'flat' (deep stone cornice) | 'mansard' (copper, dormers front and back) | 'hip' (copper, on the cornice)
  crown     None | 'pediment' (a low stone pediment over the middle bays) | 'dome' (a copper dome on a drum) |
            'tower' (a stone clock-stage tower with a copper pyramid) | 'balustrade' (along the cornice)
  attic     True: an attic storey set back behind the cornice, its own small cornice
  quoins    True: long-and-short stone quoins up both ends of the front
  back      'full' (the block runs to the rear) | 'block' (a back block a storey lower) | 'step' (back block, then
            a one-storey store) | 'hall' (a one-storey skylit banking hall) | 'court' (two wings round a light court)
  wall, base, back_mat, door, lites
"""
import math
from lt_kit import Mesh, Wall, finish, wall, style, surface, party, wbox, lbox, bay, gable_wall, gable_roof, chimney, E, TRIM
from nf_kit import band, holes_for, mansard_row
from lt_shapes import cornice_roof, pavilion_roof, dome, slab
from lt_designs.cannery import mansard_dormer, monitor, vent
from lt_designs.mainst import tower

SET = 1.2                     # the street wall stands 1.2 m in (cornice, columns and hoods stay on the lot)
CSET = 1.0                    # corner: both street walls stand 1.0 m in (Rule 29; 0.4 m cornice stays 0.6 m inside lot)
G = 5.2                       # the banking storey
F = 3.6                       # each office floor
MAIN = 14.0                   # depth of the main block when something stands behind it
DEEP = .75                    # the main cornice
HALL = 6.4                    # a one-storey banking hall
COURT = 5.0                   # light court width
MANS = (3.0, .9, 1.0)         # mansard: steep rise, run, deck rise (Cannery Row's proportions)
STONE = "Dressed"
COPPER = "TinGreen"
FRAME = "Iron"                # dark bronze sashes
DEFAULT = dict(storeys=3, ground="arch", rust=False, order=None, hood=None, oriels=False, roof="flat", crown=None,
               attic=False, quoins=False, back="block", wall=STONE, base="StoneBase", back_mat=None, door="Iron",
               lites="6", corner=False, main_d=MAIN, court_w=COURT)


def rows(n, arched, hood):
    """(width, sill, head[, kind]) per storey, and the eave line (clear of the hoods and the frieze)."""
    win = [(1.6, .9, 4.3, "bay") if arched else (1.4, .9, 3.9)]
    win += [(1.1, G + F * (j - 1) + .85, G + F * (j - 1) + 2.75) for j in range(1, n)]
    return win, win[-1][2] + (1.35 if hood == "pediment" else .85)


def piece_top(k):
    return HALL if k == 0 else G + F * (k - 1)


def piece_rows(k):
    if k == 0:
        return [(1.6, 1.2, 4.6, "bay")]               # the banking hall: tall arched windows
    return [(1.2, 1.0, 3.6)] + [(1.1, G + F * (j - 1) + .85, G + F * (j - 1) + 2.75) for j in range(1, k)]


def column(m, cx, yw, r, z0, z1, lod, mat):
    """An engaged giant column against the wall at yw (facing -y): square base, round shaft (only the half that
    stands proud of the wall is built), square capital and abacus. Close and middle views only."""
    if lod == 2:
        return
    cy = yw - r * .55
    wbox(m, cx - r - .1, cx + r + .1, cy - r - .1, yw - E, z0, z0 + .35, mat, ("y+", "z-"))
    wbox(m, cx - r - .14, cx + r + .14, cy - r - .14, yw - E, z1 - .22, z1, mat, ("y+",))
    wbox(m, cx - r - .04, cx + r + .04, cy - r - .04, yw - E, z1 - .5, z1 - .22 - E, mat, ("y+",))
    k = 12 if lod == 0 else 8
    za, zb = z0 + .35 + E, z1 - .5 - E
    for i in range(k):
        a0, a1 = 2 * math.pi * i / k, 2 * math.pi * (i + 1) / k
        p0 = (cx + r * math.cos(a0), cy + r * math.sin(a0))
        p1 = (cx + r * math.cos(a1), cy + r * math.sin(a1))
        if (p0[1] + p1[1]) / 2 > yw:                 # inside the wall
            continue
        m.facing([(p0[0], p0[1], za), (p1[0], p1[1], za), (p1[0], p1[1], zb), (p0[0], p0[1], zb)],
                 ((p0[0] + p1[0]) / 2 - cx, (p0[1] + p1[1]) / 2 - cy, 0), mat)


def balustrade(m, x0, x1, y, z, lod, mat, depth=.3):
    """A stone balustrade standing on the cornice top at z along its front edge y (facing -y): a plinth, dies every
    ~3 m, the rail; turned balusters close up. An open frame (the blank-wall audit's half-solid rule)."""
    if lod == 2:
        return
    y1 = y + depth
    wbox(m, x0, x1, y, y1, z, z + .16, mat, ("z-",))
    wbox(m, x0, x1, y - .03, y1 + .03, z + .86, z + 1.0, mat)
    k = max(2, round((x1 - x0) / 3.0))
    dies = [x0 + .2 + (x1 - x0 - .4) * i / k for i in range(k + 1)]
    for d in dies:
        wbox(m, d - .2, d + .2, y - .01, y1 + .01, z + .16 + E, z + .86 - E, mat, ("z-", "z+"))
    if lod == 0:
        for a, b in zip(dies, dies[1:]):
            c = a + .2 + .17
            while c < b - .2 - .1:
                wbox(m, c - .05, c + .05, y + .1, y1 - .1, z + .16 + E, z + .86 - E, mat, ("z-", "z+"))
                c += .3


def pediment(m, g, x0, x1, y0, y1, z, lod):
    """A low stone pediment on the cornice top: front and back triangles, a stone-covered gable roof (closed)."""
    rise = (x1 - x0) / 2 * .3
    gable_wall(m, g, (x0, y0), (x1, y0), z, z + rise, lod, STONE)
    gable_wall(m, g, (x1, y1), (x0, y1), z, z + rise, lod, STONE)
    gable_roof(m, x0, x1, y0, y1, z, z + rise, lod, STONE, over=(.25, .0), sides=("e", "e"), rake=STONE, th=.18)
    return z + rise


def roof_vents(m, x0, x1, y0, y1, z, lod, mat, keep=0.0, step=7.0):
    """Louvred ventilators on a flat back roof (stone or brick box, bronze louvres, copper pyramid cap), on a ~7 m
    grid; keep: leave |x| < keep clear (the hall's skylight)."""
    nx, ny = max(1, round((x1 - x0) / step)), max(1, round((y1 - y0) / step))
    for i in range(nx):
        cx = x0 + (x1 - x0) * (i + .5) / nx
        if abs(cx) < keep:
            continue
        for j in range(ny):
            cy = y0 + (y1 - y0) * (j + .5) / ny
            vent(m, cx, cy, z, .3, lod, mat, FRAME, COPPER, a=.5, h=.9)


def rusticate(m, w, H, z_top, lod, mat):
    """Raised courses across the granite storey, cut round each opening (and an arched window's stone ring)."""
    if lod:
        return
    z = .12
    while z + .42 < z_top - .2:
        cuts = [(h[0] - .28, h[1] + .28) for h in H if h[2] - .12 < z + .42 and z < h[3] + .3]
        band(m, w, z, z + .42, .02, mat, "-", "-", cuts)
        z += .55


def side_bays_ex(y0, y1, margin=1.85, max_p=3.55):
    """Evenly spaced window bay Y-coordinates down the side-street wall (y0..y1)."""
    inner = y1 - y0 - 2 * margin
    if inner < 2.2:
        return [(y0 + y1) / 2]
    k = max(2, math.ceil(inner / max_p) + 1)
    return [y0 + margin + inner * i / (k - 1) for i in range(k)]


def column_side(m, xw, cy, r, z0, z1, lod, mat):
    """An engaged giant column against the left side-street wall at xw (facing -x)."""
    if lod == 2:
        return
    cx = xw - r * .55
    wbox(m, cx - r - .1, xw - E, cy - r - .1, cy + r + .1, z0, z0 + .35, mat, ("x+", "z-"))
    wbox(m, cx - r - .14, xw - E, cy - r - .14, cy + r + .14, z1 - .22, z1, mat, ("x+",))
    wbox(m, cx - r - .04, xw - E, cy - r - .04, cy + r + .04, z1 - .5, z1 - .22 - E, mat, ("x+",))
    k = 12 if lod == 0 else 8
    za, zb = z0 + .35 + E, z1 - .5 - E
    for i in range(k):
        a0, a1 = 2 * math.pi * i / k, 2 * math.pi * (i + 1) / k
        p0 = (cx + r * math.cos(a0), cy + r * math.sin(a0))
        p1 = (cx + r * math.cos(a1), cy + r * math.sin(a1))
        if (p0[0] + p1[0]) / 2 > xw:
            continue
        m.facing([(p0[0], p0[1], za), (p1[0], p1[1], za), (p1[0], p1[1], zb), (p0[0], p0[1], zb)],
                 ((p0[0] + p1[0]) / 2 - cx, (p0[1] + p1[1]) / 2 - cy, 0), mat)


def balustrade_side(m, y0, y1, x, z, lod, mat, depth=.3):
    """A stone balustrade standing on the cornice top at z along its left side-street edge x (facing -x)."""
    if lod == 2:
        return
    x1 = x + depth
    wbox(m, x, x1, y0, y1, z, z + .16, mat, ("z-",))
    wbox(m, x - .03, x1 + .03, y0, y1, z + .86, z + 1.0, mat)
    k = max(2, round((y1 - y0) / 3.0))
    dies = [y0 + .2 + (y1 - y0 - .4) * i / k for i in range(k + 1)]
    for d in dies:
        wbox(m, x - .01, x1 + .01, d - .2, d + .2, z + .16 + E, z + .86 - E, mat, ("z-", "z+"))
    if lod == 0:
        for a, b in zip(dies, dies[1:]):
            c = a + .2 + .17
            while c < b - .2 - .1:
                wbox(m, x + .1, x1 - .1, c - .05, c + .05, z + .16 + E, z + .86 - E, mat, ("z-", "z+"))
                c += .3


def mansard_dormer_side(m, g, x0, cy, ze, lod, mat, roof_mat, trim, w=1.2, dz=(.45, 2.2), depth=1.4):
    """A gabled dormer on the left side-street mansard slope (facing -x)."""
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
         th=.1, what=f"side dormer roof at y {cy:.2f}")


def build(lod, W=2, D=3, **variant):
    variant.pop("palette", None)
    v = dict(DEFAULT, **variant)
    n, wm, base = v["storeys"], v["wall"], v["base"]
    bm = v["back_mat"] or wm
    arched = v["ground"] == "arch"
    corner = v["corner"]
    win, top = rows(n, arched, v["hood"])
    X = 4.0 * W - .01
    XL = -4.0 * W + CSET if corner else -X
    sx_ = "x" if corner else "-"
    yF = -4.0 * D + (CSET if corner else SET)
    end = 4.0 * D - .6
    back = v["back"]
    main_d = v["main_d"]
    court_w = v["court_w"]
    yR = end if back == "full" or end - yF - main_d < 6.0 else yF + main_d
    if yR >= end - .1:
        back = "full"
    nb = 2 * W + 1                                   # odd: the door on the middle bay
    ml = 1.85 if corner else 1.6
    mr = 1.6
    s = (X - XL - ml - mr) / (nb - 1)
    bays = [XL + ml + s * i for i in range(nb)]
    door_x = bays[nb // 2] if corner else 0.0
    m, g = Mesh(), Mesh()

    ftrim = dict(door=v["door"], lites=v["lites"], masonry=STONE, reveal=wm, frame=FRAME, lean=True, bay_wall=base,
                 arch=True, glazed=True)
    if v["hood"]:
        ftrim["hood"] = v["hood"]
    rtrim = dict(door=v["door"], lites=v["lites"], masonry=STONE, reveal=bm, frame=FRAME, lean=True, hood="cap")

    # ---- the street front
    st = style(top, [(0.0, G, base), (G, top, wm)], win, belts=(G,), plinth=None, corners=False, frieze=.45,
               belt_mat=STONE)
    door = (door_x, 1.8, 3.9)
    waive, omit = {}, []
    if v["oriels"]:
        ob = (bays[1], bays[-2])
        omit = [(c, f) for c in ob for f in range(1, n)]
        waive = dict(glass="the bronze oriels carry the glass of their bays",
                     rhythm="bronze oriels fill two bays on every office floor")
    fw = wall(m, g, st, (XL, yF), (X, yF), sx_, "-", bays, lod, door=door, trim=ftrim, waive=waive, omit=omit)
    if v["rust"]:
        H = [h for h in holes_for(fw, bays, win, door) if h[2] < G]
        rusticate(m, fw, H, G - .06, lod, base)
    if v["quoins"] and lod == 0:                     # long-and-short quoins up both ends of the ashlar front
        z, k = G + .12, 0
        while z + .4 < top - .5:
            wq = .6 if k % 2 == 0 else .35
            for a0, a1 in ((0.0, wq), (fw.L - wq, fw.L)):
                lbox(m, fw, a0 + E, a1 - E, z, z + .38, E, .05, STONE)
            z += .42
            k += 1
    if v["order"] and lod < 2:                       # the giant order across the office floors
        z0, z1 = G + .10 + E, top - .45 - .03
        for a, b in zip(bays, bays[1:]):
            c = (a + b) / 2
            if v["order"] == "columns":
                column(m, c, yF, .3, z0, z1, lod, STONE)
            else:
                u = fw.u_of(c)
                lbox(m, fw, u - .3, u + .3, z0, z1 - .3, E, .1, STONE)
                lbox(m, fw, u - .38, u + .38, z1 - .3 + E, z1, E, .16, STONE)
    if v["oriels"]:                                  # bronze oriels on stone brackets, every office floor
        z0, z1 = G + .45, win[-1][2] + .4
        for c in ob:
            bay(m, g, c, yF, 1.8, .6, z0, z1, lod, FRAME, [(b_, t_) for _, b_, t_ in win[1:]], ftrim, COPPER,
                v["lites"])
            a = .9 + .6
            m.facing([(c - a, yF, z0), (c - .9, yF - .6, z0), (c + .9, yF - .6, z0), (c + a, yF, z0)], (0, 0, -1),
                     STONE)
            if lod == 0:
                for cc in (c - .7, c + .7):
                    wbox(m, cc - .09, cc + .09, yF - .5, yF - E, z0 - .6, z0 - E, STONE, ("y+", "z+"))

    # ---- the main block: side-street elevation (corner) or party wall, right party wall, and roof
    party(m, (X, yF), (X, yR), 0.0, top, wm)
    sw, ys = None, []
    if corner:
        ys = side_bays_ex(yF, yR, margin=1.85, max_p=3.55)
        sdoor = (ys[len(ys) // 2], 1.8, 3.9) if len(ys) >= 3 else None
        swaive = {"balance": "Beaux-Arts corner side-street elevation"}
        sw = wall(m, g, st, (XL, yR), (XL, yF), "x", "x", ys, lod, door=sdoor, trim=ftrim, waive=swaive)
        if v["rust"]:
            Hs = [h for h in holes_for(sw, ys, win, sdoor) if h[2] < G]
            rusticate(m, sw, Hs, G - .06, lod, base)
        if v["quoins"] and lod == 0:
            z, k = G + .12, 0
            while z + .4 < top - .5:
                wq = .6 if k % 2 == 0 else .35
                for a0, a1 in ((0.0, wq), (sw.L - wq, sw.L)):
                    lbox(m, sw, a0 + E, a1 - E, z, z + .38, E, .05, STONE)
                z += .42
                k += 1
        if v["order"] and lod < 2:
            z0, z1 = G + .10 + E, top - .45 - .03
            for a, b in zip(ys, ys[1:]):
                c = (a + b) / 2
                if v["order"] == "columns":
                    column_side(m, XL, c, .3, z0, z1, lod, STONE)
                else:
                    u = sw.u_of(c)
                    lbox(m, sw, u - .3, u + .3, z0, z1 - .3, E, .1, STONE)
                    lbox(m, sw, u - .38, u + .38, z1 - .3 + E, z1, E, .16, STONE)
    else:
        party(m, (-X, yR), (-X, yF), 0.0, top, wm)
    z1 = top + DEEP
    roof_top = z1
    kind = v["roof"]
    if kind == "mansard":
        h1, i1, h2 = MANS
        msides = dict(x0="s", x1="e") if corner else dict(x0="e", x1="e")
        mridge = ("x" if (X - XL) >= (yR - yF) else "y") if corner else "x"
        mansard_row(m, XL + E, X - E, yF, yR, top, h1, i1, h2, lod, sides=msides, ridge=mridge,
                    steep=COPPER, deck="TinFlat", roll=FRAME, end=wm)
        gt = dict(rtrim, reveal=wm)
        for cx in bays:                              # a stone dormer on every window axis, front and back (rule 10)
            mansard_dormer(m, g, cx, yF + .15, 1, top, lod, wm, COPPER, gt, w=1.2)
            mansard_dormer(m, g, cx, yR - .15, -1, top, lod, bm, COPPER, dict(gt, reveal=bm), w=1.2)
        if corner:
            for cy in (ys[::2] if lod == 2 else ys):
                mansard_dormer_side(m, g, XL + .15, cy, top, lod, wm, COPPER, gt, w=1.2)
        roof_top = top + h1 + h2
    else:
        cx0 = XL - .4 if corner else XL + E
        cornice_roof(m, cx0, X - E, yF - .4, yR + .25, top, lod, deep=DEEP, side=STONE, ends=STONE if corner else wm)
        if corner and lod < 2:
            wbox(m, cx0 - .06, cx0 - E, yF - .4 + E, yR + .25 - E, z1 - .14, z1 + .04, STONE, ("x+",))
        if lod == 0:                                 # dentils on the frieze, modillions under the cornice
            for w_ in (fw, sw) if sw else (fw,):
                c = .3
                while c + .1 < w_.L - .3:
                    lbox(m, w_, c, c + .1, top - .36, top - .24, .07 + E, .12, STONE)
                    c += .25
            for i in range(int((X - XL - 1.0) / .8) + 1):
                cx = XL + .5 + i * .8
                wbox(m, cx - .07, cx + .07, yF - .36, yF - .07 - E, top - .22, top - E, STONE, ("y+", "z+"))
            if corner:
                for i in range(int((yR - yF - 1.0) / .8) + 1):
                    cy = yF + .5 + i * .8
                    wbox(m, XL - .36, XL - .07 - E, cy - .07, cy + .07, top - .22, top - E, STONE, ("x+", "z+"))
        if kind == "hip":                            # a copper hip standing on the cornice
            d = min(X - XL, yR - yF) if corner else (yR - .05 - (yF - .1))
            hx0 = XL - .1 if corner else XL + .01
            roof_top = pavilion_roof(m, hx0, X - .01, yF - .1, yR - .05, z1 + .006, d / 2 * .55, lod, COPPER)
    crown = v["crown"]
    if kind == "flat":                               # a stone balustrade along every flat cornice (round a pediment)
        hw = s + 1.3
        bx0 = XL - .32 if corner else XL + E + .02
        spans = [(bx0, door_x - hw - .35), (door_x + hw + .35, X - E - .02)] if crown == "pediment" else [(bx0, X - E - .02)]
        for a_, b_ in spans:
            if b_ - a_ > 1.0:
                balustrade(m, a_, b_, yF - .32, z1 + E, lod, STONE)
        if corner:
            balustrade_side(m, yF - .32 + .35 + E, yR + .2, XL - .32, z1 + E, lod, STONE)
    if crown == "pediment":
        hw = s + 1.3
        roof_top = max(roof_top, pediment(m, g, door_x - hw, door_x + hw, yF - .34, yF + 1.6, z1 + E, lod))
    elif crown == "dome":
        r = 2.0 if W == 2 else 2.6
        cx_d = (XL + min(5.2, (X - XL) / 2)) if corner else 0.0
        cy = (yF + min(5.2, (yR - yF) / 2)) if corner else (yF + min(MAIN, yR - yF) / 2)
        roof_top = dome(m, g, cx_d, cy, r, z1 + E, lod, COPPER, wm, drum=2.4)
        if lod < 2:                                  # a lantern finial on the crown
            wbox(m, cx_d - .12, cx_d + .12, cy - .12, cy + .12, roof_top - .05, roof_top + 1.4, FRAME, ("z-",))
            wbox(m, cx_d - .3, cx_d + .3, cy - .3, cy + .3, roof_top - E, roof_top + .35, COPPER)
    elif crown == "tower":
        a = 2.0
        zt = z1 + 6.2
        tx = (XL + a + .5) if corner else 0.0
        ty = yF + a + .5
        tower(m, g, lod, tx, ty, a, 4, z1 + E, zt, 4.4, wm, COPPER,
              dict(door=v["door"], lites=v["lites"], masonry=STONE, reveal=wm, frame=FRAME, lean=True),
              [(z1 + 3.5, z1 + 5.3, (0, 1, 2, 3))], STONE)
        if lod < 2:                                  # clock dial(s) on the street face(s) of the shaft
            yc = yF + .5 - .02
            k = 12 if lod == 0 else 8
            zc, rc = z1 + 1.8, .85
            ring = [(tx + rc * math.cos(2 * math.pi * i / k), zc + rc * math.sin(2 * math.pi * i / k)) for i in range(k)]
            m.facing([(x, yc, z) for x, z in ring][::-1], (0, -1, 0), "Cream")
            if lod == 0:
                wbox(m, tx - .03, tx + .03, yc - .03, yc - E, zc, zc + .6, FRAME, ("y+",))
                wbox(m, tx + .03 + E, tx + .4, yc - .025, yc - E, zc - .03, zc + .03, FRAME, ("y+",))
            if corner:
                xc = XL + .5 - .02
                sring = [(ty + rc * math.cos(2 * math.pi * i / k), zc + rc * math.sin(2 * math.pi * i / k)) for i in range(k)]
                m.facing([(xc, y, z) for y, z in sring], (-1, 0, 0), "Cream")
                if lod == 0:
                    wbox(m, xc - .03, xc - E, ty - .03, ty + .03, zc, zc + .6, FRAME, ("x+",))
                    wbox(m, xc - .025, xc - E, ty + .03 + E, ty + .4, zc - .03, zc + .03, FRAME, ("x+",))
        roof_top = max(roof_top, zt + 4.4)
    if v["attic"]:                                   # a set-back attic storey, its own small cornice
        za, ha = z1 + E, 2.9
        ya, yb = yF + .4, (yR - 1.0) if back in ("full", "court") else yR - .2
        xa = XL + .4 if corner else XL
        awin = [(round(s / 3.3, 2), za + .5, za + 2.05)]
        ast = style(za + ha, [(za, za + ha, wm)], awin, plinth=None, corners=False, frieze=.3, belt_mat=STONE)
        wall(m, g, ast, (xa, ya), (X, ya), sx_, "-", bays, lod, z0=za, trim=dict(ftrim, hood=None))
        wall(m, g, ast, (X, yb), (xa, yb), "-", sx_, bays, lod, z0=za, trim=dict(rtrim, reveal=wm))
        party(m, (X, ya), (X, yb), za, za + ha, wm)
        if corner:
            ys_a = side_bays_ex(ya, yb, margin=1.65, max_p=3.55)
            wall(m, g, ast, (xa, yb), (xa, ya), "x", "x", ys_a, lod, z0=za, trim=dict(ftrim, hood=None),
                 waive={"balance": "corner attic side elevation"})
        else:
            party(m, (-X, yb), (-X, ya), za, za + ha, wm)
        cornice_roof(m, xa - (.3 if corner else -E), X - E, ya - .3, yb + .3, za + ha, lod, deep=.4, side=STONE,
                     ends=STONE if corner else wm)
        roof_top = max(roof_top, za + ha + .4)
    cz = (top + MANS[0] - .1) if kind == "mansard" else (z1 + 2.9 + .3 if v["attic"] else z1 - .1)
    chimney(m, X - .5, yF + 3.5, .3, .45, cz, cz + 1.6, lod)
    chimney(m, XL + (.9 if corner else .5), yR - 2.5, .3, .45, cz, cz + 1.4, lod)

    # ---- the back of the main block, then whatever stands behind it
    rwin = [(1.2, 1.0, 3.6)] + win[1:]
    rst = style(top, [(0.0, top, bm)], rwin, plinth=None, corners=False, frieze=None)
    if back == "full":
        wall(m, g, rst, (X, yR), (XL, yR), "-", sx_, bays, lod, door=(door_x, 1.4, 3.0), trim=rtrim,
             waive={"balance": "corner rear lane door"} if corner else {})
        finish(m, g)
        return
    if back == "court":
        hk = n - 1
        h = piece_top(hk)
        cw = court_w / 2
        prow = piece_rows(hk)
        pst = style(h, [(0.0, h, bm)], prow, belts=(G,) if hk > 1 else (), plinth=None, corners=False, frieze=None,
                    belt_mat=STONE)
        # the main block's back wall: in the court up to the wings' cornice, then full width above them
        wall(m, g, rst, (cw, yR), (-cw, yR), "c", "c", [0.0], lod, door=(0.0, 1.4, 3.0), trim=rtrim, top=h + .45)
        if h + .45 < top - 1.5:
            wall(m, g, rst, (X, yR), (XL, yR), "-", sx_, bays, lod, z0=h + .45, trim=rtrim)
        span = end - yR
        k = max(2, math.ceil((span - 2.8) / 3.0) + 1)
        ys_c = [yR + 1.4 + (span - 2.8) * j / (k - 1) for j in range(k)]
        party(m, (X, yR), (X, end), 0.0, h, bm)
        if corner:
            wall(m, g, pst, (XL, end), (XL, yR), "x", "-", ys_c, lod, trim=rtrim,
                 waive={"balance": "corner court wing side elevation"})
        else:
            party(m, (-X, end), (-X, yR), 0.0, h, bm)
        wall(m, g, pst, (cw, end), (cw, yR), "x", "c", ys_c, lod, trim=rtrim)            # right wing, court side
        wall(m, g, pst, (-cw, yR), (-cw, end), "c", "x", ys_c, lod, trim=rtrim)          # left wing, court side
        wx = [c for c in bays if c > cw + 1.45]
        wxl = [c for c in bays if c < -cw - 1.45]
        wall(m, g, pst, (X, end), (cw, end), "-", "x", wx or [(X + cw) / 2], lod, trim=rtrim,
             waive={"balance": "the rear of one wing"})
        wall(m, g, pst, (-cw, end), (XL, end), "x", sx_, wxl or [(XL - cw) / 2], lod, trim=rtrim,
             waive={"balance": "the rear of one wing"})
        for x0, x1 in ((cw, X - E), (XL - (.3 if corner else -E), -cw)):
            cornice_roof(m, x0 - (.3 if x0 == cw else 0), x1 + (.3 if x1 == -cw else 0), yR + E, end + .3, h, lod,
                         deep=.45, side=STONE, ends=STONE if corner and x1 == -cw else bm, front=False)
        m.facing([(-cw, yR, .02), (cw, yR, .02), (cw, end + .3, .02), (-cw, end + .3, .02)], (0, 0, 1), "Paving")
        if lod < 2:
            for x0, x1 in ((cw + .8, X - .8), (XL + .8, -cw - .8)):
                roof_vents(m, x0, x1, yR + 1.0, end - 1.0, h + .45, lod, bm)
        finish(m, g)
        return
    if back == "hall":
        pieces = [(0, yR, end)]
    elif back == "block" or end - yR < 14.0:
        pieces = [(max(1, n - 1), yR, end)]
    else:
        pieces = [(max(1, n - 1), yR, yR + 8.0), (1, yR + 8.0, end)]
    zc = piece_top(pieces[0][0]) + .45
    if zc < top - 1.5:
        wall(m, g, rst, (X, yR), (XL, yR), "-", sx_, bays, lod, z0=zc, trim=rtrim)
    for i, (k, ya, yb) in enumerate(pieces):
        h = piece_top(k)
        nxt = pieces[i + 1] if i + 1 < len(pieces) else None
        pst = style(h, [(0.0, h, bm)], piece_rows(k), belts=(G,) if k > 1 else (), plinth=None, corners=False,
                    frieze=None, belt_mat=STONE)
        party(m, (X, ya), (X, yb), 0.0, h, bm)
        ptrim = dict(rtrim, glazed=True, arch=True, bay_wall=bm) if k == 0 else rtrim
        if corner:
            ys_p = side_bays_ex(ya, yb, margin=1.85 if k == 0 else 1.4, max_p=5.0 if k == 0 else 3.55)
            pw_ = wall(m, g, pst, (XL, yb), (XL, ya), "x", "-", ys_p, lod, trim=ptrim,
                       waive={"balance": "corner back-block side elevation"})
            if v["rust"]:
                Hp = [hh for hh in holes_for(pw_, ys_p, piece_rows(k), None) if hh[2] < G]
                rusticate(m, pw_, Hp, min(G, h) - .06, lod, bm)
        else:
            party(m, (-X, yb), (-X, ya), 0.0, h, bm)
        if nxt is None:
            ew = wall(m, g, pst, (X, yb), (XL, yb), "-", sx_, bays, lod, door=(door_x, 1.4, 3.0), trim=ptrim,
                      waive={"balance": "corner rear lane door"} if corner else {})
            if v["rust"]:                            # the rusticated base carries round to the back
                H = [hh for hh in holes_for(ew, bays, piece_rows(k), (door_x, 1.4, 3.0)) if hh[2] < G]
                rusticate(m, ew, H, min(G, h) - .06, lod, bm)
        else:
            hz = piece_top(nxt[0]) + .45
            if hz < h - 1.5:
                wall(m, g, pst, (X, yb), (XL, yb), "-", sx_, bays, lod, z0=hz, trim=rtrim)
        cornice_roof(m, XL - (.3 if corner else -E), X - E, ya + E, yb + .3, h, lod, deep=.45, side=STONE,
                     ends=STONE if corner else bm, front=False)
        if lod < 2 and yb - ya > 5:
            roof_vents(m, XL + 1.0, X - 1.0, ya + 1.0, yb - 1.0, h + .45, lod, bm,
                       keep=(min(3.0, (X - XL) / 2 - 2.0) + 1.2) if k == 0 else 0.0, step=5.5 if k == 0 else 7.0)
        if k == 0 and lod < 2:                       # the banking hall's skylight, or a clerestory monitor
            xm_h = (XL + X) / 2
            s0, s1 = ya + 2.0, yb - 2.0
            zz = h + .45
            if v["oriels"]:
                monitor(m, g, xm_h, s0, s1, zz + .3, 0.0, lod, bm, COPPER, FRAME, rake=COPPER)
            else:
                hw = min(3.0, (X - XL) / 2 - 2.0)
                wbox(m, xm_h - hw, xm_h + hw, s0, s1, zz, zz + .4, bm, ("z-",))
                lo, hi = zz + .4 + E, zz + 1.6                # a glazed ridge skylight, iron gable ends
                a, b = xm_h - hw + .1, xm_h + hw - .1
                g.facing([(a, s0 + .1, lo), (a, s1 - .1, lo), (xm_h, s1 - .1, hi), (xm_h, s0 + .1, hi)], (-1, 0, 1), "Glass")
                g.facing([(xm_h, s0 + .1, hi), (xm_h, s1 - .1, hi), (b, s1 - .1, lo), (b, s0 + .1, lo)], (1, 0, 1), "Glass")
                m.facing([(xm_h - hw + .1, s1 - .1, zz + .4 + E), (xm_h + hw - .1, s1 - .1, zz + .4 + E), (xm_h, s1 - .1, zz + 1.6)],
                         (0, 1, 0), FRAME)
                m.facing([(xm_h - hw + .1, s0 + .1, zz + .4 + E), (xm_h, s0 + .1, zz + 1.6), (xm_h + hw - .1, s0 + .1, zz + .4 + E)],
                         (0, -1, 0), FRAME)
    finish(m, g)
