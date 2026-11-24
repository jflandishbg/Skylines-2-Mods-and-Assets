"""Lobstertown Boardwalk Shops (the author 2026-11-16: "mixed, built up over time"): a commercial street that grew over
decades. About half are brick commercial blocks (cast-iron shopfronts, the firm's name painted on the brick, corbelled
or bracketed cornices, flat roofs) and half are painted clapboard false fronts (a tall square front with a bracketed
cornice hiding a gable or lean-to roof, stronger paint than the grey residential streets). 1-3 storeys. Every shop
door opens at grade: at most a 15 cm step up onto a plank walk.

    build(lod, W=2, D=3, **variant)

Every lot is a row building (party walls both sides). ZC2 (Boardwalk Palaces) stays on boardwalk.py.

Variant keys (both kinds):
  kind     'brick' | 'clap'
  storeys  brick 2-3, clap 1-2
  wall, roof_mat, door (shopfront / cast-iron paint), lites, sign (atlas key without 'Sign_'), sign_side 'l' | 'r'
  corner   False | True: a LeftCorner building (the author 2026-11-17: no bare party wall at a block end). The street side
           is the left (x = XL, set in CI): the shop glass turns the corner to a corner pier, windows on every floor
           down the side street, the cornice carried round. No lettering (the game mirrors it for right corners).
brick:
  ground   'iron' (cast-iron shopfront, brick piers) | 'granite' (a granite shop storey)
  cornice  'corbel' (a brick corbel table under a brick cornice) | 'bracket' (a painted bracketed cornice)
  pediment True: a raised name block over the middle of the cornice
  skylight True: a photographer's north-light skylight on the flat roof
  back     'full' | 'store' (a lower brick stockroom behind)
clap:
  top      'flat' | 'step' (the middle of the false front stands a storey-band higher)
  roof     'gable' (one front-to-back gable per 8 m cell behind the false front) | 'shed' (a lean-to falling to the rear)
  awning   True: a shed awning on posts over the plank walk
  stock    the one-storey stockroom that fills a deep lot behind the shop (rule 17, to 0.6 m off the rear line):
           'shed' (a lean-to falling to the rear) | 'flat' (a flat roof behind a plain cornice) |
           'gable' (one low front-to-back gable per 8 m cell, for 2-storey shops)
"""
import math
from lt_kit import Mesh, Wall, finish, wall, style, gable_wall, gable_roof, shed_roof, porch, party, wbox, lbox, E, TRIM, chimney
from lt_shapes import cornice_roof
from lt_designs.shore_row import SIGN_W, SIGN_H
from lt_designs.cannery import corbels
from lt_designs.cottage import cupola

STEP = .15                    # the plank walk: one low step, the shop doors open off it (the author: entrances at grade)
WALK = 1.2                    # depth of the open walk in front of a shop without an awning
AWN = 2.6                     # awning depth (the walk under it)
CI = .40                      # corner: the side-street wall stands this far in (eaves and cornices overhang it)
BAY = 8.0 / 3                 # three window bays a cell, evenly spaced across cells too (rule 2)
PICTURESQUE = {"balance": "a commercial street grown over decades: the shop goes where trade put it "
                          "(Lobstertown standing waiver)"}
DEFAULT = dict(kind="clap", storeys=2, sign=None, sign_side="r", wall="Clapboard", roof_mat="SlateDark", door="Green",
               lites="2", ground="iron", cornice="corbel", pediment=False, skylight=False, back="full", top="flat",
               roof="gable", awning=False, stock="shed", stock_mat=None, vent=False, corner=False)
CORNER_WAIVE = {"corners": "the shop glass turns the corner to a corner pier, as on a New England commercial block"}


def side_bays(y0, y1, pitch=2.2, margin=1.2):
    """Window columns down a side-street wall from y0 to y1, at most `pitch` apart."""
    inner = y1 - y0 - 2 * margin
    if inner < 1.6:
        return [(y0 + y1) / 2]
    k = math.ceil(inner / pitch) + 1
    return [y0 + margin + inner * j / (k - 1) for j in range(k)]


