"""Architecture and material placement for the three Round 12 residential zones."""
import math

from mathutils import Vector
import detail_mesh as detail
from house_parts import edges, hip, roof, round_wall, curve_step, thin_glass
from tenement_details import beam
import round5_geometry as g

core,kit,nb=g.core,g.kit,g.nb
box,flat,xyz,rectangle,block=g.box,g.flat,g.xyz,g.rectangle,g.block
UP,DOWN=g.UP,g.DOWN
STONE,IRON,BRICK="Dressed","Iron","Brick085"
WATER="CanalWater"

def rect(l,r,f,b):
    return (l,r,f,b)

def slab(h,p,z,t,mat,top=None):
    box(h.body,*p,z,t,mat,top)

def surface(h,p,z,mat):
    flat(h.body,rectangle(*p),z,UP,mat)

def post(h,x,y,z,t,w=.20,mat=IRON):
    slab(h,(x-w/2,x+w/2,y-w/2,y+w/2),z,t,mat)

def staff(h,p,z=.11):
    f=edges(p)[0]
    g.stair(h,f,f.length/2,1.22,z)

def steps(h,x,y,z,count=6,w=2.1,run=2.7):
    for i in range(count):
        slab(h,(x-w/2,x+w/2,y-run+run*i/count,y-run+run*(i+1)/count-.008),
             .05,z*(i+1)/count,STONE)

def section(h,p,z,e,levels=2,roof_kind="hip",rise=2.5,mat=BRICK,omit=(),
            front="entry",bays=None,roof_mat=None,over=0,side_entry=False):
    l,r,f,b=p
    entry_side=3 if side_entry==3 else 1   # side_entry=3 puts the side door on the left face
    flat(h.body,rectangle(*p),z,DOWN,"StoneBase")
    for side,face in enumerate(edges(p)):
        if side in omit:
            continue
        n=(bays or max(1,min(4,round(face.length/3.6)))) if side in (0,2) else max(1,min(3,round(face.length/5.2)))
        if h.lod==1:
            n=min(n,2)
        if h.lod==2:
            n=min(n,2)
        for i in range(levels):
            low=z+(e-z)*i/levels
            high=z+(e-z)*(i+1)/levels
            slots=[]
            entry=(side==0 and front in {"entry","shop","dock","hotel","gallery"} and i==0)
            entry=entry or (side_entry and side==entry_side and i==0)
            for j in range(n):
                u=face.length*(j+.5)/n
                if entry and j==n//2:
                    u=face.length/2
                opening_width=min(1.39,face.length/n*.52)
                ht=high-.47
                bottom=low+.67
                if entry and j==n//2:
                    slots.append((u,min(1.32,face.length/n*.52),low+.11,min(ht,low+2.34),.11,True,False))
                    continue
                if side==0 and front=="gallery" and j==n//2 and i>0 and h.lod<2:
                    deck=(3.09,6.17,9.25)[i-1]
                    slots.append((face.length/2,min(1.15,face.length/n*.42),max(deck+.035,low+.04),high-.43,.11,True,False))
                    continue
                if side==0 and front=="blind":
                    continue
                if side==0 and front in {"shop","dock"} and i==0:
                    opening_width=min(2.65,face.length/n*.74)
                    bottom=low+.31
                if side_entry and side==entry_side and i==0:
                    bottom=low+.29
                if low+.08<bottom<ht-.22:
                    slots.append((u,opening_width,bottom,ht,.15 if h.lod<2 and i!=levels-1 else 0,False,False))
            if h.lod==2:
                slots=[s for s in slots if side==0 and i==min(1,levels-1) and not s[5]][:1]
            candidates=[s for s in slots if not s[5]]
            lit={s[0] for j,s in enumerate(candidates)
                 if (h.quiet_counter+j+1)%3==0 and (not h.estate or i==levels-1 and side in (0,2))}
            h.quiet_counter+=len(candidates)
            if h.hotel:
                lit={candidates[0][0]} if side==0 and i==1 and candidates else set()
            if h.estate and levels==1 and z>3 and side==0 and candidates and h.lod==1:
                lit={candidates[0][0]}
            if h.lod==2 and slots:
                lit={slots[0][0]}
            h.quiet_panes={s[0] for s in slots}-lit
            h.finish_cornice=i==levels-1 and side in (0,2)
            h.plain_piers=side in (1,3)
            h.plain_frames=side in (1,3) or (h.compact_trim and side==2)
            g.row(h,face,low,high,mat,slots)
    h.plain_piers=False
    h.plain_frames=False
    if roof_kind:
        q=(l-over,r+over,f-over,b+over)
        cover(h,q,e,roof_kind,rise,roof_mat or h.roof,mat)

