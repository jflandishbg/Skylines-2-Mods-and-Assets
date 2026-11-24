"""Preserve the original silhouettes while renewing masonry, glazing and trim."""
from collections import defaultdict
from functools import lru_cache
import math

from mathutils import Vector
from mathutils.bvhtree import BVHTree
import detail_mesh as detail
from r12_build import core,nb,g
from rebake_specs import INBOX,read
from audit_round5 import atlas_partition

MASONRY={"Brick085","Brick094","BuffBrick"}
MATERIALS={
 "Brick097":"Brick094","Brick074":"BuffBrick","Brick054":"Brick085",
 "BrownBrick":"Brick094","Chimney":"Brick085",
 "RenderSide":"RevealStone","RenderGrey":"Render",
 "FrontFlags":"YardSetts","CourtSetts":"YardSetts","MatteDial":"Dressed",
 "SootUnder":"RevealStone","ShutterFaded":"TinGreen","PatchedLime":"Render",
}
IGNORED={"RoofGreen","Ivy"}
ROOF={"TinFlat","Slate","SlateDark","SlateGreen","SlateBrown","TinOxide","Tin"}
SIGN_SLOTS=("VillaJeuDePaume","ImmeubleBowWindows","ImmeubleImprimeur","ImmeubleJardinHiver")

@lru_cache(maxsize=16)
def source_layout(batch,tag):
    return read(INBOX/batch/"source/kit/atlas_layout.json")["lods"][tag]

def load(a,lod,window=False):
    suffix=("" if lod==0 else "_LOD"+str(lod))+("_Win" if window else "")
    name=a["name"]
    p=INBOX/a["source_batch"]/a["source_import"]/name/(name+suffix+".fbx")
    core.bpy.ops.import_scene.fbx(filepath=str(p),axis_forward="-Z",axis_up="Y")
    ob=core.bpy.context.selected_objects[0]
    normal_transform=ob.matrix_world.to_3x3().inverted().transposed()
    v=[ob.matrix_world@p.co for p in ob.data.vertices]
    uv=ob.data.uv_layers.active.data
    faces=[([v[j] for j in f.vertices],[tuple(uv[j].uv) for j in f.loop_indices],
            (normal_transform@f.normal).normalized()) for f in ob.data.polygons]
    imported=ob.data
    materials=list(imported.materials)
    core.bpy.data.objects.remove(ob,do_unlink=True)
    core.bpy.data.meshes.remove(imported)
    for mat in materials:
        if mat is not None and not mat.users:
            core.bpy.data.materials.remove(mat)
    return faces

def tile(uv,layout):
    u,v=[sum(q[i] for q in uv)/len(uv) for i in (0,1)]
    for key,cell in layout.items():
        l,b,r,t=cell["uv"]
        if l-.000002<=u<=r+.000002 and b-.000002<=v<=t+.000002:
            return key
    raise ValueError(("Source UV has no tile",u,v))

def local(points):
    return [Vector((p.x,p.y-nb.YSHIFT,p.z)) for p in points]

def transfer(mesh,points,uv,source,target,flip=False):
    l,b,r,t=source["uv"]
    x,y,u,v=target["uv"]
    fx=lambda j:max(0,min(1,(j-l)/(r-l)))
    mesh._add(points,[(x+(u-x)*((1-fx(j)) if flip else fx(j)),
                       y+(v-y)*max(0,min(1,(k-b)/(t-b)))) for j,k in uv])

def reads_backwards(points,uv,n):
    """True when a sign's lettering runs right-to-left as seen from outside (mirrored Right-hand bakes)."""
    if abs(n.z)>.5:
        return False
    right=Vector((0,0,1)).cross(n)
    pairs=[(i,j) for i in range(len(points)) for j in range(i+1,len(points))]
    i,j=max(pairs,key=lambda q:abs(uv[q[1]][0]-uv[q[0]][0]))
    du=uv[j][0]-uv[i][0]
    return abs(du)>1e-6 and (points[j]-points[i]).dot(right)*du<0

