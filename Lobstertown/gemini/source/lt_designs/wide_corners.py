"""Two-cell block ends for Shore Rows and Main Street. Street is -Y, canonical side street is -X."""
from math import ceil
from lt_kit import Mesh, Wall, wall, style, party, chimney, finish, roof_check, wbox, lbox, E, TRIM
from lt_shapes import dormer, slab
from lt_designs.mainst import tower
from lt_designs.cannery import corbels


def bays(a, b, width=.95):
    span = b - a
    count = max(1, ceil(span / (3.45 * width)))
    return [a + (i + .5) * span / count for i in range(count)]


def section_roof(m, rings, materials, label):
    """Closed sloping or level roof, with a continuous soffit under the projecting cornice."""
    cap = Mesh()
    cap.facing(rings[0][::-1], (0,0,-1), materials[0])
    for lo, hi, mat in zip(rings, rings[1:], materials):
        for i, p in enumerate(lo):
            j = (i+1) % len(lo)
            hint = (lo[j][1]-p[1], p[0]-lo[j][0], 0)
            cap.facing([p, lo[j], hi[j], hi[i]], hint, mat)
    cap.facing(rings[-1], (0,0,1), "TinFlat")
    roof_check(m, cap, label)


def ring(l, r, f, b, cut, z):
    pts = [(l+cut,f), (r,f), (r,b), (l,b), (l,f+cut)] if cut else [(l,f),(r,f),(r,b),(l,b)]
    return [(x,y,z) for x,y in pts]


def retail_wall(m, g, st, a, b, axes, lod, trim, flatdoor=False, shop_entry=False):
    w = Wall(a,b)
    centres = sorted((w.u_of(c), c) for c in axes)
    holes = []
    for i,(u,c) in enumerate(centres):
        residential = flatdoor and i == len(centres)-1
        hw = .55 if residential else min(.91 if flatdoor else .86, u / 2.22, (w.L-u) / 2.22)
        entry = shop_entry and i == len(centres)//2
        kind = "door" if residential else "shop" if entry else "win"
        holes.append((u-hw,u+hw,0 if residential or entry else .68,2.95 if residential else 3.28,kind))
    if lod == 0:
        corbels(m,w,st['top']-.03,lod,st['mats'][-1][2],step=.34)
        for (u,_),(un,_) in zip(centres,centres[1:]):
            c=(u+un)/2
            lbox(m,w,c-.16,c+.16,.53,3.69,.012,.12,"Dressed")
            lbox(m,w,c-.25,c+.25,3.70,3.84,.018,.19,"Dressed")
    return wall(m,g,st,a,b,"x","-",axes,lod,holes=holes,omit=[(c,0) for c in axes],trim=trim,
                waive={"balance":"the separate flats entrance occupies the end bay of a shop range"})


