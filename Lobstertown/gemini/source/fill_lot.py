"""Second-pass standard (the author, 2026-11-13): the building is the whole footprint.

fill_lot(h,a) runs after a model is built (new or legacy) and before export:
  1. pushes the whole model forward so its front stands 0.3 m inside the lot front;
  2. maps the ground footprint (walls that reach the ground, enclosed areas filled);
  3. builds walled, windowed, flat-roofed ranges over every open part of the lot
     (0.3 m in from the sides and rear), stopping just under anything overhead,
     so bays and galleries sit on solid rooms instead of posts.
The plan is measured once per model, on its first LOD0 build, and reused for every
detail grade and LOD so all LODs share one footprint.
Mesh frame: x = lot x - W/2, y = lot y - 12 (nb.X / nb.Y)."""
import math
import r12_geometry as rg
from r12_geometry import nb

C=.25          # grid
EDGE=.26       # keep-in from the side and rear lines (rule: >= .25)
FRONT=.30      # front wall line
PLANS={}

def _tris(m):
    V=m.vertices
    for f in m.faces:
        for i in range(1,len(f)-1):
            yield V[f[0]],V[f[i]],V[f[i+1]]

def _faces(m):
    V=m.vertices
    for f in m.faces:
        yield [V[i] for i in f]

def _normal(ps):
    nx=ny=nz=0.0
    for i,p in enumerate(ps):
        q=ps[(i+1)%len(ps)]
        nx+=(p[1]-q[1])*(p[2]+q[2]);ny+=(p[2]-q[2])*(p[0]+q[0]);nz+=(p[0]-q[0])*(p[1]+q[1])
    l=math.sqrt(nx*nx+ny*ny+nz*nz) or 1
    return nx/l,ny/l,nz/l

def _shift(h,dy):
    for m in (h.body,h.windows):
        m.vertices=[(v[0],v[1]+dy,v[2]) for v in m.vertices]
        if hasattr(m,"lookup"):m.lookup={tuple(round(c,5) for c in v):i for i,v in enumerate(m.vertices)}

def _crop_front(m,ycut):
    """drop faces lying wholly in front of the lot line (old front paths, steps), pin stragglers to it"""
    V=m.vertices
    keep=[k for k,f in enumerate(m.faces) if max(V[i][1] for i in f)>ycut+.002]
    if len(keep)<len(m.faces):
        faces=[m.faces[k] for k in keep];uvs=[m.uvs[k] for k in keep]
        used=sorted({i for f in faces for i in f});remap={o:n for n,o in enumerate(used)}
        m.vertices=[V[i] for i in used];m.faces=[[remap[i] for i in f] for f in faces];m.uvs=uvs
    m.vertices=[(v[0],max(v[1],ycut),v[2]) for v in m.vertices]
    if hasattr(m,"lookup"):m.lookup={tuple(round(c,5) for c in v):i for i,v in enumerate(m.vertices)}

