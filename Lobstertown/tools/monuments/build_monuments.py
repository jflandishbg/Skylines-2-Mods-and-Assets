"""Claude's park monuments for Paris on the Delaware (2026-11-09).
Run:  blender -b --python build_monuments.py -- <out_dir> <atlas_dir> [name ...]
Writes, per monument, <out>/<name>/ with three FBX levels of detail and their maps, plus
<out>/_previews/<name>.png, <out>/_thumbs/<name>.png and <out>/props.json (tree, lamp and bollard positions).
No benches, anywhere: that is a project rule."""
import bpy, sys, os, json
from math import sin, cos, pi, radians
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcore import *

INSC_ROW = lambda i: (0.0, i / 6, 1.0, (i + 1) / 6)       # row i of the inscription tile


def ground(b, W, D, tile):
    b.box(-W / 2 + .1, -D / 2 + .1, -.4, W / 2 - .1, D / 2 - .1, .05, tile)


def hedge_L(b, x, y, sx, sy, arm=3.2, t=.8, h=.9):
    """L-shaped clipped hedge wrapping a corner at (x, y); sx, sy = +-1 point back toward the lot centre."""
    b.box(min(x, x + sx * arm), min(y, y + sy * t), .05, max(x, x + sx * arm), max(y, y + sy * t), h, HEDGE)
    b.box(min(x, x + sx * t), min(y + sy * t, y + sy * arm), .05, max(x, x + sx * t), max(y + sy * t, y + sy * arm), h, HEDGE)


# ------------------------------------------------------------------------------------------------------
def colonne(b):                                             # Colonne de l'Ecluse, 2x2 (16 x 16 m)
    L = b.lod; ground(b, 16, 16, GRV)
    b.cyl(0, 0, 6.2, .05, .09, PAV, 24 if L < 2 else 8, smooth=False)
    for r, z0, z1 in ((3.7, .09, .39), (3.15, .39, .69), (2.6, .69, .99)):
        b.cyl(0, 0, r, z0, z1, GRAN, 8, smooth=False, phase=pi / 8)
    b.box(-1.5, -1.5, .99, 1.5, 1.5, 1.4, GRAN)
    b.box(-1.2, -1.2, 1.4, 1.2, 1.2, 3.6, SMO)
    b.box(-1.45, -1.45, 3.6, 1.45, 1.45, 3.85, SMO); b.box(-1.3, -1.3, 3.85, 1.3, 1.3, 4.05, SMO)
    if L < 2:
        e, z0, z1, w = 1.215, 2.35, 2.72, 1.08               # the lock's date, cut on all four faces
        b.decal((-w, -e, z0), (w, -e, z0), (w, -e, z1), (-w, -e, z1), INSC, INSC_ROW(3), (0, -1, 0))
        b.decal((w, e, z0), (-w, e, z0), (-w, e, z1), (w, e, z1), INSC, INSC_ROW(3), (0, 1, 0))
        b.decal((e, -w, z0), (e, w, z0), (e, w, z1), (e, -w, z1), INSC, INSC_ROW(3), (1, 0, 0))
        b.decal((-e, w, z0), (-e, -w, z0), (-e, -w, z1), (-e, w, z1), INSC, INSC_ROW(3), (-1, 0, 0))
    b.lathe(0, 0, [(1.05, 4.05), (1.05, 4.25), (.95, 4.36), (.9, 4.5), (.8, 4.6)], SMO)
    n = (10, 5, 2)[L]                                       # shaft with a slight swell (entasis)
    b.lathe(0, 0, [(.75 - .13 * (k / n) ** 1.7, 4.6 + 11 * k / n) for k in range(n + 1)], SMO)
    if L < 2:
        for t in (.3, .62):
            r = .75 - .13 * t ** 1.7 + .035; z = 4.6 + 11 * t
            b.lathe(0, 0, [(r - .04, z), (r, z + .04), (r, z + .26), (r - .04, z + .3)], VERD)
    b.lathe(0, 0, [(.62, 15.6), (.7, 15.72), (.95, 16.0), (1.0, 16.0), (1.0, 16.15), (0, 16.15)], SMO)
    b.box(-1.05, -1.05, 16.15, 1.05, 1.05, 16.4, SMO)
    b.cyl(0, 0, .55, 16.4, 17.5, VERD, 8, smooth=False, phase=pi / 8)      # the lock-keeper's lantern
    if L < 2: b.cyl(0, 0, .72, 17.5, 17.62, VERD, 8, smooth=False, phase=pi / 8)
    b.lathe(0, 0, [(.62, 17.62), (.55, 17.9), (.38, 18.15), (.15, 18.32), (.08, 18.5)], VERD, 8 if L else 12)
    b.ball(0, 0, 18.7, .24, GILT, 8 if L else 12)
    if L < 2:
        for sx in (-1, 1):
            for sy in (-1, 1): hedge_L(b, sx * 7.6, sy * 7.6, -sx, -sy)
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.prop("tree", sx * 5.9, sy * 5.9); b.prop("lamp", sx * 6.9, sy * 2.6)
    for k in range(8):
        a = pi / 8 + k * pi / 4; b.prop("bollard", 4.9 * cos(a), 4.9 * sin(a))
    return (16, 16)