def rear_layout(a,body):
    """Lot-metre rear line of the full-height house, and the blank one-storey boxes standing behind it."""
    w,d=[v*8 for v in a["lot"]]
    tall=[p for p,uv,n in body if abs(n.z)<.05 and max(v.z for v in p)>5.5]
    rear=max(v.y+d/2 for p in tall for v in p)
    planes={}
    for p,uv,n in body:
        if rear_clutter(a,p):
            continue   # the stripped garage is not a box to give a door to
        top=max(v.z for v in p)
        y=sum(v.y for v in p)/len(p)+d/2
        if n.y>.97 and top<5.0 and rear+.8<y<rear+7 and min(v.z for v in p)<.4:
            key=round(y,2)
            xs=[v.x+w/2 for v in p]
            lo,hi,zt=planes.get(key,(99,-99,0))
            planes[key]=(min(lo,*xs),max(hi,*xs),max(zt,top))
    boxes=[(y,lo,hi,zt) for y,(lo,hi,zt) in planes.items() if hi-lo>1.6 and zt>2.3]
    return rear,boxes

def back_door(h,a,y,lo,hi):
    """A plain back door, frame and step on a one-storey rear box (R18d: these read as blank boxes)."""
    w,d=[v*8 for v in a["lot"]]
    m=lambda x:(x-w/2,y-d/2-nb.YSHIFT)
    ff=nb.Face(m(hi),m(lo))
    if ff.out.y<0:
        ff=nb.Face(m(lo),m(hi))
    c=ff.length/2
    blk=g.block
    # pieces stop a few mm short of each other so no two faces share a plane (the validator's coplanar check)
    blk(h.body,ff,c-.465,c+.465,.09,2.135,.004,.046,"Green")
    for s in (-1,1):
        blk(h.body,ff,c+s*.47-(.12 if s<0 else 0),c+s*.47+(.12 if s>0 else 0),.09,2.135,.004,.10,"Dressed")
    blk(h.body,ff,c-.61,c+.61,2.14,2.27,.004,.112,"Dressed")
    blk(h.body,ff,c-.72,c+.72,.02,.085,.004,.44,"Dressed")

def rear_clutter(a,points):
    zone=a["zone_key"]
    w,d=[v*8 for v in a["lot"]]
    coords=[(v.x+w/2,v.y+d/2,v.z) for v in points]
    if zone=="Z4":
        rear=a["walls"][3]
        return all(p[1]>rear+.31 for p in coords) and max(p.z for p in points)>.15
    if zone in {"Z1A","Z1B"} and a.get("outbuilding"):
        # Strip the detached garage/outbuilding wholly (the author 2026-11-11). The source geometry is not always
        # mirrored the way the record says, so test both the recorded and the as-baked boxes, by piece centre,
        # and run each box to the back of the lot so the garage apron goes too.
        boxes=[a["outbuilding"],(a.get("as_baked_layout") or {}).get("outbuilding")]
        cx=sum(p[0] for p in coords)/len(coords)
        cy=sum(p[1] for p in coords)/len(coords)
        return any(l-.9<cx<r+.9 and f-.9<cy<d+.5 for l,r,f,b in (q for q in boxes if q))
    return False

def midpoint(points):
    return sum(points[1:],points[0].copy())/len(points)

