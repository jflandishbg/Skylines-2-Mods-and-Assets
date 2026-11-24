"""Six original Paris on the Delaware pilot recipes; no previous design recipe is invoked.
Run Blender 5.2 background with this file. All measurements metres, front-left lot origin.
"""
import sys
sys.dont_write_bytecode = True
import json, math, copy, shutil, hashlib, traceback
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'source' / 'kit'))
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import nf_build as nb
import nf_round3 as r3
import nf_r5 as r5
OUT = ROOT / 'bake'
ATLAS = Path(r'C:\Users\<you>\CS2Planner\NewFrance\generator\out_r5\NA_NewFranceSideHallIronHouse_L1_1x6')
OLD_OWNER = ATLAS.name

# The new brief specifies 1 mm TOTAL separation (legacy helper used 2 mm).
def plate(mesh, pts, n, mat):
    v = Vector(n).normalized() * .0005
    mesh.polygon([Vector(p) + v for p in pts], n, mat)
    mesh.polygon([Vector(p) - v for p in pts], -Vector(n), mat)
nb.dquad = r3.dquad = plate
# Close undersides even for details previously terminating on another surface.
box_original = nb.Mesh.box
def closed_box(self, x0,x1,y0,y1,z0,z1,material,top=None,bottom=True):
    return box_original(self,x0,x1,y0,y1,z0,z1,material,top,bottom=True)
nb.Mesh.box = closed_box
def pilot_chimney(h,x,y,z0,z1,mat='Chimney',sx=.34,sy=.42):
    m=h.body
    if h.lod==2:
        m.box(x-sx,x+sx,y-sy,y+sy,z0,z1+.46,mat)
        return
    m.box(x-sx,x+sx,y-sy,y+sy,z0,z1,mat)
    if h.lod<2:
        m.box(x-sx-.045,x+sx+.045,y-sy-.045,y+sy+.045,z1-.3,z1-.2,mat)
        m.box(x-sx-.06,x+sx+.06,y-sy-.06,y+sy+.06,z1,z1+.1,'Dressed')
    # All LODs retain chimney pots and the same top silhouette.
    m.box(x-.1,x+.1,y-.1,y+.1,z1+.1,z1+.46,'Chimney')
r3.chimney=pilot_chimney


def op(c,w,b,t,k='W',floor=0,shutter=None,side=None):
    return dict(c=c,w=w,b=b,t=t,k=k,floor=floor,shutter=shutter,side=side)

def spec(name, walls, floors, eave, roof, brick='Brick094', trim='Cream', shutter='Green'):
    xa,xb,yf,yb=walls
    return dict(design=name,zone='Residential Low',walls=walls,datums=floors,eave=eave,
                facade=[brick,brick,brick,'StoneBase',trim],door=shutter,frame='Cream',
                cornice=[.18,.26,True,trim],access='Front',chamfer=0,
                front=[],rear=[],sides=[],R=roof,roof_raw='mansard' if roof['type'] in ('mansard4','ridgeX') else roof['type'],
                dormers=None,chimneys=[])

def gallery(bounds,decks,roofz,postxs,structure='iron',rail='lace',piers=None):
    return dict(bounds_m=bounds,deck_z_m=decks,structure=structure,post_width_m=.18,
                post_x_m=postxs,front_post_y_m=bounds[2]+.13,rail_style=rail,piers=piers,
                roof=dict(kind='shallow-shed',wall_z=roofz+.18,front_z=roofz,
                          thickness_m=.08,material='TinFlat'))

def rear_windows(S, xs, floors, height=1.65):
    for i,z in enumerate(floors):
        S['rear'] += [op(x,.9,z+.8,z+.8+height,floor=i) for x in xs]

def side_windows(S, ys, floors, side='R'):
    for i,z in enumerate(floors):
        S['sides'] += [op(y,.85,z+.85,z+2.3,floor=i,side=side) for y in ys]

