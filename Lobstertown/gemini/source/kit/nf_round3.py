"""New France round 3: bakes GPT's 32 round-3 specs (read straight from the spec sheets in ../gpt_round3, with
Claude's review revisions R1-R5 applied) plus the 5 pilots, each in three colour versions (A = as specced, B, C).

Generic part: a parser for GPT's spec blocks and one builder that makes walls (with gable/mansard ends), roof slab,
cornice, dormers, chimneys, walks from them. Per-design features (stairs, galleries, bays, arches...) are in FEATURES.
Run: blender -b --factory-startup -P nf_round3.py [-- Design ...]
"""
import json, math, re, sys, random, zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nf_build as nb
import copy
from nf_build import (Mesh, Face, Opening, House, edges, rectangle, extrude, bar, offset_plan, prism, profile_z,
                      profile_y, chimney, walk, railing, iron_stair, X, Y, UP, DOWN, clip, area2d,
                      cornice_profile, iron_post, iron_frieze, lace_ring, dquad)

SPECS = Path(__file__).resolve().parent.parent / "gpt_round3"
T = .12                     # roof slab thickness
SOFFIT = "Cream"

# ------------------------------------------------------------------ spec parser
def nums(s): return [float(v) for v in re.findall(r"-?\d*\.?\d+", s)]

def parse_openings(text, datums):
    out = []
    if text.strip() in ("", "blank"):
        return out
    for tok in [t.strip() for t in text.split("·") if t.strip()]:
        parts = tok.split()
        side = None
        if parts[0] in ("L", "R", "C") and len(parts) > 1 and parts[1] in "DWAV":
            side, parts = parts[0], parts[1:]
        k = parts[0]
        shutter = parts[-1] if parts[-1][0].isalpha() and len(parts) > 1 and parts[-1] not in "DWAV" else None
        vals = parts[1:-1] if shutter else parts[1:]
        c, w = float(vals[0]), float(vals[1])
        if k == "D":
            for f in vals[2].split(","):
                z = datums[int(f)]
                out.append(dict(side=side, k="D", c=c, w=w, b=z, t=z + 2.10, floor=int(f), shutter=shutter))
        elif k == "W":
            for f in vals[2].split(","):
                z = datums[int(f)]
                out.append(dict(side=side, k="W", c=c, w=w, b=z + .88, t=z + 2.26, floor=int(f), shutter=shutter))
        else:
            out.append(dict(side=side, k=k, c=c, w=w, b=float(vals[2]), t=float(vals[3]), floor=None, shutter=shutter))
    return out

def parse_block(block):
    S = {}
    g = lambda pat: re.search(pat, block)
    S["name"] = block.strip().splitlines()[0].strip()
    S["design"] = re.match(r"NA_NewFrance(\w+?)_L1_1x3", S["name"]).group(1)
    S["zone"] = g(r"zone: (Napoleon [A-Za-z ]+?)\s{2,}").group(1).strip()
    S["access"] = g(r"access: (\w+)").group(1)
    m = g(r"walls: X ([\d.]+)–([\d.]+), Y ([\d.]+)–([\d.]+)")
    S["walls"] = [float(v) for v in m.groups()]
    S["datums"] = nums(g(r"floor datums: ([\d. /]+)").group(1))
    S["eave"] = float(g(r"eave or flat deck: z([\d.]+)").group(1))
    roof = g(r"roof: (.+)").group(1).strip()
    S["roof_raw"] = roof
    S["roof_mat"] = roof.split("·")[-1].split()[0]
    S["facade"] = [v.strip() for v in g(r"facade: ([^(]+)\(").group(1).split("/")]
    m = g(r"cornice: ([\d.]+) m projection × ([\d.]+) m height\s+brackets: (\w+)\s+material: (\w+)")
    S["cornice"] = (float(m.group(1)), float(m.group(2)), m.group(3) == "yes", m.group(4))
    for key in ("front", "rear"):
        S[key] = parse_openings(g(rf"\n{key}: (.+)").group(1), S["datums"])
    S["sides"] = parse_openings(g(r"exposed sides and chamfer: (.+)").group(1), S["datums"])
    d = g(r"dormers: (.+)").group(1).strip()
    S["dormers"] = None if d == "none" else (d.split()[0], [float(v) for v in d.split()[1].split(",")], float(d.split()[2]))
    S["features"] = g(r"features: (.+)").group(1)
    ch = g(r"chimneys \(x y width depth top\): (.+)").group(1)
    S["chimneys"] = [nums(c) for c in ch.split("·")]
    m = g(r"door / frame: (\w+) / (\w+)")
    S["door"], S["frame"] = m.group(1), m.group(2)
    return S

def load_specs():
    specs = {}
    for f in ("MEDIUM-ROWS.md", "LOW-HOMES.md", "COMMERCIAL.md"):
        for block in re.findall(r"```text\n(.*?)```", (SPECS / f).read_text(encoding="utf-8"), re.S):
            S = parse_block(block)
            specs[S["design"]] = S
    return specs

def parse_roof(S):
    r, x0, x1, yf, yb = S["roof_raw"], *S["walls"]
    e = S["eave"]
    R = {"mat": S["roof_mat"]}
    pts = [tuple(map(float, p)) for p in re.findall(r"\(([\d.]+), ([\d.]+)\)", r)]
    if r.startswith("Side gable"):
        z, y = map(float, re.search(r"ridge z([\d.]+) at y([\d.]+)", r).groups())
        R.update(type="ridgeX", P=[(yf, e), (y, z), (yb, e)])
    elif r.startswith(("Gable-ended mansard", "Bellcast")):
        ry = float(re.search(r"mirrored about ridge y([\d.]+)", r).group(1))
        front = pts
        R.update(type="ridgeX", P=front + [(2 * ry - y, z) for y, z in reversed(front[:-1])])
    elif r.startswith("Saltbox"):
        z, y = map(float, re.search(r"ridge z([\d.]+) at y([\d.]+)", r).groups())
        rz = float(re.search(r"rear eave z([\d.]+)", r).group(1))
        R.update(type="ridgeX", P=[(yf, e), (y, z), (yb, rz)])
    elif r.startswith("Street gable"):
        z, x = map(float, re.search(r"ridge z([\d.]+) at x([\d.]+)", r).groups())
        R.update(type="ridgeY", Q=[(x0, e), (x, z), (x1, e)])
    elif r.startswith("Equal-pitch hip"):
        z = float(re.search(r"ridge z([\d.]+)", r).group(1))
        R.update(type="hip", ridge=(pts[0], pts[1]), rz=z)
    elif r.startswith("Four-sided mansard"):
        inset = float(re.search(r"short-end break set in ([\d.]+) m", r).group(1))
        xa, xb, rz = map(float, re.search(r"ridge x([\d.]+)–([\d.]+) at z([\d.]+)", r).groups())
        R.update(type="mansard4", front=pts, inset=inset, ridge=((xa, pts[-1][0]), (xb, pts[-1][0])), rz=rz)
    elif r.startswith("Flat"):
        cz = float(re.search(r"coping at z([\d.]+)", r).group(1))
        R.update(type="flat", coping=cz)
    else:
        raise ValueError(r)
    return R

# ------------------------------------------------------------------ revisions from CLAUDE_REVIEW_R3
def revise(specs):
    d = specs["BellcastDouble"]                                                     # R1 real bellcast
    d["roof_raw"] = "Bellcast · Y/Z front profile (3.25, 6.12) → (4.47, 6.47) → (10.03, 10.08) mirrored about ridge y10.03 · Tin"
    d["chimneys"] = [[1.16, 10.7, .53, .66, 10.90]]
    # R2 shotgun posts, R5 triplex rear stair: in FEATURES. R3 dormer sash: in dormer3. R4: setup script.
    return specs

# ------------------------------------------------------------------ walls with any convex-ish top outline
def drop_collinear(poly, eps=1e-6):
    """remove vertices lying on the line through their neighbours (clipping a W-shaped wall leaves a
    back-tracking edge along the cut line, which would triangulate into a spurious flap)"""
    pts = list(poly)
    changed = True
    while changed and len(pts) > 3:
        changed = False
        for i in range(len(pts)):
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % len(pts)]
            if abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) < eps:
                pts.pop(i); changed = True
                break
    return pts

def poly_wall(h, f, top, bands, openings, arches=()):
    """wall on face f: from z=0 up to the outline top [(u, z)] (u from 0 to f.length), material bands
    [(z0, z1, mat)], rectangular holes for openings (Opening objects, built with h.opening) and arches"""
    m, L = h.body, f.length
    region = [(0.0, 0.0), (L, 0.0)] + [p for p in sorted(top, key=lambda p: -p[0])]
    tsorted = sorted(top, key=lambda p: p[0])
    holes = list(openings) + list(arches)
    cuts = {0.0, max(z for _, z in region)} | {z for _, z in region} | {b[0] for b in bands} | {b[1] for b in bands}
    if h.lod < 2:
        cuts |= {o.bottom for o in holes} | {o.top for o in holes}
    cuts = sorted(c for c in cuts if c >= 0)
    def band(z):
        for z0, z1, mat in bands:
            if z0 - 1e-6 <= z <= z1 + 1e-6:
                return mat
        return bands[-1][2]
    for z0, z1 in zip(cuts, cuts[1:]):
        if z1 - z0 < 1e-5:
            continue
        slab = clip(clip(region, 1, z0, True), 1, z1, False)
        if len(slab) < 3 or area2d(slab) < 1e-6:
            continue
        mid = (z0 + z1) / 2
        gaps, u = [], 0.0
        if h.lod < 2:
            for o in sorted((o for o in holes if o.bottom < mid < o.top), key=lambda o: o.left):
                gaps.append((u, o.left)); u = o.right
        gaps.append((u, L))
        valleys = sorted(pu for i, (pu, pz) in enumerate(tsorted[1:-1], 1)
                         if pz < tsorted[i - 1][1] - 1e-6 and pz < tsorted[i + 1][1] - 1e-6 and pz < z1 - 1e-6)
        if valleys:                                       # W-shaped tops: split at each valley so pieces stay convex
            split = []
            for ua, ub in gaps:
                cs = [ua] + [v for v in valleys if ua < v < ub] + [ub]
                split += list(zip(cs, cs[1:]))
            gaps = split
        for ua, ub in gaps:
            if ub - ua < 1e-5:
                continue
            piece = drop_collinear(clip(clip(slab, 0, ua, True), 0, ub, False))
            if len(piece) >= 3 and area2d(piece) > 1e-6:
                m.polygon([f.point(a, b) for a, b in piece], f.out, band(mid))
    for o in openings:
        h.opening(f, o, band((o.bottom + o.top) / 2))
    for o in arches:
        arch(h, f, o, band((o.bottom + o.top) / 2))