def window_bar(h,p,n,raw,style=0):
    if abs(n.z)>.10:
        return
    t=Vector((0,0,1)).cross(n).normalized()
    m=midpoint(p)
    xx=[(v-m).dot(t) for v in p]
    zz=[v.z for v in p]
    l,r=min(xx),max(xx)
    bottom,top=min(zz),max(zz)
    if r-l<.67 or top-bottom<.76:
        return
    # Use the solid pane interior to size joinery. The curved crown stays clear.
    hull=[((v-m).dot(t),v.z) for v in p]
    def limits(z):
        xs=[]
        for (x,a),(u,b) in zip(hull,hull[1:]+hull[:1]):
            if min(a,b)<z<max(a,b):
                xs.append(x+(u-x)*(z-a)/(b-a))
        return (min(xs),max(xs)) if len(xs)>=2 else (l,r)
    x=m-t*.5*(r-l)
    y=m+t*.5*(r-l)
    ff=nb.Face((x.x,x.y),(y.x,y.y))
    if ff.out.dot(n)<0:
        ff=nb.Face((y.x,y.y),(x.x,x.y))
    height=top-bottom
    # Keep the bar further forward than the pane but behind the façade ornament.
    d=.084 if style==0 else .064
    detail.quad_bar(h.body,ff,(r-l)/2-.016,(r-l)/2+.016,bottom+.065,top-.14,d,"Iron")
    cuts=(.48,.72) if h.lod==0 and height>1.6 else (.49,)
    for fraction in cuts:
        z=bottom+height*fraction
        lo,hi=limits(z)
        detail.quad_bar(h.body,ff,(r-l)/2+lo+.058,(r-l)/2+hi-.058,z-.016,z+.016,d+.011,"Iron")

def relief_for_wall(h,a,wall_faces,panes,raw,grade):
    w,d=[v*8 for v in a["lot"]]
    terrain=a.get("walls")
    spec=a.get("spec",{})
    if not terrain:
        terrain=spec.get("walls")
    e=a.get("cornice_m") or spec.get("eave")
    if not terrain and a.get("blocks"):
        terrain=a["blocks"][0]["spec"]["walls"]
        e=a["blocks"][0]["spec"]["eave"]
    if not terrain or not e:
        return
    l,r,f,b=terrain
    mirrored=a.get("mirror_geometry",False)
    if mirrored:
        l,r=w-r,w-l
    datums=a.get("floor_datums_m") or spec.get("datums") or [0,3.7,7.4,11.1]
    if a.get("blocks"):
        datums=a["blocks"][0]["spec"].get("datums",datums)
    datums=sorted({0.,float(e),*(float(z) for z in datums if 1.6<z<e-1.0)})
    if len(datums)==2:
        datums.insert(1,e*.51)
    corners=[(nb.X(l),nb.Y(f)),(nb.X(r),nb.Y(f)),(nb.X(r),nb.Y(b)),(nb.X(l),nb.Y(b))]
    for side,(x,y) in enumerate(zip(corners,corners[1:]+corners[:1])):
        if a.get("compact",0)>=4 and side!=0:
            continue
        ff=nb.Face(x,y)
        if ff.length<2.3:
            continue
        plane=ff.point(0,0,0)
        matches=[(p,n) for p,n in wall_faces if n.dot(ff.out)>.99 and abs((midpoint(p)-plane).dot(ff.out))<.012]
        if not matches:
            continue
        span=[(p-plane).dot(ff.tangent) for pts,_ in matches for p in pts]
        left=max(.40,min(span)+.12)
        right=min(ff.length-.40,max(span)-.12)
        if right-left<1.0:
            continue
        for i,(z,t) in enumerate(zip(datums,datums[1:])):
            if t-z<1.65:
                continue
            row=[]
            for p,n in panes:
                m=midpoint(p)
                dist=(m-plane).dot(ff.out)
                if n.dot(ff.out)<.99 or not -.89<dist<.84 or not z<m.z<t:
                    continue
                q=[(v-plane).dot(ff.tangent) for v in p]
                row.append(((min(q)+max(q))*.5,max(q)-min(q),min(v.z for v in p),max(v.z for v in p)))
            def has_wall(u,z):
                point=ff.point(u,z,.60)
                point.y+=nb.YSHIFT
                loc,n,idx,length=raw.ray_cast(point,-ff.out,1.2)
                return loc is not None and n.dot(ff.out)>.96 and abs(length-.60)<.019
            cap=t-.41 if i<len(datums)-2 else t-.42
            band=.16 if i<len(datums)-2 else .22
            for lo,hi in detail.gaps(row,left,right,cap-band,cap,.18):
                if hi-lo>.52 and all(has_wall(lo+(hi-lo)*u,cap-band*.50) for u in (.08,.5,.92)):
                    detail.bevel(h.body,ff,lo,hi,cap-band,cap,.013,.164,"Dressed",shadow=True)
            if i==0:
                for lo,hi in detail.gaps(row,left,right,.18,.52,.28):
                    if hi-lo>.54 and all(has_wall(lo+(hi-lo)*u,.34) for u in (.10,.5,.9)):
                        detail.bevel(h.body,ff,lo,hi,.19,.44,.014,.14,"StoneBase")
            if grade or side in (0,2):
                for lo,hi in detail.gaps(row,left,right,z+.82,t-.68,.22):
                    if hi-lo>.51:
                        centers=[(lo+hi)/2] if hi-lo<3.5 or not grade else [lo+(hi-lo)*q for q in (.23,.75)]
                        for c in centers:
                            if all(has_wall(c,k) for k in (z+.93,(z+t)*.5,t-.79)):
                                detail.bevel(h.body,ff,c-.105,c+.105,z+.85,t-.66,.010,.091,"Dressed")
                                if grade>=.5:
                                    for zz,zt in detail.divide(z+.87,t-.70,.75 if grade<1 else .57 if grade<2 else .36):
                                        if has_wall(c,(zz+zt)/2):
                                            detail.bevel(h.body,ff,c-.148,c+.148,zz+.021,zt-.025,.096,.144,"Dressed")
            if grade>1:
                for lo,hi in detail.gaps(row,left,right,z+.57,z+.79,.25):
                    for u,v in detail.divide(lo,hi,.61 if grade<2 else .46):
                        if v-u>.19 and abs(math.sin(u*493.8+z*173.1+side*231.7))<min(1,(grade-1)*.65) and has_wall((u+v)/2,z+.68):
                            detail.bevel(h.body,ff,u+.018,v-.018,z+.585,z+.754,.027,.073,"Dressed")

