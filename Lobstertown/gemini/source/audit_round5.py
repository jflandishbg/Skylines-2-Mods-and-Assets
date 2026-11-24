"""Audit exterior winding, door openings and material tiles on the exported FBXs."""
import json
from itertools import combinations
from pathlib import Path
import sys
from time import monotonic, sleep
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from round5_specs import make

ROOT=Path(__file__).resolve().parents[1]
TILES=json.loads((ROOT/"source"/"kit"/"atlas_layout.json").read_text(encoding="utf8"))["lods"]
STEPS=("","_LOD1","_LOD2")

def atlas_partition(lod):
    tiles={name:tuple(cell["uv"]) for name,cell in TILES[lod].items()}
    for (k,(l,b,r,t)),(j,(ll,bb,rr,tt)) in combinations(tiles.items(),2):
        assert min(r,rr)<=max(l,ll) or min(t,tt)<=max(b,bb),(lod,k,j,"overlapping material tiles")
    buckets={}
    for key,rect in tiles.items():
        l,b,r,t=rect
        for u in range(int(l*7),int(r*7)+1):
            for v in range(int(b*7),int(t*7)+1):
                buckets.setdefault((u,v),[]).append((key,rect))
    return buckets

def material_uvs(obj,verts,tiles,a):
    uv=obj.data.uv_layers.active.data
    normals=obj.matrix_world.to_3x3().inverted().transposed()
    names={}
    paved=0
    eps=2e-6
    for f in obj.data.polygons:
        us,vs=zip(*(tuple(uv[i].uv) for i in f.loop_indices))
        l,r,b,t=min(us),max(us),min(vs),max(vs)
        owners=[n for n,(a0,b0,a1,b1) in tiles.get((int((l+r)*3.5),int((b+t)*3.5)),()) if a0-eps<=l and r<=a1+eps and b0-eps<=b and t<=b1+eps]
        assert len(owners)==1,(obj.name,f.index,"material UV",l,b,r,t,owners)
        tag=owners[0]
        names[tag]=names.get(tag,0)+1
        if (normals@f.normal).normalized().z>.97 and all(abs(verts[i].z-.027)<.0002 for i in f.vertices):
            assert tag in {"YardSetts"},(obj.name,f.index,"paving material",tag)
            paved+=1
    pass  # second pass (2026-11-13): no yards, so no paving is required
    assert not any("Glass" in key and key not in {"GardenGlass","CourtGlass"} for key in names),(obj.name,"unexpected body glazing")

    if not a.get("reimport") and not a.get("gemini"):assert names.get(a["wall_tile"]), (obj.name,"missing colourway",a["wall_tile"])   # runner buildings choose their own walls
    return dict(body_faces=sum(names.values()),paving_faces=paved,inscription_faces=names.get("Sign_"+a["design"],0),wall_tile=a.get("wall_tile",a.get("brick","retained palette")),material_tiles=sorted(names),glazed_faces=names.get("GlassBlue",0)+names.get("GlassWarm",0))

def audit_routes(body,a,lod):
    w,d=(8*n for n in a["lot"])
    ray=Vector((0,1,0))
    def hit(x,y,z,length):
        return body.ray_cast(Vector((x-w/2,y-d/2,z)),ray,length)[0]
    bays={}
    for name,ent in a["entrances"].items():
        x,y,z=ent["position_lot_m"]
        expected=y+(.35 if lod<2 else -.014)-d/2
        for offset in (-.25,0,.25):
            p=hit(x+offset,y-.10,z+1.03,.85)
            assert p is not None and abs(p.y-expected)<.05,(a["name"],lod,name,p,expected)
        bays[name]=3
    l,r,f,b=a["walls"]
    checks=[]
    if a["style"]=="bridge":
        assert a["passage_width_m"]>=2.0
        checks=[(x,.06,z,b+.42) for x in (r+.095,r+.64,r+1.27,r+1.99) for z in (.32,1.30,2.34)]
    if a["style"]=="porch":
        assert a["porch_clear_height_m"]>=2.4
        checks=[(x,.06,z,b+.31) for x in (r-.74,r-.54,r-.39) for z in (.32,1.32,2.45)]
    if a["style"]=="split":
        assert a["court_width_m"]>=3.5
        checks=[(x,.06,z,b-1.71) for x in (a["left_end"]+.19,a["right_start"]-.19,8.0) for z in (1.2,2.4)]
    for x,y,z,distance in checks:
        p=hit(x,y,z,distance-y)
        assert p is None,(a["name"],lod,"garden route obstructed",x,y,z,p)
    return dict(door_leaf_rays=bays,open_passage_rays=len(checks))

