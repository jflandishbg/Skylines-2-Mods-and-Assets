"""New France round 4: GPT's 40 JSON-specified designs (rows, Mixed Main Street, low homes, 2-wide accents).
Each design in round4-designs.json is converted into the round-3 spec shape, so the tested wall / opening / roof
builder (nf_round3.build_spec) does the main block. Feature modules add the bespoke pieces, and the rear parts and
court are built straight from GPT's explicit parts[] and court (the author 2026-11-05: slightly lower coverage, as GPT
planned it). Lot width and depth are set per design, so 2x6 and 2x4 lots work.
Output: generator/out_r4 (one import batch, its own texture owner).
Run: blender -b --factory-startup -P nf_r4.py [-- Design ...] [-- --a-only]
"""
import json, math, sys, copy, zlib, shutil, random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nf_build as nb
import nf_round3 as r3
from nf_build import House, Opening, Face, rectangle, edges, prism, X, Y, UP, DOWN

SRC = Path(r"C:\Users\<you>\CS2Planner\NewFrance\GPT_INBOX\2026-11-04_round4\round4-designs.json")
OUT = nb.HERE / "out_r4"
OWNER = "NA_NewFranceCrossGableCottage_L1_1x6"     # owns the atlas copy for this batch
PILOTS = ["CrossGableCottage", "InsetGalleryHouse", "LeftCornerGableEndRow", "MainStationer", "RightCornerMainBooks",
          "AsymmetricGableDouble"]
CHANGES = []                                        # every correction to GPT's numbers, for the reply
MANIFEST, CHANGES_FILE = "manifest_r4.json", "r4_changes.json"

def note(design, text):
    if (design, text) not in CHANGES:
        CHANGES.append((design, text))

def set_lot(w, d):
    nb.W = 8.0 * w
    nb.LOT_D = d
    nb.YSHIFT = -(d * 4.0 - 12.0)
    r3.LB = -12.0 + 8.0 * d
    r3.LIM = nb.W / 2 - .02
    nb.XMAP = None

# ------------------------------------------------------------------ JSON -> round-3 spec
def floor_of(b, datums):
    return max(i for i, z in enumerate(datums) if z <= b + .05) if b + .05 >= datums[0] else 0

def conv_opening(o, datums, side=None):
    k = o["kind"]
    b, t, w = o["bottom_m"], o["top_m"], o["width_m"]
    floor = o.get("floor_index", floor_of(b, datums))
    if k in ("door", "arched-door", "closed-arched-leaf"):
        kind = "shopdoor" if o.get("use") == "commercial" else "door"
        code = "D"
    elif k in ("display", "arched-display"):
        kind, code = "shop", "V"
    elif k == "french-door":
        kind, code = "french", "F"
    else:
        kind = "small" if (t - b < .5 or w < .5) else "pair" if w >= 1.5 else "sash"
        code = "W" if k == "sash" else "A"
    return dict(side=side, k=code, c=o["centre_m"], w=w, b=b, t=t, floor=floor, shutter=None, kind=kind,
                src=k, use=o.get("use"), xo=o.get("wall_x_override_m"), yo=o.get("wall_y_override_m"))

def mirror(prof, about):
    return prof + [(2 * about - a, z) for a, z in reversed(prof[:-1])]

def conv_roof(a, seg=None):
    r = seg or a["main"]["roof"]
    k = r["kind"]
    x0, x1, yf, yb = (seg or a["main"])["bounds_m"]
    e = (seg or {}).get("eave_m", a["main"]["eave_m"])
    mat = a["main"]["roof"]["material"]
    if k == "GX":
        ry = r["ridge_xy"][0][1]
        return dict(type="ridgeX", P=[(yf, e), (ry, r["ridge_z"]), (yb, e)], mat=mat)
    if k == "GY":
        rx = r["ridge_xy"][0][0]
        return dict(type="ridgeY", Q=[(x0, e), (rx, r["ridge_z"]), (x1, e)], mat=mat)
    if k == "H":
        return dict(type="hip", ridge=[tuple(p) for p in r["ridge_xy"]], rz=r["ridge_z"], mat=mat)
    if k == "F":
        return dict(type="flat", coping=r["coping_z"], mat=mat)
    if k in ("MG", "B"):
        if r.get("profile_axis", "Y") == "Y":
            return dict(type="ridgeX", P=mirror([tuple(p) for p in r["profile_front_to_ridge"]], r["mirror_about_y"]),
                        mat=mat, kind=k)
        return dict(type="ridgeY", Q=mirror([tuple(p) for p in r["profile_left_to_ridge"]], r["mirror_about_x"]),
                    mat=mat, kind=k)
    if k == "CLIP":                                       # street gable, both peaks clipped back and down
        xc = r["ridge_xy"][0][0]
        rz, drop = r["ridge_z"], r["clip_drop"]
        t = (rz - e) / (xc - x0)
        xa, xb, zc = xc - drop / t, xc + drop / t, rz - drop
        return dict(type="ridgeY", Q=[(x0, e), (xa, zc), (xb, zc), (x1, e)], mat=mat,
                    clip=dict(xa=xa, xb=xb, xc=xc, zc=zc, rz=rz, depth=r["clip_depth"]))
    if k == "paired-street-gables":                       # one W-profile roof: two street gables and a valley
        Q = []
        for sg in r["segments"]:
            sx0, sx1 = sg["bounds_m"][:2]
            Q += [(sx0, sg["eave_m"]), (sg["ridge_xy"][0][0], sg["ridge_z"])]
        Q.append((r["segments"][-1]["bounds_m"][1], r["segments"][-1]["eave_m"]))
        Q = [q for i, q in enumerate(Q) if i == 0 or abs(q[0] - Q[i - 1][0]) > 1e-6]
        parts = [[(sg["bounds_m"][0], sg["eave_m"]), (sg["ridge_xy"][0][0], sg["ridge_z"]), (sg["bounds_m"][1], sg["eave_m"])]
                 for sg in r["segments"]]
        return dict(type="ridgeY", Q=Q, mat=mat, parts=parts)
    if k == "paired-hips":
        vb = r.get("valley_bridge")
        return dict(type="multihip", mat=mat,
                    segments=[dict(x0=sg["bounds_m"][0], x1=sg["bounds_m"][1], rz=sg["ridge_z"],
                                   ridge=[tuple(p) for p in sg["ridge_xy"]]) for sg in r["segments"]],
                    bridge=(vb["bounds_m"][0], vb["bounds_m"][1], vb["deck_z"]) if vb else None)
    raise NotImplementedError(f"{a['design']}: roof kind {k}")

