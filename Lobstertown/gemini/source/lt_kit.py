"""Lobstertown building kit (Claude, 2026-11-14): New England shingle pieces on top of the New France kit.

Same frame as nf_kit: lot centre origin, street at -Y, z up, 4 mm air gaps (E) wherever parts touch.
The rulebook (nf_rules) still checks every wall; Shingle Style asymmetry is waived per wall with a reason.

  window/door      white casings, double-hung sash, optional shutters, panelled door with a transom
  wall             shingle facade: granite water table, white corner boards, frieze board, trim belts
  gable_wall       the triangle (or any profile) above an eave, with attic windows cut in
  gable_roof       a front-to-back gable with real thickness, rake boards and soffits
  porch            deck on a lattice skirt, turned posts, rail, shed roof and steps to the walk
  bay              a canted two-storey bay with its own windows and a hipped cap
"""
import math
from nf_kit import Mesh, Wall, lbox, wbox, band, holes_for, cuts_of, world_cuts, party, flat_roof, chimney, finish, E, UP
import nf_rules

TRIM = "TrimWhite"
__all__ = ["Mesh", "Wall", "wbox", "lbox", "party", "flat_roof", "chimney", "finish", "E", "UP",
           "style", "wall", "gable_wall", "gable_roof", "porch", "bay", "opening", "TRIM"]


# ---------------------------------------------------------------- openings

