"""Apartment houses and distinct workers' housing types."""
from r12_geometry import (
    math, detail, g, nb, box, flat, xyz, rectangle, block, edges, round_wall, curve_step,
    beam, UP, DOWN, STONE, IRON, BRICK, WATER, slab, surface, post, steps, section,
    cover, rail, arcade, sign, yard, garden, canal, boat, glass_panel, glass_roof,
)

def apartments(h,a,w,d):
    typ=a["design"]
    p=(1.18,14.82,4.05,4.05+d*.64)
    l,r,f,b=p
    front=edges(p)[0]
    e=15.68 if typ=="ImmeubleBowWindows" else 15.0 if typ=="ImmeubleImprimeur" else 13.95
    h.plain_frames=True
    section(h,p,.05,e,4,None,omit=(0,))
    section(h,(2.19,13.80,5.85,b-1.11),e+.28,e+2.55,1,
            "mansard" if typ=="ImmeubleBowWindows" else "flat",1.41,front="windows")
    slab(h,(l-.09,r+.09,f-.105,b+.093),e+.017,e+.24,STONE,"TinFlat")
    z=.05
    top=e/4
    if typ=="ImmeubleImprimeur":
        # Three real recesses have iron shutter leaves set behind each arch.
        arcade(h,(l+.014,r-.014,f-.015,f+1.24),z,top-.39,3,BRICK,open_back=True)
        slab(h,(l+.008,r-.008,f+1.34,f+1.53),.051,top-.003,BRICK)
        for j in range(3):
            u=front.length*(j+.5)/3
            block(h.body,front,u-1.25,u+1.25,.13,2.61,-1.30,-1.24,"TinGreen" if j==1 else "Iron")
            if h.lod<2:
                for k in range(11):
                    y=.24+k*.208
                    block(h.body,front,u-1.18,u+1.18,y,y+.033,-1.23,-1.18,"TinGreen")
        sign(h,a,front,top-.19,w=7.1)
    else:
        c=front.length/2
        slots=[(u,1.25,.73,top-.54,.23,False,False) for u in (1.56,3.55,front.length-3.55,front.length-1.56)]
        slots.append((c,1.43,.13,2.56,.24,True,False))
        h.quiet_panes={s[0] for s in slots}
        h.finish_cornice=False
        g.row(h,front,z,top,BRICK,slots)
    for floor in range(1,4):
        low=e*floor/4
        high=e*(floor+1)/4
        if typ=="ImmeubleBowWindows":
            slots=[(front.length/2,1.29,low+.64,high-.43,.24,False,False)]
        elif typ=="ImmeubleJardinHiver":
            slots=[(u,1.36,low+.63,high-.47,.18,False,False) for u in (2.04,front.length-2.04)]
        else:
            slots=[(front.length*(i+.5)/4,1.51,low+.64,high-.44,.19,False,False) for i in range(4)]
        h.quiet_panes={s[0] for i,s in enumerate(slots) if (i+floor)%3}
        if h.lod==2 and floor==2:
            h.quiet_panes.discard(slots[0][0])
        h.finish_cornice=floor==3
        h.skip_relief=typ=="ImmeubleBowWindows"
        g.row(h,front,low,high,BRICK,slots)
        h.skip_relief=False
        if typ=="ImmeubleBowWindows" and (h.lod<2 or floor==1):
            for x in (l+3.24,r-3.24):
                oriel(h,x,f,low,e if h.lod==2 else high)
        if typ=="ImmeubleJardinHiver":
            conservatory(h,(w*.5-3.0,w*.5+3.0,f-1.79,f-.33),low,high,floor)
    if typ=="ImmeubleBowWindows" and h.lod==0:
        for x in (.36,front.length-.36):
            detail.bevel(h.body,front,x-.15,x+.15,top+.08,e-.28,.012,.115,BRICK)
        detail.bevel(h.body,front,.15,front.length-.15,e-.26,e-.13,.013,.282,STONE,shadow=True)
    if typ!="ImmeubleImprimeur":
        sign(h,a,front,top-.33)
    return (w*.5-.77,w*.5+.77,f-.08)

