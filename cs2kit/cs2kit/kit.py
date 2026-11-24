"""Pack-agnostic architectural kit builders: openings, walls, gables, roofs, porches, bays, signs.

Every material key defaults to standard atlas names while accepting overrides via `trim` or kwargs.
"""
import math
from .math_compat import Vector, E, UP
from . import rules
from .mesh import (
    Mesh,
    Wall,
    wbox,
    lbox,
    band,
    holes_for,
    cuts_of,
    world_cuts,
    party,
    flat_roof,
    chimney,
    roof_check,
    finish,
)

TRIM = "TrimWhite"

__all__ = [
    "Mesh",
    "Wall",
    "wbox",
    "lbox",
    "band",
    "holes_for",
    "cuts_of",
    "world_cuts",
    "party",
    "flat_roof",
    "chimney",
    "roof_check",
    "finish",
    "E",
    "UP",
    "TRIM",
    "style",
    "wall",
    "gable_wall",
    "gable_roof",
    "shed_roof",
    "porch",
    "bay",
    "opening",
    "shop_front",
    "loading_bay",
    "surface",
    "sign_plate",
]


def opening(m, g, w, h, lod, trim):
    """Window, door, shopfront, loading bay, or blind panel in a wall."""
    u0, u1, zb, zt, kind = h
    P, n, t = w.P, w.n, w.t
    if kind == "shop":
        return shop_front(m, g, w, h, lod, trim)
    if kind == "bay":
        return loading_bay(m, g, w, h, lod, trim)
    frame = trim.get("frame", TRIM)
    glass_mat = trim.get("glass", "Glass")
    if kind == "blind":  # Rule 28: cased board panel where no room stands behind
        if lod == 2:
            return
        jw = 0.14
        for q in (
            (u0 - jw, u0, zb - 0.10, zt + 0.18),
            (u1, u1 + jw, zb - 0.10, zt + 0.18),
            (u0, u1, zt, zt + 0.18),
            (u0, u1, zb - 0.10, zb),
        ):
            m.facing([P(q[0], q[2], 0.01), P(q[1], q[2], 0.01), P(q[1], q[3], 0.01), P(q[0], q[3], 0.01)], n, frame)
        if lod == 1:
            m.facing([P(u0, zb, 0.005), P(u1, zb, 0.005), P(u1, zt, 0.005), P(u0, zt, 0.005)], n, frame)
            return
        dep, f = 0.08, 0.10
        for a_, hint in ((u0, t), (u1, -t)):
            m.facing([P(a_, zb, 0), P(a_, zb, -dep), P(a_, zt, -dep), P(a_, zt, 0)], hint, frame)
        m.facing([P(u0, zt, 0), P(u1, zt, 0), P(u1, zt, -dep), P(u0, zt, -dep)], -UP, frame)
        m.facing([P(u0, zb, 0), P(u1, zb, 0), P(u1, zb, -dep), P(u0, zb, -dep)], UP, frame)
        m.facing([P(u0, zb, -dep), P(u1, zb, -dep), P(u1, zt, -dep), P(u0, zt, -dep)], n, frame)
        a0, a1, c0, c1, r = u0 + f, u1 - f, zb + f, zt - f, -dep + 0.04
        m.facing([P(a0, c0, r), P(a1, c0, r), P(a1, c1, r), P(a0, c1, r)], n, frame)
        m.facing([P(a0, c0, -dep), P(a0, c0, r), P(a0, c1, r), P(a0, c1, -dep)], -t, frame)
        m.facing([P(a1, c0, r), P(a1, c0, -dep), P(a1, c1, -dep), P(a1, c1, r)], t, frame)
        m.facing([P(a0, c1, r), P(a1, c1, r), P(a1, c1, -dep), P(a0, c1, -dep)], UP, frame)
        m.facing([P(a0, c0, -dep), P(a1, c0, -dep), P(a1, c0, r), P(a0, c0, r)], -UP, frame)
        return

    door = kind == "door"
    stone = trim.get("masonry")
    rev = trim.get("reveal", frame) if stone else frame
    dmat = trim.get("door", "Green")
    la = trim.get("lite_above")
    if la is not None and not door and zb > la:
        if lod == 2:
            return
        if lod == 0:
            dep, jw = 0.12, 0.14
            for a_, hint in ((u0, t), (u1, -t)):
                m.facing([P(a_, zb, 0), P(a_, zb, -dep), P(a_, zt, -dep), P(a_, zt, 0)], hint, frame)
            m.facing([P(u0, zt, 0), P(u1, zt, 0), P(u1, zt, -dep), P(u0, zt, -dep)], -UP, frame)
            m.facing([P(u0, zb, 0), P(u1, zb, 0), P(u1, zb, -dep), P(u0, zb, -dep)], UP, frame)
            g.facing([P(u0, zb, -dep), P(u1, zb, -dep), P(u1, zt, -dep), P(u0, zt, -dep)], n, glass_mat)
            for q in (
                (u0 - jw, u0, zb - 0.10, zt + 0.18),
                (u1, u1 + jw, zb - 0.10, zt + 0.18),
                (u0, u1, zt, zt + 0.18),
                (u0, u1, zb - 0.10, zb),
            ):
                m.facing([P(q[0], q[2], 0.01), P(q[1], q[2], 0.01), P(q[1], q[3], 0.01), P(q[0], q[3], 0.01)], n, frame)
            return

    flat = lod == 2 or (lod == 1 and trim.get("lean"))
    if flat:
        pane = [P(u0, zb, 0.02), P(u1, zb, 0.02), P(u1, zt, 0.02), P(u0, zt, 0.02)]
        (m if door else g).facing(pane, n, dmat if door else glass_mat)
        if lod == 2:
            return
        if trim.get("lean") == "bare":
            jw = 0.14
            lo = 0.0 if door else zb - 0.10
            m.facing(
                [P(u0 - jw, lo, 0.01), P(u1 + jw, lo, 0.01), P(u1 + jw, zt + 0.18, 0.01), P(u0 - jw, zt + 0.18, 0.01)],
                n,
                frame,
            )
            return

    dep = trim.get("dep", 0.16) if lod == 0 else 0.10
    for a, hint in ((u0, t), (u1, -t)):
        m.facing([P(a, zb, 0), P(a, zb, -dep), P(a, zt, -dep), P(a, zt, 0)], hint, rev)
    m.facing([P(u0, zt, 0), P(u1, zt, 0), P(u1, zt, -dep), P(u0, zt, -dep)], -UP, rev)
    if not door:
        m.facing([P(u0, zb, 0), P(u1, zb, 0), P(u1, zb, -dep), P(u0, zb, -dep)], UP, stone or frame)
    um = (u0 + u1) / 2
    if door:
        tr = zt - 0.45
        m.facing([P(u0, zb, -dep), P(u1, zb, -dep), P(u1, tr, -dep), P(u0, tr, -dep)], n, dmat)
        g.facing([P(u0, tr, -dep), P(u1, tr, -dep), P(u1, zt, -dep), P(u0, zt, -dep)], n, glass_mat)
        if lod == 0:
            b0 = -dep + 0.005
            lbox(m, w, u0 + E, u1 - E, tr - 0.04, tr + 0.04, b0, b0 + 0.05, frame)
            for p0, p1 in ((0.35, tr * 0.45), (tr * 0.52, tr - 0.22)):
                lbox(m, w, u0 + 0.16, u1 - 0.16, p0, p1, b0, b0 + 0.03, dmat)
    else:
        g.facing([P(u0, zb, -dep), P(u1, zb, -dep), P(u1, zt, -dep), P(u0, zt, -dep)], n, glass_mat)
        if lod == 0 and trim.get("simple"):
            b0 = -dep + 0.005
            zm = (zb + zt) / 2
            lbox(m, w, u0 + E, u1 - E, zm - 0.035, zm + 0.035, b0, b0 + 0.04, frame)
        elif lod == 0:
            b0 = -dep + 0.005
            zm = (zb + zt) / 2
            lbox(m, w, u0 + E, u0 + 0.06, zb + E, zt - E, b0, b0 + 0.04, frame)
            lbox(m, w, u1 - 0.06, u1 - E, zb + E, zt - E, b0, b0 + 0.04, frame)
            for za, zz in ((zb + E, zb + 0.07), (zm - 0.035, zm + 0.035), (zt - 0.06, zt - E)):
                lbox(m, w, u0 + 0.06 + E, u1 - 0.06 - E, za, zz, b0, b0 + 0.04, frame)
            lites = trim.get("lites", "2")
            inner_w = (u1 - 0.06) - (u0 + 0.06)
            if inner_w > 0.08:
                lbox(m, w, um - 0.015, um + 0.015, zb + 0.07, zt - 0.06, b0, b0 + 0.03, frame)
            if lites == "6" and inner_w > 0.20:
                for k in (1, 2):
                    c = u0 + (u1 - u0) * k / 3
                    lbox(m, w, c - 0.012, c + 0.012, zb + 0.07, zt - 0.06, b0, b0 + 0.03, frame)
                for zz in ((zb + zm) / 2, (zm + zt) / 2):
                    lbox(m, w, u0 + 0.06, u1 - 0.06, zz - 0.012, zz + 0.012, b0, b0 + 0.022, frame)

    if stone:
        lbox(m, w, u0 - 0.10, u1 + 0.10, zt, zt + 0.26, E, 0.05, stone)
        hood = trim.get("hood")
        if hood:
            zc = zt + 0.26 + E
            lbox(m, w, u0 - 0.2, u1 + 0.2, zc, zc + 0.09, E, 0.13, stone)
            if lod == 0:
                for a_, b_ in ((u0 - 0.19, u0 - 0.10 - E), (u1 + 0.10 + E, u1 + 0.19)):
                    lbox(m, w, a_, b_, zt - 0.32, zc - E, E, 0.11, stone)
            if hood == "pediment":
                za, zp, d = zc + 0.09 + E, zc + 0.09 + 0.34, 0.11
                a0, a1 = u0 - 0.16, u1 + 0.16
                m.facing([P(a0, za, d), P(a1, za, d), P(um, zp, d)], n, stone)
                m.facing([P(a0, za, 0), P(a0, za, d), P(um, zp, d), P(um, zp, 0)], UP - t, stone)
                m.facing([P(um, zp, 0), P(um, zp, d), P(a1, za, d), P(a1, za, 0)], UP + t, stone)
                m.facing([P(a0, za, 0), P(a1, za, 0), P(a1, za, d), P(a0, za, d)], -UP, stone)
        if not door:
            lbox(m, w, u0 - 0.08, u1 + 0.08, zb - 0.12, zb, E, 0.08, stone)
        return

    jw = 0.14
    lo = 0.0 if door else zb
    lbox(m, w, u0 - jw, u0, lo, zt, E, 0.05, frame, ("in", "top", "bot") if door else ("in", "top"))
    lbox(m, w, u1, u1 + jw, lo, zt, E, 0.05, frame, ("in", "top", "bot") if door else ("in", "top"))
    lbox(m, w, u0 - jw - 0.02, u1 + jw + 0.02, zt, zt + 0.18, E, 0.06, frame)
    if lod == 0 and not trim.get("simple"):
        lbox(m, w, u0 - jw - 0.05, u1 + jw + 0.05, zt + 0.18, zt + 0.22, E, 0.11, frame)
    if not door:
        lbox(m, w, u0 - jw - 0.02, u1 + jw + 0.02, zb - 0.10, zb, E, 0.09, frame)
    sh = trim.get("shutters")
    if sh and not door:
        sw = (u1 - u0) / 2
        for a, b in ((u0 - jw - 0.03 - sw, u0 - jw - 0.03), (u1 + jw + 0.03, u1 + jw + 0.03 + sw)):
            lbox(m, w, a, b, zb, zt, E, 0.045, sh, ("in",))
            if lod == 0:
                for k in range(1, 3):
                    zz = zb + (zt - zb) * k / 3
                    lbox(m, w, a + 0.03, b - 0.03, zz - 0.02, zz + 0.02, 0.045, 0.055, sh, ("in",))


