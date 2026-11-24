"""Geometry for the Haussmann apartments and the Delaware counting houses."""
import math

import civic_geometry as civic
import detail_mesh as detail
from round5_specs import footprint

core,kit,nb=civic.core,civic.kit,civic.nb
face,flat,rectangle,xyz=civic.face,civic.flat,civic.rectangle,civic.xyz
box,block,relief=civic.box,civic.block,civic.relief
UP,DOWN=civic.UP,nb.DOWN
STONE="Dressed"
BASE="StoneBase"
BRICK="Brick085"
SLATE="SlateDark"
IRON="Iron"
LOWS=(0,1,2)

def plane(m,f,a,b,z,e,material):
    if b-a>.00004 and e-z>.00004:f.quad(m,a,b,z,e,0,material)

def inset(plan,value):
    l,r=min(x for x,y in plan),max(x for x,y in plan)
    f,b=min(y for x,y in plan),max(y for x,y in plan)
    cx,cy=(l+r)/2,(f+b)/2
    return [(cx+(x-cx)*(1-2*value/(r-l)),cy+(y-cy)*(1-2*value/(b-f))) for x,y in plan]

def paving(h,a):
    rows=[s["bounds_lot_m"] for s in a["native_surfaces"]]
    m=h.body
    xs=sorted({t for p in rows for t in p[:2]})
    ys=sorted({t for p in rows for t in p[2:]})
    cells={}
    for i,(l,r) in enumerate(zip(xs,xs[1:])):
        for j,(f,b) in enumerate(zip(ys,ys[1:])):
            for k,(l0,r0,f0,b0) in enumerate(rows):
                if l0<=(l+r)/2<=r0 and f0<=(f+b)/2<=b0:
                    cells[i,j]="CourtSetts" if k==1 else "FrontFlags"
                    break
    for (i,j),mat in cells.items():
        p=rectangle(xs[i],xs[i+1],ys[j],ys[j+1])
        flat(m,p,.030,UP,mat)
        if h.lod==2:continue
        flat(m,p,.002,DOWN,mat)
        for k,other in enumerate(((i,j-1),(i+1,j),(i,j+1),(i-1,j))):
            if other in cells:continue
            f=face(p[k],p[(k+1)%4])
            f.quad(m,0,f.length,.002,.030,0,mat)

def frontage(a,plan):
    roof=a["roofline"]
    for i,(p,q) in enumerate(zip(plan,plan[1:]+plan[:1])):
        if roof=="convex":
            role="front" if i<5 else ("rear" if i==6 else "party")
        elif a["access"]=="LeftCorner":
            role=("front","party","rear","corner-side","chamfer")[i]
        else:role=("front","party","rear","party")[i]
        yield role,face(p,q)

def plate(h,f,u,z,w,height,key,d=.182):
    m=h.body
    u0,v0,u1,v1=nb.LAYOUT["lods"][m.lodkey][key]["uv"]
    m._add([f.point(u-w/2,z-height/2,d),f.point(u+w/2,z-height/2,d),
            f.point(u+w/2,z+height/2,d),f.point(u-w/2,z+height/2,d)],
           [(u0,v0),(u1,v0),(u1,v1),(u0,v1)])

def fascia(h,f,a,u,z,w):
    height=.59 if a["zone_key"]=="Z3" else .66
    block(h.body,f,u-w/2-.10,u+w/2+.10,z-height/2-.068,z+height/2+.068,.015,.152,IRON)
    plate(h,f,u,z,w,height,"Sign_"+a["design"])

