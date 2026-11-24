"""Four revised estates, with their signatures visible at the street camera."""
from r12_geometry import *
from r12_geometry import g, detail
from mathutils import Vector
import math

def eaves(h,p,z,mat="SlateDark",spacing=1.03):
    l,r,f,b=p
    slab(h,(l-.46,r+.46,f-.48,b+.48),z-.13,z-.032,mat)
    for k,face in enumerate(edges(p)):
        if not spacing or h.lod==2 or k not in (0,1,3):
            continue
        for u,v in detail.divide(.27,face.length-.27,spacing if h.lod==0 else spacing*2.7):
            x=(u+v)/2
            g.relief(h.body,face,[(x-.075,z-.70),(x+.075,z-.70),(x+.075,z-.12),(x-.075,z-.12)],
                     .019,.32,"BrownBrick")

def tennis(h,a,w,d):
    villa=(2.22,11.62,7.11,7.11+d*.305)
    hall=(13.03,21.73,11.80,11.80+d*.538)
    section(h,villa,.043,6.45,2,"hip",2.07)
    e=7.50
    h.compact_trim=True
    flat(h.body,rectangle(*hall),.061,DOWN,"StoneBase")
    for side,f in enumerate(edges(hall)):
        count=max(3,round(f.length/2.2)) if side in (1,3) else 3
        if h.lod==1:count=min(count,6)
        if h.lod==2:count=min(count,3)
        slots=[(f.length*(j+.5)/count,min(1.65,f.length/count*.77),5.12,7.04,.48,False,False)
               for j in range(count)]
        h.quiet_panes={o[0] for j,o in enumerate(slots) if side!=0 or j%3!=0}
        h.finish_cornice=True
        h.skip_relief=True
        g.row(h,f,.062,e,BRICK,slots)
        h.skip_relief=False
        if h.lod==0:
            detail.bevel(h.body,f,.16,f.length-.16,.092,.68,.025,.19,"StoneBase")
            detail.bevel(h.body,f,.15,f.length-.15,e-.29,e-.17,.025,.22,"Dressed",shadow=True)
        if h.lod<2:
            for j in range(1,count):
                u=f.length*j/count
                detail.bevel(h.body,f,u-.12,u+.12,1.00,7.15,.023,.17,BRICK)
            detail.bevel(h.body,f,.12,f.length-.12,4.86,4.99,.019,.19,STONE)
    h.compact_trim=False
    l,r,f,b=hall
    eaves(h,hall,e,"SlateBrown",None)
    cover(h,(l-.43,r+.43,f-.44,b+.44),e,"gable",(r-l+.86)*.5*math.tan(math.radians(33)),"SlateBrown")
    sign(h,a,edges(hall)[0],3.29)
    return (6.1,7.77,villa[2])

def inhabited(h,a,w,d):
    main=(1.56,8.75,9.31,9.31+d*.47)
    wing=(8.63,14.35,9.31+d*.196,9.31+d*.47-.09)
    h.compact_trim=True
    section(h,main,.055,7.78,2,"cross",3.68,front="entry",roof_mat="SlateDark",over=.08)
    section(h,wing,.072,6.71,2,"gable",2.73,front="entry",roof_mat="SlateBrown")
    h.compact_trim=False
    # R18c: an enclosed front court. A coped garden wall runs from the gateway to both sides and turns back to
    # meet the house front (left) and the wing front (right); no free-standing rooms, windows or balcony.
    wing_front=9.31+d*.196
    y0,y1=5.10,5.55
    def wall(p,k=0):
        # k offsets crossing pieces by millimetres so their bases and copings never share a plane
        l,r,f,b=p
        slab(h,p,.07+k,2.55+k,BRICK)
        pier=lambda x:10.5<x<13.2   # ends buried in a gate pier get no overhang
        slab(h,(l+(.02 if pier(l) else -.06),r+(-.02 if pier(r) else .06),f-.06,b+.06),2.50+k,2.72+k,STONE,"SlateDark")
    wall((1.66,10.61,y0,y1))            # street wall, left of the gate (ends buried in the gate pier)
    wall((13.06,14.29,y0,y1))           # street wall, right of the gate
    wall((1.70,2.15,y1-.05,9.36),.006)       # left return to the main house front
    wall((13.80,14.25,y1-.05,wing_front+.05),.006)   # right return to the wing front
    slab(h,(10.55,13.12,4.49,6.14),3.39,4.26,BRICK)
    slab(h,(10.43,13.24,4.32,6.32),4.275,4.53,STONE,"SlateDark")
    for x0,x1 in ((10.58,10.84),(12.83,13.09)):   # full-depth stone piers carry the lintel
        slab(h,(x0,x1,4.53,6.11),.064,3.42,STONE)
    return (10.84,12.14,round(9.31+d*.196,3))

