"""Lobstertown landmarks (Claude 2026-11-17, landmarks thread). Five one-off ploppables, one lot each.

the author's brief: "lean into the gaudiness: sea animals, things of that nature". Walls and roofs keep the muted
Landmarks palette row; the creatures carry the show, cast in iron, copper (TinGreen) and buoy red (Oxblood).
Concept sheet: (not published)

    build(lod, W, D, kind=..., **variant)

  kind 'theatre'   Siren Theatre 4x5: brick opera house, giant cream shell niche round the doors, twin copper-capped
                   stair towers, a mermaid in the pediment
  kind 'carousel'  Seahorse Carousel House 3x3: glazed octagon, skirt roof hung with a scalloped valance, seahorse
                   finials, clerestory, ogee dome in cream and grey-blue gores, a back ticket wing
  kind 'lodge'     Lobstermen's Lodge No. 1 3x3: two storey clapboard lodge hall, lancet windows, steep hip,
                   a 12 m red lobster across the ridge, a claw roundel over the door
  kind 'aquarium'  Tidewater Aquarium 4x3: granite rotunda and copper dome, an iron octopus over the door, a fish
                   frieze, low tank halls behind to the rear line
  kind 'hall'      Saltwater Exhibition Hall 6x5: a glass and iron barrel vault between granite aisles, a scallop
                   fan at both ends, cast iron seahorses on the piers, a copper whale on the ridge

Creatures are built here from three primitives: prism (a flat relief or cut-out), blob (a low-poly ellipsoid) and
beam (a square bar between two points). LOD 2 drops every creature but the lodge lobster (it is the silhouette).
"""
import math
from mathutils import Vector
from lt_designs.sculpture import (tube, rounded_beam, curved_strip, cod_body, turtle_shell, turtle_anatomy,
                                  relief_blob, nautilus, nautilus_3d, walrus)
from lt_kit import Mesh, Wall, wall, style, finish, wbox, gable_wall, gable_roof, chimney, E, TRIM, surface, roof_check
from nf_kit import band, flat_roof
from lt_shapes import pavilion_roof
from lt_designs.mainst import tower
from lt_designs.civic import spread

SM = 1.2
# Front wall set back from the lot front (m). Tuned so the foremost piece of each building (eave, shell, marquee)
# stands 0.15 m inside the lot line, i.e. on the sidewalk like Main Street (setback fix 2026-11-18).
SET_THEATRE, SET_CAROUSEL, SET_LODGE, SET_AQUARIUM, SET_HALL = 1.1, 1.55, .6, .7, 1.0
OV = 1.0                      # carousel skirt roof overhang beyond the glazed octagon
BRICK, STONE, CLAP = "Brick074", "Dressed", "Clapboard"
IRON, COPPER, RED, CREAM, BLUE = "Black", "TinGreen", "Oxblood", "Cream", "GreyBlue"
ROOF = "SlateDark"

ROSTER = {   # one lot per design; lt_roster gets the same block when the author gives the go
    "SirenTheatre": dict(lot=(4, 5), kind="theatre"),
    "CarouselHouse": dict(lot=(3, 3), kind="carousel"),
    "LobstermensLodge": dict(lot=(3, 3), kind="lodge"),
    "TidewaterAquarium": dict(lot=(4, 3), kind="aquarium"),
    "ExhibitionHall": dict(lot=(6, 5), kind="hall"),
    "KingCrabPalace": dict(lot=(5, 4), kind="crab"),
    "SacredCodExchange": dict(lot=(5, 4), kind="cod"),
    "SeaTurtlePavilion": dict(lot=(4, 4), kind="turtle"),
    "ClipperBowHall": dict(lot=(4, 5), kind="clipper"),
    "NautilusMarineGallery": dict(lot=(4, 3), kind="nautilus"),
    "WalrusBathhouse": dict(lot=(5, 4), kind="walrus"),
}


# ---------------------------------------------------------------- primitives

def plane(ox, oy, ux, uy):
    """(u, z, d) -> world: u along (ux, uy) from (ox, oy), d out of the wall (to the right of u)."""
    nx, ny = uy, -ux
    return lambda u, z, d: (ox + ux * u + nx * d, oy + uy * u + ny * d, z)


def prism(m, pts, P, d0, d1, mat, back=False):
    """A convex outline (u, z) extruded from d0 to d1 off the plane P."""
    o = P(0, 0, 0)
    n = [a - b for a, b in zip(P(0, 0, 1), o)]
    m.facing([P(u, z, d1) for u, z in pts], n, mat)
    if back:
        m.facing([P(u, z, d0) for u, z in pts], [-c for c in n], mat)
    cu = sum(p[0] for p in pts) / len(pts)
    cz = sum(p[1] for p in pts) / len(pts)
    for i in range(len(pts)):
        (au, az), (bu, bz) = pts[i], pts[(i + 1) % len(pts)]
        mu, mz = (au + bu) / 2 - cu, (az + bz) / 2 - cz
        h = [a - b for a, b in zip(P(cu + mu, cz + mz, 0), P(cu, cz, 0))]
        m.facing([P(au, az, d0), P(bu, bz, d0), P(bu, bz, d1), P(au, az, d1)], h, mat)


def oval(cu, cz, ru, rz, n=8, a0=0.0):
    return [(cu + ru * math.cos(a0 + 2 * math.pi * k / n), cz + rz * math.sin(a0 + 2 * math.pi * k / n)) for k in range(n)]


def strip(m, P, pts, w0, w1, d0, d1, mat, step=.004):
    """A tapering bar along a polyline (u, z): tentacles, tails, rope."""
    n = len(pts) - 1
    for i in range(n):
        (au, az), (bu, bz) = pts[i], pts[i + 1]
        L = math.hypot(bu - au, bz - az) or 1
        nu, nz = -(bz - az) / L, (bu - au) / L
        wa, wb = (w0 + (w1 - w0) * i / n) / 2, (w0 + (w1 - w0) * (i + 1) / n) / 2
        # bakefix: neighbouring segments overlap at every bend; step their faces 4 mm apart so none share a plane
        prism(m, [(au - nu * wa, az - nz * wa), (bu - nu * wb, bz - nz * wb), (bu + nu * wb, bz + nz * wb),
                  (au + nu * wa, az + nz * wa)], P, d0, d1 + step * i, mat)


def blob(m, c, r, mat, nu=8, nv=4):
    """A closed low-poly ellipsoid at c with radii r."""
    cx, cy, cz = c
    rx, ry, rz = r
    ring = lambda j: [(cx + rx * math.sin(math.pi * j / nv) * math.cos(2 * math.pi * k / nu),
                       cy + ry * math.sin(math.pi * j / nv) * math.sin(2 * math.pi * k / nu),
                       cz - rz * math.cos(math.pi * j / nv)) for k in range(nu)]
    bot, top = (cx, cy, cz - rz), (cx, cy, cz + rz)
    for j in range(1, nv):
        R = ring(j)
        if j == 1:
            for k in range(nu):
                p, q = R[k], R[(k + 1) % nu]
                m.facing([bot, q, p], [(p[i] + q[i]) / 2 - c[i] for i in range(3)], mat)
        if j == nv - 1:
            for k in range(nu):
                p, q = R[k], R[(k + 1) % nu]
                m.facing([p, q, top], [(p[i] + q[i]) / 2 - c[i] for i in range(3)], mat)
        else:
            S = ring(j + 1)
            for k in range(nu):
                a, b, cc, d = R[k], R[(k + 1) % nu], S[(k + 1) % nu], S[k]
                m.facing([a, b, cc, d], [(a[i] + cc[i]) / 2 - c[i] for i in range(3)], mat)


def beam(m, p, q, w, mat):
    """A square bar of width w from p to q."""
    d = [q[i] - p[i] for i in range(3)]
    L = math.sqrt(sum(x * x for x in d)) or 1
    d = [x / L for x in d]
    ref = (0, 0, 1) if abs(d[2]) < .9 else (1, 0, 0)
    a = [d[1] * ref[2] - d[2] * ref[1], d[2] * ref[0] - d[0] * ref[2], d[0] * ref[1] - d[1] * ref[0]]
    la = math.sqrt(sum(x * x for x in a))
    a = [x / la * w / 2 for x in a]
    b = [d[1] * a[2] - d[2] * a[1], d[2] * a[0] - d[0] * a[2], d[0] * a[1] - d[1] * a[0]]
    cs = [(1, 1), (-1, 1), (-1, -1), (1, -1)]
    P0 = [tuple(p[i] + s * a[i] + t * b[i] for i in range(3)) for s, t in cs]
    P1 = [tuple(q[i] + s * a[i] + t * b[i] for i in range(3)) for s, t in cs]
    for k in range(4):
        h = [P0[k][i] + P0[(k + 1) % 4][i] - 2 * p[i] for i in range(3)]
        m.facing([P0[k], P0[(k + 1) % 4], P1[(k + 1) % 4], P1[k]], h, mat)
    m.facing(P0, [-x for x in d], mat)
    m.facing(P1, d, mat)


# ---------------------------------------------------------------- the creatures

def fish(m, P, u, z, s, mat, d0=.02, d1=.18, dirn=1):
    f = lambda pts: [(u + dirn * a * s, z + b * s) for a, b in pts]
    body = f([(-.35, 0), (-.2, .13), (.15, .14), (.35, 0), (.15, -.14), (-.2, -.13)])
    tail = f([(-.3, 0), (-.52, .15), (-.52, -.15)])
    prism(m, body if dirn > 0 else body[::-1], P, d0, d1, mat)
    prism(m, tail if dirn > 0 else tail[::-1], P, d0, d1 - .01, mat)     # bakefix: tail tucks under the body


def frieze(m, P, u0, u1, z, s, mat, lod):
    if lod:
        return
    k, u = 0, u0 + .6 * s
    while u < u1 - .5 * s:
        fish(m, P, u, z, s, mat, dirn=1 if k % 2 == 0 else -1)
        u += 1.3 * s
        k += 1


def shell(m, P, u, z, r, lod, fan=CREAM, rib="RevealStone", n=11, lobe=6, k=1.0):
    """A scallop fan in relief: alternating wedges, a lip of round lobes. k scales the relief depth."""
    for i in range(n):
        a0, a1 = math.pi * i / n, math.pi * (i + 1) / n
        pts = [(u, z), (u + r * math.cos(a0), z + r * math.sin(a0)), (u + r * math.cos(a1), z + r * math.sin(a1))]
        if pts[1][0] < pts[2][0]:
            pts = [pts[0], pts[2], pts[1]]
        prism(m, pts[::-1] if i % 2 else pts[::-1], P, .02, (.22 if i % 2 else .3) * k, fan if i % 2 else rib)
    if lod == 0:
        rl = r * (.12 if n <= 11 else 1.2 / n)                           # bakefix: smaller lobes when there are more
        for i in range(n):
            a = math.pi * (i + .5) / n
            prism(m, oval(u + r * math.cos(a), z + r * math.sin(a), rl, rl, lobe), P, .02, .34 * k, fan)
    prism(m, oval(u, z, r * .12, r * .12, 6), P, .02, .4 * k, rib)


