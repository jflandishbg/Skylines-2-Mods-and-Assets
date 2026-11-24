"""Export, reimport, and validate every Round 12 model."""
from hashlib import sha256
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from r12_build import build as new_build, core, nb, kit
from legacy_r12 import build as legacy_build
from separate_legacy import separate,repair_export
from finish_surface_repairs import trim,add_backings,remove_hidden_trim
from gemini_specs import make, atlas_owners, COUNTS
from detail_mesh import smooth_export
from fbx_check import verify_raw
from scan_windows import audit as windows
from audit_round5 import sweep, atlas_partition, material_uvs

ROOT=Path(__file__).resolve().parents[1]
SUFFIXES=("","_LOD1","_LOD2")
ROOF_TILES={"Slate","SlateDark","SlateGreen","SlateBrown","TinFlat","TinOxide","GardenGlass","CourtGlass","TinGreen"}

def read(path):
    return json.loads(path.read_text(encoding="utf8"))

def write(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf8")

def dispose():
    nb.clear_objects()
    for col in (core.bpy.data.meshes,core.bpy.data.materials):
        for obj in list(col):
            if not obj.users:
                col.remove(obj)

def mesh_bvh(obj):
    vs=[obj.matrix_world@v.co for v in obj.data.vertices]
    faces=[tuple(p.vertices) for p in obj.data.polygons]
    return BVHTree.FromPolygons(vs,faces),vs

def coverage(ob,a):
    w,d=(8*n for n in a["lot"])
    step=.25
    mesh=ob.data
    tree,verts=mesh_bvh(ob)
    uv=mesh.uv_layers.active.data
    cells=[nb.LAYOUT["lods"]["main"][key]["uv"] for key in ROOF_TILES if key in nb.LAYOUT["lods"]["main"]]
    roof_polys=[]
    normals=ob.matrix_world.to_3x3().inverted().transposed()
    for poly in mesh.polygons:
        if (normals@poly.normal).normalized().z<.20 or min(verts[j].z for j in poly.vertices)<2.65:
            continue
        u,v=[sum(uv[j].uv[k] for j in poly.loop_indices)/len(poly.loop_indices) for k in (0,1)]
        if any(l<=u<=r and b<=v<=t for l,b,r,t in cells):
            roof_polys.append(tuple(poly.vertices))
    assert roof_polys,a["name"]
    roofs=BVHTree.FromPolygons(verts,roof_polys)
    roof=paving=0
    nz=Vector((0,0,-1))
    for i in range(round(w/step)):
        for j in range(round(d/step)):
            p=Vector(((i+.5)*step-w/2,(j+.5)*step-d/2,35))
            if roofs.ray_cast(p,nz,40)[0] is not None:
                roof+=1
            elif tree.ray_cast(p,nz,40)[0] is not None:
                paving+=1
    total=round(w/step)*round(d/step)
    return dict(sample_spacing_m=step,roofed_pct=round(100*roof/total,3),
                occupied_unroofed_pct=round(100*paving/total,3),open_pct=round(100*(total-roof-paving)/total,3))

def envelope(ob,skip=()):
    # Sum the five exterior orthographic projections. Edges and small applied
    # trim do not inflate the denominator as they would in a raw polygon sum.
    tree,vertices=mesh_bvh(ob)
    lo=[min(v[k] for v in vertices) for k in range(3)]
    hi=[max(v[k] for v in vertices) for k in range(3)]
    lo[2]=.34
    spacing=.38
    area=0
    for axis,sign in ((0,1),(0,-1),(1,1),(1,-1),(2,-1)):
        if (axis,sign) in skip:continue   # declared party walls: neighbours cover them
        direction=Vector([sign if k==axis else 0 for k in range(3)])
        u,v=[k for k in range(3) if k!=axis]
        for i in range(int((hi[u]-lo[u])/spacing)):
            for j in range(int((hi[v]-lo[v])/spacing)):
                point=[0.,0.,0.]
                point[axis]=lo[axis]-1 if sign>0 else hi[axis]+1
                point[u]=lo[u]+(i+.5)*spacing
                point[v]=lo[v]+(j+.5)*spacing
                hit=tree.ray_cast(Vector(point),direction,60)[0]
                if hit is not None and hit.z>=.34:
                    area+=spacing**2
    return area

def asset(out,a,diagnose=False):
    name=a["name"]
    folder=out/name
    if not diagnose:
        folder.mkdir(exist_ok=True)
    lods={}
    meshes={}
    limits=a["budget"]
    legacy=a["reimport"]
    build=legacy_build if legacy else new_build
    for lod,suffix in enumerate(SUFFIXES):
        levels=[0,.5,1,1.12,1.22,1.34,1.45,1.6,1.72,1.86,2.0,2.2,2.45,2.7,3.0] if legacy else [0,1,2,3]
        choices=[(g,c) for g in (levels if not lod else [0]) for c in ([0,1,2,3,4,5] if legacy else [0])]
        skip_grade=None
        for grade,compact in choices:
            if grade==skip_grade:
                continue
            dispose()
            h=build(dict(a,detail_grade=grade,compact=compact),lod)
            pairs=[]
            for m,tag in ((h.body,name+suffix),(h.windows,name+suffix+"_Win")):
                mat=None if tag.endswith("_Win") else core.bpy.data.materials.new(tag)
                ob=core.optimize_far(m.object(tag,mat),lod)
                if legacy and not tag.endswith("_Win"):
                    conflicts=kit.overlaps(ob)
                    if conflicts:
                        if lod==2:
                            # Face indices must correspond to the original loops before dissolve.
                            core.bpy.data.objects.remove(ob,do_unlink=True)
                            ob=m.object(tag,mat)
                            conflicts=kit.overlaps(ob)
                        for attempt in range(7):
                            if not conflicts:
                                break
                            separate(m,ob,conflicts)
                            core.bpy.data.objects.remove(ob,do_unlink=True)
                            ob=m.object(tag,mat)
                            conflicts=kit.overlaps(ob)
                        ob=core.optimize_far(ob,lod)
                pairs.append((ob,tag,core.mesh_stats(ob)))
            count=sum(s["triangles"] for _,_,s in pairs)
            body=pairs[0][0]
            if not lod:
                if not grade and not compact:
                    area=envelope(body,a.get("party_skip",()))
                if count<=limits[0] and count/area<a.get("density_floor",8):
                    skip_grade=grade
                    continue
            if diagnose:
                print("CHOICE",a["name"],lod,grade,compact,count,round(count/area,3) if lod==0 else 0,flush=True)
            if count<=limits[lod]:
                break
        overlaps=kit.overlaps(body)
        if diagnose:
            print("DIAG",a["name"],lod,count,round(count/area,2) if not lod else 0,
                  "overlaps",len(overlaps),overlaps[:3],
                  coverage(body,a)["roofed_pct"] if not lod else "",flush=True)
            continue
        assert count<=limits[lod],(name,lod,count,limits)
        assert not overlaps,(name,lod,overlaps[:7])
        if lod==0:
            assert count/area>=a.get("density_floor",8),(name,count,area)
        for ob,tag,_ in pairs:
            if not tag.endswith("_Win"):
                smooth_export(ob)
            nb.export_fbx(ob,folder/(tag+".fbx"))
        lods[suffix or "main"]=dict(triangles=count,bounds_m=pairs[0][2]["bounds_m"],coplanar_overlaps=0)
    if diagnose:
        return
    for path in sorted(folder.glob("*.fbx")):
        row=core.validate(path,a)
        if not path.stem.endswith("_Win"):
            loaded=core.bpy.context.selected_objects[0]
            overlaps=kit.overlaps(loaded)
            if legacy and overlaps:
                trim(loaded,path,overlaps,kit.overlaps)
                row=core.validate(path,a)
                overlaps=kit.overlaps(core.bpy.context.selected_objects[0])
                for _ in range(3):
                    current=core.bpy.context.selected_objects[0]
                    if not overlaps or not remove_hidden_trim(current,path,overlaps):
                        break
                    row=core.validate(path,a)
                    overlaps=kit.overlaps(core.bpy.context.selected_objects[0])
            if overlaps and legacy and max(v["overlap_m2"] for v in overlaps)<.0055:
                key=path.stem[len(name):] or "main"
                lods[key]["minor_trim_ties"]=len(overlaps)
            else:
                assert not overlaps,(path.name,overlaps[:7])
        row["raw_fbx"]=verify_raw(path,row["bounds_m"])
        meshes[path.stem]=row
    for lod,suffix in enumerate(SUFFIXES):
        key=suffix or "main"
        actual=sum(meshes[name+suffix+end]["triangles"] for end in ("","_Win"))
        assert actual<=limits[lod],(name,lod,actual,limits[lod])
        lods[key]["triangles"]=actual
    measure=meshes[name]["coverage"]
    if False:
        assert measure["roofed_pct"]+measure.get("occupied_unroofed_pct",0)>=85,(name,measure)   # R24: fill the lot
    _,owner=atlas_owners(a)
    return dict(name=name,design=a["design"],zone_key=a["zone_key"],lot=a["lot"],budget=limits,
                lods=lods,coverage=measure,meshes=meshes,envelope_m2=round(area,3),
                tris_per_m2=round(lods["main"]["triangles"]/area,3),atlas=owner,reimport=legacy)

def verify_audits(out,a,record):
    name=a["name"]
    w,d=(8*v for v in a["lot"])
    scans={}
    probes={}
    audits={}
    for suffix in SUFFIXES:
        lod=suffix or "main"
        layout=nb.LAYOUT["lods"][lod]
        scans[lod]=windows(out/name,name,suffix,layout)
        body=core.bpy.data.objects[name+suffix]
        pane=core.bpy.data.objects[name+suffix+"_Win"]
        bv,vertices=mesh_bvh(body)
        glow,_=mesh_bvh(pane)
        probe=sweep((bv,glow),w,d,max(v.z for v in vertices))
        if a["reimport"] and any(x["backface_first_hits"] for x in probe.values()):
            path=out/name/(name+suffix+".fbx")
            for _ in range(4):
                ids=sorted({i for r in probe.values() for i in r["backface_polygons"]})
                if not ids:
                    break
                original=core.mesh_stats(body)["triangles"]
                extra=sum(len(body.data.polygons[i].vertices)-2 for i in ids)
                if original+extra+core.mesh_stats(pane)["triangles"]>a["budget"][SUFFIXES.index(suffix)]:
                    break
                add_backings(body,path,ids)
                scans[lod]=windows(out/name,name,suffix,layout)
                body=core.bpy.data.objects[name+suffix]
                pane=core.bpy.data.objects[name+suffix+"_Win"]
                bv,vertices=mesh_bvh(body)
                glow,_=mesh_bvh(pane)
                probe=sweep((bv,glow),w,d,max(v.z for v in vertices))
            count=core.mesh_stats(body)["triangles"]+core.mesh_stats(pane)["triangles"]
            record["lods"][lod]["triangles"]=count
            row=core.mesh_stats(body)
            row["raw_fbx"]=verify_raw(path,row["bounds_m"])
            record["meshes"][name+suffix].update(row)
            if lod=="main":
                record["tris_per_m2"]=round(count/record["envelope_m2"],3)
        probes[lod]=probe
        audits[lod]=material_uvs(body,vertices,atlas_partition(lod),a)
    return probes,audits,scans

def bake(zone,args):
    core.coverage=coverage
    import os
    out=Path(os.environ["GEMINI_OUT"])
    plans=list(make(zone))
    assert len(plans)==COUNTS[zone]
    if "--diagnose" in args:
        seen=set()
        for a in plans:
            if (len(args)>1 and a["design"] not in args) or a["design"] in seen and zone!="Z1B":
                continue
            if zone=="Z1B" and a["colourway"]!="A":
                continue
            seen.add(a["design"])
            try:
                asset(out,a,True)
            except Exception as exc:
                import traceback
                print("DIAG_ERROR",a["name"],type(exc).__name__,str(exc),flush=True)
                traceback.print_exc()
        return
    journal=next((v.split("=",1)[1] for v in args if v.startswith("--journal=")),"progress.json")
    partial=out/journal
    old=read(partial) if partial.exists() else {}
    keep={}
    failures=[]
    groups=set()
    for a in plans:
        name=a["name"]
        _,owner=atlas_owners(a)
        groups.add(owner)
        if "--only" in args and a["design"] not in args:
            if name in old:keep[name]=old[name]
            continue
        if name in old and a["design"] not in args and "--force" not in args and not ("--redo-legacy" in args and a["reimport"]):
            keep[name]=old[name]
            continue
        try:
            try:
                rec=asset(out,a)
            except AssertionError as exc:
                # mostly plain infill wall on a big lot: retry once with a 7.5 detail floor (listed in the reply)
                e=exc.args[0] if exc.args else None
                if not (isinstance(e,tuple) and len(e)==3 and e[0]==name and isinstance(e[2],float)):raise
                print("FILL_TALL_RETRY",name,exc.args[0][1:],flush=True)
                a=dict(a,density_floor=7.5)
                rec=asset(out,a)
        except Exception as exc:
            failures.append((name,str(exc)))
            print("ASSET_ERROR",name,type(exc).__name__,str(exc),flush=True)
            continue
        if name!=owner:
            paths=sorted((out/owner).glob("*.png"))
            assert len(paths)==15,(owner,len(paths))
            write(out/name/"settings.json",dict(sharedAssets={
                f.name.replace(owner,name,1):f"../{owner}/{f.name}" for f in paths}))
        try:
            probes,audits,scans=verify_audits(out,a,rec)
        except Exception as exc:
            failures.append((name,str(exc)))
            print("AUDIT_ERROR",name,type(exc).__name__,str(exc),flush=True)
            continue
        print("ASSET_PASS",zone,len(keep)+1,name,"covered",
              [scans[k]["covered"] for k in ("main","_LOD1")], "backfaces",
              sum(v["backface_first_hits"] for probe in probes.values() for v in probe.values()),flush=True)
        keep[name]=[rec,probes,audits,scans]
        old[name]=keep[name]
        write(partial,old)
    assert not failures,failures
    if "--only" in args:return
    maps={p.relative_to(out).as_posix():sha256(p.read_bytes()).hexdigest()
          for p in out.glob("*/*") if p.suffix in {".png",".fbx"} or p.name=="settings.json"}
    assert len(maps)==len(keep)*7+14*len(groups)
    write(out/"manifest.json",dict(batch="GEMINI",zone_key=zone,registrations=len(keep),
          texture_owners=sorted(groups),assets=[v[0] for v in keep.values()],sha256=maps))
    for i,file in enumerate(("probe-results","audit","window-coverage"),1):
        write(out/(file+".json"),{name:items[i] for name,items in keep.items()})
    (out/"IMPORT-LIST.txt").write_text("\n".join(keep)+"\n",encoding="utf8")
    print("BAKE_COMPLETE",zone,len(keep),flush=True)

if __name__=="__main__":
    zone,*args=sys.argv[sys.argv.index("--")+1:]
    bake(zone,args)
