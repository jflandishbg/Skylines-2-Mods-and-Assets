"""Lobstertown Main Street (ZM1, the author 2026-11-16: "shops below, flats above", its own commercial architecture).

A New England downtown: 3-4 storey brick commercial blocks shoulder to shoulder on 8 m lots, a shopfront at the
sidewalk (cast iron or a granite shop storey, the shop's sign on the fascia), the flats' own street door beside it,
and above it the flats: stone-trimmed windows (plain lintels, Italianate hoods or pediments), oriels and canted bays,
corbelled or bracketed cornices, a few mansards and brick gable fronts, Queen Anne turrets and Italianate corner
towers. Unlike the Boardwalk Shops (1-3 storeys, plank walk, painted false fronts) every block here is masonry and
taller, and the backs step down to the service lane in brick (back blocks, stockrooms, iron fire escapes, porches).

    build(lod, D=3, **variant)          D = lot depth in cells (2..6); lots are one cell (8 m) wide

Variant keys:
  storeys   3 | 4 (the shop storey and the flats above it)
  ground    'iron' (cast-iron shopfront on brick) | 'granite' (a granite shop storey)
  roof      'flat' (deep cornice) | 'mansard' (slate, dormers both slopes) | 'gable' (a brick front gable)
  cornice   flat roofs: 'corbel' (brick corbel table) | 'bracket' (painted bracketed frieze)
  pediment  flat roofs: a raised name block over the middle of the cornice
  parapet   gable roofs: the front gable rises as a stone-coped brick parapet (the roof hides behind it)
  upper     None | 'oriel' (the middle bay, every flat floor) | 'bays' (two canted bays, every flat floor) |
            'turret' (a Queen Anne turret corbelled out at the right end, rising through the cornice)
  hood      None (plain stone lintels) | 'cap' (an Italianate hood on consoles) | 'pediment'
  hall      True: the top floor is a lodge hall (Odd Fellows): taller windows, giant pilasters
  quoins    True: dressed quoins up both ends of the front (the stone bank front)
  corner    False | True: a LeftCorner building. The street side is the left (x = XL): the shop windows wrap the
            corner, windows down every floor of the side street; tower 'square' | 'octagon' stands on the corner
  back      storeys of the pieces behind the main block, front to back, e.g. (2, 1): a 2-storey back block, then
            a 1-storey stockroom to 0.6 m off the rear line (rule 17)
  escape    True: an iron fire escape down the main block's back wall
  decks     True: stacked wooden porches on the main block's back wall
  awning    None | paint: a canvas awning over the shop window
  wall, back_mat (rear walls), roof_mat, door (shopfront / iron paint), oriel_mat, lites, sign, sign_side 'l' | 'r'
"""
import math
from lt_kit import (Mesh, Wall, finish, wall, style, gable_wall, gable_roof, shed_roof, party, wbox, lbox, bay, E,
                    TRIM, chimney)
from lt_kit import surface, roof_check
from nf_kit import band
from lt_shapes import slab, dormer, side_dormers, cornice_roof
from lt_designs.shore_row import SIGN_W, SIGN_H, rear_decks
from lt_designs.cannery import corbels, rake_corbels

X = 3.99                      # party walls on the side lot lines
CI = .40                      # corner: the street-side wall stands this far in (the cornice overhangs it)
SET = 1.0                     # the shopfront stands at the sidewalk, 1 m in (room for the cornice overhang)
G = 4.6                       # the shop storey: the second floor's level
F = 3.2                       # each floor above it
HALL = 4.2                    # a lodge hall's floor height
SHOP_HEAD = 3.25              # shop glass head; the fascia 3.30-4.12, the sign 3.48-4.06 on the atlas grid
MAIN = 15.0                   # depth of the main block on a lot with room behind it
DEEP = .75                    # flat-roof cornice depth
MANS_RUN, MANS_RISE = 1.2, 3.0
PITCH = .9                    # brick front gables
STREET = {"balance": "a shopfront and the flats' street door, as on every New England commercial block"}
DEFAULT = dict(storeys=3, ground="iron", roof="flat", cornice="corbel", pediment=False, parapet=False, upper=None,
               hood=None, hall=False, quoins=False, corner=False, tower=None, back=(2, 1), escape=False, decks=False,
               awning=None, wall="Brick074", back_mat=None, roof_mat="SlateDark", door="Green", oriel_mat="Cream",
               lites="2", sign=None, sign_side="r")


