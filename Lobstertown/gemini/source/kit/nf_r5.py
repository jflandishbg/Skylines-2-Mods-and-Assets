"""New France round 5, "Paris on the Delaware": GPT's 28 New Orleans designs (round5-designs.json).
Built on the round-4 builder (nf_r4): the same JSON -> spec conversion, main block, rear parts and court, plus the
New Orleans kit: front galleries (wood or cast iron, one to three decks, wrap-around returns), curved balconies,
porte-cochere and pedestrian tunnels, a ground side-gallery notch, an upper loggia, oval bull's-eye dormers, ridge
cresting, pedimented window hoods, rear court galleries with stacked stairs, hanging ferns and rail pots.
Output: generator/out_r5 (its own import batch and texture owner). Level 1 only.
Run: blender -b --factory-startup -P nf_r5.py [-- Design ...] [-- PILOTS] [-- --a-only]
"""
import json, math, sys, copy, zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nf_build as nb
import nf_round3 as r3
import nf_r4 as r4
from nf_build import House, Opening, Face, rectangle, edges, prism, X, Y, UP, DOWN

r4.SRC = Path(r"C:\Users\<you>\CS2Planner\NewFrance\GPT_INBOX\2026-11-05_round5\round5-designs.json")
r4.OUT = nb.HERE / "out_r5"
r4.OWNER = "NA_NewFranceSideHallIronHouse_L1_1x6"
r4.MANIFEST, r4.CHANGES_FILE = "manifest_r5.json", "r5_changes.json"
r4.DRESS_SRC = Path("__none__")                    # round 5 B/C keep the A geometry (GPT): palette only
PILOTS = ["SideHallIronHouse", "SingleCamelbackHouse", "CenterHallPedimentCottage", "LeftCornerWrapGalleryRow",
          "EntresolArchMain", "PorteCochereMain"]
note = r4.note
nb.LACE_K = 2.4                                    # broad lace motifs (GPT: "a few broad motifs per bay")
FOLIAGE = "=Green"                                 # pinned: foliage stays dark green in every colourway
FOLIAGE2 = "=ClapSage"
POT = "=RenderOchre"

# ------------------------------------------------------------------ spec
VOIDS = ("arched-passage", "open-passage")

def to_spec(a):
    a = copy.deepcopy(a)
    for o in a["front"] + a["side"] + a["rear"]:
        if o["kind"] in VOIDS:
            o["_void"] = True
        o["kind"] = {"arched-french-door": "french-door", "arched-sash": "sash", "attic-sash": "attic-sash",
                     "arched-passage": "door", "open-passage": "door"}.get(o["kind"], o["kind"])
    for dm in a["dormers"]:
        dm["width"] = dm.get("width_m", dm.get("width"))
    S = r4.to_spec(a)
    shut = a.get("shutter_material") or a["shutters"]["material"]
    lists = (("front", a["front"]), ("rear", a["rear"]))
    for key, src in lists:
        for o, j in zip(S[key], src):
            _fix(o, j, shut)
    sides = [j for j in a["side"]]
    for o, j in zip(S["sides"], sides):
        _fix(o, j, shut)
    # openings on recessed inner walls (notch, loggia) are built by their feature, not on the main faces
    S["inner"] = [o for o in S["front"] + S["sides"] if o.get("xo") or o.get("yo")]
    S["front"] = [o for o in S["front"] if not o.get("yo")]
    S["sides"] = [o for o in S["sides"] if not o.get("xo")]
    S["dormer_list"] = [dm for dm in a["dormers"] if dm.get("kind") != "oval-bullseye"]
    S["ovals"] = [dm for dm in a["dormers"] if dm.get("kind") == "oval-bullseye"]
    return S

def _fix(o, j, shut):
    if j.get("_void"):
        o.update(kind="void", k="A")
    if j.get("shutters") and o["kind"] in ("sash", "french", "pair", "door"):
        o["shutter"] = shut

# ------------------------------------------------------------------ galleries
def _posts_top(g, i, decks, roof_under):
    return decks[i + 1] - g.get("deck_thickness_m", .16) if i + 1 < len(decks) else roof_under