def aperture(h,f,opening,ground):
    u,w,b,t,curve,door,bars=opening
    m=h.body
    a,r=u-w/2,u+w/2
    depth=-(.66 if door and getattr(h,"deep_portal",False) else .72 if not door and getattr(h,"deep_arcade",False) and b<1.2 else getattr(h,"window_recess",.35) if not door else .35) if h.lod<2 else .014
    pointed=curve<0
    rise=min(abs(curve),w*(.75 if pointed else .36))
    spring=t-rise
    steps=(16 if rise>.48 else 8) if h.lod==0 else 6 if h.lod==1 else 3
    def header(half,rise):
        if not pointed:return kit.arch_points(u,half,spring,rise,steps)
        return [(u+half*v,spring+rise*math.sqrt(1-abs(v))) for v in (-1,-.75,-.5,0,.5,.75,1)]
    arc=header(w/2,rise) if rise else [(a,t),(r,t)]
    outline=[(a,b),(r,b),*arc[::-1]]
    if h.lod<2:
        for (x,z),(y,k) in zip(outline,outline[1:]+outline[:1]):
            normal=-f.tangent*(k-z)+UP*(y-x)
            m.polygon([f.point(x,z,0),f.point(y,k,0),f.point(y,k,depth-.012),f.point(x,z,depth-.012)],normal,"RevealStone")
        for (x,z),(y,k) in zip(arc,arc[1:]):
            pts=[(x,z),(y,k),(y,t),(x,t)]
            if max(t-z,t-k)>.00001:
                m.polygon([f.point(v,j,0) for v,j in pts],f.out,ground)
    if door:
        leaf=spring-.16 if rise else t-.42
        f.quad(m,a,r,b,leaf,depth, "TinOxide" if bars else "Green")
        window=[(a,leaf),(r,leaf),*arc[::-1]]
        if h.lod==0:
            block(m,f,u-.03,u+.03,b+.03,leaf-.02,depth+.011,depth+.034,IRON)
            for x in (u-.20,u+.20):
                block(m,f,x-.023,x+.023,b+.96,b+1.20,depth+.036,depth+.071,"Mustard")
    else:window=outline
    points=[f.point(x,z,depth) for x,z in window]
    if (not door or getattr(h,"r12",False)) and u in getattr(h,"quiet_panes",()):
        m.polygon(points,f.out,getattr(h,"quiet_material","GreyBlue"))
    else:
        h.windows.polygon(points,f.out,"Cream",room=nb.ROOMS[round(17*u+13*b)%len(nb.ROOMS)])
    detail.window(h,f,opening,depth,arc,spring,header)

def row(h,f,z,e,mat,slots):
    m=h.body
    if h.lod==2:plane(m,f,0,f.length,z,e,mat)
    prev=0
    for opening in sorted(slots):
        u,w,b,t,*_=opening
        a,r=u-w/2,u+w/2
        assert prev<=a and r<=f.length and z<=b<t<e,(h.name,f.length,opening,z,e,prev)
        if h.lod<2:
            plane(m,f,prev,a,z,e,mat)
            plane(m,f,a,r,z,b,mat)
            plane(m,f,a,r,t,e,mat)
        aperture(h,f,opening,mat)
        prev=r
    if h.lod<2:plane(m,f,prev,f.length,z,e,mat)
    detail.facade(h,f,z,e,slots,mat)

def stair(h,f,u,w,threshold):
    m=h.body
    steps=3 if threshold>.4 else 1
    for j in range(steps):
        depth=1.30-j*.34 if steps>1 else .38
        z0=.035+j*(threshold-.035)/steps
        z1=.035+(j+1)*(threshold-.035)/steps-.004
        block(m,f,u-w/2-.25+j*.073,u+w/2+.25-j*.073,z0,z1,-.018,depth,STONE)

def positions(h,a,f,role,count):
    if role=="chamfer":return [f.length/2]
    if role=="corner-side":
        end=f.length-.78
        total=min(10.8,end-1.15)
        return [end-total*(j+.5)/count for j in range(count)]
    return [f.length*(i+.5)/count for i in range(count)]

def to_local(f,x):
    return (nb.X(x)-f.point(0,0,0).x)/f.tangent.x

def door_here(a,f,role):
    if role=="chamfer":return [f.length/2]
    if role=="rear":return [f.length/2]
    if role!="front" or a["access"]=="LeftCorner":return []
    x0=f.point(0,0,0).x
    x1=f.point(f.length,0,0).x
    return [to_local(f,e["position_lot_m"][0]) for e in a["active_entrances"]
            if x0+.35<nb.X(e["position_lot_m"][0])<x1-.35]

def rustication(h,f,z,e,a,split):
    if h.lod==2:return
    m=h.body
    for hgt in (z+.51,z+1.28,z+2.07,z+2.88):
        if hgt>e-.48:continue
        for l,r in split:
            if r-l>.19:block(m,f,l,r,hgt,hgt+.105,.011,.082,STONE)