def kiosque(b):                                             # Kiosque des Mariniers, 2x2 (16 x 16 m)
    L = b.lod; ph = pi / 8; ground(b, 16, 16, GRV)
    b.cyl(0, 0, 5.7, .05, .08, PAV, 24 if L < 2 else 8, smooth=False)
    b.box(-1.7, -7.9, .05, 1.7, -5.2, .08, PAV)
    b.cyl(0, 0, 4.2, .05, 1.05, GRAN, 8, smooth=False, phase=ph)
    b.cyl(0, 0, 4.35, 1.05, 1.17, SMO, 8, smooth=False, phase=ph)
    b.cyl(0, 0, 4.0, 1.17, 1.2, WOOD, 8, smooth=False, phase=ph)
    ns = 5 if L < 2 else 2                                  # front steps, flanked by cheek walls
    for i in range(ns):
        b.box(-1.3, -3.88 - (i + 1) * 1.7 / ns, .05, 1.3, -3.86, 1.17 - (i + 1) * .935 / ns, GRAN)
    if L < 2:
        for sx in (-1, 1): b.box(min(sx * 1.3, sx * 1.62), -5.75, .05, max(sx * 1.3, sx * 1.62), -3.86, 1.17, GRAN, top=SMO)
    V = [(3.85 * cos(ph + k * pi / 4), 3.85 * sin(ph + k * pi / 4)) for k in range(8)]
    for x, y in V:
        b.lathe(x, y, [(.16, 1.2), (.16, 1.4), (.09, 1.5), (.09, 4.3), (.17, 4.6)] if L < 2 else [(.11, 1.2), (.11, 4.6)], IRON, (8, 6, 3)[L])
    for k in range(8):
        if k == 5: continue                                  # the bay over the steps stays open
        (xa, ya), (xb, yb) = V[k], V[(k + 1) % 8]
        if L < 2: b.beam((xa, ya, 2.1), (xb, yb, 2.1), .08, .07, IRON)
        if L < 2: b.beam((xa, ya, 1.36), (xb, yb, 1.36), .06, .05, IRON)
        if L == 0:
            for j in range(1, 10):
                x, y = xa + (xb - xa) * j / 10, ya + (yb - ya) * j / 10
                b.box(x - .018, y - .018, 1.38, x + .018, y + .018, 2.07, IRON, skip="bt")
    b.lathe(0, 0, [(4.05, 4.6), (4.05, 4.95), (3.8, 4.95), (3.8, 4.6), (4.05, 4.6)], IRON, 8, ph, smooth=False)
    if L < 2:
        y = -4.05 * cos(pi / 8) - .02                        # painted name board over the steps
        b.decal((-1.05, y, 4.6), (1.05, y, 4.6), (1.05, y, 4.95), (-1.05, y, 4.95), INSC, INSC_ROW(5), (0, -1, 0))
    b.lathe(0, 0, [(0, 4.95), (4.7, 4.95)], WOOD, 8, ph, smooth=False)
    roof = [(4.7, 4.95), (4.7, 5.03), (3.7, 5.45), (2.7, 6.05), (1.7, 6.9), (1.0, 7.55), (.5, 8.1), (.38, 8.3)]
    b.lathe(0, 0, roof if L < 2 else [roof[0], roof[3], roof[5], roof[7]], ZINC, 8, ph, smooth=False)
    b.lathe(0, 0, [(.5, 8.3), (.5, 8.75), (.62, 8.78), (.3, 9.1), (.06, 9.32)], VERD, 8, ph, smooth=False)
    b.ball(0, 0, 9.5, .17, GILT, 8)
    if L < 2:
        for sx in (-1, 1):
            for sy in (-1, 1): hedge_L(b, sx * 7.6, sy * 7.6, -sx, -sy)
    for sx in (-1, 1):
        for sy in (-1, 1): b.prop("tree", sx * 5.9, sy * 5.9)
        b.prop("lamp", sx * 2.5, -6.9); b.prop("lamp", sx * 6.9, 0)
    return (16, 16)