def side_street(m, g, lod, st, v, XL, y_back, y_front, shop_head, trim, cast=None):
    """The side-street wall of a corner building, from the back (y_back) to the street front (y_front), outside to
    -X: shop glass round the corner from 0.75 m to 3.2 m, a window in every bay of every floor past it. cast: the
    material of the fascia over the wrapped shop glass. Returns the Wall."""
    y1 = y_front + 1.975                              # the first bay stands over the wrapped shop glass
    ys = [y1] + side_bays(y1, y_back, pitch=2.6, margin=0.0)[1:] if y_back - y1 > 3.8 else [y1]
    if len(ys) > 1:                                   # the last bay 1.4 m off the back corner
        ys = [y1] + side_bays(y1, y_back - 1.4 + 1.2, pitch=2.6, margin=0.0)[1:]
    sw = Wall((XL, y_back), (XL, y_front))
    ua, ub = sw.u_of(y_front + 3.2), sw.u_of(y_front + .75)
    shop = [(ua, ub, 0.0, shop_head, "shop")]
    om = [(y1, 0)]
    w = wall(m, g, st, (XL, y_back), (XL, y_front), "x", "x", ys, lod, trim=trim, holes=shop, omit=om,
             waive=dict(PICTURESQUE, **CORNER_WAIVE))
    if lod < 2 and cast:
        lbox(m, w, ua - .3, ub, shop_head + .01, shop_head + .4, E, .16, cast, ("in",))
    return w, ys


def shopfronts(xa, xb, pier=1.4, edge=.8, target=7.0):
    """Shop openings (x0, x1) along a front from xa to xb: about one per 7 m, piers between."""
    inner = (xb - edge) - (xa + edge)
    k = max(1, round(inner / target))
    sw = (inner - pier * (k - 1)) / k
    return [(xa + edge + j * (sw + pier), xa + edge + j * (sw + pier) + sw) for j in range(k)]


def sign_x(v, X):
    """The sign's left edge, on the 3 m atlas grid (rule 26), just left or right of the middle."""
    return -SIGN_W if v["sign_side"] == "l" or X < SIGN_W + .3 else 0.0


def paint_sign(m, v, sx, y, z0):
    """A sign painted on the wall face at y (facing -Y), 6 mm proud (rule 22)."""
    m.facing([(sx, y - .006, z0), (sx + SIGN_W, y - .006, z0), (sx + SIGN_W, y - .006, z0 + SIGN_H),
              (sx, y - .006, z0 + SIGN_H)], (0, -1, 0), "Sign_" + v["sign"])


def seams(m, lod, x0, x1, y0, y1, za, zb, mat, th=.12, step=.6):
    """Standing seams on a tin lean-to (LOD0): a raised rib every `step` m running down the slope from y0 (top
    at za + th) to y1 (zb + th). Ribs stand 3 cm proud, so nothing shares the roof's plane (rule 22)."""
    if lod or not mat.startswith("Tin"):
        return
    k = int((x1 - x0 - .3) / step)
    s = (za - zb) / (y1 - y0)
    for i in range(k + 1):
        c = x0 + .15 + (x1 - x0 - .3) * i / k
        a0, a1 = (y0 + .05, za + th - s * .05), (y1 - .05, zb + th + s * .05)
        for x, d in ((c - .02, -1), (c + .02, 1)):
            m.facing([(x, a0[0], a0[1]), (x, a1[0], a1[1]), (x, a1[0], a1[1] + .03), (x, a0[0], a0[1] + .03)],
                     (d, 0, 0), mat)
        m.facing([(c - .02, a0[0], a0[1] + .03), (c + .02, a0[0], a0[1] + .03), (c + .02, a1[0], a1[1] + .03),
                  (c - .02, a1[0], a1[1] + .03)], (0, s, 1), mat)


def plank_walk(m, XL, X, y0, y1):
    """The plank walk in front of the shop: one step up from the street, solid to the ground."""
    wbox(m, XL + E, X - E, y0, y1 - E, 0.0, STEP, "Deck", ("y+",))


# ---------------------------------------------------------------- brick commercial blocks

B_SHOP_HEAD = 3.55            # plate glass head; a cast-iron beam 3.56-3.96 over it
B_GROUND = 4.7                # the shop storey
B_FLOOR = 3.2                 # storeys above it


