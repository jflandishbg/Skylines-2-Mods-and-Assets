"""Lobstertown Motor Courts (ZP4, the author 2026-11-18): the 1920s tourist cabin courts of the Maine coast road.

Low shingle cabins, each its own small gable (or gambrel) with a door at grade under a canopy, linked round a paved
auto court; an office with a bigger gable and a chimney at the street. Layouts (courtplan.py): 'U' (front row, both
wings, rear row), 'L' (right wing and rear row), 'R' (two facing wings, the court running to the rear line).
Each cabin is built in its own frame (front wall at y 0, facing -y) and placed with a quarter turn, so every wall
keeps the rulebook's checks.

    build(lod, W=3, D=5, **variant)

Variant keys: layout 'U' | 'L' | 'R'; roof 'gable' | 'gambrel'; wall (cabins), base (stone), office_wall,
roof_mat, door, trim_door, lites
"""
import math
from lt_kit import Mesh, finish, wall, style, gable_wall, gable_roof, porch, wbox, chimney, E, TRIM
import nf_rules
from lt_designs.courtplan import plan, CABIN

DEFAULT = dict(layout="U", roof="gable", wall="ShingleGrey", office_wall="Clapboard", base="Rubble",
               roof_mat="SlateDark", door="Green", lites="2")
EAVE = 3.0
PITCH_G = .8
GAM = dict(knee=2.0, inset=.8, slope=.55)
CANOPY = .6


def cabin(lod, kind, v, tl=False, tr=False, par=0):
    """One cabin in its own frame: front wall at y 0 from x -w/2 to w/2, walls going back to y = d."""
    w, d = CABIN[kind]
    h = w / 2
    m, g = Mesh(), Mesh()
    office = kind == "O"
    wm = v["office_wall"] if office else v["wall"]
    eave = EAVE + (.4 if office else 0.0)
    st = style(eave, [(0.0, eave, wm)], [(.9, .9, 2.4)], plinth=(.45 + .015 * par, .05, "Greystone") if v["base"] else None,
               corners=False, frieze=None)
    trim = dict(door=v["door"], lites=v["lites"], masonry="Dressed", reveal=wm, lean=True)
    waive = {"balance": "a cabin: door and one window to a side, as on a tourist court",
             "rhythm": "a cabin's two windows and door"}
    fb = [-h * .62, 0.0, h * .62]
    wall(m, g, st, (-h, 0), (h, 0), "x", "x", fb, lod, door=(0.0, 1.0, 2.4), trim=trim, waive=waive)
    sb = [d * .2, d * .5, d * .8] if office else [d * .3, d * .7]
    wall(m, g, st, (h, 0), (h, d), "x", "x", [] if tr else sb, lod, trim=trim, waive=waive)
    wall(m, g, st, (h, d), (-h, d), "x", "x", ([h * .6, 0.0, -h * .6] if office else [h * .5, -h * .5]), lod, trim=trim, waive=waive)
    wall(m, g, st, (-h, d), (-h, 0), "x", "x", [] if tl else sb, lod, trim=trim, waive=waive)
    gam = v["roof"] == "gambrel" and not office
    if gam:
        zk, ik = eave + GAM["knee"], GAM["inset"]
        zr = zk + (h - ik) * GAM["slope"]
        shape = knee = (zk, ik)
    else:
        zr = eave + h * PITCH_G
        shape = knee = None
    gt = dict(trim)
    gable_wall(m, g, (-h, 0), (h, 0), eave, zr, lod, wm, wins=[], trim=gt, shape=shape)
    gable_wall(m, g, (h, d), (-h, d), eave, zr, lod, wm, wins=[], trim=gt, shape=shape)
    gable_roof(m, -h, h, 0.0, d, eave, zr, lod, v["roof_mat"], over=(.45, .1), sides=("e", "e"), knee=knee)
    # the door canopy: a shed on two posts, entrance at grade
    if lod < 2:
        porch(m, -1.1, 1.1, 0.0, CANOPY, lod, zf=.14, zt=2.75, mat=v["roof_mat"], rail=False, open_sides=(), skirt=False)
        chimney(m, h * .45, d * .6, .32, .45, zr - .9, zr + 1.0, lod)
    nf_rules.verdict(m)
    return m, g


def put(dst, src, ang, ox, oy):
    c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    base = len(dst.v)
    dst.v += [(c * x - s * y + ox, s * x + c * y + oy, z) for x, y, z in src.v]
    for f, k in zip(src.f, src.m):
        name = src.mats[k]
        if name not in dst.mats:
            dst.mats.append(name)
        dst.f.append([base + i for i in f])
        dst.m.append(dst.mats.index(name))


