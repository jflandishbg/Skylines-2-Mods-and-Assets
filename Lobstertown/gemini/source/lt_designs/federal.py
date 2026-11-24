"""Lobstertown Prestige Cottages (ZP1) and Cottage Flats (ZP2), second edition (Direction A, the author 2026-11-17): the
Federal and Greek Revival harbour town of Portland's West End, Bath and Wiscasset, 1800-1850.

    build(lod, W=2, D=5, **variant)

Painted clapboard (white, cream, straw, pale grey-blue: colour 1) with green or black shutters, Federal brick ends
with paired end chimneys, granite steps and water tables, Greek Revival gable fronts (corner pilasters, a deep
frieze, a pedimented gable, sidelights), Federal doubles with fanlights, 1.5-storey capes and brick Federal rows;
low roof pitches. Behind the house, as in the rest of the Prestige family (rule 17), a kitchen ell runs down one
side (or both) to a carriage barn across the back of the lot, .6 m off the rear line, round a paved service court;
an ell may end in a lower woodshed. The barn and woodshed are board-and-batten in colour 0 (barn red or white).

Variant keys (main house):
  kind     'side' (side gable) | 'gambrel' (side gambrel) | 'hip' (Federal hipped) | 'cape' (1.5 storeys, steep side
           gable, dormers) | 'temple' (Greek Revival gable front; a 1.5-storey side wing fills a lot 3 or more wide)
           | 'twin' (two Greek gable fronts side by side)
  storeys  2 | 3 (cape: always 1.5)
  doors    1 (centre, or side hall on a temple) | 2 (a double house) ; units: n (a brick row of n houses)
  brick    a brick for every main wall (rows, Wiscasset brick houses) ; brick_ends: brick gable ends only
  entry    'fan' (Federal fanlight, pilasters, entablature) | 'side' (Greek sidelights, deep entablature)
  portico  True: a pedimented portico on two columns over each door (only where a LOW eave already exists)
  porch    True: a one-storey Greek porch across a temple front
  walk     True: a widow's walk on the ridge ; lantern: a louvred belvedere on a hip
  dormers, shutters, door, lites, wall, roof_mat
Rear:
  ell      'LOW' (1.5 storeys) | 'MID' (2 storeys) ; wings 'near' | 'far' | 'twin' (ells down both sides)
  woodshed True: a LOW woodshed between a MID ell and a LOW barn
  barn     'gable' | 'gambrel' | 'cross' ; barn_h 'LOW' | 'MID' ; barn_mat ; barn_roof ; cupola ; lofts
  flats    True (ZP2): plain one-over-one windows on the back blocks, flat entrances on the court
Audit geometry (see RULEBOOK "How the audit sees"): every ridge sits on a 0.25 m grid line so its cap never splits an
eave run; side yards 1.0 m; at most three eave levels (main, MID 6.7, LOW 3.55).
"""
import math
from lt_kit import Mesh, Wall, chimney, finish, wall, style, gable_wall, gable_roof, porch, wbox, E, TRIM, roof_check
from lt_shapes import slab, dormer, pavilion_roof, widows_walk
from lt_designs.shore_row import TOPS, WIN1, WIN2, WIN3
from lt_designs.cottage import cupola, spread, nearest

SET = 3.5                     # the main front back from the lot front: a lawn strip and the granite step
SM = 1.0                      # side yards
LOW, MID = 3.55, 6.7          # the two back-block eaves
PITCH = .55                   # Federal and Greek Revival: low pitches
CAPE_P = .75                  # ... a cape's is steeper
HIP_P = .5
GAM_RUN, GAM_RISE, GAM_UP = 1.8, 2.7, .45
ELL_P = .55
WING_IN = .5
WING_W = {2: 6.0, 3: 7.0, 4: 8.0}
CD_S, CD_L = 7.8, 9.3         # barn depth (its ridge lands on a grid line: 4D - .6 - CD/2)
DOOR = (1.1, 3.25)            # door width, head (level with the ground-floor window heads)
SIDE_DOOR = (1.7, 3.25)       # a Greek door with its sidelights
WINS = {2: WIN2, 3: WIN3}
MAIN_D = {"side": {2: 11.0, 3: 12.0, 4: 12.0}, "gambrel": {2: 11.0, 3: 12.0, 4: 12.0},
          "hip": {2: 11.0, 3: 12.0, 4: 12.0}, "cape": {2: 10.0, 3: 10.0, 4: 10.0},
          "temple": {2: 14.0, 3: 14.0, 4: 14.0}, "twin": {2: 13.0, 3: 13.0, 4: 13.0}}
TW = 14.0                     # a temple front's width when a side wing fills the rest of the lot
DEFAULT = dict(kind="side", storeys=2, doors=1, units=0, brick=None, brick_ends=None, entry="fan", portico=False,
               porch=False, walk=False, lantern=False, dormers=False, shutters=None, door="Black", lites="6",
               wall="Clapboard", roof_mat="SlateDark", ell="MID", ell_mat=None, wings="near", woodshed=False,
               barn="gable", barn_h="LOW", barn_mat="BoardBatten", barn_roof=None, cupola=False, lofts=False,
               flats=False, hand="L", corner=False)
ODD = "Federal front: odd bays, the door on the middle one"
WOOD = "a woodshed: board walls, one door and one window a side"


def fbays(a, b, pier=1.5, step=3.1, odd=True):
    """Window bays from a to b, at most `step` apart: an odd number (a centre bay for the door) or an even one."""
    L = b - a - 2 * pier
    k = max(1, math.ceil(L / step))
    if odd and k % 2:
        k += 1
    if not odd and k % 2 == 0:
        k += 1
    return [a + pier + L * j / k for j in range(k + 1)]


