"""Measured façade relief, window joinery, ivy and export normals."""
import math
from mathutils import Vector

UP=Vector((0,0,1))
STONE="Dressed"
IRON="Iron"

def bevel(m,f,l,r,z,t,d0,d1,mat,edge=.025,shadow=False):
    """Closed extrusion with a single chamfer on its street-facing perimeter."""
    if min(r-l,t-z,d1-d0)<=.002:return
    edge=min(edge,(r-l)*.19,(t-z)*.19,(d1-d0)*.36)
    if edge<=.0005:return
    outer=[(l,z),(r,z),(r,t),(l,t)]
    inner=[(l+edge,z+edge),(r-edge,z+edge),(r-edge,t-edge),(l+edge,t-edge)]
    back=[f.point(u,v,d0) for u,v in outer]
    near=[f.point(u,v,d1-edge) for u,v in outer]
    front=[f.point(u,v,d1) for u,v in inner]
    m.polygon(back,-f.out,mat)
    m.polygon(front,f.out,mat)
    for i,(u,v) in enumerate(outer):
        j=(i+1)%4
        du,dv=outer[j][0]-u,outer[j][1]-v
        normal=f.tangent*dv-UP*du
        use="RevealStone" if shadow and i==0 else mat
        m.polygon([back[i],back[j],near[j],near[i]],normal,use)
        m.polygon([near[i],near[j],front[j],front[i]],normal+f.out,use)

def gaps(slots,lo,hi,z0,z1,margin=.16):
    safe=lo
    for u,w,b,t,*_ in sorted(slots):
        if t<=z0 or b>=z1:continue
        left,right=u-w*.5-margin,u+w*.5+margin
        if left>safe+.045:
            yield safe,min(left,hi)
        safe=max(safe,right)
        if safe>=hi:return
    if hi>safe+.045:
        yield safe,hi

def facade(h,f,z,t,slots,mat):
    if h.lod!=0 or getattr(h,"skip_relief",False) or t-z<1.45 or f.length<1.45:return
    m=h.body
    industry=getattr(h,"works",False)
    if getattr(h,"compact_trim",False) and f.out.y>-.5:
        from round5_geometry import block
        if z<.08:
            for l,r in gaps(slots,.08,f.length-.08,z+.025,z+.60,.15):
                block(m,f,l,r,z+.027,z+.60,.011,.162,"StoneBase")
        block(m,f,.12,f.length-.12,t-.19,t-.10,.019,.217,STONE)
        for l,r in gaps(slots,.20,f.length-.20,z+.69,t-.32,.24):
            if r-l>.34:
                u=(l+r)*.5
                block(m,f,u-.13,u+.13,z+.72,t-.27,.016,.09,mat)
        return
    span=f.length
    corner=.078 if industry else .207
    base=.61 if z<.06 else .14
    if z<.06:
        for l,r in gaps(slots,.063,span-.063,z+.018,z+base,.14):
            bevel(m,f,l,r,z+.012,z+base,-.012,.192,"StoneBase",edge=.022)
            # Individual cap blocks establish the scale of the masonry.
            for x,y in divide(l+.019,r-.019,1.35 if getattr(h,"r12",False) else 1.04 if industry else .81):
                bevel(m,f,x+.009,y-.009,z+base+.017,z+base+.122,.011,.235,STONE)
    crown=getattr(h,"finish_cornice",True)
    level=t-(.102 if industry else .082)
    for l,r in gaps(slots,corner,span-corner,level-.19,level+.065,.15):
        bevel(m,f,l,r,level-.18,level,.022,.276 if crown else .177,STONE,shadow=True)
        if not crown:continue
        bevel(m,f,l+.014,r-.014,level+.012,level+.075,.025,.335,STONE)
        pitch=1.24 if getattr(h,"r12",False) else .78 if industry else .57
        for x,y in divide(l+.02,r-.02,pitch):
            u=(x+y)/2
            ww=min(.18,(y-x)*.50)
            if ww>.04:
                bevel(m,f,u-ww*.5,u+ww*.5,level-.30,level-.204,.023,.224,STONE,edge=.016)
    pilaster_base=z+base+.151 if z<.06 else z+.079
    pilaster_top=level-.329
    if pilaster_top-pilaster_base<.42:return
    intervals=list(gaps(slots,.13,span-.13,pilaster_base,pilaster_top,.215))
    for j,(l,r) in enumerate(intervals):
        if r-l<.28:continue
        centers=((l+.16,r-.16) if not slots and r-l>3.0 else ((l+r)*.5,))
        for k,u in enumerate(centers):
            # A structural bay pier plus a cap and a foot. The inset panels remain brick.
            ww=min(r-l-.065,.52 if industry else .34)
            if ww<.18:continue
            uu=max(l+ww*.5,min(r-ww*.5,u))
            from round5_geometry import block
            block(m,f,uu-ww/2,uu+ww/2,pilaster_base,pilaster_top,.003,.106,mat)
            if (crown or z<.06) and not getattr(h,"plain_piers",False):
                for a,b in ((pilaster_base-.105,pilaster_base-.026),(pilaster_top+.018,pilaster_top+.101)):
                    bevel(m,f,uu-ww*.52,uu+ww*.52,a,b,.009,.158,STONE,edge=.018)
            if h.detail_grade>0:
                count=max(2,round((pilaster_top-pilaster_base)/(.49 if industry else .41)))
                for i in range(1,count):
                    e=pilaster_base+(pilaster_top-pilaster_base)*i/count
                    bevel(m,f,uu-ww*.46,uu+ww*.46,e-.026,e+.026,.109,.139,mat,edge=.010)
    # Recess-like spandrels with real raised soldier bricks. Added where the envelope
    # has long runs of masonry, so every triangle contributes to a visible feature.
    if h.detail_grade:
        y0=pilaster_base+.024
        y1=min(pilaster_top-.018,y0+.139)
        if y1-y0>.055:
            for l,r in gaps(slots,.10,span-.10,y0,y1,.21):
                pitch=(.39,.30,.23)[min(h.detail_grade,3)-1]
                for x,y in divide(l,r,pitch):
                    if y-x>.09:
                        bevel(m,f,x+.012,y-.012,y0,y1,.013,.075,mat,edge=.015)

