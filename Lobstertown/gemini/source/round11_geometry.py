"""Fifteen residential forms. Roofs and street-facing features vary by family."""
import math
from mathutils import Vector
from house_parts import (core,kit,nb,face,flat,rectangle,xyz,box,block,UP,DOWN,BRICK,STONE,
    IRON,WOOD,edges,ground,roof,hip,flat_roof,wood_beam,plank,plaque,wall,pavers,leaf,
    curve_step,round_wall,thin_glass)
import round5_geometry as g
from tenement_details import beam
import detail_mesh as detail

def split(h,a):
    l,r,f,b=a["walls"]
    q,s=a["left_end"],a["right_start"]
    left=(l,q,f,b)
    right=(s,r,f+.14,b+.08)
    e=a["eave_m"]
    lf=wall(h,a,left,.014,e,omit=(1,),sign=True)
    rf=wall(h,a,right,.014,e-.65,omit=(3,))
    for f0,key,x0 in ((lf,"west",l),(rf,"east",s)):
        ent=a["entrances"][key]
        x=ent["position_lot_m"][0]-x0+.86
        block(h.body,f0,x-.13,x+.13,1.37,1.57,.015,.087,STONE)
        g.plate(h,f0,x,1.47,.21,.155,"Address"+ent["address_number"],.095)
    roof(h,left,e,2.87,a["roof_tile"],.47)
    roof(h,right,e-.65,2.01,"TinOxide" if a["colourway"]=="B" else a["roof_tile"],.54)
    # The rear link meets both side walls. The two rooflines remain separated over the court.
    link=(q,s,b-1.65,b-.013)
    box(h.body,*link,.023,2.88,BRICK,"TinFlat")
    pavers(h,(q+.27,s-.28,f-.10,b-1.69))
    if h.lod<2:
        for x in (q+.34,s-.88):
            box(h.body,x,x+.55,f+.11,b-1.97,.031,.36,"Dressed","RoofGreen")
        f0=face((q+.05,f-.45),(s-.05,f-.45))
        for u in (.13,f0.length-.13):
            block(h.body,f0,u-.075,u+.075,.037,.88,.03,.17,STONE)

def dovecote(h,a):
    p=a["walls"]
    l,r,f,b=p
    z=a["eave_m"]
    wall(h,a,p,.014,z,sign=True)
    hip(h,p,z,1.86,a["roof_tile"])
    # Wide, short tower anchored at the garden end of the house.
    x0,x1,y0,y1=r-4.71,r-.45,b-4.46,b-.24
    top=z+2.49
    box(h.body,x0,x1,y0,y1,z-.07,top,BRICK)
    box(h.body,x0-.18,x1+.18,y0-.18,y1+.18,top-.022,top+.12,STONE)
    hip(h,(x0-.28,x1+.28,y0-.28,y1+.28),top+.12,1.37,a["roof_tile"])
    if h.lod<2:
        for f0 in edges((x0,x1,y0,y1)):
            for k in range(3):
                u=f0.length*(k+1)/4
                block(h.body,f0,u-.19,u+.19,top-.69,top-.37,.012,.065,"Black")
                block(h.body,f0,u-.30,u+.30,top-.77,top-.69,.025,.225,STONE)