def arch(h, f, o, reveal):
    """segmental-arched opening: spandrels, arched reveal, recessed leaf or glass, stone archivolt"""
    m = h.body
    a, b, sill, spring, crown = o.left, o.right, o.bottom, o.spring, o.top
    c, half = o.center, o.width / 2
    s = crown - spring
    r = (half * half + s * s) / (2 * s); cz = crown - r
    n = 8 if h.lod == 0 else 5
    th = math.asin(half / r)
    arc = [(c + r * math.sin(-th + 2 * th * i / n), cz + r * math.cos(-th + 2 * th * i / n)) for i in range(n + 1)]
    d = -o.depth if h.lod < 2 else .018
    if h.lod < 2:
        m.polygon([f.point(a, crown), f.point(a, spring)] + [f.point(u, z) for u, z in arc[:n // 2 + 1]] +
                  ([f.point(c, crown)] if n % 2 else []), f.out, reveal)
        m.polygon([f.point(c, crown)] + [f.point(u, z) for u, z in arc[(n + 1) // 2:]] + [f.point(b, spring), f.point(b, crown)],
                  f.out, reveal)
        for x, nn in ((a, f.tangent), (b, -f.tangent)):
            m.polygon([f.point(x, sill, 0), f.point(x, sill, d), f.point(x, spring, d), f.point(x, spring, 0)], nn, reveal)
        m.polygon([f.point(a, sill, 0), f.point(b, sill, 0), f.point(b, sill, d), f.point(a, sill, d)], UP, reveal)
        for (u0, z0), (u1, z1) in zip(arc, arc[1:]):
            m.polygon([f.point(u0, z0, 0), f.point(u1, z1, 0), f.point(u1, z1, d), f.point(u0, z0, d)],
                      Vector3(f, (u0 + u1) / 2 - c, (z0 + z1) / 2 - cz, inward=True), reveal)
    shape = [f.point(a, sill, d), f.point(b, sill, d)] + [f.point(u, z, d) for u, z in reversed(arc)]
    if o.kind == "leaf":
        m.polygon(shape, f.out, h.door)
        if h.lod == 0:
            for u in (c - half * .5, c, c + half * .5):
                f.trim(m, u - .02, u + .02, sill, spring, d, d + .02, h.door)
    else:
        h.windows.polygon(shape, f.out, "Cream", room=nb.ROOMS[(int(c * 10) + 7) % len(nb.ROOMS)])
        if h.lod < 2:
            f.trim(m, c - .045, c + .045, sill, crown - .02, d, d + .06, h.frame)
            f.trim(m, a, b, sill, sill + .07, d, d + .06, h.frame)
    if h.lod < 2:                                                          # archivolt and jamb stones
        w = o.surround
        outer = [(c + (r + w) * math.sin(-th + 2 * th * i / n), cz + (r + w) * math.cos(-th + 2 * th * i / n)) for i in range(n + 1)]
        for (u0, z0), (u1, z1), (U0, Z0), (U1, Z1) in zip(arc, arc[1:], outer, outer[1:]):
            m.polygon([f.point(u0, z0, .03), f.point(u1, z1, .03), f.point(U1, Z1, .03), f.point(U0, Z0, .03)], f.out, "Dressed")
        for x0 in (a - w, b):
            f.trim(m, x0, x0 + w, sill, spring, 0, .03, "Dressed")

def Vector3(f, du, dz, inward=False):
    v = f.tangent * du
    v.z += dz
    return tuple(-v if inward else v)

# ------------------------------------------------------------------ roofs
def top_line(f, fn, breaks, L):
    """sample a roof-underside function along face f: fn(x, y) -> z, breakpoints in u"""
    us = sorted({0.0, L} | {u for u in breaks if 0 < u < L})
    return [(u, fn(*f.point(u, 0).to_tuple()[:2])) for u in us]

def roof_fn(R, ext):
    """underside height z(x, y) of the main roof at the wall line (walls rise to this)"""
    t = R["type"]
    if t == "ridgeX":
        P = R["Pext"]
        return lambda x, y: profile_z(P, min(max(y, P[0][0]), P[-1][0])) if True else None
    if t == "ridgeY":
        Q = R["Qext"]
        return lambda x, y: profile_z(Q, min(max(x, Q[0][0]), Q[-1][0]))
    z = R["coping"] if t == "flat" else R["eave"]
    return lambda x, y: z

def face_breaks(f, R):
    br = []
    if R["type"] == "ridgeX" and abs(f.tangent.y) > 1e-6:
        br = [(Y(y) - f.a.y) / f.tangent.y for y, _ in R["P"]]
    if R["type"] == "ridgeY" and abs(f.tangent.x) > 1e-6:
        br = [(X(x) - f.a.x) / f.tangent.x for x, _ in R["Q"]]
    return br

def slab_x(m, P, xa, xb, roof, cap):
    """roof slab: underside profile P [(y, z)] (blender y), thickness T, along x from xa to xb"""
    top = [(y, z + T) for y, z in P]
    for (y0, z0), (y1, z1) in zip(top, top[1:]):
        m.polygon([(xa, y0, z0), (xb, y0, z0), (xb, y1, z1), (xa, y1, z1)], (0, -(z1 - z0), y1 - y0), roof)
    for (y0, z0), (y1, z1) in zip(P, P[1:]):
        m.polygon([(xa, y0, z0), (xb, y0, z0), (xb, y1, z1), (xa, y1, z1)], (0, z1 - z0, -(y1 - y0)), SOFFIT)
    for (y, z), s in ((P[0], -1), (P[-1], 1)):
        m.polygon([(xa, y, z), (xb, y, z), (xb, y, z + T), (xa, y, z + T)], (0, s, 0), SOFFIT)
    sect = top + list(reversed(P))
    for x, s in ((xa, -1), (xb, 1)):
        m.polygon([(x, y, z) for y, z in sect], (s, 0, 0), cap)

def slab_y(m, Q, ya, yb, roof, cap):
    top = [(x, z + T) for x, z in Q]
    for (x0, z0), (x1, z1) in zip(top, top[1:]):
        m.polygon([(x0, ya, z0), (x0, yb, z0), (x1, yb, z1), (x1, ya, z1)], (-(z1 - z0), 0, x1 - x0), roof)
    for (x0, z0), (x1, z1) in zip(Q, Q[1:]):
        m.polygon([(x0, ya, z0), (x0, yb, z0), (x1, yb, z1), (x1, ya, z1)], (z1 - z0, 0, -(x1 - x0)), SOFFIT)
    for (x, z), s in ((Q[0], -1), (Q[-1], 1)):
        m.polygon([(x, ya, z), (x, yb, z), (x, yb, z + T), (x, ya, z + T)], (s, 0, 0), SOFFIT)
    sect = top + list(reversed(Q))
    for y, s in ((ya, -1), (yb, 1)):
        m.polygon([(x, y, z) for x, z in sect], (0, s, 0), cap)

def hip_faces(m, rect, z0, r0, r1, z1, mat):
    (xa, xb, ya, yb) = rect
    if abs(r0[0] - r1[0]) < 1e-6:            # ridge along y, r0 front
        r0, r1 = sorted((r0, r1), key=lambda p: p[1])
        faces = [([(xa, ya, z0), (xb, ya, z0), (*r0, z1)], (0, -1, 1)),
                 ([(xb, ya, z0), (xb, yb, z0), (*r1, z1), (*r0, z1)], (1, 0, 1)),
                 ([(xb, yb, z0), (xa, yb, z0), (*r1, z1)], (0, 1, 1)),
                 ([(xa, yb, z0), (xa, ya, z0), (*r0, z1), (*r1, z1)], (-1, 0, 1))]
    else:                                    # ridge along x, r0 left
        r0, r1 = sorted((r0, r1), key=lambda p: p[0])
        faces = [([(xa, ya, z0), (xb, ya, z0), (*r1, z1), (*r0, z1)], (0, -1, 1)),
                 ([(xb, ya, z0), (xb, yb, z0), (*r1, z1)], (1, 0, 1)),
                 ([(xb, yb, z0), (xa, yb, z0), (*r0, z1), (*r1, z1)], (0, 1, 1)),
                 ([(xa, yb, z0), (xa, ya, z0), (*r0, z1)], (-1, 0, 1))]
    for pts, d in faces:
        if len({tuple(round(c, 4) for c in p) for p in pts}) >= 3:
            m.polygon(pts, d, mat)

def eave_ring(m, outline, z):
    """soffit under a hipped/flat overhang + fascia"""
    m.polygon([(x, y, z) for x, y in outline], DOWN, SOFFIT)
    for f in edges(outline):
        f.quad(m, 0, f.length, z, z + T, 0, SOFFIT)

# ------------------------------------------------------------------ dormers (GPT round-3 rule)
def dormer3(h, xc, w_out, prof, yd, kind, roof, cheek, face, sashes=None, face_h=1.23, sash_z=(.18, 1.08), sash_in=.40,
            face_fn=None):
    m = h.body
    zb = profile_z(prof, yd)
    zde = zb + face_h
    half, oh = w_out / 2, .08
    if kind == "G":
        rise = (half + oh) * math.tan(math.radians(32))
        cap = [(-half - oh, 0), (0, rise), (half + oh, 0)]
    elif kind == "P":
        cap = [(-half - oh, 0), (0, .22), (half + oh, 0)]
    else:
        n = 6 if h.lod < 2 else 3
        cap = [(-(half + oh) * math.cos(math.pi * i / n), .22 * math.sin(math.pi * i / n)) for i in range(n + 1)]
    peak = zde + max(z for _, z in cap)
    zmax = max(z for _, z in prof)
    yend = profile_y(prof, min(peak, zmax - .01)) + .05
    yc = profile_y(prof, min(zde, zmax - .01))
    front = Face((xc - half, yd), (xc + half, yd))
    ops = sashes or [Opening(half, w_out - sash_in, zb + sash_z[0], zb + sash_z[1], "sash", stone=False)]
    if sashes:
        ops = [Opening(half + dx, sw, zb + .18, zb + 1.08, "sash", stone=False) for dx, sw in sashes]
    if face_fn:                                             # round 5: custom face (oval bull's-eye)
        face_fn(h, front, zb, zde, face)
    else:
        front.wall(h, zb, zde, ops, face)
    m.polygon([(xc + x, yd, zde + z) for x, z in cap], (0, -1, 0), face)
    for (xa, za), (xb, zb2) in zip(cap, cap[1:]):
        quad = [(xc + xa, yd - oh, zde + za), (xc + xb, yd - oh, zde + zb2), (xc + xb, yend, zde + zb2), (xc + xa, yend, zde + za)]
        m.polygon(quad, (-(zb2 - za), 0, xb - xa), roof)
        m.polygon([(x, y, z - .05) for x, y, z in quad], ((zb2 - za), 0, -(xb - xa)), SOFFIT)
        m.polygon([(xc + xa, yd - oh, zde + za - .05), (xc + xb, yd - oh, zde + zb2 - .05),
                   (xc + xb, yd - oh, zde + zb2), (xc + xa, yd - oh, zde + za)], (0, -1, 0), SOFFIT)
    m.polygon([(xc + x, yend, zde + z) for x, z in cap], (0, 1, 0), roof)
    for s, (x, z) in ((-1, cap[0]), (1, cap[-1])):
        m.polygon([(xc + x, yd - oh, zde + z - .05), (xc + x, yend, zde + z - .05), (xc + x, yend, zde + z),
                   (xc + x, yd - oh, zde + z)], (s, 0, 0), SOFFIT)
    inner = [(y, z) for y, z in reversed(prof) if yd + 1e-4 < y < yc - 1e-4]
    for s in (-1, 1):
        x = xc + s * half
        # cheek runs all the way back to the dormer roof's end and down to the base height: the part below the
        # main roof is buried, and the dormer stays closed even where its cap rises above the ridge
        m.polygon([(x, yd, zb), (x, yd, zde), (x, yend, zde), (x, yend, zb)], (s, 0, 0), cheek)
    m.polygon([(xc - half, yend, zb), (xc + half, yend, zb), (xc + half, yend, zde), (xc - half, yend, zde)], (0, 1, 0), cheek)

# ------------------------------------------------------------------ small shared pieces
def stoop(h, xa, xb, yw, ztop, landing=.95, tread=.27, rails=None, flare=0.0):
    """stone stoop against the wall at blender y=yw, steps running toward the street; returns front edge y"""
    m = h.body
    n = max(1, round(ztop / .17))
    rise = ztop / n
    depth = landing + (n - 1) * tread
    room = yw - (-12.0) - .15
    if depth > room:
        tread = max(.20, (room - landing) / max(1, n - 1)); depth = landing + (n - 1) * tread
        if depth > room:
            landing = max(.5, room - (n - 1) * tread); depth = landing + (n - 1) * tread
    y0 = yw - depth
    for k in range(n):
        ya = y0 + k * tread
        fl = flare * (1 - k / max(1, n - 1)) if k == 0 else 0
        m.box(xa - fl, xb + fl, ya, yw, k * rise, (k + 1) * rise, "Dressed", bottom=False)
    if (rails if rails is not None else ztop > .45) and h.lod < 2:
        for x in (xa + .06, xb - .06):
            bar(m, "x", y0 + .05, rise + .92, yw - landing, ztop + .92, x - .025, x + .025, .05, "Iron")
            m.box(x - .03, x + .03, y0 + .03, y0 + .09, rise, rise + .95, "Iron", bottom=False)
            if landing > .3:
                m.box(x - .025, x + .025, yw - landing, yw - .02, ztop + .87, ztop + .92, "Iron", bottom=False)
    return y0

def walk_to(h, xc, y_from, w=1.0):
    if y_from > -11.9:
        walk(h, max(-nb.W / 2 + .01, xc - w / 2), min(nb.W / 2 - .01, xc + w / 2), y_from)

def shed(h, axis, a0, a1, w_wall, w_face, z_wall, z_face, mat):
    """thin sloped sheet roof (hood / porch / gallery roof) from a wall line to its face, along `axis`"""
    prof = [(w_wall, z_wall), (w_face, z_face), (w_face, z_face - .06), (w_wall, z_wall - .06)]
    extrude(h.body, prof, axis, a0, a1, [mat, SOFFIT, SOFFIT, SOFFIT], (SOFFIT, SOFFIT))

def gallery(h, xa, xb, yw, yo, decks, roof=None, posts=None, post_mat="Cream", rail_mat="Iron", gap=None,
            base="Rubble", stairs_x=None, ceiling=True, plain=False):
    """deck(s) between the wall line yw and outer line yo (blender), posts on the outer line, rails on the open
    edges (except the stair gap), optional shed roof (z_wall, z_face, mat)"""
    m = h.body
    ya, yb = sorted((yw, yo))
    s = 1 if yo > yw else -1                                   # direction away from the wall
    py = yo - s * .10
    if posts is None:
        n = max(1, math.ceil((xb - xa - .14) / 2.1))
        posts = [xa + .07 + (xb - xa - .14) * i / n for i in range(n + 1)]
    top_z = None
    if roof:
        z_wall, z_face, rmat = roof
        shed(h, "x", xa - .05, xb + .05, yw, yo + s * .10, z_wall, z_face, rmat)
        top_z = z_face + (z_wall - z_face) * .10 / (abs(yo - yw) + .10) - .07
    for i, z in enumerate(decks):
        if i == 0 and z > .2 and base:
            m.box(xa, xb, ya, yb, 0, z - .16, base, bottom=False)
        m.box(xa, xb, ya, yb, max(0, z - .16), z, "Deck", top=None, bottom=(i > 0))
        nxt = decks[i + 1] - .16 if i + 1 < len(decks) else top_z
        if nxt and h.lod < 2 or (nxt and h.lod == 2 and i == 0):
            for x in posts:
                if post_mat == "Iron":
                    iron_post(h, x, py, z, nxt)
                else:
                    m.box(x - .07, x + .07, py - .07, py + .07, z, nxt, post_mat, bottom=False)
            if post_mat == "Iron" and len(posts) > 1 and not plain:
                iron_frieze(h, [(x, py) for x in posts], nxt)
        if z > .3 or i > 0:
            lo, hi = sorted((xa + .07, xb - .07))
            segs = [(lo, hi)]
            if gap and i == 0:
                segs = [(lo, gap[0]), (gap[1], hi)]
            for a, b in segs:
                if b - a > .2:
                    railing(h, a, py, b, py, z, .92, rail_mat, .2 if plain else .14)
            for x in (xa + .07, xb - .07):
                railing(h, x, py, x, yw - s * .03, z, .92, rail_mat, .2 if plain else .14)
    if decks[0] <= .2 or True:
        for x in posts:
            if decks[0] > .2:
                pass
    if posts and decks[0] > .2:                                # posts under the first deck stand on the base
        pass
    if stairs_x is not None and decks[0] > .05:
        n = max(1, round(decks[0] / .17))
        for k in range(n):
            y0 = yo + s * (n - k) * .27
            a, b = sorted((yo, y0))
            m.box(stairs_x - .55, stairs_x + .55, a, b, k * decks[0] / n, (k + 1) * decks[0] / n, "Dressed", bottom=False)
        return yo + s * n * .27
    return yo

def lantern(h, cx, cy, half, z0, z1, peak, side_mat="TinFlat", cap_mat="TinFlat"):
    m = h.body
    sq = rectangle(cx - half, cx + half, cy - half, cy + half)
    prism(m, sq, z0, z1, side_mat, bottom=False)
    cap = rectangle(cx - half - .1, cx + half + .1, cy - half - .1, cy + half + .1)
    m.polygon([(*p, z1) for p in cap], DOWN, SOFFIT)
    for a, b in zip(cap, cap[1:] + cap[:1]):
        m.polygon([(*a, z1), (*b, z1), (cx, cy, peak)], ((a[0] + b[0]) / 2 - cx, (a[1] + b[1]) / 2 - cy, .8), cap_mat)

class Path2:
    """centreline for stair flights: list of straight/arc pieces in blender xy"""
    def __init__(self, pieces):
        self.pieces = pieces                       # ("line", p0, p1) | ("arc", centre, r, a0, a1)
        self.lengths = [self._len(p) for p in pieces]
        self.L = sum(self.lengths)
    def _len(self, p):
        if p[0] == "line":
            return math.dist(p[1], p[2])
        return abs(p[4] - p[3]) * p[2]
    def at(self, s):
        for p, l in zip(self.pieces, self.lengths):
            if s <= l + 1e-9 or p is self.pieces[-1]:
                t = min(1, s / l) if l else 0
                if p[0] == "line":
                    (x0, y0), (x1, y1) = p[1], p[2]
                    return (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t), ((x1 - x0) / l, (y1 - y0) / l)
                (cx, cy), r, a0, a1 = p[1:]
                a = a0 + (a1 - a0) * t
                sg = 1 if a1 > a0 else -1
                return (cx + r * math.cos(a), cy + r * math.sin(a)), (-math.sin(a) * sg, math.cos(a) * sg)
            s -= l

def quad_prism(m, quad, z0, z1, mat):
    if area2d(quad) < 0:
        quad = list(reversed(quad))
    prism(m, quad, z0, z1, mat)

def flight(h, path, z0, z1, risers, width):
    """iron flight along a Path2 from z0 (start) to z1 (end): treads, side plates, stepped rails"""
    m = h.body
    n = risers if h.lod == 0 else max(4, risers // 2) if h.lod == 1 else max(3, risers // 4)
    if nb.LITE >= 4:
        n = max(3, (risers * 2) // 3) if h.lod == 0 else max(3, risers // 4)
    rise = (z1 - z0) / n
    goings = n - 1
    hw = width / 2
    for k in range(1, n):
        s0, s1 = path.L * (k - 1) / goings, path.L * k / goings
        (p0, t0), (p1, t1) = path.at(s0), path.at(s1)
        n0, n1 = (-t0[1], t0[0]), (-t1[1], t1[0])
        z = z0 + k * rise
        quad = [(p0[0] + n0[0] * hw, p0[1] + n0[1] * hw), (p1[0] + n1[0] * hw, p1[1] + n1[1] * hw),
                (p1[0] - n1[0] * hw, p1[1] - n1[1] * hw), (p0[0] - n0[0] * hw, p0[1] - n0[1] * hw)]
        quad_prism(m, quad, z - .05, z, "Iron")
        for sgn in (1, -1):                                   # closed stringer plates, stepped
            o0, o1 = hw * sgn, (hw + .08) * sgn
            plate = [(p0[0] + n0[0] * o0, p0[1] + n0[1] * o0), (p1[0] + n1[0] * o0, p1[1] + n1[1] * o0),
                     (p1[0] + n1[0] * o1, p1[1] + n1[1] * o1), (p0[0] + n0[0] * o1, p0[1] + n0[1] * o1)]
            quad_prism(m, plate, max(0, z - .32), z + .04, "Iron")
            if h.lod < 2 and not (nb.LITE >= 4 and h.lod == 1):
                rail = [(p0[0] + n0[0] * (o0 + .02 * sgn), p0[1] + n0[1] * (o0 + .02 * sgn)),
                        (p1[0] + n1[0] * (o0 + .02 * sgn), p1[1] + n1[1] * (o0 + .02 * sgn)),
                        (p1[0] + n1[0] * (o1 - .02 * sgn), p1[1] + n1[1] * (o1 - .02 * sgn)),
                        (p0[0] + n0[0] * (o1 - .02 * sgn), p0[1] + n0[1] * (o1 - .02 * sgn))]
                quad_prism(m, rail, z + .90, z + .95, "Iron")
                if k % 2 == 1 and nb.LITE < 4:
                    q = p0[0] + n0[0] * (o0 + o1) / 2, p0[1] + n0[1] * (o0 + o1) / 2
                    m.box(q[0] - .015, q[0] + .015, q[1] - .015, q[1] + .015, z, z + .9, "Iron", bottom=False)

def landing(h, xa, xb, ya, yb, z, posts=True):
    m = h.body
    m.box(xa, xb, ya, yb, z - .12, z, "Iron")
    if posts:
        for x, y in ((xa + .05, ya + .05), (xb - .05, ya + .05)):
            m.box(x - .04, x + .04, y - .04, y + .04, 0, z - .12, "Iron", bottom=False)

def bay(h, cx, yw, z0, z_cap, datum, oriel=False, cap_face=None, cap_wall=None, mat="Brick097"):
    """canted bay (or oriel): 2.18 at the wall, .62 deep, 1.34 face, sashes .88 above `datum`"""
    m = h.body
    plan = [(cx - 1.09, yw), (cx + 1.09, yw), (cx + .67, yw - .62), (cx - .67, yw - .62)]
    plan = [plan[0], plan[3], plan[2], plan[1]]                     # CCW seen from above
    fs = edges(plan)
    for i, f in enumerate(fs[:3]):
        w = 1.04 if i == 1 else .43
        f.wall(h, z0, z_cap, [Opening(f.length / 2, w, datum + .88, datum + 2.26)], mat)
    if oriel:
        m.polygon([(*p, z0) for p in plan], DOWN, "Dressed")
        for i in (0, 2):
            p = fs[i].point(fs[i].length / 2, 0)
            m.box(p.x - .09, p.x + .09, yw - .45, yw, z0 - .26, z0, "Dressed", bottom=False)
        zf, zw = cap_face, cap_wall
        capp = [(cx - 1.15, yw), (cx - .70, yw - .68), (cx + .70, yw - .68), (cx + 1.15, yw)]
        top = [(x, y, zw + (zf - zw) * (yw - y) / .68) for x, y in capp]
        m.polygon(top, UP, "SlateDark")
        m.polygon([(x, y, z - .16) for x, y, z in reversed(top)], DOWN, SOFFIT)
        for a, b in zip(top, top[1:]):
            m.polygon([(a[0], a[1], a[2] - .16), (b[0], b[1], b[2] - .16), b, a], (b[1] - a[1], -(b[0] - a[0]), 0), "SlateDark")
    else:
        capp = [(cx - 1.15, yw), (cx - .70, yw - .68), (cx + .70, yw - .68), (cx + 1.15, yw)]
        prism(m, capp, z_cap, z_cap + .16, "TinFlat")

# ------------------------------------------------------------------ the generic builder
def build_spec(h, S):
    m = h.body
    x0, x1, yf, yb = S["walls"]
    bx0, bx1, byf, byb = X(x0), X(x1), Y(yf), Y(yb)
    e = S["eave"]
    h.door, h.frame, h.shop = S["door"], S["frame"], "Green"
    front_m, side_m, rear_m, base_m, trim_m = S["facade"]
    h.sill = "Dressed" if trim_m == "Dressed" else "Dressed"
    commercial = "Commercial" in S["zone"]
    detached = "Residential Low" in S["zone"]
    R = copy.deepcopy(S["R"]) if S.get("R") else parse_roof(S); R["eave"] = e
    cp, ch, brackets, cmat = S["cornice"]
    chamf = S.get("chamfer", 0.0)
    acc = S["access"]
    # plan (CCW from above): front, right, rear, left (+ chamfer)
    if chamf and acc == "LeftCorner":
        plan = [(bx0 + chamf, byf), (bx1, byf), (bx1, byb), (bx0, byb), (bx0, byf + chamf)]
        names = ["front", "right", "rear", "left", "chamfer"]
    elif chamf and acc == "RightCorner":
        plan = [(bx0, byf), (bx1 - chamf, byf), (bx1, byf + chamf), (bx1, byb), (bx0, byb)]
        names = ["front", "chamfer", "right", "rear", "left"]
    else:
        plan = [(X(a), Y(b)) for a, b in S["plan_spec"]] if S.get("plan_spec") else rectangle(bx0, bx1, byf, byb)
        names = S.get("plan_names") or ["front", "right", "rear", "left"]
    faces = list(zip(names, edges(plan)))
    exposed = {"left": detached or acc == "LeftCorner", "right": detached or acc == "RightCorner"}
    # roof outline extension (overhang): eaves move out by the cornice projection on non-party sides
    ov_side = max(.15, cp) if detached else 0.0
    if R["type"] == "ridgeX":
        P = [(Y(y), z) for y, z in R["P"]]
        if S.get("front_kick"):
            P = [(Y(y), z) for y, z in S["front_kick"]] + P
        else:
            P[0] = (P[0][0] - cp, P[0][1])
        P[-1] = (P[-1][0] + cp, P[-1][1])
        R["Pext"] = P
    elif R["type"] == "ridgeY":
        Q = [(X(x), z) for x, z in R["Q"]]
        Q[0] = (Q[0][0] - ov_side, Q[0][1]); Q[-1] = (Q[-1][0] + ov_side, Q[-1][1])
        R["Qext"] = Q
    zfn = roof_fn(R, None)
    # openings by face
    by_face = {n: [] for n in names}
    arches = {n: [] for n in names}
    def local(face_name, f, o):
        side = o["side"]
        if face_name == "front":
            return X(o["c"]) - f.a.x
        if face_name == "rear":
            return f.a.x - X(o["c"])
        if face_name == "chamfer":
            return o["c"] if acc == "RightCorner" else f.length - o["c"]
        return (Y(o["c"]) - f.a.y) / f.tangent.y
    def kind(o, face_name):
        if o.get("kind"):                                   # round 4: explicit opening kind
            return o["kind"]
        k = o["k"]
        if k == "F":
            return "french"
        if k == "D":
            return "shopdoor" if commercial and o["floor"] == 0 and face_name in ("front", "chamfer") else "door"
        if k == "V":
            return "shop"
        if k == "A" and (o["t"] - o["b"] < .5 or o["w"] < .5):
            return "small"
        return "pair" if o["w"] >= 1.5 else "sash"
    def place(face_name, o):
        cands = [(n, f) for n, f in faces if n == face_name or (face_name in ("left", "right") and n.startswith(face_name) and abs(f.tangent.y) > .5)]
        for n, f in cands:
            u = local(n, f, o)
            if -1e-6 <= u - o["w"] / 2 and u + o["w"] / 2 <= f.length + 1e-6:
                op = Opening(u, o["w"], o["b"], o["t"], kind(o, face_name), o["shutter"],
                             stone=not (o["k"] == "A" and o["t"] - o["b"] < .5))
                by_face[n].append(op)
                return
        raise ValueError(f"{S['design']}: opening {o} does not fit {face_name}")
    for o in S["front"]:
        place("front", o)
    for o in S["rear"]:
        place("rear", o)
    for o in S["sides"]:
        place({"L": "left", "R": "right", "C": "chamfer"}[o["side"]], o)
    for n, o in S.get("arches", []):
        f = dict(faces)[n]
        o.center = X(o.center) - f.a.x if n == "front" else o.center
        arches[n].append(o)
    for n, f in faces:
        fit_shutters(f, by_face[n])
    # walls
    datum0 = S["datums"][0]
    for n, f in faces:
        mat = front_m if n in ("front", "chamfer") else rear_m if n == "rear" else side_m
        if n == "chamfer" and S.get("chamfer_mat"):
            mat = S["chamfer_mat"]
        if n.startswith("left") or n.startswith("right"):
            mat = side_m
        bands = [(0,99,mat)] if h.lod==2 else [(0, max(datum0, .12), base_m), (max(datum0, .12), 99, mat)]
        top = top_line(f, zfn, face_breaks(f, R), f.length)
        poly_wall(h, f, top, bands, by_face[n], arches[n])
    m.polygon([(x, y, .02) for x, y in plan], DOWN, base_m)
    belt_courses(h, S, faces, by_face, arches, front_m, trim_m)
    # roof
    rm = R["mat"]
    cap_mat = trim_m if trim_m in ("Dressed", "Cream") else SOFFIT
    xa = bx0 - (ov_side if exposed["left"] else 0)
    xb = bx1 + (ov_side if exposed["right"] else 0)
    if acc == "LeftCorner":
        xa = bx0 - .2
    if acc == "RightCorner":
        xb = bx1 + .2
    xa, xb = max(xa, -nb.W / 2), min(xb, nb.W / 2)
    prof_front = None
    fw = S.get("firewall")
    if R["type"] == "ridgeX":
        sxa, sxb = (bx0 + .22, bx1 - .22) if fw else (xa, xb)
        slab_x(m, R["Pext"], sxa, sxb, rm, side_m if not exposed["left"] and not exposed["right"] else cap_mat)
        top = [(y, z + T) for y, z in R["Pext"]]
        imax = max(range(len(top)), key=lambda i: top[i][1])
        prof_front = top[:imax + 1]
        if fw:
            from nf_build import firewall as fwall
            for a, b in ((bx0, bx0 + .22), (bx1 - .22, bx1)):
                fwall(h, top, a, b, side_m, front_m, "Dressed", fw)
        if cp > 0 and not S.get("front_kick"):
            for yw, out in ((byf, -1), (byb, 1)):
                z = zfn(0, yw)
                f = Face((xa, yw), (xb, yw)) if out < 0 else Face((xb, yw), (xa, yw))
                cornice_profile(h, f, 0, f.length, z, cp, ch, cmat, brackets, plain=out > 0)
        elif cp > 0:
            m.box(xa, xb, byb, byb + cp, e - ch, e, cmat)
    elif R["type"] == "ridgeY":
        ya, yb2 = byf - .15, byb + .15
        if R.get("parts"):                                                     # paired street gables, one slab each
            for i, qp in enumerate(R["parts"]):
                Qp = [(X(x), z) for x, z in qp]
                if i == 0:
                    Qp[0] = (Qp[0][0] - ov_side, Qp[0][1])
                if i == len(R["parts"]) - 1:
                    Qp[-1] = (Qp[-1][0] + ov_side, Qp[-1][1])
                slab_y(m, Qp, ya, yb2, rm, cap_mat)
        else:
            slab_y(m, R["Qext"], ya, yb2, rm, cap_mat)
        if R.get("clip"):                                                      # round 4 clipped gable: small hips
            c = R["clip"]
            hip_faces(m, (X(c["xa"]), X(c["xb"]), ya, yb2), c["zc"] + T, (X(c["xc"]), ya + c["depth"]),
                      (X(c["xc"]), yb2 - c["depth"]), c["rz"] + T, rm)
        if h.lod < 2:                                                          # cornice returns across the gable fronts
            for yw, out in ((byf, -1), (byb, 1)):
                f = Face((bx0, yw), (bx1, yw)) if out < 0 else Face((bx1, yw), (bx0, yw))
                cornice_profile(h, f, 0, f.length, e, max(cp, .1), ch, cmat, False, plain=out > 0)
            if detached:
                for xw, s in ((bx0, -1), (bx1, 1)):
                    q0, q1 = sorted((xw, xw + s * max(cp, .1)))
                    m.box(q0, q1, byf, byb, e - ch, e, cmat)
            Q = R["Qext"]
            for (qa, za), (qb, zb) in zip(Q, Q[1:]):                          # any number of gables (round 4)
                for yw, d in ((byf - .15, -1), (byb + .15, 1)):
                    a2, b2 = sorted((yw, yw + d * .12))
                    bar(m, "y", qa, za + T + .02, qb, zb + T + .02, a2, b2, .18, cap_mat)
    elif R["type"] in ("hip", "mansard4"):
        dists = []
        for n, f in faces:
            party = (n == "left" and not exposed["left"]) or (n == "right" and not exposed["right"])
            dists.append(0.0 if party else cp)
        rect_plan = rectangle(bx0, bx1, byf, byb)
        rd = [dists[names.index("front")], dists[names.index("right")], dists[names.index("rear")], dists[names.index("left")]]
        out = offset_plan(rect_plan, rd)
        if cp > 0 and h.lod < 2:
            prism(m, out, e - ch, e, cmat, bottom=True)
        eave_ring(m, out, e)
        oxa, oxb = out[0][0], out[1][0]; oya, oyb = out[0][1], out[2][1]
        if R["type"] == "hip":
            (r0, r1) = [(X(a), Y(b)) for a, b in R["ridge"]]
            hip_faces(m, (oxa, oxb, oya, oyb), e + T, r0, r1, R["rz"] + T, rm)
            prof_front = None
        else:
            fr = [(Y(y), z) for y, z in R["front"]]
            ins = R["inset"]
            bz = fr[1][1] + T
            br = (bx0 + ins, bx1 - ins, fr[1][0], 2 * fr[-1][0] - fr[1][0])
            low = [((oxa, oya), (oxb, oya), (br[1], br[2]), (br[0], br[2]), (0, -1, 1)),
                   ((oxb, oya), (oxb, oyb), (br[1], br[3]), (br[1], br[2]), (1, 0, 1)),
                   ((oxb, oyb), (oxa, oyb), (br[0], br[3]), (br[1], br[3]), (0, 1, 1)),
                   ((oxa, oyb), (oxa, oya), (br[0], br[2]), (br[0], br[3]), (-1, 0, 1))]
            for a, b, c, d, dr in low:
                m.polygon([(*a, e + T), (*b, e + T), (*c, bz), (*d, bz)], dr, rm)
            (r0, r1) = [(X(a), b) for a, b in R["ridge"]]
            r0, r1 = (r0[0], Y(R["front"][-1][0])), (r1[0], Y(R["front"][-1][0]))
            hip_faces(m, br, bz, r0, r1, R["rz"] + T, R.get("upper_mat", rm))
            prof_front = [(oya, e + T), (br[2], bz), (r0[1], R["rz"] + T)]
    elif R["type"] == "multihip":                                              # round 4 paired pavilions
        rd = [cp, cp if exposed["right"] else 0.0, cp, cp if exposed["left"] else 0.0]
        out = offset_plan(rectangle(bx0, bx1, byf, byb), rd)
        if cp > 0 and h.lod < 2:
            prism(m, out, e - ch, e, cmat, bottom=True)
        eave_ring(m, out, e)
        for sg in R["segments"]:
            sx0, sx1 = X(sg["x0"]), X(sg["x1"])
            sxa = out[0][0] if sg["x0"] <= x0 + .01 else sx0
            sxb = out[1][0] if sg["x1"] >= x1 - .01 else sx1
            (r0, r1) = [(X(a), Y(b)) for a, b in sg["ridge"]]
            hip_faces(m, (sxa, sxb, out[0][1], out[2][1]), e + T, r0, r1, sg["rz"] + T, rm)
        bz = R["bridge"]
        if bz:
            m.box(X(bz[0]), X(bz[1]), out[0][1], out[2][1], e + T, bz[2], "TinFlat", bottom=False)
    elif R["type"] == "flat":
        cz = R["coping"]
        inner = offset_plan(plan, [-.22] * len(plan))
        m.polygon([(x, y, e) for x, y in inner], UP, "TinFlat")
        for (a, b), (ia, ib) in zip(zip(plan, plan[1:] + plan[:1]), zip(inner, inner[1:] + inner[:1])):
            m.polygon([(*a, cz), (*b, cz), (*ib, cz), (*ia, cz)], UP, "Dressed")
            nrm = (-(b[1] - a[1]), b[0] - a[0], 0)
            m.polygon([(*ia, e), (*ib, e), (*ib, cz), (*ia, cz)], nrm, side_m)
        if cp > 0:
            for n, fr in faces:
                if n in ("front", "chamfer"):
                    cornice_profile(h, fr, 0, fr.length, cz - .07, cp, ch, cmat, brackets)
    # dormers
    if S["dormers"] and prof_front:
        k, xs, w = S["dormers"]
        off = .52 if "mansard" in S["roof_raw"].lower() else 1.05
        face_mat = "Dressed" if trim_m == "Dressed" and k == "P" else "Cream" if trim_m != "Dressed" else "Dressed"
        if k == "G":
            face_mat = front_m
        cheek = S.get("dormer_cheek", rm)
        for xc in xs:
            dormer3(h, X(xc), w, prof_front, byf + off, k, rm, cheek, face_mat, S.get("dormer_sashes"))
    # chimneys
    for c in S["chimneys"]:
        cx, cy, cw, cd, top = c
        chimney(h, X(cx), Y(cy), e - .3, top - .12, "Chimney" if "Brick" in side_m or "Brick" in front_m else
                ("Rubble" if base_m == "Rubble" else "Chimney"), cw / 2, cd / 2)
    if S.get("fq"):
        fq_balconies(h, S, faces, by_face, arches, acc)
    return {"roof_outline_m2": area2d(plan), "roof_check_z": min(e, min((z for _, z in R.get("P", [(0, e)])), default=e)) - .05,
            "party_sides": [s for s in ("left", "right") if not exposed[s]], "access": acc}

# ------------------------------------------------------------------ French Quarter dressing
NO_BELT = {"RightCornerTinStore", "SteppedBayRow"}          # these carry their own specced band

def belt_courses(h, S, faces, by_face, arches, front_m, trim_m):
    """projecting belt course at every upper floor line on masonry street faces, broken around openings"""
    if h.lod == 2 or front_m.startswith("Clap") or S["design"] in NO_BELT:
        return
    mat = trim_m if trim_m in ("Dressed", "Cream") else "Dressed"
    for n, f in faces:
        if n not in ("front", "chamfer"):
            continue
        for dz in S["datums"][1:]:
            z0, z1 = dz - .03, dz + .09
            blocked = sorted((o.left - .02, o.right + .02) for o in list(by_face[n]) + list(arches[n])
                             if o.bottom < z1 and o.top > z0)
            u = 0.0
            for a, b in blocked + [(f.length, f.length)]:
                if a - u > .08:
                    f.trim(h.body, u, a, z0, z1, 0, .035, mat)
                u = max(u, b)

def fit_shutters(f, ops):
    """shutter leaf width from the room each side: neighbours on the same floor share the gap"""
    for o in ops:
        if not o.shutter:
            continue
        room = [o.left - .10, f.length - o.right - .10]
        for q in ops:
            if q is o or not (q.bottom < o.top and q.top > o.bottom):
                continue
            g = o.left - q.right if q.center < o.center else q.left - o.right
            room.append(g / 2 - .06 if q.shutter else g - .10)
        o.shutter_w = max(0.0, min(.55, o.width / 2, *room) - .03)

def console(h, x, y, nx, ny, ztop, d):
    """wrought-iron balcony console: a triangular plate under the slab with a scroll ring"""
    m = h.body
    zb = ztop - .40
    if abs(ny) > .5:
        extrude(m, [(y, ztop), (y + ny * d, ztop), (y, zb)], "x", x - .025, x + .025, "Iron", ("Iron", "Iron"))
        P = lambda s, zz: (x, y + ny * s, zz); n = (1, 0, 0)
    else:
        extrude(m, [(x, ztop), (x + nx * d, ztop), (x, zb)], "y", y - .025, y + .025, "Iron", ("Iron", "Iron"))
        P = lambda s, zz: (x + nx * s, y, zz); n = (0, 1, 0)
    if h.lod == 0 and not nb.LITE:
        for sx in (.03, -.03):
            Pq = (lambda s, zz, sx=sx: tuple(a + b for a, b in zip(P(s, zz), (n[0] * sx, n[1] * sx, 0))))
            lace_ring(m, Pq, d * .30, ztop - .14, .085, .065, n, "Iron", 8)

def balcony(h, path, z, depth, blocked=()):
    """cantilevered wrought-iron balcony along a wall polyline (outside on the right of travel): stone slab,
    cast-iron lace railing with end returns, consoles on the piers"""
    m = h.body
    path = list(path)
    LIM = nb.W / 2 - .08                                             # width-aware (round 4)
    for end, nxt in ((0, 1), (len(path) - 1, len(path) - 2)):
        p, q = path[end], path[nxt]
        L = math.dist(p, q)
        sgn = 1 if end == 0 else -1
        nx, ny = ((q[1] - p[1]) / L, -(q[0] - p[0]) / L) if end == 0 else ((p[1] - q[1]) / L, -(p[0] - q[0]) / L)
        ox = p[0] + nx * depth
        if abs(ox) > LIM and abs(q[0] - p[0]) > 1e-6:
            target = math.copysign(LIM, ox) - nx * depth            # wall x that keeps the outer edge at the limit
            t = (target - p[0]) / (q[0] - p[0])
            if 0 < t < .95:
                path[end] = (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
    segs = list(zip(path, path[1:]))
    def nrm(p, q):
        L = math.dist(p, q)
        return ((q[1] - p[1]) / L, -(q[0] - p[0]) / L)
    ns = [nrm(p, q) for p, q in segs]
    outer = []
    for i, p in enumerate(path):
        if 0 < i < len(path) - 1:
            a, b = ns[i - 1], ns[i]
            bx, by = a[0] + b[0], a[1] + b[1]
            l = math.hypot(bx, by); nx, ny = bx / l, by / l
            k = depth / (nx * a[0] + ny * a[1])
        else:
            nx, ny = ns[0] if i == 0 else ns[-1]
            k = depth
        outer.append((min(LIM, max(-LIM, p[0] + nx * k)), max(-11.92, p[1] + ny * k)))
    slab = list(path) + outer[::-1]
    if area2d(slab) < 0:
        slab.reverse()
    th = .12
    prism(m, slab, z - th, z, "Dressed")
    if h.lod == 2:
        return
    if h.lod == 1 and nb.LITE >= 3:                                  # budget fallback: one closed rail band
        for a, b in zip(outer, outer[1:]):
            obar = nb.obar
            obar(m, a, b, .04, z + .05, z + .95, "Iron")
        return
    if h.lod == 0:                                                   # moulded slab edge
        for a, b in zip(outer, outer[1:]):
            from nf_build import obar
            obar(m, a, b, .05, z - th - .04, z - th + .02, "Dressed")
    for a, b in zip(outer, outer[1:]):
        railing(h, a[0], a[1], b[0], b[1], z, .95, "Iron")
    for wpt, opt in ((path[0], outer[0]), (path[-1], outer[-1])):
        d = math.dist(wpt, opt)
        if d > .12:
            t = (d - .04) / d
            railing(h, opt[0], opt[1], opt[0] + (wpt[0] - opt[0]) * t, opt[1] + (wpt[1] - opt[1]) * t, z, .95, "Iron")
    for (p, q), (nx, ny) in zip(segs, ns):
        L = math.dist(p, q)
        if L < .3 or not (abs(nx) < 1e-6 or abs(ny) < 1e-6):
            continue
        ncons = max(2, math.ceil(L / 1.6) + 1)
        for i in range(ncons):
            s_ = .12 + (L - .24) * i / (ncons - 1)
            x, y = p[0] + (q[0] - p[0]) * s_ / L, p[1] + (q[1] - p[1]) * s_ / L
            along = x if abs(ny) > .5 else y
            if any(lo - .06 < along < hi + .06 for lo, hi in blocked):
                continue
            if h.lod == 0 or nb.LITE < 3:
                console(h, x, y, nx, ny, z - th, depth * .78)

def fq_balconies(h, S, faces, by_face, arches, acc):
    fd = dict(faces)
    z = S["datums"][1] + .02
    f = fd["front"]
    blocked = []                                                     # piers only: no consoles over ground openings
    for o in list(by_face["front"]) + list(arches["front"]):
        if o.bottom < 1.2:
            blocked.append((f.a.x + o.left, f.a.x + o.right))
    pt = lambda face, u: (face.point(u, 0).x, face.point(u, 0).y)
    if S["fq"] == "continuous":
        L = f.length
        if acc == "LeftCorner" and "chamfer" in fd:
            c = fd["chamfer"]
            paths = [[pt(c, 0), pt(c, c.length), pt(f, L - .15)]]
        elif acc == "RightCorner" and "chamfer" in fd:
            c = fd["chamfer"]
            paths = [[pt(f, .15), pt(f, L), pt(c, c.length)]]
        else:
            paths = [[pt(f, .15), pt(f, L - .15)]]
        depth = .85
    else:
        paths, depth = [], .72
        for n in ("front", "chamfer"):
            if n not in fd:
                continue
            face = fd[n]
            spans = sorted((max(0, o.left - .28), min(face.length, o.right + .28)) for o in by_face[n]
                           if o.kind == "french" and abs(o.bottom - z) < .05)
            merged = []
            for a, b in spans:
                if merged and a <= merged[-1][1] + .25:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], b))
                else:
                    merged.append((a, b))
            paths += [[pt(face, a), pt(face, b)] for a, b in merged]
    for path in paths:
        balcony(h, path, z, depth, blocked)

FQ_BALCONY = {"FirewallBrickRow", "RockfaceRow", "FaubourgRow", "CarriageArchRow", "TinParapetRow", "RearGalleryTriplexRow",
              "LeftCornerEpicerieStore", "RightCornerTinStore", "LeftCornerTavernShop", "RightCornerPharmacieShop",
              "BuffBrickMansardShop", "ArcadeBakeryShop"}
FQ_IRON_GALLERY = {"GalleryGreystoneRow", "GalleryCafeShop"}

def fq_dress(S, k):
    """colourway B: second-floor French doors on individual wrought-iron balconies; C: one continuous balcony
    (wrapping the cut corner on corner shops). Galleries go cast iron in B and C. A stays as GPT specced."""
    S = copy.deepcopy(S)
    if k == 0:
        return S
    d = S["design"]
    if d in FQ_IRON_GALLERY:
        S["iron_gallery"] = True
    if d not in FQ_BALCONY or len(S["datums"]) < 2:
        return S
    z1 = S["datums"][1]
    nxt = S["datums"][2] if len(S["datums"]) > 2 else S["eave"]
    top = min(z1 + 2.50, nxt - .50)
    S["fq"] = "single" if k == 1 else "continuous"
    for o in S["front"] + [o for o in S["sides"] if o["side"] == "C"]:
        if o["k"] == "W" and o["floor"] == 1:
            o.update(k="F", b=z1 + .02, t=top)
            if not o["shutter"]:
                o["shutter"] = S["door"]
    return S

# ------------------------------------------------------------------ per-design features
def door_walks(h, S, skip=()):
    """front walks for ground-floor front doors that no stoop/stair handles"""
    for o in S["front"]:
        if o["k"] == "D" and o["floor"] == 0 and o["c"] not in skip:
            walk_to(h, X(o["c"]), Y(S["walls"][2]), min(1.0, o["w"]))

def st(h, S, xa, xb, **kw):
    """stoop on the front wall at a datum-0 door; walk to the street"""
    y0 = stoop(h, X(xa), X(xb), Y(S["walls"][2]), S["datums"][0], **kw)
    walk_to(h, X((xa + xb) / 2), y0, min(1.0, xb - xa))

def F_FirewallBrickRow(h, S):
    st(h, S, .66, 2.04)

def F_LeftCornerCurvePlex(h, S):
    p = Path2([("line", (X(4.95), Y(.62)), (X(3.10), Y(.62))),
               ("arc", (X(3.10), Y(1.92)), 1.30, -math.pi / 2, -math.pi)])
    flight(h, p, 0.0, 3.15, 17, .96)
    landing(h, X(1.25), X(2.35), Y(1.92), Y(2.95), 3.15)
    if h.lod < 2:
        railing(h, X(1.25), Y(1.92), X(1.25), Y(2.93), 3.15, .95, "Iron")
    walk_to(h, X(4.95), Y(.62) - .1)
    st(h, S, 6.10, 7.50)

def F_RightStairPlex(h, S):
    iron_stair(h, X(6.30), X(2.65), Y(1.45), Y(2.43), 3.06, 17)
    landing(h, X(6.30), X(7.45), Y(1.45), Y(3.0), 3.06)
    if h.lod < 2:
        railing(h, X(6.30), Y(1.45), X(7.45), Y(1.45), 3.06, .95, "Iron")
        railing(h, X(7.45), Y(1.45), X(7.45), Y(2.98), 3.06, .95, "Iron")
        dict(zip(["front"], [Face((-4, Y(3)), (4, Y(3)))]))["front"].trim(h.body, 0, 8, 3.08, 3.22, 0, .05, "Dressed")
    walk_to(h, X(2.40), Y(1.45))
    st(h, S, .45, 1.75)

def F_ReturnStairPlex(h, S):
    flight(h, Path2([("line", (X(2.95), Y(.48)), (X(2.95), Y(2.70)))]), 0, 1.64, 9, .96)
    landing(h, X(2.42), X(3.48), Y(2.70), Y(3.76), 1.64)
    flight(h, Path2([("line", (X(3.48), Y(3.23)), (X(6.02), Y(3.23)))]), 1.64, 3.47, 10, .96)
    landing(h, X(6.02), X(7.08), Y(2.70), Y(4.10), 3.47)
    if h.lod < 2:
        railing(h, X(6.02), Y(2.70), X(7.08), Y(2.70), 3.47, .95, "Iron")
        railing(h, X(7.08), Y(2.70), X(7.08), Y(4.08), 3.47, .95, "Iron")
        f = Face((-4, Y(4.1)), (4, Y(4.1)))
        for x in (3.7, 5.0):
            f.trim(h.body, x - .22, x + .22, .18, .37, 0, .01, "Iron")
    walk_to(h, X(2.95), Y(.48))
    st(h, S, .47, 1.87)

def F_RearGalleryTriplexRow(h, S):
    st(h, S, .5, 3.35)
    if h.lod < 2:
        h.body.box(X(1.9) - .02, X(1.9) + .02, Y(1.4), Y(2.4), .1, S["datums"][0] + .92, "Iron")
    walk_to(h, X(2.65), Y(1.5))
    yb = Y(17.4)
    gallery(h, X(.80), X(7.20), yb, Y(19.05), S["datums"], roof=None, post_mat="Iron", base=None, plain=True)   # alley side: plain iron
    if h.lod < 2:                                                          # R5: stair between the decks
        for z0, z1 in zip(S["datums"], S["datums"][1:]):
            flight(h, Path2([("line", (X(7.0), Y(18.6)), (X(3.6), Y(18.6)))]), z0, z1, 16, .70)

def F_OrielGreystoneRow(h, S):
    bay(h, X(4.95), Y(S["walls"][2]), 3.31, 6.14, S["datums"][1], oriel=True, cap_face=6.14, cap_wall=6.34, mat="Greystone")
    st(h, S, .68, 2.08)
    if h.lod < 2:
        f = Face((-4, Y(S["walls"][2])), (4, Y(S["walls"][2])))
        f.trim(h.body, 1.38 - .66, 1.38 - .50, .62, 2.72, 0, .04, "Dressed")
        f.trim(h.body, 1.38 + .50, 1.38 + .66, .62, 2.72, 0, .04, "Dressed")
        f.trim(h.body, 1.38 - .66, 1.38 + .66, 2.72, 2.92, 0, .05, "Dressed")

def F_RockfaceRow(h, S):
    st(h, S, 3.17, 4.83)
    if h.lod == 0:
        f = Face((-4, Y(S["walls"][2])), (4, Y(S["walls"][2])))
        z, i = .45, 0
        while z + .27 <= 6.2:
            w = .24 if i % 2 else .36
            f.trim(h.body, 0, w, z, z + .27, 0, .03, "Dressed")
            f.trim(h.body, 8 - w, 8, z, z + .27, 0, .03, "Dressed")
            z += .27; i += 1

def F_GalleryGreystoneRow(h, S):
    yw = Y(3.35)
    gallery(h, X(.35), X(7.65), yw, Y(1.75), [.47, 3.49], roof=(6.12, 5.80, "Tin"), gap=(X(6.0), X(6.96)),
            post_mat="Iron" if S.get("iron_gallery") else "Cream")
    for k in range(3):
        h.body.box(X(6.0), X(6.96), Y(1.75) - (3 - k) * .27, Y(1.75), k * .157, (k + 1) * .157, "Dressed", bottom=False)
    walk_to(h, X(6.48), Y(1.75) - .81)

def F_FaubourgRow(h, S):
    st(h, S, 5.3, 6.6)

def F_CarriageArchRow(h, S):
    st(h, S, 6.00, 7.30)
    if h.lod < 2:
        Face((-4, Y(2.2)), (4, Y(2.2))).trim(h.body, 0, 8, 6.95, 7.07, 0, .055, "Dressed")
    walk_to(h, X(1.92), Y(2.2), 2.3)

def F_TinParapetRow(h, S):
    st(h, S, 3.29, 4.81)
    m, yf = h.body, Y(2.05)
    m.box(X(2.30), X(5.70), yf, yf + .22, 9.48, 9.77, "BuffBrick", bottom=False)
    m.box(X(2.25), X(5.75), yf - .03, yf + .25, 9.77, 9.84, "Dressed", bottom=False)
    m.box(X(3.12), X(4.88), yf, yf + .22, 9.84, 10.06, "BuffBrick", bottom=False)
    m.box(X(3.07), X(4.93), yf - .03, yf + .25, 10.06, 10.13, "Dressed", bottom=False)
    if h.lod < 2:
        Face((-4, yf), (4, yf)).trim(m, 3.45, 4.55, 9.32 - .3, 9.62 - .3, 0, .02, "Greystone")

def F_SteppedBayRow(h, S):
    bay(h, X(2.65), Y(S["walls"][2]), 0, 3.26, S["datums"][0], mat="Brick097")
    st(h, S, 5.55, 7.05)
    if h.lod < 2:
        f = Face((-4, Y(S["walls"][2])), (4, Y(S["walls"][2])))
        f.trim(h.body, 0, 2.65 - 1.15, 3.34, 3.45, 0, .05, "Cream")
        f.trim(h.body, 2.65 + 1.15, 8, 3.34, 3.45, 0, .05, "Cream")

def F_RaisedCottageRow(h, S):
    st(h, S, 3.24, 4.76, rails=True)

def F_BellcastDouble(h, S):
    yw = Y(3.25)
    gallery(h, X(1.0), X(6.98), yw, Y(1.8), [.43], roof=(3.10, 2.90, "Tin"), base="StoneBase",
            gap=(X(1.29), X(3.59)))
    for xc in (1.78, 3.10):
        for k in range(2):
            h.body.box(X(xc) - .49, X(xc) + .49, Y(1.8) - (2 - k) * .27, Y(1.8), k * .215, (k + 1) * .215, "Dressed", bottom=False)
        walk_to(h, X(xc), Y(1.8) - .54, .98)

def F_TwoChimneyStoneCottage(h, S):
    st(h, S, 3.25, 4.75)

def F_SideGalleryCreoleCottage(h, S):
    st(h, S, 4.88, 6.22)
    m = h.body
    gx0, gx1, ya, yb = X(5.84), X(7.18), Y(6.2), Y(11.95)
    m.box(gx0, gx1, ya, yb, 0, .33, "Rubble", bottom=False)
    m.box(gx0, gx1, ya, yb, .33, .49, "Deck", bottom=False)
    e = S["eave"]
    for y in (6.29, 9.06, 11.86):
        m.box(X(7.06) - .07, X(7.06) + .07, Y(y) - .07, Y(y) + .07, .49, e, "Cream", bottom=False)
    if h.lod < 2:
        railing(h, X(7.06), Y(6.95), X(7.06), Y(11.86), .49, .92, "Cream", .16)
    m.polygon([(gx0, ya, e), (gx1, ya, e), (gx1, yb, e), (gx0, yb, e)], DOWN, SOFFIT)
    # gable fill above the open gallery side
    R = parse_roof(S)
    P = [(Y(y), z) for y, z in R["P"]]
    pts = [(gx1, ya, e)] + [(gx1, y, z) for y, z in P if ya < y < yb] + [(gx1, yb, profile_z(P, yb)), (gx1, yb, e)]
    pts.insert(1, (gx1, ya, profile_z(P, ya)))
    m.polygon(pts, (1, 0, 0), "Clapboard")
    for k in range(3):
        m.box(X(5.93), X(6.91), Y(5.36) + k * .28, ya, k * .163, (k + 1) * .163, "Dressed", bottom=False)
    walk(h, X(7.22), X(7.85), Y(5.36))

def F_TwoDormerCreoleCottage(h, S):
    gallery(h, X(.72), X(7.28), Y(3.72), Y(1.89), [.56], roof=None, gap=(X(3.5), X(4.6)), stairs_x=X(4.05))
    m = h.body
    R = S["front_kick"]
    post_top = profile_z([(Y(y), z) for y, z in R + parse_roof(S)["P"]], Y(1.99))
    for x in (.80, 2.6, 5.5, 7.20):
        m.box(X(x) - .07, X(x) + .07, Y(1.99) - .07, Y(1.99) + .07, .56, post_top, "Cream", bottom=False)
    walk_to(h, X(4.05), Y(1.89) - 3 * .27)

def F_ClapboardFaubourgHouse(h, S):
    st(h, S, 1.17, 2.53)
    shed(h, "x", X(1.07), X(2.62), Y(3.24), Y(2.12), 2.97, 2.70, S["roof_mat"])
    for x in (1.12, 2.57):
        h.body.box(X(x) - .05, X(x) + .05, Y(2.17) - .05, Y(2.17) + .05, S["datums"][0], 2.70, "Cream", bottom=False)

def F_MaisonCarreeHouse(h, S):
    st(h, S, 3.17, 4.83)
    if h.lod < 2:
        x0, x1, yf, yb = [X(S["walls"][0]), X(S["walls"][1]), Y(S["walls"][2]), Y(S["walls"][3])]
        for f in edges(rectangle(x0, x1, yf, yb)):
            f.trim(h.body, 0, .23, .52, S["eave"] - .24, 0, .03, "Dressed")
            f.trim(h.body, f.length - .23, f.length, .52, S["eave"] - .24, 0, .03, "Dressed")

def F_ShotgunGalleryHouse(h, S):
    gallery(h, X(.84), X(7.16), Y(3.45), Y(1.82), [.44], roof=(3.43, 3.03, S["roof_mat"]),
            posts=[X(1.05), X(2.95), X(5.05), X(6.95)], gap=(X(3.45), X(4.55)), stairs_x=X(4.0))     # R2
    walk_to(h, X(4.0), Y(1.82) - 3 * .27)

def F_OchreShutterHouse(h, S):
    st(h, S, 5.20, 6.64, landing=1.22, tread=.28)
    walk(h, X(.12), X(.77), Y(12.0))

def F_GableDormerBrickHouse(h, S):
    st(h, S, 1.28, 2.80)

def F_SageSaltboxHouse(h, S):
    st(h, S, 3.30, 4.76)

def F_LowPavilionCottage(h, S):
    st(h, S, 2.58, 5.42, flare=.22)
    if h.lod < 2:
        for f in edges(rectangle(X(.76), X(7.24), Y(4.65), Y(13.2))):
            f.trim(h.body, 0, f.length, 3.30, 3.42, 0, .04, "Dressed")

def corner_door_walk(h, S):
    for n, f in []:
        pass

def F_LeftCornerEpicerieStore(h, S):
    lantern(h, X(4.12), Y(6.35), .55, 9.84, 10.94, 11.40)
    fascia(h, S, 2.98, 3.39)
    walk(h, X(.25), X(1.6), Y(2.12) + .3)

def F_RightCornerTinStore(h, S):
    fascia(h, S, 2.76, 3.14)
    band(h, S, 3.45, 3.57)
    walk(h, X(6.4), X(7.75), Y(1.82) + .3)

def F_LeftCornerTavernShop(h, S):
    fascia(h, S, 2.73, 3.12)
    shed(h, "x", X(1.90), X(7.65), Y(2.88), Y(2.88) - .75, 3.06, 2.76, "TinOxide")
    shed(h, "y", Y(5.12), Y(7.61), X(.25), X(.25) - .22, 3.06, 2.86, "TinOxide")
    walk(h, X(.25), X(1.7), Y(2.88) + .3)

def F_RightCornerPharmacieShop(h, S):
    fascia(h, S, 3.03, 3.46)
    m = h.body
    if S.get("fq"):                                   # B/C: the wrought-iron balcony replaces the specced one
        walk(h, X(6.4), X(7.75), Y(2.4) + .3)
        return
    m.box(X(3.21), X(7.11), Y(1.76), Y(2.40), 4.46 - .13, 4.46, "Iron")
    if h.lod < 2:
        railing(h, X(3.21), Y(1.79), X(7.11), Y(1.79), 4.46, .95, "Iron", .12)
        for x in (3.24, 7.08):
            railing(h, X(x), Y(1.79), X(x), Y(2.38), 4.46, .95, "Iron", .12)
    walk(h, X(6.4), X(7.75), Y(2.4) + .3)

def F_GalleryCafeShop(h, S):
    gallery(h, X(.30), X(7.70), Y(3.60), Y(1.66), [.12], roof=(3.28, 2.95, "TinOxide"), base=None,
            post_mat="Iron" if S.get("iron_gallery") else "Cream")
    walk_to(h, X(4.0), Y(1.66), 1.6)

def F_BuffBrickMansardShop(h, S):
    fascia(h, S, 3.04, 3.40)
    if h.lod < 2:
        f = Face((-4, Y(1.62)), (4, Y(1.62)))
        for x in (.74 + 4.5 / 3, .74 + 9.0 / 3):
            f.trim(h.body, x - .043, x + .043, .43, 2.93, -.12, -.06, "Green")
        for x in (.66, 5.32):
            f.trim(h.body, x - .08, x + .08, 0, 3.04, 0, .05, "Oxblood")
    door_walks(h, S)

def F_ShutterRenderShop(h, S):
    fascia(h, S, 2.77, 3.10)
    shed(h, "x", X(.50), X(1.98), Y(2.27), Y(2.27) - .55, 2.70, 2.53, "Tin")
    door_walks(h, S)

def F_ArcadeBakeryShop(h, S):
    fascia(h, S, 3.19, 3.48, (.5, 7.5))
    shed(h, "x", X(6.03), X(7.43), Y(2.48), Y(2.48) - .48, 2.95, 2.78, "TinFlat")
    if h.lod < 2:
        Face((-4, Y(2.48)), (4, Y(2.48))).trim(h.body, 3.2, 4.8, 3.22, 3.45, 0, .09, "Cream")
    door_walks(h, S)

def fascia(h, S, z0, z1, span=None):
    if h.lod == 2:
        return
    x0, x1, yf, yb = S["walls"]
    f = Face((X(x0), Y(yf)), (X(x1), Y(yf)))
    a, b = span if span else (0, f.length)
    c = S.get("chamfer", 0)
    if S["access"] == "LeftCorner":
        a = max(a, c)
    if S["access"] == "RightCorner":
        b = min(b, f.length - c)
    f.trim(h.body, a, b, z0, z1, 0, .07, "Green")

def band(h, S, z0, z1):
    if h.lod == 2:
        return
    x0, x1, yf, yb = S["walls"]
    Face((X(x0), Y(yf)), (X(x1), Y(yf))).trim(h.body, 0, X(x1) - X(x0), z0, z1, 0, .05, "Dressed")

FEATURES = {k[2:]: v for k, v in globals().items() if k.startswith("F_")}

def prepare(specs):
    """per-design data the generic builder needs beyond the sheets"""
    specs["LeftCornerEpicerieStore"]["chamfer"] = 1.25
    specs["RightCornerTinStore"]["chamfer"] = 1.25
    specs["LeftCornerTavernShop"]["chamfer"] = 1.40
    specs["RightCornerPharmacieShop"]["chamfer"] = 1.30
    specs["FirewallBrickRow"]["firewall"] = .35
    specs["RaisedCottageRow"]["dormer_cheek"] = "Cream"
    specs["GableDormerBrickHouse"]["dormer_sashes"] = [(-.41, .66), (.41, .66)]
    specs["TwoDormerCreoleCottage"]["front_kick"] = [(1.74, 3.28)]
    cb = specs["CarriageArchRow"]
    o = Opening(1.92, 2.32, .20, 3.15, "leaf"); o.spring, o.depth, o.surround = 2.52, .24, .18
    cb["arches"] = [("front", o)]
    ab = specs["ArcadeBakeryShop"]
    ab["arches"] = []
    for c in (1.78, 4.13):
        o = Opening(c, 1.91, .48, 3.05, "glass"); o.spring, o.depth, o.surround = 2.51, .12, .13
        ab["arches"].append(("front", o))
    sg = specs["SideGalleryCreoleCottage"]
    x0, x1, yf, yb = sg["walls"]
    sg["plan_spec"] = [(x0, yf), (x1, yf), (x1, 6.2), (5.84, 6.2), (5.84, 11.95), (x1, 11.95), (x1, yb), (x0, yb)]
    sg["plan_names"] = ["front", "right", "right_end1", "right_recess", "right_end2", "right2", "rear", "left"]
    return specs


# ------------------------------------------------------------------ 1x6 lots: back buildings, courtyard walls, widening
# Everything is still built in the old 1x3 frame (street at blender y -12); nf_build moves it forward at export, so
# the rear lot line of the 1x6 lot sits at blender y +36 here.
LB = -12.0 + 8.0 * nb.LOT_D
LIM = 3.98
LOW_MARGIN = .25            # low-density houses widened to 0.25 m off each side line: 0.5 m between neighbours

def widen_map(x0, x1, m=LOW_MARGIN):
    """spec x -> spec x: the walls x0..x1 move out to m..8-m; whatever sat outside them is squeezed into the margin"""
    def f(a):
        if a <= x0:
            return a * m / x0
        if a >= x1:
            return 8 - (8 - a) * m / (8 - x1)
        return m + (a - x0) * (8 - 2 * m) / (x1 - x0)
    return f

def tris(m):
    return sum(len(f) - 2 for f in m.faces)

def back_building(h, x0, x1, y0, y1, eave, roof, wall_m, base_m, roof_m, wins=(), door=None, attached=False,
                  storeys=1, datum=.3, pitch=16, door_w=1.0, plain=False):
    """a plain back building, blender coords. roof: shedL / shedR (high side left / right), shedF (high at the
    back), gableX (ridge across the lot), gableY (ridge along it) or flat. Windows on the faces in wins, a door on
    the face named by door; the face against the house is left out when attached."""
    m = h.body
    plan = rectangle(x0, x1, y0, y1)
    names = ["front", "right", "rear", "left"]
    oh = .22
    ohl = 0.0 if x0 <= -LIM + .05 else min(oh, x0 + LIM)       # eaves never cross the lot line
    ohr = 0.0 if x1 >= LIM - .05 else min(oh, LIM - x1)
    ohf = 0.0 if attached else oh
    ohb = max(0.0, min(oh, LB - .03 - y1))
    t = math.tan(math.radians(pitch))
    cap = "Cream"
    breaks = lambda f: []
    if roof in ("shedL", "shedR"):
        z = (lambda x: eave + (x1 - x) * t) if roof == "shedL" else (lambda x: eave + (x - x0) * t)
        Q = [(x0 - ohl, z(x0 - ohl)), (x1 + ohr, z(x1 + ohr))]
        slab_y(m, Q, y0 - ohf, y1 + ohb, roof_m, cap)
        zfn = lambda x, y: z(min(max(x, x0), x1))
        top_z = max(z(x0 - ohl), z(x1 + ohr)) + T
    elif roof == "gableY":
        xc = (x0 + x1) / 2
        rz = eave + (xc - x0) * t
        Q = [(x0 - ohl, eave - ohl * t), (xc, rz), (x1 + ohr, eave - ohr * t)]
        slab_y(m, Q, y0 - ohf, y1 + ohb, roof_m, cap)
        zfn = lambda x, y: profile_z(Q, min(max(x, x0), x1))
        breaks = lambda f: [(xc - f.a.x) / f.tangent.x] if abs(f.tangent.x) > .5 else []
        top_z = rz + T
    elif roof in ("gableX", "shedF", "shedB"):
        if roof == "shedB":                                     # long addition: falls gently from the house
            t = min(t, .9 / max(1.0, y1 - y0))
            P = [(y0 - ohf, eave + (y1 - y0 + ohf) * t), (y1 + ohb, eave - ohb * t)]
            breaks = lambda f: []
        elif roof == "gableX":
            yc = (y0 + y1) / 2
            rz = eave + (yc - y0) * t
            P = [(y0 - ohf, eave - ohf * t), (yc, rz), (y1 + ohb, eave - ohb * t)]
            breaks = lambda f: [(yc - f.a.y) / f.tangent.y] if abs(f.tangent.y) > .5 else []
        else:
            P = [(y0 - ohf, eave - ohf * t), (y1 + ohb, eave + (y1 + ohb - y0) * t)]
        slab_x(m, P, x0 - ohl, x1 + ohr, roof_m, cap)
        zfn = lambda x, y: profile_z(P, min(max(y, y0), y1))
        top_z = max(z for _, z in P) + T
    else:                                                       # flat with a parapet
        cz = eave + .35
        inner = offset_plan(plan, [-.22] * 4)
        m.polygon([(x, y, eave) for x, y in inner], UP, "TinFlat")
        for (a, b), (ia, ib) in zip(zip(plan, plan[1:] + plan[:1]), zip(inner, inner[1:] + inner[:1])):
            m.polygon([(*a, cz), (*b, cz), (*ib, cz), (*ia, cz)], UP, "Dressed")
            nrm = (-(b[1] - a[1]), b[0] - a[0], 0)
            m.polygon([(*ia, eave), (*ib, eave), (*ib, cz), (*ia, cz)], nrm, wall_m)
        zfn = lambda x, y: cz
        top_z = cz
    bands = [(0, max(datum, .12), base_m), (max(datum, .12), 99, wall_m)]
    for n, f in zip(names, edges(plan)):
        # the face against the house is kept too: where the addition rises above a low eave it is the only cover
        top = top_line(f, zfn, breaks(f), f.length)
        wall_top = min(z for _, z in top)
        ops = []
        if not plain:
            L = f.length
            dz = None
            if n == door:
                house_end = 0.0 if (attached and abs(f.tangent.y) > .5 and abs(f.a.y - y0) < 1e-6) else \
                            L if (attached and abs(f.tangent.y) > .5) else L / 2
                dc = min(max(house_end + (1.0 if house_end == 0 else -1.0 if house_end == L else 0), door_w / 2 + .35),
                         L - door_w / 2 - .35)
                if L >= door_w + .7 and datum + 2.2 < wall_top - .1:
                    ops.append(Opening(dc, door_w, datum, datum + 2.1, "door"))
                    dz = (dc - door_w / 2 - .25, dc + door_w / 2 + .25)
            if n in wins:
                nwin = max(1, int((L - .6) / 2.5))
                for st_ in range(storeys):
                    zb = datum + st_ * 2.9
                    if zb + 2.2 > wall_top - .15:
                        continue
                    for i in range(nwin):
                        u = L * (i + .5) / nwin
                        if st_ == 0 and dz and dz[0] < u + .45 and u - .45 < dz[1]:
                            continue
                        if .55 < u < L - .55:
                            ops.append(Opening(u, .84, zb + .9, zb + 2.2, "sash"))
        poly_wall(h, f, top, bands, ops)
    m.polygon([(x, y, .02) for x, y in plan], DOWN, base_m)
    return top_z

def wall_run(h, x0, x1, y0, y1, height, mat, coping=True):
    """garden / courtyard wall or board fence (no coping) between two corners, axis-aligned"""
    if x1 - x0 < .05 or y1 - y0 < .05:
        return
    h.body.box(x0, x1, y0, y1, 0, height, mat, bottom=False)
    if coping:
        h.body.box(x0 - .03 if x0 > -LIM else x0, x1 + .03 if x1 < LIM else x1, y0 - .03 if y0 > -11 else y0,
                   min(y1 + .03, LB - .005), height, height + .07, "Dressed", bottom=False)

def plan_rear(I, seed):
    """every random choice for the back of the lot, made once per building so all LODs agree. Toronto-style: the
    house runs deep with rear additions (often two storeys stepping down to one), a small garden, a lane building"""
    rnd = random.Random(seed)
    kind, bx0, bx1, byb = I["kind"], I["bx0"], I["bx1"], I["byb"]
    W = bx1 - bx0
    P = {"adds": [], "out": None}
    clutter = I["back"] > byb + .6
    two_ok = I["eave"] > 5.6 and len(I["datums"]) > 1
    # the lane building: garage / coach house / stable at the back lot line
    garage = True                                            # the author: lot coverage maximised at all times
    gd = rnd.uniform(5.0, 6.5) if garage else 0.0
    garden = rnd.uniform(2.0, 3.5)
    end = LB - .3 - (gd + .15 if garage else 0.0) - garden
    start = I["back"] + rnd.uniform(3.0, 4.5) if clutter else byb       # behind a rear gallery: a court first
    length = end - start
    if length < 4.0:
        end = start + 4.0; length = 4.0
    # widths: rows and shops mostly full width; houses keep a side yard
    widths = [W, W - .8, W - 1.6]                           # full width first; narrower only to clear windows
    sides = ["L", "R"]; rnd.shuffle(sides)
    split = length > 9.0 and rnd.random() < .7
    l1 = length * rnd.uniform(.4, .6) if split else length
    s1 = 2 if len(I["datums"]) > 1 else 1
    roof1 = rnd.choice(["flat", "flat", "shed"]) if s1 == 2 else \
        rnd.choice(["gableY", "shed"]) if kind == "low" else rnd.choice(["shed", "flat"])
    roof2 = rnd.choice(["shed", "flat", "shed"]) if kind != "low" else rnd.choice(["gableY", "shed", "flat"])
    pitch = lambda r: rnd.uniform(26, 34) if r == "gableY" else rnd.uniform(10, 16)
    p1, p2 = pitch(roof1), pitch(roof2)
    rmat = rnd.choice(["TinFlat", I["roof_m"]])

    def eave_for(st):
        if st == 2:
            e = min(I["datums"][1] + 2.75, I["eave"] - .3) if len(I["datums"]) > 1 else I["datums"][0] + 5.7
            return e
        return max(2.7, I["datums"][0] + 2.8)

    def roof_top(r, w, e, p):
        t = math.tan(math.radians(p))
        return (e + .9 if r == "shedB" else e + w * t if r.startswith("shed") else e + w / 2 * t if r == "gableY" else e + .35) + T

    first = None
    for w in widths:
        w = max(2.6, min(w, W))
        for side, rf, st in [(sd, rf, st) for st in dict.fromkeys([s1, 1]) for rf in dict.fromkeys([roof1, "flat"])
                             for sd in sides]:
            e = eave_for(st)
            if st == 2 and e < I["datums"][min(1, len(I["datums"]) - 1)] + 2.4:
                continue
            ex0, ex1 = (bx0, bx0 + w) if side == "L" else (bx1 - w, bx1)
            r = {"shed": "shedL" if side == "L" else "shedR"}.get(rf, rf)
            if r.startswith("shed") and w > 6.5:
                r = "shedB"                                  # wide additions: fall back to the garden instead
            top = roof_top(r, w, e, p1)
            if I.get("ell_top_max") and top > I["ell_top_max"] and not clutter:
                continue
            if not clutter and not all(not (xl < ex1 + .12 and xr > ex0 - .12) or tz <= e - .05 or bz >= top + .12
                                       for xl, xr, bz, tz in I["rear_ops"]):
                continue
            first = dict(x0=ex0, x1=ex1, y0=start, y1=start + l1, eave=e, roof=r, storeys=st, pitch=p1,
                         roof_m=rmat if r != "flat" else I["roof_m"], side=side, attached=not clutter)
            break
        if first:
            break
    if first:
        P["adds"].append(first)
        if split:                                            # the step down: one storey, same side, no wider
            w2 = first["x1"] - first["x0"]
            ex0, ex1 = (first["x0"], first["x0"] + w2) if first["side"] == "L" else (first["x1"] - w2, first["x1"])
            r = {"shed": "shedL" if first["side"] == "L" else "shedR"}.get(roof2, roof2)
            if r.startswith("shed") and w2 > 6.5:
                r = "shedB"
            e2 = eave_for(1)
            if roof_top(r, w2, e2, p2) > first["eave"] - .2 and first["storeys"] == 1:
                r = "flat"
            P["adds"].append(dict(x0=ex0, x1=ex1, y0=first["y1"], y1=end, eave=e2, roof=r, storeys=1, pitch=p2,
                                  roof_m=rmat if r != "flat" else I["roof_m"], side=first["side"], attached=True))
        for i, ad in enumerate(P["adds"]):
            last = i == len(P["adds"]) - 1
            wins = ["rear"] if last else []
            for fn, x in (("left", ad["x0"]), ("right", ad["x1"])):
                if abs(x) < 3.9 or kind == "low":
                    wins.append(fn)
            if not ad["attached"]:
                wins.append("front")
            ad["wins"] = tuple(wins)
            ad["door"] = "front" if not ad["attached"] else "rear" if last else None
        P["add_end"] = P["adds"][-1]["y1"]
    else:
        P["add_end"] = start if not clutter else I["back"] + .1
    if garage:
        ow = rnd.uniform(5.6, 7.52)
        side = rnd.choice(["L", "R", "C"])
        if side == "L":
            ox0 = -3.76; ox1 = ox0 + ow
        elif side == "R":
            ox1 = 3.76; ox0 = ox1 - ow
        else:
            c = rnd.uniform(-1, 1) * max(0, 3.76 - ow / 2)
            ox0, ox1 = c - ow / 2, c + ow / 2
        oy1 = LB - .26
        roof = rnd.choice(["gableX", "gableX", "gableY", "shedF", "flat"])
        P["out"] = dict(x0=ox0, x1=ox1, y0=oy1 - gd, y1=oy1, roof=roof, eave=rnd.uniform(2.6, 3.2),
                        pitch=rnd.uniform(28, 38) if roof.startswith("gable") else rnd.uniform(10, 16),
                        wall_m=rnd.choice([I["rear_m"], I["rear_m"], "Clapboard", "Rubble", "BrownBrick"]),
                        roof_m=rnd.choice([I["roof_m"], "TinFlat", "TinOxide"]),
                        door_w=2.5 if ow > 3.3 else 1.0, wins=("front",) if ow > 3.8 else ())
    P["wall_h"] = rnd.uniform(1.8, 2.3) if kind == "row" else 2.4 if kind == "shop" else rnd.uniform(1.4, 1.7)
    P["wall_m"] = rnd.choice([I["rear_m"], "Rubble", I["rear_m"]]) if kind != "low" else "Deck"
    P["gate"] = rnd.uniform(-2.6, 2.6)
    P["patio"] = rnd.uniform(1.8, 3.0)
    P["court"] = clutter
    return P

def rear_lot(h, I, P):
    m, lod = h.body, h.lod
    plain = lod == 1 or (lod == 0 and tris(m) > 9500)
    for ad in P["adds"]:
        if lod == 2:
            if tris(m) > 470:
                break
            hgt = ad["eave"] + (.35 if ad["roof"] == "flat" else .5)
            m.box(ad["x0"], ad["x1"], ad["y0"], ad["y1"], 0, hgt, I["rear_m"],
                  top="TinFlat" if ad["roof"] == "flat" else ad["roof_m"], bottom=False)
            continue
        back_building(h, ad["x0"], ad["x1"], ad["y0"], ad["y1"], ad["eave"], ad["roof"], I["rear_m"], I["base_m"],
                      ad["roof_m"], wins=ad["wins"], door=ad["door"], attached=ad["attached"],
                      storeys=ad["storeys"], datum=I["datums"][0], pitch=ad["pitch"], plain=plain)
    o = P["out"]
    if o:
        if lod == 2:
            if tris(m) <= 470:
                m.box(o["x0"], o["x1"], o["y0"], o["y1"], 0, o["eave"] + .4, o["wall_m"], top=o["roof_m"], bottom=False)
        else:
            back_building(h, o["x0"], o["x1"], o["y0"], o["y1"], o["eave"], o["roof"], o["wall_m"], "Rubble",
                          o["roof_m"], wins=o["wins"], door="rear", datum=.15, pitch=o["pitch"], door_w=o["door_w"],
                          plain=plain)
    if lod == 2:
        return
    # garden wall on the left side line and along the lane (one per boundary, since every lot does the same)
    masonry = I["kind"] != "low"
    th = .2 if masonry else .06
    adds = P["adds"]
    left_built = [ad for ad in adds if ad["x0"] <= -3.9]
    y_start = max([ad["y1"] for ad in left_built] + [I["byb"]]) if left_built else \
        (I["back"] + .1 if P["court"] else I["byb"])
    wall_run(h, -LIM, -LIM + th, y_start, LB - .02, P["wall_h"], P["wall_m"], masonry)
    gx = P["gate"]
    xs = [(-LIM + th, gx - .55), (gx + .55, LIM)]
    if o:
        xs = [(a, min(b, o["x0"] - .02)) for a, b in xs] + [(max(a, o["x1"] + .02), b) for a, b in xs]
    for a, b in xs:
        if b - a > .3:
            wall_run(h, a, b, LB - .02 - th, LB - .02, P["wall_h"], P["wall_m"], masonry)
    # paving: a patio at the garden door, a path to the lane building
    px0, px1 = -LIM + th + .02, LIM
    if I["kind"] == "low":
        px0, px1 = max(px0, I["bx0"]), min(px1, I["bx1"])
    py0 = P["add_end"]
    py1 = py0 + P["patio"]
    if px1 - px0 > .8:
        h.body.box(px0, px1, py0, py1, 0, .04, "Paving", bottom=False)
    if o and o["y0"] - py1 > .5:
        cx = (o["x0"] + o["x1"]) / 2
        h.body.box(cx - .45, cx + .45, py1, o["y0"], 0, .04, "Paving", bottom=False)
    if P["court"] and adds:                                   # paved court between the gallery and the back building
        h.body.box(-LIM + th + .02, LIM, I["back"] + .1, adds[0]["y0"], 0, .04, "Paving", bottom=False)

def rear_info(S=None, design=None):
    """what plan_rear needs about the main building, blender coords (call with XMAP already set)"""
    if S:
        x0, x1, yf, yb = S["walls"]
        fm, sm, rm, bm, tm = S["facade"]
        return dict(kind="low" if "Residential Low" in S["zone"] else "shop" if "Commercial" in S["zone"] else "row",
                    bx0=X(x0), bx1=X(x1), byb=Y(yb), eave=S["eave"], datums=S["datums"], rear_m=rm, base_m=bm,
                    roof_m=S["roof_mat"] if S["roof_mat"] != "TinFlat" else "Tin", roof_type=parse_roof(S)["type"],
                    rear_ops=[(X(o["c"]) - o["w"] / 2, X(o["c"]) + o["w"] / 2, o["b"], o["t"]) for o in S["rear"]])
    x0, x1, yf, yb, eave, kind, rm, rf, d0 = PILOT_INFO[design]
    return dict(kind=kind, bx0=X(x0), bx1=X(x1), byb=Y(yb), eave=eave, datums=[d0], rear_m=rm, base_m="StoneBase",
                roof_m=rf, roof_type="mansard", rear_ops=[], ell_flat=True, ell_top_max=3.9)

PILOT_INFO = {   # walls x0 x1 yf yb, eave, kind, rear wall, roof, ground datum (from the pilot builders in nf_build)
    "Plex": (0, 8, 3.0, 17.2, 6.42, "row", "Brick097", "Tin", .30),
    "GreystoneRow": (0, 8, 2.3, 17.3, 6.60, "row", "Brick094", "Slate", .48),
    "CreoleCottage": (.8, 7.2, 5.0, 14.0, 3.35, "low", "RenderSide", "Tin", .45),
    "GalleryShop": (0, 8, 2.25, 16.65, 6.66, "shop", "Brick097", "Tin", .15),
    "RightCornerStore": (0, 7.75, 1.8, 16.2, 6.56, "shop", "Brick054", "Tin", .10),
}

def make_recipe(S, k=0, design=None, base=None):
    """main building (spec or pilot), then the back of the 1x6 lot; the rear plan is fixed at LOD0"""
    I, P = {}, {}
    def recipe(h):
        if base:
            d = base(h)
        else:
            d = build_spec(h, S)
            FEATURES.get(S["design"], lambda h, S: door_walks(h, S))(h, S)
        if not P:
            I.update(rear_info(S, design))
            I["back"] = max(v[1] for v in h.body.vertices)
            P.update(plan_rear(I, zlib.crc32(f"{design or S['design']}/{k}".encode())))
        rear_lot(h, I, P)
        return d
    return recipe

# ------------------------------------------------------------------ colour variants
FAMILIES = [
    ["Brick097", "Brick094", "BuffBrick", "Brick085", "Brick074", "BrownBrick", "Brick054"],
    ["Slate", "SlateDark", "SlateGreen", "SlateBrown", "Tin", "TinOxide", "TinGreen"],
    ["Clapboard", "ClapSage"],
    ["Render", "RenderOchre", "RenderRose", "RenderGrey", "RenderSage"],
    ["Green", "Oxblood", "GreyBlue", "Black", "Mustard"],
    ["Greystone", "Ashlar"],
]
def variant_map(k):
    if k == 0:
        return {}
    remap = {}
    for fam, step in zip(FAMILIES, (2, 3, 1, 2, 2, 1)):
        for i, mname in enumerate(fam):
            remap[mname] = fam[(i + k * step) % len(fam)]
    remap["RenderSide"] = "RenderSide"
    return remap

# ------------------------------------------------------------------ run
def run(only=None, variants=3):
    specs = prepare(revise(load_specs()))
    designs = [(d, z, f, None) for d, z, f in nb.ASSETS] + [(d, S["zone"], None, S) for d, S in specs.items()]
    manifest, total = {}, 0
    for design, zone, base_recipe, spec in designs:
        if only and design not in only:
            continue
        for k in range(variants):
            recipe = make_recipe(fq_dress(spec, k), k) if spec else make_recipe(None, k, design, base_recipe)
            nb.XMAP = widen_map(*spec["walls"][:2]) if spec and "Residential Low" in spec["zone"] else None
            nb.REMAP.clear(); nb.REMAP.update(variant_map(k))
            name = f"NA_NewFrance{design}{'' if k == 0 else 'BC'[k - 1]}_L1_1x{nb.LOT_D}"
            folder = nb.OUT / name
            folder.mkdir(parents=True, exist_ok=True)
            rec = {"design": design, "variant": k, "zone": zone, "meshes": {}}
            for lod, suffix in enumerate(("", "_LOD1", "_LOD2")):
                nb.clear_objects()
                h = House(lod)
                try:
                    details = recipe(h)
                except Exception as err:
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
            if name != nb.OWNER:
                share = {f"{name}{l}_{kind}.png": f"../{nb.OWNER}/{nb.OWNER}{l}_{kind}.png"
                         for l in ("", "_LOD1", "_LOD2") for kind in nb.MAPS}
                (folder / "settings.json").write_text(json.dumps({"sharedAssets": share}, indent=2), encoding="utf-8")
            try:
                for path in sorted(folder.glob("*.fbx")):
                    rec["meshes"][path.stem.removeprefix(name) or "Main"] = nb.validate_export(
                        path, (8, 8 * nb.LOT_D), details, path.stem.endswith("_Win"))
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
    nb.REMAP.clear(); nb.XMAP = None
    mf = nb.HERE / "reports" / "manifest_round3.json"
    if only and mf.exists():                                 # partial rebake: merge into the full manifest
        manifest = {**json.loads(mf.read_text(encoding="utf-8")), **manifest}
    mf.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    bad = [n for n, r in manifest.items() if not r["ok"]]
    print(f"ROUND3 DONE {total} buildings, {len(bad)} failed", flush=True)

if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    v = 3
    if argv and argv[0].startswith("v="):
        v = int(argv.pop(0)[2:])
    run(set(argv) or None, v)