def oriel(h,x,y,z,t):
    n=(24,12,8)[h.lod]
    curve=[(x+1.63*math.cos(math.pi+math.pi*i/n),y-.29+1.33*math.sin(math.pi+math.pi*i/n))
           for i in range(n+1)]
    for k,(p,q) in enumerate(zip(curve,curve[1:])):
        f=g.face(p,q)
        f.quad(h.body,0,f.length,z+.088,z+.63,0,"TinGreen")
        f.quad(h.body,0,f.length,t-.56,t-.048,.003,"TinGreen")
        f.quad(h.body,0,f.length,z+.65,t-.57,-.005,"GreyBlue")
        if h.lod<2 and k%(3 if h.lod==0 else 4)==0:
            beam(h,f.point(.013,z+.63,.018),f.point(.013,t-.56,.018),.049,IRON)
        if h.lod==0 and k%2==0:
            f.quad(h.body,.003,f.length-.003,z+1.61,z+1.65,.016,IRON)
    flat(h.body,curve,t-.047,UP,"TinFlat")
    flat(h.body,curve,z+.086,DOWN,"TinGreen")
    for u,v in ((curve[-1],curve[0]),):
        f=g.face(u,v)
        f.quad(h.body,0,f.length,z+.085,t-.047,0,IRON)

def conservatory(h,p,z,t,floor):
    l,r,f,b=p
    slab(h,(l+.012,r-.012,f+.012,b-.012),z+.08,z+.26,STONE)
    if h.lod==2:
        face=edges(p)[0]
        face.quad(h.body,.01,face.length-.01,z+.29,t-.31,.002,"CourtGlass")
        return
    for k,face in enumerate(edges(p)):
        if k==2:
            continue
        # The lower band is open-backed so the planted ledge can be seen from street level.
        face.quad(h.body,.03,face.length-.03,z+1.02,t-.37,0,"CourtGlass")
        n=(9 if h.lod==0 else 5 if h.lod==1 else 3) if k==0 else 2
        for j in range(n):
            u=.046+(face.length-.092)*j/(n-1)
            block(h.body,face,u-.027,u+.027,z+.30,t-.30,.014,.072,IRON)
        block(h.body,face,.02,face.length-.02,z+.99,z+1.05,.017,.064,IRON)
    cover(h,(l-.012,r+.012,f-.012,b+.012),t-.316,"flat",0,"TinGreen")

def familistere(h,a,w,d):
    f,b=5.23,5.23+d*.57
    left,right=(1.20,5.25,f,b),(10.75,14.80,f+.37,b-.09)
    for wing,i in ((left,1),(right,3)):
        section(h,wing,.056,9.81,3,"gable",2.07,omit=(i,),front="entry")
        face=edges(wing)[i]
        for j in range(3):
            z=.14+3.2*j
            block(h.body,face,.06,face.length-.06,z-.049,z+.083,.031,.79,STONE)
            if h.lod<2:
                rail(h,face,.12,face.length-.12,z+.083,.67, .48 if h.lod==0 else .80)
            slots=[(face.length*(k+.5)/4,1.05,z+.62,z+2.63,.10,False,False) for k in range(4)] if h.lod==0 else []
            h.quiet_panes={s[0] for s in slots}
            h.finish_cornice=j==2
            g.row(h,face,z-.08,z+2.98,BRICK,slots)
            face.quad(h.body,0,face.length,z+2.98,9.81 if j==2 else z+3.12,0,BRICK)
    q=(5.88,10.12,f+.97,b-.48)
    glass_roof(h,q,8.89,1.36)
    for x in (6.03,9.97):
        for y in (q[2],(q[2]+q[3])/2,q[3]):
            post(h,x,y,.09,8.88,.105,IRON)
    return (6.99,9.01,f)

