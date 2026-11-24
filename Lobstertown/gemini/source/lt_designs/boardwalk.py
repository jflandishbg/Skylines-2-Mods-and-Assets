"""Lobstertown Boardwalk (the author 2026-11-15: "commercial boardwalk low/high"): the Atlantic City and Old Orchard Beach
boardwalk in Maine shingle. Shops shoulder to shoulder behind a covered arcade over a plank boardwalk, the shop's name
painted on the arcade beam, and a row of front gables, one per 8 m cell of frontage, like a midway.

    build(lod, W=2, D=3, **variant)

Low (Boardwalk Shops, Commercial Low): two storeys, the shop below and a storey of rooms above under the gables.
High (Boardwalk Palaces, Commercial High): emporiums, music halls and natatoria 4-6 storeys high, behind a two-deck
promenade arcade, with corner turrets and a lantern.

Every lot is a row building (party walls both sides). Because each gable spans one 8 m cell and runs front to back,
the roof is the same height on any lot depth, and the block fills the lot to .6 m off its rear line.

Variant keys:
  storeys  2 (low) .. 6 (high): the ground storey is a 4.6 m shop storey, the rest 3.0 m
  roofs    a string, one letter per cell from the left: 'g' gable, 'm' gambrel (repeats to fill the lot)
  turret   None | 'l' | 'r' | 'both': octagonal corner towers on the front (lots 2 wide or more)
  lantern  True | False: a louvred lantern on the middle cell's ridge
  back     'full' (gables to the rear line) | 'store' (a lower flat-roofed stockroom or market hall behind)
  promenade True | False: a second, open deck over the arcade (high)
  base     None | a stone for the shop storey's piers
  wall, gable_mat, roof_mat, door (shopfront paint), lites, sign (atlas key without 'Sign_')
Château (the author 2026-11-16, CHATEAU_PLAN.md; rule 11b lets crown blocks under 150 m2 rise past the eaves):
  towers   ((pos, k, cap), ...): square towers over a cell, k storeys above the eave. pos 'l' (2nd cell from the
           left), 'c' (middle), 'r' (2nd from the right); the end cells keep the turrets. cap 'hip' (a steep
           pavilion roof), 'hipl' (with a lantern on it), 'dome' (a drum, bell dome and lantern)
  spire    (left, right): storeys the corner turrets rise past the eave, under a needle cone
  pitch    gable cells' pitch (1.0 default; 1.5-1.7 reads as a steep château roof)
"""
import math
from lt_kit import Mesh, finish, wall, style, gable_wall, gable_roof, porch, party, wbox, lbox, E, TRIM
from lt_shapes import turret, cornice_roof, pavilion_roof, dome, slab
from lt_designs.shore_row import SIGN_W, SIGN_H
from lt_designs.cottage import cupola, spread

ARC = 3.0                     # arcade depth (the boardwalk under it)
FRONT = .35                   # the arcade roof's front edge stays this far inside the lot front (with its .25 overhang)
SHOP_HEAD = 3.55              # tall shopfront glass; a painted fascia 3.60-4.12 above it, under the arcade roof
FASCIA = SHOP_HEAD + .05       # (a deeper fascia ran 47 m x .9 m unglazed on the widest lots: a blank band)
GROUND = 4.6                  # the shop storey
FLOOR = 3.0                   # storeys above it
GAM_KNEE, GAM_IN = 2.6, 1.0   # gambrel cells: the steep lower slope rises 2.6 m in 1.0 m
PITCH = 1.0                   # gable cells: 4 m of rise on an 8 m cell
DEFAULT = dict(storeys=2, roofs="g", turret=None, lantern=False, back="full", promenade=False, base=None,
               wall="ShingleSilver", gable_mat=None, roof_mat="SlateDark", door="Green", lites="2", sign=None,
               towers=(), spire=(0, 0), pitch=None, corner=False)
PICTURESQUE = {"balance": "boardwalk shops: shopfronts and gables in a row, not a formal front (Lobstertown standing waiver)"}


