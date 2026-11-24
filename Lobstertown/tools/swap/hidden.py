# window panes with a wall directly in front of them (ghost windows)
import bpy, sys, os, bmesh
from mathutils.bvhtree import BVHTree
def load(path):
    bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.fbx(filepath=path)
    bm = bmesh.new()
    for o in bpy.context.scene.objects:
        if o.type == 'MESH':
            t = bmesh.new(); t.from_mesh(o.data); t.transform(o.matrix_world); m = bpy.data.meshes.new("x"); t.to_mesh(m); bm.from_mesh(m); t.free()
    return bm
for folder in sys.argv[sys.argv.index("--")+1:]:
    name = os.path.basename(folder.rstrip("/\\"))
    for lod in ("", "_LOD1"):
        w = os.path.join(folder, name + lod + "_Win.fbx")
        if not os.path.exists(w): continue
        body = load(os.path.join(folder, name + lod + ".fbx")); bvh = BVHTree.FromBMesh(body)
        win = load(w); win.faces.ensure_lookup_table()
        tot = hid = 0.0; spots = []
        for f in win.faces:
            a = f.calc_area(); tot += a; c = f.calc_center_median(); n = f.normal
            body.faces.ensure_lookup_table(); votes = 0
            for v in f.verts:
                q = c + (v.co - c)*0.6
                hit = bvh.ray_cast(q + n*0.005, n, 1.2)
                if hit[0] is not None and hit[1].dot(n) > 0.9 and body.faces[hit[2]].calc_area() > 1.5: votes += 1
            if votes >= len(f.verts) - 1:      # a big wall facing the same way covers the pane
                h = bvh.ray_cast(c + n*0.005, n, 1.2); out = bvh.ray_cast(h[0] + n*0.01, n, 200)
                if out[0] is None:          # that wall is on the outside, so the defect is visible
                    hid += a; spots.append((round(c.x,1), round(c.y,1), round(h[3],2)))
        print("HID", name + lod, f"{hid:.1f} of {tot:.1f} m2 glass hidden", sorted(set(spots))[:6])