def morris(b):                                              # Square de la Colonne Morris, 1x1 (8 x 8 m)
    L = b.lod; ground(b, 8, 8, PAV)
    b.box(-3.7, 3.0, .05, 3.7, 3.7, .9, HEDGE)
    for sx in (-1, 1): b.box(min(sx * 3.0, sx * 3.7), .8, .05, max(sx * 3.0, sx * 3.7), 3.0, .9, HEDGE)
    cx, cy = -1.5, -.9                                      # the poster column
    b.lathe(cx, cy, [(.9, .05), (.9, .3), (.78, .45)], IRON)
    n = (16, 10, 6)[L]; r = .75
    for i in range(n):
        A0, A1 = 2 * pi * i / n, 2 * pi * (i + 1) / n
        P = lambda A, z: (cx + r * cos(A), cy + r * sin(A), z); nn = (cos((A0 + A1) / 2), sin((A0 + A1) / 2), 0)
        b.decal(P(A0, .45), P(A1, .45), P(A1, 1.85), P(A0, 1.85), POST, (i / n, .5, (i + 1) / n, 1), nn, smooth=True)
        b.decal(P(A0, 1.85), P(A1, 1.85), P(A1, 3.25), P(A0, 3.25), POST, ((i / n + .5) % 1, 0, (i / n + .5) % 1 + 1 / n, .5), nn, smooth=True)
    b.lathe(cx, cy, [(.75, 3.25), (.92, 3.35), (.92, 3.5), (1.1, 3.55), (1.1, 3.6), (.85, 3.75), (.7, 4.1), (.45, 4.45), (.2, 4.65), (.1, 4.9), (0, 5.0)], IRON)
    b.ball(cx, cy, 5.05, .09, VERD, 8)
    fx, fy = 1.8, -.2                                      # drinking fountain: four slim colonnettes under a dome
    b.cyl(fx, fy, .6, .05, .3, IRON, 8, smooth=False)
    b.lathe(fx, fy, [(.45, .3), (.4, .45), (.33, 1.1), (.5, 1.2), (.5, 1.3), (0, 1.3)], IRON, (12, 8, 6)[L])
    if L < 2:
        b.cyl(fx, fy, .4, 1.3, 1.32, WATER, 12)
        for k in range(4):
            a = pi / 4 + k * pi / 2; b.cyl(fx + .36 * cos(a), fy + .36 * sin(a), .045, 1.3, 2.15, IRON, 6)
    else: b.cyl(fx, fy, .12, 1.3, 2.15, IRON, 4)
    b.lathe(fx, fy, [(0, 2.15), (.52, 2.15), (.52, 2.25), (.4, 2.45), (.22, 2.7), (.08, 2.85), (.05, 3.02)], IRON, (12, 8, 6)[L])
    b.ball(fx, fy, 3.06, .07, VERD, 8)
    for x, y in ((2.2, 1.9), (-2.2, 1.9)):
        if L < 2: b.cyl(x, y, .75, .05, .07, IRON, 12, smooth=False)       # cast-iron tree grates
        b.prop("tree", x, y)
    b.prop("lamp", 3.0, -3.2)
    return (8, 8)


