"""Run a Gemini script for one LOD and pour its 'Body' and 'Windows' faces into the pipeline's mesh, which
cuts every face into texture-sheet tiles (nb.Mesh.polygon) exactly as our own buildings are made."""
import importlib.util, random
import bpy
from mathutils import Vector
from r12_build import core, nb

class GeminiError(Exception):
    pass

def _run(path, lod):
    spec = importlib.util.spec_from_file_location("gemini_building", path)
    mod = importlib.util.module_from_spec(spec)
    mod.__name__ = "gemini_building"          # its  if __name__ == "__main__"  block must not run
    spec.loader.exec_module(mod)
    if not hasattr(mod, "build"): raise GeminiError("the script has no build(lod) function")
    mod.build(lod)

def _faces(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg); me = ev.to_mesh()
    M = ob.matrix_world; N = M.to_3x3().inverted().transposed()
    names = [s.material.name if s.material else None for s in ob.material_slots]
    out = []
    for p in me.polygons:
        pts = [M @ me.vertices[i].co for i in p.vertices]
        mat = names[p.material_index] if names and p.material_index < len(names) else None
        out.append((pts, (N @ p.normal).normalized(), mat))
    ev.to_mesh_clear()
    return out

def build(a, lod):
    core.setup(a, lod, 0)
    h = nb.House(lod); h.name = a["name"]; h.detail_grade = 0
    _run(a["gemini_script"], lod)
    body = bpy.data.objects.get("Body"); win = bpy.data.objects.get("Windows")
    if body is None or body.type != "MESH": raise GeminiError(f"LOD{lod}: no mesh object named 'Body'")
    if win is None or win.type != "MESH": raise GeminiError(f"LOD{lod}: no mesh object named 'Windows'")
    layout = nb.LAYOUT["lods"][("main", "_LOD1", "_LOD2")[lod]]
    shift = Vector((0, nb.YSHIFT, 0))        # Gemini's frame (lot centre) -> the pipeline's build frame
    bad = {}; skipped = 0
    for pts, n, mat in _faces(body):
        key = mat.split(".")[0] if mat else None
        if key not in layout:
            bad[key] = bad.get(key, 0) + 1; continue
        try: h.body.polygon([p - shift for p in pts], n, key)
        except ValueError: skipped += 1
    if bad: raise GeminiError(f"LOD{lod}: materials not on the texture sheet: {bad}")
    rng = random.Random(a["name"])
    for pts, n, _ in _faces(win):
        if abs(n.z) > .9: continue           # flat glass (skylights) has no room to light
        try: h.windows.polygon([p - shift for p in pts], n, "Glass", room=rng.choice(nb.ROOMS))
        except ValueError: skipped += 1
    for ob in [o for o in bpy.data.objects if o.name in ("Body", "Windows") or o.name.startswith(("Body.", "Windows."))]:
        bpy.data.objects.remove(ob, do_unlink=True)
    for o in list(bpy.data.objects):          # anything else Gemini left behind (cameras, lights, helpers)
        if not o.name.startswith(a["name"]): bpy.data.objects.remove(o, do_unlink=True)
    h.gemini_skipped = skipped
    return h