def colombages(h,a):
    l,r,f,b=a["walls"]
    e=a["eave_m"]
    base=(l,r,f+.60,b)
    upper=(l,r,f,b)
    wall(h,a,base,.014,3.14,1,trim=False,sign=True)
    front=wall(h,a,upper,3.14,e,1,omit=(1,3),trim=False)
    rx=roof(h,upper,e,3.68,a["roof_tile"],.50)
    # Raised timber stays out of the window apertures.
    mat="BrownBrick"
    plank(h,front,.018,front.length-.018,3.15,3.34,.14,mat)
    plank(h,front,.023,front.length-.023,e-.25,e-.096,.128,mat)
    for u in (.18,front.length/3,front.length*2/3,front.length-.18):
        plank(h,front,u-.074,u+.074,3.35,e-.262,.108,mat)
    if h.lod<2:
        for side in (.24,front.length-.24):
            s=1 if side<1 else -1
            wood_beam(h,front,(side,3.43),(side+s*.72,4.73),.13,.073,mat)
        for flank in edges(upper)[1:]:
            for u in (.27,flank.length*.5,flank.length-.27):
                plank(h,flank,u-.067,u+.067,3.34,e-.23,.092,mat)
    for i,u in enumerate((.26,front.length-.26)):
        beam(h,front.point(u,e+.09,.105),front.point(front.length/2+(-.17,.17)[i],e+3.50,.105),.19,WOOD)
    if h.lod<2:
        for frac in (.23,.38,.5,.62,.77):
            u=front.length*frac
            t=e+3.63*(1-abs(frac-.5)*2)
            plank(h,front,u-.055,u+.055,e+.04,t-.055,.092,mat)

def studio(h,a):
    p=a["walls"]
    l,r,f,b=p
    e=a["eave_m"]
    ff=wall(h,a,p,.014,e,sign=True,front_studio=True)
    top=e+4.18
    ridge=roof(h,p,e,top-e,a["roof_tile"],.272,open_front=True)
    uu=r-l
    peak=ridge-l
    m=h.body
    u,v=uu*.452,uu*.841
    low=e+.12
    zt=lambda x:top-(top-e)*(x-peak)/(uu-peak)
    tl,tr=zt(u)-.19,zt(v)-.19
    for q in (((0,e),(peak,top),(u,zt(u)),(u,e)),
              ((v,e),(v,zt(v)),(uu,e)),((u,e),(v,e),(v,low),(u,low)),
              ((u,tl),(v,tr),(v,zt(v)),(u,zt(u)))):
        m.polygon([ff.point(x,z,0) for x,z in q],ff.out,BRICK)
    corners=((u,low),(v,low),(v,tr),(u,tl))
    m.polygon([ff.point(x,z,-.365) for x,z in corners],ff.out,"GreyBlue")
    for (x,z),(y,t) in zip(corners,corners[1:]+corners[:1]):
        inward=-ff.tangent*(t-z)+UP*(y-x)
        m.polygon([ff.point(x,z,0),ff.point(y,t,0),ff.point(y,t,-.365),ff.point(x,z,-.365)],inward,IRON)
    for j in range(1,5 if h.lod==0 else 4 if h.lod==1 else 3):
        n=5 if h.lod==0 else 4 if h.lod==1 else 3
        x=u+(v-u)*j/n
        block(m,ff,x-.033,x+.033,low+.005,zt(x)-.207,-.356,-.288,IRON)
    if h.lod<2:
        beam(h,ff.point(u+.026,low+.64,-.283),ff.point(v-.026,low+.64,-.283),.065,IRON)

def stair_curve(h,a):
    m=h.body
    x,f,_=a["entrances"]["front"]["position_lot_m"]
    n=(10,7,4)[h.lod]
    def path(t):
        return x+2.02*(1-t)**1.43,f-3.28+2.68*t
    z=lambda t:.10+1.40*t
    for j in range(n):
        t0,t1=j/n,(j+1)/n
        x0,y0=path(t0+.003)
        x1,y1=path(t1-.003)
        poly=[(x0-.69,y0),(x0+.69,y0),(x1+.69,y1),(x1-.69,y1)]
        curve_step(h,poly,z(t1)-.095,z(t1),IRON)
    box(m,x-.73,x+.73,f-.606,f-.012,1.402,1.50,STONE)
    for side in (-1,1):
        for j in range(n):
            t0,t1=j/n,(j+1)/n
            x0,y0=path(t0)
            x1,y1=path(t1)
            beam(h,xyz(x0+side*.64,y0,z(t0)+.93),xyz(x1+side*.64,y1,z(t1)+.93),.061,"Iron")
            if h.lod<2:
                beam(h,xyz(x0+side*.64,y0,z(t0)-.018),xyz(x0+side*.64,y0,z(t0)+.90),.039,"Iron")

