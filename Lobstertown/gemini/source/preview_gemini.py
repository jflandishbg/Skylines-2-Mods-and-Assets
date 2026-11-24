"""Textured previews from street level on every side, plus an aerial and the two far LODs.
  blender -b --python preview_gemini.py -- <run folder> <name>      -> <run folder>/<name>/preview/*.png
The old grey top-down previews hid blank walls; these are meant to show the building as a player sees it."""
import bpy, sys, math
from pathlib import Path
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
OUT = Path(args[0]); NAME = args[1]
folder = OUT / NAME; pv = folder / "preview"; pv.mkdir(exist_ok=True)

def image(suffix):
    for p in (folder / f"{NAME}{suffix}_BaseColor.png",):
        if p.exists(): return bpy.data.images.load(str(p))
    import json
    rel = json.loads((folder / "settings.json").read_text(encoding="utf8"))["sharedAssets"][f"{NAME}{suffix}_BaseColor.png"]
    return bpy.data.images.load(str((folder / rel).resolve()))

def textured(img):
    m = bpy.data.materials.new("tex"); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes["Principled BSDF"]
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = img
    nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"]); bsdf.inputs["Roughness"].default_value = .8
    return m

def glass():
    m = bpy.data.materials.new("glass"); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (.05, .08, .1, 1); b.inputs["Roughness"].default_value = .15
    return m

def scene(suffix):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    for part, mat in (("", textured(image(suffix))), ("_Win", glass())):
        bpy.ops.import_scene.fbx(filepath=str(folder / f"{NAME}{suffix}{part}.fbx"))
        for o in bpy.context.selected_objects:
            if o.type == "MESH": o.data.materials.clear(); o.data.materials.append(mat)
    obs = [o for o in s.objects if o.type == "MESH"]
    pts = [o.matrix_world @ v.co for o in obs for v in o.data.vertices]
    bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, -.01))
    g = bpy.data.materials.new("ground"); g.use_nodes = True
    g.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (.23, .27, .16, 1)
    s.objects["Plane"].data.materials.append(g)
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); s.collection.objects.link(sun)
    sun.data.energy = 4; sun.rotation_euler = (math.radians(50), 0, math.radians(35))
    w = bpy.data.worlds.new("w"); s.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (.55, .65, .8, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = .9
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try: s.render.engine = eng; break
        except TypeError: pass
    try: s.eevee.taa_render_samples = 16
    except Exception: pass
    s.render.resolution_x, s.render.resolution_y = 900, 600
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); s.collection.objects.link(cam); s.camera = cam
    cam.data.lens = 28
    lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
    return s, cam, lo, hi

def shot(s, cam, lo, hi, direction, height, file):
    c = (lo + hi) / 2
    r = (hi - lo).length / 2
    fov = cam.data.angle_x if direction.z == 0 else cam.data.angle_y
    dist = r / math.tan(min(cam.data.angle_x, cam.data.angle_y) / 2) * 1.05
    d = Vector((direction.x, direction.y, 0)).normalized()
    cam.location = Vector((c.x, c.y, 0)) + d * dist + Vector((0, 0, height(dist)))
    cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
    s.render.filepath = str(pv / file)
    bpy.ops.render.render(write_still=True)

street = lambda dist: 6.0                       # eye level from across the street
views = [("1 front", (0, -1)), ("2 front-left", (-1, -1)), ("3 front-right", (1, -1)),
         ("4 right side", (1, 0)), ("5 rear", (0, 1)), ("6 left side", (-1, 0))]
s, cam, lo, hi = scene("")
for label, (x, y) in views:
    shot(s, cam, lo, hi, Vector((x, y, 0)), street, label + ".png")
shot(s, cam, lo, hi, Vector((-1, -1.3, 0)), lambda dist: dist * .9, "7 aerial.png")
for k, suffix in ((8, "_LOD1"), (9, "_LOD2")):
    s, cam, lo, hi = scene(suffix)
    shot(s, cam, lo, hi, Vector((-1, -1, 0)), street, f"{k} far LOD{suffix[-1]} (front-left).png")
print("PREVIEW_DONE", NAME, flush=True)
