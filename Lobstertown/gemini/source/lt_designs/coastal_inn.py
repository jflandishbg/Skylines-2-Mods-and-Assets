"""Street-front coastal inns. Street is -Y. Plan dimensions are in metres."""
import math

from lt_kit import Mesh, Wall, E, TRIM, wall, style, surface, wbox, chimney, finish, gable_wall, gable_roof
from lt_shapes import slab, dormer, pavilion_roof
from lt_designs.mainst import tower
from lt_designs.shore_row import WIN2, WIN3


def bays(a, b, width=.90):
    """Even room bays, keeping the end openings clear of returns."""
    if b - a < 2.05:
        return []
    n = max(1, math.ceil((b-a-2.46)/(3.44*width))+1)
    if n > 1 and (b-a-2.46)/(n-1) < 1.86*width:
        n -= 1
    return [(a+b)/2] if n == 1 else [a+1.23+(b-a-2.46)*i/(n-1) for i in range(n)]


def floor_plan(W, D, layout, corner):
    """Main block, service range and dining wings. The final wing flag denotes a joint with the range."""
    width, depth = W*8, D*8
    l = -width/2 + (.98 if corner else 1.42)
    r = width/2 - 1.42
    span = r-l
    front, end = -depth/2+.92, depth/2-.6
    # Fractions across the main frontage locate the wings and the lane range.
    if layout == 'quadrangle':
        main, back, lane = .34, .20, (0,1)
        wings = [(.028,.309,True),(.691,.972,True)]
    elif layout == 'slip':
        main, back, lane = .42, .23, (0,.885)
        wings = [(.028,.55,True)]
    elif layout == 'spine':
        main, back, lane = .405, .225, (.055,.945)
        wings = [(.263,.737,True)]
    elif layout == 'lodge':
        main, back, lane = .48, .195, (.315,1)
        wings = [(.345,.970,True)]
    elif layout == 'offset':
        main, back, lane = .365, .215, (.40,1)
        wings = [(.035,.275 if W==3 else .32,False),(.44,.96,True)]
    else:
        raise ValueError(layout)
    # Corner parcels get a longer range on the side street and a shorter foreblock.
    if corner:
        main -= .055
        back += .065
    at = lambda fraction: l+span*fraction
    return (l,r,front,front+main*depth,end-back*depth,end,at(lane[0]),at(lane[1]),
            [(at(a),at(b),attached) for a,b,attached in wings])


def roof(m, g, lod, l, r, f, b, eave, gambrel, mat, gmat, trim, *, end_windows=True):
    """A closed transverse roof with glazed gable ends; returns its profile for dormers and joints."""
    mid = (b+f)/2
    half = (b-f)/2
    knee = min(1.85,.47*half)
    lower = 1.45 if gambrel else .74
    upper = .39 if gambrel else lower
    def height(run):
        return eave + lower*min(run,knee) + upper*max(0,run-knee)
    def run_for(z):
        h = z-eave
        return min(h/lower,knee)+max(0,h-lower*knee)/upper
    ridge = height(half)
    profile = [(f-.25,height(-.25))]
    if gambrel:
        profile += [(f+knee,height(knee))]
    profile.append((mid,ridge))
    if gambrel:
        profile.append((b-knee,height(knee)))
    profile.append((b+.28,height(-.28)))
    slab(m,profile,l-.27,r+.27,lambda x,y,z:(x,y,z),lod,mat,end=mat,what="shingled range roof")
    shape=(height(knee),knee) if gambrel else None
    windows=[(mid,.74,eave+.50,eave+1.70)] if end_windows and ridge-eave>2.25 else []
    for A,B in [((l,b),(l,f)),((r,f),(r,b))]:
        gable_wall(m,g,A,B,eave,ridge,lod,gmat,wins=windows,trim=trim,shape=shape)
    return mid,ridge,height,run_for