def raised(h,a):
    p=a["walls"]
    l,r,f,b=p
    e=a["eave_m"]
    ff=wall(h,a,p,.014,e,sign=False,staff_stairs=False)
    plaque(h,a,ff,4.09,ff.length*.71)
    flat_roof(h,p,e,.29)
    stair_curve(h,a)
    if h.lod<2:
        for x in (l+.75,r-2.44):
            box(h.body,x,x+1.61,f-.68,f-.11,.029,.119,"Dressed")
            for u in (x,x+1.53):
                box(h.body,u,u+.081,f-.69,f-.102,.121,.26,STONE)

def belvedere(h,a):
    p=a["walls"]
    l,r,f,b=p
    z=a["eave_m"]
    wall(h,a,p,.014,z,sign=True)
    flat_roof(h,p,z)
    m=h.body
    for y in (f+.18,b-.40):
        box(m,l+.15,r-.15,y,y+.21,z+.21,z+.66,BRICK)
    for x in (l+.14,r-.38):
        box(m,x,x+.21,f+.41,b-.42,z+.221,z+.62,BRICK)
    # A low enclosed stair head gives the open terrace a believable way up.
    box(m,r-3.33,r-.58,b-3.33,b-.54,z+.194,z+2.31,BRICK,"SlateDark")
    x0,x1=l+.85,r-3.93
    y0,y1=f+1.12,min(b-1.53,f+5.13)
    for x in (x0,x1):
        for y in (y0,y1):
            box(m,x-.07,x+.07,y-.07,y+.07,z+.214,z+2.37,IRON)
        box(m,x-.08,x+.08,y0-.11,y1+.11,z+2.35,z+2.47,IRON)
    for i in range((6,5,3)[h.lod]):
        n=(6,5,3)[h.lod]
        y=y0+(y1-y0)*i/(n-1)
        box(m,x0-.12,x1+.12,y-.054,y+.054,z+2.478,z+2.564,IRON)
    if h.lod<2:
        for j in range(5 if h.lod==0 else 3):
            x=x0+.27+j*(x1-x0-.54)/(4 if h.lod==0 else 2)
            detail.ivy(h,x,y0+.18+(j%2)*.29,z+2.546,.49)
        for x in (x0,x1):
            box(m,x-.20,x+.20,y0-.23,y0+.24,z+.215,z+.68,STONE,"RoofGreen")

def greenhouse(h,a):
    p=a["walls"]
    l,r,f,b=p
    e=a["eave_m"]
    wall(h,a,p,.014,e,omit=(1,),sign=True)
    hip(h,p,e,2.08,a["roof_tile"])
    x=r+a["greenhouse_width"]
    y=f+(b-f)*.24
    u=y+(b-f)*.67
    m=h.body
    box(m,r+.015,x,y,u,.018,.54,STONE)
    low,high=2.65,3.91
    n=max(3,round((u-y)/.96)) if h.lod==0 else max(3,round((u-y)/1.46)) if h.lod==1 else 3
    for j in range(n):
        y0=y+(u-y)*j/n
        y1=y+(u-y)*(j+1)/n
        thin_glass(m,[xyz(x,y0,.54),xyz(x,y1,.54),xyz(x,y1,low),xyz(x,y0,low)],(1,0,0))
        thin_glass(m,[xyz(r,y0,high),xyz(x,y0,low),xyz(x,y1,low),xyz(r,y1,high)],UP)
        if h.lod<2:
            box(m,x-.051,x+.051,y0-.03,y0+.03,.51,low+.04,IRON)
            beam(h,xyz(r+.005,y0,high+.042),xyz(x+.018,y0,low+.04),.062,IRON)
    for yy,side in ((y,-1),(u,1)):
        for j in range(3):
            x0=r+(x-r)*j/3
            x1=r+(x-r)*(j+1)/3
            top=lambda v:high+(low-high)*(v-r)/(x-r)
            thin_glass(m,[xyz(x0,yy,.54),xyz(x1,yy,.54),xyz(x1,yy,top(x1)),xyz(x0,yy,top(x0))],(0,side,0))
            box(m,x1-.043,x1+.043,yy-.035,yy+.035,.506,top(x1)+.02,IRON)
    box(m,x-.065,x+.062,y-.04,u+.04,low-.06,low+.065,IRON)
    if h.lod<2:
        box(m,x-.056,x+.046,y-.016,u+.016,1.36,1.42,IRON)
    # The green raised bed follows the greenhouse wall so planting is legible in plan.
    box(m,x+.075,x+.66,y+.14,u-.14,.028,.43,"Dressed","RoofGreen")
    if h.lod==0:
        for j in range(n):
            y0=y+(u-y)*(j+.5)/n
            detail.ivy(h,x+.29,y0,.43,.35)