def to_spec(a):
    m = a["main"]
    S = dict(design=a["design"], zone=a["zone"], access=a["access"], walls=list(m["bounds_m"]),
             datums=list(m["floors_m"]), eave=m["eave_m"], facade=list(m["materials"]),
             cornice=(m["cornice"]["projection_m"], m["cornice"]["height_m"], m["cornice"]["brackets"],
                      m["cornice"]["material"]),
             door=a["door_material"], frame=a["frame_material"], chamfer=a.get("chamfer_m") or 0.0,
             dormers=None, roof_raw="", chimneys=[[*c["centre_xy"], *c["size_xy"], c["top_z"]] for c in a["chimneys"]])
    if m["roof"]["kind"] == "F":
        S["eave"] = m["roof"]["deck_z"]
    if m["roof"]["kind"] != "unequal-gable-bellcast":
        S["R"] = conv_roof(a)
    d = S["datums"]
    S["front"] = [conv_opening(o, d) for o in a["front"]]
    S["rear"] = [conv_opening(o, d) for o in a["rear"]]
    S["sides"] = [conv_opening(o, d, {"left": "L", "right": "R"}[o["side"]]) for o in a["side"]]
    if a.get("corner_door"):
        S["sides"].append(conv_opening(a["corner_door"], d, "C"))
    S["dormer_list"] = a["dormers"]
    S["roof_kind"] = m["roof"]["kind"]
    return S

# ------------------------------------------------------------------ shared pieces
def front_y(S): return Y(S["walls"][2])

def entries(h, S, a, skip=()):
    """stoop at every raised ground-floor street door, a 1 m walk from each to the street"""
    narrow = a["width_cells"] == 1
    hw = (1.4 if narrow else 1.7) / 2
    doors = sorted((o for o in S["front"] if o["k"] == "D" and o["floor"] == 0 and o["c"] not in skip
                    and o.get("src") != "closed-arched-leaf"), key=lambda o: o["c"])
    groups = []                                          # doors whose stoops would overlap share one stoop
    for o in doors:
        if groups and o["c"] - hw < groups[-1][-1]["c"] + hw and abs(o["b"] - groups[-1][-1]["b"]) < .02:
            groups[-1].append(o)
        else:
            groups.append([o])
    for g in groups:
        xa, xb = X(g[0]["c"]) - hw, X(g[-1]["c"]) + hw
        xa, xb = max(xa, -nb.W / 2 + .05), min(xb, nb.W / 2 - .05)
        y0 = r3.stoop(h, xa, xb, front_y(S), g[0]["b"]) if g[0]["b"] > .2 else front_y(S)
        for o in g:
            r3.walk_to(h, X(o["c"]), y0, 1.0)
    for o in S["sides"]:
        if o["side"] == "C" and o["k"] == "D":          # corner door: paved apron at the cut corner to the street
            c = S["chamfer"]
            x0, x1, yf, _ = S["walls"]
            xc = x0 + c / 2 if S["access"] == "LeftCorner" else x1 - c / 2
            nb.walk(h, X(xc) - .6, X(xc) + .6, Y(yf + c / 2))

def dormers(h, S, R):
    if not S["dormer_list"] or R["type"] != "ridgeX":
        return
    P = [(Y(y), z + r3.T) for y, z in R["P"]]
    i = max(range(len(P)), key=lambda i: P[i][1])
    prof = P[:i + 1]
    off = .48 if S["roof_kind"] == "MG" else 1.05
    trim = S["facade"][4]
    for dm in S["dormer_list"]:
        k = {"segmental": "S", "pediment": "P", "gable": "G"}.get(dm["kind"], "S")
        face = S["facade"][0] if k == "G" else ("Dressed" if trim == "Dressed" else "Cream")
        r3.dormer3(h, X(dm["x"]), dm["width"], prof, front_y(S) + off, k, R["mat"], R["mat"], face,
                   face_h=1.55, sash_z=(.15, 1.40), sash_in=.40)

def main_block(h, S, a):
    d = r3.build_spec(h, S)
    dormers(h, S, S["R"])
    return d