def _shed_under(roof, w_wall, w_face, w_post):
    """underside height of a shed canopy at the post line"""
    zw, zf = roof["wall_z"], roof["front_z"]
    t = (w_post - w_wall) / (w_face - w_wall) if abs(w_face - w_wall) > 1e-6 else 1
    return zw + (zf - zw) * t - roof.get("thickness_m", .08)

def post(h, x, y, z0, z1, structure, w, piers=None):
    m = h.body
    if z1 - z0 < .1:
        return
    if structure == "iron":
        nb.iron_post(h, x, y, z0, z1)
        return
    if piers and z0 < piers["top_z"] - .05:
        px, py = piers["size_xy"]
        m.box(x - px / 2, x + px / 2, y - py / 2, y + py / 2, z0, piers["top_z"], piers["material"], bottom=False)
        z0 = piers["top_z"]
    hw = (w or .16) / 2
    m.box(x - hw, x + hw, y - hw, y + hw, z0, z1, "Cream", bottom=False)
    if h.lod == 0 and structure == "turned-wood":
        m.box(x - hw - .03, x + hw + .03, y - hw - .03, y + hw + .03, z1 - .18, z1 - .08, "Cream", bottom=False)

def rail(h, x0, y0, x1, y1, z, style):
    if math.hypot(x1 - x0, y1 - y0) < .15:
        return
    if style.startswith("lace"):
        nb.railing(h, x0, y0, x1, y1, z, .95, "Iron")
    else:
        nb.railing(h, x0, y0, x1, y1, z, .95, "Cream", .14)

def beam(h, pts, z_top, structure, axis):
    """frieze under each gallery storey: cast-iron lace on iron galleries, a timber beam with a scroll frieze on wood"""
    m = h.body
    if structure == "iron":
        nb.iron_frieze(h, pts, z_top)
        return
    (ax, ay), (bx, by) = pts[0], pts[-1]
    if axis == "x":
        m.box(min(ax, bx) - .08, max(ax, bx) + .08, ay - .09, ay + .09, z_top - .26, z_top, "Cream")
    else:
        m.box(ax - .09, ax + .09, min(ay, by) - .08, max(ay, by) + .08, z_top - .26, z_top, "Cream")