def dentils(m, x0, x1, yw, top, s, mat):
    """LOD0: a Federal dentil course on the frieze of an eave wall along x at yw; s = -1 faces -y, +1 faces +y."""
    k = int((x1 - x0 - .3) / .22)
    y0, y1 = sorted((yw + s * (.07 + E), yw + s * .17))
    for j in range(k + 1):
        x = x0 + .15 + j * .22
        wbox(m, x, x + .09, y0, y1, top - .21, top - .11, mat, ("y+" if s < 0 else "y-",))


def sspread(a, b):
    """Window bays for a shuttered wall: piers 1.3-1.8 m (the open shutters clear the corner boards) and bays
    2.15-3.1 m apart (neighbouring shutters never touch); the fewest bays that fit."""
    L = b - a
    if L < 2 * 1.3 + 2.15:
        return [(a + b) / 2]
    for k in range(1, 30):
        for p in (1.5, 1.4, 1.6, 1.3, 1.7, 1.8):
            s = (L - 2 * p) / k
            if 2.15 <= s <= 3.1:
                return [a + p + s * j for j in range(k + 1)]
    return spread(a, b, pier=1.5)


def entrance(m, g, x, yw, kind, dw, dh, lod, mat=TRIM, step=True):
    """The granite step and the door surround on a street wall at yw (facing -Y): 'fan' a Federal fanlight
    (radiating muntins over the transom) between pilasters under an entablature; 'side' Greek sidelights (posts and
    glass in the door recess) under a deep entablature."""
    if step:
        wbox(m, x - dw / 2 - .45, x + dw / 2 + .45, yw - .55, yw - E, 0.0, .16, "Greystone", ("z-",))
    if lod == 2:
        return
    a = dw / 2 + .16
    for s in (-1, 1):                                  # pilasters, clear of the casings (they end at dw/2 + .14)
        x0, x1 = sorted((x + s * a, x + s * (a + .16)))
        wbox(m, x0, x1, yw - .12, yw - E, .16 + E, dh + .2, mat, ("y+", "z-"))
    deep = .62 if kind == "side" else .42
    wbox(m, x - a - .2, x + a + .2, yw - .18, yw - E, dh + .22 + E, dh + deep, mat, ("y+",))
    if lod == 0:
        wbox(m, x - a - .28, x + a + .28, yw - .26, yw - E, dh + deep + E, dh + deep + .07, mat, ("y+",))
    if kind == "side":                                 # sidelights: two posts and two tall panes beside the leaf
        for s in (-1, 1):
            p0, p1 = sorted((x + s * .43, x + s * .5))
            wbox(m, p0, p1, yw + .02, yw + .155, E, dh - .45 - E, mat, ("y+", "z-", "z+"))
            q0, q1 = sorted((x + s * .51, x + s * (dw / 2 - .02)))
            g.facing([(q0, yw + .15, .35), (q1, yw + .15, .35), (q1, yw + .15, dh - .5), (q0, yw + .15, dh - .5)],
                     (0, -1, 0), "Glass")
    elif lod == 0:                                     # the fan: muntins radiating over the transom glass
        zc, r = dh - .45, dw / 2 - .04
        for k in range(1, 6):
            t = math.pi * k / 6
            cx, cz = x - math.cos(t) * r, zc + math.sin(t) * min(r, .41)
            ux, uz = cx - x, cz - zc
            L = math.hypot(ux, uz)
            nx, nz = -uz / L * .012, ux / L * .012
            sx, sz = x + ux / L * .1, zc + uz / L * .1          # from a hub .1 m out, so no two muntins overlap
            m.facing([(sx - nx, yw + .14, sz - nz), (sx + nx, yw + .14, sz + nz), (cx + nx, yw + .14, cz + nz),
                      (cx - nx, yw + .14, cz - nz)], (0, -1, 0), mat)


def portico(m, x, yw, lod, roof_mat, w=2.8, d=1.6):
    """A pedimented portico over a door: two columns, a beam and a little front-gabled roof (eave 3.55)."""
    ze, zr = LOW, LOW + w / 2 * .6
    gable_roof(m, x - w / 2, x + w / 2, yw - d, yw - 2 * E, ze, zr, lod, roof_mat, over=(.25, -2 * E), sides=("e", "e"))
    t = Mesh()                                         # the tympanum: a closed triangle (rule 15)
    yf = yw - d + .02
    t.facing([(x - w / 2, yf, ze), (x + w / 2, yf, ze), (x, yf, zr - .05)], (0, -1, 0), TRIM)
    t.facing([(x - w / 2, yf, ze), (x, yf, zr - .05), (x + w / 2, yf, ze)], (0, 1, 0), TRIM)
    roof_check(m, t, "portico tympanum")
    wbox(m, x - w / 2 + .05, x + w / 2 - .05, yw - d + .03, yw - .3, ze - .32, ze - .01, TRIM, ("y+",))   # beam
    for s in (-1, 1):
        cx = x + s * (w / 2 - .25)
        wbox(m, cx - .13, cx + .13, yw - d + .1, yw - d + .36, .16 + E, ze - .32 - E, TRIM, ("z+",))
        if lod == 0:
            wbox(m, cx - .17, cx + .17, yw - d + .06, yw - d + .40, .16 + E, .4, TRIM, ("z-",))