# ------------------------------------------------------------------ feature modules (pilots first)
def F_CrossGable(h, S, a):
    """low cross gable over a front porch: gable wall with its own attic sash at y2.38, porch on three posts"""
    f = a["feature"]
    m = h.body
    gx0, gx1 = f["gable_x"]
    yg, rz, bz = Y(f["front_y"]), f["ridge_z"], f["base_z"]
    xc = (gx0 + gx1) / 2
    yf = front_y(S)
    front_m, trim = S["facade"][0], "Cream"
    oh = .15
    Q = [(X(gx0) - oh, bz - oh * (rz - bz) / (xc - gx0)), (X(xc), rz), (X(gx1) + oh, bz - oh * (rz - bz) / (gx1 - xc))]
    yend = Y(9.4)                                         # dies into the main roof (hidden beyond here)
    r3.slab_y(m, Q, yg - .12, yend, S["R"]["mat"], trim)
    # gable triangle (z from the porch beam up), with the attic sash
    tri = Face((X(gx0), yg), (X(gx1), yg))
    region_top = [(gx1 - gx0, bz), (xc - gx0, rz), (0, bz)]
    _gable_wall(h, tri, bz, region_top, front_m, [Opening(xc - gx0, .80, 4.45, 5.60, "sash")])
    # beam, ceiling and the back face of the gable void
    m.box(X(gx0), X(gx1), yg - .02, yg + .18, bz - .28, bz, trim, bottom=True)
    m.polygon([(X(gx0), yg, bz - .28), (X(gx1), yg, bz - .28), (X(gx1), yf, bz - .28), (X(gx0), yf, bz - .28)], DOWN, trim)
    # porch deck, posts, steps
    px0, px1, py0, py1 = f["porch"]
    dz = f["porch_deck_z"]
    m.box(X(px0), X(px1), Y(py0), yf, 0, dz - .16, "Rubble", bottom=False)
    m.box(X(px0), X(px1), Y(py0), yf, dz - .16, dz, "Deck", bottom=False)
    for x in (gx0 + .1, xc, gx1 - .1):
        m.box(X(x) - .07, X(x) + .07, yg + .02, yg + .16, dz, bz - .28, "Cream", bottom=False)
    sx = X(px0 + 1.0)
    y0 = r3.stoop(h, sx - .55, sx + .55, Y(py0), dz, landing=.27, rails=False)
    r3.walk_to(h, sx, y0, 1.0)
    if h.lod < 2:
        r3.railing(h, sx + .6, Y(py0) + .06, X(px1) - .06, Y(py0) + .06, dz, .92, "Cream", .2)
    entries(h, S, a)

def _gable_wall(h, f, z0, top, mat, ops):
    """triangular gable wall on face f from z0 up to the outline top [(u, z)], with openings"""
    m = h.body
    region = [(0.0, z0), (f.length, z0)] + sorted([p for p in top if p[1] > z0 + 1e-6], key=lambda p: -p[0])
    cuts = sorted({z0, *(z for _, z in region), *(v for o in ops for v in (o.bottom, o.top))})
    for za, zb in zip(cuts, cuts[1:]):
        slab = nb.clip(nb.clip(region, 1, za, True), 1, zb, False)
        if len(slab) < 3 or nb.area2d(slab) < 1e-6:
            continue
        mid = (za + zb) / 2
        u, gaps = 0.0, []
        for o in sorted((o for o in ops if o.bottom < mid < o.top and h.lod < 2), key=lambda o: o.left):
            gaps.append((u, o.left)); u = o.right
        gaps.append((u, f.length))
        for ua, ub in gaps:
            piece = nb.clip(nb.clip(slab, 0, ua, True), 0, ub, False)
            if len(piece) >= 3 and nb.area2d(piece) > 1e-6:
                m.polygon([f.point(p, q) for p, q in piece], f.out, mat)
    for o in ops:
        if h.lod < 2:
            h.opening(f, o, mat)
        else:
            h.pane(f, o.left, o.right, o.bottom, o.top, .018)
    # back face (inside the roof void) so the gable reads closed from behind too
    m.polygon([f.point(p, q, -.16) for p, q in region], -f.out, mat)   # behind the sash glass (set .12 deep)

def F_InsetSide(h, S, a):
    """ground-floor side gallery under the upper floor: the right wall's ground storey moves in to x5.95"""
    f = a["feature"]
    m = h.body
    gx0, gx1, gy0, gy1 = f["bounds"]
    dz, z1 = f["deck_z"], S["datums"][1]
    side_m, base_m = S["facade"][1], S["facade"][3]
    xi = X(gx0)
    # inner wall with the gallery door (Y9.0) and the relocated side sash
    inner = Face((xi, Y(gy0)), (xi, Y(gy1)))                 # runs +y, faces +x
    ops = [Opening(9.0 - gy0, 1.0, dz, dz + 2.10, "door"), Opening(11.6 - gy0, .95, 1.30, 2.69, "sash")]
    bands = [(0, max(dz, .12), base_m), (max(dz, .12), 99, side_m)]
    r3.poly_wall(h, inner, [(inner.length, z1), (0, z1)], bands, ops)
    # cheeks at both ends of the notch, ceiling under the upper floor
    for y, out in ((Y(gy0), -1), (Y(gy1), 1)):
        cf = Face((X(gx1), y), (xi, y)) if out < 0 else Face((xi, y), (X(gx1), y))
        r3.poly_wall(h, cf, [(cf.length, z1), (0, z1)], bands, [])
    m.polygon([(xi, Y(gy0), z1), (X(gx1), Y(gy0), z1), (X(gx1), Y(gy1), z1), (xi, Y(gy1), z1)], DOWN, "Cream")
    # deck on a rubble base, posts, rail
    m.box(xi, X(gx1), Y(gy0), Y(gy1), 0, dz - .16, "Rubble", bottom=False)
    m.box(xi, X(gx1), Y(gy0), Y(gy1), dz - .16, dz, "Deck", bottom=False)
    for y in (7.95, 10.5, 13.05):
        m.box(X(7.4) - .07, X(7.4) + .07, Y(y) - .07, Y(y) + .07, dz, z1, "Cream", bottom=False)
    if h.lod < 2:
        r3.railing(h, X(7.4), Y(gy0) + .1, X(7.4), Y(gy1) - .1, dz, .92, "Cream", .2)
    entries(h, S, a)

def F_EndGable(h, S, a):
    entries(h, S, a)

def F_ShopMansard(h, S, a):
    r3.fascia(h, S, 3.0, 3.4)
    entries(h, S, a)

def F_CornerDormers(h, S, a):
    entries(h, S, a)

