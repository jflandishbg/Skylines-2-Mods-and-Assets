"""Street-height comparisons from the actual before/after FBXs."""
from pathlib import Path
import math
import sys

sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
from mathutils import Vector
from round5_specs import make
from detail_specs import atlas_owners, INDUSTRY
import preview_round5 as p

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT.with_name(ROOT.name[:-1])
OUT=ROOT/"previews"/"closeups"
OUT.mkdir(exist_ok=True)
PLANS=list(make())
INDUSTRIAL=("RedentsAteliers","MoulinFilature","GazometreBatterie","HalleFonderie")
STYLES=[a for a in PLANS if (INDUSTRY or a["colourway"]=="A") and a["lot"][1]==(5 if INDUSTRY else 3)
        and (not INDUSTRY or a["design"] in INDUSTRIAL)]
if INDUSTRY:
    STYLES.sort(key=lambda a:INDUSTRIAL.index(a["design"]))
OLD_OWNERS={z:next(a["name"] for a in PLANS if a["zone_key"]==z)
            for z in {a["zone_key"] for a in PLANS}}

def body_material(folder,owner):
    key=str(folder/owner)
    cached=bpy.data.materials.get(key)
    if cached:return cached
    m,bs=p.material(key,(.6,.4,.28),.66)
    nodes=m.node_tree.nodes
    links=m.node_tree.links
    for mode in ("BaseColor","Normal","MaskMap"):
        node=nodes.new("ShaderNodeTexImage")
        node.image=bpy.data.images.load(str(folder/owner/f"{owner}_{mode}.png"),check_existing=True)
        if mode=="BaseColor":
            links.new(node.outputs["Color"],bs.inputs["Base Color"])
            mix=nodes.new("ShaderNodeMixShader")
            links.new(node.outputs["Alpha"],mix.inputs[0])
            links.new(nodes.new("ShaderNodeBsdfTransparent").outputs[0],mix.inputs[1])
            links.new(bs.outputs[0],mix.inputs[2])
            links.new(mix.outputs[0],nodes.get("Material Output").inputs["Surface"])
        elif mode=="Normal":
            node.image.colorspace_settings.name="Non-Color"
            normal=nodes.new("ShaderNodeNormalMap")
            normal.inputs["Strength"].default_value=.37
            links.new(node.outputs["Color"],normal.inputs["Color"])
            links.new(normal.outputs[0],bs.inputs["Normal"])
        else:
            node.image.colorspace_settings.name="Non-Color"
            node.image.alpha_mode="CHANNEL_PACKED"
            rough=nodes.new("ShaderNodeMath")
            rough.operation="SUBTRACT"
            rough.inputs[0].default_value=1
            links.new(node.outputs["Alpha"],rough.inputs[1])
            links.new(rough.outputs[0],bs.inputs["Roughness"])
    return m

def load(folder,name,owner):
    for suffix in ("","_Win"):
        path=folder/name/f"{name}{suffix}.fbx"
        bpy.ops.import_scene.fbx(filepath=str(path),axis_forward="-Z",axis_up="Y")
        ob=bpy.context.selected_objects[0]
        ob.data.materials.clear()
        ob.data.materials.append(p.GLASS if suffix else body_material(folder,owner))

def view(a,old=False,reference=False):
    p.reset("day")
    p.SC.cycles.samples=14
    p.SC.render.resolution_x,p.SC.render.resolution_y=1080,724
    if reference:
        folder=ROOT.parent/"2026-11-10_round10"/"import_Z10"
        name="NA_PdDRedentsTissageB_L1_4x5"
        owner="NA_PdDRedentsTissage_L1_4x4"
        w,d=32,40
    else:
        folder=(OLD if old else ROOT)/f'import_{a["zone_key"]}'
        owner=OLD_OWNERS[a["zone_key"]] if old else atlas_owners(a)[1]
        name=a["name"]
        w,d=(8*v for v in a["lot"])
    load(folder,name,owner)
    p.cube("Turf",(0,0,-.072),(w+6,d+3,.136),p.FILL)
    p.cube("Walk",(0,-d*.5-1.07,-.041),(w+8,2.13,.078),p.WALK)
    p.cube("Road",(0,-d*.5-5.6,-.105),(w+12,7.0,.16),p.ROAD)
    broad=INDUSTRY or reference
    target=Vector((-.68,-d/2+(8.6 if broad else 6.6),5.8 if broad else 4.08))
    azimuth=math.radians(26)
    distance=25
    direction=Vector((math.sin(azimuth)*math.cos(math.pi/6),
                      -math.cos(azimuth)*math.cos(math.pi/6),math.sin(math.pi/6)))
    cam=p.camera(target+distance*direction,target)
    cam.data.ortho_scale=37 if broad else 20.6
    p.light("SUN",(-19,-27,44),2.05,(1,.94,.83),target)
    p.light("AREA",(23,-24,29),6300,(.80,.90,1),target,25)
    tag="R10-reference" if reference else a["design"]+("-old" if old else "-new")
    p.SC.render.filepath=str(OUT/(tag+".png"))
    bpy.ops.render.render(write_still=True)

if __name__=="__main__":
    args=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    start=int(args[0]) if args else 0
    stop=int(args[1]) if args else len(STYLES)
    for a in STYLES[start:stop]:
        if "new-only" not in args:
            view(a,old=True)
        view(a)
    if not INDUSTRY and start==0:
        view(None,reference=True)
    print("DETAIL_PREVIEWS_READY",start,stop,flush=True)