def divide(l,r,pitch):
    n=max(1,round((r-l)/pitch))
    for i in range(n):
        yield l+(r-l)*i/n,l+(r-l)*(i+1)/n

def quad_bar(m,f,u0,u1,z0,z1,d,mat=IRON):
    # The bar is seated on the pane. A narrow closed extrusion avoids flat painted lines.
    if u1-u0<.002 or z1-z0<.002:return
    if z1-z0>u1-u0:
        mid=(u0+u1)*.5
        l=[f.point(u0,z0,d),f.point(u1,z0,d),f.point(mid,z0,d-.024)]
        u=[f.point(u0,z1,d),f.point(u1,z1,d),f.point(mid,z1,d-.024)]
        end=UP
        side=f.tangent
    else:
        mid=(z0+z1)*.5
        l=[f.point(u0,z0,d),f.point(u0,z1,d),f.point(u0,mid,d-.024)]
        u=[f.point(u1,z0,d),f.point(u1,z1,d),f.point(u1,mid,d-.024)]
        end=f.tangent
        side=UP
    m.polygon(l,-end,mat)
    m.polygon(u,end,mat)
    for j,n in enumerate((f.out,side-f.out,-side-f.out)):
        k=(j+1)%3
        m.polygon([l[j],l[k],u[k],u[j]],n,mat)