def build(lod, W=2, D=5, **variant):
    variant.pop("lots", None)
    v = dict(DEFAULT, **variant)
    if lod:                                            # far views: no shutters (LOD1 budget)
        v["shutters"] = None
    corner = v["corner"]
    if corner:
        v["wings"] = "twin" if W >= 3 else "near"
        v["hand"] = "L"
    kind, n = v["kind"], v["storeys"]
    cape, temple, twin_t = kind == "cape", kind == "temple", kind == "twin"
    gam, hip = kind == "gambrel", kind == "hip"
    flats = v["flats"]
    XH = 4.0 * W - SM
    XL = (-4.0 * W + 2.65) if corner else -XH
    if corner:
        MD = max(MAIN_D[kind][W], 12.5)
        yF = -4.0 * D + (2.0 if v["portico"] else 1.0)
    else:
        MD = min(MAIN_D[kind][W], 8.6 if v["porch"] else 9.2 if v["portico"] else 9.6) if D == 3 else MAIN_D[kind][W]
        yF = -4.0 * D + ((3.1 if v["porch"] else 2.0 if v["portico"] else 1.4) if D == 3 else SET)
    yR = yF + MD
    end = 4.0 * D - .6
    ym = (yF + yR) / 2
    top = LOW if cape else TOPS[n]
    win = WIN1 if cape else WINS[n]
    brick = v["brick"]
    wmat = brick or v["wall"]
    frieze = .5 if (temple or twin_t) else .3
    trim = dict(door=v["door"], shutters=v["shutters"], lites=v["lites"], lean="bare" if lod else True)
    if brick:
        trim = dict(trim, masonry="Dressed", reveal=brick, shutters=v["shutters"])
    strim = dict(trim, simple=True) if flats else trim
    gtrim = dict(trim, shutters=None)
    belts = (3.75, 6.85)[:n - 1] if brick else ()
    bmat = "Dressed" if brick else TRIM
    main = style(top, [(0.0, top, wmat)], win, belts=belts, frieze=frieze, belt_mat=bmat)
    ends_mat = v["brick_ends"] or wmat
    end_trim = dict(trim, masonry="Dressed", reveal=ends_mat) if v["brick_ends"] else strim
    endst = style(top, [(0.0, top, ends_mat)], win, belts=belts, frieze=frieze, belt_mat=bmat)
    gmat = ends_mat
    m, g = Mesh(), Mesh()

    # ---- the main block's x extent (a temple on a wide lot leaves room for its side wing; corners use full width)
    wing_side = temple and W >= 3 and not corner
    MX1 = XL + TW if wing_side else XH

    # ---- the street front
    dw, dh = SIDE_DOOR if v["entry"] == "side" else DOOR
    if cape:                                           # a cape's door stands under its low eave
        dw, dh = 1.0, 2.7
    units = v["units"]
    waive = {}
    holes, omit = [], []
    if units:                                          # a brick row: units side by side, three bays each
        uw = (MX1 - XL) / units
        bays, doors = [], []
        for k in range(units):
            a0 = XL + uw * k
            ub = [a0 + uw * f for f in (.2, .5, .8)]
            bays += ub
            doors.append(ub[2] if k % 2 == 0 else ub[0])   # doors paired at the shared walls
        waive = {"balance": "a brick row: each house's door at its side bay, paired with its neighbour's",
                 "rhythm": "the row's houses repeat three bays each"}
    elif twin_t:
        a_, b_ = XL + 1.5, -1.5                          # the two side-hall doors at +-1.5
        k_ = math.ceil((b_ - a_) / 3.1)
        half = [a_ + (b_ - a_) * j / k_ for j in range(k_ + 1)]
        bays = half + [-c for c in half][::-1]
        doors = [-1.5, 1.5]
        waive = {"balance": "twin Greek fronts: the two side-hall doors meet at the middle"}
    elif temple:
        bays = fbays(XL, MX1, pier=1.9, odd=False) if (corner and W == 2) else fbays(XL, MX1, pier=2.0)
        doors = [bays[0]]
        waive = {"balance": "Greek Revival side-hall plan: the door in the end bay under the pediment"}
    elif v["doors"] == 2:
        bays = fbays(XL, MX1, odd=False)
        doors = [bays[len(bays) // 2 - 1], bays[len(bays) // 2]]
        waive = {"balance": "a Federal double house: twin doors in the middle bays"}
    else:
        bays = fbays(XL, MX1)
        doors = [bays[len(bays) // 2]]
    fw = Wall((XL, yF), (MX1, yF))
    for c in doors[1:]:                                # extra doors: holes in wall coords, their windows omitted
        u = fw.u_of(c)
        holes.append((u - dw / 2, u + dw / 2, 0.0, dh, "door"))
        omit.append((c, 0))
    cuts = [(c - dw / 2 - .5, c + dw / 2 + .5) for c in doors]
    wall(m, g, main, (XL, yF), (MX1, yF), "x", "x" if not wing_side else "c", bays, lod, door=(doors[0], dw, dh),
         trim=trim, waive=waive or None, plinth_cuts=cuts, holes=holes, omit=omit)
    if lod == 0 and not (temple or twin_t):
        dentils(m, XL, MX1, yF, top, -1, bmat)
    for c in doors:
        entrance(m, g, c, yF, v["entry"], dw, dh, lod, "Dressed" if brick else TRIM, step=not v["porch"])
        if v["portico"]:
            portico(m, c, yF, lod, v["roof_mat"])
    if v["porch"]:                                     # a Greek porch across the temple front
        pst = [XL + .15 + (MX1 - XL - .3) * j / max(1, round((MX1 - XL) / 3.0)) for j in range(round((MX1 - XL) / 3.0) + 1)]
        if lod == 2:
            pst = [pst[0], pst[-1]]
        porch(m, XL + E, MX1 - E, yF, 2.4, lod, stair=(doors[0] - .7, doors[0] + .7), mat=v["roof_mat"], posts=pst,
              open_sides=("l", "r"), zf=.16, zt=LOW, skirt=False)
    if (temple or twin_t) and lod < 2:                 # corner pilasters under the deep frieze
        for px in ((XL, MX1) if temple else (XL, 0.0, XH)):
            a, b = (px - .08, px + .42) if px == XL else (px - .42, px + .08) if px != 0.0 else (-.25, .25)
            wbox(m, a, b, yF - .10, yF - E, .75 + .02, top - frieze - .02, TRIM, ("y+",))

    # ---- side walls (the right one hides behind a temple's side wing; left gets a side-street entrance on corners)
    sb = sspread(yF, yR)
    if corner:
        sdoor = (sb[len(sb) // 2], dw, dh)
        wall(m, g, endst, (XL, yR), (XL, yF), "x", "x", sb, lod, door=sdoor, trim=end_trim,
             waive={"balance": "Federal corner captain's house side-street entrance"})
        from lt_designs.boardwalk import _side_porch
        sy0, sy1 = yF + .4, yR - .4
        sp = [sy0 + .15 + (sy1 - sy0 - .3) * j / max(1, round((sy1 - sy0) / 3.0))
              for j in range(max(1, round((sy1 - sy0) / 3.0)) + 1)]
        if lod == 2:
            sp = [sp[0], sp[-1]]
        _side_porch(m, XL, sy0, sy1, 2.2, lod, zf=.16, zt=LOW, posts=sp, mat=v["roof_mat"], rail=False, roof=True)
    else:
        wall(m, g, endst, (XL, yR), (XL, yF), "x", "x", sb, lod, trim=end_trim)
    if wing_side:
        yW0, yW1 = yF + 1.5, yF + 9.5
        zwr = LOW + (yW1 - yW0) / 2 * .65
        om = [(c, f) for c in sb for f, (_, zb_, zt_) in enumerate(win) if yW0 - .6 < c < yW1 + .6 and zb_ < zwr + .3]
        wall(m, g, endst, (MX1, yF), (MX1, yR), "x", "x", sb, lod, trim=end_trim, omit=om,
             waive={"glass": "the side wing covers the lower windows", "rhythm": "the side wing covers the lower windows"})
    else:
        wall(m, g, endst, (XH, yF), (XH, yR), "x", "x", sb, lod, trim=end_trim)

    # ---- the main roof
    th = .16
    if temple or twin_t:                               # gable fronts: ridges along y, pedimented gables front and back
        spans = [(XL, MX1)] if temple else [(XL, -E), (E, XH)]
        zrs = []
        for a0, a1 in spans:
            xc, half = (a0 + a1) / 2, (a1 - a0) / 2
            zr = top + half * PITCH
            zrs.append(zr)
            lo_ = (a0 - .35, top - .35 * PITCH) if a0 != E else (a0, top)
            hi_ = (a1 + .35, top - .35 * PITCH) if a1 != -E else (a1, top)
            slab(m, [lo_, (xc, zr), hi_], yF - .45, yR + .35, lambda a, q, z: (q, a, z), lod, v["roof_mat"], end=TRIM,
                 what="temple roof")
            if lod == 0:
                wbox(m, xc - .09, xc + .09, yF - .45 + 3 * E, yR + .35 - 3 * E, zr + th - .02, zr + th + .07, v["roof_mat"],
                     ("z-",))
            gw = [(xc, 1.6 if half > 6 else 1.0, top + .7, top + 1.6)] if half * PITCH > 2.3 else []
            gable_wall(m, g, (a0, yF), (a1, yF), top, zr, lod, wmat, wins=gw, trim=dict(gtrim, simple=True))
            gable_wall(m, g, (a1, yR), (a0, yR), top, zr, lod, wmat, trim=gtrim)
            if lod < 2:                                # the pediment's horizontal cornice across the gable base
                wbox(m, a0 - (.12 if a0 < -1 else -2 * E), a1 + (.12 if a1 > 1 else -2 * E), yF - .30, yF - .074,
                     top - .12, top - .02, TRIM, ("y+",))
            chimney(m, xc, yF + MD * .3, .4, .4, zr - 1.0, zr + 1.0, lod)
        zr = max(zrs)
        rear_slope = None                              # the rear is a gable wall: back blocks butt it
        front_top = None
    elif hip:
        rise = (MD / 2 + .35) * HIP_P
        zr = pavilion_roof(m, XL - .35, MX1 + .35, yF - .35, yR + .35, top, rise, lod, v["roof_mat"], finial=False)
        rear_slope = HIP_P
        front_top = lambda q: top + (q - yF + .35) * HIP_P - .35 * HIP_P
        for cx in (XL + 2.2, MX1 - 2.2):
            for cy in (ym - 1.6, ym + 1.6):
                chimney(m, cx, cy, .35, .45, top, zr + .3, lod)
    else:                                              # side gable, gambrel or cape: ridge along x
        o = .35
        if gam:
            k1 = GAM_RISE / GAM_RUN
            zk = top + GAM_RISE
            zr = zk + (MD / 2 - GAM_RUN) * GAM_UP
            prof = [(yF - o, top - o * k1), (yF + GAM_RUN, zk), (ym, zr), (yR - GAM_RUN, zk), (yR + o, top - o * k1)]
            shape = (zk, GAM_RUN)
            front_top = lambda q: top + min(q - yF, GAM_RUN) * k1 + max(0.0, q - yF - GAM_RUN) * GAM_UP
            rear_slope = k1
        else:
            P = CAPE_P if cape else PITCH
            zr = top + MD / 2 * P
            prof = [(yF - o, top - o * P), (ym, zr), (yR + o, top - o * P)]
            shape = None
            front_top = lambda q: top + (q - yF) * P
            rear_slope = P
        gw = [(ym - 1.6, .8, top + .9, top + 2.2), (ym + 1.6, .8, top + .9, top + 2.2)] if zr - top > 3.2 else \
             [(ym, .8, top + .5, top + 1.6)]
        gt = end_trim if v["brick_ends"] else gtrim
        gable_wall(m, g, (XL, yR), (XL, yF), top, zr, lod, gmat, wins=gw, trim=gt, shape=shape)
        gable_wall(m, g, (XH, yF), (XH, yR), top, zr, lod, gmat, wins=gw, trim=gt, shape=shape)
        slab(m, prof, XL - .3, XH + .3, lambda a, q, z: (a, q, z), lod, v["roof_mat"], end=TRIM, what="main roof")
        if lod == 0:
            wbox(m, XL - .3 + 3 * E, XH + .3 - 3 * E, ym - .09, ym + .09, zr + .14, zr + .23, v["roof_mat"], ("z-",))
        if cape:                                       # a big centre chimney (two on a double)
            for cx in ([0.0] if v["doors"] == 1 else [XL / 2, XH / 2]):
                chimney(m, cx, ym, .7, .6, zr - 1.4, zr + .9, lod)
        else:                                          # paired end chimneys, in from each gable
            for cx in (XL + .65, XH - .65):
                for cy in (ym - 1.7, ym + 1.7):
                    chimney(m, cx, cy, .45, .4, top - .2, zr + .8, lod)
            if units:                                  # and on every party wall of a row
                for k in range(1, units):
                    chimney(m, XL + (MX1 - XL) * k / units, ym, .5, .45, zr - 1.0, zr + .9, lod)
        if v["dormers"]:
            th_ = .16
            top_of = lambda o_: front_top(-o_) + th_
            picks = bays[1::2] if len(bays) > 3 else bays
            for cx in picks:
                if any(abs(cx - d_) < .05 for d_ in doors) and len(picks) > 2:
                    continue
                dormer(m, g, lambda o_, t, z: (t, -o_, z), top_of, -(yF + (.25 if gam else 1.0)), cx, 1.2, lod,
                       wmat if not brick else "Clapboard", v["roof_mat"], gtrim, rise=.5, height=1.3, lites=v["lites"])
    xm_main = (XL + MX1) / 2
    if v["walk"]:                                      # the widow's walk straddling the ridge
        hw = 1.6
        slope = HIP_P if hip else PITCH
        z0 = zr - (hw + .3) * slope - (1.6 * HIP_P if hip else 0) - .1
        widows_walk(m, xm_main - hw - .4, xm_main + hw + .4, ym - hw, ym + hw, z0, zr + .45, lod, wmat if not brick else TRIM)
    if v["lantern"]:
        cupola(m, xm_main, ym, zr + .16, lod, wmat if not brick else "Clapboard", v["roof_mat"], v["shutters"] or v["door"],
               a=1.1, sink=1.1 * HIP_P + .5, h=1.9)

    # ---- the temple's side wing: 1.5 storeys, side-gabled, its own door
    if wing_side:
        wst = style(LOW, [(0.0, LOW, wmat)], WIN1, belts=(), frieze=.3)
        wb_ = fbays(MX1, XH, pier=1.5, step=2.9, odd=True)
        wall(m, g, wst, (MX1, yW0), (XH, yW0), "c", "x", wb_, lod, door=(wb_[len(wb_) // 2], 1.0, 2.6), trim=trim,
             plinth_cuts=[(MX1 - .1, MX1 + .1)])
        wall(m, g, wst, (XH, yW0), (XH, yW1), "x", "x", sspread(yW0, yW1), lod, trim=strim)
        wall(m, g, wst, (XH, yW1), (MX1, yW1), "x", "c", fbays(MX1, XH, pier=1.5, step=2.9), lod, trim=strim,
             plinth_cuts=[(MX1 - .1, MX1 + .1)])
        wp = .65
        yWm = (yW0 + yW1) / 2
        slab(m, [(yW0 - .35, LOW - .35 * wp), (yWm, zwr), (yW1 + .35, LOW - .35 * wp)], MX1 + 3 * E, XH + .3,
             lambda a, q, z: (a, q, z), lod, v["roof_mat"], end=TRIM, what="side wing roof")
        gable_wall(m, g, (XH, yW0), (XH, yW1), LOW, zwr, lod, wmat, wins=[(yWm, .8, LOW + .4, LOW + 1.5)], trim=gtrim)
        if lod == 0:
            wbox(m, MX1 + 6 * E, XH + .3 - 3 * E, yWm - .09, yWm + .09, zwr + .14, zwr + .23, v["roof_mat"], ("z-",))

    # ---- the back of the lot: ell(s), woodshed, carriage barn, round the service court
    rear(m, g, lod, v, W, D, XL, XH, MX1, yR, end, top, zr, rear_slope, main, trim, strim, gtrim, wmat, win)

    if v["hand"] == "R":                               # mirrored whole (rule 23)
        for mm in (m, g):
            mm.v = [(-x, y, zz) for x, y, zz in mm.v]
            mm.f = [f[::-1] for f in mm.f]
    finish(m, g)


def rear(m, g, lod, v, W, D, XL, XH, MX1, yR, end, top, zr_main, rear_slope, main, trim, strim, gtrim, wmat, win):
    flats = v["flats"]
    corner = v.get("corner", False)
    EH = LOW if v["ell"] == "LOW" else MID
    CH = LOW if v["barn_h"] == "LOW" else MID
    WW = ({2: 6.8, 3: 6.4}.get(W, WING_W[W]) if corner else WING_W[W])
    room = end - yR
    CD = (9.8 if D <= 4 else 10.3) if corner else (6.8 if D == 3 else (CD_S if room < 20 else CD_L))
    yC = end - CD
    yk = (yC + end) / 2
    if yC - yR < 9.0:                                  # no room for a woodshed between ell and barn
        v = dict(v, woodshed=False)
    twin = v["wings"] == "twin" and W >= 3
    fx = -1 if v["wings"] == "far" else 1
    o = .4                                             # barn eaves: .4, off the audit's 0.25 m ray grid

    def bwall(st, A, B, s, e, bays, door=None, **kw):
        if fx == 1:
            return wall(m, g, st, A, B, s, e, bays, lod, door=door, **kw)
        along_x = abs(A[1] - B[1]) < 1e-9
        bb = [-c for c in bays] if along_x else list(bays)
        dd = None if door is None else ((-door[0] if along_x else door[0]),) + tuple(door[1:])
        if along_x and kw.get("omit"):
            kw = dict(kw, omit=[(-c, f) for c, f in kw["omit"]])
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

    # the main house's rear wall: the yard part with the garden door, the part behind the ell, the outer strip
    wa, wb = XL + WING_IN, XL + WING_IN + WW
    rwa, rwb = XH - WING_IN - WW, XH - WING_IN
    zw = EH + WW / 2 * ELL_P                           # the ell's ridge
    into = rear_slope is not None and zw + .16 > top - .05   # the ell roof runs on into the main rear slope
    if into:
        fwd = (zw + .16 - top) / rear_slope + .5
        assert zw < zr_main - .3, f"ell ridge {zw:.2f} would run over the main ridge {zr_main:.2f}"
    else:
        assert zw + .16 < top + (0 if rear_slope is not None else 1.0), "ell roof above a gable-end rear wall's eave"
        fwd = -2 * E
    gwv = {"balance": "the garden door opens onto the service court"}
    rx1 = MX1 if fx == 1 else -XL                      # the main block's far side in build coordinates
    over = [(f, zb_) for f, (_, zb_, _) in enumerate(win)]
    behind = [((wa + wb) / 2, f) for f, zb_ in over if zb_ < (zw + .3 if not into else 99)]
    fe = abs(top - EH) > .01                           # a rear frieze level with the ell's would end flush on its wall
    if twin:
        cb_mid = sspread(wb, rwa)
        ydx = nearest(cb_mid, (wb + rwa) / 2)
        wall(m, g, main, (XH, yR), (rwb, yR), "x", "c", [], lod, trim=strim, frieze_on=fe)
        wall(m, g, main, (rwa, yR), (wb, yR), "c", "c", cb_mid, lod, door=(ydx, 1.0, 2.95), trim=strim, waive=gwv,
             frieze_on=fe)
        wall(m, g, main, (wa, yR), (XL, yR), "c", "x", [], lod, trim=strim, frieze_on=fe)
        for A, B, xc_w in (((wb, yR), (wa, yR), (wa + wb) / 2), ((rwb, yR), (rwa, yR), (rwa + rwb) / 2)):
            cb = [xc_w]
            ob = [(xc_w, f) for _, f in behind]
            if len(ob) < len(win):
                wall(m, g, main, A, B, "-", "-", cb, lod, z0=EH, trim=strim, omit=ob,
                     waive={"glass": "the ell covers the lower floors", "shape": "the ell covers the lower floors"})
            else:
                wall(m, g, main, A, B, "-", "-", [], lod, z0=EH, trim=strim, frieze_on=fe)
    else:
        xr = MX1 if fx == 1 else -XL
        rb_ = sspread(wb, xr)
        ydx = nearest(rb_, (wb + xr) / 2)
        bwall(main, (xr, yR), (wb, yR), "x", "c", rb_, door=(ydx, 1.0, 2.95), trim=strim, waive=gwv,
              frieze_on=fe)
        cb = [(wa + wb) / 2]
        if len(behind) < len(win):
            bwall(main, (wb, yR), (wa, yR), "-", "-", cb, z0=EH, trim=strim, omit=behind,
                  waive={"glass": "the ell covers the lower floors", "shape": "the ell covers the lower floors"})
        else:
            bwall(main, (wb, yR), (wa, yR), "-", "-", [], z0=EH, trim=strim, frieze_on=fe)
        bwall(main, (wa, yR), (XL, yR), "c", "x", [], trim=strim, frieze_on=fe)

    if lod == 0 and fe and rear_slope is not None:   # the dentil course on the rear, clear of the ells
        if twin:
            segs = [(XL, wa - .5), (wb + .5, rwa - .5), (rwb + .5, XH)]
        else:
            segs = [(XL, wa - .5), (wb + .5, (MX1 if fx == 1 else -XL))]
            if fx == -1:
                segs = [(-b_, -a_) for a_, b_ in segs]
        for a_, b_ in segs:
            if b_ - a_ > 1.0:
                dentils(m, a_, b_, yR, top, 1, main["belt_mat"])
    # the barn's roof profile
    if v["barn"] == "gambrel":
        ck = GAM_RISE / GAM_RUN
        czk = CH + GAM_RISE
        zc = czk + (CD / 2 - GAM_RUN) * GAM_UP
        cprof = [(yC - o, CH - o * ck), (yC + GAM_RUN, czk), (yk, zc), (end - GAM_RUN, czk), (end + o, CH - o * ck)]
        cshape = (czk, GAM_RUN)
        car_in = lambda z: (z - CH) / ck if z <= czk else GAM_RUN + (z - czk) / GAM_UP
        cp = None
    else:
        ws_top = LOW + WW / 2 * ELL_P if v["woodshed"] else zw
        cp = max(.75, (ws_top + .5 - CH) / (CD / 2))
        zc = CH + CD / 2 * cp
        cprof = [(yC - o, CH - o * cp), (yk, zc), (end + o, CH - o * cp)]
        cshape = None
        car_in = lambda z: (z - CH) / cp

    # the ell (and the woodshed behind it)
    emat = v["ell_mat"] or ("Clapboard" if v["brick"] else wmat)
    bw = [(.9, 1.0, 2.7)] if EH == LOW else WIN2
    wst = style(EH, [(0.0, EH, emat)], bw, belts=())
    etrim = dict(gtrim, simple=True) if flats else gtrim
    yE = yC if not v["woodshed"] else yR + max(5.0, (yC - yR) * .55)
    span = yE - yR
    ys = spread(yR, yE, pier=1.1, step=3.1)
    kw = {"balance": "the flats entrance opens onto the court" if flats else "the kitchen door opens onto the service court"}
    butts = []
    if twin:
        for side_i, (xa_, xb_) in enumerate(((wa, wb), (rwa, rwb))):
            if side_i == 0:
                wall(m, g, wst, (xb_, yR), (xb_, yE), "c", "c" if not v["woodshed"] else "x", ys, lod,
                     door=(ys[0], 1.0, 2.6 if EH == LOW else 2.95), trim=etrim, waive=kw)
                wall(m, g, wst, (xa_, yE), (xa_, yR), "c" if not v["woodshed"] else "x", "c", ys, lod, trim=etrim)
            else:
                wall(m, g, wst, (xa_, yE), (xa_, yR), "c" if not v["woodshed"] else "x", "c", ys, lod,
                     door=(ys[0], 1.0, 2.6 if EH == LOW else 2.95), trim=etrim, waive=kw)
                wall(m, g, wst, (xb_, yR), (xb_, yE), "c", "c" if not v["woodshed"] else "x", ys, lod, trim=etrim)
            if v["woodshed"]:
                est = style(EH, [(0.0, EH, emat)], bw, belts=())
                wall(m, g, est, (xb_, yE), (xa_, yE), "x", "x", [], lod, z0=LOW, trim=etrim)
                gable_wall(m, g, (xb_, yE), (xa_, yE), EH, zw, lod, emat, wins=[((xa_ + xb_) / 2, .7, EH + .5, EH + 1.5)], trim=etrim)
                aft = .3
            else:
                if zw + .16 < CH:
                    aft = -2 * E
                    butts.append((xa_, xb_))
                else:
                    aft = car_in(zw + .16) + .5
                assert aft < CD / 2 + .3, f"ell roof would run through the barn ridge ({aft:.2f} m)"
            gable_roof(m, xa_, xb_, yR, yE, EH, zw, lod, v["roof_mat"], over=(fwd, aft), sides=("e", "e"))
            if lod < 2:
                chimney(m, (xa_ + xb_) / 2, yR + span * .55, .4, .4, zw - .8, zw + 1.1, lod)
            if v["woodshed"]:
                zs = LOW + WW / 2 * ELL_P
                sst = style(LOW, [(0.0, LOW, v["barn_mat"])], [(.9, 1.0, 2.7)], belts=(), plinth=None)
                sy = [(yE + yC) / 2]
                if side_i == 0:
                    wall(m, g, sst, (xb_, yE), (xb_, yC), "x", "c", sy, lod, door=(sy[0], 1.3, 2.6),
                         trim=dict(gtrim, simple=True), waive={"balance": "the woodshed door opens onto the court", "glass": WOOD})
                    wall(m, g, sst, (xa_, yC), (xa_, yE), "c", "x", sy, lod, trim=dict(gtrim, simple=True), waive={"glass": WOOD})
                else:
                    wall(m, g, sst, (xa_, yC), (xa_, yE), "c", "x", sy, lod, door=(sy[0], 1.3, 2.6),
                         trim=dict(gtrim, simple=True), waive={"balance": "the woodshed door opens onto the court", "glass": WOOD})
                    wall(m, g, sst, (xb_, yE), (xb_, yC), "x", "c", sy, lod, trim=dict(gtrim, simple=True), waive={"glass": WOOD})
                aft = car_in(zs + .16) + .5
                assert aft < CD / 2 + .3, f"woodshed roof would run through the barn ridge ({aft:.2f} m)"
                gable_roof(m, xa_, xb_, yE, yC, LOW, zs, lod, v["barn_roof"] or v["roof_mat"], over=(-2 * E, aft), sides=("e", "e"))
    else:
        bwall(wst, (wb, yR), (wb, yE), "c", "c" if not v["woodshed"] else "x", ys, door=(ys[0], 1.0, 2.6 if EH == LOW else 2.95),
              trim=etrim, waive=kw)
        bwall(wst, (wa, yE), (wa, yR), "c" if not v["woodshed"] else "x", "c", ys, trim=etrim)
        if v["woodshed"]:                              # the ell's back end stands over the woodshed
            est = style(EH, [(0.0, EH, emat)], bw, belts=())
            bwall(est, (wb, yE), (wa, yE), "x", "x", [], z0=LOW, trim=etrim)
            bgable((wb, yE), (wa, yE), EH, zw, emat, wins=[((wa + wb) / 2, .7, EH + .5, EH + 1.5)], trim=etrim)
            aft = .3
        else:
            if zw + .16 < CH:                          # a low ell under a tall barn butts the barn's front wall
                aft = -2 * E
                butts.append(fx)
            else:
                aft = car_in(zw + .16) + .5
            assert aft < CD / 2 + .3, f"ell roof would run through the barn ridge ({aft:.2f} m)"
        broof(wa, wb, yR, yE, EH, zw, lod, v["roof_mat"], over=(fwd, aft))
        if lod < 2:
            chimney(m, fx * (wa + wb) / 2, yR + span * .55, .4, .4, zw - .8, zw + 1.1, lod)
        if v["woodshed"]:
            zs = LOW + WW / 2 * ELL_P
            sst = style(LOW, [(0.0, LOW, v["barn_mat"])], [(.9, 1.0, 2.7)], belts=(), plinth=None)
            sy = [(yE + yC) / 2]
            bwall(sst, (wb, yE), (wb, yC), "x", "c", sy, door=(sy[0], 1.3, 2.6), trim=dict(gtrim, simple=True),
                  waive={"balance": "the woodshed door opens onto the court", "glass": WOOD})
            bwall(sst, (wa, yC), (wa, yE), "c", "x", sy, trim=dict(gtrim, simple=True), waive={"glass": WOOD})
            aft = car_in(zs + .16) + .5
            assert aft < CD / 2 + .3, f"woodshed roof would run through the barn ridge ({aft:.2f} m)"
            broof(wa, wb, yE, yC, LOW, zs, lod, v["barn_roof"] or v["roof_mat"], over=(-2 * E, aft))

    # the carriage barn across the back
    bmat_ = v["barn_mat"]
    rmat = v["barn_roof"] or v["roof_mat"]
    if CH == LOW:
        cst = style(CH, [(0.0, CH, bmat_)], [(.8, 1.4, 2.6)], belts=(), plinth=(.4, .04, "Greystone"))
        cdoor = (2.2, 2.9)
    else:
        bwins = [(.9, 1.3, 2.9), (.9, 4.4, 5.9)] if flats else [(.8, 1.6, 2.9), (.9, 4.1, 5.5)]
        cst = style(CH, [(0.0, CH, bmat_)], bwins, belts=(3.75,) if flats else (), plinth=(.4, .04, "Greystone"))
        cdoor = (1.1, 2.95) if flats else (2.2, 2.9)
    btrim = dict(gtrim, simple=True)
    cstep = 3.1 if flats else 2.75
    cwv = {"balance": "the flats entrance opens onto the court" if flats else "carriage doors onto the service court"}
    if twin:
        cb = [(wb + rwa) / 2] if (not flats and rwa - wb < 7.2) else spread(wb, rwa, pier=1.2, step=cstep)
        cdx = nearest(cb, (wb + rwa) / 2)
        wall(m, g, cst, (wb, yC), (rwa, yC), "c", "c", cb, lod, door=(cdx,) + cdoor, trim=btrim, waive=cwv)
        wall(m, g, cst, (XL, yC), (wa, yC), "x", "c", [], lod, trim=btrim)
        wall(m, g, cst, (rwb, yC), (XH, yC), "c", "x", [], lod, trim=btrim)
        for xa_, xb_ in butts:
            wall(m, g, cst, (xa_, yC), (xb_, yC), "-", "-", [], lod, z0=EH, trim=btrim)
    else:
        cb = [(wb + XH) / 2] if (not flats and XH - wb < 7.2) else spread(wb, XH, pier=1.2, step=cstep)
        cdx = nearest(cb, (wb + XH) / 2)
        bwall(cst, (wb, yC), (XH, yC), "c", "x", cb, door=(cdx,) + cdoor, trim=btrim, waive=cwv)
        bwall(cst, (XL, yC), (wa, yC), "x", "c", [], trim=btrim)
        for fx in butts:                                   # the barn front above a low ell
            bwall(cst, (wa, yC), (wb, yC), "-", "-", [], z0=EH, trim=btrim)
    fx = -1 if v["wings"] == "far" else 1
    sbc = spread(yC, end, pier=1.2, step=cstep)
    bwall(cst, (XL, end), (XL, yC), "x", "x", sbc, trim=btrim)
    bwall(cst, (XH, yC), (XH, end), "x", "x", sbc, trim=btrim)
    rb = spread(XL, XH, pier=1.2, step=cstep)
    bwall(cst, (XH, end), (XL, end), "x", "x", rb, trim=btrim)
    gwc = [(yk, .8, CH + .6, CH + 1.9)]
    bgable((XL, end), (XL, yC), CH, zc, bmat_, wins=gwc, trim=btrim, shape=cshape)
    bgable((XH, yC), (XH, end), CH, zc, bmat_, wins=gwc, trim=btrim, shape=cshape)
    slab(m, cprof, XL - .3, XH + .3, lambda a, q, z: (a, q, z), lod, rmat, end=TRIM, what="carriage barn roof")
    if lod == 0:
        wbox(m, XL - .3 + 3 * E, XH + .3 - 3 * E, yk - .09, yk + .09, zc + .14, zc + .23, rmat, ("z-",))
    xg = nearest(rb, (XL + XH) / 2)
    if v["barn"] == "cross":                           # a cross gable over the lane front's middle bay
        cw = 4.4
        zg = CH + cw / 2 * .9
        bgable((xg + cw / 2, end), (xg - cw / 2, end), CH, zg, bmat_, wins=[(xg, .8, CH + .5, CH + 1.45)], trim=btrim)
        broof(xg - cw / 2, xg + cw / 2, end, end, CH, zg, lod, rmat, over=(car_in(zg + .16) + .5, .47))
    if v["lofts"] and v["barn"] != "gambrel" and lod == 0:
        picks = [rb[1], rb[-2]] if W == 2 else [rb[1], rb[len(rb) // 2], rb[-2]]
        if v["barn"] == "cross":
            picks = [c for c in picks if abs(c - xg) > 3.2]
        top_of = lambda o_: CH + (end - o_) * cp + .16
        for cx in picks:
            dormer(m, g, lambda o_, t, z: (t, o_, z), top_of, end - .9, fx * cx, 1.3, lod, bmat_, rmat, btrim,
                   rise=.45, height=1.2, lites="2")
    if v["cupola"]:
        cupola(m, (XL + XH) / 2, yk, zc + .16, lod, bmat_, rmat, v["shutters"] or v["door"])

    # the court walk: garden door -> along the left ell -> barn doors (kept to one edge on twin courts so the yard stays open for planting!)
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
    if lod < 2 and corner:                                   # Lot review fix: pave side-street walk clear of barn plinth & rear plane
        wbox(m, -4.0 * W + .25, XL - .06, yR + .06, end - .06, 0.0, .05, "Paving", ("z-",))