def _brick(lod, W, D, v):
    n = v["storeys"]
    assert 2 <= n <= 3, "a brick block is 2-3 storeys"
    win = [(1.1, 5.5 + B_FLOOR * j, 7.3 + B_FLOOR * j) for j in range(n - 1)]
    top = win[-1][2] + 1.15                          # room for the corbel table over the top lintels
    corner = v["corner"]
    X = 4.0 * W - .01
    XL = -X + CI if corner else -X
    xm = (XL + X) / 2
    sx_ = "x" if corner else "-"
    cw = (X - XL) / W
    cells = [(XL + cw * i, XL + cw * (i + 1)) for i in range(W)]
    yF = -4.0 * D + .45 + WALK                       # the street wall, behind the plank walk
    end = 4.0 * D - .6
    granite = v["ground"] == "granite"
    zg = 4.3 if granite else None                    # granite shop storey, its string course clear of the shop surrounds
    mats = [(0.0, zg, "Greystone"), (zg, top, v["wall"])] if granite else [(0.0, top, v["wall"])]
    belts = (zg + .05,) if granite else (4.9,)
    st = style(top, mats, win, belts=belts, plinth=None, corners=False, frieze=None, belt_mat="Dressed")
    trim = dict(door=v["door"], lites=v["lites"], lean=True, masonry="Dressed", reveal=v["wall"])
    m, g = Mesh(), Mesh()

    plank_walk(m, XL, X, yF - WALK, yF)
    shops = shopfronts(XL, X)
    if corner:                                       # the shop glass runs to a 0.75 m corner pier
        shops[0] = (XL + .75, shops[0][1])
    holes = [(a - XL, b - XL, 0.0, B_SHOP_HEAD, "shop") for a, b in shops]
    bay = min(BAY, cw / 2 - 1.22)                    # a one-cell corner lot is 0.4 m narrower
    bays = [c for a, b in cells for c in ((a + b) / 2 - bay, (a + b) / 2, (a + b) / 2 + bay)]
    fwv = dict(PICTURESQUE, **CORNER_WAIVE) if corner else dict(PICTURESQUE)
    fw = wall(m, g, st, (XL, yF), (X, yF), sx_, "-", bays, lod, trim=trim, waive=fwv, holes=holes)
    if lod < 2:
        iron = v["door"]
        for a, b in shops:                           # cast-iron pilasters at each side of the plate glass
            ua, ub = a - XL, b - XL
            for u0, u1 in ((ua - .32, ua), (ub, ub + .32)):
                lbox(m, fw, u0, u1, STEP + E, B_SHOP_HEAD - E, E, .14, "Greystone" if granite else iron, ("in",))
                if lod == 0:                         # capital and base
                    lbox(m, fw, u0 - .05, u1 + .05, B_SHOP_HEAD - .3, B_SHOP_HEAD - .004 - E, .14 + E, .2,
                         "Greystone" if granite else iron, ("in",))
        if not granite:                              # the cast-iron beam over the whole front
            lbox(m, fw, .3, fw.L - .3, B_SHOP_HEAD + .01, 3.96, E, .16, iron)
    if v["sign"]:
        paint_sign(m, v, sign_x(v, X), yF, (8 if granite else 7) * SIGN_H)   # on the brick over the beam / granite

    # ---- the cornice and flat roof
    store = v["back"] == "store"
    zS = B_GROUND
    yR = (yF + (12.0 if n <= 2 else 14.0)) if store and end - yF > (17.0 if n <= 2 else 19.0) else end
    store = yR < end - .1
    deep = .75
    bracket = v["cornice"] == "bracket"
    side = v["door"] if bracket else v["wall"]
    x0 = XL - .33 if corner else XL + E              # on a corner the cornice carries round the side street
    cornice_roof(m, x0, X - E, yF - .4, yR + .25, top, lod, deep=deep, side=side, ends=side if corner else v["wall"])
    if corner and lod < 2:                           # its crown moulding down the side street
        wbox(m, x0 - .06, x0 - E, yF - .4 + E, yR + .25 - E, top + deep - .14, top + deep + .04, side, ("x+",))
    sw = None
    if corner:                                       # the side street: the same storeys, the shop glass round the corner
        swin = [(1.0, 1.2, 3.3)] + win
        sst = style(top, mats, swin, belts=belts, plinth=None, corners=False, frieze=None, belt_mat="Dressed")
        sw, sys_ = side_street(m, g, lod, sst, v, XL, yR, yF, B_SHOP_HEAD, trim,
                               cast=None if granite else v["door"])
    if not bracket:
        corbels(m, fw, top, lod, v["wall"])
        if sw:
            corbels(m, sw, top, lod, v["wall"])
    elif lod < 2:                                    # paired scroll brackets on a painted frieze, dentils under it
        for w_ in (fw, sw) if sw else (fw,):
            lbox(m, w_, .2, w_.L - .2, top - .45, top - E, E, .06, side)
            if lod == 0:
                u = .3
                while u + .1 < w_.L - .3:
                    lbox(m, w_, u, u + .1, top - .6, top - .45 - E, E, .05, side)
                    u += .25
        if lod == 0 and sw:                          # paired brackets down the side street, one pair a bay
            for c in sys_:
                for cc in (c - .12, c + .12):
                    wbox(m, XL - .38, XL - .06 - E, cc - .05, cc + .05, top - .6, top - E, side, ("x+", "z+"))
        if lod == 0:
            for a, b in cells:
                for i in range(6):
                    c = a + .5 + (b - a - 1.0) * i / 5
                    for cc in (c - .12, c + .12):
                        wbox(m, cc - .05, cc + .05, yF - .38, yF - .06 - E, top - .6, top - E, side, ("y+", "z+"))
    z1 = top + deep
    if v["pediment"]:                                # a raised block over the middle, for the name and the date
        pw = min(3.2, (X - XL) / 2 - 1.0)
        wbox(m, xm - pw, xm + pw, yF - .3, yF + .3, z1, z1 + 1.15, v["wall"], ("z-",))
        wbox(m, xm - pw - .12, xm + pw + .12, yF - .42, yF + .42, z1 + 1.15 + E, z1 + 1.35, side if bracket else "Dressed")
        if lod == 0:
            for c in (xm - pw + .4, xm + pw - .4):  # pier caps either side
                wbox(m, c - .25, c + .25, yF - .36, yF + .36, z1 + 1.35 + E, z1 + 1.65, "Dressed")
    if v["skylight"]:                                # north light: glass sloping up to the rear, iron ends
        sx0, sx1 = xm - min(3.5, (X - XL) / 2 - 1.2), xm + min(3.5, (X - XL) / 2 - 1.2)
        s0 = yF + 2.0
        s1 = min(s0 + 4.0, yR - 1.5)
        zh = z1 + 2.0
        g.facing([(sx0, s0, z1), (sx1, s0, z1), (sx1, s1, zh), (sx0, s1, zh)], (0, -1, 1), "Glass")
        m.facing([(sx0, s1, z1), (sx1, s1, z1), (sx1, s1, zh), (sx0, s1, zh)], (0, 1, 0), v["wall"])
        for xx, d in ((sx0, -1), (sx1, 1)):
            m.facing([(xx, s0, z1), (xx, s1, z1), (xx, s1, zh)], (d, 0, 0), v["wall"])
        if lod == 0:                                 # glazing bars
            k = round((sx1 - sx0) / .9)
            for i in range(k + 1):
                c = sx0 + (sx1 - sx0) * i / k
                t0 = .03
                m.facing([(c - .03, s0, z1 + t0), (c + .03, s0, z1 + t0), (c + .03, s1, zh + t0),
                          (c - .03, s1, zh + t0)], (0, -1, 1), v["door"])
    if lod == 0 and D >= 4 and not v["skylight"] and not store:  # deep 4-cell flat roofs: skylights & vents (density)
        for a, b in cells:
            cx = (a + b) / 2
            for cy in (yF + (yR - yF) * .3, yF + (yR - yF) * .55, yF + (yR - yF) * .8):
                cupola(m, cx, cy, z1, lod, v["wall"], "TinFlat", v["door"], a=.65, sink=.1, h=1.05)

    # ---- the body: party walls, the rear (or a stockroom behind)
    party(m, (X, yF), (X, yR), 0.0, top, v["wall"])
    if not corner:
        party(m, (-X, yR), (-X, yF), 0.0, top, v["wall"])
    rb = list(bays)
    rdx = min(rb, key=abs)
    rwin = [(1.0, 1.2, 3.2)] + win
    if store:
        rst = style(zS, [(0.0, zS, v["wall"])], [(1.0, 1.2, 3.2)], plinth=None, corners=False, frieze=None)
        party(m, (X, yR), (X, end), 0.0, zS, v["wall"])
        if corner:                                   # the stockroom's side-street wall: windows, no shop glass
            ys = side_bays(yR, end)
            kw = wall(m, g, rst, (XL, end), (XL, yR), "x", "-", ys, lod, trim=trim, waive=dict(PICTURESQUE))
            corbels(m, kw, zS, lod, v["wall"])
        else:
            party(m, (-X, end), (-X, yR), 0.0, zS, v["wall"])
        sw_ = wall(m, g, rst, (X, end), (XL, end), "-", sx_, rb, lod, door=(rdx, 1.4, 3.0), trim=trim,
                   waive={"balance": "the stockroom's loading door"})
        corbels(m, sw_, zS, lod, v["wall"])
        cornice_roof(m, XL + E, X - E, yR + E, end + .3, zS, lod, deep=.45, side=v["wall"], ends=v["wall"],
                     front=False)
        rst2 = style(top, [(0.0, top, v["wall"])], win, plinth=None, corners=False, frieze=None)
        rw = wall(m, g, rst2, (X, yR), (XL, yR), "-", sx_, rb, lod, z0=zS + .45, trim=trim)
        corbels(m, rw, top, lod, v["wall"])
    else:
        rst = style(top, [(0.0, top, v["wall"])], rwin, plinth=None, corners=False, frieze=None)
        rw = wall(m, g, rst, (X, yR), (XL, yR), "-", sx_, rb, lod, door=(rdx, 1.2, 2.95), trim=trim,
                  waive={"balance": "the back door to the service lane"})
        corbels(m, rw, top, lod, v["wall"])          # the corbel table carries round the back
    finish(m, g)