def build_corner(lod, D, v):
    m,g = Mesh(),Mesh()
    kind = v["wide_corner"]
    home, arcade = kind == "double", kind == "arcade"
    interior = not v.get("corner", True)
    l,r = -7.99 if interior else -7.48,7.99
    left_end = "-" if interior else "x"
    f,end = -4*D+.92,4*D-.6
    b = f + (10.5 if home else 12.2)
    wm,rm = v["wall"],v["roof_mat"]
    cut = 2.4 if arcade and not interior else 0.0
    trim = dict(door="Green" if home or arcade else "Oxblood", lites="2", lean=True)
    if not home:
        trim.update(masonry="Dressed", reveal=wm)
    rows = [(.98,.98,2.68),(.95,4.10,5.72)] if home else [(1,1.0,3.1),(1.0,4.96,6.77),(1.0,8.18,9.94)]
    if kind == "block":
        rows.append((1.0,11.33,13.00))
    top = rows[-1][2]+.82
    mats = [(0,top,wm)] if home else [(0,4.05,"Greystone"),(4.05,top,wm)]
    st = style(top,mats,rows,belts=(3.30,) if home else (4.05,),corners=home,frieze=.22 if home else None,
               plinth=(.51,.04,"StoneBase" if home else "Dressed"),belt_mat=TRIM if home else "Dressed")
    fa,si = bays(l+cut,r),bays(f+cut,b)
    if interior and not home:
        fa = bays(l+.10,r-.10)
    if home:
        doors = [fa[1], fa[-2]]
        u = Wall((l,f),(r,f)).u_of
        wall(m,g,st,(l,f),(r,f),left_end,"-",fa,lod,holes=[(u(c)-.52,u(c)+.52,0,2.85,"door") for c in doors],
             omit=[(c,0) for c in doors], trim=trim,waive={"balance":"paired entrances to two houses"})
        if not interior:
            wall(m,g,st,(l,b),(l,f),"c","x",si,lod,trim=trim)
    else:
        retail_wall(m,g,st,(l+cut,f),(r,f),fa,lod,trim,True,interior or not arcade)
        if not interior:
            retail_wall(m,g,st,(l,b),(l,f+cut),si,lod,trim)
        if cut:
            w=Wall((l,f+cut),(l+cut,f))
            c=w.A.x + (w.L/2)/w.t.x
            wall(m,g,dict(st,plinth=None,belts=()),(l,f+cut),(l+cut,f),"x","x",[c],lod,door=(c,1.18,3.0),trim=trim,
                 waive={"balance":"angled entrance to the corner shop"})
    if interior:
        party(m,(l,b),(l,f),0,top,wm)
    party(m,(r,f),(r,b),0,top,wm)
    ra=bays(l,r,.91 if home and interior else .95)
    annex = 3.55 if home else 6.65
    # House court has a full-height rear window wall beside the ell.
    joint = 1.025 if interior else -.68
    if home:
        back_axes=bays(joint,r)
        wall(m,g,st,(r,b),(joint,b),"-","c",back_axes,lod,door=(back_axes[0],1.0,2.8),trim=trim,
             waive={"balance":"the yard door serves the nearer half of the double"})
        lower = [(c,i) for c in bays(l,joint) for i in range(len(rows)) if rows[i][1]<annex+.3]
        wall(m,g,st,(joint,b),(l,b),"c",left_end,bays(l,joint),lod,z0=annex+.16,omit=lower,trim=trim)
    else:
        wall(m,g,st,(r,b),(l,b),"-",left_end,ra,lod,z0=annex+.24,trim=trim)
    mould = TRIM if home else "Dressed"
    outer = (l+E if interior else l-.32,r-E,f-.30,b+.25)
    roofrings = [ring(*outer,cut,top),ring(*outer,cut,top+.21)]
    if arcade:
        roofrings.append(ring(l+.012 if interior else l-.29,r-.012,f-.26,b+.22,cut,top+.48))
    else:
        slope=2.0
        rise=3.0
        roofrings.append(ring((l+.05 if interior else outer[0]+rise/slope),r-.05,outer[2]+rise/slope,outer[3]-rise/slope,0,top+.21+rise))
    section_roof(m,roofrings,[mould,rm],"main corner roof")
    if arcade:
        a=1.75
        tower(m,g,lod,(0 if interior else l+a+.52),f+a+.52,a,8,top+.32,top+3.6,3.6,wm,rm,trim,
              [(top+1.12,top+2.75,tuple(range(8)))],"Dressed",crest=False)
    else:
        if home:
            front_picks=fa[::2]
        else:
            front_picks=fa[1::2]
        for c in front_picks:
            dormer(m,g,lambda o,t,z:(t,-o,z),lambda o:top+.21+(-o-outer[2])*slope,-(f+.02),c,1.20,lod,
                   wm,rm,trim,height=1.47,rise=.43)
        if interior:
            for c in ra[1::2]:
                dormer(m,g,lambda o,t,z:(t,o,z),lambda o:top+.21+(outer[3]-o)*slope,b-.02,c,1.18,lod,
                       wm,rm,trim,height=1.42,rise=.40)
        for c in ([] if interior else si[1::2]):
            dormer(m,g,lambda o,t,z:(-o,t,z),lambda o:top+.21+(-o-outer[0])*slope,-(l+.02),c,1.20,lod,
                   wm,rm,trim,height=1.47,rise=.43)
    for cy in (f+2.8,b-2.2):
        crest = top+.21+(3 if not arcade else .27)
        chimney(m,r-.58,cy,.32,.40,crest-.48,crest+1.26,lod)
    if home:
        car=end-5.55
        ax=bays(b,car,.91)
        reartrim=dict(trim,simple=True)
        cottage=style(annex,[(0,annex,"BoardBatten")],[(.91,.96,2.55)],belts=(),corners=False,frieze=None)
        for a0,a1 in ([((joint,b),(joint,car))] if interior else [((joint,b),(joint,car)),((l,car),(l,b))]):
            wall(m,g,cottage,a0,a1,"c","c",ax,lod,trim=reartrim)
        # Single pitch dies under the rear face of the main roof and rises into the carriage gable.
        slab(m,[(joint+.2,annex),(l+.015 if interior else l-.23,annex+.84)], b+.015,car+1.55,lambda a,q,z:(q,a,z),lod,
             "TinGreen",what="covered kitchen ell")
        if interior:
            party(m,(l,car),(l,b),0,annex,"BoardBatten")
        m.facing([(l,b,annex),(l,car,annex),(l,car,annex+.80),(l,b,annex+.80)],(-1,0,0),"BoardBatten")
        carriage=style(annex,[(0,annex,"Clapboard")],[(.91,.96,2.55)],belts=(),corners=False,frieze=None)
        yard=bays(joint,r)
        wall(m,g,carriage,(joint,car),(r,car),"c","-",yard,lod,door=(yard[1],1.55,2.65),trim=reartrim,
             waive={"balance":"carriage doors facing the court"})
        wall(m,g,carriage,(r,end),(l,end),"-",left_end,ra,lod,trim=reartrim)
        if interior:
            party(m,(l,end),(l,car),0,annex,"Clapboard")
        else:
            wall(m,g,carriage,(l,end),(l,car),"x","c",bays(car,end),lod,trim=reartrim)
        party(m,(r,car),(r,end),0,annex,"Clapboard")
        mid=(car+end)/2
        ridge=annex+2.3
        for x,normal in ((l,(-1,0,0)),(r,(1,0,0))):
            m.facing([(x,car,annex),(x,mid,ridge),(x,end,annex)],normal,"BoardBatten")
        slab(m,[(car-.27,annex-.19),(mid,ridge),(end+.27,annex-.19)],l+.014 if interior else l-.26,r-.012,lambda a,q,z:(a,q,z),lod,
             "Slate" if interior else "SlateBrown",what="carriage house roof")
    else:
        annexwall="BrownBrick" if arcade else "Greystone"
        st2=style(annex,[(0,annex,annexwall)],[(.96,.93,2.53),(.94,3.96,5.52)],
                  belts=(3.2,),corners=False,frieze=None,belt_mat="Dressed")
        reartrim=dict(trim,simple=True)
        if interior:
            party(m,(l,end),(l,b),0,annex,annexwall)
        else:
            wall(m,g,st2,(l,end),(l,b),"x","c",bays(b,end),lod,trim=reartrim)
        lane_axes = bays(l,r,.78) if interior and not arcade else ra
        service = lane_axes[-2] if interior and not arcade else ra[1]
        wall(m,g,st2,(r,end),(l,end),"-",left_end,lane_axes,lod,door=(service,1.30,2.52),trim=reartrim,
             waive={"balance":"service entrance to the stockroom"})
        party(m,(r,b),(r,end),0,annex,annexwall)
        for a0,a1 in ([((r,end),(l,end))] if interior else [((l,end),(l,b)),((r,end),(l,end))]):
            corbels(m,Wall(a0,a1),annex-.02,lod,annexwall,step=.38)
        section_roof(m,[ring(l+.012 if interior else l-.24,r-E,b+.013,end+.23,0,annex),ring(l+.012 if interior else l-.24,r-E,b+.013,end+.23,0,annex+.28)],
                     ["Dressed"],"rear flats roof")
        if interior and not arcade:
            # A shallow folded-zinc hood identifies the flats entrance on the lane.
            slab(m,[(end+.48,2.84),(end+.015,3.08)],service-1.15,service+1.15,
                 lambda a,q,h:(a,q,h),lod,"TinGreen",what="lane entrance hood")
        if arcade:
            cy=(b+end)/2
            for x in (-2.35,2.35):
                z=annex+.28
                wbox(m,x-1.02,x+1.02,cy-1.7,cy+1.7,z,z+.18,"Iron",("z-",))
                slab(m,[(x-.95,z+.18),(x,z+.68),(x+.95,z+.18)],cy-1.62,cy+1.62,lambda a,q,h:(q,a,h),lod,
                     "TinFlat",end="Iron",eave="Iron",th=.055,what="stockroom skylight")
                for side in (-1,1):
                    for j in range(4):
                        a,bay_end=cy-1.57+.79*j,cy-1.57+.79*j+.73
                        def pane(t,y):
                            return (x+side*t,y,z+.68-.50*t/.95+.064)
                        g.facing([pane(.06,a),pane(.89,a),pane(.89,bay_end),pane(.06,bay_end)],(side*.53,0,1),"Glass")
    if v["hand"]=="R":
        for mesh in (m,g):
            mesh.v=[(-x,y,z) for x,y,z in mesh.v]
            mesh.f=[face[::-1] for face in mesh.f]
    finish(m,g)