def measure(h,a):
    W,D=a["lot"][0]*8,a["lot"][1]*8
    X=lambda v:v[0]+W/2
    Y=lambda v:v[1]+12
    faces=list(_faces(h.body))
    raised=[Y(v) for ps in faces for v in ps if v[2]>.12]
    tall=[Y(v) for ps in faces for v in ps if v[2]>2.0]
    front=min(tall) if tall else min(raised)
    dy=-(min(front-FRONT,min(raised)-.05))      # move forward (dy<0 means toward the street)
    nx,ny=int(round(W/C)),int(round(D/C))
    wall=set();xwalls=[];ywalls=[]
    for ps in faces:
        z0=min(p[2] for p in ps);z1=max(p[2] for p in ps)
        n=_normal(ps)
        if z0<.6 and abs(n[2])<.3 and z1-z0>.25:
            xs=[X(p) for p in ps];ys=[Y(p)+dy for p in ps]
            a0,a1,b0,b1=min(xs),max(xs),min(ys),max(ys)
            L=max(a1-a0,b1-b0);k=max(1,int(L/(C/2)))
            for t in range(k+1):
                x=a0+(a1-a0)*t/k if n[0]*n[1]<=0 else a1-(a1-a0)*t/k
                y=b0+(b1-b0)*t/k
                wall.add((int(x//C),int(y//C)))
            if abs(n[0])>.97 and z1>1.5:xwalls.append((sum(xs)/len(xs),b0,b1,1 if n[0]>0 else -1))
            if abs(n[1])>.97 and z1>1.5:ywalls.append((sum(ys)/len(ys),a0,a1,1 if n[1]>0 else -1))
    outside=set();st=[(-1,-1)]
    while st:
        c=st.pop()
        if c in outside or c in wall or not(-1<=c[0]<=nx and -1<=c[1]<=ny):continue
        outside.add(c);st+=[(c[0]+1,c[1]),(c[0]-1,c[1]),(c[0],c[1]+1),(c[0],c[1]-1)]
    foot={(i,j) for i in range(nx) for j in range(ny) if (i,j) not in outside}
    lo_i,hi_i=int(math.ceil(EDGE/C-1e-6)),int((W-EDGE)//C)
    lo_j,hi_j=int(math.ceil(FRONT/C-1e-6)),int((D-EDGE)//C)
    free={(i,j) for i in range(lo_i,hi_i) for j in range(lo_j,hi_j) if (i,j) not in foot}
    # what is overhead of each free cell, and how tall the house stands
    cap={};tops={}
    for p,q,r in _tris(h.body):
        n=_normal((p,q,r))
        if abs(n[2])<.05:continue
        zmin=min(p[2],q[2],r[2])
        P=[(X(v),Y(v)+dy,v[2]) for v in (p,q,r)]
        x0,x1=min(v[0] for v in P),max(v[0] for v in P);y0,y1=min(v[1] for v in P),max(v[1] for v in P)
        den=(P[1][1]-P[2][1])*(P[0][0]-P[2][0])+(P[2][0]-P[1][0])*(P[0][1]-P[2][1])
        if abs(den)<1e-9:continue
        for i in range(int(x0//C),int(x1//C)+1):
            for j in range(int(y0//C),int(y1//C)+1):
                cx,cy=(i+.5)*C,(j+.5)*C
                l1=((P[1][1]-P[2][1])*(cx-P[2][0])+(P[2][0]-P[1][0])*(cy-P[2][1]))/den
                l2=((P[2][1]-P[0][1])*(cx-P[2][0])+(P[0][0]-P[2][0])*(cy-P[2][1]))/den
                l3=1-l1-l2
                if min(l1,l2,l3)<-1e-6:continue
                z=l1*P[0][2]+l2*P[1][2]+l3*P[2][2]
                c=(i,j)
                if c in free:
                    if z>1.0:cap[c]=min(cap.get(c,1e9),zmin if n[2]<0 else z)
                elif c in foot and n[2]>0:
                    tops[c]=max(tops.get(c,0),z)
    hs=sorted(tops.values())
    eave=hs[len(hs)//4] if hs else 7.0
    eave=max(3.6,min(6.2,eave-.7))   # back ranges sit a little below the house
    def level(c):
        e=eave
        if c in cap:e=min(e,cap[c]-.68)
        if e<2.4:return round(max(1.2,cap[c]-.05)*4)/4,False
        return round(e*4)/4,True
    cls={c:level(c) for c in free}
    # one height per connected patch under an overhang (its lowest), so overhangs fill as one block
    seen=set()
    for c in list(cls):
        if c in seen or cls[c]==(round(eave*4)/4,True):continue
        comp=[];st=[c];seen.add(c)
        while st:
            a0=st.pop();comp.append(a0)
            for b0 in ((a0[0]+1,a0[1]),(a0[0]-1,a0[1]),(a0[0],a0[1]+1),(a0[0],a0[1]-1)):
                if b0 in cls and b0 not in seen and cls[b0]!=(round(eave*4)/4,True):seen.add(b0);st.append(b0)
        low=min(cls[x][0] for x in comp);roof=all(cls[x][1] for x in comp)
        for x in comp:cls[x]=(low,roof)
    def decompose(rowfirst):
        rects=[];used=set()
        order=sorted(free,key=(lambda c:(c[1],c[0])) if rowfirst else (lambda c:(c[0],c[1])))
        ok=lambda c,k:c in free and c not in used and cls[c]==k
        for c in order:
            if c in used:continue
            k=cls[c];i1,j1=c
            if rowfirst:
                while ok((i1+1,c[1]),k):i1+=1
                while all(ok((i,j1+1),k) for i in range(c[0],i1+1)):j1+=1
            else:
                while ok((c[0],j1+1),k):j1+=1
                while all(ok((i1+1,j),k) for j in range(c[1],j1+1)):i1+=1
            for i in range(c[0],i1+1):
                for j in range(c[1],j1+1):used.add((i,j))
            rects.append([c[0],i1,c[1],j1,k])
        kept=sum((r[1]-r[0]+1)*(r[3]-r[2]+1) for r in rects if r[1]-r[0]>=1 and r[3]-r[2]>=1)
        return kept,-len(rects),rects
    rects=max(decompose(True),decompose(False))[2]
    plan=[]
    for i0,i1,j0,j1,(e,roofed) in rects:
        l,r,f,b=i0*C,(i1+1)*C,j0*C,(j1+1)*C
        if i0==lo_i:l=EDGE
        if i1==hi_i-1:r=W-EDGE
        if j0==lo_j:f=FRONT+.07   # street-front window trim projects about 0.33 m
        if j1==hi_j-1:b=D-EDGE
        # snap open edges onto nearby existing walls (closes the sub-grid crack)
        def snap(v,lst,side,a0,a1,sign):
            best=None
            for pos,s0,s1,out in lst:
                if out!=sign or s1<a0+.2 or s0>a1-.2:continue
                gap=(v-pos)*side
                if -.001<gap<=C+.06 and (best is None or gap<best[0]):best=(gap,pos)
            return best[1]+.006*side if best else v
        def touch(side):
            if side==0:cells=[(i,j0-1) for i in range(i0,i1+1)]
            elif side==2:cells=[(i,j1+1) for i in range(i0,i1+1)]
            elif side==3:cells=[(i0-1,j) for j in range(j0,j1+1)]
            else:cells=[(i1+1,j) for j in range(j0,j1+1)]
            return sum(cc in foot for cc in cells)/len(cells)
        t=[touch(s) for s in range(4)]
        ll=snap(l,xwalls,1,f,b,1) if t[3]>.999 else l
        rr=snap(r,xwalls,-1,f,b,-1) if t[1]>.999 else r
        ff=snap(f,ywalls,1,l,r,1) if t[0]>.999 else f
        bb=snap(b,ywalls,-1,l,r,-1) if t[2]>.999 else b
        import os
        if os.environ.get("FILL_MAP"):print("RECT",i0,i1,j0,j1,e,roofed,(round(l,2),round(r,2),round(f,2),round(b,2)),"->",(round(ll,2),round(rr,2),round(ff,2),round(bb,2)))
        ll+=.0017 if ll==l else 0;rr-=.0017 if rr==r else 0
        ff+=.0017 if ff==f else 0;bb-=.0017 if bb==b else 0
        if rr-ll<.3 or bb-ff<.3:continue
        if (rr-ll)*(bb-ff)<.6:continue
        # which sides are fully closed by existing building (no wall needed)
        online=[ff<=FRONT+.3,rr>=W-EDGE-.3,bb>=D-EDGE-.3,ll<=EDGE+.3]
        omit=tuple(s for s in range(4) if t[s]>.999)
        # windows only on street fronts and on walls facing open ground; party walls and walls against the house are plain
        blank=tuple(s for s in range(4) if s not in omit and (t[s]>0 or (online[s] and s!=0)))
        plan.append(dict(p=(round(ll,4),round(rr,4),round(ff,4),round(bb,4)),e=e,roofed=roofed,omit=omit,blank=blank,
                         open_sky=not any(cap.get((i,j),1e9)<e+2.4 for i in range(i0,i1+1) for j in range(j0,j1+1))))
    # infill blocks that touch each other: the lower one drops the shared wall
    for k,A in enumerate(plan):
        for B in plan:
            if A is B:continue
            l,r,f,b=A["p"];L,R,F,Bk=B["p"]
            if B["e"]<A["e"] or (B["e"]==A["e"] and id(B)<id(A)):continue
            for side,(edge,lo,hi) in enumerate(((f,l,r),(r,f,b),(b,l,r),(l,f,b))):
                if side in A["omit"]:continue
                if side in (0,2):
                    if abs(edge-(Bk if side==0 else F))<.01:
                        if L<=lo+.01 and R>=hi-.01:A["omit"]+=(side,)
                        elif min(R,hi)-max(L,lo)>.01 and side not in A["blank"]:A["blank"]+=(side,)
                else:
                    if abs(edge-(L if side==1 else R))<.01:
                        if F<=lo+.01 and Bk>=hi-.01:A["omit"]+=(side,)
                        elif min(Bk,hi)-max(F,lo)>.01 and side not in A["blank"]:A["blank"]+=(side,)
    import os
    if os.environ.get("FILL_MAP"):
        cov=set()
        for q in plan:
            l,r,f,b=q["p"]
            for i in range(int(l//C),int(math.ceil(r/C))):
                for j in range(int(f//C),int(math.ceil(b/C))):cov.add((i,j))
        rows=[]
        for j in range(ny-1,-1,-1):
            rows.append("".join("#" if (i,j) in foot else "+" if (i,j) in cov else "c" if (i,j) in cap else "." for i in range(nx)))
        open(os.environ["FILL_MAP"],"a").write(a["name"]+chr(10)+chr(10).join(rows)+chr(10)*2)
    # windows only where at least 1 m of open ground lies in front of the wall
    taken=set(foot)
    for q in plan:
        l,r,f,b=q["p"]
        for i in range(int(l//C),int(math.ceil(r/C-1e-6))):
            for j in range(int(f//C),int(math.ceil(b/C-1e-6))):taken.add((i,j))
    for q in plan:
        l,r,f,b=q["p"]
        I=range(int(l//C),int(math.ceil(r/C-1e-6)));J=range(int(f//C),int(math.ceil(b/C-1e-6)))
        for side in range(4):
            if side in q["omit"] or side in q["blank"]:continue
            if side==0:near=[(i,J[0]-k) for i in I for k in range(1,5)]
            elif side==2:near=[(i,J[-1]+k) for i in I for k in range(1,5)]
            elif side==3:near=[(I[0]-k,j) for j in J for k in range(1,5)]
            else:near=[(I[-1]+k,j) for j in J for k in range(1,5)]
            if side==0 and f<=FRONT+.05:continue      # the street front keeps its windows
            if any(c in taken for c in near):q["blank"]+=(side,)
    lot=W*D
    area=sum((q["p"][1]-q["p"][0])*(q["p"][3]-q["p"][2]) for q in plan)
    before=len([c for c in foot if 0<=c[0]<nx and 0<=c[1]<ny])*C*C
    return dict(dy=dy,eave=eave,blocks=plan,before_pct=round(100*before/lot,1),after_pct=round(100*(before+area)/lot,1))

def apply(h,a,plan):
    _shift(h,plan["dy"])
    for m in (h.body,h.windows):_crop_front(m,-12+.003)
    for name,val in (("quiet_counter",0),("estate",False),("hotel",False),("compact_trim",False),
                     ("roof",a.get("roof_tile","SlateDark")),("quiet_panes",set()),("finish_cornice",False),
                     ("plain_piers",False),("plain_frames",False),("detail_grade",0),("window_recess",.355),("r12",True)):
        if not hasattr(h,name):setattr(h,name,val)
    if a.get("wall_tile"):nb.REMAP[rg.BRICK]=a["wall_tile"]
    saved=(h.estate,h.detail_grade,h.compact_trim);h.estate=False;h.detail_grade=0;h.compact_trim=True
    for q in plan["blocks"]:
        e=q["e"];p=q["p"];z=.012
        lv=1 if e<5.2 else 2
        skip=tuple(sorted(set(q["omit"])|set(q["blank"])))
        if q["roofed"] and min(p[1]-p[0],p[3]-p[2])<1.0:
            rg.section(h,p,z,e,lv,None,front="windows",omit=skip)
            rg.slab(h,p,e+.004,e+.21,rg.STONE,"TinFlat")
        elif q["roofed"] and q.get("open_sky"):
            span=min(p[1]-p[0],p[3]-p[2])
            rg.section(h,p,z,e,lv,"hip",min(2.2,.3*span),front="windows",omit=skip,roof_mat=h.roof)
        elif q["roofed"]:
            rg.section(h,p,z,e,lv,"flat",0,front="windows",omit=skip)
        else:
            rg.section(h,p,z,e,1,None,front="windows" if e>2.2 else "blind",omit=skip)
            rg.slab(h,p,e,e+.02,"TinFlat")
        for s,f in enumerate(rg.edges(p)):
            if s in q["blank"]:
                f.quad(h.body,0,f.length,z,e,0,rg.BRICK)
    h.estate,h.detail_grade,h.compact_trim=saved

def fill_lot(h,a):
    import os
    if os.environ.get("FILL_OFF"):return h
    key=a["name"]
    if key not in PLANS:
        if h.lod!=0:raise RuntimeError("fill_lot: LOD0 must be measured first "+key)
        PLANS[key]=measure(h,a)
        P=PLANS[key]
        print("FILL",key,"shift",round(P["dy"],2),"eave",round(P["eave"],2),"blocks",len(P["blocks"]),
              "occupied",P["before_pct"],"->",P["after_pct"],flush=True)
    apply(h,a,PLANS[key])
    return h