# ---------------------------------------------------------------- clapboard false fronts

C_SHOP_HEAD = 3.3
C_GROUND = 4.3
C_FLOOR = 3.0
C_PITCH = .65                 # the gables behind the false front: 2.6 m of rise on an 8 m cell
T = .3                        # thickness of the false front above the eave


def _clap(lod, W, D, v):
    n = v["storeys"]
    assert 1 <= n <= 2, "a false front is 1-2 storeys"
    win = [(1.0, 5.0 + C_FLOOR * j, 6.6 + C_FLOOR * j) for j in range(n - 1)]
    top = win[-1][2] + .6 if win else C_GROUND + .2
    corner = v["corner"]
    X = 4.0 * W - .01
    XL = -X + CI if corner else -X
    xm = (XL + X) / 2
    sx_ = "x" if corner else "-"
    cw = (X - XL) / W
    cells = [(XL + cw * i, XL + cw * (i + 1)) for i in range(W)]
    awn = v["awning"]
    yF = -4.0 * D + (.6 + AWN if awn else .45 + WALK)
    yb = yF + T                                       # the false front's back face
    yR = min(4.0 * D - .6, yF + (15.0 if n == 1 else 18.0))   # a yard behind on deep lots: shops stay shop-deep
    gable = v["roof"] == "gable"
    zr = top + cw / 2 * C_PITCH if gable else top + 1.4
    # the false front band: a row of attic windows, the sign on the tile grid over them, the cornice over all
    fwin = (.8, top + .4, top + 1.7)                  # tall enough to read as a storey's windows (rule 4)
    zs = SIGN_H * math.ceil((top + 2.1) / SIGN_H)
    zF = max(zr + .5, zs + SIGN_H + .75)
    step = v["top"] == "step"
    zC = zF + 1.8 if step else zF                     # the raised middle of a stepped front
    pw = min(3.6, (X - XL) / 2 - 1.6)

    sx = sign_x(v, X) if v["sign"] else None
    bay = min(BAY, cw / 2 - 1.22)                    # a one-cell corner lot is 0.4 m narrower
    bays = [c for a, b in cells for c in ((a + b) / 2 - bay, (a + b) / 2, (a + b) / 2 + bay)]
    def attic(c):                                     # rule 28: an attic window needs the attic behind it
        if not gable: return False                    # a lean-to is only 1.4 m over the eave at the front
        a, b2 = next((a, b2) for a, b2 in cells if a - 1e-6 <= c <= b2 + 1e-6)
        return top + (cw / 2 - abs(c - (a + b2) / 2)) * C_PITCH >= fwin[2] + .2
    blind = [(c, len(win)) for c in bays if not attic(c)]
    panels = [(c - .4 - XL, c + .4 - XL, fwin[1], fwin[2], "blind") for c, _ in blind]   # cased boards, no glass
    mats = [(0.0, zC, v["wall"])]
    st = style(zF, mats, win + [fwin], belts=(top,), plinth=(.4, .04, "StoneBase"), corners=True, frieze=.3)
    trim = dict(door=v["door"], lites=v["lites"], lean=True)
    m, g = Mesh(), Mesh()

    # ---- the walk (or the awning over it)
    if awn:
        span = (X - E) - (XL + E) - .3
        k = max(1, math.ceil(span / 3.2))
        posts = [XL + E + .15 + span * j / k for j in range(k + 1)]
        if lod == 2:
            posts = [posts[0], posts[-1]]
        porch(m, XL + E, X - E, yF, AWN, lod, zf=STEP, zt=3.75, posts=posts, mat=v["roof_mat"], rail=False,
              open_sides=(), skirt=False)
    else:
        plank_walk(m, XL, X, yF - WALK, yF)

    # ---- the front: shopfronts below, sash windows, the false front with its sign
    shops = shopfronts(XL, X)
    if corner:                                       # the shop glass runs to a 0.75 m corner post
        shops[0] = (XL + .75, shops[0][1])
    holes = [(a - XL, b - XL, 0.0, C_SHOP_HEAD, "shop") for a, b in shops]
    fwv = dict(PICTURESQUE, **CORNER_WAIVE) if corner else dict(PICTURESQUE)
    fw = wall(m, g, st, (XL, yF), (X, yF), sx_, "-", bays, lod, trim=trim, waive=fwv,
              holes=holes + panels, omit=blind)
    if lod < 2:
        for a, b in shops:                           # pilasters, a painted fascia and its cap over each shop
            ua, ub = a - XL, b - XL
            for u0, u1 in ((ua - .3, ua), (ub, ub + .3)):
                lbox(m, fw, u0, u1, .4 + E, C_SHOP_HEAD + .5 - E, E, .12, TRIM, ("in", "bot"))
            lbox(m, fw, ua - .3, ub + .3, C_SHOP_HEAD + .5, C_SHOP_HEAD + .85, E, .14, v["door"], ("in",))
            lbox(m, fw, ua - .36, ub + .36, C_SHOP_HEAD + .85 + E, C_SHOP_HEAD + .92, E, .2, TRIM)
    if lod == 0:                                     # pilasters between the bays of the false front (no sign)
        for c0, c1 in zip(bays, bays[1:]):
            u = (c0 + c1) / 2
            if sx is not None and sx - .4 < u < sx + SIGN_W + .4:
                continue
            lbox(m, fw, u - .12 - XL, u + .12 - XL, top + .14, zF - .9, E, .1, TRIM, ("in", "bot"))
            lbox(m, fw, u - .18 - XL, u + .18 - XL, zF - .9 + E, zF - .76, E, .16, TRIM, ("in",))
    if sx is not None:                               # a white board, the name painted on it
        if lod < 2:
            wbox(m, sx - .1, sx + SIGN_W + .1, yF - .05, yF - E, zs - .1, zs + SIGN_H + .1, TRIM, ("y+",))
        paint_sign(m, v, sx, yF - .05, zs)

    # the false front above the eave: back face, ends, the bracketed cornice
    m.facing([(X, yb, top), (XL, yb, top), (XL, yb, zF), (X, yb, zF)], (0, 1, 0), v["wall"])
    for xx, d in ((XL, -1), (X, 1)):
        m.facing([(xx, yF, top), (xx, yb, top), (xx, yb, zF), (xx, yF, zF)], (d, 0, 0), v["wall"])

    def cornice(x0, x1, z):
        wbox(m, x0, x1, yF - .42, yb + .06, z + E, z + .34, TRIM)
        if lod < 2:
            wbox(m, max(x0 - .04, XL + E), min(x1 + .04, X - E), yF - .5, yb + .1, z + .34 + E, z + .42, TRIM)
        if lod == 0:
            k = max(2, round((x1 - x0) / 1.3))
            for i in range(k + 1):
                c = x0 + .25 + (x1 - x0 - .5) * i / k
                wbox(m, c - .06, c + .06, yF - .4, yF - .07 - E, z - .5, z, TRIM, ("z+",))
                wbox(m, c - .08, c + .08, yF - .4, yF - .2, z - .7, z - .5, TRIM)

    if step:
        pa, pb = xm - pw, xm + pw
        cornice(XL + E, pa - E, zF)
        cornice(pb + E, X - E, zF)
        cst = style(zC, mats, [(.6, zF + .3, zF + 1.2)], plinth=None, corners=False, frieze=.3)
        wall(m, g, cst, (pa, yF), (pb, yF), "x", "x", [xm], lod, z0=zF, trim=trim, omit=[(xm, 0)],
             holes=[(pw - .3, pw + .3, zF + .3, zF + 1.2, "blind")])   # sky behind it (rule 28): a panel
        m.facing([(pb, yb, zF), (pa, yb, zF), (pa, yb, zC), (pb, yb, zC)], (0, 1, 0), v["wall"])
        for xx, d in ((pa, -1), (pb, 1)):
            m.facing([(xx, yF, zF), (xx, yb, zF), (xx, yb, zC), (xx, yF, zC)], (d, 0, 0), v["wall"])
        cornice(pa - .2, pb + .2, zC)
    else:
        cornice(XL + E, X - E, zF)

    # ---- the body: party walls, the rear (a stockroom behind on deep lots), the roof behind the false front
    party(m, (X, yF), (X, yR), 0.0, top, v["wall"])
    if corner:                                       # the side street: clapboard, corner boards, a sash every bay
        sst = style(top, mats, [(.9, 1.0, 2.9)] + win, belts=(), plinth=(.4, .04, "StoneBase"), corners=True)
        sw, _ = side_street(m, g, lod, sst, v, XL, yR, yF, C_SHOP_HEAD, trim)
        if lod < 2:                                  # the painted fascia and cap carry round over the shop glass
            ua, ub = sw.u_of(yF + 3.2), sw.u_of(yF + .75)
            lbox(m, sw, ua - .3, ub, C_SHOP_HEAD + .5, C_SHOP_HEAD + .85, E, .14, v["door"], ("in",))
            lbox(m, sw, ua - .36, ub, C_SHOP_HEAD + .85 + E, C_SHOP_HEAD + .92, E, .2, TRIM)
    else:
        party(m, (-X, yR), (-X, yF), 0.0, top, v["wall"])
    rdx = min(bays, key=abs)
    end = 4.0 * D - .6
    if end - yR > 1.5:                                # rule 17: fill the lot to 0.6 m off the rear line
        z0 = _stockroom(m, g, lod, v, XL, X, yR, end, top, cells, bays, rdx, trim)
        if win:                                       # the shop's upper storey shows over the stockroom roof
            ust = style(top, mats, win, belts=(), plinth=None, corners=False)
            wall(m, g, ust, (X, yR), (XL, yR), "-", sx_, bays, lod, z0=z0, trim=trim)
        else:                                         # a one-storey shop: a clapboard strip up to its eave
            m.facing([(X, yR, z0), (XL, yR, z0), (XL, yR, top), (X, yR, top)], (0, 1, 0), v["wall"])
    else:
        rst = style(top, mats, [(.9, 1.2, 3.0)] + win, belts=(), plinth=(.4, .04, "StoneBase"))
        wall(m, g, rst, (X, yR), (XL, yR), "-", sx_, bays, lod, door=(rdx, 1.1, 2.6), trim=trim,
             waive={"balance": "the back door to the service lane"})
    gtrim = dict(trim, simple=True)
    if gable:
        for a, b in cells:
            cx = (a + b) / 2
            gable_wall(m, g, (b, yR), (a, yR), top, zr, lod, v["wall"], wins=[(cx, .8, top + .6, top + 1.8)],
                       trim=gtrim)
            gable_roof(m, a + E, b - E, yb + E, yR, top, zr, lod, v["roof_mat"], over=(0.0, .3),
                       sides=("e" if corner and a == cells[0][0] else "p", "p"))   # an open eave on the side street
            if v["vent"]:                            # louvred kitchen ventilators on the ridge (no glass: rule 28)
                L = yR - yb
                for cy in ((yb + L / 3, yb + 2 * L / 3) if L > 10 else (yb + L / 2,)):
                    cupola(m, cx, cy, zr, lod, v["wall"], v["roof_mat"], v["door"], a=.6, sink=.55, h=1.0)
    else:
        y1 = yR + .3
        zl = top - (zr - top) * .3 / (yR - yb)
        shed_roof(m, XL + E, X - E, yb + E, y1, zr, zl, lod, v["roof_mat"])
        seams(m, lod, XL + E, X - E, yb + E, y1, zr, zl, v["roof_mat"])
        for xx, d in ((X, 1), (XL, -1)):              # the party walls' triangles under the lean-to
            m.facing([(xx, yb, top), (xx, yR, top), (xx, yb, zr)], (d, 0, 0), v["wall"])
        cy = yb + 2.5                                 # a pair of stove chimneys on the party walls (rule 12)
        zc = zr - (zr - zl) * (cy - yb) / (y1 - yb)
        for cx in (XL + (.6 if corner else .45), X - .45):
            chimney(m, cx, cy, .35, .45, zc - .4, max(zc + 1.6, zF + .4), lod)
        if lod == 0 and D >= 4:                       # deep 4-cell lean-to roofs: roof ventilators (density)
            for a, b in cells:
                cx = (a + b) / 2
                for frac in (.35, .7):
                    vy = yb + (yR - yb) * frac
                    vz = zr - (zr - zl) * (vy - yb) / (y1 - yb)
                    cupola(m, cx, vy, vz + .14, lod, v["wall"], v["roof_mat"], v["door"], a=.65, sink=.45, h=1.05)
    if lod == 0 and D >= 4 and end - yR > 1.5:        # deep 4-cell stockroom ridge/deck ventilators
        for a, b in cells:
            cx = (a + b) / 2
            for frac in (.33, .67):
                vy = yR + (end - yR) * frac
                vz = 3.8 if v["stock"] == "flat" else (3.4 + max(b_ - a_ for a_, b_ in cells) / 2 * .3) if v["stock"] == "gable" else (min(top - .6, 4.3) - (min(top - .6, 4.3) - 3.1) * frac)
                cupola(m, cx, vy, vz + .14, lod, v["wall"], v["stock_mat"] or v["roof_mat"], v["door"], a=.6, sink=.45, h=.95)
    finish(m, g)