def opening(m, g, w, h, lod, trim):
    """Window or door in a wood-framed wall. trim: frame (sash and casing material), door (door colour),
    shutters (material or None), lites ('2' two-over-two or '6' six-over-six)."""
    u0, u1, zb, zt, kind = h
    P, n, t = w.P, w.n, w.t
    if kind == "shop":
        return shop_front(m, g, w, h, lod, trim)
    if kind == "bay":
        return loading_bay(m, g, w, h, lod, trim)
    if kind == "blind":                               # rule 28: no room behind, so a cased board panel, no glass
        if lod == 2:
            return
        frame = trim.get("frame", TRIM)
        jw = .14
        for q in ((u0 - jw, u0, zb - .10, zt + .18), (u1, u1 + jw, zb - .10, zt + .18),
                  (u0, u1, zt, zt + .18), (u0, u1, zb - .10, zb)):
            m.facing([P(q[0], q[2], .01), P(q[1], q[2], .01), P(q[1], q[3], .01), P(q[0], q[3], .01)], n, frame)
        if lod == 1:
            m.facing([P(u0, zb, .005), P(u1, zb, .005), P(u1, zt, .005), P(u0, zt, .005)], n, frame)
            return
        dep, f = .08, .10                             # the recess, then a raised (fielded) panel in it
        for a_, hint in ((u0, t), (u1, -t)):
            m.facing([P(a_, zb, 0), P(a_, zb, -dep), P(a_, zt, -dep), P(a_, zt, 0)], hint, frame)
        m.facing([P(u0, zt, 0), P(u1, zt, 0), P(u1, zt, -dep), P(u0, zt, -dep)], -UP, frame)
        m.facing([P(u0, zb, 0), P(u1, zb, 0), P(u1, zb, -dep), P(u0, zb, -dep)], UP, frame)
        m.facing([P(u0, zb, -dep), P(u1, zb, -dep), P(u1, zt, -dep), P(u0, zt, -dep)], n, frame)
        a0, a1, c0, c1, r = u0 + f, u1 - f, zb + f, zt - f, -dep + .04
        m.facing([P(a0, c0, r), P(a1, c0, r), P(a1, c1, r), P(a0, c1, r)], n, frame)
        m.facing([P(a0, c0, -dep), P(a0, c0, r), P(a0, c1, r), P(a0, c1, -dep)], -t, frame)
        m.facing([P(a1, c0, r), P(a1, c0, -dep), P(a1, c1, -dep), P(a1, c1, r)], t, frame)
        m.facing([P(a0, c1, r), P(a1, c1, r), P(a1, c1, -dep), P(a0, c1, -dep)], UP, frame)
        m.facing([P(a0, c0, -dep), P(a1, c0, -dep), P(a1, c0, r), P(a0, c0, r)], -UP, frame)
        return
    door = kind == "door"
    frame = trim.get("frame", TRIM)
    stone = trim.get("masonry")                       # brick walls (Cannery Row): stone lintel and sill, no casings
    rev = trim.get("reveal", frame) if stone else frame
    dmat = trim.get("door", "Green")
    la = trim.get("lite_above")                       # tower floors (Grand Hotels): seen from afar, built light
    if la is not None and not door and zb > la:
        if lod == 2:                                  # LOD2 budget: the tower reads by its belts and outline
            return
        if lod == 0:                                  # a real recess and glass, one flat white frame (~18 triangles)
            dep, jw = .12, .14
            for a_, hint in ((u0, t), (u1, -t)):
                m.facing([P(a_, zb, 0), P(a_, zb, -dep), P(a_, zt, -dep), P(a_, zt, 0)], hint, frame)
            m.facing([P(u0, zt, 0), P(u1, zt, 0), P(u1, zt, -dep), P(u0, zt, -dep)], -UP, frame)
            m.facing([P(u0, zb, 0), P(u1, zb, 0), P(u1, zb, -dep), P(u0, zb, -dep)], UP, frame)
            g.facing([P(u0, zb, -dep), P(u1, zb, -dep), P(u1, zt, -dep), P(u0, zt, -dep)], n, "Glass")
            for q in ((u0 - jw, u0, zb - .10, zt + .18), (u1, u1 + jw, zb - .10, zt + .18),
                      (u0, u1, zt, zt + .18), (u0, u1, zb - .10, zb)):
                m.facing([P(q[0], q[2], .01), P(q[1], q[2], .01), P(q[1], q[3], .01), P(q[0], q[3], .01)], n, frame)
            return
    flat = lod == 2 or (lod == 1 and trim.get("lean"))    # lean: LOD1 openings as panes on the wall face
    if flat:
        pane = [P(u0, zb, .02), P(u1, zb, .02), P(u1, zt, .02), P(u0, zt, .02)]
        (m if door else g).facing(pane, n, dmat if door else "Glass")
        if lod == 2:
            return
        if trim.get("lean") == "bare":
            jw = .14
            lo = 0.0 if door else zb - .10
            m.facing([P(u0 - jw, lo, .01), P(u1 + jw, lo, .01), P(u1 + jw, zt + .18, .01), P(u0 - jw, zt + .18, .01)],
                     n, frame)
            return
    dep = .16 if lod == 0 else .10
    for a, hint in (() if flat else ((u0, t), (u1, -t))):
        m.facing([P(a, zb, 0), P(a, zb, -dep), P(a, zt, -dep), P(a, zt, 0)], hint, rev)
    if not flat:
        m.facing([P(u0, zt, 0), P(u1, zt, 0), P(u1, zt, -dep), P(u0, zt, -dep)], -UP, rev)
    if not door and not flat:
        m.facing([P(u0, zb, 0), P(u1, zb, 0), P(u1, zb, -dep), P(u0, zb, -dep)], UP, stone or frame)
    um = (u0 + u1) / 2
    if flat:
        pass
    elif door:
        tr = zt - .45                                     # transom over a single panelled leaf
        m.facing([P(u0, zb, -dep), P(u1, zb, -dep), P(u1, tr, -dep), P(u0, tr, -dep)], n, dmat)
        g.facing([P(u0, tr, -dep), P(u1, tr, -dep), P(u1, zt, -dep), P(u0, zt, -dep)], n, "Glass")
        if lod == 0:
            b0 = -dep + .005
            lbox(m, w, u0 + E, u1 - E, tr - .04, tr + .04, b0, b0 + .05, frame)
            for p0, p1 in ((.35, tr * .45), (tr * .52, tr - .22)):
                lbox(m, w, u0 + .16, u1 - .16, p0, p1, b0, b0 + .03, dmat)
    else:
        g.facing([P(u0, zb, -dep), P(u1, zb, -dep), P(u1, zt, -dep), P(u0, zt, -dep)], n, "Glass")
        if lod == 0 and trim.get("simple"):               # one-over-one: just the meeting rail
            b0 = -dep + .005
            zm = (zb + zt) / 2
            lbox(m, w, u0 + E, u1 - E, zm - .035, zm + .035, b0, b0 + .04, frame)
        elif lod == 0:                                    # double-hung: sash frames, meeting rail, muntins
            b0 = -dep + .005
            zm = (zb + zt) / 2
            lbox(m, w, u0 + E, u0 + .06, zb + E, zt - E, b0, b0 + .04, frame)
            lbox(m, w, u1 - .06, u1 - E, zb + E, zt - E, b0, b0 + .04, frame)
            for za, zz in ((zb + E, zb + .07), (zm - .035, zm + .035), (zt - .06, zt - E)):
                lbox(m, w, u0 + .06 + E, u1 - .06 - E, za, zz, b0, b0 + .04, frame)
            lites = trim.get("lites", "2")
            lbox(m, w, um - .015, um + .015, zb + .07, zt - .06, b0, b0 + .03, frame)
            if lites == "6":
                for k in (1, 2):
                    c = u0 + (u1 - u0) * k / 3
                    lbox(m, w, c - .012, c + .012, zb + .07, zt - .06, b0, b0 + .03, frame)
                for zz in ((zb + zm) / 2, (zm + zt) / 2):
                    lbox(m, w, u0 + .06, u1 - .06, zz - .012, zz + .012, b0, b0 + .022, frame)
    if stone:                                             # masonry: a stone lintel and a stone sill
        lbox(m, w, u0 - .10, u1 + .10, zt, zt + .26, E, .05, stone)
        hood = trim.get("hood")                           # Main Street: an Italianate hood over the lintel
        if hood:
            zc = zt + .26 + E
            lbox(m, w, u0 - .2, u1 + .2, zc, zc + .09, E, .13, stone)          # the projecting cap
            if lod == 0:                                  # a console either side of the lintel, under the cap
                for a_, b_ in ((u0 - .19, u0 - .10 - E), (u1 + .10 + E, u1 + .19)):
                    lbox(m, w, a_, b_, zt - .32, zc - E, E, .11, stone)
            if hood == "pediment":                        # a low pediment on the cap
                za, zp, d = zc + .09 + E, zc + .09 + .34, .11
                a0, a1 = u0 - .16, u1 + .16
                m.facing([P(a0, za, d), P(a1, za, d), P(um, zp, d)], n, stone)
                m.facing([P(a0, za, 0), P(a0, za, d), P(um, zp, d), P(um, zp, 0)], UP - t, stone)
                m.facing([P(um, zp, 0), P(um, zp, d), P(a1, za, d), P(a1, za, 0)], UP + t, stone)
                m.facing([P(a0, za, 0), P(a1, za, 0), P(a1, za, d), P(a0, za, d)], -UP, stone)
        if not door:
            lbox(m, w, u0 - .08, u1 + .08, zb - .12, zb, E, .08, stone)
        return
    # flat casings, a capped head and a sill
    jw = .14
    lo = 0.0 if door else zb
    lbox(m, w, u0 - jw, u0, lo, zt, E, .05, frame, ("in", "top", "bot") if door else ("in", "top"))
    lbox(m, w, u1, u1 + jw, lo, zt, E, .05, frame, ("in", "top", "bot") if door else ("in", "top"))
    lbox(m, w, u0 - jw - .02, u1 + jw + .02, zt, zt + .18, E, .06, frame)
    if lod == 0 and not trim.get("simple"):
        lbox(m, w, u0 - jw - .05, u1 + jw + .05, zt + .18, zt + .22, E, .11, frame)
    if not door:
        lbox(m, w, u0 - jw - .02, u1 + jw + .02, zb - .10, zb, E, .09, frame)
    sh = trim.get("shutters")
    if sh and not door:
        sw = (u1 - u0) / 2
        for a, b in ((u0 - jw - .03 - sw, u0 - jw - .03), (u1 + jw + .03, u1 + jw + .03 + sw)):
            lbox(m, w, a, b, zb, zt, E, .045, sh, ("in",))
            if lod == 0:
                for k in range(1, 3):
                    zz = zb + (zt - zb) * k / 3
                    lbox(m, w, a + .03, b - .03, zz - .02, zz + .02, .045, .055, sh, ("in",))