def piers(h,f,coords,z,e,mat,w,d):
    if h.lod==2:return
    for u in coords:
        block(h.body,f,u-w/2,u+w/2,z,e,.016,d,mat)
        block(h.body,f,u-w*.67,u+w*.67,e-.015,e+.15,.024,d+.076,"Cream")

def cornice(h,f,e,street):
    m=h.body
    band=min(.18,f.length*.09)
    if h.lod<2:
        block(m,f,band,f.length-band,e-.34,e-.112,.009,.174 if street else .102,STONE)
        if h.lod==0 and street:
            count=max(2,round(f.length/.90))
            for j in range(count):
                u=f.length*(j+.5)/count
                block(m,f,u-.067,u+.067,e-.49,e-.362,.012,.152,"Cream")
    else:
        block(m,f,band,f.length-band,e-.245,e-.11,.012,.11,STONE)

def rail(h,f,l,r,z,d,pattern):
    m=h.body
    block(m,f,l,r,z+.84,z+.91,d-.036,d+.041,IRON)
    if h.lod==2:return
    block(m,f,l+.02,r-.02,z+.071,z+.13,d-.023,d+.026,IRON)
    n=max(2,round((r-l)/(.53 if h.lod==0 else 1.12)))
    for j in range(n+1):
        u=l+.062+(r-l-.124)*j/n
        block(m,f,u-.017,u+.017,z+.132,z+.837,d-.018,d+.020,IRON)
    if h.lod!=0:return
    count=max(2,round((r-l)/(2.25 if pattern in {"Paris scroll pairs","Creole rings"} else 1.22)))
    for j in range(count):
        u=l+(r-l)*(j+.5)/count
        if pattern=="Paris scroll pairs" or pattern=="Creole rings":
            rings=((-0.105,.082,.16),(.105,.082,.16)) if pattern=="Paris scroll pairs" else ((0,.159,.19),)
            for delta,rx,rz in rings:
                for k in range(6):
                    theta=(k+.06)*math.tau/6
                    phi=(k+.94)*math.tau/6
                    shape=[(u+delta+rx*sc*math.cos(t),z+.49+rz*sc*math.sin(t))
                           for t,sc in ((theta,1),(phi,1),(phi,.72),(theta,.72))]
                    relief(m,f,shape,d+.026,d+.050,IRON)
            continue
        if pattern=="Lille geometric":
            qs=[(u-.16,z+.49),(u,z+.30),(u+.16,z+.49),(u,z+.68)]
        elif pattern=="Philadelphia bar-and-urn":
            qs=[(u-.09,z+.39),(u+.09,z+.39),(u+.12,z+.58),(u-.12,z+.58)]
        elif pattern=="whiplash":
            qs=[(u-.17,z+.39),(u+.01,z+.32),(u+.19,z+.62),(u-.01,z+.67),(u+.055,z+.54)]
        else:
            rx,rz=(.12,.24) if pattern=="oval iron" else (.175,.175)
            qs=[(u+rx*math.cos(i*math.tau/8),z+.49+rz*math.sin(i*math.tau/8)) for i in range(8)]
        # A separate face above the picket plane gives the scrolls their own physical depth.
        relief(m,f,qs,d+.025,d+.049,IRON)

def balcony(h,a,f,z,side):
    m=h.body
    if f.length<2.1:return
    margin=.78 if side in {"chamfer","corner-side"} else .21
    l,r=margin,f.length-margin
    if side=="corner-side":l=max(l,r-9.8)
    d=.62 if side=="chamfer" else .185 if side=="corner-side" else .86
    block(m,f,l,r,z-.165,z-.034,-.009,d,STONE)
    rail(h,f,l+.052,r-.052,z-.032,d-.084,a["ironwork"])
    if h.lod==0:
        n=max(2,round((r-l)/3.45))
        for j in range(n):
            u=l+(r-l)*(j+.5)/n
            block(m,f,u-.105,u+.105,z-.37,z-.169,.031,d*.67,"Cream")

