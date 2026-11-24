"""Ray audit on every pane of each service FBX at all three detail levels."""
import json
import sys
from pathlib import Path
from collections import Counter
import bpy
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/"source"))
from round5_specs import make
SUFFIXES=("", "_LOD1", "_LOD2")
HOSPITAL="NA_PdDHopitalInvalides"
def read(p):
    return json.loads(p.read_text(encoding="utf8"))

def import_fbx(path):
    bpy.ops.import_scene.fbx(filepath=str(path),axis_forward="-Z",axis_up="Y")
    return bpy.context.selected_objects[0]

def tile(poly,uv,layout):
    ids=poly.loop_indices
    u,v=(sum(uv[i].uv[k] for i in ids)/len(ids) for k in (0,1))
    return next((key for key,a in layout.items() if a["uv"][0]-.000002<=u<=a["uv"][2]+.000002
                 and a["uv"][1]-.000002<=v<=a["uv"][3]+.000002),"other")

def audit(folder,name,suffix,layout):
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob,do_unlink=True)
    body=import_fbx(folder/f"{name}{suffix}.fbx")
    win=import_fbx(folder/f"{name}{suffix}_Win.fbx")
    bverts=[body.matrix_world@v.co for v in body.data.vertices]
    bvh=BVHTree.FromPolygons(bverts,[tuple(p.vertices) for p in body.data.polygons])
    uv=body.data.uv_layers.active.data
    wverts=[win.matrix_world@v.co for v in win.data.vertices]
    wm=win.matrix_world.to_3x3().inverted().transposed()
    walls={}
    records=[]
    total=0
    # Interior samples avoid the coincident perimeter of a normal window reveal.
    for pane in win.data.polygons:
        pts=[wverts[i] for i in pane.vertices]
        normal=(wm@pane.normal).normalized()
        mid=sum(pts[1:],pts[0].copy())/len(pts)
        samples=[mid]+[mid.lerp(q,.54) for q in pts]+[mid.lerp((p+q)/2,.71) for p,q in zip(pts,pts[1:]+pts[:1])]
        near_hits=Counter()
        all_hits=Counter()
        for point in samples:
            total+=1
            loc,norm,i,d=bvh.ray_cast(point+normal*.012,normal,1.188)
            if loc is None or norm.dot(normal)<.94:
                continue
            if i not in walls:
                walls[i]=tile(body.data.polygons[i],uv,layout)
            mat=walls[i]
            if mat in {"Iron","TinGreen","Black","Green","Mustard","TinOxide"}:
                continue
            all_hits[mat]+=1
            outside=bvh.ray_cast(point+normal*180,-normal,180)[0]
            if outside is not None and (outside-loc).length<=.018:
                near_hits[mat]+=1
        # Keep partial cover as well as whole panes. A single edge hit is recorded separately.
        n=sum(near_hits.values())
        k=sum(all_hits.values())
        if k:
            records.append(dict(pane=pane.index,world=[round(v,3) for v in mid],
                normal=[round(v,3) for v in normal],samples=len(samples),
                near_same_facing=k,exterior_cover=n,exterior_blocking_tiles=dict(near_hits),blockers=dict(all_hits)))
    return dict(panes=len(win.data.polygons),rays=total,near_hits=sum(d["near_same_facing"]>=2 for d in records),
        covered=sum(d["exterior_cover"]>=2 for d in records),fully_covered=sum(d["exterior_cover"]>=.75*d["samples"] for d in records),
        single_exterior_sample=sum(d["exterior_cover"]==1 for d in records),details=records)

def main(zone):
    out=ROOT/f"import_{zone}"
    layout=read(ROOT/"source"/"kit"/"atlas_layout.json")["lods"]
    result={}
    for a in make(zone):
        n=a["name"]
        result[n]={}
        for s in SUFFIXES:
            k=s or "main"
            result[n][k]=audit(out/n,n,s,layout[k])
        print("WINDOW_SCAN",n,[(k,v["panes"],v["covered"],v["fully_covered"],v["near_hits"]) for k,v in result[n].items()],flush=True)
    assert len(result)=={"Z1C":72,"Z1A":18}[zone]
    (out/"window-coverage.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
    print("WINDOW_SCAN_COMPLETE",len(result),flush=True)
if __name__=="__main__":
    main(sys.argv[-1])