def cover(h,p,z,kind,rise,mat,wall=BRICK):
    l,r,f,b=p
    if kind=="hip":
        hip(h,p,z,rise,mat)
    elif kind=="gable":
        roof(h,p,z,rise,mat)
    elif kind=="cross":
        x=(l+r)/2
        mid=f+(b-f)*.40
        for y in (f,b):
            h.body.polygon([xyz(l,y,z),xyz(r,y,z),xyz(r,mid,z+rise),xyz(l,mid,z+rise)],UP,mat)
        for edge,sign in ((l,-1),(r,1)):
            h.body.polygon([xyz(edge,f,z),xyz(edge,b,z),xyz(edge,mid,z+rise)],(sign,0,0),wall)
    elif kind=="mansard":
        inset=min((r-l)*.32,(b-f)*.20,1.85)
        g.caps(h,rectangle(*p),z,((0,0),(inset,rise*.81),(inset+.31,rise)),mat)
    elif kind=="shed":
        h.body.polygon([xyz(l,f,z),xyz(r,f,z),xyz(r,b,z+rise),xyz(l,b,z+rise)],UP,mat)
        h.body.polygon([xyz(r,b,z),xyz(l,b,z),xyz(l,b,z+rise),xyz(r,b,z+rise)],(0,1,0),wall)
        for x,sign in ((l,-1),(r,1)):
            h.body.polygon([xyz(x,f,z),xyz(x,b,z),xyz(x,b,z+rise)],(sign,0,0),wall)
    else:
        slab(h,p,z+.004,z+.21,mat,"TinFlat")
        if h.lod<2:
            for q in ((l,r,f,f+.18),(l+.002,r-.002,b-.18,b),
                      (l,l+.18,f+.195,b-.195),(r-.18,r,f+.195,b-.195)):
                slab(h,q,z+.22,z+.61,wall,STONE)

def rail(h,face,l,r,z,d=.13,interval=.32):
    if r-l<.24:
        return
    block(h.body,face,l,r,z+.89,z+.95,d,d+.075,IRON)
    if h.lod==2:
        return
    block(h.body,face,l+.009,r-.009,z+.14,z+.18,d+.007,d+.062,IRON)
    n=max(2,round((r-l)/(interval if h.lod==0 else interval*2.15)))
    for i in range(n+1):
        x=l+.035+(r-l-.07)*i/n
        block(h.body,face,x-.018,x+.018,z+.19,z+.878,d+.011,d+.056,IRON)