def octopus(m, P, u, z, s, mat, lod):
    """An octopus in high relief: a bulbous mantle at (u, z), eight arms that sweep out, droop and roll into a
    spiral at the tip, framing whatever is below (the aquarium door)."""
    # bakefix: relief flattened to under 0.5 m (was 0.87 m), or the audit reads the octopus as a room hanging
    # off the rotunda. Mantle .46, head .41, eyes .475/.485, arms .36/.32/.28/.24 rising 3.5 mm a segment.
    relief_blob(m, P, u, z + .36*s, .19*s, .3*s, .02, .46, mat, lod)     # mantle
    relief_blob(m, P, u, z + .1*s, .24*s, .12*s, .02, .41, mat, lod)    # head
    if lod == 2:
        return
    steps = 9 if lod == 0 else 5
    for side in (-1, 1):
        for k, (reach, drop, spin) in enumerate(((.26, .12, 1.4), (.44, .34, 1.7), (.52, .62, 1.9), (.44, .9, 2.1))):
            pts = []
            for i in range(steps + 1):
                t = i / steps
                x = side * (.06 + reach * math.sin(t * math.pi / 2)) * s
                y = .06 * s - drop * s * t * t
                pts.append((u + x, z + y))
            cu, cz = pts[-1]
            r0 = .09 * s
            for i in range(1, 5 if lod == 0 else 3):                      # the curl: a shrinking spiral
                ang = -math.pi / 2 + side * spin * i * .55
                rr = r0 * (1 - i * .18)
                pts.append((cu - side * r0 + side * rr * math.cos(ang) * side, cz + r0 * .2 + rr * math.sin(ang)))
            curved_strip(m, P, pts, (.11 - .012 * k) * s, .025 * s, .02, .36 - .04 * k, mat, step=.0035)
    if lod == 0:
        for side in (-1, 1):
            prism(m, oval(u + side * .09 * s, z + .16 * s, .024 * s, .023 * s, 6), P, .1, .475, mat)
            prism(m, oval(u + side * .09 * s, z + .16 * s, .013 * s, .013 * s, 6), P, .1, .485, IRON)


def mermaid(m, P, u, z, s, mat, lod):
    """A mermaid relief lying along a pediment: head at (u, z), the tail sweeping right into a curl."""
    if lod == 2:
        return
    prism(m, oval(u, z, .09 * s, .1 * s, 8), P, .02, .25, mat)
    curved_strip(m, P, [(u + .05 * s, z - .1 * s), (u + .2 * s, z - .14 * s), (u + .38 * s, z - .1 * s)], .16 * s, .12 * s, .02, .22, mat)
    curved_strip(m, P, [(u + .38 * s, z - .1 * s), (u + .55 * s, z - .02 * s), (u + .72 * s, z - .1 * s), (u + .86 * s, z - .02 * s)],
          .12 * s, .04 * s, .02, .205, mat)                               # bakefix: tail sits 15 mm under the body
    prism(m, [(u + .86 * s, z - .02 * s), (u + .98 * s, z + .1 * s), (u + .92 * s, z - .04 * s), (u + .98 * s, z - .14 * s)][::-1],
          P, .02, .24, mat)
    curved_strip(m, P, [(u - .05 * s, z + .02 * s), (u - .2 * s, z - .1 * s), (u - .3 * s, z - .12 * s)], .06 * s, .03 * s, .02, .2, mat)


def seahorse(m, x, y, z, s, ang, mat):
    """A cut-out seahorse standing on (x, y, z), its profile in the vertical plane at angle ang (radians)."""
    ux, uy = math.cos(ang), math.sin(ang)
    P = plane(x, y, ux, uy)
    t = .07 * s
    q = lambda pts: [(a * s, z + b * s) for a, b in pts]
    prism(m, q(oval(.12, .5, .11, .19, 8)), P, -t, t, mat, back=True)                    # belly
    prism(m, q(oval(.12, .84, .1, .08, 6)), P, -t, t, mat, back=True)                    # head
    prism(m, q([(.2, .82), (.42, .84), (.42, .88), (.2, .9)]), P, -t * .6, t * .6, mat, back=True)   # snout
    prism(m, q([(.05, .9), (.15, .91), (.1, 1.0)]), P, -t * .5, t * .5, mat, back=True)  # coronet
    prism(m, q([(.02, .6), (.02, .42), (-.08, .5)]), P, -t * .4, t * .4, mat, back=True)  # dorsal fin
    tail = [(.1, .34), (.06, .22), (.0, .12), (.02, .03), (.12, .02), (.15, .1), (.1, .13)]
    curved_strip(m, P, q(tail), .10*s, .012*s, -t, t, mat, step=.001)



def whale(m, x, y, z, s, mat, lod):
    """A copper whale weathervane: body, flukes, a fin; on a rod from z."""
    rounded_beam(m, (x, y, z), (x, y, z + .55 * s), .08, IRON)
    zc = z + .55 * s
    blob(m, (x, y, zc), (.4 * s, .09 * s, .13 * s), mat, 8 if lod == 0 else 6, 4 if lod == 0 else 3)
    if lod < 2:
        P = plane(x, y, 1, 0)
        prism(m, [(-.36 * s, zc), (-.56 * s, zc - .1 * s), (-.47 * s, zc + .01 * s), (-.56 * s, zc + .16 * s)][::-1],
              P, -.04 * s, .04 * s, mat, back=True)
        prism(m, [(0, zc - .1 * s), (.06 * s, zc - .11 * s), (-.1 * s, zc - .22 * s)], P, -.03 * s, .03 * s, mat, back=True)


def lobster(m, x, y, z, s, mat, lod, zfoot=None):
    """A lobster lying on a ridge at height z, head to +x, length s; legs reach down to zfoot."""
    nu, nv = (12, 7) if lod == 0 else (6, 3)                              # bakefix (density floor): was (8, 4)
    for i in range(4):                                                     # tail segments
        blob(m, (x - .2 * s - i * .075 * s, y, z), (.055 * s, (.065 - i * .006) * s, (.05 - i * .005) * s), mat, nu, nv)
    blob(m, (x, y, z + .01 * s), (.17 * s, .09 * s, .075 * s), mat, nu, nv)   # carapace
    blob(m, (x + .17 * s, y, z + .01 * s), (.07 * s, .06 * s, .05 * s), mat, nu, nv)
    for d in (1, -1):
        rounded_beam(m, (x + .18 * s, y + d * .04 * s, z), (x + .3 * s, y + d * .13 * s, z + .02 * s), .035 * s, mat)
        blob(m, (x + .41 * s, y + d * .16 * s, z + .03 * s), (.12 * s, .055 * s, .045 * s), mat, nu, nv)
        if lod < 2:
            rounded_beam(m, (x + .5 * s, y + d * .18 * s, z + .03 * s), (x + .58 * s, y + d * .14 * s, z + .03 * s), .025 * s, mat)
            rounded_beam(m, (x + .22 * s, y + d * .02 * s, z + .03 * s), (x + .62 * s, y + d * .38 * s, z + .05 * s), .012 * s, mat)
            zf = zfoot if zfoot is not None else z - .1 * s
            for k in range(4):
                xa = x - .08 * s + k * .06 * s
                rounded_beam(m, (xa, y + d * .07 * s, z), (xa - .02 * s, y + d * .2 * s, zf + (z - zf) * .3), .02 * s, mat)
    if lod < 2:
        P = plane(x - .5 * s, y, 0, 1)                                       # tail fan, flat
        for d in (-1, 0, 1):
            rounded_beam(m, (x - .48 * s, y, z), (x - .6 * s, y + d * .08 * s, z - .01 * s), .05 * s, mat)


# ---------------------------------------------------------------- shared wall dress

def trims(lod, door="Oxblood"):
    t = dict(door=door, lites="2", masonry=STONE, reveal=STONE, bay_wall=STONE, frame=TRIM, arch=True, glazed=True,
             lean="bare" if lod else True)
    return t, dict(t, simple=True)


def octagon(cx, cy, a):
    R = a / math.cos(math.pi / 8)
    return [(cx + R * math.cos(math.radians(-112.5 + 45 * k)), cy + R * math.sin(math.radians(-112.5 + 45 * k))) for k in range(8)]


def oct_walls(m, g, pts, z0, z1, mat, lod, trim, wins, door_face=0, door=None):
    """Walls round a plan polygon (face 0 = street). wins: [(width, sill, head)] on every face; door=(width, head)."""
    for i in range(len(pts)):
        w = Wall(pts[i], pts[(i + 1) % len(pts)])
        H = []
        for ww, zb, zt in wins:
            if i == door_face and door and zb < door[1]:
                continue
            ww = min(ww, w.L - 1.2)
            H.append((w.L / 2 - ww / 2, w.L / 2 + ww / 2, zb, zt, "win"))
        if door and i == door_face:
            H.append((w.L / 2 - door[0] / 2, w.L / 2 + door[0] / 2, 0.0, door[1], "door"))
        surface(m, g, w, z0, z1, [(z0, z1, mat)], H, lod, trim)
        if lod < 2:
            band(m, w, z1 - .35 - .008 * (i % 2), z1 - .008 * (i % 2), .08, TRIM, "-", "-")


def oct_roof(m, cx, cy, prof, mats, lod, what):
    """A closed octagonal roof of revolution: prof = [(apothem, z)] from the eave up (last apothem 0 = a point);
    mats alternate by sector (gores)."""
    rings = []
    for a, z in prof:
        R = a / math.cos(math.pi / 8)
        rings.append([(cx + R * math.cos(math.radians(-112.5 + 45 * k)), cy + R * math.sin(math.radians(-112.5 + 45 * k)), z)
                      for k in range(8)])
    t = Mesh()
    for i in range(len(rings) - 1):
        lo, hi = rings[i], rings[i + 1]
        for k in range(8):
            a, b = lo[k], lo[(k + 1) % 8]
            c, d = hi[(k + 1) % 8], hi[k]
            h = ((a[0] + b[0]) / 2 - cx, (a[1] + b[1]) / 2 - cy, .3)
            mat = mats[k % len(mats)]
            if prof[i + 1][0] < 1e-6:
                t.facing([a, b, c], h, mat)
            else:
                t.facing([a, b, c, d], h, mat)
    t.facing(rings[0], (0, 0, -1), TRIM)
    if prof[-1][0] > 1e-6:
        t.facing(rings[-1], (0, 0, 1), mats[0])
    roof_check(m, t, what)


# ---------------------------------------------------------------- the five landmarks