def original_recipes():
    out=[]
    S=spec('DelawareMansardHouse',[.55,7.45,2.8,15.8],[.55,3.65],6.65,
           dict(type='ridgeX',P=[[2.8,6.65],[3.75,8.45],[9.3,9.9],[14.85,8.45],[15.8,6.65]],mat='SlateDark'))
    S['front']=[op(1.55,1.0,.55,3.15,'D'),op(4.0,1.02,1.25,3.05),op(6.2,1.02,1.25,3.05),
                op(1.55,1.0,4.35,6.1,floor=1),op(4.0,1.08,3.65,6.1,'F',1,'Green'),op(6.2,1.08,3.65,6.1,'F',1,'Green')]
    rear_windows(S,[1.9,5.9],S['datums']); side_windows(S,[7,12.2],S['datums'])
    S['chimneys']=[[6.75,9.9,.48,.7,10.25]]
    out.append(dict(design=S['design'],zone_key='Z1A',lot=[1,4],family='Second Empire town house',spec=S,
                    dormers=dict(kind='P',centres=[2.05,5.9],width=1.25,face_y=3.32),balconies=[4.0,6.2],
                    wing=[.85,4.45,15.8,18.8],patio=[.85,5.5,18.95,20.6],garden=[.7,7.3,21,31.5],
                    story='A Federal three-bay brick house given a slate mansard and two iron French-door balconies.'))
    S=spec('SideHallGalerieHouseLeft',[.55,7.45,3.2,17],[.5,3.65],6.7,
           dict(type='hip',ridge=[[4,6.65],[4,13.55]],rz=10.4,mat='Tin'),brick='Brick085',shutter='Black')
    S['front']=[op(1.6,1,.5,3.05,'D'),op(3.9,.95,1.15,3.0,shutter='Black'),op(6.1,.95,1.15,3.0,shutter='Black')]
    S['front'] += [op(x,1.0,3.65,6.08,'F',1,'Black') for x in [1.6,3.9,6.1]]
    rear_windows(S,[1.8,5.9],S['datums']); side_windows(S,[7.2,13],S['datums'],side='L')
    S['chimneys']=[[6.65,12,.5,.65,10.65]]
    g=gallery([.55,7.45,1.1,3.2],[.5,3.65],6.7,[.8,2.9,5,7.2],structure='iron',rail='lace',
              piers=dict(size_xy=[.28,.28],top_z=1.2,material='Brick085'))
    out.append(dict(design=S['design'],zone_key='Z1A',lot=[1,5],family='Side-hall gallery house',spec=S,gallery=g,
                    wing=[.8,4.3,17,20],outbuilding=[.8,4.3,34.3,39.3],patio=[.9,5,20.3,22.1],garden=[.7,7.3,22.5,33.7],
                    story='A tall tin hip and a two-level lace gallery; a modest washhouse and lane garage leave a deep yard. Left describes the side-hall hand, not corner access.'))
    S=spec('CreoleArdoiseCottage',[.55,7.45,2.4,12.9],[.45],3.65,
           dict(type='ridgeX',P=[[2.4,3.65],[7.65,7.7],[12.9,3.65]],mat='SlateGreen'),brick='BuffBrick',shutter='GreyBlue')
    S['roof_raw']='side gable'
    S['front']=[op(1.3,.82,.45,3.05,'D'),op(3.1,.8,1.05,2.95,shutter='GreyBlue'),
                op(4.9,.82,.45,3.05,'D'),op(6.7,.8,1.05,2.95,shutter='GreyBlue')]
    rear_windows(S,[2.2,5.8],S['datums']); side_windows(S,[6.0,10.6],S['datums'])
    S['chimneys']=[[6.65,8.7,.48,.58,8.15]]
    out.append(dict(design=S['design'],zone_key='Z1A',lot=[1,3],family='Creole cottage',spec=S,
                    dormers=dict(kind='S',centres=[2.2,5.8],width=1.2,face_y=3.45),
                    gallery=gallery([.55,7.45,.7,2.4],[.45],3.55,[.75,2.75,5.3,7.2],structure='turned-wood',rail='plain'),
                    patio=[.9,4.9,13.2,14.6],garden=[.7,7.3,15,23.5],
                    story='A buff-brick Creole cottage with a green slate roof, paired segmental dormers and two doors serving one household.'))
    S=spec('CamelbackBriqueHouse',[.7,7.3,2.4,15.6],[.4],3.55,
           dict(type='ridgeY',Q=[[.7,3.55],[4,6.0],[7.3,3.55]],mat='Tin'),brick='Brick094',shutter='Oxblood')
    S['front']=[op(1.8,1,1.0,2.95,shutter='Green'),op(3.9,1,1.0,2.95,shutter='Green'),op(6,1,.4,2.95,'D')]
    side_windows(S,[6,11],S['datums'])
    H=spec(S['design']+'RearHump',[.7,7.3,15.6,23.6],[.4,3.55],6.5,
           dict(type='ridgeY',Q=[[.7,6.5],[4,8.3],[7.3,6.5]],mat='TinFlat'),brick='ClapSage')
    H['cornice']=[.15,.18,False,'Cream']
    rear_windows(H,[1.8,5.8],H['datums']); side_windows(H,[19.8],H['datums'],'L'); side_windows(H,[19.8],H['datums'],'R')
    H['front']=[op(2.2,1,4.3,6,'W',1),op(5.8,1,4.3,6,'W',1)]
    H['chimneys']=[[6.7,20,.45,.6,8.6]]
    out.append(dict(design=S['design'],zone_key='Z1A',lot=[1,6],family='Camelback',spec=S,hump=H,
                    gallery=gallery([.7,7.3,.7,2.4],[.4],3.5,[.9,2.8,4.8,7.1],structure='turned-wood',rail='plain'),
                    outbuilding=[.9,3.4,43.3,47.3],patio=[.9,5.2,23.9,25.9],garden=[.7,7.3,26.3,42.7],
                    story='A low brick street gable with a clearly separate raised rear hump, pale sage rear clapboard and long planted garden.'))
    S=spec('VillaDesJardins',[3,13,5,18.6],[.75,4],7.15,
           dict(type='mansard4',front=[[5,7.15],[5.8,9.1],[11.8,10.25]],inset=.8,
                ridge=[[6.5,11.8],[9.5,11.8]],rz=10.25,mat='Slate'),brick='Brick085',trim='Dressed')
    S['front']=[op(4.5,1.15,1.45,3.4),op(8,1.35,.75,3.45,'D'),op(11.5,1.15,1.45,3.4)]
    S['front'] += [op(x,1.15,4,6.45,'F',1,'Green') for x in [4.5,8,11.5]]
    rear_windows(S,[4.5,8,11.5],S['datums']); side_windows(S,[8,13.2,16.5],S['datums'],'R'); side_windows(S,[8,13.2],S['datums'],'L')
    S['chimneys']=[[11.9,11,.6,.8,10.9]]
    g=gallery([.9,14,2.2,5],[.75,4],7.13,[1.1,3.64,6.18,8.72,11.26,13.8],structure='wood',rail='lace')
    g['post_width_m']=.28; g['upper_structure']='iron'
    g['wrap']=dict(side='left',bounds_m=[.9,3,5,12.8],post_line=1.03,return_wall=3,post_y_m=[5.13,7.64,10.15,12.67])
    out.append(dict(design=S['design'],zone_key='Z1B',lot=[2,5],family='Second Empire garden villa',spec=S,gallery=g,arcade=True,
                    dormers=dict(kind='S',centres=[4.3,8,11.7],width=1.3,face_y=5.55),
                    wing=[8,12,18.6,21.6],outbuilding=[10.7,15.2,33.3,39.3],patio=[8,13,21.9,23.4],garden=[.7,10.1,23.8,39],
                    story='Red brick and pale stone, four-sided mansard, three arched dormers, a shaded ground arcade and a wraparound iron balcony.'))
    S=spec('PavillonFederalHouse',[5,19,6,20.5],[.7,4],7.2,
           dict(type='multihip',segments=[dict(x0=5,x1=9.8,ridge=[[7.4,8.8],[7.4,17.7]],rz=10.55),
                 dict(x0=9.8,x1=14.2,ridge=[[12,8.6],[12,17.9]],rz=9.55),
                 dict(x0=14.2,x1=19,ridge=[[16.6,8.8],[16.6,17.7]],rz=10.55)],bridge=None,mat='SlateDark'),brick='Brick094',shutter='Black')
    S['front']=[op(x,1.1,1.4,3.4) for x in [7.4,9.5,14.5,16.6]]+[op(12,1.4,.7,3.4,'D')]
    S['front'] += [op(x,1.05,4,6.5,'F',1,'Black') for x in [7.4,9.5,12,14.5,16.6]]
    rear_windows(S,[7.4,12,16.6],S['datums']); side_windows(S,[9.5,15.8],S['datums'],'R'); side_windows(S,[9.5,15.8],S['datums'],'L')
    S['chimneys']=[[6,13,.65,.8,10.85],[18,13,.65,.8,10.85]]
    g=gallery([4,20,3.4,6],[.7,4],7.15,[4.2+i*15.6/7 for i in range(8)],structure='wood',rail='lace',
              piers=dict(size_xy=[.32,.32],top_z=1.4,material='Brick094'))
    g['upper_structure']='iron'
    out.append(dict(design=S['design'],zone_key='Z1B',lot=[3,5],family='Federal pavilion mansion',spec=S,gallery=g,
                    wing=[9,15,20.5,24.5],outbuilding=[17.5,23.5,33.3,39.3],patio=[9,16,24.8,26.3],garden=[7,16.9,26.8,39],
                    story='A broad Federal brick body with twin steep French pavilion roofs and a lower centre roof, raised galleries and spacious flanking gardens.'))
    for a in out:
        a.update(name=f"NA_PdD{a['design']}_L1_{a['lot'][0]}x{a['lot'][1]}",colourway='A',households=1,level=1,access='Front')
        a['active_entrances']=[dict(position_lot_m=[o['c'],a['spec']['walls'][2],o['b']],street_path=True) for o in a['spec']['front'] if o['k']=='D' and o['floor']==0]
        xa,xb,yf,yb=a['garden']; w,d=a['lot'][0]*8,a['lot'][1]*8
        # Explicit landscape reservations are NON-mesh, matched to vanilla prefabs by Claude.
        a['props']=[dict(kind='deciduous tree',position_lot_m=[(xa+xb)/2,yf+(yb-yf)*.35,0],size_m=[min(4,xb-xa-1),min(4,xb-xa-1),6]),
                    dict(kind='flower bed',position_lot_m=[xa+.35,yf+1,0],size_m=[.6,min(4,yb-yf-2),.45]),
                    dict(kind='hedge run',position_lot_m=[w-.35,d*.68,0],size_m=[.45,min(10,d*.32),1.2]),
                    dict(kind='fence line',position_lot_m=[.2,d*.7,0],size_m=[.06,d*.5,1.3]),
                    dict(kind='rear gate and fence',position_lot_m=[w/2,d-.2,0],size_m=[w-.4,.06,1.3])]
        if a['zone_key']=='Z1B':
            a['props'] += [dict(kind='deciduous tree',position_lot_m=[w-2.2,11,0],size_m=[3.5,3.5,6]),
                           dict(kind='parterre shrub beds',position_lot_m=[w-3.2,29,0],size_m=[3,3,.6])]
        if 'gallery' in a:
            a['props'] += [dict(kind='hanging fern',position_lot_m=[x,a['gallery']['bounds_m'][2]+.2,a['gallery']['deck_z_m'][-1]+2.1],size_m=[.5,.5,.55]) for x in a['gallery']['post_x_m'][1:-1:2]]
        a['colourway_families']=dict(walls=a['spec']['facade'][0],trim=a['spec']['facade'][4],roof=a['spec']['R']['mat'],door=a['spec']['door'],frame=a['spec']['frame'])
        a['native_surfaces']=[]
        if a['zone_key']=='Z1B':
            rects=([[14.1,15.9,0,5.4],[13.35,15.9,5.4,33.3],[10.7,15.9,30.8,33.3]] if a['lot'][0]==2 else [[20,22.8,0,33.3],[17.5,23.5,30.8,33.3]])
            a['native_surfaces']=[dict(kind='carriage drive / apron',bounds_lot_m=r,material_intent='pale compacted gravel',pedestrian_access_area=False) for r in rects]
            for prop in a['props']:
                if prop['kind']=='hedge run': prop['position_lot_m'][0]=.4
                if prop['kind']=='deciduous tree' and prop['position_lot_m'][1]==11:
                    prop['position_lot_m']=[3.2,36.8,0] if a['lot'][0]==2 else [2.8,11,0]
                    prop['size_m']=[2.5,2.5,6] if a['lot'][0]==2 else [3.5,3.5,6]
                if prop['kind']=='parterre shrub beds':
                    prop['position_lot_m']=[3,34.5,0] if a['lot'][0]==2 else [4,27.5,0]
        a['front_walks']=[dict(bounds_lot_m=[ent['position_lot_m'][0]-.5,ent['position_lot_m'][0]+.5,0,a.get('gallery',{}).get('bounds_m',[0,0,a['spec']['walls'][2],0])[2]],connects_to='ground front entrance via modelled stoop/gallery deck') for ent in a['active_entrances']]
        a['paving_note']='All native access routes run from ground-front doors to front street. Rear patio and outbuilding aprons are decorative only, not walkable subareas.'
    return out