def arcade(h,p,z,high,n,mat=STONE,horseshoe=False,open_back=False):
    l,r,f,b=p
    face=edges(p)[0]
    depth=b-f
    span=(r-l)/n
    spring=high-(.98 if horseshoe else .68)
    size=(24,12,8)[h.lod]
    for i in range(n):
        u=(i+.5)*span
        radius=span*.354
        base=z+.06
        if horseshoe:
            angles=[math.radians(-20+220*j/size) for j in range(size+1)]
            arch=[(u+radius*math.cos(q),spring+.88*math.sin(q)) for q in angles][::-1]
        else:
            arch=[(u-radius*math.cos(math.pi*j/size),spring+.51*math.sin(math.pi*j/size))
                  for j in range(size+1)]
        left,right=arch[0][0],arch[-1][0]
        pier_l,pier_r=i*span+.024,(i+1)*span-.024
        # Open lower arcade. The shared spandrels and piers frame actual air.
        for a,bx in ((pier_l,left-.004),(right+.004,pier_r)):
            block(h.body,face,a,bx,base,high,-depth,-.015,mat)
        arch=sorted(arch) if horseshoe else arch
        shape=[(a,z) for a,z in arch if left-.001<=a<=right+.001]
        g.relief(h.body,face,[*shape,(right,high-.012),(left,high-.012)],-depth+.004,-.021,mat)
        if h.lod<2:
            segments=(8 if horseshoe else 6)
            start=-math.radians(28) if horseshoe else 0
            total=math.pi-2*start
            for j in range(segments):
                aa=start+total*(j+.05)/segments
                bb=start+total*(j+.95)/segments
                ring=[]
                for q,rr,rise in ((aa,radius,.79 if horseshoe else .51),(bb,radius,.79 if horseshoe else .51),
                                  (bb,radius+.17,.97 if horseshoe else .69),(aa,radius+.17,.97 if horseshoe else .69)):
                    ring.append((u-rr*math.cos(q),spring+rise*math.sin(q)+(.16 if horseshoe else 0)))
                g.relief(h.body,face,ring,-.011,.14,("=Brick085" if j%2==0 else "Cream") if horseshoe else STONE)
    if not open_back:
        slab(h,(l+.01,r-.01,f-.07,b+.01),high+.012,high+.22,STONE)

def sign(h,a,face,z,u=None,w=None):
    u=face.length/2 if u is None else u
    w=min(face.length*.72,4.1) if w is None else w
    block(h.body,face,u-w/2-.06,u+w/2+.06,z-.26,z+.26,.19,.232,IRON)
    g.plate(h,face,u,z,w,.37,"Sign_"+a["design"],.240)

def yard(h,p):
    return  # R24: no grounds, water or boats
    surface(h,p,.027,"YardSetts")

def garden(h,p):
    return  # R24: no grounds, water or boats
    surface(h,p,.038,"RoofGreen")

def glass_panel(h,points,out):
    normal=Vector(out).normalized()*.0025
    h.body.polygon([Vector(v)+normal for v in points],normal,"CourtGlass")
    h.body.polygon([Vector(v)-normal for v in points],-normal,"CourtGlass")

def canal(h,p):
    return  # R24: no grounds, water or boats
    l,r,f,b=p
    surface(h,p,.032,WATER)
    for q in ((l-.27,l-.015,f,b),(r+.015,r+.27,f,b)):
        slab(h,q,.017,.17,STONE)

def boat(h,x,y):
    return  # R24: no grounds, water or boats
    points=[(x-.44,y-.75),(x+.44,y-.75),(x+.49,y+.53),(x+.25,y+1.31),
            (x,y+1.57),(x-.25,y+1.31),(x-.49,y+.53)]
    flat(h.body,points,.24,UP,"BrownBrick")
    for i,p in enumerate(points):
        q=points[(i+1)%len(points)]
        g.face(p,q).quad(h.body,0,math.dist(p,q),.052,.257,0,"TinOxide")
    for dy in (-.41,.34):
        slab(h,(x-.37,x+.37,y+dy,y+dy+.16),.27,.33,"BrownBrick")

def glass_roof(h,p,z,rise=1.05):
    l,r,f,b=p
    m=(l+r)/2
    for x in (l,r):
        glass_panel(h,[xyz(x,f,z),xyz(m,f,z+rise),xyz(m,b,z+rise),xyz(x,b,z)],UP)
    for y in [f+.06,(f+b)/2,b-.06] if h.lod==2 else [f+.08+(b-f-.16)*i/8 for i in range(9)]:
        for x in (l,r):
            beam(h,xyz(x,y,z+.026),xyz(m+(.095 if x==r else -.095),y,z+rise+.026),.061,IRON)
    if h.lod<2:
        for x in (l,m,r):
            top=z+rise+.079 if x==m else z+.079
            beam(h,xyz(x,f,top),xyz(x,b,top),.064,IRON)