def lz(j, hall_top=None):
    """Floor level of storey j (0 = the shop)."""
    return 0.0 if j == 0 else G + F * (j - 1)


def floors(n, hall):
    """Window rows of the flats: (width, sill, head) per storey above the shop."""
    out = []
    for j in range(1, n):
        z = lz(j)
        if hall and j == n - 1:
            out.append((1.0, z + .7, z + 3.1))      # the lodge hall: tall windows (2.4 m)
        else:
            out.append((1.0, z + .9, z + 2.7))
    return out


def piece_top(k):
    """Cornice line of a k-storey back piece."""
    return G if k == 1 else lz(k - 1) + 2.7 + 1.15


def piece_win(k):
    return [(1.0, 1.0, 3.0)] + [(1.0, lz(j) + .9, lz(j) + 2.7) for j in range(1, k)] if k > 1 else [(1.0, 1.2, 3.2)]


def plan(D, back):
    """(yF, yR, pieces): the main block from yF to yR, then [(storeys, ya, yb)] to 0.6 m off the rear line."""
    yF = -4.0 * D + SET
    end = 4.0 * D - .6
    if end - yF - MAIN < 6.0:
        return yF, end, []
    yR = yF + MAIN
    r = end - yR
    if len(back) == 1 or r < 14.0:
        return yF, yR, [(back[0], yR, end)]
    first = 8.0 if r < 20 else 10.0
    return yF, yR, [(back[0], yR, yR + first), (back[1], yR + first, end)]