def camelback(h,a):
    l,r,f,b=a["walls"]
    e=a["eave_m"]
    y=f+a["porch_depth"]
    mid=f+(b-f)*.64
    wall(h,a,(l,r,y,b),.014,e,1,sign=True)
    # Shared low gable in front, taller rear gable over the camelback addition.
    roof(h,(l,r,f,mid),e,1.84,a["roof_tile"])
    z=e+2.95
    for i,fx in enumerate(edges((l,r,mid,b))):
        centers=(.28,.72) if i in (0,2) else (.53,)
        if h.lod==2:centers=(.69,) if i==0 else ()
        bot=e+1.97 if i==0 else e+.66
        windows=[(fx.length*t,1.14,bot,z-.31,.08,False,False) for t in centers]
        h.quiet_panes={w[0] for w in windows}
        h.slim_shaft=True
        g.row(h,fx,e,z,BRICK,windows)
        h.slim_shaft=False
        h.quiet_panes=()
    roof(h,(l,r,mid,b),z,2.12,a["roof_tile"],.54)
    m=h.body
    box(m,l+.12,r-.12,f+.075,y+.007,.033,.134,"Deck")
    for x in (l+.27,(l+r)*.5,r-.27):
        if h.lod==0:
            rings=[]
            for z0,rad in ((.136,.10),(.30,.098),(.42,.071),(.62,.074),(.82,.101),
                           (1.04,.080),(e-.66,.065),(e-.48,.083),(e-.28,.108),(e,.108)):
                rings.append([xyz(x+rad*math.cos(j*math.tau/8),f+.289+rad*math.sin(j*math.tau/8),z0)
                              for j in range(8)])
            m.polygon(rings[0],DOWN,WOOD)
            for lower,upper in zip(rings,rings[1:]):
                kit.ring_surfaces(m,lower,upper,WOOD)
            m.polygon(rings[-1],UP,WOOD)
        else:
            box(m,x-.10,x+.10,f+.19,f+.39,.136,e,WOOD)
        if h.lod<2:
            box(m,x-.18,x+.18,f+.116,f+.463,e-.41,e-.27,STONE)
            for s in (-1,1):
                if l+.2<x+s*.35<r-.2:
                    beam(h,xyz(x+s*.082,f+.276,e-.54),xyz(x+s*.34,f+.276,e-.10),.075,WOOD)
    if h.lod<2:
        for x in (l+.30,r-2.01):
            for j in range(5):
                u=x+.37*j
                box(m,u-.023,u+.023,f+.21,f+.26,.15,1.02,WOOD)
            box(m,x-.045,x+1.53,f+.201,f+.291,1.025,1.095,WOOD)

