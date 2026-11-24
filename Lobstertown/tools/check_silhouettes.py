"""Render matching 128-pixel silhouettes from exported New France LOD1 FBXs."""
import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector

SIZE = 128
FRAME_MARGIN = 1.16
BODY_SUFFIX = "_LOD1.fbx"

def read_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path, help="Folder for the PNG views")
    parser.add_argument("body", nargs="+", type=Path, help="One exported _LOD1.fbx per design to review")
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])

def load_meshes(body):
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    glass = body.with_name(body.stem + "_Win.fbx")
    paths = [body, glass] if glass.is_file() else [body]
    meshes = []
    for path in paths:
        bpy.ops.import_scene.fbx(filepath=str(path), axis_forward="-Z", axis_up="Y")
        imported = [obj for obj in bpy.context.selected_objects if obj.type == "MESH"]
        if len(imported) != 1 or not imported[0].data.vertices:
            raise ValueError(f"Expected a single, nonempty mesh in {path}")
        meshes.extend(imported)
    return meshes

def configure(scene):
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.render.resolution_x = scene.render.resolution_y = SIZE
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0
    material = bpy.data.materials.new("New France silhouette")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    ink = nodes.new("ShaderNodeEmission")
    ink.inputs["Color"].default_value = (0.022, 0.049, 0.040, 1)
    material.node_tree.links.new(ink.outputs["Emission"], out.inputs["Surface"])
    return material

def render_pair(scene, body, output, ink):
    meshes = load_meshes(body)
    vertices = [obj.matrix_world @ v.co for obj in meshes for v in obj.data.vertices]
    lo = Vector(tuple(min(v[i] for v in vertices) for i in range(3)))
    hi = Vector(tuple(max(v[i] for v in vertices) for i in range(3)))
    centre = (lo + hi) * .5
    span = max(hi - lo)
    if span <= 0:
        raise ValueError(f"Expected a nonzero asset extent in {body}")
    for obj in meshes:
        obj.data.materials.clear()
        obj.data.materials.append(ink)
    camera = bpy.data.cameras.new("Orthographic silhouette")
    camera.type = "ORTHO"
    camera.ortho_scale = span * FRAME_MARGIN
    distance = max(span * 2, 25)
    camera.clip_end = distance + span * 3
    obj = bpy.data.objects.new("Orthographic silhouette", camera)
    scene.collection.objects.link(obj)
    scene.camera = obj
    for label, direction in (("front", (0, -1, 0)), ("side", (1, 0, 0))):
        obj.location = centre + Vector(direction) * distance
        obj.rotation_euler = (centre - obj.location).to_track_quat("-Z", "Y").to_euler()
        path = output / f"{body.name.removesuffix(BODY_SUFFIX)}-{label}-128.png"
        bpy.ops.render.render()
        bpy.data.images["Render Result"].save_render(str(path), scene=scene)

def main():
    args = read_arguments()
    bodies = [path.resolve(strict=True) for path in args.body]
    if any(not path.is_file() or not path.name.endswith(BODY_SUFFIX) for path in bodies):
        raise ValueError("Provide exported _LOD1.fbx body files")
    if len({path.name.casefold() for path in bodies}) != len(bodies):
        raise ValueError("The selected files must have distinct import names")
    output = args.out.resolve()
    output.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    ink = configure(scene)
    for body in bodies:
        render_pair(scene, body, output, ink)

if __name__ == "__main__":
    main()