def gallery_run(h, S, a, g, axis, span, wall, outer, post_w, posts, roof, decks, gaps=(), skip_end=(), roof_under=None):
    """one straight run of gallery. axis 'x': span = (x0, x1) lot X, wall/outer = lot Y of the wall line and the
    outer edge, posts = lot X list on the post line; axis 'y' (a return): span = (y0, y1), wall/outer = lot X."""
    m = h.body
    th = g.get("deck_thickness_m", .16)
    structure = g.get("structure", "iron")
    style = g.get("rail_style", "lace")
    if axis == "x":
        B = lambda u, w: (X(u), Y(w))
    else:
        B = lambda u, w: (X(w), Y(u))
    a0, a1 = span
    (p0x, p0y), (p1x, p1y) = B(a0, wall), B(a1, outer)
    xa, xb = sorted((p0x, p1x)); ya, yb = sorted((p0y, p1y))
    if roof and roof.get("kind") in ("shallow-shed", "shed"):
        if axis == "x":
            r3.shed(h, "x", max(xa - .02, -nb.W / 2), min(xb + .02, nb.W / 2), Y(wall), Y(outer) - .06 * (1 if outer < wall else -1),
                    roof["wall_z"], roof["front_z"], roof.get("material", "TinFlat"))
        else:
            sgn = 1 if outer > wall else -1
            r3.shed(h, "y", ya, yb, X(wall), X(outer) + .06 * sgn, roof["wall_z"], roof["front_z"],
                    roof.get("material", "TinFlat"))
    for i, z in enumerate(decks):
        if i == 0 and z > .2 and h.lod < 2:
            m.box(xa, xb, ya, yb, 0, z - th, "Rubble", bottom=False)
        m.box(xa, xb, ya, yb, (0 if i==0 and h.lod==2 else max(0, z - th)), z, "Deck", top=None, bottom=(i > 0))
        top = _posts_top(g, i, decks, roof_under)
        if h.lod == 2:                                   # far: one plain post per line, deck to canopy
            if i == 0:
                hi = roof_under or (decks[-1] + .95)
                far = [posts[0], posts[-1]]   # every other post, both ends
                for pu in far:
                    px, py = B(pu, g["_post_line"])
                    m.box(px - .06, px + .06, py - .06, py + .06, z, hi, "Iron" if structure == "iron" else "Cream",
                          bottom=False)
            continue
        if top is None:
            continue
        if True:
            near = posts if not (h.lod == 1 and nb.LITE >= 6) else                 list(posts[::2]) + ([posts[-1]] if len(posts) % 2 == 0 else [])    # LITE 6 near: every other post
            for pu in near:
                px, py = B(pu, g["_post_line"])
                post(h, px, py, z, top, g.get("upper_structure",structure) if i>0 else structure, post_w, g.get("piers") if i == 0 else None)
            if len(posts) > 1 and h.lod < 2:
                beam(h, [B(pu, g["_post_line"]) for pu in posts], top, g.get("upper_structure",structure) if i>0 else structure, axis)
        if h.lod == 2:
            continue
        if z > .45 or i > 0:
            lo, hi = sorted((a0 + .07, a1 - .07))
            segs = [(lo, hi)]
            if i == 0:
                for ga, gb in gaps:
                    segs = [s2 for s in segs for s2 in ((s[0], min(s[1], ga)), (max(s[0], gb), s[1])) if s2[1] - s2[0] > .2]
            for sa, sb in segs:
                (rx0, ry0), (rx1, ry1) = B(sa, g["_post_line"]), B(sb, g["_post_line"])
                rail(h, rx0, ry0, rx1, ry1, z, style)
            for end, u in (("a0", a0 + .07), ("a1", a1 - .07)):
                if end in skip_end:
                    continue
                (rx0, ry0), (rx1, ry1) = B(u, g["_post_line"]), B(u, wall - .03 * (1 if wall > outer else -1))
                rail(h, rx0, ry0, rx1, ry1, z, style)

def gallery(h, S, a, g):
    x0, x1, y0, y1 = g["bounds_m"]
    decks = g["deck_z_m"]
    roof = g.get("roof") or {}
    g["_post_line"] = g.get("front_post_y_m", y0 + .13)
    roof_under = None
    if roof.get("kind") in ("shallow-shed", "shed"):
        roof_under = _shed_under(roof, y1, y0, g["_post_line"])
    elif roof.get("kind") == "upper-deck":
        roof_under = roof["underside_z"]
    wrap = g.get("wrap")
    gaps = []
    yf = S["walls"][2]
    if decks[0] > .05:
        for o in S["front"]:
            if o["k"] == "D" and o["floor"] == 0 and x0 < o["c"] < x1 and abs(o["b"] - decks[0]) < .3:
                gaps.append((o["c"] - .6, o["c"] + .6))
    skip = []
    if wrap:
        skip = ["a0"] if wrap["side"] == "left" else ["a1"]
    if roof.get("kind") == "composite-upper-deck":
        for sg in roof["segments"]:
            sx0, sx1 = sg["bounds_m"][:2]
            ps = [p for p in g["post_x_m"] if sx0 - .2 <= p <= sx1 + .2]
            ru = sg.get("underside_z") or _shed_under(sg, y1, y0, g["_post_line"])
            gallery_run(h, S, a, g, "x", (sx0, sx1), y1, y0, g.get("post_width_m"), ps,
                        sg if sg["kind"] == "shed" else None, decks, [gp for gp in gaps if sx0 < gp[0] < sx1],
                        skip_end=(["a1"] if sx1 < x1 - .05 else []) + (["a0"] if sx0 > x0 + .05 else []), roof_under=ru)
    else:
        gallery_run(h, S, a, g, "x", (x0, x1), y1, y0, g.get("post_width_m"), g.get("post_x_m", []), roof, decks,
                    gaps, skip, roof_under)
    if wrap:
        wx0, wx1, wy0, wy1 = wrap["bounds_m"]
        gw = dict(g, _post_line=wrap["post_line"])
        outer = wx0 if wrap["side"] == "left" else wx1
        ru = _shed_under(roof, wrap["return_wall"], outer, wrap["post_line"]) if roof_under is not None and \
            roof.get("kind") in ("shallow-shed", "shed") else roof_under
        gallery_run(h, S, a, gw, "y", (wy0, wy1), wrap["return_wall"], outer, g.get("post_width_m"),
                    [p for p in wrap["post_y_m"] if p > wy0 + .3], roof, decks, skip_end=["a0"], roof_under=ru)
    # steps from the street up to a raised ground deck, at each door gap (kept inside the lot)
    y_out = Y(y0)
    for ga, gb in gaps:
        xc = (ga + gb) / 2
        z = decks[0]
        if z > .2:
            n = max(1, round(z / .17))
            tread = max(.03, min(.27, (y0 - .03) / n))
            for k in range(n):
                h.body.box(X(xc) - .55, X(xc) + .55, y_out - (n - k) * tread, y_out, k * z / n, (k + 1) * z / n - .001,
                           "Dressed", bottom=False)
            r3.walk_to(h, X(xc), y_out - n * tread, 1.0)
        else:
            r3.walk_to(h, X(xc), y_out, 1.0)
    return [o["c"] for o in S["front"] if o["k"] == "D" and o["floor"] == 0 and x0 < o["c"] < x1]