def court(h,a):
    l,r,f,b=a["walls"]
    z=a["eave_m"]
    p=(l,r,f,b)
    q=(r,a["wing"],b-a["wing_depth"],b)
    wall(h,a,p,.014,z,omit=(1,),sign=True)
    wall(h,a,q,.021,z-.68,1,omit=(0,3))
    hip(h,p,z,2.35,a["roof_tile"])
    hip(h,q,z-.68,1.49,a["roof_tile"])
    pavers(h,(r+.13,a["wing"]-.14,f+.44,b-a["wing_depth"]-.075))
    m=h.body
    gy=f+.21
    for j,x0 in enumerate((r+.35,a["wing"]-.36)):
        box(m,x0-.135,x0+.135,gy-.14,gy+.14,.028,.96,STONE)
        sign=1 if j==0 else -1
        end=x0+sign*1.02
        ll,rr=sorted((x0+sign*.12,end))
        for z0 in (.25,.74):
            box(m,ll,rr,gy-.036,gy+.036,z0,z0+.048,IRON)
        if h.lod<2:
            for k in range(1,5):
                xx=x0+sign*(.19+k*.182)
                box(m,xx-.022,xx+.022,gy-.022,gy+.022,.259,.81,IRON)
    x=(r+a["wing"])*.5
    y=f+2.55
    round_wall(h,x,y,.68,.034,.73,STONE,n=(24,12,8)[h.lod],inner=.46)
    if h.lod<2:
        round_wall(h,x,y,.46,.094,.155,"RaceWater",n=(24,12,8)[h.lod])
    front=face((x-.59,y),(x+.59,y))
    n=(10,8,5)[h.lod]
    top=[(1.18*i/n,.71+1.19*math.sin(math.pi*i/n)**.62) for i in range(n+1)]
    inner=[(.061+1.058*i/n,.695+1.13*math.sin(math.pi*i/n)**.62) for i in range(n+1)]
    g.relief(m,front,top+inner[::-1],-.027,.027,IRON)
    if h.lod<2:
        beam(h,xyz(x,y,.96),xyz(x,y,1.81),.029,"Iron")

def clock(h,a):
    p=a["walls"]
    l,r,f,b=p
    z=a["eave_m"]
    ff=wall(h,a,p,.014,z,sign=True)
    rise=4.14
    roof(h,p,z,rise,a["roof_tile"])
    m=h.body
    u=ff.length*.5
    radius=1.14
    height=z+1.69
    n=(24,12,8)[h.lod]
    poly=[(u+radius*math.cos(i*math.tau/n),height+radius*math.sin(i*math.tau/n)) for i in range(n)]
    g.relief(m,ff,poly,.019,.15,STONE)
    layout=nb.LAYOUT["lods"][m.lodkey]["MatteDial"]["uv"]
    u0,v0,u1,v1=layout
    m._add([ff.point(x,y,.166) for x,y in poly],[(u0+(u1-u0)*(.5+(x-u)/radius*.475),
                                                v0+(v1-v0)*(.5+(y-height)/radius*.475)) for x,y in poly])

def solar(h,a):
    p=a["walls"]
    l,r,f,b=p
    z=a["eave_m"]
    wall(h,a,p,.014,z,sign=True)
    g.caps(h,rectangle(*p),z,((0,0),(.93,2.28),(2.03,2.91)),"SolarSlate")
    m=h.body
    box(m,l+2.02,r-2.02,f+2.02,f+2.18,z+2.891,z+3.042,"CopperVent")
    for x in (l+2.26,r-2.27):
        dormer=(x-.51,x+.51,f-.08,f+1.13)
        front,*flanks=edges(dormer)
        floor,top=z+.39,z+1.67
        for flank in flanks:
            g.plane(m,flank,0,flank.length,floor,top,"CopperVent")
        flat(m,rectangle(*dormer),floor,DOWN,"CopperVent")
        box(m,x-.59,x+.59,f-.13,f+1.12,top-.014,top+.105,"CopperVent")
        h.quiet_panes={.51}
        h.skip_relief=True
        g.row(h,front,floor,top,"CopperVent",[(.51,.57,z+.89,z+1.47,.04,False,False)])
        h.quiet_panes=()
        h.skip_relief=False
    round_wall(h,r+.54,b-2.15,.44,.031,1.15,"CopperVent",n=(24,12,8)[h.lod])

