"""Matched-light visual checks rendered from delivered meshes."""
from pathlib import Path
import json
import math
import sys

sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from mathutils import Vector
from preview_detail import p, body_material
from r12_specs import make, atlas_owners

ROOT=Path(__file__).resolve().parents[1]
INBOX=ROOT.parent
PRE=ROOT/"previews"
REFS={
 "Z1B":("2026-11-06_chateau-villas/bake",("NA_PdDManoirFederalRoyal_L1_2x5","NA_PdDVillaDuParc_L1_2x5")),
 "Z2B":("2026-11-07_round2-batch2b/bake",("NA_PdDRapportLoggiaToscane_L1_2x4","NA_PdDRapportRotondeAngleLeftCorner_L1_2x4")),
 "Z4":("2026-11-09_round9/import_Z4",("NA_PdDCiteHorloge_L1_2x4","NA_PdDGarniAngle_L1_2x3")),
}
HOUSE="NA_PdDMaisonSerre_L1_2x3"
DIRECTION=Vector((math.sin(math.radians(25))*math.cos(math.pi/6),
                  -math.cos(math.radians(25))*math.cos(math.pi/6),.5))

def read(path):
    return json.loads(path.read_text(encoding="utf8"))

def previous(folder,name):
    manifest=read(folder/"manifest.json")
    a=next(r for r in manifest["assets"] if r["name"]==name)
    design=name.split("_L1_")[0][6:]
    lot=[int(v) for v in name.split("_L1_")[1].split("x")]
    owner=a.get("atlas",manifest.get("texture_owner"))
    assert owner
    return dict(name=name,display_title=design,design=design,lot=lot,folder=folder,owner=owner,props=[])

def new(a):
    return dict(a,folder=ROOT/f'import_{a["zone_key"]}',owner=atlas_owners(a)[1])

def load(a,mode,offset=(0,0,0)):
    folder,name=a["folder"],a["name"]
    pts=[]
    for ext in ("","_Win"):
        p.bpy.ops.import_scene.fbx(filepath=str(folder/name/f"{name}{ext}.fbx"),axis_forward="-Z",axis_up="Y")
        ob=p.bpy.context.selected_objects[0]
        ob.location+=Vector(offset)
        p.bpy.context.view_layer.update()
        ob.data.materials.clear()
        ob.data.materials.append(p.BLACK if mode=="shape" else
                                 (p.NIGHT if mode=="night" else p.GLASS) if ext else body_material(folder,a["owner"]))
        pts.extend(ob.matrix_world@v.co for v in ob.data.vertices)
    return pts

def save(name):
    p.SC.render.filepath=str(PRE/(name+".png"))
    p.bpy.ops.render.render(write_still=True)

def daylight(aim):
    p.light("SUN",(-19,-27,44),2.05,(1,.94,.83),aim)
    p.light("AREA",(23,-24,29),6300,(.80,.90,1),aim,25)

def profile(a):
    p.reset("shape")
    p.SC.cycles.samples=3
    p.SC.render.resolution_x,p.SC.render.resolution_y=248,232
    load(a,"shape",(0,4*a["lot"][1],0))
    for side,direction in (("front",Vector((.21,-.97,.24))),("side",Vector((.95,-.21,.28)))):
        aim=Vector((0,16,7.6))
        cam=p.camera(aim+72*direction,aim)
        cam.data.ortho_scale=47
        save("profile-"+a["design"]+"-"+side)

def closeup(a,house=False):
    p.reset("day")
    p.SC.cycles.samples=9
    p.SC.render.resolution_x,p.SC.render.resolution_y=840,620
    w,d=(8*n for n in a["lot"])
    vertices=load(a,"day",(0,d/2,0))
    p.garden(a,0)
    p.cube("Lot ground",(0,d/2,-.08),(w+.30,d+.10,.149),p.FILL)
    p.cube("Sidewalk",(0,-1.08,-.05),(w+5,2.16,.09),p.WALK)
    p.cube("Road",(0,-5.65,-.095),(w+7,7,.15),p.ROAD)
    mass=[v for v in vertices if v.z>=2.00]
    ylo,yhi=min(v.y for v in mass),max(v.y for v in mass)
    ztop=max(v.z for v in mass)
    aim=Vector((0,(yhi+ylo)/2,ztop*.40))
    camera=p.camera(aim+25*DIRECTION,aim)
    p.fit(camera,mass+[Vector((w*.43,ylo-2.2,0)),Vector((-w*.43,ylo-2.2,0))],1.17)
    daylight(aim)
    save("close-"+("R11b-reference" if house else a["design"]))

def street(zone,group,mode):
    p.reset(mode)
    p.SC.cycles.samples=10
    p.SC.render.resolution_x,p.SC.render.resolution_y=2400,702
    width=sum(8*a["lot"][0] for a in group)
    left=-width/2
    points=[]
    for a in group:
        w,d=(8*n for n in a["lot"])
        x=left+w/2
        left+=w
        points.extend(v for v in load(a,mode,(x,d/2,0)) if v.z>2)
        p.garden(a,x)
        points.extend((Vector((x-w*.48,-2,0)),Vector((x+w*.48,-2,0))))
    p.cube("Turf",(0,24,-.086),(width+20,48,.16),p.FILL)
    p.cube("Sidewalk",(0,-1.25,-.06),(width+20,2.50,.106),p.WALK)
    p.cube("Road",(0,-7.9,-.11),(width+29,10.7,.18),p.ROAD)
    aim=(0,10,5)
    cam=p.camera((23,-160,69),aim)
    p.fit(cam,points,1.075)
    if mode=="day":
        daylight(aim)
    else:
        p.light("SUN",(-34,-59,93),.22,(.62,.72,1),aim)
    save(zone+"-street-"+mode)

def main(zone):
    b,ref=REFS[zone]
    old=[previous(INBOX/b,n) for n in ref]
    desired=5 if zone=="Z1B" else 4
    plans=list(make(zone))
    families=list(dict.fromkeys(a["design"] for a in plans))
    fresh=[new(next(a for a in plans if a["design"]==f and a["lot"][1]==desired
                    and (zone=="Z4" or a["colourway"]=="ABC"[i%3]))) for i,f in enumerate(families)]
    for a in fresh+old:
        profile(a)
    for a in fresh:
        closeup(a)
    if zone=="Z1B":
        closeup(previous(INBOX/"2026-11-10_round11b/import_Z1C",HOUSE),house=True)
    picks=([fresh[0],fresh[1],fresh[2],fresh[3],fresh[4],fresh[6]] if zone=="Z1B" else
           fresh+[new(next(a for a in plans if a["design"]==f and a["lot"][1]==5 and a["colourway"]=="C")) for f in families]
           if zone=="Z2B" else [fresh[i] for i in (0,1,3,5,8,9)])
    lineup=[picks[0],old[0],*picks[1:4],old[1],*picks[4:]]
    for mode in ("day","night"):
        street(zone,lineup,mode)
    (PRE/(zone+"-review.json")).write_text(json.dumps(
        dict(new=[(a["design"],a["display_title"]) for a in fresh],old=[a["design"] for a in old],
             lineup=[a["name"] for a in lineup]),ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("R12_VISUALS",zone,flush=True)

if __name__=="__main__":
    main(sys.argv[-1])