def beguinage(h,a,w,d):
    # R18d (the author): wider houses, and the bell gate spans the gap between the front pair instead of standing
    # free in front of them. The path runs straight through the arch and up the lane between the rows; every
    # door opens off that lane.
    f=4.22
    gl,gr=6.40,9.60
    deep=d*.21
    for j in range(2):
        y=f+j*(deep+.92)
        section(h,(1.16,gl,y,y+deep),.047,4.90-.15*j,2,"gable",2.22,side_entry=True)
        section(h,(gr,14.84,y,y+deep),.047,4.90-.15*j,2,"gable",2.22,side_entry=3)
    gate=(gl+.025,gr-.025,f,f+1.20)
    arcade(h,gate,.055,3.55,1,BRICK)
    cover(h,(gl+.035,gr-.035,f+.016,f+1.205),3.785,"gable",1.25,h.roof)
    face=edges(gate)[0]
    y=f+.60
    base=4.80
    slab(h,(7.30,8.70,y-.20,y+.30),3.90,base+.004,BRICK)   # brick plinth rising out of the roof, so the cote sits on it
    slab(h,(7.22,8.78,y-.24,y+.36),base,base+.16,STONE)
    for x in (7.37,8.63):
        post(h,x,y+.04,base+.18,base+1.02,.16,STONE)
    cover(h,(7.15,8.85,y-.27,y+.40),base+1.05,"gable",.76,h.roof)
    segments=(24,12,8)[h.lod]
    rings=[[xyz(8+radius*math.cos(i*math.tau/segments),y+.014+radius*math.sin(i*math.tau/segments),base+z)
            for i in range(segments)] for radius,z in ((.23,.37),(.167,.43),(.119,.71),(.081,.81))]
    h.body.polygon(rings[0],DOWN,"Mustard")
    for lo,hi in zip(rings,rings[1:]):
        g.kit.ring_surfaces(h.body,lo,hi,"Mustard")
    h.body.polygon(rings[-1],UP,"Mustard")
    return (7.27,8.73,f-.035)

def coron(h,a,w,d):
    l,r=3.17,10.16
    f=4.11
    unit=(d-8.4)/3
    for j in range(3):
        y=f+j*unit
        p=(l,r,y,y+unit-.72)
        section(h,p,.06+j*.009,5.29+j*.31,2,"cross",1.48,side_entry=True,bays=2)
        q=(r+.56,14.22,y+.52,y+unit-.96)
        if q[3]>q[2]+.4:
            yard(h,q)
            rail(h,edges(q)[0],.12,q[1]-q[0]-.07,.036,.016,.40)
    return (6.08,7.16,f-.035)

def couree(h,a,w,d):
    f=4.43
    p=(1.09,5.42,f,5.62+d*.59)
    q=(10.60,14.91,f+.42,5.21+d*.56)
    for wing in (p,q):
        section(h,wing,.053,6.61,2,"gable",2.40,side_entry=True)
    portal=(6.12,9.90,f+.26,f+3.05)
    arcade(h,portal,.053,2.65,1,BRICK)
    cover(h,(6.10,9.92,f+.20,f+3.10),2.93,"gable",1.91,h.roof)
    sign(h,a,edges(portal)[0],3.20)
    x,y=8.12,f+6.2
    round_wall(h,x,y,.15,.064,1.73,IRON,(24,12,8)[h.lod])
    beam(h,xyz(x-.02,y,1.59),xyz(x-.54,y,1.71),.076,IRON)
    beam(h,xyz(x-.03,y+.015,1.74),xyz(x+.58,y+.08,2.11),.055,IRON)
    slab(h,(x-.55,x+.55,y-.45,y+.45),.045,.16,STONE)
    return (7.33,8.67,f+.15)