def barge(h,a):
    p=a["walls"]
    l,r,f,b=p
    z=a["eave_m"]
    ff=wall(h,a,p,.014,z,sign=True)
    split_y=f+(b-f)*.57
    rise=max(3.06,(r-l)*.57*math.tan(math.radians(40.5)))
    roof(h,(l,r,f,split_y),z,rise,a["roof_tile"],.43,open_front=True)
    # The rear ridge turns parallel to the street.
    m=h.body
    ridge=split_y+(b-split_y)*.57
    for y in (split_y,b):
        m.polygon([xyz(l,y,z),xyz(r,y,z),xyz(r,ridge,z+2.13),xyz(l,ridge,z+2.13)],UP,a["roof_tile"])
    for x,s in ((l,-1),(r,1)):
        m.polygon([xyz(x,split_y,z),xyz(x,ridge,z+2.13),xyz(x,b,z)],(s,0,0),BRICK)
    u=ff.length*.43
    for i,x in enumerate((.12,ff.length-.12)):
        wood_beam(h,ff,(x,z+.09),(u+(-.17,.17)[i],z+rise-.14),.19,.133,WOOD)
    if h.lod<2:
        for x in (u-1.78,u-1.12,u-.46,u+.44,u+1.10,u+1.76):
            plank(h,ff,x-.083,x+.083,z+.11,z+.31,.105,WOOD)
    lo,hi=u-1.01,u+1.01
    block(m,ff,lo-.12,hi+.12,z-.13,z-.022,.034,.72,STONE)
    block(m,ff,lo,hi,z+.65,z+.72,.667,.741,"Iron")
    if h.lod<2:
        for j in range(6):
            x=lo+(hi-lo)*j/5
            block(m,ff,x-.02,x+.02,z+.002,z+.64,.686,.724,"Iron")
    left,right=u-.49,u+.49
    low,top=z+.082,z+1.76
    peak=z+rise
    h0=peak-rise*(u-left)/u
    h1=peak-rise*(right-u)/(ff.length-u)
    polygons=(((0,z),(left,z),(left,h0)),((right,z),(ff.length,z),(right,h1)),
              ((left,z),(right,z),(right,low),(left,low)),
              ((left,top),(right,top),(right,h1),(u,peak),(left,h0)))
    for points in polygons:
        m.polygon([ff.point(x,y,0) for x,y in points],ff.out,BRICK)
    h.quiet_panes={u}
    g.aperture(h,ff,(u,.98,low,top,.0,False,False),BRICK)
    h.quiet_panes=()


def pontet(h,a):
    l,r,f,b=a["walls"]
    z=a["eave_m"]
    p=(l,r,f,b)
    wall(h,a,p,.014,z,omit=(1,),sign=True)
    cut=b-2.36
    roof(h,(l,r,f,cut),z,2.41,a["roof_tile"],.51)
    hip(h,(l,r,cut,b),z,1.35,a["roof_tile"])
    x=a["passage_right"]
    y=max(f+4.17,b-4.60)
    q=(r,x,y,y+2.34)
    m=h.body
    bot=2.97
    flat(m,rectangle(*q),bot,DOWN,"ClapSage")
    roof(h,q,5.77,1.09,a["roof_tile"])
    for i,side in enumerate(edges(q)):
        if i in (0,2):
            mid=side.length*.5
            h.quiet_panes={mid}
            g.row(h,side,bot,5.77,"ClapSage",[(mid,1.43,3.57,5.04,.0,False,False)])
            h.quiet_panes=()
        else:
            g.plane(m,side,0,side.length,bot,5.77,"ClapSage")
    box(m,x+.029,x+.145,y+2.17,y+2.33,.029,3.03,WOOD)
    pavers(h,(r+.16,x-.04,f+.73,b+.32))