# ---- round 4, the other 34
def recess(h, S, x0, x1, y_back, z0, z1, ops=(), mat=None, floor_mat="Dressed", riser=False):
    """a recess in the front wall (lot coords): back wall at y_back with openings [(centre_x, w, b, t, kind)],
    closed cheeks, ceiling at z1 and floor at z0. The front wall needs a void opening over it (front_void)."""
    m = h.body
    yf, yb = front_y(S), Y(y_back)
    mat = mat or S["facade"][0]
    back = Face((X(x0), yb), (X(x1), yb))
    o2 = [Opening(c - x0, w, b, t, k) for c, w, b, t, k in ops]
    r3.poly_wall(h, back, [(back.length, z1), (0, z1)], [(0, 99, mat)], o2)
    for x, side in ((X(x0), 1), (X(x1), -1)):           # cheeks face into the recess
        cf = Face((x, yf), (x, yb)) if side > 0 else Face((x, yb), (x, yf))
        cf.quad(m, 0, cf.length, z0, z1, 0, mat)
    m.polygon([(X(x0), yf, z1), (X(x1), yf, z1), (X(x1), yb, z1), (X(x0), yb, z1)], DOWN, "Cream")
    m.polygon([(X(x0), yf, z0), (X(x1), yf, z0), (X(x1), yb, z0), (X(x0), yb, z0)], UP, floor_mat)
    if riser and z0 > .01:                               # recess cut from the ground: close the step under its floor
        m.polygon([(X(x0), yf, 0), (X(x1), yf, 0), (X(x1), yf, z0), (X(x0), yf, z0)], (0, -1, 0), S["facade"][3])

def front_void(S, x0, x1, z0, z1, drop=()):
    """cut the front wall over [x0, x1] x [z0, z1] and drop the listed front openings (by centre x, floor)"""
    S["front"] = [o for o in S["front"] if (round(o["c"], 3), o["floor"]) not in drop]
    S["front"].append(dict(side=None, k="A", c=(x0 + x1) / 2, w=x1 - x0, b=z0, t=z1, floor=None, shutter=None,
                           kind="void"))

def F_Recess(h, S, a):                                  # RecessedPorchRow: ground loggia, door at the back
    f = a["feature"]
    x0, x1, _, yb = f["bounds"]
    d0 = S["datums"][0]
    recess(h, S, x0, x1, yb, d0, f["ceiling"], [((x0 + x1) / 2, 1.0, d0, d0 + 2.10, "door")], riser=True)
    y0 = r3.stoop(h, X(x0) + .05, X(x1) - .05, front_y(S), d0, rails=False)
    r3.walk_to(h, X((x0 + x1) / 2), y0, 1.0)
    entries(h, S, a)

def F_UpperLoggia(h, S, a):                             # RightCornerLoggiaRow: inset balcony on the middle floor
    f = a["feature"]
    x0, x1, _, yb = f["bounds"]
    dz, cz = f["deck_z"], f["ceiling_z"]
    recess(h, S, x0, x1, yb, dz, cz, [(f["door_x"], 1.0, dz, dz + 2.10, "french")])
    if h.lod < 2:
        nb.railing(h, X(x0) + .05, Y(2.79), X(x1) - .05, Y(2.79), dz, .95, "Iron")
    entries(h, S, a)

def F_TurnedStoop(h, S, a):
    entries(h, S, a)

def F_LeftStair(h, S, a):                               # OxbowStairPlex: quarter-turn iron stair to the upper door
    f = a["feature"]
    (sx, sy), (tx, ty), (ex, ey) = f["plan"]
    path = r3.Path2([("line", (X(sx), Y(sy)), (X(tx), Y(ty))),
                     ("arc", (X(tx), Y(ey)), ey - ty, -math.pi / 2, -math.pi)])
    lx0, lx1, ly0, ly1 = f["landing"]
    z = f["upper_z"]
    r3.flight(h, path, 0.0, z - .12, 18, f["clear_width"])
    r3.landing(h, X(lx0), X(lx1), Y(ly0), Y(ly1) - .01, z)
    r3.walk_to(h, X(sx) + .4, Y(sy), 1.0)
    entries(h, S, a, skip=(f["upper_door_x"],))

def F_RightStair(h, S, a):                              # SideEntryPlex: straight flight east to a landing
    f = a["feature"]
    fx0, fx1, fy0, fy1 = f["flight"]
    lx0, lx1, ly0, ly1 = f["landing"]
    z = f["upper_z"]
    yc = Y((fy0 + fy1) / 2)
    r3.flight(h, r3.Path2([("line", (X(fx0), yc), (X(fx1), yc))]), 0.0, z - .12, 18, f["clear_width"])
    r3.landing(h, X(lx0), X(lx1), Y(ly0), Y(ly1) - .01, z)
    r3.shed(h, "x", X(5.75), X(7.18), Y(3.4), Y(2.48), 6.14, 6.0, "TinFlat")
    r3.walk_to(h, X(fx0) - .5, yc + .5, 1.0)
    entries(h, S, a, skip=(f["upper_door_x"],))

def F_GroundBay(h, S, a):
    f = a["feature"]
    r3.bay(h, X(f["centre"]), front_y(S), 0.0, f["cap_top"] - .16, S["datums"][0], mat=S["facade"][0])
    entries(h, S, a)

def F_ShopOriel(h, S, a):
    f = a["feature"]
    x0, x1, _, _ = f["bounds"]
    r3.bay(h, X((x0 + x1) / 2), front_y(S), f["floor_z"], f["cap_wall_z"] - .2, f["floor_z"], oriel=True,
           cap_face=f["cap_face_z"], cap_wall=f["cap_wall_z"], mat=S["facade"][0])
    entries(h, S, a)

def F_Oriel(h, S, a):                                   # StoneOrielHouse
    f = a["feature"]
    x0, x1, _, _ = f["bounds"]
    r3.bay(h, X((x0 + x1) / 2), front_y(S), f["base_z"] + .27, f["cap_wall_z"] - .2, f["floor_z"], oriel=True,
           cap_face=f["cap_front_z"], cap_wall=f["cap_wall_z"], mat=S["facade"][0])
    entries(h, S, a)

def F_ShopGallery(h, S, a):                             # MainGalleryCafe: iron shop gallery on the street edge
    f = a["feature"]
    x0, x1, y0, _ = f["bounds"]
    r3.gallery(h, X(x0), X(x1), front_y(S), Y(y0), [f["deck_z"]], roof=(f["roof_wall_z"], f["roof_face_z"], "TinFlat"),
               post_mat="Iron", base=None)
    entries(h, S, a)

