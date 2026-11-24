"""Render the delivered Round 11 geometry in street ensembles and same-scale profiles."""
from pathlib import Path
import sys
from mathutils import Vector
import bpy
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from round5_specs import make

ROOT=Path(__file__).resolve().parents[1]
PRE=ROOT/"previews"
SC=bpy.context.scene
OWNERS={zone:next(make(zone))["name"] for zone in ("Z1C","Z1A")}
OWNERS["current"]="NA_PdDMercerMansardPair_L1_2x2"
OLD=ROOT.parent/"2026-11-06_chateau-townhouses"/"bake"
COURONNE=dict(name="NA_PdDCouronnePavilionPair_L1_2x3",design="CouronnePavilionPair",
              zone_key="current",lot=[2,3],props=[])
BASIN=dict(name="NA_PdDBasinLoggiaHouse_L1_2x2",design="BasinLoggiaHouse",
           zone_key="current",lot=[2,2],props=[])
BLOCK=("MaisonColombages","JumellesVerger","CouronnePavilionPair","MaisonPigeonnier","MaisonAtelier",
       "MaisonSerre","MaisonSurCave","BasinLoggiaHouse","ShotgunCamelback","MaisonPuits")

def material(name,colour,rough=.61,emission=0):
    m=bpy.data.materials.new(name);m.use_nodes=True
    bs=m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value=(*colour,1)
    bs.inputs["Roughness"].default_value=rough
    if emission:
        bs.inputs["Emission Color"].default_value=(*colour,1)
        bs.inputs["Emission Strength"].default_value=emission
    return m,bs

GLASS=material("Preview glass",(.15,.22,.27),.24)[0]
BLACK,bs=material("Profile",(.022,.041,.032),.72)
tree=BLACK.node_tree
ink=tree.nodes.new("ShaderNodeEmission")
ink.inputs["Color"].default_value=(.021,.046,.035,1)
tree.links.new(ink.outputs["Emission"],tree.nodes.get("Material Output").inputs["Surface"])
FILL=material("Turf",(.21,.29,.18))[0]
LEAVES=material("Garden leaves",(.14,.24,.10))[0]
TRUNK=material("Tree trunks",(.21,.15,.09))[0]
ROAD=material("Street",(.075,.095,.094))[0]
WALK=material("Sidewalk",(.33,.33,.29))[0]
IRON=material("Street iron",(.04,.055,.049))[0]
GLOW=material("Lamp glass",(.84,.56,.27),.43,2.65)[0]
NIGHT,bs=material("Room-grid preview",(.19,.15,.11),.32,.81)
t=NIGHT.node_tree
uv=t.nodes.new("ShaderNodeTexCoord")
scale=t.nodes.new("ShaderNodeVectorMath");scale.operation="SCALE";scale.inputs["Scale"].default_value=5
cell=t.nodes.new("ShaderNodeVectorMath");cell.operation="FLOOR"
noise=t.nodes.new("ShaderNodeTexWhiteNoise")
ramp=t.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position=.60
ramp.color_ramp.elements[0].color=(.007,.009,.012,1)
ramp.color_ramp.elements[1].position=.93
ramp.color_ramp.elements[1].color=(.86,.56,.28,1)
t.links.new(uv.outputs["UV"],scale.inputs[0])
t.links.new(scale.outputs["Vector"],cell.inputs[0])
t.links.new(cell.outputs["Vector"],noise.inputs["Vector"])
t.links.new(noise.outputs["Value"],ramp.inputs[0])
t.links.new(ramp.outputs["Color"],bs.inputs["Emission Color"])