def through_porch(h,a):
    l,r,f,b=a["walls"]
    e=a["eave_m"]
    y=f+a["porch_depth"]
    p=(l,r-.86,y,b)
    # The gable spans an open porch. The side aisle stays open to the garden.
    wall(h,a,p,.014,e,omit=(1,),sign=True)
    roof(h,(l,r,f,b),e,2.88,a["roof_tile"],.45)
    m=h.body
    for x in (l+.24,r-.18):
        box(m,x-.14,x+.14,f+.23,f+.52,.028,e,BRICK)
        box(m,x-.20,x+.20,f+.169,f+.58,e-.49,e-.35,STONE)
    for side in edges((l,r,f,b)):
        if abs(side.point(0,0,0).y-nb.Y(f))<.0001 and side.out.y<-.9:
            block(m,side,.018,side.length-.018,e-.35,e,.011,.095,WOOD)
    box(m,l+.14,r-.21,f+.12,y-.025,.031,.119,"Deck")
    pavers(h,(r-.72,r-.16,y+.02,b+.33))

def spiral(h,a):
    p=a["walls"]
    wall(h,a,p,.014,a["eave_m"],sign=True,staff_stairs=False)
    flat_roof(h,p,a["eave_m"],.23)
    m=h.body
    x,f,z=a["entrances"]["upper"]["position_lot_m"]
    y=f-1.63
    # A full turn plus a quarter brings the stair to the upper landing.
    n=(26,16,9)[h.lod]
    angle=lambda k:-math.tau+k*(math.tau+math.pi/2)/n
    step=lambda k:.09+(z-.09)*k/n
    def at(r,ang):
        return x+r*math.cos(ang),y+r*math.sin(ang)
    round_wall(h,x,y,.082,.028,z+.055,"Iron",n=(24,12,8)[h.lod])
    for i in range(n):
        a0,a1=angle(i)+.005,angle(i+1)-.005
        q=[at(.09,a0),at(1.29,a0),at(1.29,a1),at(.09,a1)]
        curve_step(h,q,step(i+1)-.07,step(i+1),"Iron")
        p0,p1=at(1.24,angle(i)),at(1.24,angle(i+1))
        beam(h,xyz(*p0,step(i)+.92),xyz(*p1,step(i+1)+.92),.048,"Iron")
        if h.lod<2 and (i%2==0 or h.lod==0):
            beam(h,xyz(*p1,step(i+1)),xyz(*p1,step(i+1)+.893),.038,"Iron")
    box(m,x-.66,x+.66,f-.43,f-.006,z-.104,z-.006,"Iron")
    for s in (-1,1):
        box(m,x+s*.61-.025,x+s*.61+.025,f-.42,f-.063,z+.89,z+.95,"Iron")
    lower=a["entrances"]["lower"]["position_lot_m"]
    g.stair(h,edges(p)[0],lower[0]-p[0],1.15,.14)

BUILDERS={"split":split,"dovecote":dovecote,"jetty":colombages,"studio":studio,"raised":raised,
          "pergola":belvedere,"greenhouse":greenhouse,"camelback":camelback,"court":court,
          "clock":clock,"solar":solar,"barge":barge,"bridge":pontet,"porch":through_porch,"spiral":spiral}

def build(a,lod):
    core.setup(a,lod,0)
    nb.REMAP[BRICK]=a["wall_tile"]
    h=nb.House(lod)
    h.name=a["name"]
    h.deep_portal=False
    h.detail_grade=a.get("detail_grade",0)
    ground(h,a)
    BUILDERS[a["style"]](h,a)
    return h
