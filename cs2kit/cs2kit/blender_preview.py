"""Persistent single-session Blender EEVEE batch preview + service thumbnail renderer.

Loads the 3 BaseColor atlas textures once per worker process and renders every asset in the chunk.
"""
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def _make_textured_material(name: str, img_path: Path):
    img = bpy.data.images.load(str(img_path))
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img
    nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.8
    return m


def _make_glass_material():
    m = bpy.data.materials.new("cs2kit_glass")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.05, 0.08, 0.10, 1.0)
    b.inputs["Roughness"].default_value = 0.15
    return m


def _setup_stage(atlas_dir: Path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene

    mats = {
        "": _make_textured_material("atlas_main", atlas_dir / "ATLAS_BaseColor.png"),
        "_LOD1": _make_textured_material("atlas_lod1", atlas_dir / "ATLAS_LOD1_BaseColor.png"),
        "_LOD2": _make_textured_material("atlas_lod2", atlas_dir / "ATLAS_LOD2_BaseColor.png"),
    }
    glass = _make_glass_material()

    bpy.ops.mesh.primitive_plane_add(size=400.0, location=(0.0, 0.0, -0.01))
    ground = bpy.context.active_object
    ground.name = "GroundPlane"
    gmat = bpy.data.materials.new("ground")
    gmat.use_nodes = True
    gmat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.23, 0.27, 0.16, 1.0)
    ground.data.materials.append(gmat)

    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    s.collection.objects.link(sun)
    sun.data.energy = 4.0
    sun.rotation_euler = (math.radians(50.0), 0.0, math.radians(35.0))

    w = bpy.data.worlds.new("sky")
    s.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.65, 0.80, 1.0)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.9

    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            s.render.engine = eng
            break
        except TypeError:
            pass
    try:
        s.eevee.taa_render_samples = 16
    except Exception:
        pass

    s.render.resolution_x = 900
    s.render.resolution_y = 600
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_mode = "RGB"

    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    s.collection.objects.link(cam)
    s.camera = cam
    cam.data.lens = 28.0
    return s, cam, ground, mats, glass


def _clear_buildings(ground):
    for ob in list(bpy.data.objects):
        if ob is ground:
            continue
        if ob.type == "MESH":
            bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        if not me.users:
            bpy.data.meshes.remove(me)


def _import_lod(folder: Path, name: str, suffix: str, mat, glass):
    imported = []
    for part, m in (("", mat), ("_Win", glass)):
        fbx = folder / f"{name}{suffix}{part}.fbx"
        if not fbx.exists():
            continue
        bpy.ops.import_scene.fbx(filepath=str(fbx), axis_forward="-Z", axis_up="Y")
        for o in bpy.context.selected_objects:
            if o.type == "MESH":
                o.data.materials.clear()
                o.data.materials.append(m)
                imported.append(o)
    pts = [o.matrix_world @ v.co for o in imported for v in o.data.vertices]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    return lo, hi


def _render_shot(scene, cam, lo: Vector, hi: Vector, direction: Vector, height_fn, out_file: Path, pad_scale: float = 1.05):
    c = (lo + hi) * 0.5
    r = max(1.0, (hi - lo).length * 0.5)
    fov = min(cam.data.angle_x, cam.data.angle_y)
    dist = r / math.tan(fov * 0.5) * pad_scale
    d = Vector((direction.x, direction.y, 0.0)).normalized()
    cam.location = Vector((c.x, c.y, 0.0)) + d * dist + Vector((0.0, 0.0, height_fn(dist)))
    cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(out_file)
    bpy.ops.render.render(write_still=True)


def render_asset(scene, cam, ground, mats, glass, out_dir: Path, thumb_dir: Path, asset: dict):
    name = asset["name"]
    folder = out_dir / name
    pv = folder / "preview"
    pv.mkdir(parents=True, exist_ok=True)

    street_views = [
        ("1_front", (0.0, -1.0)),
        ("2_front_left", (-1.0, -1.0)),
        ("3_front_right", (1.0, -1.0)),
        ("4_right", (1.0, 0.0)),
        ("5_rear", (0.0, 1.0)),
        ("6_left", (-1.0, 0.0)),
    ]

    lo, hi = _import_lod(folder, name, "", mats[""], glass)
    for label, (vx, vy) in street_views:
        _render_shot(scene, cam, lo, hi, Vector((vx, vy, 0.0)), lambda _d: 6.0, pv / f"{label}.png")
    _render_shot(scene, cam, lo, hi, Vector((-1.0, -1.3, 0.0)), lambda d: d * 0.9, pv / "7_aerial.png")

    if asset.get("render_thumbnail"):
        thumb_dir.mkdir(parents=True, exist_ok=True)
        ground.hide_render = True
        scene.render.film_transparent = True
        scene.render.image_settings.color_mode = "RGBA"
        scene.render.resolution_x = 512
        scene.render.resolution_y = 512
        cam.data.lens = 50.0
        _render_shot(
            scene,
            cam,
            lo,
            hi,
            Vector((-1.0, -1.15, 0.0)),
            lambda d: d * 0.55,
            thumb_dir / f"{name}.png",
            pad_scale=0.98,
        )
        ground.hide_render = False
        scene.render.film_transparent = False
        scene.render.image_settings.color_mode = "RGB"
        scene.render.resolution_x = 900
        scene.render.resolution_y = 600
        cam.data.lens = 28.0

    _clear_buildings(ground)

    for k, suffix, label in ((8, "_LOD1", "8_lod1"), (9, "_LOD2", "9_lod2")):
        lo_l, hi_l = _import_lod(folder, name, suffix, mats[suffix], glass)
        _render_shot(scene, cam, lo_l, hi_l, Vector((-1.0, -1.0, 0.0)), lambda _d: 6.0, pv / f"{label}.png")
        _clear_buildings(ground)


def main():
    plan_path = Path(sys.argv[sys.argv.index("--") + 1])
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    atlas_dir = Path(plan["atlas_build_dir"])
    out_dir = Path(plan["out_dir"])
    thumb_dir = out_dir / "thumbnails"

    scene, cam, ground, mats, glass = _setup_stage(atlas_dir)
    for asset in plan["assets"]:
        render_asset(scene, cam, ground, mats, glass, out_dir, thumb_dir, asset)
        print(f"PREVIEW_DONE {asset['name']}", flush=True)


if __name__ == "__main__":
    main()