def window(h,f,o,depth,arc,spring,header):
    u,w,b,t,curve,door,_=o
    m=h.body
    l,r=u-w*.5,u+w*.5
    industry=getattr(h,"works",False)
    if h.lod==2:return
    frame=IRON if industry else "TinGreen"
    # These parts sit in the opening and use separate depth from the facing trim.
    if h.lod==0 and not getattr(h,"plain_frames",False):
        for x,y in ((l+.008,l+.055),(r-.055,r-.008)):
            quad_bar(m,f,x,y,b+.017,spring-.009,depth+.052,frame)
    if not door:
        if h.lod==0:
            bevel(m,f,l-.142,r+.142,b-.123,b-.040,-.019,.182,STONE,shadow=True)
        else:
            from round5_geometry import block
            block(m,f,l-.095,r+.095,b-.092,b-.034,-.012,.101,STONE)
        if w*(t-b)>1.0:
            columns=max(2,round(w/(.41 if industry else .56)))
            rows=max(2,round((spring-b)/(.49 if industry else .71)))
            if h.lod==1:
                columns=rows=2
            grid=w/columns
            for i in range(1,columns):
                x=l+grid*i
                ymax=spring-.014
                if curve>0 and h.lod==0:
                    ymax=spring+curve*math.sqrt(max(0,1-((x-u)/(w/2))**2))-.029
                quad_bar(m,f,x-.015,x+.015,b+.043,ymax,depth+.057,frame)
            for j in range(1,rows):
                z=b+(spring-b)*j/rows
                quad_bar(m,f,l+.058,r-.058,z-.016,z+.016,depth+.063,frame)
    if h.lod!=0:return
    if curve>0:
        from round5_geometry import relief
        rim=.134 if industry else .105
        inner=header(w/2+.014,curve+.015)
        outer=header(w/2+rim,curve+rim)
        stride=max(1,(len(arc)-1)//4)
        for i in range(0,len(arc)-1,stride):
            j=min(i+stride,len(arc)-1)
            # Pull back each stone from its neighbour so the mortar joint reads.
            lerp=lambda a,b,k:(a[0]+(b[0]-a[0])*k,a[1]+(b[1]-a[1])*k)
            band=[lerp(inner[i],inner[j],.038),lerp(inner[i],inner[j],.962),
                  lerp(outer[i],outer[j],.962),lerp(outer[i],outer[j],.038)]
            relief(m,f,band,-.012,.117 if not (i<=len(arc)//2<j) else .160,STONE)
    else:
        bevel(m,f,l-.092,r+.092,t+.018,t+.137,-.016,.133,STONE,shadow=True)

def ivy(h,x,y,z,r):
    if h.lod!=0:return
    # Four lobes follow the perimeter of a real ivy scan rather than a filled shrub volume.
    from civic_geometry import xyz
    m=h.body
    tile=__import__("nf_build").LAYOUT["lods"][m.lodkey]["Ivy"]["uv"]
    u0,v0,u1,v1=tile
    outline=((-.88,-.16),(-.71,-.64),(-.29,-.72),(-.20,-.92),
             (.21,-.72),(.49,-.75),(.82,-.32),(.91,.15),
             (.72,.48),(.46,.54),(.30,.79),(-.12,.87),(-.42,.63),(-.68,.58))
    p=[Vector(xyz(x+dx*r,y+dy*r,z+.043+.12*dy)) for dx,dy in outline]
    uv=[(u0+(u1-u0)*(.5+dx*.52),v0+(v1-v0)*(.5+dy*.52)) for dx,dy in outline]
    closed_sheet(m,p,uv,UP)

def wall_ivy(h,f,u,z,w,height):
    if h.lod!=0:return
    m=h.body
    tile=__import__("nf_build").LAYOUT["lods"][m.lodkey]["Ivy"]["uv"]
    l,b,r,t=tile
    shape=((.01,.0),(.23,.05),(.35,.19),(.59,.12),(.79,.28),(.89,.51),(.71,.69),
           (.98,.88),(.81,.99),(.48,.82),(.32,.55),(.12,.43))
    p=[f.point(u+w*x,z+height*y,.017) for x,y in shape]
    uv=[(l+(r-l)*x,b+(t-b)*y) for x,y in shape]
    closed_sheet(m,p,uv,f.out)

def closed_sheet(m,points,uv,direction):
    from nf_build import newell
    normal=newell(points).normalized()
    if normal.dot(Vector(direction))<0:
        points=points[::-1]
        uv=uv[::-1]
        normal.negate()
    inner=[v-normal*.0035 for v in points]
    m._add(points,uv)
    m._add(inner[::-1],uv[::-1])
    for i,v in enumerate(points):
        j=(i+1)%len(points)
        edge=points[j]-v
        m.polygon([v,points[j],inner[j],inner[i]],edge.cross(normal),"Ivy")

def smooth_export(obj):
    mesh=obj.data
    for p in mesh.polygons:
        p.use_smooth=True
    mesh.set_sharp_from_angle(angle=math.radians(40))
    mesh.update()