def _side_porch(m, xw, y0, y1, depth, lod, zf=.3, zt=4.15, posts=None, mat="SlateDark", deck="Deck",
                rail=True, roof=True):
    """A side-street promenade arcade along x = xw (facing -X), mirroring lt_kit.porch()."""
    xf = xw - depth
    posts = posts or [y0 + .15, y1 - .15]
    wbox(m, xf, xw - E, y0 + E, y1 - E, zf - .12, zf, deck, ("x+",))
    if lod < 2 and zf < 1.5:
        wbox(m, xf + .06, xw - .1, y0 + .06, y1 - .06, 0.0, zf - .12 - E, "Black", ("x+", "z-", "z+"))
    for py in posts:
        wbox(m, xf + .06, xf + .24, py - .09, py + .09, zf + E, zt - .2, TRIM, ("z-", "z+"))
        if lod == 0:
            wbox(m, xf + .02, xf + .28, py - .13, py + .13, zf + E, zf + .25, TRIM, ("z-",))
    if lod < 2:
        wbox(m, xf, xf + .30, y0 + E, y1 - E, zt - .2 + E, zt - .02, TRIM, ("x+", "z+"))
    if roof:
        prof = [(xf - .25, zt - .02), (xw - E, zt + .45)]
        slab(m, prof, y0, y1, lambda a, q, z: (q, a, z), lod, mat, th=.12, what="side promenade roof")
    if rail and lod < 2:
        wbox(m, xf + .10, xf + .20, y0 + .2, y1 - .2, zf + .85, zf + .92, TRIM)
        if lod == 0:
            k = int((y1 - y0 - .4) / .14)
            for i in range(1, k):
                c = y0 + .2 + (y1 - y0 - .4) * i / k
                if any(abs(c - py) < .13 for py in posts):
                    continue
                wbox(m, xf + .13, xf + .17, c - .02, c + .02, zf + E, zf + .85 - E, TRIM, ("z-", "z+"))


def rows(n):
    """(width, sill, head) of each storey above the shop storey, and the eave."""
    win = [(.9, 5.2 + FLOOR * j, 6.7 + FLOOR * j) for j in range(n - 1)]
    return win, 6.7 + FLOOR * (n - 2) + .95