def _rect(kind, rot, ox, oy):
    w, d = CABIN[kind]
    pts = [(-w / 2, 0), (w / 2, 0), (w / 2, d), (-w / 2, d)]
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    xs = [c * x - s * y + ox for x, y in pts]
    ys = [s * x + c * y + oy for x, y in pts]
    return min(xs), max(xs), min(ys), max(ys)


def _gap(a, b):
    return math.hypot(max(0, a[0] - b[1], b[0] - a[1]), max(0, a[2] - b[3], b[2] - a[3]))


LW, LZ0, LZ1 = 1.4, 2.28, 2.58           # a covered link: width, underside, top (clear of the cabin eave at 3.0)


def links(m, items, lod, mat):
    """Covered walks tie the cabins into one building (a tourist court's roofed breezeways and porte-cochere)."""
    rs = [_rect(*it) for it in items]
    edges = sorted((_gap(rs[i], rs[j]), i, j) for i in range(len(rs)) for j in range(i + 1, len(rs)))
    par = list(range(len(rs)))
    idx = 0

    def find(i):
        while par[i] != i:
            i = par[i]
        return i
    for _, i, j in edges:
        if find(i) == find(j):
            continue
        par[find(i)] = find(j)
        if _gap(rs[i], rs[j]) < .3:                  # cabins that touch need no walk
            continue
        a, b = rs[i], rs[j]
        ox0, ox1 = max(a[0], b[0]), min(a[1], b[1])
        oy0, oy1 = max(a[2], b[2]), min(a[3], b[3])
        if ox1 - ox0 >= .8:                          # facing across a gap in y: a straight walk
            x = (ox0 + ox1) / 2
            hw = min(LW, ox1 - ox0 - .05) / 2
            ya, yb = (a[3], b[2]) if a[3] <= b[2] else (b[3], a[2])
            segs = [(x - hw, x + hw, ya - .3, yb + .3)]
        elif oy1 - oy0 >= LW + .4:                   # facing across a gap in x
            y = (oy0 + oy1) / 2
            xa, xb = (a[1], b[0]) if a[1] <= b[0] else (b[1], a[0])
            segs = [(xa - .3, xb + .3, y - LW / 2, y + LW / 2)]
        else:                                        # diagonal: out of A in x, then along y into B
            ya = (a[2] + a[3]) / 2
            xb = (b[0] + b[1]) / 2
            xe = a[1] if a[1] <= b[0] else a[0]
            ye = b[2] if ya <= b[2] else b[3]
            segs = [(min(xe, xb) - (.3 if xe <= xb else -.3) - LW / 2 * 0, max(xe, xb) + .3, ya - LW / 2, ya + LW / 2),
                    (xb - LW / 2, xb + LW / 2, min(ya, ye) - .3, max(ya, ye) + .3)]
        for x0, x1, y0, y1 in segs:
            idx += 1
            za, zb = LZ0 + .005 * idx, LZ1 + .005 * idx          # each walk at its own height: no shared planes
            j = .004 * idx
            wbox(m, x0 - j, x1 + j, y0 - j, y1 + j, za, zb, mat)
            if lod < 2:
                n = int(max(x1 - x0, y1 - y0) // 3.6)
                for k in range(1, n + 1):
                    px = x0 + (x1 - x0) * k / (n + 1) if x1 - x0 > y1 - y0 else (x0 + x1) / 2
                    py = y0 + (y1 - y0) * k / (n + 1) if y1 - y0 >= x1 - x0 else (y0 + y1) / 2
                    wbox(m, px - .11, px + .11, py - .11, py + .11, 0.0, za + E, "Dressed", ("z+",))


def build(lod, W=3, D=5, **variant):
    variant.pop("palette", None)
    v = dict(DEFAULT, **variant)
    m, g = Mesh(), Mesh()
    cache = {}
    cache_n = []
    items = plan(v["layout"], W, D)["items"]
    links(m, items, lod, v["roof_mat"])
    rs = [_rect(*it) for it in items]
    for n, (kind, rot, ox, oy) in enumerate(items):
        c, s_ = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        side = [False, False]                        # a wall that butts a neighbour gets no windows
        for k, o in enumerate(items):
            if k != n and _gap(rs[n], rs[k]) < .3:
                dx = (o[2] - ox) * c + (o[3] - oy) * s_
                side[0 if dx > 0 else 1] = True      # [right, left] in the cabin's own frame
        key = (kind, side[1], side[0], n % 3)
        if key not in cache:
            cache[key] = cabin(lod, kind, v, tl=side[1], tr=side[0], par=n % 3)
        cm, cg = cache[key]
        dl = .011 * (len(cache_n) % 5)               # neighbours' back walls and roofs never share a plane
        cache_n.append(1)
        sx, sy = -math.sin(math.radians(rot)) * dl, math.cos(math.radians(rot)) * dl
        put(m, cm, rot, ox + sx, oy + sy)
        put(g, cg, rot, ox + sx, oy + sy)
    finish(m, g)