def atlas(zone,suffix):
    key=f"{zone} actual {suffix}"
    if key in bpy.data.materials:return bpy.data.materials[key]
    owner=OWNERS[zone]
    folder=OLD if zone=="current" else ROOT/f"import_{zone}"
    m,bs=material(key,(.56,.42,.28),.63)
    t=m.node_tree
    for kind in ("BaseColor","Normal","MaskMap"):
        path=folder/owner/f"{owner}{suffix}_{kind}.png"
        node=t.nodes.new("ShaderNodeTexImage")
        node.image=bpy.data.images.load(str(path),check_existing=True)
        if kind=="BaseColor":
            t.links.new(node.outputs["Color"],bs.inputs["Base Color"])
            continue
        node.image.colorspace_settings.name="Non-Color"
        if kind=="Normal":
            n=t.nodes.new("ShaderNodeNormalMap");n.inputs["Strength"].default_value=.45
            t.links.new(node.outputs["Color"],n.inputs["Color"]);t.links.new(n.outputs["Normal"],bs.inputs["Normal"])
        else:
            node.image.alpha_mode="CHANNEL_PACKED"
            rough=t.nodes.new("ShaderNodeMath");rough.operation="SUBTRACT";rough.inputs[0].default_value=1
            t.links.new(node.outputs["Alpha"],rough.inputs[1]);t.links.new(rough.outputs[0],bs.inputs["Roughness"])
    return m

def reset(mode):
    for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users==0:bpy.data.meshes.remove(me)
    SC.render.engine="CYCLES"
    SC.cycles.samples=10 if mode=="shape" else 16
    SC.cycles.use_denoising=mode!="shape"
    SC.render.image_settings.file_format="PNG"
    SC.render.film_transparent=mode=="shape"
    SC.world.use_nodes=True
    w=SC.world.node_tree.nodes.get("Background")
    w.inputs[0].default_value=(.19,.29,.51,1) if mode=="night" else (.82,.89,.96,1)
    w.inputs[1].default_value=.35 if mode=="night" else .63
    SC.view_settings.view_transform="AgX"
    SC.view_settings.exposure=.35

def load(a,mode,offset=(0,0,0)):
    name=a["name"];zone=a["zone_key"]
    suff="_LOD1" if mode=="shape" else ""
    folder=OLD if zone=="current" else ROOT/f"import_{zone}"
    verts=[]
    for ext in ("","_Win"):
        path=folder/name/f"{name}{suff}{ext}.fbx"
        bpy.ops.import_scene.fbx(filepath=str(path),axis_forward="-Z",axis_up="Y")
        ob=bpy.context.selected_objects[0]
        ob.location+=Vector(offset)
        bpy.context.view_layer.update()
        ob.data.materials.clear()
        ob.data.materials.append(BLACK if mode=="shape" else
                                 (NIGHT if mode=="night" else GLASS) if ext else atlas(zone,suff))
        verts.extend(ob.matrix_world@v.co for v in ob.data.vertices)
    return verts

def cube(name,loc,dim,mat):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    ob=bpy.context.object;ob.name=name;ob.dimensions=dim
    ob.data.materials.append(mat)

def light(kind,xyz,energy,colour,target=None,scale=1):
    bpy.ops.object.light_add(type=kind,location=xyz)
    ob=bpy.context.object;ob.data.energy=energy;ob.data.color=colour
    if target is not None:ob.rotation_euler=(Vector(target)-ob.location).to_track_quat("-Z","Y").to_euler()
    if kind=="POINT":ob.data.shadow_soft_size=scale
    if kind=="AREA":ob.data.size=scale

def camera(xyz,aim):
    bpy.ops.object.camera_add(location=xyz)
    ob=bpy.context.object
    ob.rotation_euler=(Vector(aim)-ob.location).to_track_quat("-Z","Y").to_euler()
    ob.data.type="ORTHO";ob.data.sensor_fit="HORIZONTAL";SC.camera=ob
    return ob