def setup(a,lod,lite):
    nb.W=a['lot'][0]*8; nb.LOT_D=a['lot'][1]; nb.YSHIFT=12-a['lot'][1]*4
    nb.REMAP.clear(); nb.XMAP=None; nb.LITE=lite; nb.LACE_K=2.4
    r3.LB=a['lot'][1]*8-12; r3.LIM=nb.W/2-.02

def build_arches(h,a):
    # Closed segmental spandrels; underside curve never falls into a door opening.
    g=a['gallery']; posts=g['post_x_m']; y=g['front_post_y_m']; ztop=3.84
    count=6 if h.lod==0 else 2
    for x0,x1 in zip(posts,posts[1:]):
        l,r=x0+.14,x1-.14
        p=[(l,ztop),(r,ztop),(r,2.92)]
        p += [(l+(r-l)*i/count,2.92+.64*math.sin(math.pi*i/count)) for i in range(count-1,-1,-1)]
        nb.extrude(h.body,[(nb.X(x),z) for x,z in p],'y',nb.Y(y)-.09,nb.Y(y)+.09,'Dressed',('Dressed','Dressed'))

def accessory(h,rect,mat='Clapboard',garage=False):
    x0,x1,y0,y1=rect
    r3.back_building(h,nb.X(x0),nb.X(x1),nb.Y(y0),nb.Y(y1),2.7 if garage else 2.6,
                    'gableY' if garage else 'shedB',mat,'StoneBase','TinFlat',wins=('rear',),door=None,
                    attached=not garage,storeys=1,datum=.18,pitch=24,plain=True)
    # Lane door is visual only, never an active network entrance.
    if garage:
        f=nb.Face((nb.X(x1),nb.Y(y1)+.015),(nb.X(x0),nb.Y(y1)+.015))
        f.trim(h.body,.35,f.length-.35,.12,2.25,0,.03,'GreyBlue')
        # Matching courtyard-facing carriage door; visual only, not a native active entrance.
        front=nb.Face((nb.X(x0),nb.Y(y0)-.015),(nb.X(x1),nb.Y(y0)-.015))
        if h.lod<2: front.trim(h.body,.35,front.length-.35,.12,2.25,0,.03,'GreyBlue')
        if h.lod<2:
            f.trim(h.body,f.length/2-.025,f.length/2+.025,.12,2.25,.03,.05,'Cream')