def inhabited(h,a,w,d):
    p=(1.70,8.22,7.55,7.55+d*.49)
    wing=(9.24,14.28,15.1,15.1+d*.36)
    section(h,p,.05,7.70,2,"gable",3.44)
    section(h,wing,.061,6.26,2,"shed",2.0,front="entry",roof_mat="SlateBrown")
    wall=(1.11,10.26,4.45,6.55)
    section(h,wall,.072,4.41,2,"flat",0,front="windows",bays=3)
    f=edges(wall)[0]
    slab(h,(2.0,6.1,3.52,4.429),2.11,2.31,STONE)
    rail(h,f,.92,4.95,2.31,.84)
    for x in (10.65,14.12):
        post(h,x,4.58,.037,2.48,.36,STONE)
    rail(h,edges((10.83,13.95,4.68,4.92))[0],.03,3.05,.045,.05)
    return (11.32,12.67,p[2])

def water_villa(h,a,w,d):
    p=(3.4,20.6,11.05,11.05+d*.43)
    c=w*.50
    canal(h,(c-2.1,c+2.1,3.0,d-4.4))
    for l,r in ((3.6,c-2.34),(c+2.34,20.4)):
        slab(h,(l,r,p[2]+.03,p[3]-.03),.045,2.72,STONE)
    arcade(h,(c-2.31,c+2.31,p[2]+.05,p[2]+.64),.11,2.61,1,STONE)
    arcade(h,(c-2.31,c+2.31,p[3]-.65,p[3]-.061),.11,2.61,1,STONE)
    h.compact_trim=True
    section(h,p,2.86,9.11,2,"hip",3.45,over=.25)
    h.compact_trim=False
    slab(h,(c-1.13,c+1.13,6.15,p[2]-.006),2.58,2.84,STONE)
    steps(h,c,6.14,2.63,9,2.2,3.02)
    for x in (c-1.05,c+1.05):
        face=g.face((x,6.21),(x,p[2]-.09))
        rail(h,face,.02,face.length-.03,2.84,.015)
    return (c-.7,c+.7,3.08)

def plantation(h,a,w,d):
    q=(2.9,21.1,8.1,8.1+d*.45)
    l,r,f,b=q
    p=(l+2.16,r-2.16,f+2.50,b-2.16)
    for x in ((p[0]+.65,p[1]-.65) if h.lod==2 else (p[0]+.65,(p[0]+p[1])/2,p[1]-.65)):
        for y in (p[2]+.68,(p[2]+p[3])/2,p[3]-.68):
            post(h,x,y,.036,2.83,.64,BRICK)
    slab(h,q,2.87,3.12,"BrownBrick")
    section(h,p,3.14,6.84,1,None,front="entry")
    cover(h,(l-.34,r+.34,f-.38,b+.34),7.00,"hip",3.20,h.roof)
    for face in edges(q):
        for x,y in detail.divide(.11,face.length-.11,3.16 if h.lod==0 else 4.9 if h.lod==1 else 9.5):
            loc=face.point(x,0,-.24)
            round_wall(h,loc.x+nb.W/2,loc.y+12,.114,3.16,6.98,STONE,(24,12,8)[h.lod])
            if h.lod==0:
                for z in (3.19,3.44,6.65):
                    round_wall(h,loc.x+nb.W/2,loc.y+12,.177,z,z+.10,STONE,(24,12,8)[h.lod])
        if h.lod==2:
            continue
        if abs(face.length-(r-l))<.001 and face.out.y<0:
            for x,y in ((.11,face.length*.42),(face.length*.58,face.length-.12)):
                rail(h,face,x,y,3.13,.002)
        else:
            rail(h,face,.10,face.length-.10,3.13,.012)
    steps(h,w/2,f-.012,3.04,11,2.75,3.26)
    return (w/2-.80,w/2+.80,f-3.27)