def shop_front(m, g, w, h, lod, trim):
    """A wooden shopfront in a wide ground-floor opening: panelled stallrisers, plate glass with mullions and a
    transom bar, a glazed shop door at trim['shopdoor'] = (u0, u1). Painted in trim['door']."""
    u0, u1, zb, zt, _ = h
    P, n, t = w.P, w.n, w.t
    paint = trim.get("door", "Green")
    pane = lambda a, b, z0, z1, d: [P(a, z0, d), P(b, z0, d), P(b, z1, d), P(a, z1, d)]
    if lod == 2:
        g.facing(pane(u0, u1, 0, zt, .02), n, "Glass")
        return
    dep = .22 if lod == 0 else .12
    for a, hint in ((u0, t), (u1, -t)):
        m.facing([P(a, 0, 0), P(a, 0, -dep), P(a, zt, -dep), P(a, zt, 0)], hint, paint)
    m.facing([P(u0, zt, 0), P(u1, zt, 0), P(u1, zt, -dep), P(u0, zt, -dep)], -UP, paint)
    da, db = trim.get("shopdoor", ((u0 + u1) / 2 - .5, (u0 + u1) / 2 + .5))
    sr, tr = .6, zt - .55                                # stallriser top, transom bar
    for a, b, z0 in ((u0, da, sr), (db, u1, sr), (da, db, tr)):
        if b - a > .01:
            g.facing(pane(a, b, z0, zt, -dep), n, "Glass")
    m.facing(pane(da, db, 0, tr, -dep), n, paint)
    b0 = -dep
    for a, b in ((u0, da), (db, u1)):                    # stallrisers under the display windows
        if b - a > .01:
            m.facing(pane(a, b, 0, sr, -dep), n, paint)
    if lod == 0:
        for a, b in ((u0 + E, da - .06 - E), (db + .06 + E, u1 - E)):
            if b - a > .1:
                lbox(m, w, a, b, sr - .06, sr, b0, b0 + .08, TRIM, ("in",))              # sill of the display glass
                k = max(1, round((b - a) / 1.4))
                for i in range(k):                                                    # raised panels
                    pa, pb = a + (b - a) * i / k + .08, a + (b - a) * (i + 1) / k - .08
                    lbox(m, w, pa, pb, .12, sr - .14, b0, b0 + .03, paint, ("in",))
                for i in range(1, k):                                                 # mullions
                    c = a + (b - a) * i / k
                    lbox(m, w, c - .03, c + .03, sr + E, zt - E, b0, b0 + .06, paint, ("in",))
        for c in (da - .03, db + .03):                                                # door posts
            lbox(m, w, c - .03, c + .03, 0, zt - E, b0, b0 + .07, paint, ("in", "bot"))
        lbox(m, w, u0 + E, u1 - E, tr - .04, tr + .04, b0, b0 + .05, paint, ("in",))     # transom bar
        lbox(m, w, da + .12, db - .12, .15, .9, b0, b0 + .035, paint)                  # door: kick panel and light
        g.facing(pane(da + .12, db - .12, 1.05, tr - .15, b0 + .03), n, "Glass")


