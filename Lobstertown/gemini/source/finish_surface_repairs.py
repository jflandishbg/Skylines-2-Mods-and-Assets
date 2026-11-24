"""Repair the remaining inherited coplanar slivers and exposed sheet backs."""
from mathutils import Matrix, Vector
from mathutils.geometry import tessellate_polygon
import bpy
from nf_build import export_fbx
from detail_mesh import smooth_export

def raw_faces(ob):
    uv=ob.data.uv_layers.active.data
    return [[(ob.data.vertices[ob.data.loops[i].vertex_index].co.copy(),uv[i].uv.copy())
             for i in poly.loop_indices] for poly in ob.data.polygons]

def replace(ob,faces):
    vertices=[]
    index_map={}
    transform=ob.matrix_world.copy()
    polys=[]
    uvs=[]
    for face in faces:
        if len(face)<3:
            continue
        idx=[]
        for p,uv in face:
            if idx and (p-vertices[idx[-1]]).length<.000002:
                continue
            key=tuple(round(x,6) for x in p)
            if key not in index_map:
                index_map[key]=len(vertices)
                vertices.append(p)
            idx.append(index_map[key])
        if len(idx)<3:
            continue
        if (vertices[idx[0]]-vertices[idx[-1]]).length<.000002:
            idx.pop()
        if len(idx)<3:
            continue
        normal=Vector((0,0,0))
        for i,j in zip(idx,idx[1:]+idx[:1]):
            normal+=vertices[i].cross(vertices[j])
        actual=[transform@vertices[i] for i in idx]
        base=actual[0]
        normal=Vector((0,0,0))
        for a,b in zip(actual[1:],actual[2:]):
            normal+=(a-base).cross(b-base)
        span=max((v-base).length for v in actual)
        if normal.length<max(1.4e-6,span*.000036):
            continue
        polys.append(idx)
        uvs.append([min(face,key=lambda pv:(pv[0]-vertices[j]).length_squared)[1] for j in idx])
    previous=ob.data
    mat=previous.materials[0]
    data=bpy.data.meshes.new(ob.name+" cleaned")
    data.from_pydata([transform@v for v in vertices],[],polys)
    layer=data.uv_layers.new(name="UVMap")
    for p,coords in zip(data.polygons,uvs):
        for index,uv in zip(p.loop_indices,coords):
            layer.data[index].uv=uv
    data.materials.append(mat)
    ob.data=data
    ob.matrix_world=Matrix.Identity(4)
    bpy.data.meshes.remove(previous)
    data.update()
    smooth_export(ob)

def subtract(subject,clip,axes):
    u,v=axes
    cross=lambda a,b,p:(b[u]-a[u])*(p[v]-a[v])-(b[v]-a[v])*(p[u]-a[u])
    direction=sum(x[u]*y[v]-x[v]*y[u] for x,y in zip(clip,clip[1:]+clip[:1]))
    if direction<0:
        clip=clip[::-1]
    remains=[]
    for a,b in zip(clip,clip[1:]+clip[:1]):
        inner=[]
        outer=[]
        if len(subject)<3:
            break
        for prev,now in zip(subject[-1:]+subject[:-1],subject):
            cp,cn=cross(a,b,prev[0]),cross(a,b,now[0])
            if (cp>=0)!=(cn>=0):
                f=cp/(cp-cn)
                q=(prev[0].lerp(now[0],f),prev[1].lerp(now[1],f))
                inner.append(q)
                outer.append(q)
            (inner if cn>=0 else outer).append(now)
        if len(outer)>=3:
            remains.append(outer)
        subject=inner
    return remains

def trim(ob,path,hits,probe):
    for _ in range(4):
        if not hits:
            break
        data=ob.data
        originals=raw_faces(ob)
        result=[[p] for p in originals]
        for hit in hits:
            ia,ib=hit["faces"]
            a,b=sorted((ia,ib),key=lambda i:data.polygons[i].area)
            if not result[a] or not result[b]:
                continue
            axis=max(range(3),key=lambda j:abs(data.polygons[a].normal[j]))
            axes=[j for j in range(3) if j!=axis]
            # Old conflicts are between convex pieces of applied trim. Split any
            # non-convex cutter with Blender before applying its half planes.
            contour=[q[0] for q in originals[b]]
            triangles=tessellate_polygon([contour]) if len(contour)>3 else [contour]
            for tri in triangles:
                if isinstance(tri[0],int):
                    tri=[contour[j] for j in tri]
                result[a]=[p for face in result[a] for p in subtract(face,list(tri),axes)]
        replace(ob,[p for sub in result for p in sub])
        hits=probe(ob)
    export_fbx(ob,path)

def add_backings(ob,path,indices):
    faces=raw_faces(ob)
    transform=ob.matrix_world.to_3x3()
    for i in indices:
        poly=ob.data.polygons[i]
        normal=poly.normal
        distance=.00086/max(.0001,(transform@normal).length)
        back=[(p-normal*distance,uv) for p,uv in reversed(faces[i])]
        faces.append(back)
    replace(ob,faces)
    export_fbx(ob,path)


def remove_hidden_trim(obj,path,hits):
    # Drop small applied slivers only where an existing face covers them.
    faces=raw_faces(obj)
    remove=set()
    for hit in hits:
        small,large=sorted(hit["faces"],key=lambda i:obj.data.polygons[i].area)
        area=obj.data.polygons[small].area
        if area<=.075 and hit["overlap_m2"]>=area*.21:
            remove.add(small)
    if remove:
        replace(obj,[face for i,face in enumerate(faces) if i not in remove])
        export_fbx(obj,path)
    return bool(remove)
