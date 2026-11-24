"""Export all Round 11 registrations and verify each FBX and shared texture link."""
from hashlib import sha256
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))

from mathutils import Vector
from mathutils.bvhtree import BVHTree
from round11_geometry import build,core,kit,nb
from round5_specs import make
from fbx_check import verify_raw
from detail_mesh import smooth_export
from detail_specs import atlas_owners,envelope

ROOT=Path(__file__).resolve().parents[1]
SUFFIXES=("","_LOD1","_LOD2")
MAPS=("BaseColor","Normal","MaskMap","ControlMask","Emissive")
EXPECTED={"Z1C":72,"Z1A":18}

def write(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf8")

def dispose():
    nb.clear_objects()
    for mesh in list(core.bpy.data.meshes):
        if mesh.users==0:core.bpy.data.meshes.remove(mesh)
    for material in list(core.bpy.data.materials):
        if material.users==0:core.bpy.data.materials.remove(material)

def measured_coverage(obj,a):
    w,d=[8*n for n in a["lot"]]
    mesh=obj.data
    vertices=[obj.matrix_world@v.co for v in mesh.vertices]
    tree=BVHTree.FromPolygons(vertices,[tuple(p.vertices) for p in mesh.polygons])
    roof_keys=("TinFlat","SlateDark","SlateGreen","SlateBrown","TinOxide","SolarSlate","GardenGlass")
    atlas=nb.LAYOUT["lods"]["main"]
    tiles=[atlas[k]["uv"] for k in roof_keys]
    uv=mesh.uv_layers.active.data
    roof_polys=[]
    to_world=obj.matrix_world.to_3x3().inverted().transposed()
    for f in mesh.polygons:
        if (to_world@f.normal).normalized().z<=.17 or max(vertices[i].z for i in f.vertices)<2.60:
            continue
        n=len(f.loop_indices)
        u,v=(sum(uv[i].uv[k] for i in f.loop_indices)/n for k in (0,1))
        if any(l<=u<=r and b<=v<=t for l,b,r,t in tiles):
            roof_polys.append(tuple(f.vertices))
    assert roof_polys,a["name"]
    roofs=BVHTree.FromPolygons(vertices,roof_polys)
    step=.25
    roof=paved=open_ground=0
    for i in range(round(w/step)):
        x=(i+.5)*step
        for j in range(round(d/step)):
            y=(j+.5)*step
            start=Vector((x-w/2,y-d/2,70))
            direction=Vector((0,0,-1))
            if roofs.ray_cast(start,direction,72)[0] is not None:
                roof+=1
            elif tree.ray_cast(start,direction,72)[0] is not None:
                paved+=1
            else:
                open_ground+=1
    total=round(w/step)*round(d/step)
    return dict(sample_spacing_m=step,roofed_pct=round(100*roof/total,3),
                occupied_unroofed_pct=round(100*paved/total,3),open_pct=round(100*open_ground/total,3))

def check_asset(out,a,diagnose):
    n=a["name"]
    area=envelope(a)
    folder=out/n
    if not diagnose:folder.mkdir(exist_ok=True)
    lods={};meshes={}
    physical=[]
    for lod,suffix in enumerate(SUFFIXES):
        grades=(0,1,2,3) if lod==0 else (0,)
        for grade in grades:
            dispose()
            h=build(dict(a,detail_grade=grade),lod)
            pairs=[]
            for m,tag in ((h.body,n+suffix),(h.windows,n+suffix+"_Win")):
                ob=core.optimize_far(m.object(tag,None if tag.endswith("_Win") else core.bpy.data.materials.new(tag)),lod)
                pairs.append((ob,tag,core.mesh_stats(ob)))
            count=sum(s["triangles"] for _,_,s in pairs)
            if lod or count/area>=8 or count>=a["budget"][lod]:
                break
        body,_,stats=pairs[0]
        physical.append(stats["bounds_m"])
        hits=kit.overlaps(body)
        if diagnose:
            print("CHECK",a["design"],a["lot"][1],lod,count,len(hits),round(count/area,3) if lod==0 else 0,hits[:2],stats["bounds_m"],flush=True)
            if lod==0:print("COVER",a["design"],a["lot"][1],measured_coverage(body,a),flush=True)
            continue
        assert count<=a["budget"][lod],(n,lod,count,a["budget"])
        if lod==0:assert count/area>=8,(n,count,area,count/area)
        assert not hits,(n,lod,hits[:7])
        for ob,tag,_ in pairs:
            if not tag.endswith("_Win"):smooth_export(ob)
            nb.export_fbx(ob,folder/(tag+".fbx"))
        lods[suffix or "main"]=dict(triangles=count,bounds_m=stats["bounds_m"],coplanar_overlaps=0)
    if diagnose:return
    for file in sorted(folder.glob("*.fbx")):
        meshes[file.stem]=core.validate(file,a)
        meshes[file.stem]["raw_fbx"]=verify_raw(file,meshes[file.stem]["bounds_m"])
        if file.stem.endswith("_Win"):continue
        hits=kit.overlaps(core.bpy.context.selected_objects[0])
        assert not hits,(file.name,hits[:7])
    assert len(meshes)==6
    coverage=meshes[n]["coverage"]
    lo,hi=40,48
    assert lo<=coverage["roofed_pct"]<=hi,(n,coverage)
    assert max(abs(x-y) for b in physical[1:] for p,q in zip(physical[0],b) for x,y in zip(p,q))<=.84,(n,physical)
    return dict(name=n,design=a["design"],zone_key=a["zone_key"],lot=a["lot"],budget=a["budget"],
                lods=lods,coverage=coverage,meshes=meshes,envelope_m2=round(area,3),
                tris_per_m2=round(lods["main"]["triangles"]/area,3),atlas=atlas_owners(a)[1])

def run(zone,diagnose=False,which=(),force=False):
    out=ROOT/f"import_{zone}"
    plans=list(make(zone))
    assert len(plans)==EXPECTED[zone]
    if diagnose:
        for a in plans:
            if a["colourway"]=="A" and (not which or a["design"] in which):
                try:check_asset(out,a,True)
                except Exception as e:print("DIAG_ERROR",a["name"],type(e).__name__,e,flush=True)
        return
    groups={atlas_owners(a)[1] for a in plans}
    all_maps={owner:{f"{owner}{suffix}_{key}.png" for suffix in SUFFIXES for key in MAPS} for owner in groups}
    for owner,maps in all_maps.items():
        assert {p.name for p in (out/owner).glob("*.png")}==maps
    partial=out/"progress.json"
    previous={item["name"]:item for item in json.loads(partial.read_text(encoding="utf8"))} if partial.exists() else {}
    core.coverage=measured_coverage
    records=[]
    for a in plans:
        n=a["name"]
        if not force and n in previous and (not which or a["design"] not in which):
            records.append(previous[n])
            continue
        rec=check_asset(out,a,False)
        _,owner=atlas_owners(a)
        if n!=owner:
            write(out/n/"settings.json",dict(sharedAssets={old.replace(owner,n,1):f"../{owner}/{old}" for old in sorted(all_maps[owner])}))
        records.append(rec)
        previous[n]=rec
        write(partial,list(previous.values()))
        print("ASSET_PASS",len(records),n,rec["coverage"]["roofed_pct"],flush=True)
    hashes={p.relative_to(out).as_posix():sha256(p.read_bytes()).hexdigest()
            for p in out.rglob("*") if p.suffix in {".png",".fbx",".json"} and p.name not in
            {"progress.json","manifest.json","probe-results.json","audit.json","designs.json","window-coverage.json"}}
    assert len(hashes)==len(plans)*7+14*len(groups)
    write(out/"manifest.json",dict(batch="R11b",reimport=False,zone_key=zone,registrations=len(plans),texture_owners=sorted(groups),assets=records,sha256=hashes))
    (out/"IMPORT-LIST.txt").write_text("\n".join(a["name"] for a in plans)+"\n",encoding="utf8")
    print("BAKE_COMPLETE",zone,len(records),flush=True)

if __name__=="__main__":
    zone,*args=sys.argv[sys.argv.index("--")+1:]
    run(zone,"--diagnose" in args,[x for x in args if not x.startswith("--")],"--force" in args)
