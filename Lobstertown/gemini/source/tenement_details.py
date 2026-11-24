"""Ironwork, wash lines, and lightweight roof details for the river tenements."""
import math
import round5_geometry as g
from mathutils import Vector

nb,kit,c=g.nb,g.kit,g.civic
box,block,face,flat,rectangle,relief,xyz=g.box,g.block,g.face,g.flat,g.rectangle,g.relief,g.xyz
UP,DOWN=g.UP,g.DOWN
IRON="TinGreen"

def beam(h,a,b,width,mat=IRON):
    a,b=Vector(a),Vector(b)
    axis=(b-a).normalized()
    ref=Vector((0,0,1)) if abs(axis.z)<.84 else Vector((1,0,0))
    u=axis.cross(ref).normalized()*width/2
    v=axis.cross(u).normalized()*width/2
    low=[a+i*u+j*v for i,j in ((-1,-1),(1,-1),(1,1),(-1,1))]
    high=[b+i*u+j*v for i,j in ((-1,-1),(1,-1),(1,1),(-1,1))]
    m=h.body
    m.polygon(low,-axis,mat)
    m.polygon(high,axis,mat)
    for i in range(4):
        j=(i+1)%4
        m.polygon([low[i],low[j],high[j],high[i]],(low[i]+low[j])/2-a,mat)

def deck(h,f,l,r,z,reach=.98,railing=True):
    m=h.body
    if r-l<.42:
        return
    block(m,f,l,r,z-.095,z-.012,.048,reach,IRON)
    if not railing:
        return
    block(m,f,l+.009,r-.011,z+.83,z+.899,reach-.06,reach+.018,IRON)
    if h.lod==2:
        return
    pitch=(.80 if reach==.91 else .61 if reach==1.04 else .51) if h.lod==0 else .96
    count=max(2,round((r-l)/pitch))
    for j in range(count+1):
        u=l+.034+(r-l-.068)*j/count
        block(m,f,u-.019,u+.019,z+.003,z+.824,reach-.049,reach-.015,IRON)
    if h.lod==0:
        for u in (l+.24,r-.24):
            beam(h,f.point(u,z-.54,.055),f.point(u,z-.11,reach-.12),.055)

def stair_run(h,f,l,r,low,hi,reach,reverse=False):
    m=h.body
    n=10 if h.lod==0 else 6 if h.lod==1 else 3
    for k in range(n):
        a=l+(r-l)*k/n
        b=l+(r-l)*(k+1)/n
        z=low+(hi-low)*(n-k-.5 if reverse else k+.5)/n
        block(m,f,a+.006,b-.006,z-.066,z-.006,reach-.47,reach+.006,IRON)
    u,v=(r,l) if reverse else (l,r)
    for d in (reach-.485,reach+.018):
        beam(h,f.point(u,low-.05,d),f.point(v,hi-.048,d),.049)
    beam(h,f.point(u,low+.77,reach+.038),f.point(v,hi+.77,reach+.038),.043)
    if h.lod<2:
        for j in range(5 if h.lod==0 else 3):
            t=(j+.29)/(5 if h.lod==0 else 3)
            U=u+(v-u)*t
            z=low+(hi-low)*t
            block(m,f,U-.018,U+.018,z+.01,z+.738,reach+.011,reach+.048,IRON)

def galleries(h,a,f,levels,side=False):
    l,r=.18,f.length-.18
    if side:
        r=min(r,10.28)
    reach=.91 if side else 1.04
    if h.lod==2:
        # Two wide rail lines and a roof edge retain the gallery silhouette at distance.
        for z in levels[:2]:
            deck(h,f,l,r,z,reach)
        return
    for i,z in enumerate(levels[:2] if side else levels):
        deck(h,f,l,r,z,reach)
        if side:
            continue
        low=levels[i-1] if i else .38
        start=l+.05 if i%2==0 else r-4.27
        stair_run(h,f,start,start+4.03,low,z,reach+.202,reverse=i%2==1)

def escapes(h,a,f,levels,side=False):
    if h.lod==2:
        # At distance the iron platforms remain distinct without individual treads.
        u=f.length*.49
        for z in levels[:2]:
            deck(h,f,u-1.20,u+1.20,z,.78)
        return
    groups=(f.length*.28,f.length*.72) if a["feature"]=="double" and not side else (f.length*.56 if side else f.length*.48,)
    for u in groups:
        for i,z in enumerate(levels):
            l,r=u-1.40,u+1.40
            deck(h,f,l,r,z,.88)
            if i==0:
                # The counterweighted bottom flight stops above the stoop.
                stair_run(h,f,l,r,1.02,z,.99,reverse=False)
            else:
                stair_run(h,f,l,r,levels[i-1],z,1.02+.022*i,reverse=i%2==1)