def coursives(h,a,w,d):
    p=(1.44,14.55,6.72,6.72+d*.55)
    section(h,p,.07,12.46,4,"shed",1.85,front="gallery")
    for i in range(3):
        z=3.09+i*3.08
        q=(1.75,14.19,p[2]-1.84,p[2]-.025)
        slab(h,q,z-.17,z-.028,"TinGreen")
        f=edges(q)[0]
        rail(h,f,.1,f.length-.09,z,.011)
        for x in (2.01,7.88,13.89):
            post(h,x,q[2]+.32,z+.03,z+2.99,.113,IRON)
    return (7.1,8.8,p[2]-.046)

def iron_stair(h,x,y,z,r):
    n=(24,12,4)[h.lod]
    angle=lambda i: -math.pi*.87+math.pi*1.38*i/n
    at=lambda k,a:(x+k*math.cos(a),y+k*math.sin(a))
    round_wall(h,x,y,.08,.044,z+.019,IRON,(24,12,8)[h.lod])
    for i in range(n):
        q=(at(.092,angle(i)+.002),at(r,angle(i)+.002),
           at(r,angle(i+1)-.002),at(.092,angle(i+1)-.002))
        top=.16+z*(i+1)/n
        curve_step(h,q,top-.076,top,IRON)
        a,b=at(r-.045,angle(i)),at(r-.045,angle(i+1))
        if h.lod<2:
            beam(h,xyz(*a,top+.85-z/n),xyz(*b,top+.85),.041,IRON)
        if h.lod<2 and i%2==0:
            beam(h,xyz(*b,top+.012),xyz(*b,top+.83),.030,IRON)
    return at(r*.72,angle(n))

def montreal(h,a,w,d):
    p=(1.2,14.8,6.57,6.57+d*.57)
    section(h,p,.057,10.46,3,"flat",0,omit=(0,),bays=3)
    face=edges(p)[0]
    for j,center in enumerate((3.58,8.08,12.43)):
        low=(.057,3.528,6.999)[j]
        high=(3.528,6.999,10.46)[j]
        points=[(x-p[0],1.28,low+.69,high-.46,.10,False,False)
                for i,x in enumerate((3.58,8.08,12.43)) if i!=j]
        landing=(1.48,3.42,6.65)[j]+.143
        points.append((center-p[0],1.30,max(low+.08,landing),high-.36,0,True,False))
        h.quiet_panes={q[0] for q in points if q[5] or j!=1 or q!=points[0]}
        h.finish_cornice=j==2
        g.row(h,face,low,high,BRICK,points)
    for x,height,r in ((3.58,1.48,1.16),(8.08,3.42,1.42),(12.43,6.86,1.45)):
        u,v=iron_stair(h,x,p[2]-1.83,height,r)
        slab(h,(min(u,x)-.50,max(u,x)+.51,v-.15,p[2]-.025),height+.079,height+.143,IRON)
    return (2.44,4.22,3.91)

def garden_city(h,a,w,d):
    p=(1.87,14.13,5.34,5.34+d*.47)
    section(h,p,.047,5.62,2,"cross",2.82,front="windows",over=.51,roof_mat="TinOxide")
    for x in (4.21,11.78):
        q=(x-1.45,x+1.45,p[2]-1.17,p[2]-.026)
        arcade(h,q,.055,2.33,1,STONE)
        cover(h,q,2.57,"shed",.89,"TinOxide")
    return (3.59,4.86,4.14)

def dock(h,a,w,d):
    p=(2.13,13.86,4.70,4.70+d*.60)
    section(h,p,.041,11.1,3,"gable",5.17,front="dock")
    f=edges(p)[0]
    sign(h,a,f,3.36,w=7.0)
    u=f.length/2
    block(h.body,f,u-.14,u+.14,13.05,13.39,.016,1.41,"BrownBrick")
    beam(h,f.point(u,12.42,.027),f.point(u,13.15,1.35),.115,"BrownBrick")
    beam(h,f.point(u,13.06,1.34),f.point(u,11.21,1.34),.033,IRON)
    return (7.22,8.77,p[2]-.03)

