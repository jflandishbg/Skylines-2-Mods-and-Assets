"""Roof surfaces, façades, entrances and metalwork for the Round 11 houses."""
import math
from mathutils import Vector
import round5_geometry as g
from tenement_details import beam
import detail_mesh as detail

core,kit,nb=g.core,g.kit,g.nb
face,flat,rectangle,xyz,box,block=g.face,g.flat,g.rectangle,g.xyz,g.box,g.block
UP,DOWN=g.UP,g.DOWN
BRICK,STONE,IRON,WOOD="Brick085","Dressed","TinGreen","BrownBrick"

def edges(rect):
    p=rectangle(*rect)
    return [face(a,b) for a,b in zip(p,p[1:]+p[:1])]

def ground(h,a):
    # Walk surfaces remain below the thresholds and avoid covering the garden.
    xs=sorted({t for v in a["front_walks"] for t in v["bounds_lot_m"][:2]})
    ys=sorted({t for v in a["front_walks"] for t in v["bounds_lot_m"][2:]})
    for i,(l,r) in enumerate(zip(xs,xs[1:])):
        for j,(f,b) in enumerate(zip(ys,ys[1:])):
            if any(x<=(l+r)/2<=u and y<=(f+b)/2<=v
                   for row in a["front_walks"] for x,u,y,v in [row["bounds_lot_m"]]):
                flat(h.body,rectangle(l,r,f,b),.027,UP,"YardSetts")

def roof(h,p,z,rise,mat,ratio=.5,open_front=False):
    l,r,f,b=p
    x=l+(r-l)*ratio
    m=h.body
    for u in (l,r):
        m.polygon([xyz(u,f,z),xyz(x,f,z+rise),xyz(x,b,z+rise),xyz(u,b,z)],UP,mat)
    for y,s in ((f,-1),(b,1)):
        if y==f and open_front:continue
        m.polygon([xyz(l,y,z),xyz(r,y,z),xyz(x,y,z+rise)],(0,s,0),BRICK)
    return x

def hip(h,p,z,rise,mat):
    l,r,f,b=p
    margin=min((r-l)*.47,(b-f)*.44)
    g.caps(h,rectangle(l,r,f,b),z,((0,0),(margin,rise)),mat)

def flat_roof(h,p,z,depth=.20):
    l,r,f,b=p
    box(h.body,l-.10,r+.10,f-.10,b+.10,z-.016,z+depth,"TinFlat")

def wood_beam(h,f,p,q,width=.112,d=.057,mat=WOOD):
    beam(h,f.point(*p,d),f.point(*q,d),width,mat)

def plank(h,f,u0,u1,z0,z1,d=.06,mat=WOOD):
    block(h.body,f,u0,u1,z0,z1,.012,d,mat)

def plaque(h,a,f,z,x=None):
    u=f.length*.55 if x is None else x
    w=min(f.length*.47,2.70)
    block(h.body,f,u-w/2-.045,u+w/2+.045,z-.146,z+.146,.014,.107,STONE)
    g.plate(h,f,u,z,w,.224,"Sign_"+a["design"],.116)

def portal_slots(h,a,f,rect,z,e):
    l,r,y,_=rect
    return [(x-l,ent["width_m"],b,min(e-.22,b+2.22),.09,True,False)
            for ent in a["entrances"].values() for x,y0,b in [ent["position_lot_m"]]
            if abs(y-y0)<.004 and l+.55<x<r-.55 and z<b<e-.66]