def normandy(h,a,w,d):
    p=(2.17,13.33,7.7,7.7+d*.407)
    l,r,f,b=p
    section(h,p,.035,6.63,2,"gable",6.0,roof_mat="TinOxide",over=.41)
    face=edges((l-.38,r+.38,f-.418,b))[0]
    if h.lod<2:
        top=6.63+5.72
        for frac in (.18,.31,.50,.69,.82):
            x=face.length*frac
            ht=6.63+5.72*(1-abs(frac-.5)*2)
            block(h.body,face,x-.082,x+.082,6.68,ht-.13,.015,.12,"BrownBrick")
        for frac in (.27,.73):
            x=face.length*frac
            beam(h,face.point(x,6.78,.11),face.point(face.length*.5+(-.13 if frac<.5 else .13),top-.71,.11),.137,"BrownBrick")
        block(h.body,face,.12,face.length-.12,6.69,6.87,.021,.13,"BrownBrick")
    glass_p=(2.31,13.18,5.19,7.52)
    front=edges(glass_p)[0]
    glass_panel(h,[front.point(.10,.37,0),front.point(front.length-.10,.37,0),
                   front.point(front.length-.10,2.96,0),front.point(.10,2.96,0)],front.out)
    slab(h,glass_p,.049,.36,STONE)
    mid=front.length/2
    for x in (mid-.68,mid,mid+.68):
        block(h.body,front,x-.041,x+.041,.551,2.661,.084,.138,"BrownBrick")
    block(h.body,front,mid-.72,mid+.72,2.67,2.77,.086,.143,"BrownBrick")
    block(h.body,front,mid-.68,mid+.68,.38,.54,.093,.139,"BrownBrick")
    for x in range(9 if h.lod<2 else 4):
        u=.075+(front.length-.15)*x/(8 if h.lod<2 else 3)
        block(h.body,front,u-.045,u+.045,.37,3.04,.007,.083,IRON)
    cover(h,glass_p,3.06,"shed",1.08,"TinGreen")
    return (7.05,8.78,5.15)

def moorish(h,a,w,d):
    p=(1.76,14.24,9.1,9.1+d*.399)
    section(h,p,.075,8.12,2,"flat",front="entry")
    arcade(h,(1.83,14.17,6.30,8.81),.10,3.23,3,horseshoe=True)
    slab(h,(1.62,14.38,6.18,8.89),3.47,3.73,"TinGreen","TinFlat")
    f=edges(p)[0]
    for i in range(12 if h.lod==0 else 6):
        w0=(f.length-.24)/(12 if h.lod==0 else 6)
        block(h.body,f,.12+i*w0,.12+(i+1)*w0-.016,7.43,7.78,.15,.198,"TinGreen" if i%2==0 else "Cream")
    q=(5.53,10.47,10.77,15.41)
    for x in (q[0]+.19,q[1]-.19):
        for y in (q[2]+.19,q[3]-.19):
            round_wall(h,x,y,.112,8.37,10.35,STONE,(24,12,8)[h.lod])
    cover(h,q,10.39,"hip",1.41,"TinGreen")
    return (7.23,8.77,6.13)

def palladian(h,a,w,d):
    p=(6.61,17.39,9.71,9.71+d*.435)
    side=1.35+d*.28
    for q in ((1.38,5.78,11.51,11.51+side),(18.22,22.62,11.51,11.51+side)):
        section(h,q,.052,4.55,1,"hip",1.68,front="windows")
    section(h,p,.078,8.23,2,"cross",2.52,front="entry")
    q=(6.47,17.53,6.76,9.59)
    face=edges(q)[0]
    for x in (7.18,10.4,13.6,16.82):
        post(h,x,7.0,.29,.77,.58,STONE)
        round_wall(h,x,7.0,.203,.79,6.83,STONE,(24,12,8)[h.lod])
        post(h,x,7.0,6.85,7.18,.55,STONE)
    slab(h,q,7.23,7.61,STONE)
    cover(h,q,7.64,"gable",2.27,"SlateDark")
    g.relief(h.body,face,[(.16,7.70),(face.length-.16,7.70),(face.length*.5,9.72)],.014,.155,STONE)
    slab(h,(6.66,17.34,6.74,9.63),.044,.28,STONE)
    steps(h,w/2,6.72,.275,3,4.45,1.08)
    return (w/2-.82,w/2+.82,5.61)