def ferry(h,a,w,d):
    p=(1.38,9.78,7.04,7.04+d*.52)
    section(h,p,.58,8.42,3,"cross",2.57,front="entry")
    slab(h,(1.42,9.74,p[2]+.016,p[3]-.016),.046,.56,"StoneBase")
    steps(h,5.4,p[2]-.026,.58,3,2.09,1.21)
    canal(h,(10.80,14.47,3.41,d-3.42))
    for i in range(4):
        slab(h,(9.79+.17*i,10.75-.13*i,4.13+.45*i,8.04+.25*i),
             .066+i*.083,.134+i*.083,STONE)
    round_wall(h,10.35,6.28,.095,.23,.59,IRON,(24,12,8)[h.lod])
    if h.lod<2:
        nb.lace_ring(h.body,lambda u,z:xyz(10.36+u,6.16,z),0,.51,.17,.126,(0,-1,0),IRON,24 if h.lod==0 else 12)
    return (4.69,6.19,5.77)

def wash(h,a,w,d):
    p=(1.52,14.48,5.77,5.77+d*.52)
    arcade(h,(p[0]+.014,p[1]-.013,p[2],p[2]+1.02),.05,3.04,3,BRICK,open_back=True)
    slab(h,(p[0]+.02,p[1]-.02,p[2]+1.08,p[3]-.04),.043,2.94,"StoneBase")
    q=(3.62,12.36,p[2]+.14,p[2]+.96)
    slab(h,q,.052,.54,STONE)
    surface(h,(q[0]+.09,q[1]-.09,q[2]+.12,q[3]-.10),.555,WATER)
    section(h,p,3.12,10.38,2,"hip",2.02,front="windows")
    sign(h,a,edges(p)[0],3.47,w=6.6)
    return (7.12,8.87,p[2]-.042)

def hotel(h,a,w,d):
    p=(3.41,12.76,4.27,4.27+d*.61)
    section(h,p,.059,15.38,5,"mansard",2.56,front="hotel",bays=2)
    face=edges(p)[0]
    if h.lod<2:
        u=1.20
        block(h.body,face,u-.26,u+.26,3.44,8.72,.11,1.15,"TinGreen")
        blade=g.face((p[0]+u+.267,p[2]-1.16),(p[0]+u+.267,p[2]-.10))
        g.plate(h,blade,.53,6.05,.86,4.97,"Sign_"+a["design"],.013)
        x=p[1]-.92
        post(h,x,p[2]-.34,2.19,2.67,.22,"Mustard")
        post(h,x,p[2]-.34,2.69,2.79,.30,IRON)
    sign(h,a,face,2.80,w=4.3)
    return (7.54,9.03,p[2]-.037)

def lock(h,a,w,d):
    p=(1.47,9.96,5.82,5.82+d*.57)
    section(h,p,.48,11.34,3,"shed",1.85,front="entry")
    slab(h,(p[0]+.013,p[1]-.013,p[2]+.015,p[3]-.015),.045,.465,"StoneBase")
    canal(h,(12.25,14.86,4.21,d-3.03))
    for i in range(3):
        x=10.10+i*.65
        y=8.1+i*.97
        z=.78-i*.235
        slab(h,(x,x+.60,y,d-4.37),.049,z,STONE)
        surface(h,(x+.065,x+.53,y+.14,d-4.55),z+.016,"YardSetts")
    return (4.83,6.44,p[2]-.033)

WORKER_BUILDERS={
    "Familistere":familistere,"Beguinage":beguinage,"Coron":coron,"CoureePompe":couree,
    "CiteCoursives":coursives,"EscaliersMontreal":montreal,"CiteJardin":garden_city,
    "PensionDockers":dock,"MaisonPasseur":ferry,"LavoirHabite":wash,
    "HotelMeublePort":hotel,"CiteEcluse":lock,
}