def build(lod, W=2, D=3, **variant):
    v = dict(DEFAULT, **variant)
    n = v["storeys"]
    corner = v["corner"]
    win, top = rows(n)
    belts = tuple(5.2 + FLOOR * j - .6 for j in range(2, n - 1, 2))       # every other floor line above the 2nd
    X = 4.0 * W - .01
    XL = (-4.0 * W + FRONT + .25 + ARC) if corner else -X
    sx_ = "x" if corner else "-"
    cw = (X - XL) / W                                # one cell per ~7-8 m of frontage
    cells = [(XL + cw * i, XL + cw * (i + 1)) for i in range(W)]
    yF = -4.0 * D + FRONT + .25 + ARC               # the shopfront line, behind the arcade
    end = 4.0 * D - .6
    hi = v["promenade"]
    zA = 7.3 if hi else 4.15                         # arcade roof beam (the promenade's own roof when it has one)
    trim = dict(door=v["door"], lites=v["lites"], lean="bare" if n > 3 else True)
    gtrim = dict(trim, simple=True)
    rtrim = dict(trim)                               # rear and stockroom: full sashes (plain ones fell under 8 tri/m2)
    gmat = v["gable_mat"] or v["wall"]
    mats = [(0.0, GROUND, v["base"]), (GROUND, top, v["wall"])] if v["base"] else [(0.0, top, v["wall"])]
    main = style(top, mats, win, belts=belts)
    m, g = Mesh(), Mesh()

    # ---- turrets on the front corners
    tw = v["turret"] if W >= 2 else None
    ta = 2.0 if n > 3 else 1.4
    tl = True if corner else (tw in ("l", "both"))
    tr = tw in ("r", "both")
    tc = ta + .34                                    # tower centre off the side line: the cone's eave ring runs
    cl = XL if corner else (XL + tc)                 # corner: tower sits right on the (XL, yF) intersection
    cr = X - tc
    xa = (cl + ta) if tl else XL                     # the front wall's free run between the towers
    xb = (cr - ta) if tr else X

    # ---- the shopfronts: one per cell along the free run, piers between
    pier, edge = 1.4, .8
    inner = (xb - edge) - (xa + edge)
    k = max(1, round(inner / 7.0))
    sw = (inner - pier * (k - 1)) / k
    shops = [(xa + edge + j * (sw + pier), xa + edge + j * (sw + pier) + sw) for j in range(k)]
    holes = [(a - XL, b - XL, 0.0, SHOP_HEAD, "shop") for a, b in shops]

    # ---- the upper storeys: three bays a cell, clear of the towers
    bays = [c for a, b in cells for c in ((a + b) / 2 - cw * .32, (a + b) / 2, (a + b) / 2 + cw * .32)
            if c > xa + .9 + (1.0 if tl else 0) and c < xb - .9 - (1.0 if tr else 0)]
    waive = dict(PICTURESQUE)
    if tw or corner:
        waive["glass"] = "the corner tower carries the glass of its bay"
    if corner:
        waive["corners"] = "the corner tower anchors the street intersection"
    fw = wall(m, g, main, (XL, yF), (X, yF), sx_, "-", bays, lod, trim=trim, waive=waive, holes=holes)
    if lod < 2:                                      # pilasters, the painted fascia and its cap over each shop
        for a, b in shops:
            ua, ub = a - XL, b - XL
            for u0, u1 in ((ua - .3, ua), (ub, ub + .3)):
                lbox(m, fw, u0, u1, 0.0, FASCIA - E, E, .14, v["door"], ("in", "bot"))
            lbox(m, fw, ua - .3, ub + .3, FASCIA, 4.12, E, .16, v["door"], ("in",))
            lbox(m, fw, ua - .36, ub + .36, 4.12 + E, 4.18, E, .22, TRIM)
    twin_rows = [(1.55, 3.25)] + [(a, b) for _, a, b in win]
    up = lambda k_: [(top + .55 + FLOOR * j, top + 2.05 + FLOOR * j) for j in range(k_)]   # storeys over the eave
    if corner:                                       # full 8-sided corner tower at (XL, yF): windows on 5 street faces
        from lt_designs.mainst import tower
        ks = v["spire"][0]
        z1 = top + FLOOR * ks
        trows = [(a, b, (0, 1, 5, 6, 7)) for a, b in twin_rows] + [(a, b, tuple(range(8))) for a, b in up(ks)]
        tower(m, g, lod, cl, yF, ta, 8, 0.0, z1, (10.5 if ks else 7.5) if n > 3 else 4.6, v["wall"], v["roof_mat"],
              gtrim, trows, TRIM)
    for on, c, ks in ((False if corner else tl, cl, v["spire"][0]), (tr, cr, v["spire"][1])):
        if not on:
            continue
        z1 = top + FLOOR * ks
        turret(m, g, c, yF, ta, 0.0, z1, (10.5 if ks else 7.5) if n > 3 else 4.6, lod, v["wall"], twin_rows + up(ks),
               gtrim, v["roof_mat"], belts=belts, lites=v["lites"])
        if ks:                                       # its back, where it rises clear of the roof (rule 13)
            m.facing([(c + ta, yF + .02, top), (c - ta, yF + .02, top), (c - ta, yF + .02, z1),
                      (c + ta, yF + .02, z1)], (0, 1, 0), v["wall"])

    # ---- the arcade over the boardwalk, and the name board on its beam
    ax0 = (cl + .6) if tl else XL + E          # tucked into the towers (no slit at their chamfers)
    ax1 = (cr - .6) if tr else X - E
    span = ax1 - ax0 - .3
    posts = [ax0 + .15 + span * j / max(1, math.ceil(span / 3.2)) for j in range(max(1, math.ceil(span / 3.2)) + 1)]
    if lod == 2:
        posts = [posts[0], posts[-1]]
    if hi:                                           # the open arcade, and the promenade deck on its roof
        porch(m, ax0, ax1, yF, ARC, lod, zf=.3, zt=4.15, posts=posts, roof=False, rail=False, open_sides=())
        porch(m, ax0, ax1, yF, ARC, lod, zf=4.33, zt=zA, posts=posts, mat=v["roof_mat"], open_sides=())
    else:
        porch(m, ax0, ax1, yF, ARC, lod, zf=.3, zt=zA, posts=posts, mat=v["roof_mat"], rail=False, open_sides=())
    if v["sign"] and not corner:                     # on the beam face, on the atlas tile grid (no lettering on corners)
        yf = yF - ARC
        sx = min(max(0.0, SIGN_W * math.ceil((ax0 + .2) / SIGN_W)), SIGN_W * math.floor((ax1 - .2) / SIGN_W) - SIGN_W)
        z0 = 6 * SIGN_H                              # 3.48-4.06
        wbox(m, sx - .04, sx + SIGN_W + .04, yf - .03, yf - .004, z0 - .03, z0 + SIGN_H + .03, TRIM, ("y+",))
        ys = yf - .035
        m.facing([(sx, ys, z0), (sx + SIGN_W, ys, z0), (sx + SIGN_W, ys, z0 + SIGN_H), (sx, ys, z0 + SIGN_H)],
                 (0, -1, 0), "Sign_" + v["sign"])
    if lod < 2 and (tw or corner):                   # the boardwalk runs on in front of the towers
        if corner:
            wbox(m, XL - ARC, ax0 - E, yF - ARC, yF - ta - .05, .18, .30, "Deck", ("y+",))
            wbox(m, XL - ARC, XL - ta - .05, yF - ta - .05 + E, yF + .6 - E, .18, .30, "Deck", ("x+",))
        elif tl:
            wbox(m, XL + E, ax0 - E, yF - ARC, yF - ta - .05, .18, .30, "Deck", ("y+",))
        if tr:
            wbox(m, ax1 + E, X - E, yF - ARC, yF - ta - .05, .18, .30, "Deck", ("y+",))

    # ---- the body: front gables (or a stockroom behind), party walls, the rear front
    store = v["back"] == "store"
    zS = (top if n <= 2 else GROUND + FLOOR) if store else None   # the stockroom / market hall eave
    if store and n <= 2:
        zS = GROUND
    yR = (yF + (10.0 if n <= 3 else 14.0)) if store and end - yF > (16.0 if n <= 3 else 20.0) else end
    store = yR < end - .1
    party(m, (X, yF), (X, yR), 0.0, top, v["wall"])
    if corner:                                       # side-street wall along x = XL (facing -X) + wrapped promenade
        sya, syb = yF + ta, yR
        s_inner = (syb - edge) - (sya + edge)
        sk = max(1, round(s_inner / 7.0))
        ssw = (s_inner - pier * (sk - 1)) / sk
        sshops = [(sya + edge + j * (ssw + pier), sya + edge + j * (ssw + pier) + ssw) for j in range(sk)]
        sholes = [(yR - b, yR - a, 0.0, SHOP_HEAD, "shop") for a, b in sshops]
        sbays = spread(sya + 1.0, syb - .8, pier=.4, step=2.6)
        sw_w = wall(m, g, main, (XL, yR), (XL, yF), "-" if store else "x", "x", sbays, lod, trim=trim,
                    waive=waive, holes=sholes)
        if lod < 2:
            for a, b in sshops:
                ua, ub = yR - b, yR - a
                for u0, u1 in ((ua - .3, ua), (ub, ub + .3)):
                    lbox(m, sw_w, u0, u1, 0.0, FASCIA - E, E, .14, v["door"], ("in", "bot"))
                lbox(m, sw_w, ua - .3, ub + .3, FASCIA, 4.12, E, .16, v["door"], ("in",))
                lbox(m, sw_w, ua - .36, ub + .36, 4.12 + E, 4.18, E, .22, TRIM)
        ay0, ay1 = yF + .6, yR - E
        aspan = ay1 - ay0 - .3
        sposts = [ay0 + .15 + aspan * j / max(1, math.ceil(aspan / 3.2))
                  for j in range(max(1, math.ceil(aspan / 3.2)) + 1)]
        if lod == 2:
            sposts = [sposts[0], sposts[-1]]
        if hi:
            _side_porch(m, XL, ay0, ay1, ARC, lod, zf=.3, zt=4.15, posts=sposts, roof=False, rail=False)
            _side_porch(m, XL, ay0, ay1, ARC, lod, zf=4.33, zt=zA, posts=sposts, mat=v["roof_mat"], rail=True, roof=True)
        else:
            _side_porch(m, XL, ay0, ay1, ARC, lod, zf=.3, zt=zA, posts=sposts, mat=v["roof_mat"], rail=False, roof=True)
    else:
        party(m, (-X, yR), (-X, yF), 0.0, top, v["wall"])
    rb = [c for a, b in cells for c in ((a + b) / 2 - cw * .32, (a + b) / 2, (a + b) / 2 + cw * .32)]
    if store:
        rst = style(zS, [(0.0, zS, v["wall"])], [(.9, 1.55, 3.25)] + [w_ for w_ in win if w_[2] < zS - .3],
                    belts=())
        party(m, (X, yR), (X, end), 0.0, zS, v["wall"])
        if corner:
            ys_s = spread(yR, end, pier=1.2, step=2.6)
            wall(m, g, rst, (XL, end), (XL, yR), "x", "-", ys_s, lod, trim=rtrim,
                 waive={"balance": "side street of the rear stockroom"})
            if lod < 2:                                      # Lot review fix: continue plank boardwalk along side-street return
                wbox(m, XL - ARC, XL - E, yR + E, end + .3, .18, .30, "Deck", ("x+", "y-"))
        else:
            party(m, (-X, end), (-X, yR), 0.0, zS, v["wall"])
        rdx = min(rb, key=abs)
        wall(m, g, rst, (X, end), (XL, end), "-", sx_, rb, lod, door=(rdx, 2.2, 2.9), trim=rtrim,
             waive={"balance": "the stockroom's loading door"})
        cornice_roof(m, XL - (.3 if corner else -E), X - E, yR + .01, end + .3, zS, lod, deep=.45, ends=v["wall"], front=False)
        if lod < 2:
            wbox(m, XL - (.3 if corner else -E), X - E, end + .3 + E, end + .34, zS + .35, zS + .47, TRIM, ("y-",))   # rear crown
        wall(m, g, main, (X, yR), (XL, yR), "-", sx_, rb, lod, z0=zS + .45, trim=rtrim)
    else:
        rdx = min(rb, key=abs)
        rmain = style(top, mats, [(.9, 1.55, 3.25)] + win, belts=belts)
        wall(m, g, rmain, (X, yR), (XL, yR), "-", sx_, rb, lod, door=(rdx, 1.2, 2.95), trim=rtrim,
             waive={"balance": "the back door to the service lane"})

    pat = (v["roofs"] * W)[:W]
    idx = {"l": 1, "c": (W - 1) // 2, "r": W - 2}
    towers = {}
    for pos, k, cap in v["towers"]:
        i = idx[pos]
        if 0 < i < W - 1 and not {i - 1, i, i + 1} & set(towers):   # never in touching cells (shared wall planes)
            towers[i] = (k, cap)
    pitch = v["pitch"] or PITCH
    for i, ((a, b), kind) in enumerate(zip(cells, pat)):
        cx = (a + b) / 2
        if kind == "m":
            zk, zr = top + GAM_KNEE, top + GAM_KNEE + (cw / 2 - GAM_IN) * .55
            shape, knee, slope = (zk, GAM_IN), (zk, GAM_IN), .55
            fwins = [(cx - 1.4, .8, top + .8, top + 2.15), (cx + 1.4, .8, top + .8, top + 2.15),
                     (cx, .7, zk + .25, zk + 1.1)]
        else:
            zr = top + cw / 2 * pitch
            shape, knee, slope = None, None, pitch
            fwins = [(cx, .8, top + .8, top + 2.3)] + ([(cx, .6, top + 2.8, top + 3.5)] if lod < 2 else [])
        for on, c, k in ((tl, cl, v["spire"][0]), (tr, cr, v["spire"][1])):   # a spired turret hides these
            if on and k:
                fwins = [f_ for f_ in fwins if abs(f_[0] - c) > ta + .6]
        y0 = yF
        if i in towers:                              # a château tower over this cell (rule 11b crown)
            k, cap = towers[i]
            y0 = _tower(m, g, lod, v, a, b, yF, yR, top, zr, k, cap, trim, gtrim)
        if y0 < yR - .1:
            if y0 == yF:
                gable_wall(m, g, (a, yF), (b, yF), top, zr, lod, gmat, wins=fwins, trim=gtrim, shape=shape)
            gable_wall(m, g, (b, yR), (a, yR), top, zr, lod, gmat, wins=fwins[:1] if kind == "g" else fwins[:2],
                       trim=gtrim, shape=shape)
            gable_roof(m, a + E, b - E, y0 + (0 if y0 == yF else .012), yR, top, zr, lod, v["roof_mat"],
                       over=(.45 if y0 == yF else 0.0, .3), sides=("e" if corner and i == 0 else "p", "p"), knee=knee)
        if v["lantern"] and W // 2 not in towers and abs(cx - (cells[W // 2][0] + cells[W // 2][1]) / 2) < .1:
            la = 1.2
            cupola(m, cx, (yF + yR) / 2, zr + .16, lod, v["wall"], v["roof_mat"], v["door"], a=la,
                   sink=la * slope + .3, h=1.8)

    finish(m, g)


def _tower(m, g, lod, v, a, b, yF, yR, top, zr, k, cap, trim, gtrim):
    """A square château tower over the cell a..b, standing on the front wall and rising k storeys past the eave
    (at least 0.6 m clear of the cell's own ridge). Returns where the cell's gable roof starts behind it."""
    cw = b - a
    cx = (a + b) / 2
    while top + FLOOR * k < zr + .6:
        k += 1
    zT = top + FLOOR * k
    Dt = min(cw, yR - yF)
    if yR - yF - Dt < 2.0:                           # no short stub of gable behind: the tower takes the depth
        Dt = yR - yF
    yT = yF + Dt
    rows = [(.9, top + .55 + FLOOR * j, top + 2.05 + FLOOR * j) for j in range(k)]
    st = style(zT, [(top, zT, v["wall"])], rows, belts=(), plinth=None)
    fb = [cx - min(2.6, cw / 2 - 1.15), cx, cx + min(2.6, cw / 2 - 1.15)]
    ym = (yF + yT) / 2
    sb = [ym - min(2.6, Dt / 2 - 1.15), ym, ym + min(2.6, Dt / 2 - 1.15)] if Dt >= 6.4 else [ym]
    wall(m, g, st, (a, yF), (b, yF), "x", "x", fb, lod, z0=top, trim=trim, waive=dict(PICTURESQUE))
    wall(m, g, st, (b, yF), (b, yT), "x", "x", sb, lod, z0=top, trim=gtrim)
    wall(m, g, st, (b, yT), (a, yT), "x", "x", fb, lod, z0=top, trim=gtrim)
    wall(m, g, st, (a, yT), (a, yF), "x", "x", sb, lod, z0=top, trim=gtrim)
    o = .3
    if cap in ("hip", "hipl"):
        half = min(cw, Dt) / 2 + o
        rise = 1.55 * half
        zr_ = pavilion_roof(m, a - o, b + o, yF - o, yT + o, zT, rise, lod, v["roof_mat"], finial=cap == "hip")
        if cap == "hipl":                            # a lantern crowning the pavilion
            la = 1.0
            s = rise / half
            cupola(m, cx, ym, zr_ - la * s + .25, lod, v["wall"], v["roof_mat"], v["door"], a=la, sink=.55, h=1.7)
    else:                                            # a flat deck, the drum and dome, a lantern
        cornice_roof(m, a - .2, b + .2, yF - .2, yT + .2, zT, lod, deep=.45, ends=TRIM)
        r = min(cw, Dt) / 2 - .9
        zc = dome(m, g, cx, ym, r, zT + .45, lod, v["roof_mat"], v["wall"])
        cupola(m, cx, ym, zc + .02, lod, v["wall"], v["roof_mat"], v["door"], a=.75, sink=.05, h=1.4)
    return yT