def F_ShopArches(h, S, a):
    r3.fascia(h, S, 3.15, 3.5)
    entries(h, S, a)

def F_CornerLantern(h, S, a):
    f = a["feature"]
    cx, cy = f["centre"]
    r3.lantern(h, X(cx), Y(cy), f["width"] / 2, f["base_z"], f["eave_z"], f["top_z"])
    entries(h, S, a)

def F_CornerHood(h, S, a):
    f = a["feature"]
    xa, xb = f["front_span"]
    yf = front_y(S)
    r3.shed(h, "x", X(xa), X(xb), yf, yf - f["projection"], f["z_wall"], f["z_face"], f["material"])
    entries(h, S, a)

def F_CornerIronGallery(h, S, a):                       # LeftCornerMainIronwork: .85 m iron balcony
    f = a["feature"]
    x0, x1, y0, y1 = f["bounds"]
    r3.balcony(h, [(X(x0), Y(y1)), (X(x1), Y(y1))], f["deck_z"], y1 - y0)
    entries(h, S, a)

def F_WideVeranda(h, S, a):                             # VerandaCourtHouse
    f = a["feature"]
    x0, x1, y0, _ = f["bounds"]
    door = next(o for o in S["front"] if o["k"] == "D")
    xd = X(door["c"])
    g = (xd - .575, xd + .575)
    posts = [X(x0) + .07 + (x1 - x0 - .14) * i / 7 for i in range(8)]
    posts = sorted([p for p in posts if not g[0] - .3 < p < g[1] + .3] + [g[0] - .08, g[1] + .08])
    y_st = r3.gallery(h, X(x0), X(x1), front_y(S), Y(y0), [f["deck_z"]],
                      roof=(f["roof_wall_z"], f["roof_face_z"], a["main"]["roof"]["material"]), posts=posts,
                      gap=g, stairs_x=xd)
    r3.walk_to(h, xd, y_st, 1.0)
    entries(h, S, a, skip=(door["c"],))

def F_HalfPorch(h, S, a):                               # HalfPorchHouse: posts at the ends and either side of the steps
    f = a["feature"]
    x0, x1, y0, _ = f["bounds"]
    door = next(o for o in S["front"] if o["k"] == "D")
    xd = X(door["c"])
    y_st = r3.gallery(h, X(x0), X(x1), front_y(S), Y(y0), [f["deck_z"]],
                      roof=(f["roof_wall_z"], f["roof_face_z"], a["main"]["roof"]["material"]),
                      posts=[X(.68), xd - .62, xd + .62, X(3.52)], gap=(xd - .55, xd + .55), stairs_x=xd)
    r3.walk_to(h, xd, y_st, 1.0)
    entries(h, S, a, skip=(door["c"],))

def F_EndChimney(h, S, a):                              # GableWallCottage: stone breast up the front gable
    f = a["feature"]
    x0, x1, y0, y1 = f["bounds"]
    h.body.box(X(x0), X(x1), Y(y0), Y(y1) + .02, f["z_bottom"], f["z_top"], "Dressed", bottom=True)
    entries(h, S, a)

def F_LongDormer(h, S, a):                              # BroadDormerCottage: one broad dormer, three sashes
    f = a["feature"]
    x0, x1, y0, _ = f["bounds"]
    R = S["R"]
    P = [(Y(y), z + r3.T) for y, z in R["P"]]
    i = max(range(len(P)), key=lambda i: P[i][1])
    xc = (x0 + x1) / 2
    r3.dormer3(h, X(xc), x1 - x0, P[:i + 1], Y(y0), "S", R["mat"], R["mat"], "Cream",
               sashes=[(x - xc, .94) for x in (3.1, 4.55, 6.0)], face_h=f["face_z_top"] - f["face_z_bottom"])
    entries(h, S, a)

def F_PavilionBay(h, S, a):                             # FrontPavilionHouse: two-storey square pavilion, hipped cap
    f = a["feature"]
    x0, x1, y0, y1 = f["bounds"]
    m = h.body
    e = f["eave"]
    plan = [(X(x0), Y(y1)), (X(x0), Y(y0)), (X(x1), Y(y0)), (X(x1), Y(y1))]
    mat = S["facade"][0]
    for i, fc in enumerate(edges(plan)[:3]):             # left cheek, front, right cheek
        w = .95 if i == 1 else .42
        ops = [Opening(fc.length / 2, w, d + .86, d + 2.25, "sash") for d in S["datums"] if fc.length > w + .2]
        fc.wall(h, 0.0, e, ops, mat)
    oh = .2
    rect = (X(x0) - oh, X(x1) + oh, Y(y0) - oh, Y(y1))
    m.polygon([(rect[0], rect[2], e), (rect[1], rect[2], e), (rect[1], rect[3], e), (rect[0], rect[3], e)], DOWN, r3.SOFFIT)
    xc = X((x0 + x1) / 2)
    r3.hip_faces(m, rect, e + r3.T, (xc, Y(y1) - .3), (xc, Y(y1)), f["cap_top"], "Tin")
    entries(h, S, a)

FEATURES = {k[2:]: v for k, v in globals().items() if k.startswith("F_")}