def arc(b):                                                 # Arc des Deux Rives, 3x2 (24 x 16 m)
    L = b.lod; ground(b, 24, 16, PAV); a, zs, X, Y, zt = 2.75, 6.0, 6.5, 2.5, 10.5
    bx = lambda sx, x0, x1, y0, z0, y1, z1, t, **k: b.box(min(sx * x0, sx * x1), y0, z0, max(sx * x0, sx * x1), y1, z1, t, **k)
    for sx in (-1, 1): bx(sx, a, X + .15, -Y - .15, .05, Y + .15, 1.5, GRAN)
    for ny in (-1, 1): b.arch_face(ny * Y, ny, -X, X, 1.5, zt, 0, a, 1.5, zs, ASH)
    for sx in (-1, 1): b.face([(sx * X, -Y, 1.5), (sx * X, Y, 1.5), (sx * X, Y, zt), (sx * X, -Y, zt)], ASH, (sx, 0, 0))
    b.arch_soffit(-Y, Y, 0, a, 1.5, zs, SMO)
    if L < 2:
        for sx in (-1, 1):
            bx(sx, a - .08, X + .12, -Y - .12, 5.8, Y + .12, 6.1, SMO, skip="")
            for x0 in (3.1, 5.65):
                for ny in (-1, 1): bx(sx, x0, x0 + .6, min(ny * Y, ny * (Y + .22)), 1.5, max(ny * Y, ny * (Y + .22)), zt, SMO)
            for ny in (-1, 1):
                b.roundel(sx * 4.675, ny * Y, 8.3, .62, ny, VERD)
                if L == 0: bx(sx, 3.95, 5.4, min(ny * Y, ny * (Y + .07)), 2.4, max(ny * Y, ny * (Y + .07)), 5.6, SMO)
        for ny in (-1, 1):
            b.arch_band(ny * Y, ny, 0, a, a + .5, zs, .1, SMO)
            b.box(-.42, min(ny * Y, ny * (Y + .3)), 8.4, .42, max(ny * Y, ny * (Y + .3)), 9.6, SMO, skip="")
    b.box(-X - .25, -Y - .25, zt, X + .25, Y + .25, zt + .28, SMO, skip="")
    b.box(-X - .5, -Y - .5, zt + .28, X + .5, Y + .5, 11.1, SMO, skip="")
    b.box(-6.3, -2.3, 11.1, 6.3, 2.3, 13.4, ASH)
    if L < 2:
        b.decal((-4.5, -2.32, 11.5), (4.5, -2.32, 11.5), (4.5, -2.32, 13.0), (-4.5, -2.32, 13.0), INSC, INSC_ROW(0), (0, -1, 0))
        b.decal((4.5, 2.32, 11.5), (-4.5, 2.32, 11.5), (-4.5, 2.32, 13.0), (4.5, 2.32, 13.0), INSC, INSC_ROW(1), (0, 1, 0))
    b.box(-6.55, -2.55, 13.4, 6.55, 2.55, 13.68, SMO, skip="")
    b.box(-6.0, -2.0, 13.68, 6.0, 2.0, 14.1, SMO)
    b.box(-2.2, -1.4, 14.1, 2.2, 1.4, 14.6, SMO)
    b.urn(0, 0, 14.6, 1.7, VERD)
    for sx in (-1, 1):
        for sy in (-1, 1): b.urn(sx * 6.27, sy * 2.27, 13.68, .95)
        if L < 2: b.box(min(sx * 10.3, sx * 11.3), -6.6, .05, max(sx * 10.3, sx * 11.3), 6.6, .8, HEDGE)
        for y in (-4.6, 0, 4.6): b.prop("tree", sx * 10.8, y)
        for sy in (-1, 1): b.prop("lamp", sx * 8.7, sy * 5.6)
    for k in range(9):
        x = -9 + k * 2.25
        if abs(x) > 2.6:
            b.prop("bollard", x, -7.3); b.prop("bollard", x, 7.3)
    return (24, 16)


