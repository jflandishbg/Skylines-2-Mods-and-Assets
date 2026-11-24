"""Production meshes for the two R4-0 civic buildings."""
import math
from mathutils import Vector

import bake_round2 as kit
from civic_specs import FIRE_AXIS, FIRE_ARCH_Y, FIRE_BACK_Y, FIRE_BAY, FIRE_DOOR_Y, PORTALS

core,nb=kit.core,kit.nb
face,block,relief=kit.face,kit.block,kit.relief
BRICK,STONE,SLATE,IRON="Brick085","Dressed","SlateDark","Iron"
PAVING="Paving"
UP=Vector((0,0,1))

def xyz(x,y,z):
    return (nb.X(x),nb.Y(y),z)

def box(m,x0,x1,y0,y1,z0,z1,mat,top=None):
    m.box(nb.X(x0),nb.X(x1),nb.Y(y0),nb.Y(y1),z0,z1,mat,top)

def rectangle(x0,x1,y0,y1):
    return [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]

def flat(m,plan,z,up,mat):
    m.polygon([xyz(x,y,z) for x,y in plan],up,mat)

def paving(h,rects):
    """One 3 cm slab union. Internal cell boundaries have no vertical faces."""
    m=h.body
    xs=sorted({p for rect in rects for p in rect[:2]})
    ys=sorted({p for rect in rects for p in rect[2:]})
    grid={(i,j) for i,(x0,x1) in enumerate(zip(xs,xs[1:]))
          for j,(y0,y1) in enumerate(zip(ys,ys[1:]))
          if any(l<=(x0+x1)/2<=r and f<=(y0+y1)/2<=b for l,r,f,b in rects)}
    for i,j in sorted(grid):
        plan=rectangle(xs[i],xs[i+1],ys[j],ys[j+1])
        flat(m,plan,.030,UP,PAVING)
        flat(m,plan,.004,-UP,PAVING)
        for k,cell in enumerate(((i,j-1),(i+1,j),(i,j+1),(i-1,j))):
            if cell not in grid:
                f=face(plan[k],plan[(k+1)%4])
                f.quad(m,0,f.length,.004,.030,0,PAVING)

def uv_plate(m,f,u,z,width,height,key):
    u0,v0,u1,v1=nb.LAYOUT["lods"][m.lodkey][key]["uv"]
    p=f.point
    x0,x1=u-width/2,u+width/2
    z0,z1=z-height/2,z+height/2
    m._add([p(x0,z0,.201),p(x1,z0,.201),p(x1,z1,.201),p(x0,z1,.201)],
           [(u0,v0),(u1,v0),(u1,v1),(u0,v1)])

