"""Separate old applied surfaces that occupy the same plane."""
from collections import defaultdict
from mathutils import Vector

def separate(mesh,obj,hits):
    neighbors=defaultdict(set)
    for hit in hits:
        a,b=hit["faces"]
        neighbors[a].add(b)
        neighbors[b].add(a)
    normals={p.index:p.normal.copy() for p in obj.data.polygons}
    areas={p.index:p.area for p in obj.data.polygons}
    selected={}
    for i in sorted(neighbors,key=lambda j:(-areas[j],j)):
        used={selected[j] for j in neighbors[i] if j in selected}
        selected[i]=next(slot for slot in range(len(used)+1) if slot not in used)
    adjusted=[]
    for i,slot in selected.items():
        if not slot:
            continue
        # Keep a real gap for FBX precision. Prefer leaving the larger supporting
        # wall in place and moving only the overlapping applied facing.
        off=normals[i]*(slot*.00118)/max(.0001,(obj.matrix_world.to_3x3()@normals[i]).length)
        replacement=[]
        for j in mesh.faces[i]:
            point=Vector(mesh.vertices[j])+off
            replacement.append(len(mesh.vertices))
            mesh.vertices.append(tuple(point))
        adjusted.append((i,replacement))
    for i,f in adjusted:
        mesh.faces[i]=f
    return len(adjusted)


def repair_export(obj,path,hits,overlaps):
    """Resolve sub-millimetre ties that become visible only after FBX round-trip."""
    import bpy
    from detail_mesh import smooth_export
    from nf_build import export_fbx
    from types import SimpleNamespace

    for _ in range(7):
        if not hits:
            break
        data=obj.data
        mat=data.materials[0]
        uv=data.uv_layers.active.data
        raw=SimpleNamespace(vertices=[tuple(v.co) for v in data.vertices],
            faces=[list(p.vertices) for p in data.polygons],
            uvs=[[tuple(uv[i].uv) for i in p.loop_indices] for p in data.polygons])
        separate(raw,obj,hits)
        new=bpy.data.meshes.new(obj.name+" repaired")
        new.from_pydata(raw.vertices,[],raw.faces)
        layer=new.uv_layers.new(name="UVMap")
        for poly,coords in zip(new.polygons,raw.uvs):
            for index,coord in zip(poly.loop_indices,coords):
                layer.data[index].uv=coord
        new.materials.append(mat)
        obj.data=new
        bpy.data.meshes.remove(data)
        new.update()
        hits=overlaps(obj)
    smooth_export(obj)
    export_fbx(obj,path)