def fontaine(b):                                            # Fontaine de la Grotte des Bateliers, 2x3 (16 x 24 m)
    L = b.lod; ground(b, 16, 24, GRV); yf, yb, zt = 8.2, 10.4, 6.6
    b.box(-5.2, -10.3, .05, 5.2, 8.05, .08, PAV)
    b.box(-6.15, yf - .15, .05, 6.15, yb + .15, .6, GRAN)
    niches = ((-4.3, .85, 1.7, 3.6, .6, -6, -2.6), (0, 1.9, .6, 3.8, 1.2, -2.6, 2.6), (4.3, .85, 1.7, 3.6, .6, 2.6, 6))
    for cx, a, zb, zs, d, x0, x1 in niches:                 # rusticated grotto wall with three arched niches
        b.arch_face(yf, -1, x0, x1, .6, zt, cx, a, zb, zs, RUST)
        b.arch_soffit(yf, yf + d, cx, a, zb, zs, SMO, floor_tile=SMO)
        b.arch_back(yf + d, -1, cx, a, zb, zs, SHADE)
        if cx: b.urn(cx, yf + .32, zb, 1.25, VERD)
    for sx in (-1, 1): b.face([(sx * 6, yf, .6), (sx * 6, yb, .6), (sx * 6, yb, zt), (sx * 6, yf, zt)], RUST, (sx, 0, 0))
    b.face([(-6, yb, .6), (6, yb, .6), (6, yb, zt), (-6, yb, zt)], ASH, (0, 1, 0))
    b.box(-1.4, yf + .1, .6, 1.4, yf + 1.2, 1.3, SMO, top=WATER)             # cascade in the middle niche
    b.box(-.9, yf + .5, 1.3, .9, yf + 1.2, 2.1, SMO, top=WATER)
    if L < 2:
        b.roundel(0, yf + 1.2, 3.1, .45, -1, VERD)
        b.face([(-.5, yf + .07, .5), (.5, yf + .07, .5), (.5, yf + .07, 1.3), (-.5, yf + .07, 1.3)], WATER, (0, -1, 0))
        for sx in (-1, 1):
            for x0 in (2.3, 5.45): b.box(min(sx * x0, sx * (x0 + .6)), yf - .25, .6, max(sx * x0, sx * (x0 + .6)), yf, zt, SMO)
    b.box(-6.2, yf - .2, zt, 6.2, yb + .2, 7.3, SMO, skip="")
    if L < 2: b.decal((-2.1, yf - .22, zt), (2.1, yf - .22, zt), (2.1, yf - .22, 7.3), (-2.1, yf - .22, 7.3), INSC, INSC_ROW(2), (0, -1, 0))
    b.box(-6.5, yf - .5, 7.3, 6.5, yb + .5, 7.6, SMO, skip="")
    b.gable(-3.4, 3.4, yf - .35, yb + .35, 7.6, 9.1, SMO, roof=ZINC)
    if L < 2: b.roundel(0, yf - .35, 8.15, .42, -1, VERD)
    for sx in (-1, 1):
        b.box(min(sx * 4.6, sx * 6.3), yf - .2, 7.6, max(sx * 4.6, sx * 6.3), yb + .2, 8.3, SMO)
        b.urn(sx * 5.45, 9.3, 8.3, 1.2)
        b.box(min(sx * 2.75, sx * 3.2), -8.6, .05, max(sx * 2.75, sx * 3.2), 8.05, .7, SMO)       # basin walls
        if L < 2:
            b.box(min(sx * 6.5, sx * 7.3), -10, .05, max(sx * 6.5, sx * 7.3), 8, .9, HEDGE)
            for y in (-8.375, -2.9, 2.6):
                b.box(sx * 2.975 - .36, y - .36, .7, sx * 2.975 + .36, y + .36, 1.2, SMO); b.urn(sx * 2.975, y, 1.2, .95)
        for y in (-9, -4.5, 0, 4.5): b.prop("tree", sx * 5.85, y)
        b.prop("lamp", sx * 4.3, -10.9); b.prop("lamp", sx * 4.3, 6.9)
    b.box(-2.75, -8.6, .05, 2.75, -8.15, .7, SMO)
    b.face([(-2.75, -8.15, .52), (2.75, -8.15, .52), (2.75, 8.05, .52), (-2.75, 8.05, .52)], WATER, (0, 0, 1))
    for y in (-4.6, 2.2):                                   # two tazza jets standing in the long basin
        b.lathe(0, y, [(.45, .5), (.45, .85), (.28, 1.0), (.22, 1.6), (.5, 1.85), (1.3, 2.05), (1.35, 2.2), (1.2, 2.2)], SMO, (16, 10, 6)[L])
        b.lathe(0, y, [(1.2, 2.17), (0, 2.17)], WATER, (16, 10, 6)[L], smooth=False)
        if L < 2: b.lathe(0, y, [(.13, 2.17), (.08, 2.8), (0, 2.92)], VERD, 8)
    return (16, 24)