def wall(h,a,rect,base,e,floors=2,omit=(),trim=True,sign=False,staff_stairs=True,front_studio=False):
    m=h.body
    flat(m,rectangle(*rect),base,DOWN,"StoneBase")
    zs=[base]+[base+(e-base)*i/floors for i in range(1,floors+1)]
    if a["style"]=="spiral" and floors==2:
        zs=[base,3.07,e]
    if a["style"]=="raised":
        zs=[base,1.43,4.37,e]
    for k,f in enumerate(edges(rect)):
        for i,(z,t) in enumerate(zip(zs,zs[1:])):
            slots=portal_slots(h,a,f,rect,z,t) if k==0 else []
            if staff_stairs:
                for u,w,b,*_ in slots:
                    if b<.48:
                        g.stair(h,f,u,w,b)
            cnt=3 if f.length>8.7 else 2
            if k in (1,3):
                cnt=3 if f.length>11.5 else 2
            if h.lod==1:cnt=min(cnt,2)
            if h.lod==2:cnt=1 if k in (0,2) else 0
            if k in omit:cnt=0
            for j in range(cnt):
                u=f.length*(j+.5)/cnt
                w=min(f.length/cnt*.53,1.36)
                b=z+.80 if i==0 else z+.64
                hgt=t-.52
                if a["style"]=="raised" and i==0:
                    b,hgt=.27,1.12
                if front_studio and k==0 and i==floors-1:
                    u,w=f.length*.646,f.length*.39
                    if j>0:continue
                if any(abs(u-p[0])<(w+p[1])/2+.35 for p in slots):
                    continue
                if t-b>.66 and hgt>b+.25:
                    slots.append((u,w,b,hgt,.12,False,False))
            h.quiet_panes={slot[0] for j,slot in enumerate(sorted(slots))
                           if not slot[5] and (k not in (0,2) or j!=0 or i!=0 or front_studio and k==0)}
            h.slim_shaft=h.lod==1 or a["style"]=="jetty"
            h.window_recess=.365
            h.quiet_material="GreyBlue"
            h.finish_cornice=i==len(zs)-2
            h.skip_relief=k in omit
            g.row(h,f,z,t,BRICK,slots)
            h.skip_relief=False
            h.finish_cornice=True
            h.quiet_material="GreyBlue"
            h.quiet_panes=()
            h.slim_shaft=False
            if trim and h.lod<2 and t-z>2.1:
                plank(h,f,.085,f.length-.085,t-.23,t-.115,.105,STONE)
        if sign and k==0:
            plaque(h,a,f,zs[1]-.19)
    return edges(rect)[0]

def pavers(h,p,z=.029):
    flat(h.body,rectangle(*p),z,UP,"YardSetts")

def leaf(h,x,y,z,r,mat="RoofGreen"):
    m=h.body
    p=[xyz(x+r*math.cos(j*math.tau/5),y+r*math.sin(j*math.tau/5),z+.035) for j in range(5)]
    q=xyz(x+.032,y-.048,z+r*.82)
    m.polygon(p,DOWN,mat)
    for i,v in enumerate(p):
        m.polygon([v,p[(i+1)%5],q],UP,mat)

def curve_step(h,quad,low,high,mat=IRON):
    m=h.body
    flat(m,quad,low,DOWN,mat)
    flat(m,quad,high,UP,mat)
    for f in edges_polygon(quad):
        f.quad(m,0,f.length,low,high,0,mat)

def edges_polygon(p):
    return [face(a,b) for a,b in zip(p,p[1:]+p[:1])]

def round_wall(h,x,y,r,z0,z1,mat,n=12,inner=0):
    m=h.body
    circle=lambda rr:[(x+rr*math.cos(i*math.tau/n),y+rr*math.sin(i*math.tau/n)) for i in range(n)]
    outside=circle(r)
    for f in edges_polygon(outside):
        f.quad(m,0,f.length,z0,z1,0,mat)
    if not inner:
        flat(m,outside,z0,DOWN,mat)
        flat(m,outside,z1,UP,mat)
        return
    inside=circle(inner)
    for p,q in zip(inside,inside[1:]+inside[:1]):
        f=face(q,p)
        f.quad(m,0,f.length,z0,z1,0,mat)
    for i,p in enumerate(outside):
        j=(i+1)%n
        q=[p,outside[j],inside[j],inside[i]]
        flat(m,q,z0,DOWN,mat)
        flat(m,q,z1,UP,mat)

def thin_glass(m,points,direction):
    offset=Vector(direction).normalized()*.0025
    m.polygon([Vector(v)+offset for v in points],direction,"GardenGlass")
    m.polygon([Vector(v)-offset for v in points],-offset,"GardenGlass")