# per-design fixes to the spec before building (each one is reported)
def prep_InsetGalleryHouse(S, a):
    # the notch Y7.8-13.2 swallows two ground-floor right sashes: one moves onto the recessed wall (built by the
    # feature at Y11.6), the one at Y13.4 straddled the notch end and moves to Y14.4 on the outer wall
    keep = []
    for o in S["sides"]:
        if o["side"] == "R" and o["floor"] == 0:
            if o.get("xo"):
                note(a["design"], "right ground sash at Y7.9 (on the recessed wall) moved to Y11.6: at Y7.9 it "
                     "straddled the notch end at Y7.8, and the gallery door at Y9.0 sits beside it")
                continue
            if abs(o["c"] - 13.4) < .01:
                o["c"] = 14.4
                note(a["design"], "right ground sash at Y13.4 moved to Y14.4: it straddled the notch end at Y13.2")
        keep.append(o)
    S["sides"] = keep
    # the ground storey of the right wall over the notch is a hole only (the feature builds the recessed wall)
    gx0, gx1, gy0, gy1 = a["feature"]["bounds"]
    S["sides"].append(dict(side="R", k="A", c=(gy0 + gy1) / 2, w=gy1 - gy0, b=0.0, t=S["datums"][1], floor=0,
                           shutter=None, kind="void"))

def prep_LeftCornerGableEndRow(S, a):
    S["sides"].append(dict(side="L", k="A", c=10.375, w=.92, b=7.02, t=8.28, floor=None, shutter=None, kind="sash"))

def prep_RightCornerMainBooks(S, a):
    for o in S["front"]:
        if o["kind"] == "sash" and o["floor"] >= 1:
            o["shutter"] = "GreyBlue"

def prep_RightCornerFirewallRow(S, a):
    S["firewall"] = a["feature"]["raise_above_roof"]
    S["sides"].append(dict(side="R", k="A", c=10.5, w=.86, b=7.05, t=8.25, floor=None, shutter=None, kind="sash"))

def prep_PairedDormerRow(S, a):
    S["dormer_list"] = a["feature"]["items"]

def prep_TinBellcastRow(S, a):
    S["dormer_list"] = a["feature"]["items"]

def prep_OxbowStairPlex(S, a):
    S["dormer_list"] = a["feature"].get("dormers") or S["dormer_list"]

def prep_RecessedPorchRow(S, a):
    x0, x1, _, _ = a["feature"]["bounds"]
    front_void(S, x0, x1, 0.0, a["feature"]["ceiling"], drop=((1.45, 0),))

def prep_RightCornerLoggiaRow(S, a):
    f = a["feature"]
    x0, x1, _, _ = f["bounds"]
    front_void(S, x0, x1, f["deck_z"], f["ceiling_z"], drop=((6.05, 1), (5.9, 1)))

def prep_SingleBayRenderRow(S, a):
    S["front"] = [o for o in S["front"] if not (abs(o["c"] - 2.65) < .01 and o["floor"] == 0)]

def _drop_in(S, x0, x1, floor=None):
    S["front"] = [o for o in S["front"] if not (x0 < o["c"] < x1 and (floor is None or o["floor"] == floor))]

def prep_MainBayGrocer(S, a):
    _drop_in(S, *a["feature"]["bounds"][:2], 1)

def prep_StoneOrielHouse(S, a):
    _drop_in(S, *a["feature"]["bounds"][:2], 1)

def prep_FrontPavilionHouse(S, a):
    _drop_in(S, *a["feature"]["bounds"][:2])

PREP = {k[5:]: v for k, v in globals().items() if k.startswith("prep_")}

# ------------------------------------------------------------------ two masses side by side (AsymmetricGableDouble)
def wide_twin(h, S, a):
    segs = copy.deepcopy(a["main"]["roof"]["segments"])
    _, _, yf, yb = a["main"]["bounds_m"]
    for seg, span, wh in zip(segs, (a["feature"]["left"], a["feature"]["right"]), a["main"]["wall_height_segments"]):
        seg.setdefault("bounds_m", [span[0], span[1], yf, yb])   # the bellcast half only gives its X profile
        seg.setdefault("eave_m", wh["eave"])
    details = []
    for seg in segs:
        x0, x1, yf, yb = seg["bounds_m"]
        sub = copy.deepcopy(S)
        sub["walls"] = [x0, x1, yf, yb]
        sub["eave"] = seg["eave_m"]
        sub["R"] = conv_roof(a, seg)
        sub["front"] = [o for o in S["front"] if x0 <= o["c"] <= x1]
        sub["rear"] = []
        for o in S["rear"]:
            if x0 <= o["c"] <= x1:
                if o["c"] + o["w"] / 2 > x1 - .1:
                    old = o["c"]; o = dict(o, c=x1 - o["w"] / 2 - .35)
                    note(a["design"], f"rear upper sash at X{old} moved to X{o['c']:.2f}: it crossed the step "
                         f"from the tall left mass to the low right roof at X{x1}")
                sub["rear"].append(o)
        sub["sides"] = [o for o in S["sides"] if (o["side"] == "L") == (x0 < 1)]
        if x0 > 1:                                         # the low mass has one storey: drop upper side sashes
            sub["sides"] = [o for o in sub["sides"] if o["t"] < seg["eave_m"] - .2]
            sub["datums"] = S["datums"][:1]
        sub["chimneys"] = [c for c in S["chimneys"] if x0 <= c[0] <= x1]
        details.append(r3.build_spec(h, sub))
    return {"roof_outline_m2": sum(d["roof_outline_m2"] for d in details),
            "roof_check_z": min(d["roof_check_z"] for d in details), "party_sides": [], "access": S["access"]}

MAINS = {"unequal-side-by-side-masses": wide_twin}

# ------------------------------------------------------------------ rear parts and court (GPT's plan, as given)
WALL_H = {"L": 1.45, "R": 1.85, "N": 2.0, "C": 2.0}