def ground(h,a,f,role,cap,count):
    res=a["zone_key"]=="Z3";m=h.body
    threshold=.74 if a["ground"]=="paired" else .13 if res else .67
    ground_mat=getattr(h,"tower_ground",None) or ("Ashlar" if a["ground"] in {"granite","rusticated","arcade"} else STONE)
    ds=door_here(a,f,role)
    narrow=f.length<5.1
    door_w=min(2.23 if getattr(h,"large_entry",False) else 1.46 if res else 2.10,f.length-.81)
    windows=positions(h,a,f,role,count)
    window_w=min(2.35 if res else 2.78,f.length/count*.53)
    if a["roofline"]=="bank-gable" and role=="front":
        windows=[f.length*.365];window_w=5.95
    if a["roofline"]=="exchange" and role=="front":
        windows=[f.length*.59];window_w=5.55
    if res and a["ground"]=="arcade" and role=="front":window_w=min(3.19,f.length/count*.72)
    openings=[]
    for u in ds:
        openings.append((u,door_w,threshold,cap-.68,.48 if res else .70,True,not res))
    for u in windows:
        if any(abs(u-v)<(window_w+door_w)/2+.26 for v in ds):continue
        b=.61 if res else 1.10
        head=cap-.82
        if role=="rear":head=cap-.96
        openings.append((u,window_w,b,head,.48 if res else .80,False,not res and role=="front"))
    row(h,f,.008,cap,ground_mat,openings)
    if h.lod<2:
        edges=[0.]
        for u,w,*_ in sorted(openings):edges.extend((u-w/2-.17,u+w/2+.17))
        edges.append(f.length)
        rustication(h,f,.12,cap,a,list(zip(edges[::2],edges[1::2])))
    for u in ds:stair(h,f,u,door_w,threshold)
    if role=="front" and h.lod<2 and a["ground"]=="granite" and not narrow:
        cs=[f.length*.085,f.length*.915]
        piers(h,f,cs,.19,2.67,"Greystone",.48,.39)

def oriel(h,f,u,w,z,e,wall):
    m=h.body
    l,r=u-w/2-.27,u+w/2+.27
    # The stone-sided projection carries its own window and seats on the brick wall.
    a,b=f.point(l,0,.72),f.point(r,0,.72)
    ff=nb.Face(a[:2],b[:2])
    for x,normal in ((l,-f.tangent),(r,f.tangent)):
        m.polygon([f.point(x,k,d) for k,d in ((z+.16,-.01),(z+.16,.72),(e-.29,.72),(e-.29,-.01))],
                  normal,STONE)
    for height,normal in ((z+.16,DOWN),(e-.29,UP)):
        m.polygon([f.point(x,height,d) for x,d in ((l,-.01),(r,-.01),(r,.72),(l,.72))],normal,STONE)
    row(h,ff,z+.16,e-.29,STONE,[(ff.length/2,w,z+.52,e-.55,0,False,False)])
    if h.lod<2:
        for x in (l+.21,r-.21):
            block(m,f,x-.088,x+.088,z-.048,z+.152,.025,.48,STONE)