def beam(m, p0, p1, w, h, mat):
    """A straight member from p0 to p1 (a stair stringer): w wide across, h deep, a closed box."""
    dx, dy, dz = (p1[i] - p0[i] for i in range(3))
    L = math.sqrt(dx * dx + dy * dy + dz * dz)
    ax = (dx / L, dy / L, dz / L)
    side = (-ax[1], ax[0], 0.0)
    n = math.hypot(*side)
    side = (side[0] / n, side[1] / n, 0.0)
    up = (ax[1] * side[2] - ax[2] * side[1], ax[2] * side[0] - ax[0] * side[2], ax[0] * side[1] - ax[1] * side[0])
    def c(p, s, u):
        return tuple(p[i] + side[i] * s * w / 2 + up[i] * u * h / 2 for i in range(3))
    q = [(s, u) for s, u in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    for k in range(4):
        (s0, u0), (s1, u1) = q[k], q[(k + 1) % 4]
        nrm = tuple(side[i] * (s0 + s1) + up[i] * (u0 + u1) for i in range(3))
        m.facing([c(p0, s0, u0), c(p1, s0, u0), c(p1, s1, u1), c(p0, s1, u1)], nrm, mat)
    m.facing([c(p0, *q[k]) for k in range(4)], tuple(-a for a in ax), mat)
    m.facing([c(p1, *q[k]) for k in range(4)], ax, mat)


def fire_escape(m, cx, yw, levels, lod, floor=0.0, mat="Iron"):
    """An iron fire escape on a back wall at yw (facing +Y): a railed landing at each floor level in `levels`
    (rising), a stair between landings, a drop ladder under the lowest one."""
    a0, a1, dp = cx - 1.25, cx + 1.25, 1.0
    for k, zf in enumerate(levels):
        wbox(m, a0, a1, yw + E, yw + dp, zf - .08, zf, mat)
        if lod < 2:
            wbox(m, a0, a1, yw + dp - .05, yw + dp, zf + .9, zf + .96, mat)                 # top rail
            for xx in (a0, a1 - .05):
                wbox(m, xx, xx + .05, yw + .05, yw + dp, zf + .9 - .06, zf + .9, mat)     # end rails
                wbox(m, xx, xx + .05, yw + dp - .05, yw + dp, zf + E, zf + .84 - E, mat, ("z-", "z+"))
            if lod == 0:
                c = a0 + .3
                while c < a1 - .3:                                                       # pickets
                    wbox(m, c - .012, c + .012, yw + dp - .04, yw + dp - .016, zf + E, zf + .9 - E, mat, ("z-", "z+"))
                    c += .3
        if k and lod < 2:                          # the stair up from the landing below
            zl = levels[k - 1]
            beam(m, (a0 + .35, yw + dp - .35, zl + .05), (a1 - .45, yw + dp - .35, zf - .12), .5, .06, mat)
    if lod < 2:                                    # the drop ladder
        z0 = levels[0]
        for xx in (a1 - .55, a1 - .2):
            wbox(m, xx - .02, xx + .02, yw + dp - .3, yw + dp - .26, max(floor + 2.4, z0 - 3.0), z0 - .08 - E, mat)


def tower(m, g, lod, cx, cy, a, sides, z0, z1, rise, mat, roof, trim, rows, belt, bottom=False, crest=True):
    """A tower on the roof or corbelled out from the wall: a square or octagonal shaft of apothem a centred at
    (cx, cy), face 0 facing the street, walls from z0 to z1, then a pyramid / cone cap `rise` high.
    rows: [(sill, head, faces)] windows on the faces listed. bottom: close the underside (a corbelled turret)."""
    R = a / math.cos(math.pi / sides)
    ang = lambda k: math.radians(-90 - 180 / sides + 360 / sides * k)
    pts = [(cx + R * math.cos(ang(k)), cy + R * math.sin(ang(k))) for k in range(sides)]
    for i in range(sides):
        w = Wall(pts[i], pts[(i + 1) % sides])
        H = []
        for zb, zt, faces in rows:
            if i in faces:
                ww = min(w.L - .5, .9)
                H.append((w.L / 2 - ww / 2, w.L / 2 + ww / 2, zb, zt, "win"))
        surface(m, g, w, z0, z1, [(z0, z1, mat)], H, lod, trim)
        if lod < 2:
            dz = -.008 * (1 + i % 2)               # neighbouring faces' bands never share a plane at the corners
            band(m, w, z1 - .32 + dz, z1 + dz, .07, belt, "-", "-")
    if bottom:
        m.facing([(x, y, z0) for x, y in pts][::-1], (0, 0, -1), TRIM)
    Rc = (a + .3) / math.cos(math.pi / sides)
    zc = z1 + .02
    ring = [(cx + Rc * math.cos(ang(k)), cy + Rc * math.sin(ang(k)), zc) for k in range(sides)]
    apex = (cx, cy, zc + rise)
    t = Mesh()
    for k in range(sides):
        p, q = ring[k], ring[(k + 1) % sides]
        t.facing([p, q, apex], ((p[0] + q[0]) / 2 - cx, (p[1] + q[1]) / 2 - cy, .5), roof)
    t.facing(ring, (0, 0, -1), TRIM)
    roof_check(m, t, f"tower cap at {cx:.2f}, {cy:.2f}")
    if lod < 2 and crest:                          # a finial
        wbox(m, cx - .06, cx + .06, cy - .06, cy + .06, zc + rise - .3, zc + rise + .7, "Iron", ("z-",))
        if lod == 0:
            wbox(m, cx - .13, cx + .13, cy - .13, cy + .13, zc + rise + .25, zc + rise + .37, "Iron")


def build(lod, D=3, **variant):
    if variant.get("wide_corner"):
        from lt_designs.wide_corners import build_corner
        return build_corner(lod, D, variant)
    hand = variant.get("hand", "L")
    variant.pop("palette", None)
    for k in ("front", "hand", "rear", "dormers", "gable_mat", "shutters", "barn_mat"):   # old shore_row keys
        variant.pop(k, None)
    v = dict(DEFAULT, **variant)
    n, kind, corner = v["storeys"], v["roof"], v["corner"]
    flat, mans, gab = kind == "flat", kind == "mansard", kind == "gable"
    wm = v["wall"]
    bm = v["back_mat"] or wm
    win = floors(n, v["hall"])
    last = win[-1][2]
    top = last + (1.15 if flat else .85 if v["hood"] == "pediment" else .6)   # clear of the window hoods
    XL = -X + CI if corner else -X
    xm = (XL + X) / 2
    yF, yR, pieces = plan(D, v["back"])
    granite = v["ground"] == "granite"
    ftrim = dict(door=v["door"], lites=v["lites"], masonry="Dressed", reveal=wm, lean=True)
    if v["hood"]:
        ftrim["hood"] = v["hood"]
    rtrim = dict(door=v["door"], lites=v["lites"], masonry="Dressed", reveal=bm, lean=True)
    m, g = Mesh(), Mesh()
    sx = "x" if corner else "-"

    # ---- the street front: shop storey, flats' door, the flats above
    parapet = gab and v["parapet"]
    ftop = top + .5 if parapet else top
    mats = [(0.0, G, "Greystone"), (G, ftop, wm)] if granite and wm != "Greystone" else [(0.0, ftop, wm)]
    fwin = [(1.0, 1.0, 3.0)] + win                 # a ground row, never built: the shop and door take it
    st = style(ftop, mats, fwin, belts=(G,), plinth=(.45, .05, "Greystone"), corners=False, frieze=None,
               belt_mat="Dressed")
    bays = [xm - 2.3, xm, xm + 2.3] if corner else [-2.4, 0.0, 2.4]
    left_door = v["sign_side"] == "r" and not corner
    dx = -3.0 + .5 if left_door else 2.5
    if corner:
        sa, sb = XL + .75, 1.45
    elif left_door:
        sa, sb = -1.45, X - .64
    else:
        sa, sb = XL + .64, 1.45
    fwall = Wall((XL, yF), (X, yF))
    u = fwall.u_of
    holes = [(u(sa), u(sb), 0.0, SHOP_HEAD, "shop"), (u(dx) - .5, u(dx) + .5, 0.0, 2.95, "door")]
    sm = (sa + sb) / 2
    trim_shop = dict(ftrim, shopdoor=(u(sm) - .55, u(sm) + .55))
    waive, omit = dict(STREET), [(c, 0) for c in bays]   # rules sort the door into the ground row
    up = v["upper"]
    if up == "oriel":
        omit += [(xm, f) for f in range(1, len(fwin))]
        waive["glass"] = "the oriel carries the glass of the middle bay"
        waive["rhythm"] = "the oriel fills the middle bay on every floor of flats"
    elif up == "bays":
        omit += [(c, f) for c in (bays[0], bays[2]) for f in range(1, len(fwin))]
        waive["glass"] = "the two canted bays carry the glass of the outer bays"
        waive["rhythm"] = "canted bays fill the outer bays on every floor of flats"
    elif up == "turret":
        omit += [(bays[2], f) for f in range(1, len(fwin))]
        waive["rhythm"] = "the turret fills the right-hand bay on every floor of flats"
    if v["hall"]:
        waive["order"] = "the lodge hall on the top floor: tall windows, as on an Odd Fellows block"
    if corner:
        waive["corners"] = "the corner shop's window runs to a corner pier, as on a New England commercial block"
    fw = wall(m, g, st, (XL, yF), (X, yF), sx, "-", bays, lod, trim=trim_shop, waive=waive, omit=omit, holes=holes)
    if lod < 2:                                     # shop pilasters, the fascia and its cap (iron or granite)
        paint = v["door"]
        ua, ub = u(sa), u(sb)
        pil = "Greystone" if granite else paint
        for u0, u1 in ((ua - .3, ua), (ub, ub + .3)):
            lbox(m, fw, u0, u1, 0.0, 3.30 - E, E, .14, pil, ("in", "bot"))
        lbox(m, fw, ua - .3, ub + .3, 3.30, 4.12, E, .16, paint, ("in",))
        lbox(m, fw, ua - .36, ub + .36, 4.12 + E, 4.2, E, .22, "Dressed" if granite else paint)
        if lod == 0 and not granite:                # iron rosettes on the pilaster caps
            for c in (ua - .15, ub + .15):
                lbox(m, fw, c - .1, c + .1, 2.9, 3.1, .14 + E, .19, paint)
    if v["sign"]:
        z0 = 6 * SIGN_H
        ys = yF - .16 - E
        x0 = 0.0 if left_door else -SIGN_W
        m.facing([(x0, ys, z0), (x0 + SIGN_W, ys, z0), (x0 + SIGN_W, ys, z0 + SIGN_H), (x0, ys, z0 + SIGN_H)],
                 (0, -1, 0), "Sign_" + v["sign"])
    if v["awning"]:                                 # a canvas awning on iron arms over the shop window
        shed_roof(m, sa - .2, sb + .2, yF - .9, yF - E, 3.28, 2.72, lod, v["awning"], fascia=v["awning"], th=.05,
                  high="y1")
    if lod < 2 and (v["hall"] or v["quoins"]):
        if v["hall"]:                               # giant pilasters up the flats, in dressed stone
            for c in (-3.55, -1.2, 1.2, 3.55):
                lbox(m, fw, u(c) - .2, u(c) + .2, G + .12, ftop - .35, E, .08, "Dressed")
        if v["quoins"] and lod == 0:                # long-and-short quoins at both ends
            z, k = G + .12, 0
            while z + .4 < ftop - .3:
                wq = .55 if k % 2 == 0 else .35
                for a0, a1 in ((0.0, wq), (fw.L - wq, fw.L)):
                    lbox(m, fw, a0 + E, a1 - E, z, z + .38, E, .05, "Dressed")
                z += .42
                k += 1
    if up == "oriel":                               # a painted oriel on brackets, every floor of flats
        z0, z1, wd, pj = G + .35, last + .45, 2.2, .6
        bay(m, g, xm, yF, wd, pj, z0, z1, lod, v["oriel_mat"], [(b, t) for _, b, t in win], ftrim, v["roof_mat"],
            v["lites"])
        a = wd / 2 + pj
        m.facing([(xm - a, yF, z0), (xm - wd / 2, yF - pj, z0), (xm + wd / 2, yF - pj, z0), (xm + a, yF, z0)],
                 (0, 0, -1), TRIM)
        if lod == 0:
            for c in (xm - .8, xm + .8):
                wbox(m, c - .07, c + .07, yF - .5, yF - E, z0 - .55, z0 - E, TRIM, ("y+", "z+"))
    elif up == "bays":                              # canted brick bays either side, every floor of flats
        z0, z1 = G + .2, last + .4
        for c in (bays[0], bays[2]):
            bay(m, g, c, yF, 1.4, .5, z0, z1, lod, wm, [(b, t) for _, b, t in win], ftrim, v["roof_mat"], v["lites"])
            a = .7 + .5
            m.facing([(c - a, yF, z0), (c - .7, yF - .5, z0), (c + .7, yF - .5, z0), (c + a, yF, z0)], (0, 0, -1),
                     "Dressed")
    elif up == "turret":                            # a Queen Anne turret corbelled out at the right, through the cornice
        tc = bays[2]
        rows = [(b, t, (0, 1, 7)) for _, b, t in win]
        z1 = top + DEEP + 2.9
        rows.append((top + DEEP + .7, top + DEEP + 2.3, tuple(range(8))))
        tower(m, g, lod, tc, yF + .62, 1.25, 8, G + .3,   # set back: the cap stays on the lot
              z1, 4.2, wm, v["roof_mat"], dict(ftrim, hood=None), rows,
              "Dressed", bottom=True)

    # ---- the roof of the main block
    z1 = top + DEEP
    if flat:
        bracket = v["cornice"] == "bracket"
        side = v["door"] if bracket else wm
        x0 = XL - .33 if corner else XL + E           # its crown moulding stays on the lot
        cornice_roof(m, x0, X - E, yF - .4, yR + .25, top, lod, deep=DEEP, side=side,
                     ends=side if corner else wm)
        if corner and lod < 2:                      # crown moulding down the side street
            wbox(m, x0 - .06, x0 - E, yF - .4 + E, yR + .25 - E, z1 - .14, z1 + .04, side, ("x+",))
        if not bracket:
            corbels(m, fw, top, lod, wm)
        elif lod < 2:
            lbox(m, fw, .2, fw.L - .2, top - .45, top - E, E, .06, side)
            if lod == 0:
                c = .3
                while c + .1 < fw.L - .3:           # dentils
                    lbox(m, fw, c, c + .1, top - .6, top - .45 - E, E, .05, side)
                    c += .25
                for i in range(6):                  # paired scroll brackets
                    cc0 = XL + .5 + (X - XL - 1.0) * i / 5
                    for cc in (cc0 - .12, cc0 + .12):
                        wbox(m, cc - .05, cc + .05, yF - .38, yF - .06 - E, top - .6, top - E, side, ("y+", "z+"))
        if v["pediment"]:                           # a raised name block over the middle of the cornice
            pw = 2.6
            wbox(m, xm - pw, xm + pw, yF - .3, yF + .3, z1, z1 + 1.15, wm, ("z-",))
            wbox(m, xm - pw - .12, xm + pw + .12, yF - .42, yF + .42, z1 + 1.15 + E, z1 + 1.35,
                 side if bracket else "Dressed")
            if lod == 0:
                for c in (xm - pw + .4, xm + pw - .4):
                    wbox(m, c - .25, c + .25, yF - .36, yF + .36, z1 + 1.35 + E, z1 + 1.65, "Dressed")
        if lod < 2:                                 # a roof hatch
            wbox(m, .6, 1.6, yR - 3.2, yR - 2.2, z1, z1 + .55, "Tin", ("z-",))
        party(m, (X, yF), (X, yR), 0.0, top, wm)
        if not corner:
            party(m, (-X, yR), (-X, yF), 0.0, top, wm)
        chimney(m, X - .45, yF + 4.0, .3, .45, z1 - .1, z1 + 1.5, lod)
        chimney(m, XL + .45 if not corner else XL + .6, yR - 3.0, .3, .45, z1 - .1, z1 + 1.3, lod)
        rtop = top
    elif mans:
        zt_ = top + MANS_RISE
        for xx, d in ((X, 1), (-X, -1)):            # the party walls rise into the mansard, 3 cm under the slab
            m.facing([(xx, yF, 0.0), (xx, yR, 0.0), (xx, yR, top - .03), (xx, yR - MANS_RUN, zt_ - .03),
                      (xx, yF + MANS_RUN, zt_ - .03), (xx, yF, top - .03)], (d, 0, 0), wm)
        prof = [(yF - .45, top - .15), (yF, top), (yF + MANS_RUN, zt_), (yR - MANS_RUN, zt_), (yR, top),
                (yR + .4, top - .13)]
        slab(m, prof, -X + E, X - E, lambda a, q, z: (a, q, z), lod, v["roof_mat"], end=v["roof_mat"],
             what="mansard roof")
        if lod < 2:                                 # iron cresting round the deck
            for yy in (yF + MANS_RUN + .05, yR - MANS_RUN - .1):
                wbox(m, -X + .2, X - .2, yy, yy + .05, zt_ + .16 + E, zt_ + .5, "Iron", ("z-",))
        th, k = .16, MANS_RISE / MANS_RUN
        fr = lambda o_: top + th + (-o_ - yF) * k
        rr = lambda o_: top + th + (yR - o_) * k
        dtrim = dict(door=v["door"], lites=v["lites"])
        for cx in bays:
            dormer(m, g, lambda o_, t, z: (t, -o_, z), fr, -(yF + .25), cx, 1.2, lod, wm, v["roof_mat"], dtrim,
                   rise=.5, height=1.5, lites=v["lites"])
        for cx in (-1.5, 1.5):
            dormer(m, g, lambda o_, t, z: (t, o_, z), rr, yR - .25, cx, 1.2, lod, bm, v["roof_mat"], dtrim,
                   rise=.5, height=1.4, lites=v["lites"])
        chimney(m, X - .5, yF + MANS_RUN + 3.0, .35, .45, zt_ - .1, zt_ + 1.4, lod)
        chimney(m, -X + .5, yR - MANS_RUN - 2.5, .35, .45, zt_ - .1, zt_ + 1.2, lod)
        rtop = top
    else:
        half = (X - XL) / 2
        ridge = top + half * PITCH
        party(m, (X, yF), (X, yR), 0.0, top, wm)
        if not corner:
            party(m, (-X, yR), (-X, yF), 0.0, top, wm)
        gt = dict(door=v["door"], lites=v["lites"], masonry="Dressed", reveal=wm)
        if parapet:                                 # a stone-coped parapet gable, the roof hiding behind it
            zp = ridge + .9
            gable_wall(m, g, (XL, yF), (X, yF), ftop, zp, lod, wm,
                       wins=[(xm - 1.0, .75, top + .7, top + 1.95), (xm + 1.0, .75, top + .7, top + 1.95)],
                       trim=gt)
            yb = yF + .36
            m.facing([(X, yb, top), (X, yb, ftop), (xm, yb, zp), (XL, yb, ftop), (XL, yb, top)], (0, 1, 0), wm)
            for xx, d in ((X, 1), (XL, -1)):
                m.facing([(xx, yF, top), (xx, yb, top), (xx, yb, ftop), (xx, yF, ftop)], (d, 0, 0), wm)
            k = (zp - ftop) / half
            cop = [(XL + E, ftop - .02), (xm, zp - .02), (X - E, ftop - .02)]
            slab(m, cop, yF - .1, yb + .1, lambda a, q, z: (q, a, z), lod, "Dressed", end="Dressed", eave="Dressed",
                 th=.16, what="parapet coping")
            rake_corbels(m, (XL, yF), (X, yF), ftop, zp - ftop, lod, wm)
            y0r, over0 = yF + .37, 0.0                # 1 cm behind the parapet's back face
        else:
            gw = [(xm, 1.5, top + .7, top + 2.1)] if v["tower"] is None else [(xm + 1.0, .8, top + .7, top + 2.0)]
            gable_wall(m, g, (XL, yF), (X, yF), top, ridge, lod, wm, wins=gw, trim=gt)
            corbels(m, fw, top, lod, wm)
            y0r, over0 = yF, .45
        rear_cov = pieces and piece_top(pieces[0][0]) > top - .1
        if not rear_cov:
            gable_wall(m, g, (X, yR), (XL, yR), top, ridge, lod, bm, wins=[(xm, .8, top + .7, top + 2.0)],
                       trim=dict(gt, reveal=bm))
        gable_roof(m, XL, X, y0r, yR, top, ridge, lod, v["roof_mat"], over=(over0, .3),
                   sides=("e" if corner else "p", "p"))
        if corner:
            side_dormers(m, g, half, top, ridge, .16, [yF + 6.5, yF + 10.5], lod, wm, v["roof_mat"],
                         dict(door=v["door"], lites=v["lites"]), sides=(-1,), xc=xm)
        chimney(m, X - .5, yF + 6.0, .35, .45, top + .3, ridge + 1.0, lod)
        rtop = top

    # ---- corner towers
    if corner and v["tower"] == "square":           # an Italianate tower over the corner, a stage above the cornice
        a = 1.5
        zb_ = z1
        zt = zb_ + 3.6
        tower(m, g, lod, XL + a, yF + a, a, 4, zb_, zt, 3.4, wm, v["roof_mat"], dict(ftrim), [
            (zb_ + .8, zb_ + 2.7, (0, 1, 2, 3))], "Dressed")
    elif corner and v["tower"] == "octagon":        # a Queen Anne belfry over the corner, rising out of the roof
        a = 1.45
        zt = top + 5.4
        tower(m, g, lod, XL + a - .05, yF + a - .05, a, 8, top, zt, 4.6, wm, v["roof_mat"], dict(ftrim), [
            (top + 3.2, top + 4.8, tuple(range(8)))], "Dressed")

    # ---- the side street (corner buildings): shop glass round the corner, windows on every floor
    if corner:
        span = yR - yF
        k = max(3, round((span - 2.0) / 2.6))
        ys = [yF + 1.4 + (span - 2.8) * j / (k - 1) for j in range(k)]
        sst = style(top, mats if not parapet else [(0.0, top, wm)], [(1.0, 1.0, 3.0)] + win, belts=(G,),
                    plinth=(.45, .05, "Greystone"), corners=False, frieze=None, belt_mat="Dressed")
        sw = Wall((XL, yR), (XL, yF))
        shop2 = [(sw.u_of(yF + 3.2), sw.u_of(yF + .75), 0.0, SHOP_HEAD, "shop")]
        om = [(y, 0) for y in ys if y < yF + 4.3]
        sw_ = wall(m, g, sst, (XL, yR), (XL, yF), "-" if pieces else "x", "x", ys, lod, trim=ftrim, holes=shop2,
                   omit=om, waive=dict(STREET, corners="the shop glass turns the corner to a corner pier"))
        if lod < 2:
            ua, ub = shop2[0][0], shop2[0][1]
            lbox(m, sw_, ua - .3, ub, 3.30, 4.12, E, .16, v["door"], ("in",))
            lbox(m, sw_, ua - .36, ub, 4.12 + E, 4.2, E, .22, "Dressed" if granite else v["door"])
        if flat:
            corbels(m, sw_, top, lod, wm)

    # ---- the back of the main block
    rb = [-2.4, 0.0, 2.4] if not corner else [xm - 2.3, xm, xm + 2.3]
    rwin = [(1.0, 1.0, 3.0)] + floors(n, False)
    if pieces:
        zc = piece_top(pieces[0][0]) + .45
        rst = style(rtop, [(0.0, rtop, bm)], rwin, plinth=None, corners=False, frieze=None)
        if zc < rtop - 1.5:
            rw = wall(m, g, rst, (X, yR), (XL, yR), "-", sx, rb, lod, z0=zc, trim=rtrim)
            if flat:
                corbels(m, rw, rtop, lod, bm)
    else:
        rst = style(rtop, [(0.0, rtop, bm)], rwin, plinth=None, corners=False, frieze=None)
        rw = wall(m, g, rst, (X, yR), (XL, yR), "-", sx, rb, lod, door=(rb[1], 1.1, 2.95), trim=rtrim,
                  waive={"balance": "the back door to the service lane"})
        if flat:
            corbels(m, rw, rtop, lod, bm)
        zc = 0.0
    exposed = [lz(j) for j in range(1, n) if lz(j) > zc + .2]      # landings clear of the roof behind
    if v["escape"] and exposed and pieces:          # over a back block, never past the rear line
        fire_escape(m, rb[2], yR, exposed, lod, floor=zc)
    if v["decks"] and exposed and pieces:
        lv = [(z - .05, z + 2.9 if i + 1 < len(exposed) else z + 1.1) for i, z in enumerate(exposed)]
        rear_decks(m, rb[0] - 1.3, rb[0] + 1.4, yR, 1.8, lv, lod)

    # ---- the pieces behind: a back block, a stockroom, down to the service lane
    for i, (k, ya, yb) in enumerate(pieces):
        h = piece_top(k)
        nxt = pieces[i + 1] if i + 1 < len(pieces) else None
        pst = style(h, [(0.0, h, bm)], piece_win(k), belts=(G,) if k > 1 else (), plinth=(.45, .05, "Greystone"),
                    corners=False, frieze=None, belt_mat="Dressed")
        party(m, (X, ya), (X, yb), 0.0, h, bm)
        if corner:
            span = yb - ya
            kk = max(1, round(span / 2.6))
            ys = [ya + span * (j + .5) / kk for j in range(kk)]
            pw = wall(m, g, pst, (XL, yb), (XL, ya), "x" if nxt is None else "-", "-", ys, lod, trim=rtrim,
                      door=(ys[len(ys) // 2], 1.1, 2.95) if k == 1 else None,
                      waive={"balance": "a loading door onto the side street"})
            corbels(m, pw, h, lod, bm)
        else:
            party(m, (-X, yb), (-X, ya), 0.0, h, bm)
        if nxt is None:
            ew = wall(m, g, pst, (X, yb), (XL, yb), "-", sx, rb, lod, door=(rb[1], 1.4 if k == 1 else 1.1, 2.95),
                      trim=rtrim, waive={"balance": "the loading door to the service lane"})
        else:
            hz = piece_top(nxt[0]) + .45
            ew = wall(m, g, pst, (X, yb), (XL, yb), "-", sx, rb, lod, z0=hz, trim=rtrim) if hz < h - 1.5 else None
        if ew is not None:
            corbels(m, ew, h, lod, bm)
        x0 = XL - .3 if corner else XL + E
        cornice_roof(m, x0, X - E, ya + E, yb + .3, h, lod, deep=.45, side=bm, ends=bm, front=False)
        if k >= 2:
            chimney(m, (XL + .5) if not corner else X - .5, yb - 2.0, .3, .4, h + .3, h + 1.6, lod)
        if lod < 2 and k == 1 and yb - ya > 9:      # a skylight over a long stockroom
            s0, s1 = ya + 2.5, min(ya + 6.5, yb - 1.5)
            zz = h + .45
            wbox(m, -1.6, 1.6, s0, s1, zz, zz + .35, bm, ("z-",))
            g.facing([(-1.5, s0 + .1, zz + .35 + E), (1.5, s0 + .1, zz + .35 + E), (1.5, s1 - .1, zz + 1.1),
                      (-1.5, s1 - .1, zz + 1.1)], (0, -1, 1), "Glass")
            m.facing([(-1.5, s1 - .1, zz + .35 + E), (1.5, s1 - .1, zz + .35 + E), (1.5, s1 - .1, zz + 1.1),
                      (-1.5, s1 - .1, zz + 1.1)], (0, 1, 0), "Iron")
            for xx, d in ((-1.5, -1), (1.5, 1)):
                m.facing([(xx, s0 + .1, zz + .35 + E), (xx, s1 - .1, zz + .35 + E), (xx, s1 - .1, zz + 1.1)],
                         (d, 0, 0), "Iron")
    if hand == "R":
        for mesh in (m, g):
            mesh.v = [(-x, y, z) for x, y, z in mesh.v]
            mesh.f = [face[::-1] for face in mesh.f]
    finish(m, g)