def tennis(h,a,w,d):
    p=(2.22,11.62,7.11,7.11+d*.305)
    q=(13.00,21.75,11.8,11.8+d*.538)
    section(h,p,.043,6.45,2,"hip",2.07)
    section(h,q,.069,7.65,2,"gable",4.58,front="windows",roof_mat="TinOxide")
    sign(h,a,edges(q)[0],3.89)
    f=edges(q)[1]
    if h.lod<2:
        for l,r in detail.divide(.44,f.length-.40,2.24):
            block(h.body,f,l+.02,l+.26,3.95,7.32,.08,.20,STONE)
    return (6.1,7.77,p[2])

def lookout(h,a,w,d):
    p=(1.82,14.18,8.25,8.25+d*.429)
    section(h,p,.048,7.1,2,"hip",2.17)
    q=(4.19,11.81,11.12,17.26)
    slab(h,q,7.15,9.61,STONE)
    for x in (q[0]+.21,(q[0]+q[1])/2,q[1]-.21):
        for y in (q[2]+.22,q[3]-.22):
            post(h,x,y,9.66,11.46,.23,STONE)
    for face in edges(q):
        rail(h,face,.31,face.length-.31,9.64,.017)
    cover(h,q,11.52,"hip",1.54,h.roof)
    return (7.17,8.83,p[2])

# ---- R24 new Z1B families (Claude, 2026-11-13): built to the curb; fill_lot builds the rest of the lot ----
def two_pavilions(h,a,w,d):
    """Hôtel des Deux Pavillons: two tall stone corner pavilions with the mansard corps de logis between."""
    for l,r in ((.3,6.6),(w-6.6,w-.3)):
        section(h,(l,r,.3,10.3),.05,10.6,3,"hip",2.6,mat=STONE,front="windows")
    section(h,(6.606,w-6.606,.3,13.3),.06,8.2,2,"mansard",3.0,front="entry",omit=(1,3))
    return (w/2-.8,w/2+.8,.3)

def loggia_house(h,a,w,d):
    """Hôtel de la Loggia: two storeys, then a top-floor loggia of four stone arches under one broad hipped roof."""
    p=(.3,w-.3,.3,13.3)
    section(h,p,.05,7.4,2,None,front="entry")
    slab(h,p,7.404,7.6,STONE,"TinFlat")
    section(h,(.3,w-.3,2.6,13.3),7.61,10.6,1,None,front="windows")
    for l,r in ((.3,.62),(w-.62,w-.3)):
        slab(h,(l,r,.3,2.594),7.61,10.6,STONE)
    arcade(h,(.626,w-.626,.3,2.594),7.6,10.6,4,STONE,open_back=True)
    cover(h,(.3,w-.3,.3,13.3),10.61,"hip",2.3,h.roof)
    return (w/2-.8,w/2+.8,.3)

def tall_mansard(h,a,w,d):
    """Hôtel à la Mansarde: a tall three-storey town palace under a deep slate mansard."""
    keep=h.estate;h.estate=False      # town-palace lighting: some lit rooms on every floor (LOD1 needs lit glass)
    section(h,(.3,w-.3,.3,12.8),.05,10.4,3,"mansard",3.6,front="entry")
    h.estate=keep
    return (w/2-.8,w/2+.8,.3)

def square_belvedere(h,a,w,d):
    """Villa au Belvédère Carré: a long two-storey villa with a broad, low square belvedere room on the roof."""
    section(h,(.3,w-.3,.3,12.3),.05,7.6,2,"hip",2.8,front="entry")
    section(h,(w/2-3.2,w/2+3.2,3.1,9.5),7.66,10.9,1,"hip",1.3,mat=STONE,front="windows")
    return (w/2-.8,w/2+.8,.3)