MONUMENTS = {"NA_PdDColonneEcluse": colonne, "NA_PdDKiosqueMariniers": kiosque, "NA_PdDSquareColonneMorris": morris,
             "NA_PdDArcDeuxRives": arc, "NA_PdDFontaineGrotte": fontaine}

if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:]; out, atlas = os.path.abspath(args[0]), os.path.abspath(args[1]); want = args[2:] or list(MONUMENTS)
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    pj = os.path.join(out, "props.json"); allprops = json.load(open(pj, encoding="utf-8")) if os.path.exists(pj) else {}
    for name in want:
        for lod in (0, 1, 2):
            b = B(lod); W, D = MONUMENTS[name](b); ob = b.finish(name)
            ob.data.materials.append(material("m", atlas))
            tris = len(ob.data.polygons)
            if lod == 0:
                ex = standins(b.props)
                os.makedirs(os.path.join(out, "_previews"), exist_ok=True); os.makedirs(os.path.join(out, "_thumbs"), exist_ok=True)
                render(ob, os.path.join(out, "_previews", name + ".png"), (1400, 1050), False, ex)
                for o in ex: o.hide_render = True
                render(ob, os.path.join(out, "_thumbs", name + ".png"), (512, 512), True)
                for o in ex: bpy.data.objects.remove(o)
                allprops[name] = {"lot_m": [W, D], "props": [{"kind": k, "position_lot_m": [round(x + W / 2, 2), round(y + D / 2, 2), 0],
                                                              **({"size_m": s} if s else {})} for k, x, y, s in b.props]}
            export(ob, name, lod, os.path.join(out, name), atlas)
            print(f"BUILT {name} LOD{lod}: {tris} tris")
            bpy.data.objects.remove(ob)
    json.dump(allprops, open(pj, "w", encoding="utf-8"), indent=1)