def fit(ob,pts,pad=1.06):
    rot=ob.rotation_euler.to_matrix()
    right,up=rot@Vector((1,0,0)),rot@Vector((0,1,0))
    u=[(p-ob.location).dot(right) for p in pts]
    v=[(p-ob.location).dot(up) for p in pts]
    ob.location+=right*((max(u)+min(u))/2)+up*((max(v)+min(v))/2)
    aspect=SC.render.resolution_x/SC.render.resolution_y
    ob.data.ortho_scale=pad*max(max(u)-min(u),(max(v)-min(v))*aspect)

def save(name):
    SC.render.filepath=str(PRE/f"{name}.png")
    bpy.ops.render.render(write_still=True)

def profile(a):
    reset("shape")
    load(a,"shape")
    SC.render.resolution_x,SC.render.resolution_y=410,262
    ob=camera((14,-79,20),(0,0,6.0))
    ob.data.ortho_scale=32
    save(a["design"]+"-shape")

def garden(a,x):
    w=a["lot"][0]*8
    for prop in a["props"]:
        px,py,_=prop["position_lot_m"]
        loc=(x+px-w/2,py,0)
        sx,sy,sz=prop["size_m"]
        if prop["kind"]=="tree":
            cube("Tree trunk",(loc[0],loc[1],.72),(.16,.15,1.44),TRUNK)
            for dx,dy,dz in ((0,0,0),(-.42,.1,-.16),(.31,-.26,-.24)):
                bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=1,
                    location=(loc[0]+dx,loc[1]+dy,2.37+dz))
                ob=bpy.context.object
                ob.scale=(.85,.80,1.16)
                ob.data.materials.append(LEAVES)
        elif prop["kind"]=="hedge":
            cube("Clipped hedge",(loc[0],loc[1],sz*.5),(sx,sy,sz),LEAVES)

def street(zone,group,mode,index):
    reset(mode)
    SC.render.resolution_x,SC.render.resolution_y=3000,741
    length=sum(8*a["lot"][0] for a in group)
    left=-length/2
    points=[]
    for i,a in enumerate(group):
        width=8*a["lot"][0]
        x=left+width/2
        left+=width
        d=a["lot"][1]*8
        pts=load(a,mode,(x,d/2,0))
        garden(a,x)
        points.extend(v for v in pts if v.z>2)
        for v in (-1,1):points.append(Vector((x+v*width*.48,-2.10,0)))
    cube("District lawn",(0,13,-.096),(length+18,34,.185),FILL)
    cube("Sidewalk",(0,-1.4,-.060),(length+18,2.8,.115),WALK)
    cube("Street",(0,-8.8,-.13),(length+32,12,.205),ROAD)
    aim=(0,7,5)
    ob=camera((46,-155,62),aim)
    fit(ob,points,1.11)
    if mode=="day":
        light("SUN",(-62,-71,105),2.06,(1,.91,.78),aim)
        light("AREA",(31,-50,68),29000,(.76,.88,1),aim,66)
    else:
        light("SUN",(-33,-56,93),.19,(.60,.72,1),aim)
    save(f"R11-street-{mode}")

def main():
    profile_plans=[a for a in make() if a["lot"][1]==3 and a["colourway"]=="A"]
    plans={a["design"]:a for a in make() if a["lot"][1]==3 and a["colourway"]=="A"}
    color=("B","A","A","B","C","A","A","A","B","C")
    plans.update({a["design"]:a for a in (COURONNE,BASIN)})
    group=[]
    for design,tone in zip(BLOCK,color):
        if plans[design]["zone_key"]=="current":
            group.append(plans[design])
        else:
            group.append(next(a for a in make("Z1C") if a["design"]==design and a["colourway"]==tone and
                              a["lot"][1]==(2 if design in {"MaisonAtelier","MaisonSurCave","MaisonPigeonnier"} else 3)))
    for mode in ("day","night"):
        street("Z1C",group,mode,1)
    for a in [*profile_plans,COURONNE]:
        profile(a)
    print("PREVIEWS_READY R11",flush=True)

if __name__=="__main__":main()