def panel_timber(h,f,x0,x1,low,high,depth=.058):
    if x1-x0<.34 or high-low<.25:
        return
    for u in (x0+.04,x1-.04):
        block(h.body,f,u-.052,u+.052,low,high,depth,depth+.09,"BrownBrick")
    if h.lod==0 and x1-x0>.85:
        beam(h,f.point(x0+.10,low+.07,depth+.114),f.point(x1-.10,high-.06,depth+.114),.096,"BrownBrick")

def normandy(h,a,w,d):
    p=(2.16,13.39,7.65,7.65+d*.404)
    l,r,f,b=p
    section(h,p,.043,6.66,2,None,omit=(0,),mat=BRICK)
    face=edges(p)[0]
    for z,t in ((.043,3.38),(3.38,6.66)):
        slots=[(u,1.30,z+.60,t-.48,.08,False,False) for u in (2.03,5.64,9.02)]
        if z<.10:
            slots[1]=(5.64,1.35,.17,2.72,.10,True,False)
        h.quiet_panes={o[0] for o in slots if o[0]!=2.03 or z<.10}
        h.finish_cornice=z>1
        g.row(h,face,z,t,BRICK if z<1 else "RenderOchre",slots)
        if z>1 and h.lod<2:
            for a0,a1 in detail.gaps(slots,.14,face.length-.14,z+.20,t-.32,.18):
                panel_timber(h,face,a0,a1,z+.28,t-.33)
            block(h.body,face,.12,face.length-.12,z+.16,z+.25,.032,.107,"BrownBrick")
    roofp=(l-.43,r+.43,f-.39,b+.42)
    cover(h,roofp,6.69,"cross",4.96,"SlateBrown","RenderOchre")
    eaves(h,p,6.65,"SlateBrown")
    if h.lod<2:
        for side in (1,3):
            f0=edges(roofp)[side]
            peak=.40 if side==1 else .60
            span=f0.length
            def slope(x):
                fraction=x/span
                return 6.69+4.96*(fraction/peak if fraction<peak else (1-fraction)/(1-peak))
            posts=[span*j/(12 if h.lod==0 else 7) for j in range(1,12 if h.lod==0 else 7)]
            block(h.body,f0,.13,span-.13,6.72,6.85,.014,.126,"BrownBrick")
            for x in posts:
                block(h.body,f0,x-.062,x+.062,6.89,slope(x)-.105,.018,.136,"BrownBrick")
            if h.lod==0:
                for u,v in zip(posts[1:],posts[2:]):
                    z=min(slope(u),slope(v))-.23
                    if z>7.31:
                        beam(h,f0.point(u+.11,6.98,.158),f0.point(v-.11,z,.158),.085,"BrownBrick")
    wing=(3.00,10.33,f-.58,f+(b-f)*.52)
    # The street gable meets the long transverse ridge.
    gable=edges(wing)[0]
    rise=3.77
    roof(h,wing,6.72,rise,"SlateBrown",open_front=True)
    gable_shape=[(0,6.72),(gable.length,6.72),(gable.length*.5,6.72+rise)]
    h.body.polygon([gable.point(x,z,.002) for x,z in gable_shape],gable.out,"RenderOchre")
    if h.lod<2:
        for x in (.10,.91,1.76,2.65,gable.length*.5,4.68,5.58,6.43,7.20):
            z=6.72+rise*(1-abs(x/gable.length-.5)*2)
            if z>6.90:
                block(h.body,gable,x-.038,x+.038,6.77,z-.07,.048,.141,"BrownBrick")
        for j in range(3):
            x0=.43+j*.79
            a0=x0+.23
            z=6.72+rise*(1-abs(a0/gable.length-.5)*2)
            if z>7.1:
                for u,v in ((x0,a0),(gable.length-x0,gable.length-a0)):
                    beam(h,gable.point(u,6.84,.168),gable.point(v,z-.18,.168),.086,"BrownBrick")
        block(h.body,gable,.10,gable.length-.10,6.77,6.90,.153,.237,"BrownBrick")
    veranda=(2.36,13.17,5.17,7.51)
    vf=edges(veranda)[0]
    slab(h,veranda,.052,.69,STONE)
    for k,f0 in enumerate(edges(veranda)):
        if k==2:continue
        n=(9 if h.lod==0 else 7 if h.lod==1 else 3) if k==0 else 2
        for j in range(n):
            u0=f0.length*j/n+.049
            u1=f0.length*(j+1)/n-.051
            if k==0 and j==n//2:
                # R18d: the walk arrives here, so the middle bay is a glazed door with a panelled base,
                # a transom and three steps up to the veranda floor.
                block(h.body,f0,u0+.01,u1-.01,.71,1.24,.004,.052,"Green")
                glass_panel(h,[f0.point(u0,1.26,.006),f0.point(u1,1.26,.006),f0.point(u1,2.36,.006),f0.point(u0,2.36,.006)],f0.out)
                glass_panel(h,[f0.point(u0,2.46,.006),f0.point(u1,2.46,.006),f0.point(u1,2.89,.006),f0.point(u0,2.89,.006)],f0.out)
                block(h.body,f0,u0,u1,2.36,2.46,.008,.112,"Dressed")
                block(h.body,f0,(u0+u1)/2-.028,(u0+u1)/2+.028,1.24,2.36,.008,.07,"Dressed")
                block(h.body,f0,u0-.073,u0-.006,.71,2.91,.010,.106,"Dressed")
                for s in range(3):
                    # mm offsets keep the overlapping step blocks off each other's planes
                    block(h.body,f0,u0-.16-s*.004,u1+.16+s*.004,.052+s*.003,.69-s*.21,.004+s*.002,.32*(s+1),STONE)
                continue
            glass_panel(h,[f0.point(u0,.73,.006),f0.point(u1,.73,.006),f0.point(u1,2.89,.006),f0.point(u0,2.89,.006)],f0.out)
            block(h.body,f0,u0-.073,u0-.006,.71,2.91,.010,.106,"Dressed")
        block(h.body,f0,.027,f0.length-.027,2.04,2.118,.112,.175,"Dressed")
        block(h.body,f0,.035,f0.length-.035,2.91,3.025,.014,.125,STONE)
    cover(h,veranda,3.08,"shed",.95,"SlateDark")
    door=2.36+vf.length/2   # the walk lines up with the veranda door (middle bay), and stops at the bottom step
    return (round(door-.88,3),round(door+.88,3),round(5.17-1.0,3))