def curved_balcony(h, S, a, g):
    m = h.body
    x0, x1, y0, y1 = g["bounds_m"]
    z = g["deck_z_m"][0]
    th = g.get("deck_thickness_m", .16)
    poly = g["front_polyline_xy"]
    if h.lod == 2:
        poly = [poly[0], poly[len(poly) // 2], poly[-1]]
    pts = [(X(px), Y(py)) for px, py in poly] + [(X(x1), Y(y1)), (X(x0), Y(y1))]
    if nb.area2d(pts) < 0:
        pts.reverse()
    if nb.is_convex(pts):
        prism(m, pts, z - th, z, "Dressed")
    else:
        prism(m, pts, z - th, z, "Dressed")
    if h.lod == 2:
        return
    for (ax, ay), (bx, by) in zip(poly, poly[1:]):
        rail(h, X(ax), Y(ay), X(bx), Y(by), z, "lace")
    for px, py in (poly[0], poly[-1]):
        rail(h, X(px), Y(py), X(px), Y(y1) - .03, z, "lace")
    for cx in (1.2, 3.0, 5.0, 6.8):
        r3.console(h, X(cx), Y(y1), 0, -1, z - th, .45)

# ------------------------------------------------------------------ features
def tunnel(h, S, a, f, arch=None):
    """open tunnel through the ground storey: closed side walls, soffit, paved floor (the end walls carry voids)"""
    m = h.body
    x0, x1, ya, yb = f["bounds_m"]
    cz = f["ceiling_z"]
    mat = S["facade"][1] if S["facade"][1] not in ("Clapboard", "ClapSage") else "RenderSide"
    for x, sgn in ((X(x0), 1), (X(x1), -1)):
        fc = Face((x, Y(ya)), (x, Y(yb))) if sgn > 0 else Face((x, Y(yb)), (x, Y(ya)))
        fc.quad(m, 0, fc.length, 0, cz, 0, mat)
    m.polygon([(X(x0), Y(ya), cz), (X(x1), Y(ya), cz), (X(x1), Y(yb), cz), (X(x0), Y(yb), cz)], DOWN, "Cream")
    m.box(X(x0), X(x1), Y(ya) + .01, Y(yb) - .01, 0, .05, "Paving", bottom=False)
    if h.lod < 2 and arch:                                # stone surround at both ends
        for yw, out in ((Y(ya), -1), (Y(yb), 1)):
            for xs in (x0 - .17, x1):
                m.box(X(xs), X(xs + .17), yw - .04 if out < 0 else yw, yw if out < 0 else yw + .04, 0, arch["crown_m"] + .1,
                      "Dressed", bottom=False)
            m.box(X(x0 - .17), X(x1 + .17), yw - .04 if out < 0 else yw, yw if out < 0 else yw + .04,
                  arch["crown_m"], arch["crown_m"] + .17, "Dressed", bottom=False)
    r3.walk_to(h, X((x0 + x1) / 2), Y(ya), x1 - x0 - .2)

def notch(h, S, a, f):
    """ground side-gallery notch: only the ground storey retreats to wall_x; deck, posts, ceiling, end returns"""
    m = h.body
    gx0, gx1, gy0, gy1 = f["bounds_m"]
    dz, cz = f["deck_z"], f["ceiling_z"]
    xi = X(gx0)
    inner = Face((xi, Y(gy0)), (xi, Y(gy1)))
    ops = []
    for o in (f["door"], f["sash"]):
        ops.append(Opening(o["centre_y"] - gy0, o["width_m"], o["bottom_m"], o["top_m"],
                           "door" if o is f["door"] else "sash", S["inner_shutter"] if o is f["sash"] else None))
    bands = [(0, max(dz, .12), S["facade"][3]), (max(dz, .12), 99, S["facade"][1])]
    r3.poly_wall(h, inner, [(inner.length, cz), (0, cz)], bands, ops)
    for y, out in ((Y(gy0), -1), (Y(gy1), 1)):
        cf = Face((X(gx1), y), (xi, y)) if out < 0 else Face((xi, y), (X(gx1), y))
        r3.poly_wall(h, cf, [(cf.length, cz), (0, cz)], bands, [])
    m.polygon([(xi, Y(gy0), cz), (X(gx1), Y(gy0), cz), (X(gx1), Y(gy1), cz), (xi, Y(gy1), cz)], DOWN, "Cream")
    m.box(xi, X(gx1) - .01, Y(gy0), Y(gy1), 0, dz - .16, "Rubble", bottom=False)
    m.box(xi, X(gx1) - .01, Y(gy0), Y(gy1), dz - .16, dz, "Deck", bottom=False)
    px = X(gx1 - .15)
    for y in (8.35, 10.95, 13.65):
        m.box(px - .08, px + .08, Y(y) - .08, Y(y) + .08, dz, cz, "Cream", bottom=False)
    if h.lod < 2:
        nb.railing(h, px, Y(gy0) + .1, px, Y(9.7) - .6, dz, .92, "Cream", .14)
        nb.railing(h, px, Y(9.7) + .6, px, Y(gy1) - .1, dz, .92, "Cream", .14)

def loggia(h, S, a, f):
    x0, x1, y0, y1 = f["bounds_m"]
    ops = [(o["c"], o["w"], o["b"], o["t"], "french") for o in S["inner"] if o.get("yo")]
    r4.recess(h, S, x0, x1, f["inner_wall_y"], f["floor_z"], f["ceiling_z"], ops)
    if h.lod < 2:
        nb.railing(h, X(x0) + .05, Y(y0) - .02, X(x1) - .05, Y(y0) - .02, f["floor_z"], .95, "Iron")

def cresting(h, S, a, f):
    m = h.body
    x0, x1, ya, yb = f["bounds_m"]
    z0, ht = f["base_z"], f["height_m"]
    yc = Y((ya + yb) / 2)
    n = (0, -1, 0)
    chim = [c[0] for c in S["chimneys"]]
    if h.lod == 2:
        nb.dquad(m, [(X(x0), yc, z0), (X(x1), yc, z0), (X(x1), yc, z0 + ht * .6), (X(x0), yc, z0 + ht * .6)], n, "Iron")
        return
    nb.obar(m, (X(x0), yc), (X(x1), yc), .05, z0, z0 + .05, "Iron")
    k = min(f.get("max_motifs", 12), int((x1 - x0) / .6))
    if h.lod == 1:
        k = max(3, k // 2)
    for i in range(k):
        xc = x0 + (x1 - x0) * (i + .5) / k
        if any(abs(xc - c) < .5 for c in chim):
            continue
        w = .14
        nb.dquad(m, [(X(xc) - w, yc, z0 + .05), (X(xc) + w, yc, z0 + .05), (X(xc), yc, z0 + ht)], n, "Iron")
        if h.lod == 0:
            nb.dquad(m, [(X(xc), yc, z0 + ht * .45), (X(xc) + w * 1.3, yc, z0 + ht * .7), (X(xc), yc, z0 + ht * .95),
                         (X(xc) - w * 1.3, yc, z0 + ht * .7)], n, "Iron")

def hoods(h, S, a, f):
    m = h.body
    yf = r4.front_y(S)
    for xc in f["centres_x"]:
        w, b, p, r = f["width_m"], f["base_z"], f["projection_m"], f["rise_m"]
        m.box(X(xc - w / 2), X(xc + w / 2), yf - p, yf, b - .06, b, f.get("material", "Cream"))
        if h.lod < 2:
            nb.extrude(m, [(X(xc - w / 2), b), (X(xc + w / 2), b), (X(xc), b + r)], "y", yf - p, yf,
                       [f.get("material", "Cream")] * 3, (f.get("material", "Cream"), f.get("material", "Cream")))

def rear_gallery(h, S, a, f):
    """rear court gallery: decks against the rear wall, posts, iron rails, two stacked straight flights"""
    m = h.body
    x0, x1, yw, yo = f["bounds_m"]
    th = f.get("deck_thickness_m", .14)
    st = f["stairs"]
    sx_lo = min(min(s["from_xyz"][0], s["to_xyz"][0]) for s in st)
    sx_hi = max(max(s["from_xyz"][0], s["to_xyz"][0]) for s in st)
    lx1 = st[0]["landing_m"][1]
    inner_y = yo - .85
    if h.lod == 2:                                       # far: the decks as one closed block face
        m.box(X(x0), X(x1), Y(yw), Y(yo), f["deck_z_m"][0] - th, f["deck_z_m"][-1], "Deck", bottom=False)
        return
    for i, z in enumerate(f["deck_z_m"]):
        m.box(X(x0), X(x1), Y(yw), Y(inner_y), z - th, z, "Deck")               # inner walk
        m.box(X(x0), X(lx1), Y(inner_y), Y(yo), z - th, z, "Deck")             # landing
        if i == 0:
            m.box(X(sx_hi), X(x1), Y(inner_y), Y(yo), z - th, z, "Deck")
        if h.lod < 2:
            rail(h, X(x0) + .05, Y(yo) - .05, X(lx1), Y(yo) - .05, z, "lace")
            if i == 0:
                rail(h, X(sx_hi), Y(yo) - .05, X(x1) - .05, Y(yo) - .05, z, "lace")
                rail(h, X(lx1), Y(inner_y) - .03, X(sx_hi), Y(inner_y) - .03, z, "lace")
            else:
                rail(h, X(lx1), Y(inner_y) - .03, X(x1) - .05, Y(inner_y) - .03, z, "lace")
            for x in (x0 + .05, x1 - .05):
                rail(h, X(x), Y(yo) - .05, X(x), Y(yw) + .03, z, "lace")
    top = f["deck_z_m"][-1]
    for x in (x0 + .08, lx1, sx_hi, x1 - .08):
        m.box(X(x) - .055, X(x) + .055, Y(yo) - .11, Y(yo), 0, top, "Iron", bottom=False)
    for s in st:
        (fx, fy, fz), (tx, ty, tz) = s["from_xyz"], s["to_xyz"]
        r3.flight(h, r3.Path2([("line", (X(fx), Y(fy)), (X(tx), Y(ty)))]), fz, tz - .12, s["risers"], s["clear_width_m"])

# ------------------------------------------------------------------ oval bull's-eye dormers
def oval_face(dm):
    def face(h, f, zb, zde, mat):
        m = h.body
        L = f.length
        cu, cz = L / 2, (zb + zde) / 2
        rx, rz = dm["clear_oval_xy_m"][0] / 2, dm["clear_oval_xy_m"][1] / 2
        n = (12, 8, 6)[h.lod]
        ring = [(cu + rx * math.cos(2 * math.pi * i / n), cz + rz * math.sin(2 * math.pi * i / n)) for i in range(n)]
        def to_rect(u, z):                                   # project from the centre onto the face boundary
            du, dz = u - cu, z - cz
            s = min(abs((L / 2) / du) if abs(du) > 1e-9 else 1e9, abs(((zde - zb) / 2) / dz) if abs(dz) > 1e-9 else 1e9)
            return cu + du * s, cz + dz * s
        corners = [(L, zde), (0, zde), (0, zb), (L, zb)]
        for i in range(n):
            (u0, z0), (u1, z1) = ring[i], ring[(i + 1) % n]
            q0, q1 = to_rect(u0, z0), to_rect(u1, z1)
            poly = [(u0, z0), q0]
            a0, a1 = math.atan2(q0[1] - cz, q0[0] - cu), math.atan2(q1[1] - cz, q1[0] - cu)
            if a1 < a0:
                a1 += 2 * math.pi
            for cuv in corners:                              # include any rectangle corner between the two rays
                ac = math.atan2(cuv[1] - cz, cuv[0] - cu)
                while ac < a0:
                    ac += 2 * math.pi
                if a0 < ac < a1:
                    poly.append(cuv)
            poly = poly[:2] + sorted(poly[2:], key=lambda p: (math.atan2(p[1] - cz, p[0] - cu) - a0) % (2 * math.pi))
            poly += [q1, (u1, z1)]
            m.polygon([f.point(u, z) for u, z in poly], f.out, mat)
            if h.lod < 2:
                m.polygon([f.point(u0, z0), f.point(u1, z1), f.point(u1, z1, -.10), f.point(u0, z0, -.10)],
                          None or _inward(f, (u0 + u1) / 2 - cu, (z0 + z1) / 2 - cz), "Dressed")
        h.pane(f, cu - rx, cu + rx, cz - rz, cz + rz, -.10)
    return face

def _inward(f, du, dz):
    t = f.tangent
    return (-t.x * du, -t.y * du, -dz)

def ovals(h, S, a):
    if not S["ovals"] or S["R"]["type"] != "ridgeX" or h.lod == 2:   # far: too small to read
        return
    P = [(Y(y), z + r3.T) for y, z in S["R"]["P"]]
    i = max(range(len(P)), key=lambda i: P[i][1])
    face_m = "Dressed" if S["facade"][4] == "Dressed" else "Cream"
    for dm in S["ovals"]:
        r3.dormer3(h, X(dm["x"]), dm["width_m"], P[:i + 1], r4.front_y(S) + .48, "S", S["R"]["mat"], S["R"]["mat"],
                   face_m, face_h=dm["height_m"], face_fn=oval_face(dm))

# ------------------------------------------------------------------ planting
def fern(h, x, y, z, d, drop):
    m = h.body
    if h.lod == 2:
        return
    r = d * .32
    prism(m, nb.ngon(x, y, r, 6), z - .2, z, POT, bottom=True)
    m.box(x - .01, x + .01, y - .01, y + .01, z, z + .2, "Iron", bottom=False)
    k = 5 if h.lod == 0 else 3
    for i in range(k):
        a = 2 * math.pi * (i + .3) / k
        ca, sa = math.cos(a), math.sin(a)
        p0 = (x + ca * r * .6, y + sa * r * .6, z + .02)
        p1 = (x + ca * (d / 2 + .12) - sa * .13, y + sa * (d / 2 + .12) + ca * .13, z - drop * .55)
        p2 = (x + ca * (d / 2 + .12) + sa * .13, y + sa * (d / 2 + .12) - ca * .13, z - drop * .55)
        tip = (x + ca * (d / 2 + .05), y + sa * (d / 2 + .05), z - drop)
        nb.dquad(m, [p0, p1, tip, p2], (ca, sa, .6), FOLIAGE)

def rail_pot(h, x, y, z, d, fh):
    m = h.body
    if h.lod == 2:
        return
    r = d * .4
    prism(m, nb.ngon(x, y, r, 6), z - .18, z, POT, bottom=True)
    k = 4 if h.lod == 0 else 2
    for i in range(k):
        a = math.pi * i / k
        ca, sa = math.cos(a), math.sin(a)
        nb.dquad(m, [(x - ca * d * .55, y - sa * d * .55, z), (x + ca * d * .55, y + sa * d * .55, z), (x, y, z + fh)],
                 (-sa, ca, 0), FOLIAGE2)

def planting(h, S, a):
    if nb.LITE >= 5 or (nb.LITE >= 4 and h.lod == 1):
        return
    for p in a["planting"]:
        x, y, z = p["centre_xyz"]
        if p["kind"] == "hanging-fern":
            fern(h, X(x), Y(y), z, p["diameter_m"], p.get("drop_m", .6))
        elif p["kind"] == "rail-pot":
            rail_pot(h, X(x), Y(y), z, p["diameter_m"], p.get("foliage_height_m", .3))

# ------------------------------------------------------------------ recipe
FEATS = {"porte-cochere-tunnel": lambda h, S, a, f: tunnel(h, S, a, f, f.get("front_arch")),
         "pedestrian-tunnel": lambda h, S, a, f: tunnel(h, S, a, f),
         "ground-side-gallery-notch": notch, "upper-loggia": loggia, "ridge-cresting": cresting,
         "pedimented-window-hoods": hoods, "rear-court-gallery-and-stairs": rear_gallery}

def prep(S, a):
    for f in a["features"]:
        if f["kind"] == "ground-side-gallery-notch":
            gx0, gx1, gy0, gy1 = f["bounds_m"]
            S["sides"].append(dict(side="R", k="A", c=(gy0 + gy1) / 2, w=gy1 - gy0, b=0.0, t=f["ceiling_z"], floor=0,
                                   shutter=None, kind="void"))
            S["inner_shutter"] = None
        if f["kind"] == "upper-loggia":
            x0, x1, _, _ = f["bounds_m"]
            r4.front_void(S, x0, x1, f["floor_z"], f["ceiling_z"])
            S["front"] = [o for o in S["front"] if not (x0 < o["c"] < x1 and o["floor"] == 1)]
    # notch openings on the main right wall that the notch removes
    for f in a["features"]:
        if f["kind"] == "ground-side-gallery-notch":
            gx0, gx1, gy0, gy1 = f["bounds_m"]
            for o in S["sides"]:
                if o["side"] == "R" and o["kind"] != "void" and o["t"] < f["ceiling_z"] + .05 and \
                        o["c"] + o["w"] / 2 > gy0 and o["c"] - o["w"] / 2 < gy1:
                    note(a["design"], f"right ground opening at Y{o['c']} lies in the notch, dropped")
                    o["kind"] = "drop"
            S["sides"] = [o for o in S["sides"] if o["kind"] != "drop"]

def make_recipe(a, k):
    S = to_spec(a)
    prep(S, a)
    seed = zlib.crc32(f"{a['design']}/{k}".encode())
    def recipe(h):
        build = r4.MAINS.get(a["feature"].get("kind"), r4.main_block)
        d = r4.main_block(h, S, a)
        r4.rear(h, S, a, seed)                           # before the galleries: the far-LOD guard keeps rear masses
        ovals(h, S, a)
        served = []
        for g in a["galleries"]:
            if g["kind"] == "curved-balcony":
                curved_balcony(h, S, a, g)
            else:
                served += gallery(h, S, a, g)
        for f in a["features"]:
            FEATS[f["kind"]](h, S, a, f)
        skip = tuple(served) + tuple(o["c"] for o in S["front"] if o["kind"] == "void")
        r4.entries(h, S, a, skip=skip)
        planting(h, S, a)
        return d
    return recipe

r4.make_recipe = make_recipe

if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    a_only = "--a-only" in argv
    names = {v for v in argv if not v.startswith("--")}
    if names == {"PILOTS"}:
        names = set(PILOTS)
    r4.run(names or None, 1 if a_only else 3)