def build(a,lod):
    core.setup(a,lod,0)
    body=load(a,lod)
    panes=load(a,lod,True)
    h=nb.House(lod)
    h.name=a["name"]
    h.r12=True
    compact=a.get("compact",0)
    tag=h.body.lodkey
    source=source_layout(a["source_batch"],tag)
    target=nb.LAYOUT["lods"][tag]
    raw_vertices=[]
    raw_faces=[]
    raw_tiles=[]
    walls=[]
    estate=a["zone_key"]=="Z1B"
    if estate:
        rear_y,rear_boxes=rear_layout(a,body)
        w0,d0=[v*8 for v in a["lot"]]
    for p,uv,n in body:
        key=tile(uv,source)
        if key in IGNORED or rear_clutter(a,p):
            continue
        # R18d: ground paving left behind the house (old patio and garage-apron strips) leads to no door.
        if estate and max(v.z for v in p)<.26 and sum(v.y for v in p)/len(p)+d0/2>rear_y+.30:
            continue
        flip=key.startswith("Sign_") and reads_backwards(p,uv,n)
        if key.startswith("Sign_"):
            dest="Sign_"+SIGN_SLOTS[a["sign_index"]]
        elif key.startswith("Address_"):
            dest="Dressed"
        else:
            dest=MATERIALS.get(key,key)
        if dest not in target:
            dest="CourtGlass" if "Glass" in dest else "YardSetts" if abs(n.z)>.75 and max(v.z for v in p)<.2 else "Dressed"
        points=local(p)
        if lod==0 and dest in MASONRY:
            cell=target[dest]
            original=cell["metres"]
            if compact>=3:
                cell["metres"]=[2.11,2.11]
            try:
                h.body.polygon(points,n,dest)
            finally:
                cell["metres"]=original
        else:
            transfer(h.body,points,uv,source[key],target[dest],flip)
        raw_faces.append(tuple(range(len(raw_vertices),len(raw_vertices)+len(p))))
        raw_vertices.extend(p)
        raw_tiles.append(dest)
        if abs(n.z)<.02 and dest in MASONRY|{"Render","RenderRose","RenderOchre","Ashlar","Dressed"}:
            walls.append((points,n))
    if estate and lod<2:   # the far LOD has no triangles to spare and the door is invisible there
        for y,lo,hi,_ in rear_boxes:
            back_door(h,a,y,lo,hi)
    raw=BVHTree.FromPolygons(raw_vertices,raw_faces)
    good=[]
    for p,uv,n in panes:
        if rear_clutter(a,p):
            continue
        # Avoid treating cut glass hidden by the old structure as a night room.
        center=midpoint(p)
        tangent=Vector((0,0,1)).cross(n).normalized()
        span=max(abs((v-center).dot(tangent)) for v in p)
        blocked=0
        for shift in (-.65,-.32,.27,.62):
            origin=center+tangent*(shift*span)+n*.019
            hit,normal,j,dist=raw.ray_cast(origin,n,.63)
            if hit is not None and normal.dot(n)>.94 and raw_tiles[j] not in {"Iron","TinGreen","Green","Cream","Dressed","Mustard","GreyBlue","CourtGlass"}:
                blocked+=1
        if blocked>=3 and lod<2:
            continue
        points=local(p)
        if lod<2 and abs(n.z)<.03 and max(v.z for v in p)-min(v.z for v in p)>.64 and (not compact or n.y<-.65):
            sample=center+tangent*.21*span-n*.013
            hit,_,_,dist=raw.ray_cast(sample,-n,.211)
            if hit is None:
                depth=.190
                inset=[v-n*depth for v in points]
                for j,(x,y) in enumerate(zip(points,points[1:]+points[:1])):
                    k=(j+1)%len(points)
                    inside=n.cross(y-x)
                    if inside.length>.003:
                        h.body.polygon([x,y,inset[k],inset[j]],inside,"RevealStone")
                points=inset
        good.append((points,uv,n))
    assert good,(a["name"],lod,"no window geometry")
    candidates=list(range(0,len(good),3 if a["zone_key"]!="Z1B" else 6))
    if lod==2:
        candidates=candidates[:max(1,len(good)//3)]
    elif a["zone_key"]=="Z1B":
        candidates=candidates[:5]
    for i,(p,uv,n) in enumerate(good):
        if (lod==0 and (not compact or n.y<-.35) and (compact<2 or i%(2 if compact<5 else 3)==0)) or (lod==1 and not compact and i%2==0):
            window_bar(h,p,n,raw)
    if lod==0 and compact<5:
        relief_for_wall(h,a,walls,[(p,n) for p,_,n in good],raw,a.get("detail_grade",0))
    if lod<2:
        vertices=[Vector(v) for v in h.body.vertices]
        tree=BVHTree.FromPolygons(vertices,h.body.faces)
        allowed={"Iron","TinGreen","Black","Green","Mustard","TinOxide"}
        def clear(p,n):
            mid=midpoint(p)
            samples=[mid]+[mid.lerp(q,.54) for q in p]+[mid.lerp((x+y)/2,.71) for x,y in zip(p,p[1:]+p[:1])]
            blocked=0
            for point in samples:
                hit,norm,index,dist=tree.ray_cast(point+n*.012,n,1.188)
                if hit is None or norm.dot(n)<.94 or tile(h.body.uvs[index],target) in allowed:
                    continue
                outside=tree.ray_cast(point+n*180,-n,180)[0]
                if outside is not None and (outside-hit).length<=.018:
                    blocked+=1
            return blocked<2
        candidates=[j for j in candidates if clear(good[j][0],good[j][2])]
        if not candidates:
            candidates=[j for j,(p,uv,n) in enumerate(good) if clear(p,n)][:1]
    for i,(p,uv,n) in enumerate(good):
        if i in candidates:
            h.windows._add(p,uv)
        elif lod<2:
            h.body.polygon([q+n*.006 for q in p],n,"GreyBlue")
            if not compact or a["zone_key"]=="Z1B":
                h.body.polygon([q+n*.002 for q in p],-n,"GreyBlue")
    return h
