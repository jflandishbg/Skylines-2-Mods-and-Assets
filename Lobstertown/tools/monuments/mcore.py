"""Shared kit for Claude's park monuments (2026-11-09). Imported by build_monuments.py inside Blender.
Everything is modelled in metres with the lot centred on the origin and the street at -Y, then exported in
centimetres the way the CS2 importer wants. All surfaces sample one 4x4 swatch atlas (see make_atlas.py)."""
import bpy, bmesh, math, os, shutil
from math import sin, cos, pi, hypot, ceil, floor, radians
from mathutils import Vector, Matrix

(ASH, SMO, PAV, GRV, IRON, VERD, WATER, GILT, WOOD, GRAN, ZINC, POST, INSC, RUST, SHADE, HEDGE) = range(16)
REP = {ASH: 2, SMO: 3, PAV: 2, GRV: 3, IRON: 1.5, VERD: 1.5, WATER: 4, GILT: 1.5, WOOD: 2, GRAN: 2, ZINC: 2,
       RUST: 2.5, SHADE: 3, HEDGE: 2}                     # metres covered by one texture repeat
SPAN = 2.56                                              # repeats held by one atlas tile
MAPS = ("BaseColor", "Normal", "MaskMap", "ControlMask", "Emissive")


def atl(tile, u, v):
    """Repeat-space (0..2.5) inside a tile -> atlas UV."""
    return ((tile % 4 + (0.03 + u) / SPAN) / 4, 1 - (tile // 4 + 1) / 4 + ((0.03 + v) / SPAN) / 4)


def fit(uvs):
    mu, mv = floor(min(u for u, v in uvs)), floor(min(v for u, v in uvs))
    uvs = [(u - mu, v - mv) for u, v in uvs]
    m = max(max(u, v) for u, v in uvs)
    k = 2.5 / m if m > 2.5 else 1
    return [(u * k, v * k) for u, v in uvs]


class B:
    def __init__(s, lod):
        s.lod = lod
        s.seg = (24, 12, 6)[lod]          # round things
        s.aseg = (16, 8, 4)[lod]          # arches
        s.bm = bmesh.new()
        s.t = s.bm.faces.layers.int.new("tile"); s.fx = s.bm.faces.layers.int.new("fixed")
        s.uv = s.bm.loops.layers.uv.new("UVMap")
        s.props = []

    # ---- basic faces -------------------------------------------------------------------------------
    def face(s, pts, tile, n=None, uvs=None, smooth=False):
        vs = [s.bm.verts.new(p) for p in pts]
        try: f = s.bm.faces.new(vs)
        except ValueError: return None
        f.normal_update()
        if f.calc_area() < 1e-8:
            s.bm.faces.remove(f); return None
        if n is not None and f.normal.dot(Vector(n)) < 0: f.normal_flip()
        f[s.t] = tile; f.smooth = smooth
        if uvs:
            m = dict(zip(vs, uvs)); f[s.fx] = 1
            for l in f.loops: l[s.uv].uv = m[l.vert]
        return f

    def decal(s, p0, p1, p2, p3, tile, rect, n=None, smooth=False):
        """p0 bottom-left, p1 bottom-right, p2 top-right, p3 top-left (seen from outside).
        rect = (x0, y0, x1, y1) as fractions of the tile, y measured DOWN from the tile's top edge."""
        c, r = tile % 4, tile // 4; x0, y0, x1, y1 = rect
        U = lambda x: (c + x) / 4; V = lambda y: 1 - (r + y) / 4
        return s.face([p0, p1, p2, p3], tile, n, [(U(x0), V(y1)), (U(x1), V(y1)), (U(x1), V(y0)), (U(x0), V(y0))], smooth)

    def box(s, x0, y0, z0, x1, y1, z1, tile, skip="b", top=None):
        F = s.face
        if "t" not in skip: F([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], tile if top is None else top, (0, 0, 1))
        if "b" not in skip: F([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)], tile, (0, 0, -1))
        if "f" not in skip: F([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], tile, (0, -1, 0))
        if "k" not in skip: F([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], tile, (0, 1, 0))
        if "l" not in skip: F([(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)], tile, (-1, 0, 0))
        if "r" not in skip: F([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], tile, (1, 0, 0))

    def beam(s, p, q, w, h, tile):
        """Horizontal bar from p to q (centre line), w wide, h tall."""
        p, q = Vector(p), Vector(q); d = q - p
        if d.length < 1e-6: return
        u = d.normalized(); sd = Vector((-u.y, u.x, 0)) * w / 2; up = Vector((0, 0, h / 2))
        for a, b in ((sd, up), (-sd, up), (up, sd), (-up, sd)):
            s.face([p + a - b, q + a - b, q + a + b, p + a + b], tile, a)
        for e, n in ((p, -u), (q, u)):
            s.face([e - sd - up, e + sd - up, e + sd + up, e - sd + up], tile, n)

    # ---- turned shapes -----------------------------------------------------------------------------
    def lathe(s, cx, cy, prof, tile, seg=None, phase=0.0, smooth=True):
        """Spin a profile [(radius, z), ...] round a vertical axis. Draw the profile so the outside is on
        the right of the direction of travel (up the outside, then inward across the top)."""
        seg = seg or s.seg; R = REP.get(tile, 2); rref = max(r for r, z in prof)
        pts = [prof[0]]
        for (r0, z0), (r1, z1) in zip(prof, prof[1:]):
            n = max(1, ceil(hypot(r1 - r0, z1 - z0) / (1.5 * R))) if (smooth and s.lod < 2) else 1
            pts += [(r0 + (r1 - r0) * k / n, z0 + (z1 - z0) * k / n) for k in range(1, n + 1)]
        cum = [0.0]
        for (r0, z0), (r1, z1) in zip(pts, pts[1:]): cum.append(cum[-1] + hypot(r1 - r0, z1 - z0))
        P = lambda r, z, A: (cx + r * cos(A), cy + r * sin(A), z)
        for i in range(seg):
            A0, A1 = phase + 2 * pi * i / seg, phase + 2 * pi * (i + 1) / seg; Am = (A0 + A1) / 2
            for j in range(len(pts) - 1):
                (r0, z0), (r1, z1) = pts[j], pts[j + 1]; dr, dz = r1 - r0, z1 - z0
                if abs(dr) + abs(dz) < 1e-9: continue
                ring = [(r0, z0, A0, cum[j])] + ([(r0, z0, A1, cum[j])] if r0 > 1e-6 else []) + \
                       [(r1, z1, A1, cum[j + 1])] + ([(r1, z1, A0, cum[j + 1])] if r1 > 1e-6 else [])
                if len(ring) < 3: continue
                uvs = None
                if smooth:
                    uvs = [atl(tile, u, v) for u, v in fit([(A * rref / R, c / R) for r, z, A, c in ring])]
                s.face([P(r, z, A) for r, z, A, c in ring], tile, (dz * cos(Am), dz * sin(Am), -dr), uvs, smooth)

    def cyl(s, cx, cy, r, z0, z1, tile, seg=None, smooth=True, phase=0.0, top=None):
        s.lathe(cx, cy, [(r, z0), (r, z1)], tile, seg, phase, smooth)
        s.lathe(cx, cy, [(r, z1), (0, z1)], tile if top is None else top, seg, phase, False)

    def ball(s, cx, cy, cz, r, tile, seg=None):
        n = max(3, (seg or s.seg) // 2)
        s.lathe(cx, cy, [(r * sin(pi * k / n), cz - r * cos(pi * k / n)) for k in range(n + 1)], tile, seg)

    def urn(s, cx, cy, z, k=1.0, tile=SMO):
        if s.lod == 2: return
        pr = [(.22, 0), (.22, .08), (.1, .18), (.1, .3), (.3, .5), (.36, .75), (.3, .95), (.18, 1.02), (.24, 1.1), (.24, 1.14), (0, 1.14)]
        s.lathe(cx, cy, [(r * k, z + h * k) for r, h in pr], tile, 12 if s.lod == 0 else 6)

    # ---- arches (walls face +-Y) -------------------------------------------------------------------
    def arc(s, cx, a, zs):
        return [(cx - a * cos(pi * k / s.aseg), zs + a * sin(pi * k / s.aseg)) for k in range(s.aseg + 1)]

    def arch_face(s, y, ny, x0, x1, z0, z1, cx, a, zb, zs, tile):
        """Wall face x0..x1, z0..z1 with a round-headed opening (centre cx, half-width a, sill zb, spring zs)."""
        n = (0, ny, 0); F = lambda q: s.face([(x, y, z) for x, z in q], tile, n)
        F([(x0, z0), (cx - a, z0), (cx - a, z1), (x0, z1)]); F([(cx + a, z0), (x1, z0), (x1, z1), (cx + a, z1)])
        if zb > z0 + 1e-6: F([(cx - a, z0), (cx + a, z0), (cx + a, zb), (cx - a, zb)])
        pts = s.arc(cx, a, zs)
        for (xa, za), (xb, zb2) in zip(pts, pts[1:]): F([(xa, za), (xb, zb2), (xb, z1), (xa, z1)])

    def arch_soffit(s, y0, y1, cx, a, zb, zs, tile, floor_tile=None):
        s.face([(cx - a, y0, zb), (cx - a, y1, zb), (cx - a, y1, zs), (cx - a, y0, zs)], tile, (1, 0, 0))
        s.face([(cx + a, y0, zb), (cx + a, y1, zb), (cx + a, y1, zs), (cx + a, y0, zs)], tile, (-1, 0, 0))
        pts = s.arc(cx, a, zs)
        for (xa, za), (xb, zb2) in zip(pts, pts[1:]):
            s.face([(xa, y0, za), (xa, y1, za), (xb, y1, zb2), (xb, y0, zb2)], tile, (cx - (xa + xb) / 2, 0, zs - (za + zb2) / 2))
        if floor_tile is not None:
            s.face([(cx - a, y0, zb), (cx + a, y0, zb), (cx + a, y1, zb), (cx - a, y1, zb)], floor_tile, (0, 0, 1))

    def arch_back(s, y, ny, cx, a, zb, zs, tile):
        s.face([(cx - a, y, zb), (cx + a, y, zb)] + [(x, y, z) for x, z in reversed(s.arc(cx, a, zs))], tile, (0, ny, 0))

    def arch_band(s, ywall, ny, cx, a0, a1, zs, proud, tile):
        """Moulded band round an arch head, standing 'proud' of the wall."""
        yf = ywall + ny * proud; pi_, po = s.arc(cx, a0, zs), s.arc(cx, a1, zs)
        for k in range(s.aseg):
            (xa, za), (xb, zb), (xc, zc), (xd, zd) = pi_[k], pi_[k + 1], po[k + 1], po[k]
            s.face([(xa, yf, za), (xb, yf, zb), (xc, yf, zc), (xd, yf, zd)], tile, (0, ny, 0))
            s.face([(xd, yf, zd), (xc, yf, zc), (xc, ywall, zc), (xd, ywall, zd)], tile, ((xc + xd) / 2 - cx, 0, (zc + zd) / 2 - zs))
            s.face([(xa, yf, za), (xb, yf, zb), (xb, ywall, zb), (xa, ywall, za)], tile, (cx - (xa + xb) / 2, 0, zs - (za + zb) / 2))

    def roundel(s, cx, y, cz, r, ny, tile, proud=0.06, seg=None):
        seg = seg or max(8, s.seg // 2); yf = y + ny * proud
        ring = [(cx + r * cos(2 * pi * k / seg), cz + r * sin(2 * pi * k / seg)) for k in range(seg)]
        s.face([(x, yf, z) for x, z in ring], tile, (0, ny, 0))
        for (xa, za), (xb, zb) in zip(ring, ring[1:] + ring[:1]):
            s.face([(xa, yf, za), (xb, yf, zb), (xb, y, zb), (xa, y, za)], tile, ((xa + xb) / 2 - cx, 0, (za + zb) / 2 - cz))

    def gable(s, x0, x1, y0, y1, z0, zt, tile, roof=None):
        xm = (x0 + x1) / 2; roof = tile if roof is None else roof
        s.face([(x0, y0, z0), (x1, y0, z0), (xm, y0, zt)], tile, (0, -1, 0))
        s.face([(x0, y1, z0), (x1, y1, z0), (xm, y1, zt)], tile, (0, 1, 0))
        s.face([(x0, y0, z0), (x0, y1, z0), (xm, y1, zt), (xm, y0, zt)], roof, (-1, 0, 1))
        s.face([(x1, y0, z0), (x1, y1, z0), (xm, y1, zt), (xm, y0, zt)], roof, (1, 0, 1))

    def prop(s, kind, x, y, size=None):
        s.props.append((kind, x, y, size))

    # ---- finishing ---------------------------------------------------------------------------------
    def _subdivide(s):
        bm = s.bm
        for tile, R in REP.items():
            step = 1.5 * R
            for ax in range(3):
                def big(p=None):
                    out = []
                    for f in bm.faces:
                        if f[s.t] != tile or f[s.fx] or abs(f.normal[ax]) > 0.9: continue
                        c = [v.co[ax] for v in f.verts]; lo, hi = min(c), max(c)
                        if hi - lo > step + 1e-3 and (p is None or (lo < p - 0.02 and hi > p + 0.02)): out.append(f)
                    return out
                fs = big()
                if not fs: continue
                lo = min(v.co[ax] for f in fs for v in f.verts); hi = max(v.co[ax] for f in fs for v in f.verts)
                k = floor(lo / step) + 1
                while k * step < hi - 0.02:
                    fs = big(k * step)
                    if fs:
                        geom = list({e for f in fs for e in f.edges} | {v for f in fs for v in f.verts}) + fs
                        co = Vector((0, 0, 0)); co[ax] = k * step; no = Vector((0, 0, 0)); no[ax] = 1
                        bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-4, plane_co=co, plane_no=no)
                    k += 1

    def finish(s, name):
        bm = s.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-4)
        if s.lod < 2: s._subdivide()
        bm.normal_update()
        for f in bm.faces:
            if f[s.fx]: continue
            n = f.normal; ax = max(range(3), key=lambda i: abs(n[i])); a, b = [i for i in range(3) if i != ax]
            R = REP.get(f[s.t], 2)
            uvs = fit([(l.vert.co[a] / R, l.vert.co[b] / R) for l in f.loops])
            for l, (u, v) in zip(f.loops, uvs): l[s.uv].uv = atl(f[s.t], u, v)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        try: me.set_sharp_from_angle(angle=radians(38))
        except Exception: pass
        ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
        return ob


# ---- materials, export, pictures ---------------------------------------------------------------------
def material(name, atlas_dir):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; bsdf = nt.nodes["Principled BSDF"]
    def img(kind, data=False):
        n = nt.nodes.new("ShaderNodeTexImage"); n.image = bpy.data.images.load(os.path.join(atlas_dir, f"Atlas_{kind}.png"), check_existing=True)
        if data: n.image.colorspace_settings.name = "Non-Color"
        return n
    nt.links.new(img("BaseColor").outputs["Color"], bsdf.inputs["Base Color"])
    nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(img("Normal", True).outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    mk = img("MaskMap", True); sep = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(mk.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Red"], bsdf.inputs["Metallic"])
    inv = nt.nodes.new("ShaderNodeInvert"); nt.links.new(mk.outputs["Alpha"], inv.inputs["Color"])
    nt.links.new(inv.outputs["Color"], bsdf.inputs["Roughness"])
    return m


def export(ob, name, lod, out_dir, atlas_dir):
    suf = "" if lod == 0 else f"_LOD{lod}"
    os.makedirs(out_dir, exist_ok=True)
    ob.name = ob.data.name = name + suf
    ob.data.materials[0].name = name + suf
    ob.data.transform(Matrix.Scale(100, 4))                  # metres -> centimetres, transform stays identity
    sc = bpy.context.scene; sc.unit_settings.system = "METRIC"; sc.unit_settings.scale_length = 0.01
    bpy.context.view_layer.update()
    for o in bpy.data.objects: o.select_set(False)
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(filepath=os.path.join(out_dir, name + suf + ".fbx"), use_selection=True, object_types={"MESH"},
                             apply_unit_scale=True, apply_scale_options="FBX_SCALE_NONE", axis_forward="-Z", axis_up="Y",
                             bake_space_transform=True, mesh_smooth_type="OFF", add_leaf_bones=False, path_mode="STRIP",
                             embed_textures=False)
    for k in MAPS:
        shutil.copyfile(os.path.join(atlas_dir, f"Atlas{suf}_{k}.png"), os.path.join(out_dir, f"{name}{suf}_{k}.png"))
    sc.unit_settings.scale_length = 1.0


def _flat(name, col):
    m = bpy.data.materials.new(name); m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*col, 1)
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = .8
    return m


def standins(props):
    """Rough trees, lamps and bollards so the preview shows the finished square (the game supplies real ones)."""
    out = []; leaf = _flat("leaf", (.10, .22, .06)); bark = _flat("bark", (.16, .12, .09)); iron = _flat("iron", (.03, .06, .05))
    glow = _flat("glow", (1, .9, .6))
    def add(mat):
        o = bpy.context.active_object; o.data.materials.append(mat); out.append(o)
    for kind, x, y, size in props:
        if kind == "tree":
            bpy.ops.mesh.primitive_cylinder_add(radius=.18, depth=4, location=(x, y, 2), vertices=8); add(bark)
            bpy.ops.mesh.primitive_ico_sphere_add(radius=2.0, subdivisions=2, location=(x, y, 5.4)); add(leaf)
        elif kind == "lamp":
            bpy.ops.mesh.primitive_cylinder_add(radius=.07, depth=4.2, location=(x, y, 2.1), vertices=6); add(iron)
            bpy.ops.mesh.primitive_ico_sphere_add(radius=.22, subdivisions=1, location=(x, y, 4.3)); add(glow)
        elif kind == "bollard":
            bpy.ops.mesh.primitive_cylinder_add(radius=.11, depth=.9, location=(x, y, .45), vertices=8); add(iron)
    return out


def render(ob, path, res, thumb, extra=(), view=(-.6, -1.0, .36)):
    sc = bpy.context.scene
    for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try: sc.render.engine = e; break
        except Exception: pass
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100
    sc.render.film_transparent = thumb; sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA" if thumb else "RGB"
    try: sc.view_settings.view_transform = "Standard"
    except Exception: pass
    if sc.world is None: sc.world = bpy.data.worlds.new("w")
    sc.world.use_nodes = True; bg = sc.world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (.62, .76, .95, 1); bg.inputs[1].default_value = .9
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    for o in extra: pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
    ctr = (lo + hi) / 2; rad = (hi - lo).length / 2; d = Vector(view).normalized()
    cd = bpy.data.cameras.new("c"); cam = bpy.data.objects.new("c", cd); sc.collection.objects.link(cam)
    if thumb: cd.type = "ORTHO"; cd.ortho_scale = rad * 1.9; dist = rad * 4
    else: cd.lens = 55; dist = rad / math.tan(math.atan(18 / 55)) * 1.02
    cd.clip_end = dist + rad * 4; cam.location = ctr + d * dist; cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    ld = bpy.data.lights.new("s", "SUN"); ld.energy = 3.0; ld.angle = radians(3)
    sun = bpy.data.objects.new("s", ld); sc.collection.objects.link(sun); sun.rotation_euler = (radians(52), 0, radians(-38))
    sc.camera = cam; sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    for o in (cam, sun): bpy.data.objects.remove(o)