def loading_bay(m, g, w, h, lod, trim):
    """An open loading bay in a masonry wall (Cannery Row): a deep reveal in stone, a dark interior, a glazed
    fanlight over it (a round arch if trim['arch'], else a square transom), and close up a stone arch ring with a
    keystone (or a stone lintel). trim: masonry (stone), bay_wall (wall material of the spandrels), frame,
    glazed (Exchange Row: glass and a mullion below the fanlight instead of the dark doorway)."""
    u0, u1, zb, zt, _ = h
    P, n, t = w.P, w.n, w.t
    stone = trim.get("masonry", "Dressed")
    wallm = trim.get("bay_wall", stone)
    frame = trim.get("frame", "Black")
    arch = trim.get("arch")
    r, um = (u1 - u0) / 2, (u0 + u1) / 2
    zs = zt - r if arch else zt - .55                    # spring line (arch) or transom bar (square)
    if arch:
        k = 8 if lod == 0 else 4
        head = [(um - r * math.cos(math.pi * i / k), zs + r * math.sin(math.pi * i / k)) for i in range(k + 1)]
    else:
        k, head = 0, [(u0, zs), (u0, zt), (u1, zt), (u1, zs)]
    flat = lod == 2 or (lod == 1 and trim.get("lean"))
    if flat:                                             # the wall was not cut: dark doorway and fanlight as panes
        q = [P(u0, zb, .02), P(u1, zb, .02), P(u1, zs, .02), P(u0, zs, .02)]
        (g if trim.get("glazed") else m).facing(q, n, "Glass" if trim.get("glazed") else "Black")
        g.facing([P(a, z, .02) for a, z in head], n, "Glass")
        return
    if arch:                                             # spandrels: fill the cut rectangle's top corners
        m.facing([P(u0, zt, 0)] + [P(a, z, 0) for a, z in head[:k // 2 + 1]], n, wallm)
        m.facing([P(u1, zt, 0)] + [P(a, z, 0) for a, z in head[k // 2:][::-1]], n, wallm)
    dep = .45 if lod == 0 else .25
    ring = [(u0, zb)] + head + [(u1, zb)]                # clockwise seen from outside: inside is on the right
    for (a0, z0_), (a1, z1_) in zip(ring, ring[1:]):
        du, dz = a1 - a0, z1_ - z0_
        hint = t * dz - UP * du
        m.facing([P(a0, z0_, 0), P(a1, z1_, 0), P(a1, z1_, -dep), P(a0, z0_, -dep)], hint, stone)
    m.facing([P(u0, zb, 0), P(u1, zb, 0), P(u1, zb, -dep), P(u0, zb, -dep)], UP, stone)     # the sill
    q = [P(u0, zb, -dep), P(u1, zb, -dep), P(u1, zs, -dep), P(u0, zs, -dep)]
    if trim.get("glazed"):                              # Exchange Row: a glazed arched window, not an open bay
        g.facing(q, n, "Glass")
        if lod == 0:
            lbox(m, w, um - .03, um + .03, zb + E, zs - .05 - E, -dep + .005, -dep + .045, frame)
    else:
        m.facing(q, n, "Black")
    g.facing([P(a, z, -dep) for a, z in head], n, "Glass")
    if lod == 0:
        b0 = -dep + .005
        lbox(m, w, u0 + E, u1 - E, zs - .05, zs + .05, b0, b0 + .06, frame)          # transom bar
        lbox(m, w, um - .03, um + .03, zs + .05 + E, zt - .02, b0, b0 + .04, frame)    # fanlight bar
        if arch:                                         # stone arch ring, proud of the wall, and a keystone
            R2 = r + .24
            for i in range(k):
                c0, s0 = math.cos(math.pi * i / k), math.sin(math.pi * i / k)
                c1, s1 = math.cos(math.pi * (i + 1) / k), math.sin(math.pi * (i + 1) / k)
                pi0, pi1 = (um - r * c0, zs + r * s0), (um - r * c1, zs + r * s1)
                po0, po1 = (um - R2 * c0, zs + R2 * s0), (um - R2 * c1, zs + R2 * s1)
                m.facing([P(*pi0, .04), P(*pi1, .04), P(*po1, .04), P(*po0, .04)], n, stone)
                m.facing([P(*po0, E), P(*po1, E), P(*po1, .04), P(*po0, .04)],
                         t * -(po1[1] - po0[1]) + UP * (po1[0] - po0[0]), stone)
                m.facing([P(*pi0, E), P(*pi1, E), P(*pi1, .04), P(*pi0, .04)],
                         t * (pi1[1] - pi0[1]) - UP * (pi1[0] - pi0[0]), stone)
            for a, b in ((um - R2, um - r), (um + r, um + R2)):                     # ends on the spring line
                m.facing([P(a, zs, E), P(b, zs, E), P(b, zs, .04), P(a, zs, .04)], -UP, stone)
            lbox(m, w, um - .15, um + .15, zt - .06, zt + .30, .04 + E, .09, stone)
        else:
            lbox(m, w, u0 - .2, u1 + .2, zt, zt + .3, E, .05, stone)
    elif not arch:
        lbox(m, w, u0 - .2, u1 + .2, zt, zt + .3, E, .05, stone)


def surface(m, g, w, z0, z1, mats, holes, lod, trim, left=None, right=None):
    """Wall face from z0 to z1 with openings cut out. left/right: functions z -> u giving a sloped outline
    (gables, gambrels); breakpoints in the outline go in `knees`."""
    L = left or (lambda z: 0.0)
    R = right or (lambda z: w.L)
    cut = [] if lod == 2 or (lod == 1 and trim.get("lean")) else holes
    zs = {z0, z1} | {z for a, b, _ in mats for z in (a, b) if z0 < z < z1} | {z for h in cut for z in h[2:4] if z0 < z < z1}
    zs |= {z for z in trim.get("knees", ()) if z0 < z < z1}
    zs = sorted(zs)
    for za, zb in zip(zs, zs[1:]):
        mid = (za + zb) / 2
        mat = next(mm for a, b, mm in mats if a <= mid <= b)
        segs, u = [], None
        gaps = sorted((h[0], h[1]) for h in cut if h[2] <= mid <= h[3])
        edges = [("L", None)] + [(a, b) for a, b in gaps] + [("R", None)]
        for (a0, b0), (a1, b1) in zip(edges, edges[1:]):
            lo = (L(za), L(zb)) if a0 == "L" else (b0, b0)
            hi = (R(za), R(zb)) if a1 == "R" else (a1, a1)
            if hi[0] - lo[0] > 1e-4 or hi[1] - lo[1] > 1e-4:
                pts = [w.P(lo[0], za), w.P(hi[0], za), w.P(hi[1], zb), w.P(lo[1], zb)]
                if abs(hi[1] - lo[1]) < 1e-5:
                    pts = pts[:3]
                elif abs(hi[0] - lo[0]) < 1e-5:
                    pts = [pts[0], pts[2], pts[3]]
                m.facing(pts, w.n, mat)
    for h in holes:
        opening(m, g, w, h, lod, trim)


# ---------------------------------------------------------------- walls

def style(top, mats, win, belts=(), eave=.35, plinth=(.75, .05, "StoneBase"), corners=True, frieze=.30, low=(),
          belt_mat=TRIM):
    """A shingle facade. top: eave line. mats: wall materials by height. win: (width, sill, head) per floor.
    belts: floor heights with a white trim board. eave: overhang of the roof above (for the frieze/fascia).
    plinth: granite water table (height, proud, mat). corners: white corner boards at outside corners.
    belt_mat: material of the belts and frieze (white boards; stone string courses on brick)."""
    return dict(top=top, mats=mats, win=win, belts=tuple(belts), eave=eave, plinth=plinth, corners=corners,
                frieze=frieze, low=tuple(low), cornice=None, cap=None, rust=None, quoin_from=None, belt_mat=belt_mat)


def wall(m, g, st, A, B, s, e, bays, lod, door=None, z0=0.0, trim=None, waive=None, top=None, holes=(),
         frieze_on=True, plinth_cuts=(), omit=()):
    """A whole facade from A to B. s/e: 'x' outside corner, 'c' inside corner, '-' party-wall end.
    bays: world x (or y) of each window column; door = (bay, width, head). holes: extra openings in wall coords.
    top: override the wall top (a lower wing). plinth_cuts: world ranges kept clear of the water table (steps)."""
    w = Wall(A, B)
    trim = dict(dict(so=.16, key=False), **(trim or {}))
    zt = st["top"] if top is None else top
    H = [h for h in holes_for(w, bays, st["win"], door) if h[2] >= z0 - 1e-6 and h[3] <= zt - .2]
    for c, f in omit:                                  # (bay, floor) openings hidden behind a bay or porch
        u = w.u_of(c)
        H = [h for h in H if not (abs((h[0] + h[1]) / 2 - u) < .05 and abs(h[2] - st["win"][f][1]) < 1e-6)]
    H += list(holes)
    surface(m, g, w, z0, zt, st["mats"], H, lod, trim)
    if lod == 0:
        bands = []
        if st["plinth"] and z0 == 0:
            bands.append(("water table", 0.0, st["plinth"][0], cuts_of(H, .25, ("door", "shop"))))
        for z in st["belts"]:
            if z0 + .2 < z < zt - .2:
                bands.append(("trim belt", z - .06, z + .10, []))
        if frieze_on and st["frieze"]:
            bands.append(("frieze board", zt - st["frieze"], zt, []))
        nf_rules.check_wall(m, w, st, s, e, bays, H, door, z0, trim, False, bands, waive)
    if lod < 2:
        if st["plinth"] and z0 == 0:
            z1, p, mat = st["plinth"]
            band(m, w, 0.0, z1, p, mat, s, e, cuts_of(H, .16, ("door", "shop")) + world_cuts(w, plinth_cuts), skip=("in", "bot"))
        bm = st.get("belt_mat", TRIM)
        for z in st["belts"]:
            if z0 + .2 < z < zt - .2:
                band(m, w, z - .06, z + .10, .05, bm, s, e)
        if st["corners"]:
            for end, ty in ((0, s), (1, e)):
                if ty == "x":
                    a, b = (.055 + E, .235) if end == 0 else (w.L - .18, w.L + .055)
                    lo = max(z0, st["plinth"][0] if st["plinth"] else 0) + E
                    lbox(m, w, a, b, lo, zt - (st["frieze"] or 0) - E, E, .055, TRIM, ("in", "bot", "top"))
        if frieze_on and st["frieze"]:
            band(m, w, zt - st["frieze"], zt, .07, bm, s, e)
    return w


def gable_wall(m, g, A, B, z0, zr, lod, mat, wins=(), trim=None, shape=None):
    """The gable above an eave line at z0 between A and B, rising to zr at the middle. wins: (cx world, width,
    sill, head). shape: optional (z_knee, inset) pairs for a gambrel: the outline steps in by inset at z_knee."""
    w = Wall(A, B)
    trim = dict(dict(so=.16, key=False), **(trim or {}))
    half = w.L / 2
    if shape:                                           # gambrel: steep lower slope to the knee, then shallow
        zk, ik = shape
        def L(z):
            return ik * (z - z0) / (zk - z0) if z <= zk else ik + (half - ik) * (z - zk) / (zr - zk)
        trim["knees"] = (zk,)
    else:
        def L(z):
            return half * (z - z0) / (zr - z0)
    H = []
    for cx, wd, zb, zt in wins:
        u = w.u_of(cx)
        H.append((u - wd / 2, u + wd / 2, zb, zt, "win"))
    surface(m, g, w, z0, zr, [(z0, zr, mat)], H, lod, trim, left=L, right=lambda z: w.L - L(z))
    return w


# ---------------------------------------------------------------- roofs

def roof_check(m, t, what):
    """Rulebook rule 15 (closed construction): a roof slab is a closed solid. Every edge of `t` must be shared by
    exactly two of its faces; an edge used once is an open slab edge you can see daylight through. Then merge."""
    from collections import Counter
    c = Counter()
    for f in t.f:
        pts = [tuple(round(x, 4) for x in t.v[i]) for i in f]
        for a, b in zip(pts, pts[1:] + pts[:1]):
            if a != b:
                c[frozenset((a, b))] += 1
    bad = [tuple(e) for e, k in c.items() if k != 2]
    if bad:
        e = bad[0]
        nf_rules.rules_of(m).bad.append(
            f"Rule 15 (closed construction), {what}: {len(bad)} open edge(s), e.g. "
            + " - ".join("(%.2f, %.2f, %.2f)" % p for p in e))
    for f, k in zip(t.f, t.m):                           # merge into the building mesh
        pts = [t.v[i] for i in f]
        mat = t.mats[k]
        if mat not in m.mats:
            m.mats.append(mat)
        i = len(m.v)
        m.v += pts
        m.f.append(list(range(i, i + len(pts))))
        m.m.append(m.mats.index(mat))


def gable_roof(m, x0, x1, y0, y1, ze, zr, lod, mat="SlateDark", over=(.35, .35), sides=("p", "p"), th=.16,
               rake=TRIM, knee=None):
    """A gable with its ridge along y at the middle of x0..x1. over: overhang beyond y0 and y1 (rakes; a negative
    value stops short, for a wing butting into a wall). sides: 'p' the eave sits on a party line (no overhang),
    'e' an open eave that overhangs .35 m. knee: (z_knee, inset) makes it a gambrel.
    The slab is one closed solid at every LOD (rule 15): slopes top and bottom, both rake ends, both eave edges."""
    xm = (x0 + x1) / 2
    if knee:
        zk, ik = knee
        prof = [(x0, ze), (x0 + ik, zk), (xm, zr), (x1 - ik, zk), (x1, ze)]
    else:
        prof = [(x0, ze), (xm, zr), (x1, ze)]
    for idx, sd in ((0, sides[0]), (-1, sides[1])):     # open eaves run on down the first and last slope
        if sd == "e":
            (xa, za), (xb, zb) = (prof[0], prof[1]) if idx == 0 else (prof[-1], prof[-2])
            f = .35 / abs(xb - xa)
            prof[idx] = (xa - (xb - xa) * f, za - (zb - za) * f)
    ya, yb = y0 - over[0], y1 + over[1]
    t = Mesh()
    for (xa, za), (xb, zb) in zip(prof, prof[1:]):
        nx, nz = -(zb - za), (xb - xa)                  # outward (upward) normal of this slope in x-z
        if nz < 0:
            nx, nz = -nx, -nz
        t.facing([(xa, ya, za + th), (xb, ya, zb + th), (xb, yb, zb + th), (xa, yb, za + th)], (nx, 0, nz), mat)
        t.facing([(xa, ya, za), (xb, ya, zb), (xb, yb, zb), (xa, yb, za)], (-nx, 0, -nz), mat)
        for yy, d in ((ya, -1), (yb, 1)):
            t.facing([(xa, yy, za), (xb, yy, zb), (xb, yy, zb + th), (xa, yy, za + th)], (0, d, 0), rake)
    for idx, sd, sg in ((0, sides[0], -1), (-1, sides[1], 1)):   # eave edges: closed on party lines too
        xo, zo = prof[idx]
        t.facing([(xo, ya, zo), (xo, yb, zo), (xo, yb, zo + th), (xo, ya, zo + th)], (sg, 0, 0),
                 rake if sd == "e" else mat)
    roof_check(m, t, f"gable roof x {x0:.2f}..{x1:.2f}, y {y0:.2f}..{y1:.2f}")
    if lod == 0:
        for (xa, za), (xb, zb) in zip(prof, prof[1:]):     # rake boards under the overhanging ends
            for yy, d, o in ((ya, -1, over[0]), (yb, 1, over[1])):
                if o > 0:
                    y2 = yy - d * .05
                    m.facing([(xa, yy, za - .2), (xb, yy, zb - .2), (xb, yy, zb), (xa, yy, za)], (0, d, 0), rake)
                    m.facing([(xa, y2, za - .2), (xb, y2, zb - .2), (xb, yy, zb - .2), (xa, yy, za - .2)], (0, 0, -1), rake)
        wbox(m, xm - .09, xm + .09, ya + E, yb - E, zr + th - .02, zr + th + .07, mat, ("z-",))   # ridge cap


def shed_roof(m, x0, x1, y0, y1, z_high, z_low, lod, mat="SlateDark", fascia=TRIM, th=.12, high="y0"):
    """A lean-to roof between y0 and y1, high along one of them (against a wall), falling to the other (its eave).
    A closed slab (rule 15) with a fascia board standing proud of the eave edge."""
    za, zb = (z_high, z_low) if high == "y0" else (z_low, z_high)
    s = (za - zb) / (y1 - y0)
    d1 = 1 if y1 > y0 else -1                          # outward along y at the y1 edge
    t = Mesh()
    t.facing([(x0, y0, za + th), (x1, y0, za + th), (x1, y1, zb + th), (x0, y1, zb + th)], (0, s, 1), mat)
    t.facing([(x0, y0, za), (x0, y1, zb), (x1, y1, zb), (x1, y0, za)], (0, -s, -1), mat if lod == 2 else "Deck")
    for yy, zz, d in ((y0, za, -d1), (y1, zb, d1)):
        t.facing([(x0, yy, zz), (x1, yy, zz), (x1, yy, zz + th), (x0, yy, zz + th)], (0, d, 0), fascia)
    for xx, sg in ((x0, -1), (x1, 1)):
        t.facing([(xx, y0, za), (xx, y1, zb), (xx, y1, zb + th), (xx, y0, za + th)], (sg, 0, 0), fascia)
    roof_check(m, t, f"shed roof x {x0:.2f}..{x1:.2f}, y {y0:.2f}..{y1:.2f}")
    if lod < 2:
        ye, ze, d = (y1, zb, d1) if high == "y0" else (y0, za, -d1)
        a, b = sorted((ye + d * E, ye + d * .03))
        wbox(m, x0, x1, a, b, ze - .12, ze + th + .02, fascia, ("y+",) if d < 0 else ("y-",))


# ---------------------------------------------------------------- porches and bays

def porch(m, x0, x1, yw, depth, lod, zf=.79, zt=3.35, posts=None, mat="SlateDark", deck="Deck", stair=None,
          rail=True, open_sides=("l", "r"), roof=True, skirt=True):
    """A front porch against the wall at yw (facing -Y): deck at zf on a lattice skirt, square posts, a rail,
    a shed roof from zt at the wall. stair: (from x, to x) of the steps down to the walk.
    open_sides: which porch ends get a rail ('l', 'r'); an end on a party line stays closed by the neighbour."""
    yf = yw - depth
    posts = posts or [x0 + .15, x1 - .15]
    wbox(m, x0 + E, x1 - E, yf, yw - E, zf - .12 if skirt else 0.0, zf, deck, ("y+",))  # floor slab (a solid step)
    if lod < 2 and zf < 1.5 and skirt:
        wbox(m, x0 + .06, x1 - .06, yf + .06, yw - .1, 0.0, zf - .12 - E, "Black", ("y+", "z-", "z+"))  # dark skirt
    for px in posts:
        wbox(m, px - .09, px + .09, yf + .06, yf + .24, zf + E, zt - .2, TRIM, ("z-", "z+"))
        if lod == 0:
            wbox(m, px - .13, px + .13, yf + .02, yf + .28, zf + E, zf + .25, TRIM, ("z-",))
    if lod < 2:
        wbox(m, x0 + E, x1 - E, yf, yf + .30, zt - .2 + E, zt - .02, TRIM, ("y+", "z+"))   # porch beam
    if roof:
        shed_roof(m, x0, x1, yw - E, yf - .25, zt + .45, zt - .02, lod, mat)
    if rail and lod < 2:
        sx = stair or (0, 0)
        runs = [(a, b) for a, b in ((x0 + .2, sx[0] - .05), (sx[1] + .05, x1 - .2)) if b - a > .3] if stair else [(x0 + .2, x1 - .2)]
        for a, b in runs:
            wbox(m, a, b, yf + .10, yf + .20, zf + .85, zf + .92, TRIM)
            if lod == 0:
                k = int((b - a) / .14)
                for i in range(1, k):
                    c = a + (b - a) * i / k
                    if any(abs(c - px) < .13 for px in posts):
                        continue
                    wbox(m, c - .02, c + .02, yf + .13, yf + .17, zf + E, zf + .85 - E, TRIM, ("z-", "z+"))
        for side, xx in (("l", x0 + .15), ("r", x1 - .25)):
            if side in open_sides:
                wbox(m, xx, xx + .1, yf + .30, yw - .2, zf + .85, zf + .92, TRIM)
    if stair and lod < 2:
        a, b = stair
        k = max(2, round(zf / .19))
        for i in range(k):
            z = zf - (i + 1) * zf / k
            wbox(m, a, b, yf - (i + 1) * .28, yf - E - i * .28, 0.0, z + zf / k - E, "StoneBase", ("z-",))


def bay(m, g, cx, yw, width, proj, z0, z1, lod, mat, win, trim=None, roof="SlateDark", lites="2"):
    """A canted bay on a street wall at yw: front face width `width`, projecting `proj`, from z0 to z1.
    win: [(sill, head)] per floor; the front gets windows `front_w` wide, the cants narrower ones."""
    trim = dict(dict(so=.16, key=False, lites=lites), **(trim or {}))
    a = width / 2 + proj                          # half-width at the wall (45-degree cants)
    pts = [(cx - a, yw), (cx - width / 2, yw - proj), (cx + width / 2, yw - proj), (cx + a, yw)]
    faces = list(zip(pts, pts[1:]))
    for i, (A, B) in enumerate(faces):
        w = Wall(A, B)
        H = []
        for zb, zt in win:
            ww = min(w.L - .5, 1.0 if i == 1 else .62)
            H.append((w.L / 2 - ww / 2, w.L / 2 + ww / 2, zb, zt, "win"))
        surface(m, g, w, z0, z1, [(z0, z1, mat)], H, lod, trim)
        if lod < 2:
            band(m, w, z1 - .30, z1, .07, TRIM, "-", "-")
            if z0 < .8:
                band(m, w, 0.0, .72 if i == 1 else .735, .05, "StoneBase", "-", "-", skip=("in", "bot"))
    # hipped cap over the bay: a closed solid (rule 15) - two cants, the front slope, the soffit, the back
    zc = z1 + .02
    zr = zc + .55
    q = [(pts[0][0] - .12, yw - E, zc), (pts[1][0] - .07, pts[1][1] - .12, zc),
         (pts[2][0] + .07, pts[2][1] - .12, zc), (pts[3][0] + .12, yw - E, zc)]
    r1, r2 = (cx + (q[1][0] - cx) * .7, yw - E, zr), (cx + (q[2][0] - cx) * .7, yw - E, zr)
    t = Mesh()
    t.facing([q[0], q[1], r1], (-1, -1, 1), roof)
    t.facing([q[1], q[2], r2, r1], (0, -1, 1), roof)
    t.facing([q[2], q[3], r2], (1, -1, 1), roof)
    t.facing(q, (0, 0, -1), TRIM)
    t.facing([q[0], r1, r2, q[3]], (0, 1, 0), roof)
    roof_check(m, t, f"bay cap at x {cx:.2f}")