def upper(h,a,f,role,levels,count):
    res=a["zone_key"]=="Z3"
    m=h.body
    street=role in {"front","chamfer","corner-side"}
    if role=="party":
        plane(m,f,0,f.length,levels[0],levels[-1],BRICK)
        return
    for i,(z,e) in enumerate(zip(levels,levels[1:]),1):
        # Keep the full storey rhythm in the front silhouettes and simplify the rear first.
        if h.lod==2 and (role=="rear" or i%2==0):
            plane(m,f,0,f.length,z,e,BRICK)
            continue
        n=count if h.lod==0 else max(1,(count+1)//2) if h.lod==1 else max(1,count//3)
        if role=="corner-side":n=min(n,3 if h.lod==0 else 1)
        if role=="rear" and h.lod==1:n=1
        if role=="chamfer":n=1
        width=min(1.80 if res else 2.18,f.length/n*.60)
        if role=="rear":width*=.82
        sill=z+(.34 if street and (res and i in (2,5) or not res and i==1) else .48)
        head=e-.51
        slots=[(u,width,sill,head,.18 if i%3==0 and h.lod==0 else 0,False,False) for u in positions(h,a,f,role,n)]
        wall=STONE if res and i==1 else BRICK
        style=a["roofline"]
        if role=="front" and style in {"loggia","firewall"} and i in ((2,3,4,5) if style=="loggia" else (2,3,4)):
            target=f.length*(.70 if style=="firewall" else .50)
            selected=min(slots,key=lambda o:abs(o[0]-target))
            slots.remove(selected)
            oriel(h,f,selected[0],selected[1],z,e,wall)
        row(h,f,z,e,wall,slots)
        if street and h.lod<2:
            block(m,f,.14,f.length-.14,z+.046,z+.157,.018,.123,
                  "TinGreen" if a["roofline"] in {"firewall","whiplash"} and i%2==0 else "Cream")
            if role=="front" and h.lod==0 and res and i>1 and f.length>10:
                piers(h,f,[f.length*j/n for j in range(1,n)],z+.23,e-.42,STONE,.21,.133)
        if role in {"front","chamfer"} and (res and i in (2,5) or not res and i==1 and a["roofline"] in {"merchant","insurance","notary","ship-tower"}):
            balcony(h,a,f,z,role)

def caps(h,plan,e,profile,material=SLATE):
    prev=None
    for n,(margin,rise) in enumerate(profile):
        ring=[xyz(x,y,e+(rise if n else 0)) for x,y in inset(plan,margin)]
        if n==0:h.body.polygon(ring,DOWN,STONE)
        else:kit.ring_surfaces(h.body,prev,ring,material)
        prev=ring
    h.body.polygon(prev,UP,"TinFlat")

def top_ornament(h,f,shape,material=BRICK,thickness=.33):
    relief(h.body,f,shape,-thickness,.035,material)

def side_pavilions(h,a,e):
    l,r,f,b=a["walls"]
    for j,(x,w,rise) in enumerate(((l+1.42,6.38,5.78),(r-8.24,6.82,6.77))):
        rect=(x,x+w,f+.61+j*.14,f+8.23+j*.14)
        civic.profile_roof(h,rect,e+.925+j*.045,[(-.07,.014),(1.36,rise*.66),(2.31,rise)],SLATE,"TinFlat")

def triangular(h,a,e,kind):
    l,r,f,b=a["walls"]
    centre=(l+r)/2
    span={"cross-pavilion":7.3,"bank-gable":6.23,"temple":7.19}[kind]
    low=e+.47 if kind=="cross-pavilion" else e+.20
    high=e+({"cross-pavilion":6.9,"bank-gable":6.45,"temple":3.55}[kind])
    front=f-.126
    df=face((centre-span,front),(centre+span,front))
    pts=[(0,low),(df.length,low),(df.length/2,high)]
    top_ornament(h,df,pts,STONE if kind=="temple" else BRICK,.32)
    for x,y in ((.11,df.length/2),(df.length/2,df.length-.11)):
        z0=low+(high-low)*min(x,df.length-x)/(df.length/2)
        z1=low+(high-low)*min(y,df.length-y)/(df.length/2)
        relief(h.body,df,[(x,z0-.013),(y,z1-.013),(y,z1+.164),(x,z0+.164)],-.24,.155,STONE)
    if h.lod==2:return
    if kind!="temple":
        block(h.body,df,span-.42,span+.42,low+.603,low+2.14,.043,.13,"Black")
        for j in (1,2,3):
            z=low+j*.55
            reach=span*(1-(z-low)/(high-low))-.17
            if reach>1:block(h.body,df,span-reach,span+reach,z,z+.091,.048,.111,"Cream")
    else:
        block(h.body,df,.14,df.length-.14,low+.036,low+.25,.044,.20,STONE)

def shaped_gable(h,a,e,kind):
    l,r,f,b=a["walls"]
    mid=(l+r)/2
    w=12.94 if kind=="stepped" else 9.30 if kind=="bell-gable" else 13.27
    df=face((mid-w/2,f-.08),(mid+w/2,f-.08))
    e+=.055
    if kind=="stepped":
        shape=[(0,e),(w,e),(w,e+1.32),(.86*w,e+1.32),(.86*w,e+2.63),(.71*w,e+2.63),
               (.71*w,e+4.28),(.59*w,e+4.28),(.59*w,e+6.61),(.41*w,e+6.61),(.41*w,e+4.28),
               (.29*w,e+4.28),(.29*w,e+2.63),(.14*w,e+2.63),(.14*w,e+1.32),(0,e+1.32)]
    elif kind=="bell-gable":
        q=[(1,1.37),(.82,1.88),(.70,2.86),(.61,4.16),(.57,5.90),(.50,7.30)]
        shape=[(0,e),(w,e),*[(x*w,e+z) for x,z in q],*[(w*(1-x),e+z) for x,z in q[-2::-1]]]
    else:
        q=[(1,1.60),(.83,2.43),(.70,2.75),(.60,4.20),(.50,5.38)]
        shape=[(0,e),(w,e),*[(x*w,e+z) for x,z in q],*[(w*(1-x),e+z) for x,z in q[-2::-1]]]
    top_ornament(h,df,shape,BRICK)
    if h.lod<2:
        block(h.body,df,w*.46,w*.54,e+.92,e+2.38,.043,.12,"Black")
        if kind=="bell-gable":
            block(h.body,df,w*.477,w*.523,e+4.72,e+4.97,.04,1.05,"BrownBrick")
        else:
            for u in (.32,.68):block(h.body,df,w*u-.14,w*u+.14,e+.42,e+1.83,.043,.152,"Cream")

def box_crown(h,rect,z,top,mat=BRICK):
    box(h.body,*rect,z,top,mat,"TinFlat")

def drum(h,x,y,profile,material):
    m=h.body
    n=16 if h.lod==0 else 12 if h.lod==1 else 8
    rings=[[xyz(x+r*math.cos(i*math.tau/n),y+r*math.sin(i*math.tau/n),z)
            for i in range(n)] for r,z in profile]
    m.polygon(rings[0],DOWN,STONE)
    for i,(p,q) in enumerate(zip(rings,rings[1:])):kit.ring_surfaces(m,p,q,STONE if i==0 else material)
    m.polygon(rings[-1],UP,"TinFlat")

def corner_roof(h,a,e):
    l,r,f,b=a["walls"]
    x,y=l+3.64,f+3.73
    roof=a["roofline"]
    if roof=="square-cupola":
        rect=(x-2.53,x+2.53,y-2.53,y+2.53)
        box_crown(h,rect,e+.075,e+5.27,BRICK)
        civic.profile_roof(h,rect,e+5.27,[(-.12,.018),(.96,2.66),(1.85,3.63)],SLATE,"TinFlat")
        civic.finial(h,x,y,e+8.92,e+10.18)
        return
    green=roof=="copper-dome"
    radius=3.44 if green else 2.93
    z0=e+.41;shoulder=e+3.02
    hgt=4.67 if green else 6.05
    pairs=[(radius*.95,z0),(radius,shoulder),(radius*.92,shoulder+hgt*.34),
           (radius*.65,shoulder+hgt*.73),(.39,shoulder+hgt)]
    if h.lod==2:pairs=[pairs[j] for j in (0,1,3,4)]
    drum(h,x,y,pairs,"TinGreen" if green else SLATE)
    rect=(x-.29,x+.29,y-.29,y+.29)
    box_crown(h,rect,shoulder+hgt+.013,shoulder+hgt+.80,STONE)
    civic.finial(h,x,y,shoulder+hgt+.794,shoulder+hgt+1.69)

def roof(h,a,plan):
    l,r,f,b=a["walls"]
    e=a["cornice_m"]
    roof=a["roofline"]
    res=a["zone_key"]=="Z3"
    profile={
      "straight":((-.18,.018),(2.31,3.41),(3.05,4.04)),
      "convex":((-.18,.018),(1.24,2.88),(2.88,4.82),(3.65,5.02)),
      "bellcast":((-.18,.018),(.92,.63),(2.02,2.05),(2.77,4.60),(3.42,5.28)),
      "cross-pavilion":((-.18,.018),(2.32,3.28),(3.39,4.05)),
      "loggia":((-.18,.018),(2.71,3.94),(3.85,4.27)),
      "paired":((-.18,.018),(2.23,2.35),(3.20,3.08)),
      "stepped":((-.18,.018),(1.88,3.29),(2.93,3.85)),
      "firewall":((-.18,.018),(2.75,4.56),(3.65,4.82)),
      "whiplash":((-.18,.018),(1.90,3.30),(3.36,4.31)),
      "slate-dome":((-.15,.018),(2.30,3.43),(3.45,4.11)),
      "copper-dome":((-.15,.018),(2.55,2.93),(3.34,3.69)),
      "square-cupola":((-.15,.018),(2.70,3.69),(3.65,4.29)),
      "bank-gable":((-.15,.018),(2.55,3.82),(4.15,4.60)),
      "temple":((-.14,.018),(2.38,1.88),(3.85,2.13)),
      "merchant":((-.16,.018),(1.40,2.44),(3.62,4.47)),
      "bell-gable":((-.14,.018),(2.44,4.83),(4.15,5.05)),
      "insurance":((-.16,.018),(1.78,4.14),(2.80,5.34),(3.82,5.61)),
      "ship-tower":((-.16,.018),(2.63,3.15),(3.71,3.83)),
      "exchange":((-.16,.018),(1.98,2.79),(3.33,3.44)),
      "notary":((-.16,.018),(2.15,3.93),(4.54,6.31)),
    }[roof]
    if h.lod==2 and len(profile)>3:profile=profile[:1]+profile[-2:]
    caps(h,plan,e,profile)
    m=h.body
    if roof in {"cross-pavilion","bank-gable","temple"}:triangular(h,a,e,roof)
    if roof in {"stepped","bell-gable","whiplash"}:shaped_gable(h,a,e,roof)
    if roof=="paired":side_pavilions(h,a,e)
    if roof=="firewall":
        for x,z in ((l+.28,e+5.91),(r-.39,e+6.77)):
            box_crown(h,(x-.20,x+.20,f+.53,b-.42),e+.34,z,BRICK)
            box_crown(h,(x-.24,x+.24,f+1.23,f+2.58),z+.016,z+1.13,BRICK)
    if a["access"]=="LeftCorner":corner_roof(h,a,e)
    if roof=="loggia":
        rr=(l+5.10,r-5.10,f+3.05,f+7.28)
        box_crown(h,rr,e+3.93,e+6.04,STONE)
        civic.profile_roof(h,rr,e+6.04,[(-.10,.018),(.73,1.18),(1.32,1.45)],SLATE,"TinFlat")
        ff=face((rr[0],rr[2]),(rr[1],rr[2]))
        n=4 if h.lod<2 else 2
        for j in range(n):
            u=ff.length*(j+.5)/n
            h.pane(ff,u-.32,u+.32,e+4.30,e+5.61,.023)
    if roof in {"ship-tower","exchange"}:
        x=r-3.52 if roof=="ship-tower" else (l+r)/2
        y=f+4.24 if roof=="ship-tower" else f+6.75
        span=2.39 if roof=="ship-tower" else 2.94
        rr=(x-span,x+span,y-2.20,y+2.20)
        box_crown(h,rr,e+2.93,e+6.14,BRICK if roof=="ship-tower" else STONE)
        civic.profile_roof(h,rr,e+6.14,[(-.10,.014),(.71,1.85),(1.30,2.34)],SLATE,"TinFlat")
        if roof=="ship-tower":
            civic.finial(h,x,y,e+8.44,e+10.27)
            ff=face((x-.84,y),(x+.84,y))
            relief(m,ff,[(.08,e+9.06),(1.58,e+9.06),(1.34,e+8.86),(.40,e+8.86)],-.031,.032,IRON)
            relief(m,ff,[(.37,e+9.19),(1.23,e+9.19),(.84,e+10.02)],-.034,.035,IRON)
    if h.lod<2 and roof not in {"temple","bank-gable","bell-gable","stepped","whiplash"}:
        df=face((l+.44,f+.19),(r-.44,f+.19))
        us=(.31,.70) if not res else (.18,.41,.63,.82)
        if h.lod==1:us=us[1::3] if roof=="convex" or a["access"]=="LeftCorner" else us[::2]
        if a["access"]=="LeftCorner":us=tuple(u for u in us if u>.23)
        for i,u in enumerate(us):kit.dormer(h,df,df.length*u,e+.43,oval=h.lod==0 and i%2==0,high=.18)
    if roof not in {"firewall","temple"}:
        for i,x in enumerate((l+.63,r-.63)):
            y=b-3.06-i*.73
            z=e+profile[-1][1]*.39+.01*i
            box_crown(h,(x-.26,x+.26,y-.34,y+.34),e-.06,z+2.26,BRICK)
            box(m,x-.33,x+.33,y-.40,y+.40,z+2.247,z+2.43,STONE,"TinFlat")

def character(h,a,f,zones):
    if h.lod==2 or f.length<8:return
    m=h.body
    style=a["roofline"]
    cap=zones[0]
    if style=="temple":
        for t in (.103,.36,.64,.897):
            p=f.point(f.length*t,0,.52)
            x=p.x+nb.W/2
            y=p.y-nb.Y(0)
            civic.drum(h,x,y,.36,.07,a["cornice_m"]-.51,"Cream",10 if h.lod==0 else 7)
            civic.drum(h,x,y,.44,a["cornice_m"]-.60,a["cornice_m"]-.35,STONE,8)
    elif style in {"bank-gable","insurance"}:
        for t in (.15,.85):
            p=f.point(f.length*t,0,.31)
            x=p.x+nb.W/2
            y=p.y-nb.Y(0)
            civic.drum(h,x,y,.30,.043,cap-.22,"Greystone",10 if h.lod==0 else 7)
            civic.drum(h,x,y,.37,cap-.41,cap-.19,STONE,8)
        if style=="insurance":
            u=f.length/2
            z=a["cornice_m"]-.92
            block(m,f,u-.89,u+.89,z-.84,z+.81,.024,.144,STONE)
            plate(h,f,u,z,1.34,1.34,"MatteDial",.185)
    elif style=="merchant":
        for j in range(3):
            u=f.length*(j+.5)/3
            z=cap-.40
            relief(m,f,[(u-.19,z+.22),(u+.18,z+.22),(u+.14,z-.12),(u,z-.24),(u-.14,z-.12)],
                   .023,.20,"Cream")

def build(a,lod):
    core.setup(a,lod,0)
    nb.REMAP.update(dict(zip((BRICK,SLATE,IRON),a["palette"])))
    h=nb.House(lod);h.name=a["name"]
    h.economy=True;h.corner_detail=True;h.heavy_frame=False;h.thin_rail=True
    h.deep_portal=a["roofline"]=="notary";h.deep_arcade=a["ground"]=="arcade"
    plan=footprint(a)
    m=h.body
    res=a["zone_key"]=="Z3"
    e=a["cornice_m"]
    ground_top=3.88 if res else 5.49
    levels=[ground_top,6.21,*[6.21+(e-6.21)*j/4 for j in (1,2,3,4)]] if res else (
            [ground_top,e] if a["roofline"]=="notary" else [ground_top,(ground_top+e)/2,e])
    paving(h,a)
    flat(m,plan,.008,DOWN,BASE)
    for role,f in frontage(a,plan):
        if role=="party":
            plane(m,f,0,f.length,.008,e,BRICK)
            cornice(h,f,e,False)
            continue
        front_count=(2 if f.length>5.7 else 1) if a["roofline"]=="convex" and role=="front" else a["bays"]
        count={"front":front_count,"chamfer":1,"corner-side":3,"rear":3 if res else 2}[role]
        gcount=max(1,count if lod==0 else (count+1)//2)
        ground(h,a,f,role,ground_top,gcount)
        upper(h,a,f,role,levels,count)
        cornice(h,f,e,role!="rear")
        if role=="front" and f.length>6.7 and (a["roofline"]!="convex" or f.length>7.0):
            fascia(h,f,a,f.length/2,ground_top-.33,min(f.length-.83,8.43 if res else 9.1))
            character(h,a,f,levels)
        elif role=="chamfer":fascia(h,f,a,f.length/2,ground_top-.33,f.length-.72)
    roof(h,a,plan)
    return h