def theatre(m, g, lod, W, D, v):
    XH = 4.0 * W - SM
    yF, end = -4.0 * D + SET_THEATRE, 4.0 * D - .6
    top, zr = 14.5, 19.8
    trim, strim = trims(lod, "GreyBlue")
    sw = {"balance": "the theatre front: twin stair towers, a shell niche on the axis",
          "rhythm": "the shell niche takes the middle of the front"}
    st = style(top, [(0.0, top, BRICK)], [(1.4, .9, 3.4, "bay"), (1.2, 12.0, 13.6)], plinth=(.75, .05, "StoneBase"),
               corners=False, frieze=.4, belt_mat=STONE)
    holes = []
    if True:
        fw = Wall((-XH, yF), (XH, yF))
        for x in (-3.0, 3.0):
            holes.append((fw.u_of(x) - 1.1, fw.u_of(x) + 1.1, 0.0, 3.4, "door"))
    wall(m, g, st, (-XH, yF), (XH, yF), "x", "x", [-7.6, 0.0, 7.6], lod, door=(0.0, 2.2, 3.4), trim=trim, holes=holes,
         omit=[(-7.6, 1), (7.6, 1)], waive=dict(sw, glass="the towers stand in front of the outer upper bays"))
    sb = [yF + 7.0 + 4.6 * k for k in range(int((end - yF - 9.0) / 4.6) + 1)]
    sst = style(top, [(0.0, top, BRICK)], [(1.2, .9, 3.0), (1.4, 6.0, 11.4, "bay")], plinth=(.75, .05, "StoneBase"),
                corners=False, frieze=.4, belt_mat=STONE)
    wall(m, g, sst, (-XH, end), (-XH, yF), "x", "x", sb, lod, trim=strim, waive=dict(sw, axes="side of an auditorium"))
    wall(m, g, sst, (XH, yF), (XH, end), "x", "x", sb, lod, trim=strim, waive=dict(sw, axes="side of an auditorium"))
    bb = spread(-XH, XH, 3.6, odd=False)
    wall(m, g, style(top, [(0.0, top, BRICK)], [(1.2, .9, 3.0), (1.2, 5.6, 7.8), (1.2, 10.2, 12.4)],
                     plinth=(.75, .05, "StoneBase"), corners=False, frieze=.4, belt_mat=STONE), (XH, end), (-XH, end),
         "x", "x", bb, lod, door=(bb[1], 1.2, 2.6), trim=strim,
         waive=dict(sw, balance="stage house back: scenery door off the axis"))
    gable_roof(m, -XH, XH, yF, end, top + .006, zr, lod, ROOF, over=(.45, .35), sides=("e", "e"))
    gable_wall(m, g, (-XH, yF), (XH, yF), top, zr, lod, STONE, trim=strim)
    gable_wall(m, g, (XH, end), (-XH, end), top, zr, lod, BRICK, trim=strim, wins=[(0.0, 1.2, top + .9, top + 2.6)])
    P = plane(-XH, yF, 1, 0)                                             # u = x + XH on the front
    shell(m, P, XH, 4.6, 6.6, lod)
    prism(m, [(XH - 5.0, 3.55), (XH + 5.0, 3.55), (XH + 5.0, 4.45), (XH - 5.0, 4.45)], P, .02, .25, BLUE)   # marquee
    mermaid(m, P, XH - 2.4, top + 1.6, 6.0, CREAM, lod)
    frieze(m, P, 5.2, 2 * XH - 5.2, top - .2, .7, CREAM, lod)
    for cx in (-XH + 2.48, XH - 2.48):                                  # stair towers, set forward of the front
        # bakefix: towers stand 2 cm proud of the side walls instead of flush with them
        tower(m, g, lod, cx, yF + 1.9, 2.5, 4, 0.0, 17.0, 3.0, BRICK, COPPER, dict(strim),
              [(1.8, 5.6, (0,)), (7.6, 12.4, (0,)), (13.6, 15.8, (0, 1, 3))], STONE)
        if lod < 2:
            fish(m, plane(cx - 1.0, yF + 1.9 - 2.5, 1, 0), 1.0, 16.2, 1.2, COPPER)
    if lod == 0:
        # bakefix (density floor, theatre was 2.9 tris/m2): the auditorium sides and the stage house back were bare
        # brick. Scallop shells over and between the upper windows, and a fish frieze under the eaves (clear of the
        # stair towers, which stand over the first 4.4 m of each side).
        PL, PR, PB = plane(-XH, end, 0, -1), plane(XH, yF, 0, 1), plane(XH, end, -1, 0)
        su = sorted(set([y - yF for y in sb] + [y - yF + 2.3 for y in sb[:-1]]))
        for u in su:
            shell(m, PR, u, 11.8, .9, 0, n=15, lobe=8)
            shell(m, PL, (end - yF) - u, 11.8, .9, 0, n=15, lobe=8)
        bu = sorted(set([XH - x for x in bb] + [XH - (bb[i] + bb[i + 1]) / 2 for i in range(len(bb) - 1)]))
        for u in bu:
            shell(m, PB, u, 12.7, .75, 0, n=15, lobe=8)
        frieze(m, PR, 4.8, end - yF - .4, top - .2, .7, CREAM, lod)
        frieze(m, PL, .4, end - yF - 4.8, top - .2, .7, CREAM, lod)
        frieze(m, PB, .4, 2 * XH - .4, top - .2, .7, CREAM, lod)


def carousel(m, g, lod, W, D, v):
    yF, end = -4.0 * D + SET_CAROUSEL, 4.0 * D - .6
    a = 9.0
    cy = yF + a
    trim, strim = trims(lod, "GreyBlue")
    pts = octagon(0.0, cy, a)
    oct_walls(m, g, pts, 0.0, 6.0, TRIM, lod, trim, [(4.8, .5, 5.2)], 0, door=(2.4, 3.2))
    # skirt roof: an octagonal frustum from the eave ring to the clerestory
    oct_roof(m, 0.0, cy, [(a + OV, 6.0), (6.3, 7.7), (5.9, 7.7)], [ROOF], lod, "carousel skirt")
    pc = octagon(0.0, cy, 6.0)
    oct_walls(m, g, pc, 7.7, 10.2, TRIM, lod, strim, [(1.4, 8.2, 9.8)])
    # ogee dome in gores
    prof = [(6.4, 10.2), (6.4, 11.0), (5.6, 12.0), (3.6, 13.0), (1.4, 13.8), (.5, 14.3), (.5, 14.6)]
    oct_roof(m, 0.0, cy, prof, [CREAM, BLUE] if lod < 2 else [BLUE], lod, "carousel dome")
    if lod < 2:
        beam(m, (0, cy, 14.6), (0, cy, 16.0), .14, IRON)
        blob(m, (0, cy, 15.1), (.3, .3, .3), CREAM, 6, 3)
    R = (a + OV) / math.cos(math.pi / 8)
    if lod == 0:                                                         # scalloped valances under both eaves
        # bakefix (density floor): rounder scallops, and a second valance under the dome eave
        for ap, ze in ((a + OV, 6.0), (6.4, 10.2)):
            ring = octagon(0.0, cy, ap)
            for k in range(8):
                (ax, ay), (bx, by) = ring[k], ring[(k + 1) % 8]
                L = math.hypot(bx - ax, by - ay)
                P = plane(ax, ay, (bx - ax) / L, (by - ay) / L)
                n = int(L / 1.05)
                for j in range(n):
                    u = L * (j + .5) / n
                    prism(m, [(u + .5 * math.cos(t), ze - .45 * math.sin(t)) for t in [math.pi * q / 10 for q in range(11)]][::-1],
                          P, -.04, .04, CREAM if j % 2 else BLUE, back=True)
    if lod < 2:                                                          # seahorses on the skirt corners
        for k, (px, py) in enumerate(octagon(0.0, cy, a + OV - .1)):
            ang = math.atan2(py - cy, px) + math.pi / 2
            seahorse(m, px, py, 6.0, 2.4, ang, IRON)
    # the ticket and engine wing to the rear line
    x0, x1 = -5.0, 5.0
    y0 = cy + a - 1.0
    wst = style(4.2, [(0.0, 4.2, CLAP)], [(1.2, .9, 3.0)], plinth=(.6, .05, "StoneBase"), corners=True, frieze=.3)
    sw = {"balance": "service wing behind the carousel"}
    yw = [(y0 + 1.2 + end) / 2]
    wall(m, g, wst, (x0, end), (x0, y0), "x", "c", yw, lod, trim=strim, waive=sw)
    wall(m, g, wst, (x1, y0), (x1, end), "c", "x", yw, lod, trim=strim, waive=sw)
    wall(m, g, wst, (x1, end), (x0, end), "x", "x", spread(x0, x1, 2.4), lod, door=(0.0, 1.2, 2.6), trim=strim, waive=sw)
    pavilion_roof(m, x0 - .35, x1 + .35, y0 - .35, end + .35, 4.206, 2.4, lod, ROOF, finial=False)


def lodge(m, g, lod, W, D, v):
    XH = 4.0 * W - SM
    yF, end = -4.0 * D + SET_LODGE, 4.0 * D - .6
    G_, top = 4.6, 9.0
    yR = yF + 13.0
    trim, strim = trims(lod, "Oxblood")
    trim["masonry"] = trim["reveal"] = trim["bay_wall"] = CLAP
    strim = dict(trim, simple=True)
    win = [(1.1, 1.0, 3.6, "bay"), (1.1, G_ + .8, G_ + 3.6, "bay")]
    st = style(top, [(0.0, top, CLAP)], win, belts=(G_,), plinth=(.6, .05, "StoneBase"), corners=True, frieze=.35)
    sw = {"balance": "lodge hall front, the emblem on the axis"}
    bays = spread(-XH, XH, 3.2)
    wall(m, g, st, (-XH, yF), (XH, yF), "x", "x", bays, lod, door=(0.0, 1.8, 3.6), trim=trim,
         omit=[(0.0, 1)], waive=dict(sw, glass="the claw roundel takes the middle upper bay",
                                     rhythm="the claw roundel takes the middle upper bay"))
    sb = spread(yF, yR, 3.0, odd=False)
    wall(m, g, st, (-XH, yR), (-XH, yF), "x", "x", sb, lod, trim=strim, waive=sw)
    wall(m, g, st, (XH, yF), (XH, yR), "x", "x", sb, lod, trim=strim, waive=sw)
    rb = spread(-XH, XH, 3.0)
    wall(m, g, st, (XH, yR), (-XH, yR), "x", "x", rb, lod, trim=strim, omit=[(c, 0) for c in rb if abs(c) < 7.4],
         waive=dict(sw, glass="the back wing covers the middle", rhythm="the back wing covers the middle"))
    zr = pavilion_roof(m, -XH - .4, XH + .4, yF - .4, yR + .4, top + .006, (13.8 / 2) * .85, lod, ROOF, finial=False)
    for cx in (-XH + 3.0, XH - 3.0):
        chimney(m, cx, yR - 1.4, .4, .5, top, top + 3.2, lod)
    # back wing: kitchen and lodge stores, one storey, to the rear line
    # bakefix: wing plinth 2 cm taller than the hall's, so their tops don't meet in one plane at the joint
    wst = style(4.2, [(0.0, 4.2, CLAP)], [(1.1, 1.0, 3.2)], plinth=(.62, .05, "StoneBase"), corners=True, frieze=.3)
    x0, x1 = -6.5, 6.5
    yw = spread(yR, end, 2.6, odd=False, edge=1.6)
    wall(m, g, wst, (x0, end), (x0, yR), "x", "c", yw, lod, trim=strim, waive=sw)
    wall(m, g, wst, (x1, yR), (x1, end), "c", "x", yw, lod, trim=strim, waive=sw)
    wall(m, g, wst, (x1, end), (x0, end), "x", "x", spread(x0, x1, 2.6), lod, door=(0.0, 1.0, 2.6), trim=strim, waive=sw)
    pavilion_roof(m, x0 - .35, x1 + .35, yR - 2.0, end + .35, 4.206, 2.6, lod, ROOF, finial=False)
    P = plane(-XH, yF, 1, 0)
    if lod < 2:
        prism(m, oval(XH, G_ + 2.2, 1.2, 1.2, 10), P, .02, .2, BLUE)
        prism(m, oval(XH, G_ + 2.2, .95, .95, 10), P, .2, .26, CREAM)
        for d in (-1, 1):
            dz = .015 if d > 0 else 0.0                                  # bakefix: the two claws cross
            strip(m, P, [(XH - d * .7, G_ + 1.5), (XH - d * .1, G_ + 2.3), (XH + d * .35, G_ + 2.9)], .26, .14, .26, .36 + dz, RED)
    if lod == 0:                                                         # rope moulding on the floor belt
        # bakefix (density floor): the rope now runs round the sides and the exposed ends of the back too
        runs = [(P, .3, 2 * XH - .3), (plane(-XH, yR, 0, -1), .3, yR - yF - .3), (plane(XH, yF, 0, 1), .3, yR - yF - .3),
                (plane(XH, yR, -1, 0), .3, XH - 6.85), (plane(XH, yR, -1, 0), XH + 6.85, 2 * XH - .3)]
        for Q, u, u1 in runs:
            while u < u1 - .45:
                prism(m, [(u, G_ - .08), (u + .25, G_ - .08), (u + .45, G_ + .12), (u + .2, G_ + .12)], Q, .08, .14, TRIM)
                u += .5
    lobster(m, 0.0, (yF + yR) / 2, zr + .7, 12.0, RED, lod, zfoot=zr - 1.2)