def rear(h, S, a, seed):
    m, lod = h.body, h.lod
    LB, LIM = r3.LB, r3.LIM
    parts = a["parts"]
    plain = lod == 1
    built = []
    for i, p in enumerate(parts):
        x0, x1, y0, y1 = p["bounds_m"]
        bx0, bx1 = max(X(x0), -LIM), min(X(x1), LIM)
        by0, by1 = Y(y0), min(Y(y1), LB - .03)
        att = p["join"] == "attached"
        nxt = parts[i + 1] if i + 1 < len(parts) else None
        e, top = p["eave_m"], p["roof_top_m"]
        rise = max(.05, top - r3.T - e)
        roof = {"flat": "flat", "shed": "shedB", "gableY": "gableY", "gableX": "gableX"}[p["roof"]]
        span = {"gableY": (bx1 - bx0) / 2, "gableX": (by1 - by0) / 2, "shedB": by1 - by0}.get(roof, 1)
        pitch = math.degrees(math.atan(rise / max(span, .5)))
        wins = []
        lot_l, lot_r = -nb.W / 2, nb.W / 2
        if bx0 > lot_l + .15 or a["group"] == "L":
            wins.append("left")
        if bx1 < lot_r - .15 or a["group"] == "L":
            wins.append("right")
        if nb.LITE >= 4 and "left" in wins and "right" in wins:   # over budget: one windowed side on long rear wings
            wins.remove("right")
        end_open = not (nxt and nxt["join"] == "attached")
        if att:
            door = "rear" if end_open else None
            if end_open:
                wins.append("rear")
            datum, dw = (p.get("floors_m") or S["datums"])[0], p["openings"].get("door_width_m", .94)
            base = S["facade"][3]
        else:
            door, datum, dw, base = "rear", .15, p["openings"].get("door_width_m", 2.1), "Rubble"
            wins.append("front")
        if lod == 2:
            if r3.tris(m) > 470:
                break
            m.box(bx0, bx1, by0, by1, 0, top - .05, p["wall_material"],
                  top="TinFlat" if roof in ("flat", "shedB") else p["roof_material"], bottom=False)
        else:
            r3.back_building(h, bx0, bx1, by0, by1, e, roof, p["wall_material"], base, p["roof_material"],
                             wins=tuple(wins), door=door, attached=att, storeys=p["storeys"], datum=datum,
                             pitch=pitch, door_w=dw, plain=plain)
        built.append(dict(x0=bx0, x1=bx1, y0=by0, y1=by1, att=att))
    if lod == 2:
        return
    # court: paving next to the back door (GPT's fraction), one path to the lane building, the rest stays green
    c = a["court"]
    cx0, cx1, cy0, cy1 = X(c["bounds_m"][0]), X(c["bounds_m"][1]), Y(c["bounds_m"][2]), Y(c["bounds_m"][3])
    depth = (cy1 - cy0) * c["paving_fraction"]
    if a["group"] == "L":
        depth = min(depth, (cy1 - cy0) * .55)
    m.box(cx0, cx1, cy0, cy0 + depth, 0, .04, "Paving", bottom=False)
    lane = next((b for b in built if not b["att"] and b["y1"] >= LB - 1.0), None)
    if lane and cy1 - (cy0 + depth) > .2:
        xc = (lane["x0"] + lane["x1"]) / 2
        m.box(xc - .5, xc + .5, cy0 + depth, cy1, 0, .04, "Paving", bottom=False)
    # side wall on the left line (the neighbour supplies the right), lane wall beside the lane building / gated
    masonry = a["group"] != "L"
    th = .18 if masonry else .06
    wh = WALL_H[a["group"]]
    wm = S["facade"][2] if masonry else "Deck"
    r3.wall_run(h, -LIM, -LIM + th, cy0, LB - .02, wh, wm, masonry)
    if lane:
        xs = [(-LIM + th, lane["x0"] - .02), (lane["x1"] + .02, LIM)]
    else:
        gx = random.Random(seed).uniform(-nb.W / 2 + 1.5, nb.W / 2 - 1.5)
        xs = [(-LIM + th, gx - .55), (gx + .55, LIM)]
    for xa, xb in xs:
        if xb - xa > .3:
            r3.wall_run(h, xa, xb, LB - .02 - th, LB - .02, wh, wm, masonry)

# ------------------------------------------------------------------ bake
# ------------------------------------------------------------------ B/C New Orleans dressing (GPT round 5 plan)
DRESS_SRC = Path(r"C:\Users\<you>\CS2Planner\NewFrance\GPT_INBOX\2026-11-05_round5\round4-dressing.json")
DRESS = {}

def shutter_key(want):
    """atlas key that the colourway remap turns into the wanted shutter colour"""
    for src, dst in nb.REMAP.items():
        if dst == want:
            return src
    return want

def dress(S, a, k):
    """B: French doors on individual balconies, C: one continuous balcony; both get full-height louvred shutters
    wherever both leaves fit. Features (stairs, bays, notches, loggias) keep their clearances."""
    if k == 0 or not DRESS:
        return
    e = DRESS.get(a["design"])
    if not e:
        return
    v = "BC"[k - 1]
    pal = e["shutters"]["palette"]
    colour = shutter_key(pal[(zlib.crc32(a["design"].encode()) + k) % len(pal)])
    plan = e[v]
    S["balconies"] = []
    ground = e["mode"] == "ground-shutters-and-existing-porch"
    for fd in plan.get("french_doors", []):
        hit = [o for o in S["front"] if abs(o["c"] - fd["centre_x"]) < .05 and o["floor"] == 1 and o["kind"] == "sash"]
        for o in hit:
            o.update(k="F", kind="french", b=fd["bottom_m"], t=fd["top_m"], w=fd["width_m"])
        if not hit:
            note(a["design"], f"{v}: no first-upper sash at X{fd['centre_x']} to turn into a French door, skipped")
    for b in plan.get("individual_balconies", []):
        S["balconies"].append((b["bounds_m"], b["deck_z"]))
    if plan.get("continuous_balcony"):
        b = plan["continuous_balcony"]
        S["balconies"].append((b["bounds_m"], b["deck_z"]))
    for o in S["front"] + S["sides"]:
        if o["kind"] in ("sash", "french", "pair") and (o["floor"] or 0) >= (0 if ground else 1):
            if o["kind"] == "pair" and o["w"] > 1.9:
                continue
            o["shutter"] = colour