def shop_front(m, g, w, h, lod, trim):
    """Wooden or cast-iron shopfront in a wide ground-floor opening."""
    u0, u1, zb, zt, _ = h
    P, n, t = w.P, w.n, w.t
    paint = trim.get("door", "Green")
    sill_mat = trim.get("shop_sill", trim.get("frame", TRIM))
    glass_mat = trim.get("glass", "Glass")
    pane = lambda a, b, z0, z1, d: [P(a, z0, d), P(b, z0, d), P(b, z1, d), P(a, z1, d)]
    if lod == 2:
        g.facing(pane(u0, u1, 0, zt, 0.02), n, glass_mat)
        return
    dep = 0.22 if lod == 0 else 0.12
    for a, hint in ((u0, t), (u1, -t)):
        m.facing([P(a, 0, 0), P(a, 0, -dep), P(a, zt, -dep), P(a, zt, 0)], hint, paint)
    m.facing([P(u0, zt, 0), P(u1, zt, 0), P(u1, zt, -dep), P(u0, zt, -dep)], -UP, paint)
    da, db = trim.get("shopdoor", ((u0 + u1) / 2 - 0.5, (u0 + u1) / 2 + 0.5))
    sr, tr = 0.6, zt - 0.55
    for a, b, z0 in ((u0, da, sr), (db, u1, sr), (da, db, tr)):
        if b - a > 0.01:
            g.facing(pane(a, b, z0, zt, -dep), n, glass_mat)
    m.facing(pane(da, db, 0, tr, -dep), n, paint)
    b0 = -dep
    for a, b in ((u0, da), (db, u1)):
        if b - a > 0.01:
            m.facing(pane(a, b, 0, sr, -dep), n, paint)
    if lod == 0:
        for a, b in ((u0 + E, da - 0.06 - E), (db + 0.06 + E, u1 - E)):
            if b - a > 0.1:
                lbox(m, w, a, b, sr - 0.06, sr, b0, b0 + 0.08, sill_mat, ("in",))
                k = max(1, round((b - a) / 1.4))
                for i in range(k):
                    pa, pb = a + (b - a) * i / k + 0.08, a + (b - a) * (i + 1) / k - 0.08
                    lbox(m, w, pa, pb, 0.12, sr - 0.14, b0, b0 + 0.03, paint, ("in",))
                for i in range(1, k):
                    c = a + (b - a) * i / k
                    lbox(m, w, c - 0.03, c + 0.03, sr + E, zt - E, b0, b0 + 0.06, paint, ("in",))
        for c in (da - 0.03, db + 0.03):
            lbox(m, w, c - 0.03, c + 0.03, 0, zt - E, b0, b0 + 0.07, paint, ("in", "bot"))
        lbox(m, w, u0 + E, u1 - E, tr - 0.04, tr + 0.04, b0, b0 + 0.05, paint, ("in",))
        lbox(m, w, da + 0.12, db - 0.12, 0.15, 0.9, b0, b0 + 0.035, paint)
        g.facing(pane(da + 0.12, db - 0.12, 1.05, tr - 0.15, b0 + 0.03), n, glass_mat)