def aquarium(m, g, lod, W, D, v):
    XH = 4.0 * W - SM
    yF, end = -4.0 * D + SET_AQUARIUM, 4.0 * D - .6
    a = 7.0
    cy = yF + a
    trim, strim = trims(lod, "GreyBlue")
    pts = octagon(0.0, cy, a)
    oct_walls(m, g, pts, 0.0, 9.0, STONE, lod, trim, [(1.6, 1.4, 5.4)], 0, door=(2.6, 4.2))
    oct_roof(m, 0.0, cy, [(a + .3, 9.0), (a + .3, 9.3), (6.4, 10.8), (4.6, 12.0), (2.2, 12.8), (1.0, 13.0)],
             [COPPER], lod, "aquarium dome")
    if lod < 2:
        lp = octagon(0.0, cy, .9)
        oct_walls(m, g, lp, 13.0, 13.7, CREAM, lod, strim, [])
        oct_roof(m, 0.0, cy, [(1.1, 13.7), (0.0, 14.1)], [COPPER], lod, "aquarium lantern")
        beam(m, (0, cy, 14.1), (0, cy, 14.6), .08, IRON)
        P = plane(-.6, cy, 1, 0)
        fish(m, P, .6, 14.6, 1.4, COPPER, -.05, .05)
    # the front face: octopus over the door, fish frieze round the drum
    (ax, ay), (bx, by) = pts[0], pts[1]
    L = math.hypot(bx - ax, by - ay)
    P = plane(ax, ay, (bx - ax) / L, (by - ay) / L)
    (nautilus if v.get("creature") == "nautilus" else octopus)(m, P, L / 2, 5.5, 5.0, IRON, lod)
    for k in (7, 0, 1):
        if k == 0 and v.get("creature") == "nautilus":
            continue  # The shell fills this panel; keep the fish frieze on the two side faces.
        (ax, ay), (bx, by) = pts[k], pts[(k + 1) % 8]
        L = math.hypot(bx - ax, by - ay)
        frieze(m, plane(ax, ay, (bx - ax) / L, (by - ay) / L), .4, L - .4, 7.6, .9, BLUE, lod)
    # low tank halls round and behind the rotunda, to the side and rear lines
    yb = cy - 4.0
    hx = a * math.sqrt(2) - 4.0                                         # the rotunda's half width at y = yb
    top = 6.0
    st = style(top, [(0.0, top, STONE)], [(1.2, 1.2, 3.4)], plinth=(.75, .05, "StoneBase"), corners=False,
               frieze=.4, belt_mat=CREAM)
    sw = {"balance": "tank hall wings either side of the rotunda"}
    fb = spread(-XH, -hx, 2.4, odd=False, edge=1.8)
    wall(m, g, st, (-XH, yb), (-hx, yb), "x", "c", fb, lod, trim=strim, waive=sw)
    wall(m, g, st, (hx, yb), (XH, yb), "c", "x", [-c for c in fb[::-1]], lod, trim=strim, waive=sw)
    sb = spread(yb, end, 2.8, odd=False)
    wall(m, g, st, (-XH, end), (-XH, yb), "x", "x", sb, lod, trim=strim, waive=sw)
    wall(m, g, st, (XH, yb), (XH, end), "x", "x", sb, lod, trim=strim, waive=sw)
    ab = spread(-XH, XH, 2.8, odd=False)
    wall(m, g, st, (XH, end), (-XH, end), "x", "x", ab, lod, door=(ab[len(ab) // 2], 1.4, 2.8),
         trim=strim, waive=dict(sw, balance="service door at the back"))
    flat_roof(m, -XH, XH, yb, end, top + .006)
    if lod < 2:
        for x0, x1 in ((-XH - .1, -hx), (hx, XH + .1)):
            wbox(m, x0, x1, yb - .1, yb + .25, top, top + .9, CREAM, ("z-",))
        for x in (-XH - .09, XH - .26):                                  # bakefix: 1 cm in and 2 cm lower than the
            wbox(m, x, x + .35, yb, end + .1, top, top + .88, CREAM, ("z-",))   # front parapets they run into
    if lod == 0:
        # bakefix (density floor, aquarium was 3.3 tris/m2): a scallop shell over every tank hall window and a fish
        # frieze under the tank hall parapets
        runs = [(plane(-XH, yb, 1, 0), [x + XH for x in fb], XH - hx),
                (plane(hx, yb, 1, 0), [-c - hx for c in fb[::-1]], XH - hx),
                (plane(-XH, end, 0, -1), [end - y for y in sb], end - yb),
                (plane(XH, yb, 0, 1), [y - yb for y in sb], end - yb),
                (plane(XH, end, -1, 0), [XH - x for x in ab], 2 * XH)]
        for Q, us, L in runs:
            for u in us:
                shell(m, Q, u, 3.75, .8, 0, fan=CREAM, n=15, lobe=8, k=.55)   # under .25 m: no slits
            frieze(m, Q, .4, L - 1.0, top - .2, .7, BLUE, lod)
    if False:
        for x in ():
            P = plane(x - 1.0, yb, 1, 0)
            for k in range(8):
                t0, t1 = 2 * math.pi * k / 8, 2 * math.pi * (k + 1) / 8
                r0, r1 = .85, 1.05
                prism(m, [(1.0 + r0 * math.cos(t0), 2.8 + r0 * math.sin(t0)), (1.0 + r1 * math.cos(t0), 2.8 + r1 * math.sin(t0)),
                          (1.0 + r1 * math.cos(t1), 2.8 + r1 * math.sin(t1)), (1.0 + r0 * math.cos(t1), 2.8 + r0 * math.sin(t1))][::-1],
                      P, .02, .12, CREAM)


def hall(m, g, lod, W, D, v):
    XH = 4.0 * W - SM
    yF, end = -4.0 * D + SET_HALL, 4.0 * D - .6
    r, zs = 10.0, 4.0
    trim, strim = trims(lod, "GreyBlue")
    top = 7.0
    st = style(top, [(0.0, top, STONE)], [(1.6, 1.0, 5.0, "bay")], plinth=(.75, .05, "StoneBase"), corners=False,
               frieze=.5, belt_mat=CREAM)
    sw = {"balance": "aisle of the exhibition hall"}
    for s in (-1, 1):                                                   # the two granite aisles, both ends
        xo, xi = s * XH, s * (r + 2.0)
        bays = spread(min(xo, xi), max(xo, xi), 2.8, odd=False)
        A, B = ((xo, yF), (xi, yF)) if s < 0 else ((xi, yF), (xo, yF))
        wall(m, g, st, A, B, "x" if s < 0 else "c", "c" if s < 0 else "x", bays, lod, trim=trim, waive=sw)
        A, B = ((xi, end), (xo, end)) if s < 0 else ((xo, end), (xi, end))
        wall(m, g, st, A, B, "c" if s < 0 else "x", "x" if s < 0 else "c", bays, lod, trim=strim, waive=sw)
        sb = spread(yF, end, 3.0, odd=False)
        A, B = ((xo, end), (xo, yF)) if s < 0 else ((xo, yF), (xo, end))
        wall(m, g, st, A, B, "x", "x", sb, lod, trim=strim, waive=sw)
        if lod == 0:
            # bakefix (density floor, hall was 5.5 tris/m2): a shell over every aisle window, a fish frieze
            Q = plane(-XH, end, 0, -1) if s < 0 else plane(XH, yF, 0, 1)
            for y in sb:
                shell(m, Q, end - y if s < 0 else y - yF, 5.3, .8, 0, n=15, lobe=8)
            frieze(m, Q, .4, end - yF - .4, top - .25, .8, "Iron", lod)
        x0, x1 = sorted((xo, xi))
        flat_roof(m, x0, x1, yF, end, top + .006)
        if lod < 2:
            wbox(m, x0, x1, yF - .1, yF + .3, top, top + .8, CREAM, ("z-",))
            wbox(m, x0, x1, end - .3, end + .1, top, top + .8, CREAM, ("z-",))
        for yy in (yF, end):
            P = plane(x0, yy, 1, 0) if yy == yF else plane(x1, yy, -1, 0)
            frieze(m, P, .4, x1 - x0 - .4, top - .25, .8, "Iron", lod)
    # entrance blocks and piers at both ends, the scallop fan above
    for yy, sgn in ((yF, 1), (end, -1)):
        P = plane(-r - 2.0, yy, 1, 0) if sgn > 0 else plane(r + 2.0, yy, -1, 0)
        Wl = Wall((-r - 2.0, yy), (r + 2.0, yy)) if sgn > 0 else Wall((r + 2.0, yy), (-r - 2.0, yy))
        H = [(Wl.L / 2 + dx - 1.8, Wl.L / 2 + dx + 1.8, 0.0, 3.4, "door") for dx in (-6.0, 0.0, 6.0)]
        surface(m, g, Wl, 0.0, zs, [(0.0, zs, STONE)], H, lod, trim)
        cut = lambda z: Wl.L / 2 - math.sqrt(max(r * r - (z - zs) ** 2, 0.0))
        cutr = lambda z: Wl.L / 2 + math.sqrt(max(r * r - (z - zs) ** 2, 0.0))
        # the glass fan: radial panes in the windows mesh, iron ribs proud of it
        n = 14 if lod == 0 else 7
        for i in range(n):
            a0, a1 = math.pi * i / n, math.pi * (i + 1) / n
            g.facing([P(Wl.L / 2, zs, .0), P(Wl.L / 2 + r * math.cos(a1), zs + r * math.sin(a1), 0.0),
                      P(Wl.L / 2 + r * math.cos(a0), zs + r * math.sin(a0), 0.0)], [a - b for a, b in zip(P(0, 0, 1), P(0, 0, 0))], "Glass")
            if lod < 2:                                                  # bakefix: ribs start 1 m out, a hub covers the middle
                strip(m, P, [(Wl.L / 2 + math.cos(a0), zs + math.sin(a0)), (Wl.L / 2 + r * math.cos(a0), zs + r * math.sin(a0))],
                      .18, .18, .0, .2, IRON)
        if lod < 2:
            prism(m, oval(Wl.L / 2, zs, 1.15, 1.15, 10), P, .0, .24, IRON)
            for rr in (4.0, 7.0):
                pts = [(Wl.L / 2 + rr * math.cos(math.pi * k / 12), zs + rr * math.sin(math.pi * k / 12)) for k in range(13)]
                strip(m, P, pts, .14, .14, .0, .12, IRON)
            for i in range(14 if lod == 0 else 7):
                aa = math.pi * (i + .5) / (14 if lod == 0 else 7)
                prism(m, oval(Wl.L / 2 + (r + .2) * math.cos(aa), zs + (r + .2) * math.sin(aa), .7, .7, 8), P, -.1, .24, BLUE)   # bakefix: was .3, made slits
        band(m, Wl, zs - .3, zs + .2, .1, CREAM, "-", "-")
        for xp in (-r - 2.0, r):                                         # piers with seahorses
            wbox(m, xp - .01, xp + 2.01, yy - .4 if sgn > 0 else yy - 1.6, yy + 1.6 if sgn > 0 else yy + .4, 0.0, 8.6, STONE)
            if lod < 2:
                wbox(m, xp - .15, xp + 2.15, (yy - .55) if sgn > 0 else yy - 1.75, (yy + 1.75) if sgn > 0 else yy + .55, 8.6, 9.0, CREAM)
                seahorse(m, xp + 1.0, yy + .6 * sgn, 9.0, 3.2, 0.0 if xp < 0 else math.pi, IRON)
    # the barrel vault: glass between iron ribs, on a granite clerestory wall from the aisle roofs
    for s in (-1, 1):
        xw = s * r
        A, B = ((xw, end), (xw, yF)) if s < 0 else ((xw, yF), (xw, end))
        surface(m, g, Wall(A, B), top, zs + .2 if zs + .2 > top else top + .5, [(top, top + .5, STONE)], [], lod, strim)
    n = 12 if lod == 0 else 6
    ring = [(r * math.cos(math.pi * i / n), zs + r * math.sin(math.pi * i / n)) for i in range(n + 1)]
    for s in (-1, 1):                                                   # roof over the pier line, under the vault foot
        flat_roof(m, min(s * (r - .3), s * (r + 2.0)), max(s * (r - .3), s * (r + 2.0)), yF, end, top + .006)   # bakefix: runs under the clerestory
    zv = [(x, max(z, top + .5)) for x, z in ring]
    for i in range(n):
        (xa, za), (xb, zb) = zv[i], zv[i + 1]
        g.facing([(xa, yF, za), (xb, yF, zb), (xb, end, zb), (xa, end, za)], ((xa + xb) / 2, 0, (za + zb) / 2 - zs), "Glass")
    if lod < 2:
        y = yF
        while y <= end + 1e-6:
            for i in range(n):
                (xa, za), (xb, zb) = zv[i], zv[i + 1]
                beam(m, (xa, y, za + .14), (xb, y, zb + .14), .25 + .01 * (i % 2), IRON)   # bakefix: joints, clear the wall
            y += 4.0 if lod == 0 else 9.35
        beam(m, (0, yF, zv[n // 2][1] + .15), (0, end, zv[n // 2][1] + .15), .35, IRON)
    # bakefix (rule 28): a broad iron end truss just inside each glass fan, so the fan panes and the doors have an
    # opaque roof member over them (the audit does not count the glass vault as a roof)
    for y in ((yF + .55, end - .55) if lod < 2 else ()):
        for i in range(n):
            (xa, za), (xb, zb) = zv[i], zv[i + 1]
            beam(m, (xa, y, za + .32), (xb, y, zb + .32), .6 + .01 * (i % 2), IRON)
    whale(m, 0.0, (yF + end) / 2, max(z for _, z in zv) + .2, 2.4 if lod else 2.6, COPPER, lod)


# ---------------------------------------------------------------- four gaudy coastal landmarks (Antigravity 2026-11-20)

def starfish(m, P, u, z, r, mat, lod, d0=.02, d1=.18):
    """Five-point coastal starfish relief medallion."""
    pts = []
    for k in range(10):
        a = math.pi / 2 + 2 * math.pi * k / 10
        rr = r if k % 2 == 0 else r * .42
        pts.append((u + rr * math.cos(a), z + rr * math.sin(a)))
    # Build as 5 convex triangular rays + central pentagon (prism expects convex outline)
    center = [(u + r * .44 * math.cos(math.pi / 2 + 2 * math.pi * (2 * k + 1) / 10),
               z + r * .44 * math.sin(math.pi / 2 + 2 * math.pi * (2 * k + 1) / 10)) for k in range(5)]
    prism(m, center, P, d0, d1 + .02, mat)
    for k in range(5):
        tip = pts[2 * k]
        a = pts[(2 * k - 1) % 10]
        b = pts[(2 * k + 1) % 10]
        prism(m, [a, tip, b], P, d0, d1, mat)
    if lod == 0:
        prism(m, oval(u, z, r * .22, r * .22, 6), P, d1 + .02, d1 + .06, CREAM)


def porthole(m, P, u, z, r, mat, lod):
    """Brass/cream-rimmed nautical porthole medallion with 4 bolt bosses."""
    prism(m, oval(u, z, r, r, 10 if lod == 0 else 8), P, .02, .16, mat)
    prism(m, oval(u, z, r * .68, r * .68, 8), P, .16, .20, BLUE)
    if lod == 0:
        for k in range(4):
            a = math.pi / 4 + k * math.pi / 2
            prism(m, oval(u + r * .84 * math.cos(a), z + r * .84 * math.sin(a), r * .10, r * .10, 6),
                  P, .16, .22, COPPER)


def anchor(m, P, u, z, h, mat, lod):
    """Monumental high-relief cast-iron anchor centered at (u, z) with height h."""
    # Shank, stock, crown ring
    strip(m, P, [(u, z + h * .45), (u, z - h * .42)], h * .09, h * .11, .02, .30, mat, step=0.0)
    strip(m, P, [(u - h * .28, z + h * .28), (u + h * .28, z + h * .28)], h * .07, h * .07, .02, .34, mat, step=0.0)
    prism(m, oval(u, z + h * .48, h * .10, h * .10, 8), P, .02, .26, mat)
    # Curved arms & flukes (stepped 15 mm in relief between left & right arms so crown join never shares a plane)
    for s in (-1, 1):
        pts = [(u, z - h * .38), (u + s * h * .18, z - h * .35), (u + s * h * .32, z - h * .20),
               (u + s * h * .36, z - h * .04)]
        d_arm = .24 if s < 0 else .255
        strip(m, P, pts, h * .10, h * .06, .02, d_arm, mat, step=.004)
        fluke = [(u + s * h * .28, z - h * .08), (u + s * h * .44, z - h * .08), (u + s * h * .36, z + h * .08)]
        prism(m, fluke if s > 0 else fluke[::-1], P, .02, .29 + (.012 if s > 0 else 0.0), mat)


def king_crab(m, cx, cy, z0, s, lod):
    """Colossal buoy-red King Crab crowning a dome, raising twin pincers around a copper lantern orb."""
    nu, nv = (12, 7) if lod == 0 else (6, 3)
    # Domed armored carapace
    blob(m, (cx, cy, z0 + .08 * s), (.28 * s, .24 * s, .11 * s), RED, nu, nv)
    if lod == 2:
        return
    # Eyes & spiked crown ridge
    for sg in (-1, 1):
        blob(m, (cx + sg * .10 * s, cy - .21 * s, z0 + .16 * s), (.022 * s, .022 * s, .025 * s), RED, 6, 3)
        blob(m, (cx + sg * .10 * s, cy - .24 * s, z0 + .16 * s), (.012 * s, .012 * s, .014 * s), IRON, 6, 3)
    # 8 splayed jointed legs gripping the dome slopes
    for sg in (-1, 1):
        for k, (dy, rx1, dz1, rx2, dz2) in enumerate((
            (-.08, .36, .08, .50, -.14),
            (.02, .40, .06, .54, -.16),
            (.12, .38, .05, .50, -.16),
            (.20, .32, .03, .42, -.15),
        )):
            p0 = (cx + sg * .20 * s, cy + dy * s, z0 + .06 * s)
            p1 = (cx + sg * rx1 * s, cy + (dy - .02) * s, z0 + dz1 * s)
            p2 = (cx + sg * rx2 * s, cy + (dy + .03) * s, z0 + dz2 * s)
            rounded_beam(m, p0, p1, .038 * s, RED)
            rounded_beam(m, p1, p2, .030 * s, RED)
    # Twin colossal raised pincers cradling a glowing cream & copper lantern orb
    for sg in (-1, 1):
        p0 = (cx + sg * .16 * s, cy - .16 * s, z0 + .09 * s)
        p1 = (cx + sg * .34 * s, cy - .26 * s, z0 + .19 * s)
        p2 = (cx + sg * .24 * s, cy - .28 * s, z0 + .34 * s)
        rounded_beam(m, p0, p1, .055 * s, RED)
        rounded_beam(m, p1, p2, .050 * s, RED)
        blob(m, p2, (.10 * s, .075 * s, .075 * s), RED, nu, nv)
        # Pincer fingers closing toward lantern
        rounded_beam(m, p2, (cx + sg * .11 * s, cy - .28 * s, z0 + .40 * s), .030 * s, RED)
        rounded_beam(m, p2, (cx + sg * .12 * s, cy - .28 * s, z0 + .30 * s), .026 * s, RED)
    # Glowing lantern orb held aloft between the pincers
    orb_c = (cx, cy - .28 * s, z0 + .36 * s)
    blob(m, orb_c, (.085 * s, .085 * s, .095 * s), CREAM, nu, nv)
    blob(m, (cx, cy - .28 * s, z0 + .46 * s), (.06 * s, .06 * s, .04 * s), COPPER, 8, 3)
    rounded_beam(m, (cx, cy - .22 * s, z0 + .12 * s), (cx, cy - .28 * s, z0 + .28 * s), .03 * s, IRON)


def sacred_cod(m, cx, cy, z0, s, lod):
    for dx in (-.22*s,.20*s):
        beam(m,(cx+dx,cy,z0-.3),(cx+dx,cy,z0+.16*s),.14,IRON)
    cod_body(m,cx,cy,z0,s,lod,COPPER)


def crab(m, g, lod, W, D, v):
    """King Crab Palace / Neptune's Bathhouse (5x4): Beaux-Arts seaside bathhouse, striped dome & 11 m red King Crab."""
    XH = 4.0 * W - SM
    yF, end = -4.0 * D + 1.0, 4.0 * D - .6
    G_, top = 4.8, 9.6
    trim, strim = trims(lod, "GreyBlue")
    sw = {"balance": "King Crab Palace Beaux-Arts seaside bathhouse", "rhythm": "arched bathhouse colonnade"}
    st = style(top, [(0.0, G_, STONE), (G_, top, CREAM)], [(1.5, .9, 3.8, "bay"), (1.2, G_ + .8, G_ + 3.1)],
               belts=(G_,), plinth=(.70, .05, "StoneBase"), corners=False, frieze=.42, belt_mat=STONE)
    fb = spread(-XH, XH, 3.5)
    dc = fb[len(fb) // 2]
    holes = []
    fw = Wall((-XH, yF), (XH, yF))
    for bx in (fb[len(fb) // 2 - 1], fb[len(fb) // 2 + 1]):
        holes.append((fw.u_of(bx) - .9, fw.u_of(bx) + .9, 0.0, 3.8, "door"))
    wall(m, g, st, (-XH, yF), (XH, yF), "x", "x", fb, lod, door=(dc, 2.0, 3.9), trim=trim,
         omit=[(fb[len(fb) // 2 - 1], 0), (fb[len(fb) // 2 + 1], 0)], holes=holes, waive=sw)
    sb = spread(yF, end, 3.5, odd=False)
    wall(m, g, st, (-XH, end), (-XH, yF), "x", "x", sb, lod, trim=strim, waive=sw)
    wall(m, g, st, (XH, yF), (XH, end), "x", "x", sb, lod, trim=strim, waive=sw)
    rb = spread(-XH, XH, 3.5)
    wall(m, g, st, (XH, end), (-XH, end), "x", "x", rb, lod, door=(rb[len(rb) // 2], 1.6, 3.2), trim=strim, waive=sw)
    flat_roof(m, -XH, XH, yF, end, top + .006)
    if lod < 2:
        for xa, xb, ya, yb in (
            (-XH - .12, XH + .12, yF - .12, yF + .28),
            (-XH - .12, XH + .12, end - .28, end + .12),
            (-XH - .11, -XH + .28, yF + .28 + E, end - .28 - E),
            (XH - .28, XH + .11, yF + .28 + E, end - .28 - E),
        ):
            wbox(m, xa, xb, ya, yb, top, top + .88, STONE, ("z-",))
    # Central octagonal striped melon dome
    cy = (yF + end) / 2
    ap = 8.4
    dp = octagon(0.0, cy, ap)
    oct_walls(m, g, dp, top, top + 2.4, STONE, lod, strim, [(1.6, top + .4, top + 1.9)])
    dprof = [(ap + .35, top + 2.4), (ap + .35, top + 2.75), (7.9, top + 4.4), (6.2, top + 6.0), (3.8, top + 7.1), (1.8, top + 7.5)]
    oct_roof(m, 0.0, cy, dprof, [CREAM, BLUE] if lod < 2 else [BLUE], lod, "King Crab Palace melon dome")
    # Colossal 11 m red King Crab crowning the melon dome
    (walrus if v.get("creature") == "walrus" else king_crab)(m, 0.0, cy, top + 7.55, 11.2, lod)
    # Gaudy facade reliefs: giant scallop shells over the 3 entrance arches, copper starfish over upper windows, fish frieze
    PF = plane(-XH, yF, 1, 0)
    ent_xs = {fb[len(fb) // 2 - 1], dc, fb[len(fb) // 2 + 1]}
    for bx in ent_xs:
        shell(m, PF, bx + XH, 4.0, 1.35, lod, fan=CREAM, rib=COPPER, n=13, lobe=6, k=.75)
    if lod < 2:
        runs = [
            (PF, [x + XH for x in fb], [x + XH for x in fb if x not in ent_xs], 2 * XH),
            (plane(-XH, end, 0, -1), [end - y for y in sb], [end - y for y in sb], end - yF),
            (plane(XH, yF, 0, 1), [y - yF for y in sb], [y - yF for y in sb], end - yF),
            (plane(XH, end, -1, 0), [XH - x for x in rb], [XH - x for x in rb], 2 * XH),
        ]
        for Q, us_all, us_g, L in runs:
            for u in us_all:
                starfish(m, Q, u, G_ + 3.65, .62, COPPER, lod)
            if lod == 0:
                for u in us_g:
                    shell(m, Q, u, 4.05, .82, 0, fan=CREAM, rib=COPPER, n=9, lobe=6, k=.55)
                frieze(m, Q, .6, L - .6, top - .22, .75, BLUE, lod)
                frieze(m, Q, .6, L - .6, G_ + .35, .65, COPPER, lod)


def cod(m, g, lod, W, D, v):
    """The Sacred Cod Exchange (5x4): Brick & granite harbour market hall, twin claw towers & 14 m leaping copper cod."""
    XH = 4.0 * W - SM
    yF, end = -4.0 * D + 1.0, 4.0 * D - .6
    G_, top, zr = 4.8, 9.6, 15.8
    trim, strim = trims(lod, "Oxblood")
    sw = {"balance": "Sacred Cod harbour market hall", "rhythm": "arched harbour market bays"}
    st = style(top, [(0.0, G_, STONE), (G_, top, "BuffBrick")], [(1.6, .9, 3.8, "bay"), (1.15, G_ + .85, G_ + 3.0)],
               belts=(G_,), plinth=(.68, .05, "StoneBase"), corners=False, frieze=.40, belt_mat=STONE)
    fb = spread(-XH, XH, 3.5)
    dc = fb[len(fb) // 2]
    holes = []
    fw = Wall((-XH, yF), (XH, yF))
    for bx in (fb[len(fb) // 2 - 1], fb[len(fb) // 2 + 1]):
        holes.append((fw.u_of(bx) - .95, fw.u_of(bx) + .95, 0.0, 3.8, "door"))
    wall(m, g, st, (-XH, yF), (XH, yF), "x", "x", fb, lod, door=(dc, 2.2, 3.9), trim=trim,
         omit=[(fb[len(fb) // 2 - 1], 0), (fb[len(fb) // 2 + 1], 0)], holes=holes, waive=sw)
    sb = spread(yF, end, 3.5, odd=False)
    wall(m, g, st, (-XH, end), (-XH, yF), "x", "x", sb, lod, trim=strim, waive=sw)
    wall(m, g, st, (XH, yF), (XH, end), "x", "x", sb, lod, trim=strim, waive=sw)
    rb = spread(-XH, XH, 3.5)
    wall(m, g, st, (XH, end), (-XH, end), "x", "x", rb, lod, door=(rb[len(rb) // 2], 1.8, 3.4), trim=strim, waive=sw)
    # Main side-gable dark slate roof (ridge along X so the 14 m Sacred Cod leaps parallel to the street!)
    ym = (yF + end) / 2
    from lt_shapes import slab
    k_p = (zr - top) / (ym - yF)
    ov = .38
    prof = [(yF - ov, top - ov * k_p), (ym, zr), (end + ov, top - ov * k_p)]
    slab(m, prof, -XH - .35, XH + .35, lambda a, q, z: (a, q, z), lod, ROOF, end=STONE, eave=STONE, what="Cod Exchange main roof")
    gable_wall(m, g, (-XH, end), (-XH, yF), top, zr, lod, "BuffBrick", wins=[(ym, 1.1, top + 1.0, top + 3.2)], trim=strim)
    gable_wall(m, g, (XH, yF), (XH, end), top, zr, lod, "BuffBrick", wins=[(ym, 1.1, top + 1.0, top + 3.2)], trim=strim)
    # Grand central front clock gable projecting cleanly into main roof
    gw_h = 5.4
    gable_wall(m, g, (-gw_h, yF - .02), (gw_h, yF - .02), top, zr - .4, lod, STONE, trim=strim)
    gable_roof(m, -gw_h, gw_h, yF - .02, ym, top, zr - .4, lod, COPPER, over=(.32, 0.0), sides=("e", "e"))
    if lod < 2:
        PC = plane(-gw_h, yF - .02, 1, 0)
        prism(m, oval(gw_h, top + 2.3, 1.55, 1.55, 12), PC, .02, .18, BLUE)
        prism(m, oval(gw_h, top + 2.3, 1.32, 1.32, 12), PC, .18, .24, CREAM)
        if lod == 0:
            strip(m, PC, [(gw_h, top + 2.3), (gw_h, top + 3.2)], .12, .08, .24, .30, IRON)
            strip(m, PC, [(gw_h, top + 2.3), (gw_h + .72, top + 2.5)], .10, .07, .24, .31, IRON)
    # Twin copper-capped corner market towers with crossed buoy-red lobster-claw emblems
    for cx in (-XH + 2.48, XH - 2.48):
        tower(m, g, lod, cx, yF + 2.1, 2.5, 4, 0.0, 14.2, 2.8, "BuffBrick", COPPER, dict(strim),
              [(1.2, 3.8, (0,)), (5.6, 8.6, (0,)), (10.8, 13.0, (0, 1, 3))], STONE)
        if lod < 2:
            PT = plane(cx - 1.2, yF + 2.1 - 2.5, 1, 0)
            prism(m, oval(1.2, 13.5, .75, .75, 8), PT, .02, .14, CREAM)
            for sgn in (-1, 1):
                strip(m, PT, [(1.2 - sgn * .5, 13.0), (1.2 + sgn * .35, 14.0)], .18, .12, .14, .22 + (.012 if sgn > 0 else 0.0), RED)
    # 14 m leaping verdigris-copper & cream Sacred Cod soaring boldly over the ridge!
    sacred_cod(m, 0.0, ym, zr + .95, 14.0, lod)
    # Facade reliefs: scallop canopies + fish medallions + fish frieze
    PF = plane(-XH, yF, 1, 0)
    for bx in (fb[len(fb) // 2 - 1], dc, fb[len(fb) // 2 + 1]):
        shell(m, PF, bx + XH, 4.0, 1.4, lod, fan=CREAM, rib=STONE, n=13, lobe=6, k=.75)
    if lod == 0:
        runs = [
            (PF, [x + XH for x in fb[1:-1]], 2 * XH),
            (plane(-XH, end, 0, -1), [end - y for y in sb], end - yF),
            (plane(XH, yF, 0, 1), [y - yF for y in sb], end - yF),
            (plane(XH, end, -1, 0), [XH - x for x in rb], 2 * XH),
        ]
        for Q, us, L in runs:
            for u in us:
                shell(m, Q, u, G_ + 3.2, .78, 0, fan=CREAM, n=9, lobe=6, k=.55)
            frieze(m, Q, 4.8 if Q is PF else .5, L - (4.8 if Q is PF else .5), top - .22, .75, COPPER, lod)
            frieze(m, Q, 4.8 if Q is PF else .5, L - (4.8 if Q is PF else .5), G_ + .35, .65, BLUE, lod)


def turtle(m, g, lod, W, D, v):
    """The Great Sea Turtle Pavilion (4x4): Atlantic City Lucy-the-Elephant coastal novelty folly -- oval
    heart-tapered verdigris-copper & dark-slate hexagonal scute carapace with pale stone marginal border rim,
    proud arched sculpted turtle neck & hooked beak over the front portal, broad flat swept-back front & rear
    paddle flippers, and tapered rear tail."""
    XH = 4.0 * W - 3.2                                 # 12.8 m -> 3.2 m side margin so 31 m swept wing flippers stay inside lot!
    yF, end = -4.0 * D + 2.2, 4.0 * D - 1.0            # main wall -13.8, grounded portico at -15.05 (front_m <= 0.95 m)
    top = 6.8
    cy = (yF + end) / 2
    trim, strim = trims(lod, "GreyBlue")
    sw = {"balance": "Sea Turtle Pavilion arched coastal hall", "rhythm": "arched seaside pavilion"}
    st = style(top, [(0.0, top, STONE)], [(1.55, 1.0, 4.6, "bay")], plinth=(.72, .05, "StoneBase"),
               corners=False, frieze=.42, belt_mat=CREAM)
    fb = spread(-XH, XH, 3.6)
    dc = fb[len(fb) // 2]
    wall(m, g, st, (-XH, yF), (XH, yF), "x", "x", fb, lod, door=(dc, 2.4, 4.4), trim=trim, waive=sw)
    sb = spread(yF, end, 3.6, odd=False)
    wall(m, g, st, (-XH, end), (-XH, yF), "x", "x", sb, lod, trim=strim, waive=sw)
    wall(m, g, st, (XH, yF), (XH, end), "x", "x", sb, lod, trim=strim, waive=sw)
    rb = spread(-XH, XH, 3.6)
    wall(m, g, st, (XH, end), (-XH, end), "x", "x", rb, lod, door=(rb[len(rb) // 2], 1.8, 3.6), trim=strim, waive=sw)
    # Flat base ceiling + overhanging oval heart-tapered high-contrast sea-turtle carapace
    flat_roof(m, -XH, XH, yF, end, top + .006)
    rx = XH + 0.20                                     # 13.0 m half-width (overhangs stone pavilion walls like a real shell!)
    ry = (end - yF) / 2 - 0.10                         # 14.3 m half-length (oval elongated front-to-back!)
    turtle_shell(m, cy, rx, ry, top, lod)
    # Grounded stone entrance portico carrying the proud arched turtle neck & head
    for sgn in (-1, 1):
        wbox(m, sgn * 2.0 - .48, sgn * 2.0 + .48, yF - 1.25, yF - E, 0.0, top - .45 - E, STONE, ("y+", "z-", "z+"))
    wbox(m, -2.55, 2.55, yF - 1.32, yF - E, top - .45, top + .35, CREAM, ("y+",))
    # Proud lofted neck & reptilian head, broad flat swept-back front & rear paddle flippers, and tapered tail!
    turtle_anatomy(m, cy, yF, end, XH, top, rx, ry, lod)
    # Gaudy facade shells, starfish & fish frieze (keeps LOD0 density cleanly above 8 tri/m2)
    if lod == 0:
        runs = [
            (plane(-XH, yF, 1, 0), [x + XH for x in fb if abs(x) > 2.6], 2 * XH),
            (plane(-XH, end, 0, -1), [end - y for y in sb], end - yF),
            (plane(XH, yF, 0, 1), [y - yF for y in sb], end - yF),
            (plane(XH, end, -1, 0), [XH - x for x in rb], 2 * XH),
        ]
        for Q, us, L in runs:
            for u in us:
                shell(m, Q, u, 4.85, .86, 0, fan=CREAM, rib=COPPER, n=15, lobe=8, k=.55)
                starfish(m, Q, u, 5.95, .52, COPPER, 0)
            frieze(m, Q, .8, L - .8, top - .22, .75, BLUE, lod)


def clipper(m, g, lod, W, D, v):
    """The Clipper's Bow Maritime Hall (4x5): Granite maritime museum with a full-scale sculpted clipper-ship prow
    grounded over an arched quay bastion, copper figurehead, porthole medallions, twin giant cast-iron anchors &
    crow's-nest cupola."""
    XH = 4.0 * W - SM
    yF, end = -4.0 * D + 1.8, 4.0 * D - .6       # main wall 1.8 m in so grounded prow bastion reaches 0.95 m & bowsprit 0.30 m inside lot!
    G_, top = 5.0, 10.4
    trim, strim = trims(lod, "GreyBlue")
    sw = {"balance": "Clipper's Bow Maritime Hall front", "rhythm": "prow bastion takes central bay"}
    st = style(top, [(0.0, G_, "StoneBase"), (G_, top, STONE)], [(1.5, 1.0, 4.0, "bay"), (1.2, G_ + .9, G_ + 3.4)],
               belts=(G_,), plinth=(.72, .05, "StoneBase"), corners=False, frieze=.44, belt_mat=CREAM)
    fb = [-11.2, -7.2, 0.0, 7.2, 11.2]
    wall(m, g, st, (-XH, yF), (XH, yF), "x", "x", fb, lod, door=(0.0, 2.4, 4.2), trim=trim,
         omit=[(0.0, 1), (-7.2, 1), (7.2, 1)],
         waive=dict(sw, glass="prow & twin anchors occupy front bays"))
    sb = spread(yF, end, 3.6, odd=False)
    wall(m, g, st, (-XH, end), (-XH, yF), "x", "x", sb, lod, trim=strim, waive=sw)
    wall(m, g, st, (XH, yF), (XH, end), "x", "x", sb, lod, trim=strim, waive=sw)
    rb = spread(-XH, XH, 3.6)
    wall(m, g, st, (XH, end), (-XH, end), "x", "x", rb, lod, door=(rb[len(rb) // 2], 1.6, 3.4), trim=strim, waive=sw)
    # Main dark-slate hipped roof
    zr = pavilion_roof(m, -XH - .38, XH + .38, yF - .38, end + .38, top + .006, 6.2, lod, ROOF, finial=False)
    # Grounded quay bastion piers flanking the central portal (z = 0..G_ - .5, lintel beam projects 5 cm proud)
    for sgn in (-1, 1):
        wbox(m, sgn * 2.5 - .65, sgn * 2.5 + .65, yF - .85, yF - E, 0.0, G_ - .5 - E, "StoneBase", ("y+", "z-", "z+"))
    wbox(m, -3.25, 3.25, yF - .90, yF - E, G_ - .5, G_ + .15, STONE, ("y+",))
    # Full-scale sculpted clipper-ship prow (stempost at yF - 1.15 = -19.35, 0.65 m inside lot!)
    y_stem = yF - 1.15
    y_back = yF + .35
    p_mesh = Mesh()
    z_keel, z_gun = G_ + .15 + E, top + .85
    w_keel, w_gun = 2.8, 3.8
    p_mesh.facing([(-w_keel, y_back, z_keel), (0.0, y_stem + .35, z_keel), (0.0, y_stem, z_gun), (-w_gun, y_back, z_gun)],
                  (-1, -1, 0), BLUE)
    p_mesh.facing([(0.0, y_stem + .35, z_keel), (w_keel, y_back, z_keel), (w_gun, y_back, z_gun), (0.0, y_stem, z_gun)],
                  (1, -1, 0), BLUE)
    p_mesh.facing([(-w_gun, y_back, z_gun), (0.0, y_stem, z_gun), (w_gun, y_back, z_gun)], (0, 0, 1), "Deck")
    p_mesh.facing([(-w_keel, y_back, z_keel), (w_keel, y_back, z_keel), (0.0, y_stem + .35, z_keel)], (0, 0, -1), COPPER)
    p_mesh.facing([(-w_keel, y_back, z_keel), (-w_gun, y_back, z_gun), (w_gun, y_back, z_gun), (w_keel, y_back, z_keel)],
                  (0, 1, 0), BLUE)
    roof_check(m, p_mesh, "Clipper ship prow")
    beam(m, (0.0, y_stem + .35, z_keel), (0.0, y_stem, z_gun), .28, COPPER)
    if lod < 2:
        for sgn in (-1, 1):
            beam(m, (sgn * w_gun, y_back, z_gun + .22), (sgn * .22, y_stem + .08, z_gun + .22), .22, CREAM)
        nu, nv = (14, 8) if lod == 0 else (6, 3)
        blob(m, (0.0, y_stem - .05, z_gun - 1.25), (.48, .38, .92), COPPER, nu, nv)
        blob(m, (0.0, y_stem - .10, z_gun - .22), (.34, .30, .36), CREAM, nu, nv)
        # Short angled bowsprit stub (clears gunwale rails & ends at y = -19.68 -> 0.32 m inside lot!)
        beam(m, (0.0, y_stem + .3, z_gun + .34), (0.0, -4.0 * D + .32, z_gun + .92), .22, IRON)
    PF = plane(-XH, yF, 1, 0)
    if lod < 2:
        for ax in (-7.2, 7.2):
            anchor(m, PF, ax + XH, G_ + 2.3, 4.4, IRON, lod)
    cy_c = yF + 13.5
    cp = octagon(0.0, cy_c, 2.6)
    oct_walls(m, g, cp, zr - .8, zr + 2.8, STONE, lod, strim, [(1.0, zr + .3, zr + 2.2)])
    oct_roof(m, 0.0, cy_c, [(3.1, zr + 2.8), (2.7, zr + 3.6), (1.4, zr + 4.8), (0.0, zr + 5.6)], [COPPER], lod, "Crow's nest roof")
    if lod < 2:
        beam(m, (0.0, cy_c, zr + 5.6), (0.0, cy_c, zr + 6.9), .12, IRON)
        blob(m, (0.0, cy_c, zr + 6.2), (.32, .32, .32), CREAM, 6, 3)
    if lod == 0:
        runs = [
            (PF, [x + XH for x in (-11.2, 11.2)], 2 * XH),
            (plane(-XH, end, 0, -1), [end - y for y in sb], end - yF),
            (plane(XH, yF, 0, 1), [y - yF for y in sb], end - yF),
            (plane(XH, end, -1, 0), [XH - x for x in rb], 2 * XH),
        ]
        for Q, us, L in runs:
            for u in us:
                porthole(m, Q, u, G_ + 4.1, .68, CREAM, lod)
                shell(m, Q, u, 4.3, .82, 0, fan=CREAM, rib=COPPER, n=15, lobe=8, k=.55)
            frieze(m, Q, .6, L - .6, top - .22, .75, IRON, lod)
            frieze(m, Q, .6, L - .6, G_ + .38, .65, COPPER, lod)


def walrus_hall(m, g, lod, W, D, v):
    """Walrus Bathhouse (5x4): Distinct Gilded-Age coastal mansard thermal bathhouse in granite & silver shingle,
    flanked by twin octagonal copper-domed corner pavilions, crowned by a 13 m lofted reclining copper Walrus with
    massive sweeping ivory tusks."""
    XH = 4.0 * W - SM
    yF, end = -4.0 * D + 1.0, 4.0 * D - .6
    G_, top = 4.8, 8.8
    ym = (yF + end) / 2
    trim, strim = trims(lod, "GreyBlue")
    sw = {"balance": "Walrus Bathhouse coastal mansard thermal hall", "rhythm": "arched thermal bath bays"}
    st = style(top, [(0.0, G_, "StoneBase"), (G_, top, "ShingleSilver")],
               [(1.55, .9, 3.7, "bay"), (1.15, G_ + .8, G_ + 2.9)],
               belts=(G_,), plinth=(.68, .05, "Greystone"), corners=False, frieze=.38, belt_mat=STONE)
    fb = spread(-XH, XH, 3.6)
    dc = fb[len(fb) // 2]
    holes = []
    fw = Wall((-XH, yF), (XH, yF))
    for bx in (fb[len(fb) // 2 - 1], fb[len(fb) // 2 + 1]):
        holes.append((fw.u_of(bx) - .9, fw.u_of(bx) + .9, 0.0, 3.7, "door"))
    # Omit wall bays occluded by the twin front octagonal corner pavilions (tx = +-(XH - 2.38), ap = 2.50 -> span ~5.1 m)
    fb_omit = [(fb[len(fb) // 2 - 1], 0), (fb[len(fb) // 2 + 1], 0)]
    for bx in fb:
        if abs(bx) > XH - 5.2:
            fb_omit += [(bx, 0), (bx, 1)]
    wall(m, g, st, (-XH, yF), (XH, yF), "x", "x", fb, lod, door=(dc, 2.2, 3.8), trim=trim,
         omit=fb_omit, holes=holes, waive=sw)
    sb = spread(yF, end, 3.6, odd=False)
    sb_omit = [(by, s_) for by in sb if by < yF + 5.2 for s_ in (0, 1)]
    wall(m, g, st, (-XH, end), (-XH, yF), "x", "x", sb, lod, trim=strim, omit=sb_omit, waive=sw)
    wall(m, g, st, (XH, yF), (XH, end), "x", "x", sb, lod, trim=strim, omit=sb_omit, waive=sw)
    rb = spread(-XH, XH, 3.6)
    wall(m, g, st, (XH, end), (-XH, end), "x", "x", rb, lod, door=(rb[len(rb) // 2], 1.6, 3.2), trim=strim, waive=sw)
    # Steep blue-grey Slate mansard roof frustum (watertight closed solid, 8.8 -> 12.6 m)
    z_deck = 12.6
    ins = 1.6
    ov = .35
    rt = Mesh()
    b0 = [(-XH - ov, yF - ov, top), (XH + ov, yF - ov, top), (XH + ov, end + ov, top), (-XH - ov, end + ov, top)]
    t0 = [(-XH + ins, yF + ins, z_deck), (XH - ins, yF + ins, z_deck), (XH - ins, end - ins, z_deck), (-XH + ins, end - ins, z_deck)]
    for k in range(4):
        nk = (k + 1) % 4
        q = [b0[k], b0[nk], t0[nk], t0[k]]
        c = sum((Vector(p_) for p_ in q), Vector()) / 4
        rt.facing(q, (c.x, c.y - ym, 0.35), "Slate")
    rt.facing(t0, (0, 0, 1), "TinFlat")
    rt.facing(b0[::-1], (0, 0, -1), STONE)
    roof_check(m, rt, "Walrus Bathhouse mansard")
    # Twin octagonal copper-domed corner bathhouse pavilions standing 12 cm proud of walls & 35 cm above mansard deck (zero coplanar!)
    z_turret = z_deck + 0.35
    for sgn in (-1, 1):
        tx = sgn * (XH - 2.38)
        ty = yF + 2.38
        ap_t = 2.50
        tp = octagon(tx, ty, ap_t)
        oct_walls(m, g, tp, 0.0, z_turret, STONE, lod, strim, [(1.0, 1.0, 3.6), (1.0, 5.6, 7.8), (0.95, 9.8, 11.8)])
        tprof = ([(ap_t + .30, z_turret), (1.8, z_turret + 2.0), (0.0, z_turret + 4.1)] if lod == 2 else
                 [(ap_t + .30, z_turret), (ap_t + .25, z_turret + .7), (1.8, z_turret + 2.0), (0.8, z_turret + 3.2), (0.0, z_turret + 4.1)])
        oct_roof(m, tx, ty, tprof, [COPPER], lod, "Bathhouse corner cupola")
        if lod < 2:
            beam(m, (tx, ty, z_turret + 4.1), (tx, ty, z_turret + 5.1), .10, IRON)
            blob(m, (tx, ty, z_turret + 4.5), (.24, .24, .24), CREAM, 6, 3)
    # Stepped limestone plinth on the mansard deck carrying our 13 m lofted reclining copper Walrus!
    # Front of plinth stops cleanly at ym - 3.8 so the downward-sweeping ivory tusks stand bold against the slate roof!
    wbox(m, -4.4, 4.4, ym - 3.8, ym + 5.6, z_deck + E, z_deck + 1.35, STONE, ("z-",))
    if lod < 2:
        wbox(m, -4.65, 4.65, ym - 4.05, ym + 5.85, z_deck + 1.35 + E, z_deck + 1.70, CREAM, ("z-",))
    walrus(m, 0.0, ym - 0.8, z_deck + (1.70 if lod < 2 else 1.35), 13.0, lod)
    # Coastal bathhouse ornament: scallop shells cleanly below the 4.74 m belt (zero coplanar!), portholes & fish frieze
    PF = plane(-XH, yF, 1, 0)
    ent_xs = {fb[len(fb) // 2 - 1], dc, fb[len(fb) // 2 + 1]}
    if lod < 2:
        for bx in ent_xs:
            shell(m, PF, bx + XH, 3.90, 1.15, lod, fan=CREAM, rib=COPPER, n=13, lobe=6, k=.65)
    if lod == 0:
        runs = [
            (PF, [x + XH for x in fb if abs(x) < XH - 4.8], [x + XH for x in fb if abs(x) < XH - 4.8 and x not in ent_xs], 2 * XH, 5.0),
            (plane(-XH, end, 0, -1), [end - y for y in sb if y > yF + 4.8], [end - y for y in sb if y > yF + 4.8], end - yF, 0.6),
            (plane(XH, yF, 0, 1), [y - yF for y in sb if y > yF + 4.8], [y - yF for y in sb if y > yF + 4.8], end - yF, 5.0),
            (plane(XH, end, -1, 0), [XH - x for x in rb], [XH - x for x in rb], 2 * XH, 0.6),
        ]
        for Q, us_all, us_g, L, pad in runs:
            for u in us_all:
                porthole(m, Q, u, G_ + 3.45, .58, CREAM, lod)
            for u in us_g:
                shell(m, Q, u, 3.92, .72, 0, fan=CREAM, rib=COPPER, n=11, lobe=6, k=.55)
            frieze(m, Q, pad, L - pad, top - .20, .72, BLUE, lod)


def nautilus_gallery(m, g, lod, W, D, v):
    """Nautilus Marine Gallery (4x3): Distinct symmetrical Beaux-Arts limestone & cream gallery with a raised
    central triumphal portal pavilion carrying the spiral nautilus relief, flanked by copper-hipped wings with
    porthole medallions, crowned by a colossal 7.5 m 3D logarithmic-spiral chambered Nautilus shell."""
    XH = 4.0 * W - SM
    yF, end = -4.0 * D + 1.0, 4.0 * D - .6
    top = 8.0
    ym = (yF + end) / 2
    trim, strim = trims(lod, "GreyBlue")
    sw = {"balance": "Nautilus Marine Gallery Beaux-Arts facade", "rhythm": "triumphal portal and gallery wings"}
    st = style(top, [(0.0, 5.0, STONE), (5.0, top, CREAM)], [(1.45, 1.0, 4.4, "bay")],
               belts=(5.0,), plinth=(.68, .05, "StoneBase"), corners=False, frieze=.42, belt_mat=STONE)
    # Main gallery wings (full XH width behind a raised central pavilion)
    fb = spread(-XH, XH, 3.6)
    dc = fb[len(fb) // 2]
    wall(m, g, st, (-XH, yF), (XH, yF), "x", "x", fb, lod, door=(dc, 2.4, 4.4), trim=trim,
         omit=[(dc, 0)], waive=dict(sw, glass="central nautilus portal"))
    sb = spread(yF, end, 3.6, odd=False)
    wall(m, g, st, (-XH, end), (-XH, yF), "x", "x", sb, lod, trim=strim, waive=sw)
    wall(m, g, st, (XH, yF), (XH, end), "x", "x", sb, lod, trim=strim, waive=sw)
    rb = spread(-XH, XH, 3.6)
    wall(m, g, st, (XH, end), (-XH, end), "x", "x", rb, lod, door=(rb[len(rb) // 2], 1.6, 3.2), trim=strim, waive=sw)
    # Copper hipped roof across the gallery wings (ridge 10.2 < z_pav 11.2 so it never pokes through the pavilion deck!)
    pavilion_roof(m, -XH - .35, XH + .35, yF - .35, end + .35, top + .006, 2.2, lod, COPPER, finial=False)
    # Raised central Beaux-Arts clerestory pavilion (x = -6.0..6.0, y = yF..yF+12.6, rising cleanly to 11.2 m!)
    px, py1, z_pav = 6.0, yF + 12.6, 11.2
    pst = style(z_pav, [(top, z_pav, STONE)], [(1.10, top + .55, z_pav - .85)], plinth=None, corners=False, frieze=.30, belt_mat=CREAM)
    wall(m, g, pst, (-px, yF - .02), (px, yF - .02), "x", "x", [-3.4, 3.4], lod, z0=top, trim=strim, waive=sw)
    wall(m, g, pst, (px, py1), (-px, py1), "x", "x", [-3.4, 0.0, 3.4], lod, z0=top, trim=strim, waive=sw)
    wall(m, g, pst, (-px, py1), (-px, yF - .02), "x", "x", [yF + 3.2, yF + 6.4, yF + 9.6], lod, z0=top, trim=strim, waive=sw)
    wall(m, g, pst, (px, yF - .02), (px, py1), "x", "x", [yF + 3.2, yF + 6.4, yF + 9.6], lod, z0=top, trim=strim, waive=sw)
    flat_roof(m, -px, px, yF - .02, py1, z_pav + .006)
    if lod < 2:
        wbox(m, -px - .15, px + .15, yF - .17, yF + .22, z_pav, z_pav + .55, CREAM, ("z-",))
        wbox(m, -px - .15, px + .15, py1 - .22, py1 + .15, z_pav, z_pav + .55, CREAM, ("z-",))
        wbox(m, -px - .14, -px + .22, yF + .22 + E, py1 - .22 - E, z_pav, z_pav + .53, CREAM, ("z-",))
        wbox(m, px - .22, px + .14, yF + .22 + E, py1 - .22 - E, z_pav, z_pav + .53, CREAM, ("z-",))
    # Spiral nautilus relief mounted boldly above the grand entrance arch (cleanly above 5.0 m belt & below 8.0 m cornice!)
    PF = plane(-XH, yF, 1, 0)
    nautilus(m, PF, XH, 5.55, 3.70, COPPER, lod)
    # Stepped limestone pedestal atop the central pavilion + colossal 8.2 m 3D logarithmic-spiral Nautilus shell!
    cy_n = yF + 6.3
    wbox(m, -3.9, 3.9, cy_n - 2.6, cy_n + 2.6, z_pav + E, z_pav + 1.15, STONE, ("z-",))
    wbox(m, -4.15, 4.15, cy_n - 2.85, cy_n + 2.85, z_pav + 1.15 + E, z_pav + 1.48, CREAM, ("z-",))
    nautilus_3d(m, -0.80, cy_n, z_pav + 1.48, 8.2, lod)
    # Gallery ornament: portholes, scallop shells & fish friezes around all 4 elevations (cleanly clear of 5.0 m belt!)
    if lod == 0:
        runs = [
            (PF, [x + XH for x in fb if abs(x) > 3.2], 2 * XH),
            (plane(-XH, end, 0, -1), [end - y for y in sb], end - yF),
            (plane(XH, yF, 0, 1), [y - yF for y in sb], end - yF),
            (plane(XH, end, -1, 0), [XH - x for x in rb], 2 * XH),
        ]
        for Q, us, L in runs:
            for u in us:
                porthole(m, Q, u, 6.25, .64, CREAM, lod)
                shell(m, Q, u, 4.55, .68, 0, fan=CREAM, rib=COPPER, n=13, lobe=6, k=.48)
            frieze(m, Q, .6, L - .6, top - .22, .72, BLUE, lod)


KINDS = dict(theatre=theatre, carousel=carousel, lodge=lodge, aquarium=aquarium, hall=hall,
             crab=crab, cod=cod, turtle=turtle, clipper=clipper,
             walrus=walrus_hall, nautilus=nautilus_gallery)


def build(lod, W=3, D=3, **variant):
    for k in ("palette", "lot"):
        variant.pop(k, None)
    kind = variant.pop("kind")
    m, g = Mesh(), Mesh()
    KINDS[kind](m, g, lod, W, D, variant)
    finish(m, g)
