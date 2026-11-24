"""Asset-bar thumbnails for imported buildings (Claude, 2026-11-09).
blender -b --python service_thumbs.py -- <out_dir> <asset_folder> [<asset_folder> ...]
Each asset folder holds <name>_LOD1.fbx + <name>_LOD1_BaseColor.png (GPT's delivery format). Writes <out_dir>/<name>.png,
512x512 with a transparent background, the same three-quarter view as the monuments."""
import bpy, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mcore
def tex_of(folder, name, suffix):
    """the texture, or the atlas owner's copy when settings.json shares it (R8 followers)"""
    own = os.path.join(folder, name + suffix)
    if os.path.exists(own): return own
    import json
    shared = json.load(open(os.path.join(folder, "settings.json"), encoding="utf-8"))["sharedAssets"]
    return os.path.normpath(os.path.join(folder, shared[name + suffix]))
out, folders = os.path.abspath(sys.argv[sys.argv.index("--") + 1]), sys.argv[sys.argv.index("--") + 2:]
os.makedirs(out, exist_ok=True)
for folder in folders:
    folder = os.path.abspath(folder); name = os.path.basename(folder)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    obs = []
    for suffix, glass in (("_LOD1", False), ("_LOD1_Win", True)):
        f = os.path.join(folder, name + suffix + ".fbx")
        if not os.path.exists(f): continue
        bpy.ops.import_scene.fbx(filepath=f)
        m = bpy.data.materials.new(name + suffix); m.use_nodes = True; bsdf = m.node_tree.nodes["Principled BSDF"]
        if glass:
            bsdf.inputs["Base Color"].default_value = (.07, .10, .13, 1); bsdf.inputs["Roughness"].default_value = .08
        else:
            t = m.node_tree.nodes.new("ShaderNodeTexImage")
            t.image = bpy.data.images.load(tex_of(folder, name, "_LOD1_BaseColor.png"))
            m.node_tree.links.new(t.outputs["Color"], bsdf.inputs["Base Color"]); bsdf.inputs["Roughness"].default_value = .75
        for o in bpy.context.selected_objects:
            if o.type == "MESH":
                o.data.materials.clear(); o.data.materials.append(m); obs.append(o)
    if not obs: print("NO MESH", name); continue
    bpy.context.view_layer.update()
    mcore.render(obs[0], os.path.join(out, name + ".png"), (512, 512), True, extra=obs[1:])
    print("thumb", name)