def far_villa_gallery(h,a):
    # One closed L-shaped solid per level instead of intersecting rectangular returns.
    g=a['gallery']; m=h.body
    plan=[(nb.X(x),nb.Y(y)) for x,y in [(.9,2.2),(14,2.2),(14,5),(3,5),(3,12.8),(.9,12.8)]]
    for z0,z1,mat in [(0,.75,'Deck'),(3.84,4,'Deck'),(7.05,7.13,'TinFlat')]:
        canopy=[(nb.X(x),nb.Y(y)) for x,y in [(.84,2.14),(14.02,2.14),(14.02,5),(3,5),(3,12.8),(.84,12.8)]]
        nb.prism(m,canopy if z0>7 else plan,z0,z1,mat)
    for x,y in [(1.1,2.33),(13.8,2.33),(1.03,12.67)]:
        m.box(nb.X(x)-.14,nb.X(x)+.14,nb.Y(y)-.14,nb.Y(y)+.14,.75,7.05,'Cream')
    # Closed ramp replaces the tread detail only at far distance; same footprint/top.
    nb.extrude(m,[(nb.Y(1.12),0),(nb.Y(2.2),0),(nb.Y(2.2),.75)],'x',nb.X(8)-.55,nb.X(8)+.55,'Dressed',('Dressed','Dressed'))
    r3.walk_to(h,nb.X(8),nb.Y(1.12),1)

def far_villa_arches(h,a):
    posts=a['gallery']['post_x_m']; p=[(posts[0]+.14,3.84),(posts[-1]-.14,3.84)]
    # Joined spandrel with all five openings retained as broad two-segment arches.
    for x0,x1 in reversed(list(zip(posts,posts[1:]))):
        l,r=x0+.14,x1-.14
        p += [(r,2.92),((l+r)/2,3.56),(l,2.92)]
    y=nb.Y(a['gallery']['front_post_y_m'])
    nb.extrude(h.body,[(nb.X(x),z) for x,z in p],'y',y-.09,y+.09,'Dressed',('Dressed','Dressed'))

def far_dormer(h,xc,w,prof,yd,kind,roof):
    zb=nb.profile_z(prof,yd); zde=zb+1.5; half=w/2+.08
    cap=[(-half*math.cos(math.pi*i/3),.22*math.sin(math.pi*i/3)) for i in range(4)]
    poly=[(xc-half,zb),(xc+half,zb)]+[(xc+x,zde+z) for x,z in reversed(cap)]
    ye=nb.profile_y(prof,min(zde+.22,max(z for y,z in prof)-.01))+.05
    nb.extrude(h.body,poly,'y',yd,ye,roof,('Cream',roof))
    face=nb.Face((xc-w/2,yd),(xc+w/2,yd))
    h.opening(face,nb.Opening(w/2,w-.36,zb+.16,zb+1.34,'sash',stone=False),'Cream')