def loading_bay(m, g, w, h, lod, trim):
    """Open or glazed loading bay in a masonry wall with optional round arch."""
    u0, u1, zb, zt, _ = h
    P, n, t = w.P, w.n, w.t
    stone = trim.get("masonry", "Dressed")
    wallm = trim.get("bay_wall", stone)
    frame = trim.get("frame", "Black")
    dark_mat = trim.get("dark", "Black")
    glass_mat = trim.get("glass", "Glass")
    arch = trim.get("arch")
    r, um = (u1 - u0) / 2, (u0 + u1) / 2
    zs = zt - r if arch else zt - 0.55
    if arch:
        k = 8 if lod == 0 else 4
        head = [(um - r * math.cos(math.pi * i / k), zs + r * math.sin(math.pi * i / k)) for i in range(k + 1)]
    else:
        k, head = 0, [(u0, zs), (u0, zt), (u1, zt), (u1, zs)]
    flat = lod == 2 or (lod == 1 and trim.get("lean"))
    if flat:
        q = [P(u0, zb, 0.02), P(u1, zb, 0.02), P(u1, zs, 0.02), P(u0, zs, 0.02)]
        (g if trim.get("glazed") else m).facing(q, n, glass_mat if trim.get("glazed") else dark_mat)
        g.facing([P(a, z, 0.02) for a, z in head], n, glass_mat)
        return
    if arch:
        m.facing([P(u0, zt, 0)] + [P(a, z, 0) for a, z in head[: k // 2 + 1]], n, wallm)
        m.facing([P(u1, zt, 0)] + [P(a, z, 0) for a, z in head[k // 2 :][::-1]], n, wallm)
    dep = 0.45 if lod == 0 else 0.25
    ring = [(u0, zb)] + head + [(u1, zb)]
    for (a0, z0_), (a1, z1_) in zip(ring, ring[1:]):
        du, dz = a1 - a0, z1_ - z0_
        hint = t * dz - UP * du
        m.facing([P(a0, z0_, 0), P(a1, z1_, 0), P(a1, z1_, -dep), P(a0, z0_, -dep)], hint, stone)
    m.facing([P(u0, zb, 0), P(u1, zb, 0), P(u1, zb, -dep), P(u0, zb, -dep)], UP, stone)
    q = [P(u0, zb, -dep), P(u1, zb, -dep), P(u1, zs, -dep), P(u0, zs, -dep)]
    if trim.get("glazed"):
        g.facing(q, n, glass_mat)
        if lod == 0:
            lbox(m, w, um - 0.03, um + 0.03, zb + E, zs - 0.05 - E, -dep + 0.005, -dep + 0.045, frame)
    else:
        m.facing(q, n, dark_mat)
    g.facing([P(a, z, -dep) for a, z in head], n, glass_mat)
    if lod == 0:
        b0 = -dep + 0.005
        lbox(m, w, u0 + E, u1 - E, zs - 0.05, zs + 0.05, b0, b0 + 0.06, frame)
        lbox(m, w, um - 0.03, um + 0.03, zs + 0.05 + E, zt - 0.02, b0, b0 + 0.04, frame)
        if arch:
            R2 = r + 0.24
            for i in range(k):
                c0, s0 = math.cos(math.pi * i / k), math.sin(math.pi * i / k)
                c1, s1 = math.cos(math.pi * (i + 1) / k), math.sin(math.pi * (i + 1) / k)
                pi0, pi1 = (um - r * c0, zs + r * s0), (um - r * c1, zs + r * s1)
                po0, po1 = (um - R2 * c0, zs + R2 * s0), (um - R2 * c1, zs + R2 * s1)
                m.facing([P(*pi0, 0.04), P(*pi1, 0.04), P(*po1, 0.04), P(*po0, 0.04)], n, stone)
                m.facing(
                    [P(*po0, E), P(*po1, E), P(*po1, 0.04), P(*po0, 0.04)],
                    t * -(po1[1] - po0[1]) + UP * (po1[0] - po0[0]),
                    stone,
                )
                m.facing(
                    [P(*pi0, E), P(*pi1, E), P(*pi1, 0.04), P(*pi0, 0.04)],
                    t * (pi1[1] - pi0[1]) - UP * (pi1[0] - pi0[0]),
                    stone,
                )
            for a, b in ((um - R2, um - r), (um + r, um + R2)):
                m.facing([P(a, zs, E), P(b, zs, E), P(b, zs, 0.04), P(a, zs, 0.04)], -UP, stone)
            lbox(m, w, um - 0.15, um + 0.15, zt - 0.06, zt + 0.30, 0.04 + E, 0.09, stone)
        else:
            lbox(m, w, u0 - 0.2, u1 + 0.2, zt, zt + 0.3, E, 0.05, stone)
    elif not arch:
        lbox(m, w, u0 - 0.2, u1 + 0.2, zt, zt + 0.3, E, 0.05, stone)


def surface(m, g, w, z0, z1, mats, holes, lod, trim, left=None, right=None):
    """Wall face from z0 to z1 with openings cut out."""
    L = left or (lambda z: 0.0)
    R = right or (lambda z: w.L)
    cut = [] if lod == 2 or (lod == 1 and trim.get("lean")) else holes
    zs = {z0, z1} | {z for a, b, _ in mats for z in (a, b) if z0 < z < z1} | {z for h in cut for z in h[2:4] if z0 < z < z1}
    zs |= {z for z in trim.get("knees", ()) if z0 < z < z1}
    zs = sorted(zs)
    for za, zb in zip(zs, zs[1:]):
        mid = (za + zb) / 2
        mat = next(mm for a, b, mm in mats if a <= mid <= b)
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


def style(
    top,
    mats,
    win,
    belts=(),
    eave=0.35,
    plinth=(0.75, 0.05, "StoneBase"),
    corners=True,
    frieze=0.30,
    low=(),
    belt_mat=TRIM,
    corner_mat=None,
):
    """Facade style descriptor."""
    return dict(
        top=top,
        mats=mats,
        win=win,
        belts=tuple(belts),
        eave=eave,
        plinth=plinth,
        corners=corners,
        frieze=frieze,
        low=tuple(low),
        cornice=None,
        cap=None,
        rust=None,
        quoin_from=None,
        belt_mat=belt_mat,
        corner_mat=corner_mat or belt_mat,
    )


def wall(
    m,
    g,
    st,
    A,
    B,
    s,
    e,
    bays,
    lod,
    door=None,
    z0=0.0,
    trim=None,
    waive=None,
    top=None,
    holes=(),
    frieze_on=True,
    plinth_cuts=(),
    omit=(),
):
    """Full facade from A to B with rule checking, plinth, belts, corners, and frieze."""
    w = Wall(A, B)
    trim = dict(dict(so=0.16, key=False), **(trim or {}))
    zt = st["top"] if top is None else top
    H = [h for h in holes_for(w, bays, st["win"], door) if h[2] >= z0 - 1e-6 and h[3] <= zt - 0.2]
    for c, f in omit:
        u = w.u_of(c)
        H = [h for h in H if not (abs((h[0] + h[1]) / 2 - u) < 0.05 and abs(h[2] - st["win"][f][1]) < 1e-6)]
    H += list(holes)
    surface(m, g, w, z0, zt, st["mats"], H, lod, trim)
    if lod == 0:
        bands = []
        if st["plinth"] and z0 == 0:
            bands.append(("water table", 0.0, st["plinth"][0], cuts_of(H, 0.25, ("door", "shop"))))
        for z in st["belts"]:
            if z0 + 0.2 < z < zt - 0.2:
                bands.append(("trim belt", z - 0.06, z + 0.10, []))
        if frieze_on and st["frieze"]:
            bands.append(("frieze board", zt - st["frieze"], zt, []))
        rules.check_wall(m, w, st, s, e, bays, H, door, z0, trim, False, bands, waive)
    if lod < 2:
        if st["plinth"] and z0 == 0:
            z1, p, mat = st["plinth"]
            band(
                m,
                w,
                0.0,
                z1,
                p,
                mat,
                s,
                e,
                cuts_of(H, 0.16, ("door", "shop")) + world_cuts(w, plinth_cuts),
                skip=("in", "bot"),
            )
        bm = st.get("belt_mat", TRIM)
        cm = st.get("corner_mat", TRIM)
        for z in st["belts"]:
            if z0 + 0.2 < z < zt - 0.2:
                band(m, w, z - 0.06, z + 0.10, 0.05, bm, s, e)
        if st["corners"]:
            for end, ty in ((0, s), (1, e)):
                if ty == "x":
                    a, b = (0.055 + E, 0.235) if end == 0 else (w.L - 0.18, w.L + 0.055)
                    lo = max(z0, st["plinth"][0] if st["plinth"] else 0) + E
                    lbox(m, w, a, b, lo, zt - (st["frieze"] or 0) - E, E, 0.055, cm, ("in", "bot", "top"))
        if frieze_on and st["frieze"]:
            band(m, w, zt - st["frieze"], zt, 0.07, bm, s, e)
    return w


def gable_wall(m, g, A, B, z0, zr, lod, mat, wins=(), trim=None, shape=None):
    """Gable triangle (or gambrel profile) above eave line at z0 rising to zr."""
    w = Wall(A, B)
    trim = dict(dict(so=0.16, key=False), **(trim or {}))
    half = w.L / 2
    if shape:
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


def gable_roof(
    m,
    x0,
    x1,
    y0,
    y1,
    ze,
    zr,
    lod,
    mat="SlateDark",
    over=(0.35, 0.35),
    sides=("p", "p"),
    th=0.16,
    rake=TRIM,
    knee=None,
):
    """Closed gable or gambrel roof slab (Rule 15) ridging along Y."""
    xm = (x0 + x1) / 2
    if knee:
        zk, ik = knee
        prof = [(x0, ze), (x0 + ik, zk), (xm, zr), (x1 - ik, zk), (x1, ze)]
    else:
        prof = [(x0, ze), (xm, zr), (x1, ze)]
    for idx, sd in ((0, sides[0]), (-1, sides[1])):
        if sd == "e":
            (xa, za), (xb, zb) = (prof[0], prof[1]) if idx == 0 else (prof[-1], prof[-2])
            f = 0.35 / abs(xb - xa)
            prof[idx] = (xa - (xb - xa) * f, za - (zb - za) * f)
    ya, yb = y0 - over[0], y1 + over[1]
    t = Mesh()
    for (xa, za), (xb, zb) in zip(prof, prof[1:]):
        nx, nz = -(zb - za), (xb - xa)
        if nz < 0:
            nx, nz = -nx, -nz
        t.facing([(xa, ya, za + th), (xb, ya, zb + th), (xb, yb, zb + th), (xa, yb, za + th)], (nx, 0, nz), mat)
        t.facing([(xa, ya, za), (xb, ya, zb), (xb, yb, zb), (xa, yb, za)], (-nx, 0, -nz), mat)
        for yy, d in ((ya, -1), (yb, 1)):
            t.facing([(xa, yy, za), (xb, yy, zb), (xb, yy, zb + th), (xa, yy, za + th)], (0, d, 0), rake)
    for idx, sd, sg in ((0, sides[0], -1), (-1, sides[1], 1)):
        xo, zo = prof[idx]
        t.facing([(xo, ya, zo), (xo, yb, zo), (xo, yb, zo + th), (xo, ya, zo + th)], (sg, 0, 0), rake if sd == "e" else mat)
    roof_check(m, t, f"gable roof x {x0:.2f}..{x1:.2f}, y {y0:.2f}..{y1:.2f}")
    if lod == 0:
        for (xa, za), (xb, zb) in zip(prof, prof[1:]):
            for yy, d, o in ((ya, -1, over[0]), (yb, 1, over[1])):
                if o > 0:
                    y2 = yy - d * 0.05
                    m.facing([(xa, yy, za - 0.2), (xb, yy, zb - 0.2), (xb, yy, zb), (xa, yy, za)], (0, d, 0), rake)
                    m.facing([(xa, y2, za - 0.2), (xb, y2, zb - 0.2), (xb, yy, zb - 0.2), (xa, yy, za - 0.2)], (0, 0, -1), rake)
        wbox(m, xm - 0.09, xm + 0.09, ya + E, yb - E, zr + th - 0.02, zr + th + 0.07, mat, ("z-",))


def shed_roof(m, x0, x1, y0, y1, z_high, z_low, lod, mat="SlateDark", fascia=TRIM, soffit="Deck", th=0.12, high="y0"):
    """Closed lean-to roof slab (Rule 15) between y0 and y1."""
    za, zb = (z_high, z_low) if high == "y0" else (z_low, z_high)
    s = (za - zb) / (y1 - y0)
    d1 = 1 if y1 > y0 else -1
    t = Mesh()
    t.facing([(x0, y0, za + th), (x1, y0, za + th), (x1, y1, zb + th), (x0, y1, zb + th)], (0, s, 1), mat)
    t.facing([(x0, y0, za), (x0, y1, zb), (x1, y1, zb), (x1, y0, za)], (0, -s, -1), mat if lod == 2 else soffit)
    for yy, zz, d in ((y0, za, -d1), (y1, zb, d1)):
        t.facing([(x0, yy, zz), (x1, yy, zz), (x1, yy, zz + th), (x0, yy, zz + th)], (0, d, 0), fascia)
    for xx, sg in ((x0, -1), (x1, 1)):
        t.facing([(xx, y0, za), (xx, y1, zb), (xx, y1, zb + th), (xx, y0, za + th)], (sg, 0, 0), fascia)
    roof_check(m, t, f"shed roof x {x0:.2f}..{x1:.2f}, y {y0:.2f}..{y1:.2f}")
    if lod < 2:
        ye, ze, d = (y1, zb, d1) if high == "y0" else (y0, za, -d1)
        a, b = sorted((ye + d * E, ye + d * 0.03))
        wbox(m, x0, x1, a, b, ze - 0.12, ze + th + 0.02, fascia, ("y+",) if d < 0 else ("y-",))


def porch(
    m,
    x0,
    x1,
    yw,
    depth,
    lod,
    zf=0.79,
    zt=3.35,
    posts=None,
    mat="SlateDark",
    deck="Deck",
    stair=None,
    rail=True,
    open_sides=("l", "r"),
    roof=True,
    skirt=True,
    trim_mat=TRIM,
    skirt_mat="Black",
    step_mat="StoneBase",
):
    """Front porch against wall at yw (facing -Y) with posts, rail, shed roof, and optional steps."""
    yf = yw - depth
    posts = posts or [x0 + 0.15, x1 - 0.15]
    wbox(m, x0 + E, x1 - E, yf, yw - E, zf - 0.12 if skirt else 0.0, zf, deck, ("y+",))
    if lod < 2 and zf < 1.5 and skirt:
        wbox(m, x0 + 0.06, x1 - 0.06, yf + 0.06, yw - 0.1, 0.0, zf - 0.12 - E, skirt_mat, ("y+", "z-", "z+"))
    for px in posts:
        wbox(m, px - 0.09, px + 0.09, yf + 0.06, yf + 0.24, zf + E, zt - 0.2, trim_mat, ("z-", "z+"))
        if lod == 0:
            wbox(m, px - 0.13, px + 0.13, yf + 0.02, yf + 0.28, zf + E, zf + 0.25, trim_mat, ("z-",))
    if lod < 2:
        wbox(m, x0 + E, x1 - E, yf, yf + 0.30, zt - 0.2 + E, zt - 0.02, trim_mat, ("y+", "z+"))
    if roof:
        shed_roof(m, x0, x1, yw - E, yf - 0.25, zt + 0.45, zt - 0.02, lod, mat, fascia=trim_mat, soffit=deck)
    if rail and lod < 2:
        sx = stair or (0, 0)
        runs = (
            [(a, b) for a, b in ((x0 + 0.2, sx[0] - 0.05), (sx[1] + 0.05, x1 - 0.2)) if b - a > 0.3]
            if stair
            else [(x0 + 0.2, x1 - 0.2)]
        )
        for a, b in runs:
            wbox(m, a, b, yf + 0.10, yf + 0.20, zf + 0.85, zf + 0.92, trim_mat)
            if lod == 0:
                k = int((b - a) / 0.14)
                for i in range(1, k):
                    c = a + (b - a) * i / k
                    if any(abs(c - px) < 0.13 for px in posts):
                        continue
                    wbox(m, c - 0.02, c + 0.02, yf + 0.13, yf + 0.17, zf + E, zf + 0.85 - E, trim_mat, ("z-", "z+"))
        for side, xx in (("l", x0 + 0.15), ("r", x1 - 0.25)):
            if side in open_sides:
                wbox(m, xx, xx + 0.1, yf + 0.30, yw - 0.2, zf + 0.85, zf + 0.92, trim_mat)
    if stair and lod < 2:
        a, b = stair
        k = max(2, round(zf / 0.19))
        for i in range(k):
            z = zf - (i + 1) * zf / k
            wbox(m, a, b, yf - (i + 1) * 0.28, yf - E - i * 0.28, 0.0, z + zf / k - E, step_mat, ("z-",))


def bay(
    m,
    g,
    cx,
    yw,
    width,
    proj,
    z0,
    z1,
    lod,
    mat,
    win,
    trim=None,
    roof="SlateDark",
    lites="2",
    trim_mat=TRIM,
    plinth_mat="StoneBase",
):
    """Canted projecting bay on a street wall at yw with closed hipped cap."""
    trim = dict(dict(so=0.16, key=False, lites=lites), **(trim or {}))
    a = width / 2 + proj
    pts = [(cx - a, yw), (cx - width / 2, yw - proj), (cx + width / 2, yw - proj), (cx + a, yw)]
    faces = list(zip(pts, pts[1:]))
    for i, (A, B) in enumerate(faces):
        w = Wall(A, B)
        H = []
        for zb, zt in win:
            ww = min(w.L - 0.5, 1.0 if i == 1 else 0.62)
            H.append((w.L / 2 - ww / 2, w.L / 2 + ww / 2, zb, zt, "win"))
        surface(m, g, w, z0, z1, [(z0, z1, mat)], H, lod, trim)
        if lod < 2:
            band(m, w, z1 - 0.30, z1, 0.07, trim_mat, "-", "-")
            if z0 < 0.8:
                band(m, w, 0.0, 0.72 if i == 1 else 0.735, 0.05, plinth_mat, "-", "-", skip=("in", "bot"))
    zc = z1 + 0.02
    zr = zc + 0.55
    q = [
        (pts[0][0] - 0.12, yw - E, zc),
        (pts[1][0] - 0.07, pts[1][1] - 0.12, zc),
        (pts[2][0] + 0.07, pts[2][1] - 0.12, zc),
        (pts[3][0] + 0.12, yw - E, zc),
    ]
    r1, r2 = (cx + (q[1][0] - cx) * 0.7, yw - E, zr), (cx + (q[2][0] - cx) * 0.7, yw - E, zr)
    t = Mesh()
    t.facing([q[0], q[1], r1], (-1, -1, 1), roof)
    t.facing([q[1], q[2], r2, r1], (0, -1, 1), roof)
    t.facing([q[2], q[3], r2], (1, -1, 1), roof)
    t.facing(q, (0, 0, -1), trim_mat)
    t.facing([q[0], r1, r2, q[3]], (0, 1, 0), roof)
    roof_check(m, t, f"bay cap at x {cx:.2f}")


def sign_plate(m, x_slot, y, z_slot, mat, mw=3.0, mh=0.58, offset=0.008):
    """Mount a Rule 26 atlas-grid-aligned signboard on a -Y street wall without splitting UVs."""
    x0 = x_slot * mw
    x1 = x0 + mw
    z0 = z_slot * mh
    z1 = z0 + mh
    yy = y - offset
    m.facing([(x0, yy, z0), (x1, yy, z0), (x1, yy, z1), (x0, yy, z1)], (0, -1, 0), mat)