def solid_window(h,f,u,w,b,t,arched=False,stone=STONE,door=False,quiet=False):
    """Room-grid glazing and a closed limestone surround on a continuous wall."""
    lod=h.lod
    m=h.body
    left,right=u-w/2,u+w/2
    spring=t-(min(.59,w*.34) if arched else 0)
    rim=.18 if w>1.6 else .12
    head=kit.arch_points(u,w/2,spring,t-spring,8 if lod==0 else 5) if arched else [(left,t),(right,t)]
    bglass=b+.33 if door else b
    poly=[(left,bglass),(right,bglass)]+head[::-1]
    h.windows.polygon([f.point(x,z,.064) for x,z in poly],f.out,"Cream",room=nb.ROOMS[round(u*17+b*21)%len(nb.ROOMS)])
    if lod==2:
        return
    if door:
        block(m,f,left,right,b,bglass,.022,.092,"Green")
    if lod==1 or quiet:
        for x0,x1 in ((left-rim,left-.006),(right+.006,right+rim)):
            f.quad(m,x0,x1,b+.019,spring-.021,.115,stone)
        if arched:
            outer=kit.arch_points(u,w/2+rim,spring,t-spring+rim,len(head)-1)
            for i in range(len(head)-1):
                q=[head[i],head[i+1],outer[i+1],outer[i]]
                m.polygon([f.point(x,z,.136) for x,z in q],f.out,stone)
        else:
            f.quad(m,left-rim,right+rim,t+.020,t+.13,.115,stone)
        f.quad(m,left-rim,right+rim,b-.118,b-.048,.153,stone)
        f.quad(m,u-.028,u+.028,bglass+.024,t-.042,.083,IRON)
        return
    if arched:
        outer=kit.arch_points(u,w/2+rim,spring,t-spring+rim,len(head)-1)
        for i in range(len(head)-1):
            quad=[head[i],head[i+1],outer[i+1],outer[i]]
            if lod==0:
                relief(m,f,quad,.012,.154,stone)
            else:
                m.polygon([f.point(x,z,.145) for x,z in quad],f.out,stone)
        if lod==0:
            block(m,f,u-.13,u+.13,t+rim+.023,t+rim+.23,.016,.19,"Cream")
    else:
        block(m,f,left-rim,right+rim,t+.017,t+rim+.029,.015,.131,stone)
    for x0,x1 in ((left-rim,left-.006),(right+.006,right+rim)):
        block(m,f,x0,x1,b+.018,spring-.018,.008,.137,stone)
    if not door:
        block(m,f,left-rim-.043,right+rim+.043,b-.133,b-.031,.011,.203,"Cream")
    f.quad(m,u-.027,u+.027,bglass+.019,t-.032,.083,IRON)
    f.quad(m,left+.012,right-.012,bglass+(t-bglass)*.67,bglass+(t-bglass)*.67+.042,.086,IRON)