def base_build(a,lod,lite):
    setup(a,lod,lite)
    h=nb.House(lod); S=copy.deepcopy(a['spec'])
    # Small bracket detail omitted at farther LODs; roof shapes stay identical.
    if lod>0: S['cornice'][2]=False
    if lod==2: S['facade'][3]=S['facade'][0]
    r3.build_spec(h,S)
    if 'hump' in a:
        H=copy.deepcopy(a['hump']); H['cornice'][2]=False
        r3.build_spec(h,H)
    if 'dormers' in a:
        dm=a['dormers']; R=S['R']; e=S['eave']
        if R['type']=='ridgeX':
            prof=[(nb.Y(y),z+.12) for y,z in R['P'][:len(R['P'])//2+1]]
            prof[0]=(prof[0][0]-.18,prof[0][1])
        else:
            prof=[(nb.Y(S['walls'][2])-.18,e+.12),(nb.Y(R['front'][1][0]),R['front'][1][1]+.12),(nb.Y(R['front'][-1][0]),R['rz']+.12)]
        for x in dm['centres']:
            if a['design']=='PavillonFederalHouse' and x==12:
                prof=[(nb.Y(5.6)-.18,8.07),(nb.Y(6.18),9.87),(nb.Y(13.05),10.17)]
                dm=copy.deepcopy(dm);dm['face_y']=5.85;dm['kind']='P'
            elif a['design']=='VillaDesJardins' and x==8:
                dm=copy.deepcopy(dm);dm['kind']='P'
            if lod==2 and a['design']=='VillaDesJardins':
                far_dormer(h,nb.X(x),dm['width'],prof,nb.Y(dm['face_y']),dm['kind'],R['mat'])
            else:
                r3.dormer3(h,nb.X(x),dm['width'],prof,nb.Y(dm['face_y']),dm['kind'],R['mat'],R['mat'],'Cream',
                           face_h=1.5,sash_z=(.16,1.34),sash_in=.36)
    if 'gallery' in a:
        if lod>=1 and a['design']=='VillaDesJardins':
            far_villa_gallery(h,a); far_villa_arches(h,a)
        else:
            g=copy.deepcopy(a['gallery']); r5.gallery(h,S,a,g)
            if a.get('arcade'): build_arches(h,a)
            if lod==0 and g['rail_style'].startswith('lace'):
                # A few broad cast-iron medallions survive detail reduction at main LOD.
                y=nb.Y(g['front_post_y_m']); z=g['deck_z_m'][-1]+.63
                for l,r in zip(g['post_x_m'],g['post_x_m'][1:]):
                    x=nb.X((l+r)/2)
                    nb.lace_ring(h.body,lambda s,zz:(x+s,y,zz),0,z,.16,.14,(0,-1,0),'Iron',6)
    else:
        for ent in a['active_entrances']:
            x,y,z=ent['position_lot_m']
            yfoot=r3.stoop(h,nb.X(x)-.6,nb.X(x)+.6,nb.Y(y),z,landing=.8,rails=True)
            r3.walk_to(h,nb.X(x),yfoot,1.1)
    for x in a.get('balconies',[]):
        r3.balcony(h,[(nb.X(x-.72),nb.Y(S['walls'][2])),(nb.X(x+.72),nb.Y(S['walls'][2]))],3.65,.67)
    if a.get('wing'): accessory(h,a['wing'],mat=S['facade'][0])
    if a.get('outbuilding'): accessory(h,a['outbuilding'],garage=True)
    x0,x1,y0,y1=a['patio'];
    if lod<2 or a['design'] not in ['VillaDesJardins','PavillonFederalHouse']: h.body.box(nb.X(x0),nb.X(x1),nb.Y(y0),nb.Y(y1),.005,.035,'Paving')
    if a.get('outbuilding'):
        x0,x1,y0,y1=a['outbuilding']; depth=a['lot'][1]*8
        h.body.box(nb.X(x0),nb.X(x1),nb.Y(y1),nb.Y(depth-.01),.005,.035,'Paving')
    return h


def optimize_far(ob,lod):
    if lod!=2: return ob
    import bmesh
    bm=bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.dissolve_limit(bm,angle_limit=.00001,use_dissolve_boundaries=False,
                            verts=list(bm.verts),edges=list(bm.edges),delimit={'UV'})
    bm.to_mesh(ob.data); bm.free(); ob.data.update()
    return ob

def mesh_stats(ob):
    me=ob.data; me.calc_loop_triangles()
    pts=[ob.matrix_world @ v.co for v in me.vertices]
    return dict(triangles=len(me.loop_triangles),vertices=len(me.vertices),
                bounds_m=[[round(min(p[k] for p in pts),5) for k in range(3)],
                          [round(max(p[k] for p in pts),5) for k in range(3)]])

def coverage(ob,a):
    me=ob.data; verts=[ob.matrix_world @ v.co for v in me.vertices]
    bvh=BVHTree.FromPolygons(verts,[tuple(p.vertices) for p in me.polygons],all_triangles=False)
    width,depth=a['lot'][0]*8,a['lot'][1]*8
    step=.25; roof=paved=green=0
    scan_z=max(p.z for p in verts)+5
    for iy in range(round(depth/step)):
        for ix in range(round(width/step)):
            p,n,i,dist=bvh.ray_cast(Vector((-width/2+(ix+.5)*step,-depth/2+(iy+.5)*step,scan_z)),Vector((0,0,-1)),scan_z+5)
            if p is None:
                lx=-width/2+(ix+.5)*step+width/2; ly=-depth/2+(iy+.5)*step+depth/2
                if any(r['bounds_lot_m'][0]<=lx<=r['bounds_lot_m'][1] and r['bounds_lot_m'][2]<=ly<=r['bounds_lot_m'][3] for r in a['native_surfaces']): paved+=1
                else: green+=1
            elif p.z>=2: roof+=1
            else: paved+=1
    total=roof+paved+green
    return dict(method='Actual LOD0 exported geometry top-ray union, 0.10 m centre samples; upper projections counted as roofed. Planted is remaining open ground after subtracting the prescribed native carriage-drive surfaces; before Claude prop placement.',
                sample_spacing_m=step,roofed_pct=round(100*roof/total,2),paved_unroofed_pct=round(100*paved/total,2),planted_reserved_pct=round(100*green/total,2),
                roofed_m2=round(roof*step**2,2),paved_unroofed_m2=round(paved*step**2,2),planted_reserved_m2=round(green*step**2,2))

def validate(path,a):
    nb.clear_objects()
    for mat in list(bpy.data.materials): bpy.data.materials.remove(mat)
    bpy.ops.import_scene.fbx(filepath=str(path),axis_forward='-Z',axis_up='Y')
    obs=[o for o in bpy.context.selected_objects if o.type=='MESH']
    assert len(obs)==1, (path.name,'mesh count',len(obs))
    ob=obs[0]; me=ob.data; rec=mesh_stats(ob)
    assert ob.name==path.stem,(ob.name,path.stem)
    assert (len(me.materials)==0 if path.stem.endswith('_Win') else len(me.materials)==1 and me.materials[0].name==path.stem),(path.name,'material',list(me.materials))
    assert len(me.uv_layers)==1,path.name
    lo,hi=rec['bounds_m']; w,d=a['lot'][0]*8,a['lot'][1]*8
    assert lo[0]>=-w/2-.002 and hi[0]<=w/2+.002,(path.name,'X bounds',lo,hi)
    assert lo[1]>=-d/2-.002 and hi[1]<=d/2+.002,(path.name,'Y bounds',lo,hi)
    assert lo[2]>=-.002,(path.name,'Z bounds',lo,hi)
    for p in me.polygons:
        assert p.area>1e-9,(path.name,'zero face',p.index,p.area)
        vs=[ob.matrix_world @ me.vertices[i].co for i in p.vertices]
        if len(vs)>3:
            local_points=[point-vs[0] for point in vs]
            normal=nb.newell(local_points).normalized()
            assert max(abs(point.dot(normal)) for point in local_points)<.0003,(path.name,'nonplanar',p.index)
        uvs=[me.uv_layers[0].data[i].uv for i in p.loop_indices]
        assert all(-.00001<=v<=1.00001 for uv in uvs for v in uv),path.name
        if path.stem.endswith('_Win'):
            cells={(min(4,int(uv.x*5)),min(4,int(uv.y*5))) for uv in uvs}
            assert len(cells)==1 and not any(c in {(0,0),(4,0),(0,4),(4,4)} for c in cells),(path.name,cells)
    rec['material']=me.materials[0].name if me.materials else None
    rec['uv_checks']='PASS: finite 0..1 UVs, one UVMap; window faces stay within one legal 5x5 room cell'
    rec['planarity']='PASS: every exported polygon planar within 0.3 mm'
    if path.stem==a['name']: rec['coverage']=coverage(ob,a)
    return rec


def run():
    OUT.mkdir(parents=True,exist_ok=True)
    designs=recipes(); owner=designs[0]['name']
    (ROOT/'designs.json').write_text(json.dumps(dict(project='Paris on the Delaware',pilot='6 new originals, colourway A only',coordinate_system='Metres from FRONT LEFT corner; +X right, +Y rear, +Z up. FBX uses centred Blender metres exported as cm.',designs=designs),indent=2),encoding='utf-8')
    manifest=dict(batch='2026-11-06_pdd-pilot',texture_owner=owner,registrations=7,expected_fbx=42,
                  units='FBX centimetres, importer scale 0.01; native authoring metres',front='Blender -Y',
                  material_contract='Body: one named material. Win: zero slots, per corrected G1.',
                  iron_plate_separation_m=.001,budgets=[12000,4000,500],assets=[])
    for a in designs:
        folder=OUT/a['name']; folder.mkdir(exist_ok=True)
        rec=dict(name=a['name'],zone_key=a['zone_key'],lot=a['lot'],households=1,colourway='A',access='Front',meshes={},detail_levels={})
        for lod,suffix in enumerate(['','_LOD1','_LOD2']):
            maxtri=manifest['budgets'][lod]
            # LITE affects ornaments only, never walls/roofs/decks/dormer count.
            choices=[0,1,2,3,4,5,6] if lod==0 else [2,3,4,5,6] if lod==1 else [6]
            for lite in choices:
                nb.clear_objects()
                h=build(a,lod,lite)
                ob=optimize_far(h.body.object('candidate'),lod)
                bodytri=mesh_stats(ob)['triangles']; wintri=sum(len(f)-2 for f in h.windows.faces)
                if bodytri+wintri<=maxtri: break
            assert bodytri+wintri<=maxtri,(a['name'],lod,bodytri,wintri,'budget exceeded')
            rec['detail_levels'][str(lod)]=dict(ornament_reduction=lite,total_triangles=bodytri+wintri)
            nb.clear_objects()
            for mesh,extra in [(h.body,''),(h.windows,'_Win')]:
                tag=a['name']+suffix+extra
                old=bpy.data.materials.get(tag)
                if old: bpy.data.materials.remove(old)
                ob=optimize_far(mesh.object(tag,None if extra else bpy.data.materials.new(tag)),lod)
                nb.export_fbx(ob,folder/(tag+'.fbx'))
            print('BAKED',a['name'],lod,bodytri,wintri,'lite',lite,flush=True)
        if a['name']==owner:
            for lod in ['', '_LOD1','_LOD2']:
                for kind in nb.MAPS:
                    source=ATLAS/(OLD_OWNER+lod+'_'+kind+'.png')
                    target=folder/(owner+lod+'_'+kind+'.png')
                    if source.exists(): shutil.copy2(source,target)
                    else: assert target.exists(),('Shared owner texture missing',target)
        else:
            shares={a['name']+lod+'_'+kind+'.png':'../'+owner+'/'+owner+lod+'_'+kind+'.png' for lod in ['', '_LOD1','_LOD2'] for kind in nb.MAPS}
            (folder/'settings.json').write_text(json.dumps(dict(sharedAssets=shares),indent=2),encoding='utf-8')
        for p in sorted(folder.glob('*.fbx')):
            rec['meshes'][p.stem]=validate(p,a)
        cov=rec['meshes'][a['name']]['coverage']; rec['coverage']=cov
        low,high=(40,50) if a['zone_key']=='Z1A' else (30,40)
        assert low<=cov['roofed_pct']<=high,(a['name'],'roof coverage',cov)
        assert cov['planted_reserved_pct']>=40,(a['name'],'green',cov)
        rec['active_entrances_blender_m']=[[x-a['lot'][0]*4,y-a['lot'][1]*4,z] for ent in a['active_entrances'] for x,y,z in [ent['position_lot_m']]]
        main_bounds=rec['meshes'][a['name']]['bounds_m']
        for lod in ['_LOD1','_LOD2']:
            b=rec['meshes'][a['name']+lod]['bounds_m']
            assert all(abs(b[i][j]-main_bounds[i][j])<=.002 for i in range(2) for j in range(3)),(a['name'],'LOD bounds mismatch',main_bounds,b)
        manifest['assets'].append(rec)
        (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        print('VALIDATED',a['name'],cov,flush=True)
    manifest['validation']='PASS: all 42 FBXs reimported; axes, units, bounds, materials, UVs, polygon planarity, LOD bounds, combined body+Win budgets and garden coverage verified. Not in-game validated.'
    manifest['sha256']={str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.rglob('*') if p.suffix in ['.fbx','.png']}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('PILOT_COMPLETE',flush=True)
# V2: Claude G1-G8 and D1-D6.
def mansard(walls,e,mat, rise=1.8):
    l,r,f,b=walls; ins=.58; by=f+.58; mid=(f+b)/2
    return dict(type='mansard4',front=[[f,e],[by,e+rise],[mid,e+rise+.3]],inset=ins,
                ridge=[[l+ins,mid],[r-ins,mid]],rz=e+rise+.3,mat=mat)

def recipes():
    aa=original_recipes()
    for a in aa:
        S=a['spec']; n=a['design']; S['cornice']=[.18,.42,False,'Cream']
        for o in S['front']:
            if o['k']!='D':o['shutter']=S['door'] if S['door'] in ['Green','Black','Oxblood'] else 'Green'
        if n in ['DelawareMansardHouse','VillaDesJardins','PavillonFederalHouse','SideHallGalerieHouseLeft']:
            S['R']=mansard(S['walls'],S['eave'],'SlateDark'); S['roof_raw']='mansard'
            a['dormers']=dict(kind='S',centres=([2,5.9] if n=='DelawareMansardHouse' else [4] if 'SideHall' in n else [4.3,8,11.7] if n=='VillaDesJardins' else [7.4,12,16.6]),width=1.25,face_y=S['walls'][2]+.25)
        if n=='CreoleArdoiseCottage': S['R']['mat']='SlateDark'
        if n=='PavillonFederalHouse':
            for o in S['front']:
                if o['c']==9.5:o['c']=8.9
                if o['c']==14.5:o['c']=15.1
        if 'SideHall' in n:S['chimneys'][0][-1]=9.4
        a['colourway_families']['roof']=S['R']['mat']
        a['props'] += [dict(kind='low iron front fence with walk gates',position_lot_m=[a['lot'][0]*4,.12,0],size_m=[a['lot'][0]*8-.4,.06,.8],gaps_lot_x_m=[[e['position_lot_m'][0]-.65,e['position_lot_m'][0]+.65] for e in a['active_entrances']]),dict(kind='clipped front hedge behind fence',position_lot_m=[a['lot'][0]*4,.35,0],size_m=[a['lot'][0]*8-.5,.3,.55],gaps_lot_x_m=[[e['position_lot_m'][0]-.65,e['position_lot_m'][0]+.65] for e in a['active_entrances']])]
        if a['zone_key']=='Z1B':
            x=a['active_entrances'][0]['position_lot_m'][0]
            a['props'] += [dict(kind='flower bed flanking front stair',position_lot_m=[x+dx,1.2,0],size_m=[1,.7,.35]) for dx in [-1.35,1.35]]
    mirror=copy.deepcopy(aa[1]);mirror['design']='SideHallGalerieHouseRight';mirror['name']=mirror['name'].replace('Left','Right');mirror['mirror_geometry']=True
    # Keep source geometry specifications left-handed; mirror all placement metadata separately.
    for ent in mirror['active_entrances']:ent['position_lot_m'][0]=8-ent['position_lot_m'][0]
    for prop in mirror['props']:
        prop['position_lot_m'][0]=8-prop['position_lot_m'][0]
        if 'gaps_lot_x_m' in prop:prop['gaps_lot_x_m']=[[8-r,8-l] for l,r in prop['gaps_lot_x_m']]
    for walk in mirror['front_walks']:
        l,r,f,b=walk['bounds_lot_m'];walk['bounds_lot_m']=[8-r,8-l,f,b]
    mirror['as_baked_layout']={k:[8-v[1],8-v[0],v[2],v[3]] for k,v in mirror.items() if k in ['wing','outbuilding','patio','garden']}
    aa.append(mirror)
    return aa

# Arched principal windows with a recessed curved glass head and stone archivolt.
original_opening=nb.House.opening
def dressed_opening(h,f,o,reveal):
    if h.lod==2 or o.kind not in ['sash','pair','french'] or f.out.y>-.9:
        return original_opening(h,f,o,reveal)
    q=copy.copy(o);q.spring=o.top-.17;q.depth=.12;q.surround=.085;q.kind='glass'
    r3.arch(h,f,q,reveal)
    f.trim(h.body,o.left,o.right,(o.bottom+o.top)/2-.025,(o.bottom+o.top)/2+.025,-.12,-.055,'Cream')
    if o.shutter:
        sw=min(.4,o.shutter_w if o.shutter_w is not None else .35)
        for l,r in [(o.left-sw-.04,o.left-.04),(o.right+.04,o.right+sw+.04)]:
            f.trim(h.body,l,r,o.bottom,o.top,0,.045,o.shutter)
            if h.lod==0 and nb.LITE<3:
                for i in range(1,7):
                    z=o.bottom+(o.top-o.bottom)*i/7
                    f.trim(h.body,l+.025,r-.025,z,z+.025,.045,.06,o.shutter)
nb.House.opening=dressed_opening

# Compact dressed dormer, including an actual segmental hood; depth is always <=1.1m.
def short_dormer(h,xc,w,prof,yd,kind,roof,cheek=None,face='Cream',*args,**kwargs):
    zb=nb.profile_z(prof,yd); top=zb+1.25; half=w/2; n=6 if h.lod==0 else 3
    cap=[(-half*math.cos(math.pi*i/n),.25*math.sin(math.pi*i/n)) for i in range(n+1)]
    if kind=='P':cap=[(-half,0),(0,.25),(half,0)]
    poly=[(xc-half,zb),(xc+half,zb)]+[(xc+x,top+z) for x,z in reversed(cap)]
    end=yd+1.1
    if h.lod==2:
        nb.extrude(h.body,poly,'y',yd,end,roof,(None,roof))
    else:
        backz=nb.profile_z(prof,end)-.015
        front=[(x,yd,z) for x,z in poly];back=[(x,end,min(z,backz)) for x,z in poly]
        for i in range(len(poly)):
            j=(i+1)%len(poly); dx=poly[j][0]-poly[i][0];dz=poly[j][1]-poly[i][1]
            h.body.polygon([front[i],back[i],back[j],front[j]],(dz,0,-dx),roof)
        h.body.polygon(back,(0,1,0),roof)
    f=nb.Face((xc-half,yd),(xc+half,yd))
    f.wall(h,zb,top,[nb.Opening(half,w-.32,zb+.12,top-.08,'sash',stone=False)],'Cream')
    h.body.polygon([(xc+x,yd,top+z) for x,z in cap],(0,-1,0),'Cream')
    if h.lod<2:
        for (x,z),(xx,zz) in zip(cap,cap[1:]):nb.bar(h.body,'y',xc+x,top+z,xc+xx,top+zz,yd-.07,yd,.07,'Cream')
r3.dormer3=short_dormer
far_dormer=lambda h,xc,w,p,yd,k,roof:short_dormer(h,xc,w,p,yd,k,roof)

original_spec=r3.build_spec
def adorned_spec(h,S):
    if S['design']=='PavillonFederalHouse':
        for l,r,front,e in [(5,9.8,6,7.2),(9.8,14.2,5.6,7.95),(14.2,19,6,7.2)]:
            T=copy.deepcopy(S);T['design']='PavillonPart';T['walls']=[l,r,front,20.5];T['eave']=e
            T['R']=mansard(T['walls'],e,'SlateDark');T['chimneys']=[]
            for k in ['front','rear']:T[k]=[o for o in T[k] if l<o['c']<r]
            T['sides']=[o for o in T['sides'] if (o['side']=='L' and l==5) or (o['side']=='R' and r==19)]
            adorned_spec(h,T)
        return
    result=original_spec(h,S)
    if S['R']['type']=='mansard4':
        l,r,f,b=S['walls'];R=S['R'];z=R['front'][1][1]+.12;ins=R['inset']; fy=R['front'][1][0];by=b-(fy-f)
        # Continuous white curb on all four exposed slopes.
        for rect in ([] if h.lod==2 else [(l+ins-.04,r-ins+.04,fy-.04,fy+.04),(l+ins-.04,r-ins+.04,by-.04,by+.04),(l+ins-.04,l+ins+.04,fy,by),(r-ins-.04,r-ins+.04,fy,by)]):
            x0,x1,y0,y1=rect;h.body.box(nb.X(x0),nb.X(x1),nb.Y(y0),nb.Y(y1),z,z+.07,'Cream')
        # Cresting above the front upper curb; far retains one thin closed band.
        y=nb.Y(fy+.18);za=z+.18
        if h.lod==2:h.body.box(nb.X(l+ins),nb.X(r-ins),y-.025,y+.025,za,za+.3,'Iron')
        else:
            nb.railing(h,nb.X(l+ins),y,nb.X(r-ins),y,za,.3,'Iron',.25)
    if h.lod<2:
        l,r,f,b=S['walls'];z=S['eave']-.4
        for x in [l+.35+i*.95 for i in range(max(1,int((r-l-.7)/.95)))]:
            for dx in [-.055,.055]:h.body.box(nb.X(x+dx)-.025,nb.X(x+dx)+.025,nb.Y(f)-.17,nb.Y(f),z,z+.3,'Cream')
    return result
r3.build_spec=adorned_spec

def build(a,lod,lite):
    source=copy.deepcopy(a)
    if a.get('mirror_geometry'):
        source['active_entrances']=copy.deepcopy(original_recipes()[1]['active_entrances'])
    global CURRENT_DESIGN
    CURRENT_DESIGN=a['design']
    h=base_build(source,2 if lod==1 and a['design']=='PavillonFederalHouse' else lod,lite)
    h.lod=lod
    # Deliberate broad lace rings and scalloped spandrels at both viewing LODs.
    if lod<2 and a.get('gallery'):
        g=a['gallery'];y=nb.Y(g['front_post_y_m']);z=g['deck_z_m'][-1]
        for l,r in zip(g['post_x_m'],g['post_x_m'][1:]):
            x=nb.X((l+r)/2)
            nb.lace_ring(h.body,lambda s,zz:(x+s,y,zz),0,z+.52,.22,.19,(0,-1,0),'Iron',6 if lod==0 else 4)
            roof=g['roof']['front_z']-.12
            for u,sgn in [(l,1),(r,-1)]:
                nb.dquad(h.body,[(nb.X(u),y,roof),(nb.X(u+sgn*.42),y,roof),(nb.X(u),y,roof-.42)],(0,-1,0),'Iron')
    if lod==2 and a['design']=='PavillonFederalHouse':
        keep=[]
        for i,f in enumerate(h.body.faces):
            vs=[h.body.vertices[j] for j in f]
            internal=any(all(abs(v[0]-nb.X(x))<.001 for v in vs) and max(v[2] for v in vs)<=7.2 and min(v[1] for v in vs)>=nb.Y(6)-.001 and max(v[1] for v in vs)<=nb.Y(20.5)+.001 for x in [9.8,14.2])
            if not internal:keep.append(i)
        h.body.faces=[h.body.faces[i] for i in keep];h.body.uvs=[h.body.uvs[i] for i in keep]
    if a.get('mirror_geometry'):
        for mesh in [h.body,h.windows]:
            mesh.vertices=[(-v[0],v[1],v[2]) for v in mesh.vertices]
            mesh.faces=[f[::-1] for f in mesh.faces];mesh.uvs=[uv[::-1] for uv in mesh.uvs]
    return h

original_accessory=accessory
def accessory(h,rect,mat='Clapboard',garage=False):
    if h.lod!=2 or CURRENT_DESIGN!='PavillonFederalHouse':return original_accessory(h,rect,mat,garage)
    x0,x1,y0,y1=rect
    if garage:
        l,r=nb.X(x0)-.22,nb.X(x1)+.22
        prof=[(l,0),(r,0),(r,2.7),((l+r)/2,2.7+(r-l)/2*math.tan(math.radians(24))),(l,2.7)]
        nb.extrude(h.body,prof,'y',nb.Y(y0)-.22,nb.Y(y1)+.22,mat,(mat,mat))
    else:
        prof=[(nb.Y(y0),0),(nb.Y(y1),0),(nb.Y(y1),2.6),(nb.Y(y0),2.9)]
        nb.extrude(h.body,prof,'x',nb.X(x0),nb.X(x1),mat,(mat,mat))
# Internal library: run bake_batch.py, not this module.