def horse_profile(u,b,width,height,count):
    # The spring line is above the tapered heels. The circular portion turns
    # through 244 degrees, visibly closing in again before the jambs.
    theta=math.radians(32)
    rr=width*.5
    center=b+height*.55
    angles=[-theta+(math.pi+2*theta)*j/count for j in range(count+1)]
    arch=[(u-rr*math.cos(q),center+height*.45*math.sin(q)) for q in angles]
    return [(arch[0][0],b),*arch,(arch[-1][0],b)],angles,center

def horsed_wall(h,f,z,top,n,w,height,deep,windows):
    N=(24,12,8)[h.lod]
    step=f.length/n
    for j in range(n):
        u=(j+.5)*step
        l=j*step+.008
        r=(j+1)*step-.008
        bottom=z+.92 if windows else z+.12
        contour,angles,center=horse_profile(u,bottom,w,height,N)
        first,last=contour[0][0],contour[-1][0]
        tip=N//2+1
        left=contour[:tip+1]
        right=contour[tip:]
        shade="RevealStone" if windows else BRICK
        if windows:
            g.relief(h.body,f,[(l,z),(r,z),(r,bottom-.003),(l,bottom-.003)],-deep,0,BRICK)
        else:
            g.relief(h.body,f,[(l,z),(first-.003,z),(first-.003,bottom),(l,bottom)],-deep,0,BRICK)
            g.relief(h.body,f,[(last+.003,z),(r,z),(r,bottom),(last+.003,bottom)],-deep,0,BRICK)
        g.relief(h.body,f,[(l,bottom),*left,(left[-1][0],top-.01),(l,top-.01)],-deep,0,BRICK)
        g.relief(h.body,f,[*right,(r,bottom),(r,top-.01),(right[0][0],top-.01)],-deep,0,BRICK)
        if windows:
            p=[f.point(x,y,-deep-.006) for x,y in contour]
            if j==n//2 and f.out.y<-.90:
                h.windows.polygon(p,f.out,"Cream",room=nb.ROOMS[2])
            else:
                h.body.polygon(p,f.out,"GreyBlue")
            if h.lod<2:
                for x in (u-.25,u+.25):
                    detail.quad_bar(h.body,f,x-.019,x+.019,bottom+.07,center+.29,-deep+.025,"Iron")
                detail.quad_bar(h.body,f,first+.056,last-.056,center-.06,center-.018,-deep+.036,"Iron")
        if h.lod<2:
            groups=8 if h.lod==0 else 6
            theta=math.radians(32)
            for k in range(groups):
                a=angles[0]+(angles[-1]-angles[0])*(k+.052)/groups
                b=angles[0]+(angles[-1]-angles[0])*(k+.948)/groups
                ring=[(u-(w*.5+rim)*math.cos(q),center+(height*.45+rim)*math.sin(q))
                      for q,rim in ((a,.018),(b,.018),(b,.29),(a,.29))]
                g.relief(h.body,f,ring,.014,.21,"=Brick085" if k%2==0 else "Cream")
            for side in (-1,1):
                for k in range(3 if not windows else 2):
                    x=first if side<0 else last
                    lo=x-.24 if side<0 else x+.017
                    hi=x-.017 if side<0 else x+.24
                    base=bottom+.05+k*.19
                    block(h.body,f,lo,hi,base,base+.166,.019,.17,"=Brick085" if k%2==0 else "Cream")