def facade(h,f,z0,z1,floors,bays,ornament):
    if not bays:return
    lod=h.lod
    height=(z1-z0)/floors
    count=max(1,bays//2) if lod==2 else bays
    for i in range(floors):
        if lod==2 and i not in (0,floors-1):continue
        low=z0+i*height
        for j in range(count):
            u=f.length*(j+.5)/count
            w=min(2.34,f.length/count-.92)
            arch=ornament and (i==0 or i==floors-1) and lod<2
            solid_window(h,f,u,w,low+height*.19,low+height*.77,arched=arch,quiet=not arch)
        if ornament and i and lod<2:
            block(h.body,f,.14,f.length-.14,low-.060,low+.108,.011,.168,"Cream")
    if not ornament or lod==2:return
    for i in range(bays+1):
        u=max(.48,min(f.length-.48,f.length*i/bays))
        block(h.body,f,u-.153,u+.153,z0+.49,z1-.71,.018,.135,STONE)
        if lod==0:
            block(h.body,f,u-.235,u+.235,z1-.68,z1-.46,.033,.211,"Cream")

def volume(h,plan,z0,z1,material=BRICK,floors=0,bays=(0,0,0,0),ornament=True,cap=True):
    m=h.body
    flat(m,plan,z0,-UP,"StoneBase")
    if cap:flat(m,plan,z1,UP,"TinFlat")
    for j,(p,q) in enumerate(zip(plan,plan[1:]+plan[:1])):
        f=face(p,q)
        f.quad(m,0,f.length,z0,z1,0,material)
        if floors:
            facade(h,f,z0,z1,floors,bays[j] if j!=2 else max(1,bays[j]//2) if bays[j] else 0,ornament and j!=2)
        if ornament:
            block(m,f,.065,f.length-.065,z0+.075,z0+.39,.014,.188,"StoneBase")
            block(m,f,.078,f.length-.078,z1-.37,z1-.096,.016,.221,STONE)
            if h.lod==0:
                n=max(2,round(f.length/1.12))
                for k in range(n):
                    u=f.length*(k+.5)/n
                    block(m,f,u-.084,u+.084,z1-.59,z1-.385,.021,.158,"Cream")

def profile_roof(h,rect,z,profile,mat=SLATE,top="TinFlat"):
    l,r,f,b=rect
    previous=None
    for inset,height in profile:
        plan=rectangle(l+inset,r-inset,f+inset,b-inset)
        ring=[xyz(x,y,z+height) for x,y in plan]
        if previous is None:
            h.body.polygon(ring,nb.DOWN,STONE)
        else:
            kit.ring_surfaces(h.body,previous,ring,mat)
        previous=ring
    h.body.polygon(previous,UP,top)

def mansard(h,rect,e,rise,hood=False):
    l,r,f,b=rect
    thin=min(r-l,b-f)
    profile=[(-.24,.019),(thin*.16,rise*.75),(thin*(.38 if hood else .25),rise)]
    profile_roof(h,rect,e,profile)
    if h.lod==2 or hood:
        return
    f0=face((l+.20,f-.17),(r-.20,f-.17))
    n=max(1,round((r-l)/9.4))
    for i in range(n):
        u=f0.length*(i+.5)/n
        kit.dormer(h,f0,u,e,oval=(h.lod==0 and n>=3 and i%2==1),high=min(.73,rise*.11))

def portico_entry(h,x,y,z,w=4.6,t=6.3):
    f=face((x-w/2-1.16,y),(x+w/2+1.16,y))
    solid_window(h,f,f.length/2,w,z,z+t,True,door=True)
    if h.lod==2:return
    for u in (.72,f.length-.72):
        block(h.body,f,u-.21,u+.21,z+.05,z+t-.36,.022,.51,STONE)
        block(h.body,f,u-.29,u+.29,z+t-.34,z+t-.08,.046,.62,"Cream")
    block(h.body,f,.27,f.length-.27,z+t+.37,z+t+.65,.021,.53,STONE)

def fire_portal(h):
    m=h.body
    f,b=FIRE_ARCH_Y
    left,right=22.8,73.2
    attic_base=18.30
    fronts=[face((left,f),(right,f)),face((right,b),(left,b))]
    n=28 if h.lod==0 else 16 if h.lod==1 else 10
    last=left
    for u,w,spring,rise in PORTALS:
        lo,hi=u-w/2,u+w/2
        pier=(last,lo)
        for ff,direction in zip(fronts,(1,-1)):
            def xx(x):return x-left if direction==1 else right-x
            s,t=sorted(map(xx,pier))
            ff.quad(m,s,t,0,attic_base,0,STONE)
        flat(m,rectangle(last,lo,f,b),0,-UP,STONE)
        arc=[(u-w*.5*math.cos(i*math.pi/n),spring+rise*math.sin(i*math.pi/n)) for i in range(n+1)]
        for j,((x,z),(v,t)) in enumerate(zip(arc,arc[1:])):
            for y,norm in [(f,(0,-1,0)),(b,(0,1,0))]:
                m.polygon([xyz(x,y,z),xyz(v,y,t),xyz(v,y,attic_base),xyz(x,y,attic_base)],norm,STONE)
            norm=(math.cos((j+.5)*math.pi/n),0,-math.sin((j+.5)*math.pi/n))
            m.polygon([xyz(x,f,z),xyz(v,f,t),xyz(v,b,t),xyz(x,b,z)],norm,"Ashlar")
            if h.lod<2:
                arch_stone(h,u,w,spring,rise,f,j,n)
        for x,norm in ((lo,(1,0,0)),(hi,(-1,0,0))):
            m.polygon([xyz(x,f,0),xyz(x,b,0),xyz(x,b,spring),xyz(x,f,spring)],norm,STONE)
        if u==48 and h.lod<2:
            coffers(h,arc,f,b,n)
        last=hi
    for ff,direction in zip(fronts,(1,-1)):
        u,v=(last-left,right-left) if direction==1 else (0,right-last)
        ff.quad(m,u,v,0,attic_base,0,STONE)
    flat(m,rectangle(last,right,f,b),0,-UP,STONE)
    for x,norm in ((left,(-1,0,0)),(right,(1,0,0))):
        m.polygon([xyz(x,f,0),xyz(x,b,0),xyz(x,b,attic_base),xyz(x,f,attic_base)],norm,STONE)
    flat(m,rectangle(left,right,f,b),attic_base,UP,STONE)
    # Lower moulding, attic block and its stone cap.
    box(m,22.32,73.68,13.52,32.48,18.281,19.42,"Cream")
    box(m,22.63,73.37,13.78,32.22,19.397,23.73,STONE)
    box(m,21.8,74.2,13.12,32.88,23.708,25,STONE,"Cream")
    fsign=face((22.63,13.78),(73.37,13.78))
    u=fsign.length/2
    block(m,fsign,u-22.60,u+22.60,20.30,22.91,.014,.180,"Ashlar")
    uv_plate(m,fsign,u,21.62,44.28,2.16,"CivicName")
    if h.lod<2:
        for ff in fronts:
            for x in (25.0,38.7,57.3,71.0):
                centre=x-left if ff is fronts[0] else right-x
                block(m,ff,centre-1.19,centre+1.19,2.16,8.24,.019,.119,STONE)
                block(m,ff,centre-1.49,centre+1.49,.19,1.44,.031,.243,"StoneBase")
                sculpture(h,ff,centre,11.0)
        if h.lod==0:
            for x in range(1,49):
                block(m,fsign,x-.072,x+.072,23.42,23.64,.013,.091,"Cream")

def arch_stone(h,u,w,spring,rise,y,j,n):
    a=j*math.pi/n+.006;b=(j+1)*math.pi/n-.006
    p=lambda a,r:xyz(u-(w/2+r)*math.cos(a),y-.093,spring+(rise+r)*math.sin(a))
    q=[p(a,.028),p(b,.028),p(b,.57 if j!=n//2 else .84),p(a,.57 if j!=n//2 else .84)]
    h.body.polygon(q,(0,-1,0),"Cream" if j%2==0 else "Dressed")
    # Return the face into its stone backing.
    centre=sum((Vector(v) for v in q),Vector((0,0,0)))/len(q)
    for x,v in zip(q,q[1:]+q[:1]):
        desired=(Vector(x)+Vector(v))*.5-centre
        h.body.polygon([x,v,(v[0],v[1]+.109,v[2]),(x[0],x[1]+.109,x[2])],desired,STONE)

def coffers(h,arc,f,b,n):
    m=h.body
    count=6 if h.lod==0 else 4
    for i,((x,z),(u,t)) in enumerate(zip(arc,arc[1:])):
        if i<2 or i>=n-2:continue
        norm=Vector((math.cos((i+.5)*math.pi/n),0,-math.sin((i+.5)*math.pi/n)))
        def p(s,y,d):
            return Vector(xyz(x+(u-x)*s,y,z+(t-z)*s))+norm*d
        for j in range(count):
            y=f+.76+(b-f-1.52)*(j+.5)/count
            span=(b-f-1.52)/count*.35
            a,b0=y-span,y+span
            ring=[p(.13,a,.048),p(.87,a,.048),p(.87,b0,.048),p(.13,b0,.048)]
            inner=[p(.22,a+.15,.023),p(.78,a+.15,.023),p(.78,b0-.15,.023),p(.22,b0-.15,.023)]
            m.polygon(inner,norm,"StoneBase")
            foot=[p(.13,a,-.012),p(.87,a,-.012),p(.87,b0,-.012),p(.13,b0,-.012)]
            axis=Vector((u-x,0,t-z)).normalized()
            outside=(Vector((0,-1,0)),axis,Vector((0,1,0)),-axis)
            for k in range(4):
                q=(k+1)%4
                m.polygon([ring[k],ring[q],inner[q],inner[k]],norm,"Cream")
                m.polygon([ring[k],ring[q],foot[q],foot[k]],outside[k],STONE)

def sculpture(h,f,u,z):
    m=h.body
    block(m,f,u-1.38,u+1.38,z-2.37,z+2.26,.016,.151,"Ashlar")
    block(m,f,u-1.52,u+1.52,z+2.31,z+2.53,.027,.232,"Cream")
    block(m,f,u-1.52,u+1.52,z-2.62,z-2.42,.026,.230,"Cream")
    shield=[(u-.61,z+.29),(u,z+.59),(u+.61,z+.29),(u+.51,z-.52),(u,z-.98),(u-.51,z-.52)]
    relief(m,f,shield,.158,.268,STONE)
    if h.lod==0:
        for hand in (-1,1):
            for i in range(5):
                x=u+hand*(1.03-.08*i)
                y=z-.67+i*.36
                q=[(x-.10,y-.12),(x+.09,y-.12),(x+.14,y+.09),(x-.05,y+.16)]
                relief(m,f,q,.159,.212,"Cream")
        block(m,f,u-.24,u+.24,z+.75,z+1.22,.163,.278,"Cream")

def apparatus_house(h):
    m=h.body
    left,right,front,back=20.5,75.5,FIRE_DOOR_Y,64.9
    e=13.8
    area=rectangle(left,right,front,back)
    flat(m,area,0,-UP,"StoneBase")
    flat(m,area,e,UP,"TinFlat")
    f=face((left,front),(right,front))
    w,t=FIRE_BAY
    cursor=0
    for x in FIRE_AXIS:
        u=x-left
        lo,hi=u-w/2,u+w/2
        f.quad(m,cursor,lo,0,t,0,BRICK)
        cursor=hi
        side_y=FIRE_BACK_Y
        for xx,norm in ((x-w/2,(1,0,0)),(x+w/2,(-1,0,0))):
            m.polygon([xyz(xx,front,.030),xyz(xx,side_y,.030),xyz(xx,side_y,t),xyz(xx,front,t)],norm,"Black")
        m.polygon([xyz(x-w/2,front,t),xyz(x+w/2,front,t),xyz(x+w/2,side_y,t),xyz(x-w/2,side_y,t)],nb.DOWN,"Black")
        m.polygon([xyz(x-w/2,side_y,.030),xyz(x+w/2,side_y,.030),xyz(x+w/2,side_y,t),xyz(x-w/2,side_y,t)],
                  (0,-1,0),"Black")
        flat(m,rectangle(x-w/2,x+w/2,front,side_y),.030,UP,PAVING)
        for a,b in ((lo-.48,lo-.026),(hi+.026,hi+.48)):
            block(m,f,a,b,.048,t+.13,.011,.217,STONE)
        block(m,f,lo-.51,hi+.51,t+.037,t+.49,.016,.243,"Cream")
    f.quad(m,cursor,f.length,0,t,0,BRICK)
    f.quad(m,0,f.length,t,e,0,BRICK)
    for j,(p,q) in enumerate(zip(area,area[1:]+area[:1])):
        ff=face(p,q)
        if j:
            ff.quad(m,0,ff.length,0,e,0,BRICK)
        facade(h,ff,7.37,e,1,7 if j%2==0 else 3,h.lod==0)
        if h.lod<2:
            block(m,ff,.11,ff.length-.11,e-.32,e-.062,.018,.228,STONE)
    mansard(h,(left,right,front,back),e,5.63,hood=True)

def campanile(h):
    m=h.body
    base=(76.10,88.30,45.7,60.2)
    volume(h,rectangle(*base),0,30.7,BRICK,5,(2,2,1,1))
    profile_roof(h,base,30.7,[(-.48,.022),(.05,.57)],STONE,"Cream")
    stage=(75.65,88.75,45.15,60.65)
    volume(h,rectangle(*stage),31.31,34.61,STONE,1,(2,2,1,1),False)
    bell=(77.75,86.65,47.30,58.50)
    volume(h,rectangle(*bell),34.641,42.1,BRICK,0,(0,0,0,0),False)
    tower_openings(h,bell,36.0,40.88)
    profile_roof(h,(76.95,87.45,46.45,59.35),42.09,[(-.21,.031),(1.57,4.07),(4.33,5.66)],SLATE)
    finial(h,82.2,52.9,47.74,49.0)

def tower_openings(h,rect,lo,hi):
    p=rectangle(*rect)
    for a,b in zip(p,p[1:]+p[:1]):
        f=face(a,b)
        u=f.length/2
        solid_window(h,f,u,min(3.37,f.length-.72),lo,hi,True)
        if h.lod<2:
            for j in range(6):
                z=lo+.29+j*(hi-lo-.95)/6
                block(h.body,f,u-1.34,u+1.34,z,z+.096,.101,.217,IRON)

def finial(h,x,y,bottom,top):
    plan=rectangle(x-.10,x+.10,y-.10,y+.10)
    h.body.polygon([xyz(u,v,bottom) for u,v in plan],nb.DOWN,IRON)
    p=xyz(x,y,top)
    for (u,v),(r,s) in zip(plan,plan[1:]+plan[:1]):
        f=face((u,v),(r,s))
        h.body.polygon([xyz(u,v,bottom),xyz(r,s,bottom),p],f.out,"Mustard")

def fire(h):
    paving(h,[(18.8,78.9,0,FIRE_DOOR_Y),(9.3,18.8,0,39.0),(75.8,91.6,27.5,68.0),(18.0,78.5,65.0,73.2)])
    fire_portal(h)
    apparatus_house(h)
    admin=(8.8,20.4,37.0,63.1)
    volume(h,rectangle(*admin),0,15.1,BRICK,3,(0,4,1,2))
    facade(h,face((8.8,37.0),(20.4,37.0)),5.31,15.1,2,2,True)
    mansard(h,admin,15.1,4.88)
    portico_entry(h,13.5,37.0,.12,2.65,4.12)
    campanile(h)

def palace_pavilion(h,rect,e,rise,floors,bays,bottom=0):
    volume(h,rectangle(*rect),bottom,e,BRICK,floors,bays)
    mansard(h,rect,e,rise)

def stair(h,x,y,w,deep,height,count):
    m=h.body
    start=y-deep
    x0,x1=x-w/2,x+w/2
    rise=(height-.034)/count
    for j in range(count):
        a,b=start+deep*j/count,start+deep*(j+1)/count
        z=.034+j*rise
        flat(m,rectangle(x0,x1,a,b),z,UP,"Cream")
        for u,normal in ((x0,(-1,0,0)),(x1,(1,0,0))):
            m.polygon([xyz(u,a,0),xyz(u,b,0),xyz(u,b,z),xyz(u,a,z)],normal,STONE)
        m.polygon([xyz(x0,b,z),xyz(x1,b,z),xyz(x1,b,z+rise),xyz(x0,b,z+rise)],(0,-1,0),STONE)
    flat(m,rectangle(x0,x1,start,y),0,nb.DOWN,STONE)
    m.polygon([xyz(x0,start,0),xyz(x1,start,0),xyz(x1,start,.034),xyz(x0,start,.034)],(0,-1,0),STONE)
    m.polygon([xyz(x0,y,0),xyz(x1,y,0),xyz(x1,y,height-.014),xyz(x0,y,height-.014)],(0,1,0),STONE)
    box(m,x0+.013,x1-.013,y-.014,y+1.76,.037,height,STONE,"Cream")

def drum(h,x,y,r,z0,z1,mat,n=12,top_mat=None):
    ring=lambda z:[xyz(x+r*math.cos(i*math.tau/n),y+r*math.sin(i*math.tau/n),z) for i in range(n)]
    lo,hi=ring(z0),ring(z1)
    h.body.polygon(lo,nb.DOWN,mat)
    h.body.polygon(hi,UP,top_mat or mat)
    kit.ring_surfaces(h.body,lo,hi,mat)
    return lo,hi

def taper(h,x,y,r0,r1,z0,z1,mat,n=12):
    rings=[[xyz(x+r*math.cos(i*math.tau/n),y+r*math.sin(i*math.tau/n),z) for i in range(n)]
           for r,z in ((r0,z0),(r1,z1))]
    h.body.polygon(rings[0],nb.DOWN,mat)
    h.body.polygon(rings[1],UP,mat)
    kit.ring_surfaces(h.body,*rings,mat)

def clock(h,f,z,diameter):
    m=h.body;u=f.length/2
    steps=28 if h.lod==0 else 20 if h.lod==1 else 12
    rad=diameter/2
    outline=[(u+rad*math.cos(i*math.tau/steps),z+rad*math.sin(i*math.tau/steps)) for i in range(steps)]
    relief(m,f,outline,.029,.196,"Mustard")
    u0,v0,u1,v1=nb.LAYOUT["lods"][m.lodkey]["CivicClock"]["uv"]
    m._add([f.point(x,y,.203) for x,y in outline],
           [(u0+(u1-u0)*(.5+(x-u)/diameter),v0+(v1-v0)*(.5+(y-z)/diameter)) for x,y in outline])
    if h.lod==0:
        for i in range(4):
            a=i*math.pi/2
            x,z0=u+(rad+.24)*math.cos(a),z+(rad+.24)*math.sin(a)
            block(m,f,x-.09,x+.09,z0-.09,z0+.09,.046,.208,"Cream")

def statue(h,x,y):
    # A gilded robed figure, with raised arm and a short staff.
    n=10 if h.lod==0 else 7 if h.lod==1 else 5
    drum(h,x,y,.62,82.46,82.81,"Cream",n)
    taper(h,x,y,.47,.235,82.824,84.47,"Mustard",n)
    taper(h,x,y,.237,.34,84.488,84.98,"Mustard",n)
    taper(h,x,y,.34,.15,84.996,85.24,"Mustard",n)
    taper(h,x,y,.105,.205,85.258,85.49,"Mustard",n)
    taper(h,x,y,.202,.105,85.506,85.81,"Mustard",n)
    if h.lod<2:
        f=face((x-.90,y-.104),(x+.90,y-.104))
        p=[(.18,85.63),(.26,85.59),(.49,85.21),(.74,84.97),(.60,84.82),(.34,85.08)]
        relief(h.body,f,p,.018,.141,"Mustard")
        p=[(1.00,84.86),(1.23,85.04),(1.51,84.74),(1.58,84.35),(1.43,84.29),(1.32,84.63)]
        relief(h.body,f,p,.021,.149,"Mustard")
    finial(h,x,y,85.80,86)

def belfry(h):
    m=h.body
    shaft=(90.5,107.5,61.2,79.4)
    volume(h,rectangle(*shaft),10,54.9,BRICK,7,(2,2,1,2))
    profile_roof(h,shaft,54.88,[(-.59,.013),(-.28,.62),(.41,1.12)],STONE,"Cream")
    transition=(91.2,106.8,61.86,78.75)
    volume(h,rectangle(*transition),56.02,62.40,STONE,1,(3,3,2,3),True)
    upper=(92.94,105.06,63.55,77.04)
    volume(h,rectangle(*upper),62.43,72.43,BRICK,0,(0,0,0,0))
    for p,q in zip(rectangle(*upper),rectangle(*upper)[1:]+rectangle(*upper)[:1]):
        f=face(p,q)
        u=f.length/2
        block(m,f,u-3.56,u+3.56,63.49,71.29,.012,.140,STONE)
        block(m,f,u-3.23,u+3.23,63.81,70.96,.147,.179,IRON)
        clock(h,f,67.40,5.66)
    profile_roof(h,(92.68,105.32,63.36,77.23),72.40,[(-.16,.012),(.60,.82),(1.42,1.01)],STONE,"Cream")
    bell=(94.62,103.38,65.92,74.68)
    volume(h,rectangle(*bell),73.423,78.78,IRON,0,(0,0,0,0),False)
    tower_openings(h,bell,74.16,78.16)
    profile_roof(h,(94.25,103.75,65.55,75.05),78.75,[(-.39,.014),(1.20,2.39),(3.59,3.70)],SLATE)
    statue(h,99.0,70.30)

def civic_pavilion(h):
    m=h.body
    body=(50.8,77.2,55.2,71.0)
    volume(h,rectangle(*body),.023,30.8,BRICK,3,(0,2,0,2),True)
    facade(h,face((50.8,55.2),(77.2,55.2)),8.58,30.8,3,3,True)
    mansard(h,body,30.8,11.2,hood=True)
    f=face((50.8,55.17),(77.2,55.17))
    mid=f.length/2
    # Monumental stone pilasters and triangular pediment stand forward of the brick pavilion.
    if h.lod<2:
        for u in (3.63,8.24,18.17,22.78):
            block(m,f,u-.34,u+.34,1.02,19.18,.014,.62,STONE)
            block(m,f,u-.52,u+.52,19.21,19.63,.037,.74,"Cream")
            block(m,f,u-.54,u+.54,.79,1.00,.040,.74,"Cream")
    block(m,f,2.56,f.length-2.56,19.72,21.40,.018,.191,STONE)
    uv_plate(m,f,mid,20.56,16.74,1.08,"CivicName")
    relief(m,f,[(2.46,21.44),(f.length-2.46,21.44),(mid,27.94)],.019,.301,STONE)
    if h.lod<2:
        for side in (-1,1):
            relief(m,f,[(mid+side*.72,23.22),(mid+side*3.06,23.31),(mid+side*2.39,24.75),
                        (mid+side*1.68,25.30)],.323,.414,"Cream")
        sculpture(h,f,mid,24.62)
    portico_entry(h,64,55.20,.84,5.08,6.61)
    stair(h,64,53.48,11.72,3.11,.84,6 if h.lod==0 else 3)

def hall(h):
    paving(h,[(33.2,94.8,0,57.13),(17.0,33.2,18.1,77.6),(94.8,111.0,18.1,79.7),(22.2,111.0,79.7,87.4)])
    # A pale central court ring encloses the separately placed fountain.
    r0,r1=5.57,6.29
    n=32 if h.lod<2 else 16
    for j in range(n):
        a,b=j*math.tau/n,(j+1)*math.tau/n
        h.body.polygon([xyz(64+r*math.cos(t),30+r*math.sin(t),.034)
                        for r,t in [(r0,a),(r1,a),(r1,b),(r0,b)]],UP,"Cream")
    palace_pavilion(h,(25,103,59,81),25.88,9.37,4,(10,3,9,3))
    palace_pavilion(h,(21.2,41.8,26.4,73.7),21.13,7.2,4,(3,6,3,5),.006)
    palace_pavilion(h,(87.25,107.8,26.65,73.95),21.45,7.48,4,(3,6,3,5),.010)
    palace_pavilion(h,(18.94,43.02,22.5,41.27),23.81,9.49,4,(4,3,3,3),.014)
    palace_pavilion(h,(85.98,110.06,22.73,41.52),24.09,9.52,4,(4,3,3,3),.018)
    civic_pavilion(h)
    belfry(h)

def build(a,lod):
    core.setup(a,lod,0)
    h=nb.House(lod)
    h.economy=True
    h.corner_detail=True
    h.heavy_frame=False
    h.thin_rail=True
    if a["service"]=="fire":
        fire(h)
    else:
        hall(h)
    return h