def sweep(bv,w,d,zmax):
    directions={}
    for off in (0,.073):
        grid=lambda n:[-n/2+(i+.5)*.2+off for i in range(round(n/.2)) if (i+.5)*.2+off<n]
        zs=[.05+i*.2+off for i in range(round(zmax/.2)+1)]
        views={
          "top":(lambda x,y:Vector((x,y,zmax+9)),Vector((0,0,-1)),grid(w),grid(d)),
          "front":(lambda x,z:Vector((x,-100,z)),Vector((0,1,0)),grid(w),zs),
          "rear":(lambda x,z:Vector((x,100,z)),Vector((0,-1,0)),grid(w),zs),
          "left":(lambda y,z:Vector((-100,y,z)),Vector((1,0,0)),grid(d),zs),
          "right":(lambda y,z:Vector((100,y,z)),Vector((-1,0,0)),grid(d),zs)}
        for name,(point,ray,aa,bb) in views.items():
            good=bad=seam=0
            samples=[]
            faces=set()
            u=Vector((1,0,0)) if abs(ray.x)<.5 else Vector((0,1,0))
            v=ray.cross(u)
            shifts=[u*(sgn*.00037)+v*(other*.00071) for sgn in (-1,1) for other in (-1,1)]
            def first(start):
                body,window=(tree.ray_cast(start,ray) for tree in bv)
                if body[0] is None:return None
                if window[0] is not None and window[3]<=body[3]+1e-6:return None
                return body
            for x in aa:
                for y in bb:
                    origin=point(x,y)
                    hit=first(origin)
                    if hit is None:continue
                    if hit[1].dot(ray)<=1e-6:
                        good+=1
                        continue
                    if any(test is not None and test[1].dot(ray)>1e-6 for test in (first(origin+s) for s in shifts)):
                        bad+=1
                        faces.add(hit[2])
                        if len(samples)<10:samples.append([round(i,4) for i in hit[0]])
                    else:seam+=1
            directions[f"{name}@{off}"]=dict(good=good,backface_first_hits=bad,zero_width_grid_edge_ties=seam,samples=samples,backface_polygons=sorted(faces))
    return directions

def write(path,data):
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf8")

def wait_for_registration(out,name):
    log=ROOT/f"bake-{out.name[7:]}.txt"
    if log.exists():
        limit=monotonic()+320
        while monotonic()<limit:
            with log.open(encoding="utf8",errors="replace") as handle:
                if any(line.startswith("ASSET_PASS ") and line.split()[2]==name for line in handle):return
            sleep(.85)
        raise RuntimeError(("final export did not complete",name))
    limit=monotonic()+420
    while monotonic()<limit:
        try:
            records=json.loads((out/"progress.json").read_text(encoding="utf8"))
            if any(r["name"]==name for r in records):return
        except (OSError,ValueError):
            pass
        sleep(1)
    raise RuntimeError(("export did not complete before audit deadline",name))

def run(zone,sample=False,styles=(),watch=False,force=False):
    out=ROOT/f"import_{zone}"
    audit={};result={}
    planes={lod:atlas_partition(lod) for lod in ("main","_LOD1","_LOD2")}
    total_bad=0
    journal=ROOT/f"audit-progress-{zone}.json"
    done=json.loads(journal.read_text(encoding="utf8")) if journal.exists() and not sample else {}

    for a in make(zone):
        if sample and (a["colourway"]!="A" or a["lot"][1]!=4):continue
        if sample and styles and a["design"] not in styles:continue
        name=a["name"];w,d=[8*v for v in a["lot"]]
        if not force and name in done and (not styles or a["design"] not in styles):
            result[name],audit[name]=done[name]
            total_bad+=sum(p["backface_first_hits"] for v in result[name].values() for p in v.values())
            continue
        if watch:wait_for_registration(out,name)
        result[name]={};audit[name]={}
        for lod,suffix in enumerate(STEPS):
            for obj in list(bpy.data.objects):bpy.data.objects.remove(obj,do_unlink=True)
            for mesh in list(bpy.data.meshes):
                if mesh.users==0:bpy.data.meshes.remove(mesh)
            bv=[];zmax=0
            k=suffix or "main";verification={}
            for extra in ("","_Win"):
                stem=name+suffix+extra
                bpy.ops.import_scene.fbx(filepath=str(out/name/(stem+".fbx")),axis_forward="-Z",axis_up="Y")
                ob=bpy.context.selected_objects[0]
                verts=[ob.matrix_world@v.co for v in ob.data.vertices]
                zmax=max(zmax,max(v.z for v in verts))
                if not extra:verification["uv"]=material_uvs(ob,verts,planes[k],a)
                bv.append(BVHTree.FromPolygons(verts,[tuple(p.vertices) for p in ob.data.polygons]))
            verification["routes"]=audit_routes(bv[0],a,lod)
            probe=sweep(bv,w,d,zmax)
            result[name][k]=probe
            audit[name][k]=verification
            bad=sum(p["backface_first_hits"] for p in probe.values())
            if bad:print("HIT_LOCATIONS",name,k,{v:p["samples"][:3] for v,p in probe.items() if p["backface_first_hits"]},flush=True)
            total_bad+=bad
            print("PROBE",name,k,bad,flush=True)
        if not sample:
            done[name]=[result[name],audit[name]]
            write(journal,done)
    print("TOTAL_BAD",zone,total_bad,flush=True)
    dest=ROOT if sample else out
    tag="-"+zone+"-sample" if sample else ""
    for f,data in (("probe-results",result),("audit",audit)):
        (dest/(f+tag+".json")).write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf8")

if __name__=="__main__":
    zone,*args=sys.argv[sys.argv.index("--")+1:]
    run(zone,"--sample" in args,[x for x in args if not x.startswith("--")],"--watch" in args,"--force" in args)