def moorish(h,a,w,d):
    p=(1.75,14.25,9.03,9.03+d*.391)
    l,r,f,b=p
    z=7.94
    section(h,p,.074,z,2,None,omit=(0,),front="entry")
    ff=edges(p)[0]
    # R18d: French windows behind the two side arches (they showed bare brick), centred on the arcade bays.
    bay=(14.16-1.84)/3
    side_bays=[1.84+bay*.5-l,1.84+bay*2.5-l]
    slots=[(ff.length/2,1.37,.13,2.80,.23,True,False)]+[(u,1.24,.62,2.80,.15,False,False) for u in side_bays]
    h.quiet_panes={slots[0][0],side_bays[0]}
    h.finish_cornice=False
    g.row(h,ff,.074,3.76,BRICK,slots)
    if h.lod<2:
        horsed_wall(h,ff,3.76,7.40,4,1.69,2.05,.35,True)
    else:
        h.quiet_panes=()
        g.row(h,ff,3.76,7.40,BRICK,[(ff.length/2,1.69,4.67,6.84,.44,False,False)])
    g.plane(h.body,ff,0,ff.length,7.39 if h.lod<2 else 7.40,z,BRICK)
    slab(h,(l-.14,r+.14,f-.16,b+.12),z,z+.21,BRICK,"SlateDark")
    ground=(1.84,14.16,6.29,8.79)
    gf=edges(ground)[0]
    if h.lod<2:
        horsed_wall(h,gf,.065,3.55,3,2.95,2.95,.52,False)
    else:
        for x in (2.02,5.96,10.06,13.98):
            post(h,x,6.56,.066,3.47,.41,BRICK)
        slab(h,(1.81,14.19,6.26,7.30),3.20,3.48,BRICK)
    slab(h,(1.76,14.24,6.16,8.88),3.56,3.78,STONE,"SlateGreen")
    for face in edges(p):
        if h.lod<2:
            for j,(u,v) in enumerate(detail.divide(.11,face.length-.11,.63 if h.lod==0 else 1.27)):
                block(h.body,face,u+.006,v-.008,7.46,7.73,.027,.152,"TinGreen" if j%2 else "Cream")
                if h.lod==0:
                    u0=(u+v)/2
                    g.relief(h.body,face,[(u0-.10,7.59),(u0,7.49),(u0+.10,7.59),(u0,7.69)],.163,.192,
                             "Cream" if j%2 else "TinGreen")
        else:
            block(h.body,face,.11,face.length-.11,7.48,7.71,.032,.122,"TinGreen")
        block(h.body,face,.10,face.length-.10,z+.219,z+.48,-.06,.16,STONE)
        for j,(u,v) in enumerate(detail.divide(.14,face.length-.15,1.30 if h.lod<2 else 5.8)):
            ww=min(.58,(v-u)*.65)
            c=(u+v)/2
            block(h.body,face,c-ww/2,c+ww/2,z+.49,z+.87,-.05,.137,BRICK)
    q=(5.46,10.54,10.63,15.35)
    for x in (q[0]+.19,q[1]-.19):
        for y in (q[2]+.19,q[3]-.19):
            if h.lod==2:
                post(h,x,y,z+.22,z+1.96,.16,STONE)
            else:
                round_wall(h,x,y,.087,z+.22,z+1.96,STONE,(24,12,8)[h.lod])
    cover(h,q,z+1.985,"hip",1.28,"SlateGreen")
    return (7.24,8.76,6.27)

BUILDERS={"VillaJeuDePaume":tennis,"VillaMurHabite":inhabited,
          "VillaNormande":normandy,"VillaMauresque":moorish}