def cross_gable(m,g,lod,c,face,sign,half,eave,rise,run_for,wall_mat,mat,trim):
    a,b=(c-half,c+half) if sign<0 else (c+half,c-half)
    gable_wall(m,g,(a,face),(b,face),eave,eave+rise,lod,wall_mat,
               wins=[(c,.76,eave+.51,eave+1.63)],trim=trim)
    reach=run_for(eave+rise+.22)+.35
    overs=(.36,reach) if sign<0 else (reach,.36)
    gable_roof(m,c-half,c+half,face,face,eave,eave+rise,lod,mat,over=overs)


def veranda(m,g,lod,l,r,f,v,main,trim):
    """A recessed ground-floor gallery with solid front rooms on either side and a continuous upper wall."""
    base = v['layout']
    xs = bays(l,r)
    # Break the facade on the piers between room axes.
    fractions={'quadrangle':(.19,.81),'slip':(.10,.62),'spine':(.28,.72),
               'lodge':(.36,.90),'offset':(.15,.70)}
    start, stop = fractions[base]
    i=max(1,round(start*len(xs)))
    j=min(len(xs)-1,max(i+2,round(stop*len(xs))))
    a,b=(xs[i-1]+xs[i])/2,(xs[j-1]+xs[j])/2
    room_depth=1.18
    fy=f+room_depth
    ceiling=3.70
    skin=v['base'] or v['wall']
    low=style(ceiling,[(0,ceiling,skin)],WIN3[:1],belts=(),plinth=(.66,.05,'StoneBase'),frieze=None,corners=False)
    waiver={'balance':'The summer inn entrance opens from the recessed dining gallery.'}
    for x0,x1,axes,left,right in [(l,a,xs[:i],'x','x'),(b,r,xs[j:],'x','x')]:
        wall(m,g,low,(x0,f),(x1,f),left,right,axes,lod,trim=trim,waive=waiver)
    entry=xs[(i+j-1)//2]
    wall(m,g,low,(a,fy),(b,fy),'c','c',xs[i:j],lod,door=(entry,1.08,2.95),trim=trim,waive=waiver)
    for A,B in [((a,f),(a,fy)),((b,fy),(b,f))]:
        w=Wall(A,B)
        surface(m,g,w,0,ceiling,[(0,ceiling,skin)],[],lod,trim)
    # The cantilevered upper rooms and the end piers meet the actual street wall.
    wall(m,g,main,(l,f),(r,f),'x','x',xs,lod,z0=ceiling,trim=trim,waive=waiver)
    m.facing([(a,f,ceiling),(b,f,ceiling),(b,fy,ceiling),(a,fy,ceiling)],(0,0,-1),'Deck')
    wbox(m,a+.01,b-.01,f+.01,fy-.012,0,.07,'Deck',('z-',))
    posts=[a+.20]+[(x+y)/2 for x,y in zip(xs[i:j],xs[i+1:j])]+[b-.20]
    for n,x in enumerate(posts):
        if lod==2 and n not in (0,len(posts)-1):
            continue
        yy=f+.13
        wbox(m,x-.105,x+.105,yy-.095,yy+.095,.074,ceiling-.18,TRIM,('z-','z+'))
        if lod<2:
            wbox(m,x-.15,x+.15,yy-.14,yy+.14,.075,.32,TRIM,('z-',))
            wbox(m,x-.17,x+.17,yy-.16,yy+.16,ceiling-.24,ceiling-.09,TRIM,('z+',))
    wbox(m,a+.01,b-.01,f-.04,f+.30,ceiling-.083,ceiling-.006,TRIM)
    return xs


def exposed(a,b,joins):
    """Intervals of wall open to a yard or lane on either side of the attached wings."""
    cursor=a
    for x0,x1 in sorted(joins):
        if x0>cursor+E:
            yield cursor,x0
        cursor=max(cursor,x1)
    if b>cursor+E:
        yield cursor,b


def build(lod,W=3,D=4,**v):
    layout=v['layout']
    corner=v.get('corner',False)
    l,r,f,b,c,end,rl,rr,wings=floor_plan(W,D,layout,corner)
    m,g=Mesh(),Mesh()
    mat,body,gmat=v['roof_mat'],v['wall'],v['gable_mat']
    top,low=9.9,6.7
    face_trim=dict(door=v['door'],lites=v['lites'],lean='bare')
    plain=dict(face_trim,simple=True)
    front_mats=[(0,3.75,v['base']),(3.75,top,body)] if v['base'] else [(0,top,body)]
    main=style(top,front_mats,WIN3,belts=(3.75,6.85))
    family_door={'balance':'The service entrance is placed for access to the court.'}
    front_axes=veranda(m,g,lod,l,r,f,v,main,face_trim)
    side_axes=bays(f,b)
    # The long gable-end hotels have fully framed double-hung sash on the guest ends and lane.
    end_trim=face_trim if layout in ('slip','lodge') and D==6 else plain
    left_door=(side_axes[1],1.04,2.95) if corner else None
    wall(m,g,main,(l,b),(l,f),'x','x',side_axes,lod,door=left_door,trim=end_trim,waive=family_door)
    wall(m,g,main,(r,f),(r,b),'x','x',side_axes,lod,trim=end_trim)
    if corner:
        # A second public entrance with its own hood marks the side street.
        y=left_door[0]
        slab(m,[(l-.61,3.10),(l+.006,3.38)],y-.88,y+.88,lambda a,q,z:(q,a,z),lod,mat,what='side entry hood')
    joints=[(a,z) for a,z,_ in wings]
    for a,z in exposed(l,r,joints):
        axes=bays(a,z)
        door=(axes[len(axes)//2],1.0,2.95) if z-a>4.1 and axes else None
        wall(m,g,main,(z,b),(a,b),'c','c',axes,lod,door=door,trim=plain,waive=family_door)
    for a,z,_ in wings:
        # Closed upper spandrel behind the dining roof. The adjacent rooms have yard-facing windows.
        wall(m,g,main,(z,b),(a,b),'-','-',[],lod,z0=low,trim=plain)
    mid,ridge,height,run_for=roof(m,g,lod,l,r,f,b,top,v['roof']=='gambrel',mat,gmat,plain)
    # Each guest block has a distinct roof composition as well as a different service plan.
    centre=front_axes[len(front_axes)//2]
    gables={'quadrangle':[centre],'slip':[front_axes[-2]],'spine':[front_axes[1],front_axes[-2]],
            'lodge':[],'offset':[front_axes[1]]}[layout]
    half=2.35 if W==3 else 2.75
    for x in gables:
        cross_gable(m,g,lod,x,f,-1,half,top,2.75,run_for,gmat,mat,face_trim)
    if layout in ('quadrangle','lodge','offset'):
        for x in front_axes[1:-1:2]:
            if all(abs(x-y)>half+1.15 for y in gables):
                dormer(m,g,lambda o,t,z:(t,-o,z),lambda o:height(-o-f)+.16,-(f+.55),x,1.38,lod,
                       gmat,mat,plain,rise=.48,height=1.39)
    if layout in ('slip','lodge') or (layout=='quadrangle' and W==5):
        a=1.23 if W==3 else 1.62
        pos=(.27 if layout=='slip' else .65 if layout=='lodge' else .5)
        tx=l+(r-l)*pos
        tower(m,g,lod,tx,mid,a,8,ridge-1.9,ridge+2.55,2.65,body,mat,face_trim,
              [(ridge+.40,ridge+1.85,tuple(range(8)))],TRIM,crest=False)
    for x in (l+1.32,r-1.32):
        chimney(m,x,mid,.43,.43,ridge-.8,ridge+1.45,lod)

    # The rear range is shorter, shifted or divided from a second wing according to family.
    carmat=v['car_mat']
    rear=style(low,[(0,low,carmat)],WIN2,belts=(3.75,))
    wt=style(low,[(0,low,v['wing_mat'])],WIN2,belts=(3.75,))
    attached=[(a,z) for a,z,joins in wings if joins]
    for a,z in exposed(rl,rr,attached):
        axes=bays(a,z)
        door=(axes[len(axes)//2],1.10,2.84) if axes and z-a>3.4 else None
        wall(m,g,rear,(a,c),(z,c),'c','c',axes,lod,door=door,trim=plain,waive=family_door)
    for A,B in [((rl,end),(rl,c)),((rr,c),(rr,end))]:
        wall(m,g,rear,A,B,'x','x',bays(c,end),lod,trim=plain)
    lane_axes=bays(rl,rr)
    wall(m,g,rear,(rr,end),(rl,end),'x','x',lane_axes,lod,trim=end_trim)
    rear_mid,rear_ridge,rear_height,rear_run=roof(m,g,lod,rl,rr,c,end,low,v['car']=='gambrel',mat,carmat,plain)
    if v['car']=='cross':
        pick=lane_axes[1] if layout=='slip' else lane_axes[-2]
        cross_gable(m,g,lod,pick,end,1,2.05,low,2.35,rear_run,carmat,mat,plain)
    if v['lofts']:
        picks=lane_axes[1:-1:2] if layout=='spine' else [lane_axes[1],lane_axes[-2]]
        for x in sorted(set(picks)):
            dormer(m,g,lambda o,t,z:(t,o,z),lambda o:rear_height(end-o)+.16,end-.48,x,1.25,lod,
                   carmat,mat,plain,height=1.28,rise=.45)
    if v['cupola']:
        pos={'quadrangle':.5,'slip':.72,'lodge':.30,'offset':.58}.get(layout,.5)
        x=rl+(rr-rl)*pos
        z=rear_ridge+.16
        wbox(m,x-.56,x+.56,rear_mid-.56,rear_mid+.56,z-.48,z+.88,carmat,('z-','z+'))
        if lod<2:
            for sign in (-1,1):
                yy=rear_mid+sign*.568
                m.facing([(x-.38,yy,z+.14),(x+.38,yy,z+.14),(x+.38,yy,z+.70),(x-.38,yy,z+.70)],
                         (0,sign,0),'GreyBlue')
        pavilion_roof(m,x-.68,x+.68,rear_mid-.68,rear_mid+.68,z+.88,1.05,lod,mat,finial=False)

    for a,z,joins in wings:
        side=bays(b,c)
        wall(m,g,wt,(z,b),(z,c),'c','c',side,lod,door=(side[0],1.0,2.95),trim=plain,waive=family_door)
        wall(m,g,wt,(a,c),(a,b),'c','c',side,lod,trim=plain)
        # Broad spines have two parallel ridges, keeping the dining roof below the guest windows.
        paired=layout in ('spine','lodge') or layout=='slip' and W>3
        rise=1.92 if paired else min(2.02,(z-a)*.25)
        roof_z=low+rise
        aft=rear_run(roof_z+.20)+.24 if joins else .28
        if joins:
            assert aft < (end-c)/2, 'dining wing crosses the carriage ridge'
        if paired:
            x=(a+z)/2
            prof=[(a-.25,low-.15),((a+x)/2,roof_z),(x,low+.21),((x+z)/2,roof_z),(z+.25,low-.15)]
            slab(m,prof,b+.012,c+aft,lambda along,q,h:(q,along,h),lod,mat,end=mat,what='paired dining roofs')
        else:
            gable_roof(m,a,z,b,c,low,roof_z,lod,mat,over=(-.012,aft))
        if not joins:
            wall(m,g,wt,(z,c),(a,c),'x','x',bays(a,z),lod,trim=plain)
            gable_wall(m,g,(z,c),(a,c),low,roof_z,lod,body,trim=plain)
        if lod<2:
            x=(3*a+z)/4 if paired else (a+z)/2
            chimney(m,x,b+.46*(c-b),.29,.33,roof_z-.60,roof_z+1.13,lod)

    # Local granite stacks keep red paint confined to the doors and shutters.
    m.mats[:]=['StoneBase' if material=='Chimney' else material for material in m.mats]
    finish(m,g)