S_WIN = (.8, 1.0, 2.25)       # stockroom windows: 1.25 m tall on 0.8 m (rule 4)


def _stockroom(m, g, lod, v, XL, X, y0, y1, top, cells, bays, rdx, trim):
    """A one-storey stockroom from the shop's rear wall (y0) to 0.6 m off the rear line (y1), party walls both
    sides, a loading door on the service lane. v["stock"] picks the roof. Returns the height above which the
    shop's own rear wall shows."""
    kind, wm = v["stock"], v["wall"]
    if kind == "shed":                                # a lean-to off the shop's rear wall, falling to the lane
        zh, ze = min(top - .6, 4.3), 3.1
    elif kind == "flat":                              # a flat roof behind a plain board cornice
        zh = ze = 3.4
    else:                                             # one low gable per cell, ridging front to back
        assert kind == "gable", kind
        ze = 3.4
        zh = ze + max(b - a for a, b in cells) / 2 * .3
        assert zh + .3 < top, "a gabled stockroom needs a 2-storey shop to die into (rule 24)"
    corner = v["corner"]
    for xx, d in ((X, 1), (XL, -1)):                  # bare party walls (rule 13), the lean-to's triangle over them
        if corner and d < 0:                          # a corner's side street: a sash every bay
            kst = style(ze, [(0.0, ze, wm)], [S_WIN], belts=(), plinth=(.4, .04, "StoneBase"), corners=True)
            wall(m, g, kst, (XL, y1), (XL, y0), "x", "-", side_bays(y0, y1), lod, trim=trim,
                 waive=dict(PICTURESQUE))
        else:
            party(m, (xx, y0) if d > 0 else (xx, y1), (xx, y1) if d > 0 else (xx, y0), 0.0, ze, wm)
        if kind == "shed":
            m.facing([(xx, y0, ze), (xx, y1, ze), (xx, y0, zh)], (d, 0, 0), wm)
    sst = style(ze, [(0.0, ze, wm)], [S_WIN], belts=(), plinth=(.4, .04, "StoneBase"), corners=corner)
    wall(m, g, sst, (X, y1), (XL, y1), "-", "x" if corner else "-", bays, lod, door=(rdx, 1.4, 2.4),
         trim=dict(trim, lean=lod > 0),
         waive={"balance": "the stockroom's loading door"})   # full sashes up close: a plain shed fails the density
    if lod == 0 and kind != "gable":                  # paired eave brackets along the lane, clear of the frieze
        k = max(2, round((X - XL) / 1.3))
        for i in range(k + 1):
            c = XL + .3 + (X - XL - .6) * i / k
            wbox(m, c - .05, c + .05, y1 + .07 + E, y1 + .26, ze - .5, ze - E, TRIM, ("y-", "z+"))
    if kind == "shed":
        zl = ze - (zh - ze) * .3 / (y1 - y0)
        sm = v["stock_mat"] or v["roof_mat"]         # a tin lean-to behind a slate shop reads as added later
        shed_roof(m, XL + E, X - E, y0 + E, y1 + .3, zh, zl, lod, sm)
        seams(m, lod, XL + E, X - E, y0 + E, y1 + .3, zh, zl, sm)
        return zh
    if kind == "flat":
        cornice_roof(m, XL + E, X - E, y0 + E, y1 + .3, ze, lod, deep=.4, side=TRIM, ends=wm, front=False)
        return ze + .4
    for a, b in cells:
        gable_wall(m, g, (b, y1), (a, y1), ze, zh, lod, wm)
        gable_roof(m, a + E, b - E, y0 + E, y1, ze, zh, lod, v["roof_mat"], over=(0.0, .3),
                   sides=("e" if corner and a == cells[0][0] else "p", "p"))
    return ze


def build(lod, W=2, D=3, **variant):
    variant.pop("palette", None)                     # colour sets only (lt_roster)
    v = dict(DEFAULT, **variant)
    (_brick if v["kind"] == "brick" else _clap)(lod, W, D, v)