def dress_build(h, S, a):
    yf = front_y(S)
    for (x0, x1, y0, y1), z in S.get("balconies", []):
        x0, x1 = max(x0, S["walls"][0] + .05), min(x1, S["walls"][1] - .05)
        r3.balcony(h, [(X(x0), yf), (X(x1), yf)], z, max(.6, yf - Y(y0)))

def make_recipe(a, k):
    S = to_spec(a)
    if a["design"] in PREP:
        PREP[a["design"]](S, a)
    dress(S, a, k)
    seed = zlib.crc32(f"{a['design']}/{k}".encode())
    feat = FEATURES.get(a["module"])
    build = MAINS.get(a["feature"]["kind"], main_block)
    def recipe(h):
        d = build(h, S, a)
        if feat:
            feat(h, S, a)
        else:
            entries(h, S, a)
        dress_build(h, S, a)
        rear(h, S, a, seed)
        return d
    return recipe

def owner_textures():
    src = nb.HERE / "out" / "NA_NewFrancePlex_L1_1x6"
    dst = OUT / OWNER
    dst.mkdir(parents=True, exist_ok=True)
    for f in src.glob("*.png"):
        shutil.copyfile(f, dst / f.name.replace("NA_NewFrancePlex_L1_1x6", OWNER))

def run(only=None, variants=3):
    data = json.loads(SRC.read_text(encoding="utf-8"))
    if DRESS_SRC.exists():
        DRESS.update({e["design"]: e for e in json.loads(DRESS_SRC.read_text(encoding="utf-8"))["designs"]})
    nb.OUT, nb.OWNER = OUT, OWNER
    owner_textures()
    manifest, total = {}, 0
    for a in data["assets"]:
        if only and a["design"] not in only:
            continue
        for k in range(variants):
            set_lot(a["width_cells"], a["depth_cells"])
            name = f"NA_NewFrance{a['design']}{'' if k == 0 else 'BC'[k - 1]}_L1_{a['width_cells']}x{a['depth_cells']}"
            nb.REMAP.clear(); nb.REMAP.update(r3.variant_map(k))
            recipe = make_recipe(a, k)
            folder = OUT / name
            folder.mkdir(parents=True, exist_ok=True)
            rec = {"design": a["design"], "variant": k, "zone": a["zone"], "lot": [a["width_cells"], a["depth_cells"]],
                   "households": a["households"], "commercial_tenancies": a["commercial_tenancies"], "meshes": {}}
            details = None
            for lod, suffix in enumerate(("", "_LOD1", "_LOD2")):
                nb.clear_objects()
                try:
                    for lite in (0, 1, 2, 3, 4, 5, 6):                # over budget: lighter iron lace and plainer shutters
                        nb.LITE = lite
                        h = House(lod)
                        details = recipe(h)
                        if r3.tris(h.body) <= (11900, 3950, 500)[lod]:
                            break
                    if lite:
                        rec.setdefault("lite", {})[str(lod)] = lite
                    nb.LITE = 0
                except Exception as err:
                    nb.LITE = 0
                    import traceback; traceback.print_exc()
                    print(f"FAILED {name}: build error {err!r}", flush=True)
                    rec["ok"] = False; rec["error"] = repr(err); details = None
                    break
                if lod == 0:
                    rec.update(details); rec["entrances_blender_m"] = [[x, round(y + nb.YSHIFT, 4), z] for x, y, z in h.doors]
                for mesh, sfx in ((h.body, suffix), (h.windows, suffix + "_Win")):
                    tag = name + sfx
                    old = nb.bpy.data.materials.get(tag)
                    if old:
                        nb.bpy.data.materials.remove(old)
                    ob = mesh.object(tag, None if sfx.endswith("_Win") else nb.bpy.data.materials.new(tag))
                    nb.export_fbx(ob, folder / (tag + ".fbx"))
            if details is None:
                manifest[name] = rec; total += 1
                continue
            if name != OWNER:
                share = {f"{name}{l}_{kind}.png": f"../{OWNER}/{OWNER}{l}_{kind}.png"
                         for l in ("", "_LOD1", "_LOD2") for kind in nb.MAPS}
                (folder / "settings.json").write_text(json.dumps({"sharedAssets": share}, indent=2), encoding="utf-8")
            try:
                for path in sorted(folder.glob("*.fbx")):
                    rec["meshes"][path.stem.removeprefix(name) or "Main"] = nb.validate_export(
                        path, (nb.W, 8 * nb.LOT_D), details, path.stem.endswith("_Win"))
                c = rec["meshes"]
                assert c["Main"]["triangles"] > c["_LOD1"]["triangles"] >= c["_LOD2"]["triangles"], name
                rec["ok"] = True
                print(f"VERIFIED {name} {c['Main']['triangles']}/{c['_LOD1']['triangles']}/{c['_LOD2']['triangles']}", flush=True)
                if c["Main"]["triangles"] > 12000 or c["_LOD1"]["triangles"] > 4000:
                    print(f"OVERBUDGET {name}", flush=True)
            except AssertionError as err:
                rec["ok"] = False; rec["error"] = str(err)
                print(f"FAILED {name}: {err}", flush=True)
            manifest[name] = rec
            total += 1
    nb.REMAP.clear(); set_lot(1, 6)
    mf = nb.HERE / "reports" / MANIFEST
    if only and mf.exists():
        manifest = {**json.loads(mf.read_text(encoding="utf-8")), **manifest}
    mf.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    (nb.HERE / "reports" / CHANGES_FILE).write_text(json.dumps(CHANGES, indent=1), encoding="utf-8")
    for d, t in CHANGES:
        print(f"CHANGE {d}: {t}", flush=True)
    bad = [n for n, r in manifest.items() if not r["ok"]]
    print(f"R4 DONE {total} buildings, {len(bad)} failed", flush=True)

if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    a_only = "--a-only" in argv
    names = {v for v in argv if not v.startswith("--")}
    if names == {"PILOTS"}:
        names = set(PILOTS)
    run(names or None, 1 if a_only else 3)