def washing(h,a):
    m=h.body
    _,_,_,b=a["walls"]
    d=a["lot"][1]*8
    x0,x1=2.24,13.81
    count=3 if d>=32 and a["family"] in {"A","D"} else 2
    for j in range(count):
        y=b+.62+(d-b-1.23)*j/(count-1)
        passage=a["feature"]=="passage"
        z=(2.34 if passage else 1.91)+(.042 if j%2 else 0)
        if h.lod==0:
            for x in (x0,x1):
                box(m,x-.034,x+.034,y-.035,y+.035,.034,z+.11,"Iron")
            for k in range(2+(j+int(a["lot"][1]))%3):
                x=x0+.66+k*2.27+(.43 if j%2 else 0)
                w=.59+.21*((k+j)%2)
                ht=.43+.12*((j+2*k)%3)
                mat=("Cream","GreyBlue","ClapSage","Oxblood")[(k+j)%4]
                if passage:
                    x=(3.17,5.02,10.21,12.13)[k]+.20*(j%2)
                box(m,x,x+w,y+.016,y+.039,z-ht,z+.019,mat)
        elif h.lod==1:
            for x in (x0,x1):
                box(m,x-.035,x+.035,y-.037,y+.037,.035,z+.095,"Iron")
            for x,mat in ((x0+1.15,"Cream"),(x0+(8.2 if passage else 5.74),"GreyBlue")):
                box(m,x,x+.82,y+.026,y+.052,z-.56,z+.015,mat)
        else:
            box(m,x0+3.08,x0+4.0,y+.014,y+.034,z-.50,z+.011,"Cream")
        box(m,x0,x1,y-.011,y+.011,z-.012,z+.010,IRON)

def party_chimneys(h,a,plan,e,peak):
    m=h.body
    l,r,f,b=a["walls"]
    x=r-.46
    for j,y in enumerate((f+(b-f)*.29,f+(b-f)*.73)):
        z=e-.076+j*.009
        top=peak+(.54 if a["family"] in {"A","C"} else -.18)+j*.11
        if top<z+.28:
            top=z+.30
        box(m,x-.30,x+.29,y-.42,y+.41,z,top,a["wall_tile"])
        box(m,x-.34,x+.33,y-.46,y+.46,top-.027,top+.16,"BrownBrick")
        if h.lod==0:
            box(m,x-.10,x+.10,y-.17,y+.15,top+.14,top+.45,"Chimney")

def roof_dormer(h,x,y,z,w,height,back=1):
    m=h.body
    f=face((x-w/2,y),(x+w/2,y)) if back>0 else face((x+w/2,y),(x-w/2,y))
    inner=y+back*.82
    top=z+height*.70
    base=z-.35
    walls=rectangle(x-w/2,x+w/2,min(y,inner),max(y,inner))
    flat(m,walls,base,DOWN,"PatchedLime")
    for a,b in zip(walls,walls[1:]+walls[:1]):
        if a[1]==b[1]==y:
            continue
        flank=face(a,b)
        flank.quad(m,0,flank.length,base,top,0,"PatchedLime")
    h.window_recess=.365
    g.row(h,f,base,top,"PatchedLime",[(w/2,w*.49,z+.08,z+height*.60,0,False,False)])
    p=rectangle(x-w*.59,x+w*.59,min(y,inner)-.08,max(y,inner)+.075)
    flat(m,p,top-.005,DOWN,g.SLATE)
    ridge=[xyz(x,p[0][1],z+height),xyz(x,p[2][1],z+height)]
    for i,(a,b) in enumerate(zip(p,p[1:]+p[:1])):
        lo=[xyz(*a,top),xyz(*b,top)]
        if i in (0,2):
            m.polygon([*lo,ridge[0 if i==0 else 1]],(0,-1 if i==0 else 1,0),"PatchedLime")
        else:
            m.polygon([*lo,*(ridge[::-1] if i==1 else ridge)],UP,g.SLATE)

def raised_gable(h,f,kind,e):
    m=h.body
    u=f.length*.5
    if kind=="steps":
        # One continuous stepped profile keeps the wall free of coplanar block seams.
        a,b=u-3.41,u+3.41
        shape=[(a,e-.32),(b,e-.32),(b,e+.56),(b-.73,e+.56),(b-.73,e+1.22),
               (b-1.53,e+1.22),(b-1.53,e+1.92),(b-2.39,e+1.92),(b-2.39,e+2.70),
               (u+.38,e+2.70),(u+.38,e+3.64),(u-.38,e+3.64),(u-.38,e+2.70),
               (a+2.39,e+2.70),(a+2.39,e+1.92),(a+1.53,e+1.92),(a+1.53,e+1.22),
               (a+.73,e+1.22),(a+.73,e+.56),(a,e+.56)]
        relief(m,f,shape,-.41,.092,"BrownBrick")
    elif kind=="clock":
        relief(m,f,[(u-3.54,e-.17),(u+3.54,e-.17),(u,e+2.60)],-.45,.103,"Dressed")
        r=.74
        z=e+.72
        pts=[(u+r*math.cos(j*math.tau/16),z+r*math.sin(j*math.tau/16)) for j in range(16)]
        l,b,R,t=nb.LAYOUT["lods"][m.lodkey]["MatteDial"]["uv"]
        m._add([f.point(x,y,.128) for x,y in pts],
               [(l+(R-l)*(.5+.5*(x-u)/r),b+(t-b)*(.5+.5*(y-z)/r)) for x,y in pts])
    else:
        relief(m,f,[(u-3.75,e-.22),(u+3.75,e-.22),(u,e+2.66)],-.35,.077,"BrownBrick")
