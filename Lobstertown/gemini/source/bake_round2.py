"""Round 2 pilot geometry and FBX export. Run with Blender 5.2 in background."""
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mathutils import Vector
import pilot_core as core
from coplanar import overlaps

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "bake"
nb, r3 = core.nb, core.r3
UP = Vector((0, 0, 1))
# At the far camera distance a broad atlas repeat saves triangles on large walls.
for cell in nb.LAYOUT["lods"]["_LOD2"].values():
    cell["metres"] = [max(24, span) for span in cell["metres"]]
LODS = ("", "_LOD1", "_LOD2")
STONE, SLATE, IRON, DOOR = "Dressed", "SlateDark", "Iron", "Green"
ATLAS = ROOT.parent / "2026-11-06_chateau-townhouses" / "bake" / "NA_PdDMercerMansardPair_L1_2x2"

def recipe(name, title, family, zone, width, front, back, eave, bays, entry,
           homes, roofline, iron, dominant, guests, signature, fiction, brick="Brick094"):
    row = zone == "Z2"
    return dict(design=name, title=title, family=family, zone_key=zone, lot=[width, 5 if row else 4],
                walls=[0, 8, front, back] if row else [0.65, 15.35, front, back],
                cornice_m=eave, bays=bays, entry=entry, households=homes, level=1,
                access="Front", colourway="A", roofline=roofline, railing_pattern=iron,
                lineage=dict(dominant=dominant, guests=guests, signature=signature, fiction=fiction),
                brick=brick, colourway_families=dict(brick=brick, limestone=STONE, slate=SLATE, iron=IRON))

def plans():
    assets = [
        recipe("IndependanceMansardRow", "Indépendance Mansard Row", "Rue de l’Indépendance", "Z2", 1,
               2.15, 26.15, 10.5, [1.5, 4, 6.5], 1.5, 3, "straight mansard", "bar and urn",
               "Philadelphia", ["Paris"], "White marble stoop and lintels inside a cream stone frame",
               "A Delaware marble setter built three flats and dressed the Parisian frame in stone from his own yard.",
               "Brick085"),
        recipe("LilleOrielRow", "Lille Oriel Row", "Faubourg Lillois", "Z2", 1,
               2.3, 26.1, 12, [2.1, 5.7], 2.1, 3, "bell-cast mansard", "Lille diamonds",
               "Lille", ["Philadelphia", "Paris"], "Two-storey stone oriel on a shaped corbel below an oval dormer",
               "A Lille loom mechanic copied his childhood oriel for his narrow house near the Delaware mills."),
        recipe("CreoleGalerieRow", "Creole Galerie Row", "Vieux Carré du Nord", "Z2", 1,
               3.35, 27.1, 11, [1.52, 4, 6.48], 1.52, 3, "low broken mansard", "Creole rings",
               "New Orleans", ["Paris", "Philadelphia"], "Two-storey cast-iron gallery",
               "A Creole iron foundry owner shipped his own gallery upriver and set it against a Philadelphia terrace.",
               "Brick085"),
        recipe("HaussmannBriqueRow", "Haussmann Brique Row", "Boulevard Delaware", "Z2", 1,
               2.45, 26.2, 12.5, [1.48, 4, 6.52], 4, 4, "convex crowned mansard", "Paris scroll pairs",
               "Paris", ["Philadelphia", "Lille"], "Continuous limestone grid and a balconette in every upper bay",
               "A Paris-trained surveyor bought red brick from a Delaware kiln and laid out its panels on his exact stone grid."),
        recipe("RapportBriqueImmeuble", "Rapport Brique Immeuble", "Immeubles de Rapport", "Z2B", 2,
               4.15, 22.45, 14.55, [2.6, 6.2, 9.8, 13.4], 6.2, 8, "hipped mansard", "crossed iron",
               "Paris", ["Lille"], "Four limestone-framed bays above a round-arched door with a carved agrafe",
               "A Lille brick dealer commissioned a Paris rent house and insisted that his best red brick fill the stone panels.",
               "Brick085"),
        recipe("RapportRotondeAngle", "Rapport Rotonde Angle", "Immeubles de Rapport", "Z2B", 2,
               3.65, 23.6, 15.25, [7.0, 10.5, 14.0], None, 10, "rounded corner with zinc dome", "oval iron",
               "Paris", ["Lille", "Philadelphia"], "Rounded corner, zinc dome and glazed lantern over a diagonal entrance",
               "A Delaware shipping broker hired a Paris architect for his corner building and crowned it with a river-facing lantern."),
    ]
    for a in assets:
        corner = a["entry"] is None
        if corner:
            a.update(walls=[2.15, 15.38, 3.65, 23.6], access="LeftCorner")
        width, depth = [8 * n for n in a["lot"]]
        left, right, front, back = a["walls"]
        if corner:
            x = left + 3.6 - 3.6 * (math.cos(math.pi/6)+math.cos(math.pi/3))/2
            y = front + 3.6 - 3.6 * (math.sin(math.pi/6)+math.sin(math.pi/3))/2
            px = x - .82
        else:
            x, y, px = a["entry"], front, a["entry"]
        a["name"] = f"NA_PdD{a['design']}{'LeftCorner' if corner else ''}_L1_{a['lot'][0]}x{a['lot'][1]}"
        a["active_entrances"] = [dict(position_lot_m=[x, y, .48], street_path=True)]
        a["front_walks"] = [dict(bounds_lot_m=[px-.66, px+.66, 0, y], entrance_index=0)]
        a["native_surfaces"] = []
        a["garden"] = [.35, width-.35, back+.32, depth-.34]
        a["props"] = [
            dict(kind="low iron front fence", position_lot_m=[width/2,.20,0],size_m=[width-.40,.09,.94],
                 gaps_lot_x_m=[[px-.76,px+.76]], base="cream stone plinth and piers"),
            dict(kind="clipped front hedge", position_lot_m=[width/2,.52,0],size_m=[width-.54,.36,.61],
                 gaps_lot_x_m=[[px-.76,px+.76]]),
            dict(kind="rear residential fence line", position_lot_m=[width/2,depth-.15,0],size_m=[width-.44,.08,1.12]),
            dict(kind="deciduous tree",position_lot_m=[width*.29,(back+depth)/2,0],size_m=[3.8,3.8,6.3]),
            dict(kind="parterre shrub bed",position_lot_m=[width*.72,depth-2.10,0],size_m=[2.7,1.55,.60]),
            dict(kind="side residential fence line",position_lot_m=[width-.16,(back+depth)/2,0],
                 size_m=[.07,depth-back-.5,1.12]),
        ]
        # Fence pier positions are separate native prop prescriptions.
        a["fence_piers_lot_x_m"] = sorted({.22, width-.22, px-.82, px+.82})
        for pier_x in a["fence_piers_lot_x_m"]:
            a["props"].append(dict(kind="stone garden fence pier",position_lot_m=[pier_x,.20,0],
                                   size_m=[.27,.31,1.07]))
        a["floor_datums_m"] = [round(a["cornice_m"]*i/(3 if a["zone_key"]=="Z2" else 4),3)
                               for i in range(3 if a["zone_key"]=="Z2" else 4)]
        a["front_walks"][0]["centreline_lot_m"] = [[px,0],[px,y-.80],[x,y]] if corner else [[x,0],[x,y]]
        a["future_colourways"] = {"A":"warm red-orange","B":"oxblood","C":"salmon rose"}
        a["as_baked_layout"] = dict(garden=a["garden"], body=a["walls"])
        if a["design"] == "CreoleGalerieRow":
            a["gallery"] = dict(bounds_m=[.13,7.87,1.05,front],deck_z_m=[.48,3.83],roof_z_m=7.28)
    return assets

def face(a,b):
    return nb.Face((nb.X(a[0]),nb.Y(a[1])),(nb.X(b[0]),nb.Y(b[1])))

def rect(u0,u1,z0,z1):
    return [(u0,z0),(u1,z0),(u1,z1),(u0,z1)]

def relief(mesh, facade, shape, back, front, material):
    if nb.area2d(shape) < 0:
        shape = shape[::-1]
    point = facade.point
    mesh.polygon([point(u,z,front) for u,z in shape],facade.out,material)
    mesh.polygon([point(u,z,back) for u,z in shape],-facade.out,material)
    for (u,z),(v,t) in zip(shape,shape[1:]+shape[:1]):
        normal = facade.tangent*(t-z)-UP*(v-u)
        mesh.polygon([point(u,z,back),point(v,t,back),point(v,t,front),point(u,z,front)],normal,material)

def block(mesh,f,u0,u1,z0,z1,d0,d1,material):
    if min(u1-u0,z1-z0,d1-d0) > .0001:
        relief(mesh,f,rect(u0,u1,z0,z1),d0,d1,material)

def arch_points(u,half,spring,rise,n):
    return [(u+half*math.cos(math.pi*i/n),spring+rise*math.sin(math.pi*i/n)) for i in range(n,-1,-1)]

def window(h,f,u,w,bottom,crown,arched=False,door=False,dress=True):
    m = h.body
    lo,hi = u-w/2,u+w/2
    if h.lod==2 and door not in (True,"passage"):arched=False
    rise = min({"segment":.24,"entresol":.62,"round":w/2}.get(arched,.42),w*.49) if arched else 0
    spring = crown-rise
    passage = door == "passage"
    depth = -.105 if h.lod < 2 or passage else .024
    arc = arch_points(u,w/2,spring,rise,(6 if getattr(h,"corner_detail",False) else 8) if h.lod==0 else 4) if arched else [(lo,crown),(hi,crown)]
    outline = [(lo,bottom),(hi,bottom)] + arc[::-1]
    if h.lod < 2 or passage:
        for (x,z),(y,t) in zip(outline,outline[1:]+outline[:1]):
            m.polygon([f.point(x,z),f.point(y,t),f.point(y,t,depth),f.point(x,z,depth)],
                      -f.tangent*(t-z)+UP*(y-x),STONE)
        for (x,z),(y,t) in zip(arc,arc[1:]):
            poly=[(x,z),(y,t),(y,crown),(x,crown)]
            clean=[p for i,p in enumerate(poly) if math.dist(p,poly[i-1])>1e-6]
            if len(clean)>=3 and abs(nb.area2d(clean))>1e-6:
                m.polygon([f.point(px,pz) for px,pz in clean],f.out,STONE)
    if passage:
        return
    if door is True:
        leaf = spring if arched else crown-.40
        f.quad(m,lo,hi,bottom,leaf,depth,DOOR)
        glass = [(lo,leaf),(hi,leaf)] + arc[::-1] if not arched else arc + [(u,spring)]
        glass = [p for i,p in enumerate(glass) if math.dist(p,glass[i-1])>1e-6]
        h.windows.polygon([f.point(x,z,depth) for x,z in glass],f.out,"Cream",room=nb.ROOMS[7])
        if h.lod < 2:
            block(m,f,u-.029,u+.029,bottom+.012,leaf-.014,depth+.005,depth+.036,"Black")
            if h.lod == 0:
                for x in [lo+.115,u+.105]:
                    block(m,f,x,x+w/2-.215,bottom+.21,leaf-.24,depth+.004,depth+.020,DOOR)
    else:
        room=nb.ROOMS[(round(u*9)+round(bottom*10))%len(nb.ROOMS)]
        h.windows.polygon([f.point(x,z,depth) for x,z in outline],f.out,"Cream",room=room)
        if h.lod < 2 and (dress or h.lod==0):
            sash=getattr(h,"sash",False) and dress
            mid=bottom+(crown-bottom)*(.50 if sash else .60)
            if h.lod==0 and not getattr(h,"economy",False):
                if not sash:block(m,f,u-.033,u+.033,bottom+.014,crown-.022,depth+.004,depth+.064,"Cream")
                block(m,f,lo+.015,hi-.015,mid,mid+.055,depth+.009,depth+.074,"Cream")
                if getattr(h,"sash",False) and dress:
                    for z in (bottom+.25*(crown-bottom),bottom+.75*(crown-bottom)):
                        f.quad(m,lo+.017,hi-.017,z,z+.031,depth+.042,"Cream")
                    for x in (u-w/6,u+w/6):
                        f.quad(m,x-.012,x+.012,bottom+.018,crown-.017,depth+.045,"Cream")
            else:
                f.quad(m,u-.034,u+.034,bottom+.014,crown-.022,depth+.061,"Cream")
                f.quad(m,lo+.015,hi-.015,mid,mid+.055,depth+.070,"Cream")
    if h.lod == 2 or not dress:
        return
    if h.lod == 1 or (getattr(h,"economy",False) and door is not True):
        for x in [lo-.106,hi]:
            f.quad(m,x,x+.106,bottom,spring,.088,STONE)
        if arched:
            outer=arch_points(u,w/2+.11,spring,rise+.095,len(arc)-1)
            for i in range(len(arc)-1):
                m.polygon([f.point(x,z,.097) for x,z in
                           (arc[i],arc[i+1],outer[i+1],outer[i])],f.out,STONE)
        else:
            f.quad(m,lo-.105,hi+.105,crown,crown+.128,.094,STONE)
        return
    if not getattr(h,"sash",False):
        for x in [lo-.12,hi]:
            block(m,f,x,x+.12,bottom,spring,.002,.106,STONE)
    if arched:
        outer=arch_points(u,w/2+.13,spring,rise+.12,len(arc)-1)
        for i in range(len(arc)-1):
            relief(m,f,[arc[i],arc[i+1],outer[i+1],outer[i]],.003,.119,STONE)
    else:
        block(m,f,lo-.12,hi+.12,crown,crown+.14,.003,.115,STONE)
    if not door:
        block(m,f,lo-.16,hi+.16,bottom-.105,bottom-.005,-.015,.163,"Cream")
    if h.lod==0 and not getattr(h,"sash",False):
        relief(m,f,[(u-.082,crown+.014),(u+.082,crown+.014),(u+.125,crown+.205),(u-.125,crown+.205)],
               .077,.173,"Cream")

def rail(h,f,lo,hi,z,depth,pattern):
    if hi-lo < .20:
        return
    m=h.body
    if h.lod==2 or getattr(h,"rail_strip_only",False):
        if getattr(h,"solid_far_rails",False):
            block(m,f,lo,hi,z+.73,z+.81,depth-.009,depth+.012,IRON)
            return
        f.quad(m,lo,hi,z+.73,z+.81,depth,IRON)
        m.polygon([f.point(x,y,depth-.001) for x,y in rect(lo,hi,z+.73,z+.81)],-f.out,IRON)
        return
    compact=getattr(h,"corner_detail",False)
    if h.lod==1 and getattr(h,"thin_rail",False):
        for y0,y1 in [(z+.09,z+.15),(z+.83,z+.91)]:
            block(m,f,lo,hi,y0,y1,depth-.012,depth+.014,IRON)
        count=max(2,round((hi-lo)/.84))
        for i in range(count+1):
            u=lo+.035+(hi-lo-.07)*i/count
            for d,normal in [(depth+.009,f.out),(depth+.008,-f.out)]:
                m.polygon([f.point(x,y,d) for x,y in rect(u-.022,u+.022,z+.15,z+.83)],normal,IRON)
        return
    for low,high in [(z+.08,z+.135),(z+.85,z+.91)]:
        if h.lod==1 and compact:
            for d,normal in [(depth+.021,f.out),(depth+.020,-f.out)]:
                m.polygon([f.point(x,y,d) for x,y in rect(lo,hi,low,high)],normal,IRON)
        else:
            block(m,f,lo,hi,low,high,depth-.030,depth+.030,IRON)
    solid_spacing=getattr(h,"solid_main_spacing",None) if h.lod==0 and min(abs(f.out.x),abs(f.out.y))>.05 else None
    spacing=solid_spacing or (.43 if compact else .27 if h.lod==0 else .57)
    n=max(2,round((hi-lo)/spacing))
    for i in range(n+1):
        u=lo+.026+(hi-lo-.052)*i/n
        if h.lod==0 and (not compact or solid_spacing):
            block(m,f,u-.018,u+.018,z+.137,z+.849,depth-.017,depth+.017,IRON)
        else:
            for d,normal in [(depth+.012,f.out),(depth+.011,-f.out)]:
                m.polygon([f.point(x,y,d) for x,y in rect(u-.026,u+.026,z+.137,z+.849)],normal,IRON)
    if h.lod!=0 or getattr(h,"light_rail",False):
        return
    count=max(1,round((hi-lo)/(1.15 if compact else .67)))
    for j in range(count):
        u=lo+(hi-lo)*(j+.5)/count
        if pattern in {"Creole rings","Paris scroll pairs","oval iron"}:
            for shift in ([-.115,.115] if pattern=="Paris scroll pairs" else [0]):
                rx=.101 if shift else .17
                rz=.24 if pattern=="oval iron" else .175
                zc=z+.49
                rings=[[(u+shift+rx*k*math.cos(i*math.tau/8),zc+rz*k*math.sin(i*math.tau/8))
                        for i in range(8)] for k in (1,.82)]
                outer,inner=rings
                for i in range(8):
                    k=(i+1)%8
                    shape=[outer[i],outer[k],inner[k],inner[i]]
                    for d,normal in [(depth+.015,f.out),(depth+.014,-f.out)]:
                        m.polygon([f.point(x,z,d) for x,z in shape],normal,IRON)
        else:
            r=.145 if pattern!="bar and urn" else .07
            zc=z+(.49 if pattern!="bar and urn" else .70)
            path=[(u-r,zc),(u,zc-.19),(u+r,zc),(u,zc+.19)] if pattern!="bar and urn" else [
                (u-r,zc-.045),(u+r,zc-.045),(u+r*.7,zc+.06),(u-r*.7,zc+.06)]
            if pattern=="whiplash":
                path=[(u-.20,zc-.19),(u-.04,zc-.12),(u+.10,zc+.045),(u+.065,zc+.16),
                      (u-.015,zc+.19),(u+.11,zc+.19),(u+.16,zc+.045),(u+.016,zc-.16)]
            if pattern=="monogram":
                path=[(u-.15,zc-.17),(u-.12,zc+.17),(u,zc+.025),(u+.13,zc+.17),
                      (u+.15,zc-.17),(u+.102,zc-.17),(u+.09,zc+.059),(u,zc-.058),
                      (u-.089,zc+.062),(u-.103,zc-.17)]
            if pattern=="crossed iron":
                path=[(u-.15,zc-.12),(u+.15,zc+.10),(u+.13,zc+.13),(u-.17,zc-.09)]
            relief(m,f,path,depth+.024,depth+.047,IRON)

def balcony(h,f,lo,hi,z,projection,pattern):
    m=h.body
    block(m,f,lo,hi,z-.16,z-.025,-.024,projection,STONE)
    compact=getattr(h,"corner_detail",False)
    if h.lod < 2 and not (compact and h.lod==1):
        for x in ([(lo+hi)/2] if compact else [lo+.18,hi-.18]):
            block(m,f,x-.09,x+.09,z-.40,z-.165,-.015,projection*.57,"Cream")
    rail(h,f,lo+.025,hi-.025,z,projection-.055,pattern)

def wall_storey(h,f,z0,z1,ops,material,stone_base,dress,pattern,balconies,grid):
    m=h.body
    cutouts=[o for o in ops if h.lod<2 or o[-1]=="passage"]
    bands=getattr(h,"brick_banding",False) and dress and material.startswith("Brick") and h.lod==0
    if h.lod==2 and not cutouts:
        f.quad(m,0,f.length,z0,z1,0,material)
    else:
        zcuts={z0,z1}
        for u,w,b,t,arch,door in cutouts:
            zcuts.update([b,t])
        if stone_base and h.lod==0:
            courses=[z0+i*.49 for i in range(1,math.ceil((z1-z0)/.49))]
            for z in courses:
                zcuts.update([z,z+.024])
        else:
            courses=[]
        stripes=[z0+.33+i*.47 for i in range(int((z1-z0)/.47)) if z0+.41+i*.47<z1] if bands else []
        for z in stripes:zcuts.update([z,z+.075])
        cuts=sorted(zcuts)
        for a,b in zip(cuts,cuts[1:]):
            mid=(a+b)/2
            if mid<z0 or mid>z1:continue
            cursor=0
            holes=sorted((u-w/2,u+w/2) for u,w,low,high,*_ in cutouts if low<mid<high)
            joint=any(z<mid<z+.024 for z in courses)
            for lo,hi in holes+[(f.length,f.length)]:
                f.quad(m,cursor,lo,a,b,0,"StoneBase" if joint else "Cream" if any(z<mid<z+.075 for z in stripes) else material)
                cursor=hi
    for u,w,b,t,arched,door in ops:
        window(h,f,u,w,b,t,arched,door,dress)
        if balconies=="each" and not door:
            projection=.42
            balcony(h,f,max(.15,u-w/2-.18),min(f.length-.15,u+w/2+.18),b,projection,pattern)
    if balconies=="full":
        balcony(h,f,.095,f.length-.095,z0+.17,.76,pattern)
    if h.lod<2 and grid:
        # Piers are structural bands of relief with distinct depths. Belt courses stop clear of the pilasters.
        half=.235 if h.heavy_frame else .145
        edge=.39 if h.heavy_frame else .30
        edge_margin=.145 if getattr(h,"wide_belt_joint",False) else .024
        intervals=[(edge_margin,edge),(f.length-edge,f.length-edge_margin)]
        centers=sorted(o[0] for o in ops)
        intervals.extend(((x+y)/2-half,(x+y)/2+half) for x,y in zip(centers,centers[1:]))
        for lo,hi in intervals:
            block(m,f,lo,hi,z0+.105,z1-.295,-.025,.165,STONE)
            block(m,f,lo-.023,hi+.023,z1-.291,z1-.166,-.026,.200,"Cream")
    if h.lod<2 and dress and z0>0 and not getattr(h,"sash",False):
        margin=.195 if getattr(h,"wide_belt_joint",False) else .085 if getattr(h,"corner_detail",False) else .006
        block(m,f,margin,f.length-margin,z0-.055,z0+.072,-.031,.138,STONE)

def outline(a):
    l,r,f,b=a["walls"]
    if a["access"]=="Front":
        return [(l,f),(r,f),(r,b),(l,b)]
    radius=3.6
    arc=[(l+radius-radius*math.cos(i*math.pi/6),f+radius-radius*math.sin(i*math.pi/6)) for i in range(4)]
    return arc+[(r,f),(r,b),(l,b)]

def coordinates(a,plan,front_inset,side_inset,z):
    l,r,f,b=a["walls"]
    # Preserve the true party-wall plane for rows. Standalones hip all the way around.
    return [(nb.X(x+side_inset*(1-2*(x-l)/(r-l))),
             nb.Y(y+front_inset*(1-2*(y-f)/(b-f))),z) for x,y in plan]

def ring_surfaces(m, lower, upper, material):
    for i in range(len(lower)):
        j=(i+1)%len(lower)
        a,b,c,d=lower[i],lower[j],upper[j],upper[i]
        want=(b[1]-a[1],a[0]-b[0],.06)
        # Profile changes on rounded plan edges may twist a quadrilateral.
        m.polygon([a,b,c],want,material)
        m.polygon([a,c,d],want,material)

def roof(h,a,plan):
    m=h.body;e=a["cornice_m"];row=a["zone_key"]=="Z2"
    side=lambda x: 0 if row else x
    c0=coordinates(a,plan,-.024,side(-.020),e-.42)
    c1=coordinates(a,plan,-.224,side(-.190),e-.26)
    c2=coordinates(a,plan,-.224,side(-.190),e)
    ring_surfaces(m,c0,c1,STONE)
    ring_surfaces(m,c1,c2,"Cream")
    m.polygon(c0,nb.DOWN,STONE)
    profile={
       "straight mansard":[(.96,2.80),(1.62,3.00)],
       "bell-cast mansard":[(.54,.22),(.86,1.08),(1.06,2.84),(1.58,3.02)],
       "low broken mansard":[(.94,1.95),(2.65,2.24)],
       "convex crowned mansard":[(.45,1.46),(1.23,2.82),(3.64,3.53),(8.05,3.86)],
       "hipped mansard":[(1.03,2.73),(1.79,3.10)],
       "rounded corner with zinc dome":[(1.06,2.45),(1.80,2.76)]
    }[a["roofline"]]
    prior=c2
    for i,(offset,rise) in enumerate(profile):
        ring=coordinates(a,plan,offset,side(offset*.69),e+rise)
        ring_surfaces(m,prior,ring,SLATE)
        prior=ring
    m.polygon(prior,nb.UP,SLATE)
    # Continuous front curb and crest anchored in the last break in slope.
    l,r,f,b=a["walls"]
    offset,rise=profile[-2]
    crest_y=offset+.12
    ty=e+rise+(profile[-1][1]-rise)*.12/(profile[-1][0]-offset)
    front=face((l,f+crest_y),(r,f+crest_y))
    lo=(3.9 if a["access"]=="LeftCorner" else .23 if row else .85)
    hi=front.length-(.23 if row else .85)
    block(m,front,lo,hi,ty-.062,ty+.050,-.040,.040,STONE)
    if h.lod<2:
        block(m,front,lo+.02,hi-.02,ty+.36,ty+.407,-.020,.023,IRON)
        n=max(3,round((hi-lo)/(.25 if h.lod==0 else .51)))
        for i in range(n+1):
            u=lo+.032+(hi-lo-.064)*i/n
            block(m,front,u-.016,u+.016,ty+.044,ty+.359,-.018,.020,IRON)
    else:
        block(m,front,lo,hi,ty+.053,ty+.31,-.020,.022,IRON)
    for u in [lo+.079,hi-.084]:
        block(m,front,u-.030,u+.030,ty+.051,ty+.974,-.031,.029,IRON)
    if h.lod==0:
        for i in range(1,round((r-l)/.55)):
            x=l+i*.55
            if x>=r-.18 or (a["access"]=="LeftCorner" and x<l+3.8):continue
            cf=face((l,f),(r,f))
            block(m,cf,x-l-.057,x-l+.057,e-.526,e-.385,-.013,.111,"Cream")
    stacks=[(l+.379,b-4.02),(r-.39,b-6.2)] if row else [(l+3.0,b-4.02),(r-2.75,b-6.25)]
    for i,(x,y) in enumerate(stacks):
        along=min(y-f,b-y)
        height=profile[-1][1]
        for (lo,z0),(hi,z1) in zip([(-.224,0)]+profile,profile):
            if lo<=along<=hi:
                height=z0+(z1-z0)*(along-lo)/(hi-lo)
                break
        extra=.64 if a["design"]=="LilleOrielRow" and i==1 else 0
        chimney(h,x,y,e+height-.21,a["brick"],extra)
    return profile

def chimney(h,x,y,z,brick,extra):
    m=h.body;x,y=nb.X(x),nb.Y(y)
    m.box(x-.31,x+.31,y-.32,y+.32,z,z+1.06+extra,brick)
    m.box(x-.365,x+.365,y-.373,y+.373,z+1.02+extra,z+1.16+extra,STONE)
    for dx in [-.142,.142]:
        m.box(x+dx-.092,x+dx+.092,y-.105,y+.105,z+1.153+extra,z+1.53+extra,"Chimney")

def dormer(h,f,x,e,oval=False,high=0):
    pointed=getattr(h,"pointed_dormer",False)
    m=h.body;u=x;w=2.42 if pointed else 2.02 if high>1 else 1.62 if oval else 1.52;lo,hi=u-w/2,u+w/2
    zb=e+.16;top=e+2.26+high
    # Taper each closed cheek into the main roof, keeping the head forward of the slate.
    d=.032
    if h.lod==2:
        drop=1.02 if pointed else .27
        shape=[(lo,zb),(hi,zb),(hi,top-drop),(u,top),(lo,top-drop)]
        m.polygon([f.point(s,z,d) for s,z in shape],f.out,STONE)
        tip=f.point(u,zb+.12,-1.51)
        for (s,z),(t,q) in zip(shape,shape[1:]+shape[:1]):
            normal=f.tangent*(q-z)-UP*(t-s)-f.out*.13
            m.polygon([f.point(s,z,d),f.point(t,q,d),tip],normal,SLATE)
        h.pane(f,u-.38,u+.38,zb+.33,top-.36,d+.022)
        if getattr(h,"keep_far_sill",False):
            block(m,f,lo-.04,hi+.04,zb-.055,zb+.048,-.08,.29,"Cream")
        return
    cap = [(lo,top-1.02),(u,top),(hi,top-1.02)] if pointed else arch_points(u,w/2,top-.32,.32,6)
    shape=[(lo,zb),(hi,zb)]+cap[::-1]
    tip=f.point(u,zb+.15,-1.56)
    for (s,z),(t,q) in zip(shape,shape[1:]+shape[:1]):
        normal=f.tangent*(q-z)-UP*(t-s)-f.out*.18
        m.polygon([f.point(s,z,d),f.point(t,q,d),tip],normal,SLATE)
    # Face cut-out follows the arch or ellipse. No opaque panel behind the glass.
    if oval:
        cz=(top+zb)/2
        boundary=[(u+.39*math.cos(i*math.tau/12),cz+.64*math.sin(i*math.tau/12)) for i in range(12)]
        outer=[(u+.58*math.cos(i*math.tau/12),cz+.82*math.sin(i*math.tau/12)) for i in range(12)]
        # Add a separate rolled moulding forward of the same plane as the dressed cheeks.
        for i in range(12):
            j=(i+1)%12
            relief(m,f,[boundary[i],outer[i],outer[j],boundary[j]],d-.06,d+.075,STONE)
        # Close the annulus to the actual hood outline with projected sectors.
        hood=[(s-u,z-cz) for s,z in shape]
        def rim(p):
            direction=(p[0]-u,p[1]-cz)
            hits=[]
            for j,(ax,ay) in enumerate(hood):
                bx,by=hood[(j+1)%len(hood)];ex,ey=bx-ax,by-ay
                den=direction[0]*ey-direction[1]*ex
                if abs(den)<1e-10:continue
                k=(ax*ey-ay*ex)/den
                t=(ax*direction[1]-ay*direction[0])/den
                if k>0 and -.00001<=t<=1.00001:hits.append(k)
            return min(hits)
        for i,p in enumerate(boundary):
            j=(i+1)%12;q=boundary[j]
            kp,kq=rim(p),rim(q)
            alpha=math.atan2(p[1]-cz,p[0]-u);beta=(math.atan2(q[1]-cz,q[0]-u)-alpha)%math.tau
            corners=[(px+u,pz+cz) for px,pz in hood if 1e-6<(math.atan2(pz,px)-alpha)%math.tau<beta-1e-6]
            corners.sort(key=lambda pt:(math.atan2(pt[1]-cz,pt[0]-u)-alpha)%math.tau)
            ring=[p,(u+(p[0]-u)*kp,cz+(p[1]-cz)*kp),*corners,(u+(q[0]-u)*kq,cz+(q[1]-cz)*kq),q]
            m.polygon([f.point(s,z,d) for s,z in ring],f.out,STONE)
        h.windows.polygon([f.point(s,z,d-.035) for s,z in boundary],f.out,"Cream",room=nb.ROOMS[8])
        block(m,f,u-.026,u+.026,cz-.63,cz+.63,d-.033,d+.01,"Cream")
    else:
        zb1=zb+.22
        top1=top-.41
        # Arch geometry is cut into a vertically translated facade.
        df=nb.Face(tuple(f.point(0,0,d)[:2]),tuple(f.point(f.length,0,d)[:2]))
        half=.44
        df.quad(m,lo,u-half,zb,top-.32,0,STONE)
        df.quad(m,u+half,hi,zb,top-.32,0,STONE)
        df.quad(m,u-half,u+half,zb,zb1,0,STONE)
        df.quad(m,u-half,u+half,top1,top-.32,0,STONE)
        m.polygon([df.point(s,z) for s,z in cap],df.out,STONE)
        window(h,df,u,2*half,zb1,top1,True,dress=True)
    if h.lod==0:
        for sx in [-1,1]:
            p=u+sx*.57
            relief(m,f,[(p-.12,zb+.10),(p+.12,zb+.10),(p+.075,zb+.57),(p-.075,zb+.57)],
                   d+.012,d+.132,"Cream")
        rail(h,f,lo+.12,hi-.12,zb+.13,.247,"Paris scroll pairs")
    block(m,f,lo-.04,hi+.04,zb-.055,zb+.048,-.08,.29,"Cream")


def stoop(h,f,u,z=.48,run=1.02,width=1.30):
    lo,hi=u-width/2,u+width/2
    # One stepped extrusion, with no overlapping tread faces.
    shape=[(-.023,.006),(run,.006),(run,z/3),(run-.25,z/3),
           (run-.25,2*z/3),(run-.51,2*z/3),(run-.51,z),(0,z)]
    points=lambda s:[f.point(s,t,d) for d,t in shape]
    for s,n in [(lo,-f.tangent),(hi,f.tangent)]:
        h.body.polygon(points(s),n,"Cream")
    for i,(d,t) in enumerate(shape):
        j=(i+1)%len(shape);nd,nt=shape[j]
        h.body.polygon([points(lo)[i],points(hi)[i],points(hi)[j],points(lo)[j]],
                       f.out*(nt-t)-UP*(nd-d),"Cream")

def add_gallery(h,a,facade):
    g=a["gallery"];m=h.body;front=a["walls"][2]
    l,r,f,_=g["bounds_m"]
    lo,hi,y0,y1=nb.X(l),nb.X(r),nb.Y(f),nb.Y(front)
    for z in g["deck_z_m"]:
        m.box(lo,hi,y0,y1,z-.151,z,"Deck")
    f2=face((0,f),(8,f))
    stoop(h,f2,a["entry"],run=.85)
    # Balcony rails and posts are separate depths, so their faces do not coincide.
    for z in g["deck_z_m"]:
        ranges=[(l+.01,a["entry"]-.71),(a["entry"]+.71,r-.01)] if z==.48 else [(l+.01,r-.01)]
        for xa,xb in ranges:
            rail(h,f2,xa,xb,z,-.068,"Creole rings")
    for x in [.32,2.69,5.26,7.69]:
        block(m,f2,x-.044,x+.044,.20,7.26,-.21,-.122,IRON)
        if h.lod==0:
            for z in g["deck_z_m"]:
                block(m,f2,x-.077,x+.077,z+.013,z+.175,-.232,-.106,IRON)
    z=g["roof_z_m"]
    r3.shed(h,"x",lo-.077,hi+.077,y1,y0-.112,z+.23,z,"TinFlat")

def add_oriel(h,a,front,levels):
    x=5.7;f=a["walls"][2];lo=levels[1]-.16;hi=a["cornice_m"]-.53
    plan=[(x-1.13,f+.018),(x-1.13,f-.23),(x-.76,f-1.23),
          (x+.76,f-1.23),(x+1.13,f-.23),(x+1.13,f+.018)]
    fs=[face(p,q) for p,q in zip(plan,plan[1:]+plan[:1])]
    for i,side in enumerate(fs):
        ops=[]
        if i==2:
            ops=[(side.length/2,.93,z+.32,zt-.63,True,False)
                 for z,zt in zip(levels[1:-1],levels[2:])]
        for bottom,top in zip([lo,levels[2]],[levels[2],hi]):
            openings=[o for o in ops if bottom < o[2] < top]
            wall_storey(h,side,bottom,top,openings,STONE,False,i==2,"Lille diamonds","",False)
    p=[(nb.X(x),nb.Y(y)) for x,y in plan]
    h.body.polygon([(*q,hi) for q in p],nb.UP,"TinFlat")
    h.body.polygon([(*q,lo) for q in p],nb.DOWN,STONE)
    cap=[(nb.Y(f-1.43),hi+.026),(nb.Y(f+.053),hi+.026),
         (nb.Y(f+.053),hi+.56),(nb.Y(f-1.43),hi+.16)]
    nb.extrude(h.body,cap,"x",nb.X(x-1.15),nb.X(x+1.15),SLATE,(STONE,STONE))
    # Carved bracket, tapered toward the wall and embedded beneath the bay.
    relief(h.body,front,[(x-.28,lo-.92),(x+.28,lo-.92),(x+.83,lo+.035),(x-.83,lo+.035)],
           -.035,.26,STONE)
    corbel=[(nb.Y(f+.017),lo-.87),(nb.Y(f-.17),lo-.87),
            (nb.Y(f-1.08),lo+.018),(nb.Y(f+.017),lo+.018)]
    nb.extrude(h.body,corbel,"x",nb.X(x-.57),nb.X(x+.57),STONE,(STONE,STONE))
    if h.lod==0:
        for offset in [-.48,0,.48]:
            relief(h.body,front,[(x+offset-.095,lo-.37),(x+offset+.095,lo-.37),
                    (x+offset+.14,lo-.025),(x+offset-.14,lo-.025)],.24,.57,"Cream")

def dome(h,a):
    m=h.body;e=a["cornice_m"];l,_,f,_=a["walls"];cx,cy=l+3.25,f+3.28
    # Glazing starts above the highest adjacent roof surface (e + 2.76).
    drum_top=e+3.86
    dome_lift=drum_top-(e+2.36)
    n=10 if h.lod==0 else 8 if h.lod==1 else 6
    def ring(radius,z):
        return [(nb.X(cx)+radius*math.cos(i*math.tau/n),
                 nb.Y(cy)+radius*math.sin(i*math.tau/n),z) for i in range(n)]
    lower=ring(2.66,e+.68)
    for i in range(n):
        j=(i+1)%n
        f=nb.Face(lower[i][:2],lower[j][:2])
        # Vertical wall ring has constant radius, with a moulded stone cap above.
        if h.lod==0 and i in (4,5,6,7,8):
            wall_storey(h,f,e+.68,drum_top,[(f.length/2,.71,e+2.83,e+3.65,True,False)],
                        STONE,False,True,"oval iron","",False)
        else:
            f.quad(m,0,f.length,e+.68,drum_top,0,STONE)
    m.polygon(lower,nb.DOWN,STONE)
    e+=dome_lift
    prior=ring(2.66,drum_top)
    profile=[(2.79,e+2.49,STONE),(2.72,e+2.64,"TinFlat"),(2.49,e+3.46,"Tin"),
             (1.89,e+4.23,"Tin"),(1.02,e+4.76,"TinFlat"),(.46,e+4.89,"TinFlat")]
    if h.lod==2:profile=[profile[i] for i in (0,2,3,5)]
    for radius,z,mat in profile:
        next_ring=ring(radius,z)
        ring_surfaces(m,prior,next_ring,mat);prior=next_ring
    m.polygon(prior,nb.UP,"TinFlat")
    base=ring(.40,e+4.85);top=ring(.46,e+5.61)
    for p,q in zip(base,base[1:]+base[:1]):
        f=nb.Face(p[:2],q[:2]);z=e+4.85
        if h.lod==0 and p[1]+q[1]<2*nb.Y(cy) and f.length>.14:
            wall_storey(h,f,z,z+.72,[(f.length/2,min(.17,f.length*.58),z+.13,z+.59,False,False)],
                        STONE,False,False,"oval iron","",False)
        else:f.quad(m,0,f.length,z,z+.72,0,STONE)
    ring_surfaces(m,ring(.40,e+5.57),top,STONE)
    tip=(nb.X(cx),nb.Y(cy),e+6.07)
    for p,q in zip(top,top[1:]+top[:1]):
        m.polygon([p,q,tip],((p[0]+q[0])/2-tip[0],(p[1]+q[1])/2-tip[1],.4),"Tin")
    m.box(tip[0]-.023,tip[0]+.023,tip[1]-.023,tip[1]+.023,tip[2]-.026,tip[2]+.37,IRON)

def build(a,lod):
    core.setup(a,lod,0)
    h=nb.House(lod);m=h.body;e=a["cornice_m"]
    plan=outline(a);corner=a["access"]=="LeftCorner";row=a["zone_key"]=="Z2"
    h.corner_detail=corner
    h.heavy_frame=a["design"] in {"HaussmannBriqueRow","RapportBriqueImmeuble","RapportRotondeAngle"}
    n_floors=3 if row else 4
    levels=[e*i/n_floors for i in range(n_floors+1)]
    l,r,f,b=a["walls"];front=face((l,f),(r,f))
    gallery=a.get("gallery")
    for i,(p,q) in enumerate(zip(plan,plan[1:]+plan[:1])):
        facade=face(p,q)
        is_front=(i==0 if not corner else i==3)
        is_round=corner and i<3
        is_rear=(i==2 if not corner else i==5)
        is_side=not (is_front or is_round or is_rear)
        dressed=is_front or is_round or (corner and i==6)
        bays=[]
        if is_front:bays=[x-p[0] for x in a["bays"]]
        if is_round:bays=[facade.length/2]
        if is_rear:bays=[facade.length*k for k in ([.28,.72] if row else [.22,.51,.78])]
        if is_side and not row:bays=[facade.length*k for k in ([.35] if corner else [.29,.62])]
        for j,(z0,z1) in enumerate(zip(levels,levels[1:])):
            ops=[]
            for u in bays:
                door=(is_front and a["entry"] is not None and abs(u+p[0]-a["entry"])<.05 or is_round and i==1) and j==0
                if is_side and j<2:continue
                if lod==2 and corner and (is_side or is_rear or (is_round and j==1)):continue
                if lod==1 and corner and ((is_rear and j%2==1) or is_side):continue
                if a["design"]=="LilleOrielRow" and is_front and u>4 and j>0:continue
                if lod==2 and (is_side or is_rear) and j%2==1:continue
                low=z0+(.48 if door else .70 if j==0 else .32 if dressed else .73)
                if gallery and is_front and j==1:low=3.85
                high=z1-(.40 if j==0 else .67)
                width=(1.28 if door else 1.18 if row else 1.42)
                if is_round:width=1.23 if door else 1.13
                ops.append((u,width,low,high,dressed and (j==0 or j==n_floors-1 or is_round),door))
            material=STONE if j==0 and (dressed or not row) else a["brick"]
            balconies=""
            if dressed and not gallery and j>0 and not (corner and is_side):
                balconies=("full" if is_front and j==1 and a["design"] in
                           {"RapportBriqueImmeuble","RapportRotondeAngle"} else "each")
                if lod==2 and corner and balconies!="full" and not (is_round and i==0 and j==2):balconies=""
            wall_top=z1-.42 if row and is_side and j==n_floors-1 else z1
            wall_storey(h,facade,z0,wall_top,ops,material,j==0 and dressed,dressed,
                        a["railing_pattern"],balconies,dressed and not is_round and j>0)
        if is_side and not row and lod==0 and not dressed:
            for j,z in enumerate(levels[1:-1]):
                width=.34 if j%2 else .46
                for lo,hi in [(.025,width),(facade.length-width,facade.length-.025)]:
                    block(m,facade,lo,hi,z+.14,z+.49,-.016,.079,STONE)
        if is_round and i==1:stoop(h,facade,facade.length/2)
    m.polygon([(nb.X(x),nb.Y(y),0) for x,y in plan],nb.DOWN,"StoneBase")
    roof(h,a,plan)
    df=face((l,f-.14),(r,f-.14))
    if a["design"]=="IndependanceMansardRow": dormers=[(1.55,False,0),(6.45,False,0)]
    elif a["design"]=="LilleOrielRow":dormers=[(2.1,False,-.13),(5.7,True,1.31)]
    elif a["design"]=="CreoleGalerieRow":dormers=[(1.57,False,-.40),(4,True,-.40),(6.43,False,-.40)]
    elif a["design"]=="HaussmannBriqueRow":dormers=[(1.48,False,.04),(4,True,1.75),(6.52,False,.04)]
    else:dormers=[(x,(i%2==1),0) for i,x in enumerate(a["bays"])]
    if corner and lod==2:dormers=[dormers[1]]
    for x,oval,rise in dormers:dormer(h,df,x-l,e,oval,rise)
    if a["design"]=="LilleOrielRow":add_oriel(h,a,front,levels)
    if gallery:add_gallery(h,a,front)
    elif not corner:stoop(h,front,a["entry"],run=1.10 if a["design"]=="LilleOrielRow" else 1.02)
    if corner:dome(h,a)
    # Front walks and courts are native prescriptions. The FBXs contain no garden props.
    return h

def write_json(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def bake():
    OUT.mkdir(exist_ok=True)
    assets=plans();owner=assets[0]["name"]
    write_json(ROOT/"designs.json",dict(batch="R2-0",coordinates="Metres from the lot front-left",designs=assets))
    records=[]
    for a in assets:
        name=a["name"];folder=OUT/name;folder.mkdir(exist_ok=True)
        budget=[12000,4000,500] if a["zone_key"]=="Z2" else [16000,5000,500]
        record=dict(name=name,zone_key=a["zone_key"],lot=a["lot"],budget=budget,meshes={},lods={})
        for i,suffix in enumerate(LODS):
            nb.clear_objects()
            house=build(a,i);pair=[]
            for mesh,ext in [(house.body,""),(house.windows,"_Win")]:
                tag=name+suffix+ext
                mat=None if ext else core.bpy.data.materials.new(tag)
                ob=core.optimize_far(mesh.object(tag,mat),i)
                stats=core.mesh_stats(ob)
                pair.append((tag,ob,stats))
            total=sum(x[2]["triangles"] for x in pair)
            print("LOD",name,i,total,flush=True)
            assert total<=budget[i],(name,i,total,budget[i])
            bad=overlaps(pair[0][1])
            if bad:
                print("COPLANAR",name,i,bad[:8],flush=True)
            assert not bad,(name,i,len(bad))
            record["lods"][suffix or "main"]=dict(triangles=total,coplanar_overlaps=0)
            for tag,ob,_ in pair:nb.export_fbx(ob,folder/(tag+".fbx"))
        if name==owner:
            for suffix in LODS:
                for key in nb.MAPS:
                    src=ATLAS/f"{ATLAS.name}{suffix}_{key}.png"
                    dst=folder/f"{name}{suffix}_{key}.png"
                    if src.is_file():shutil.copy2(src,dst)
                    else:assert dst.is_file(),dst
        else:
            write_json(folder/"settings.json",dict(sharedAssets={
                f"{name}{suffix}_{key}.png":f"../{owner}/{owner}{suffix}_{key}.png"
                for suffix in LODS for key in nb.MAPS}))
        for path in sorted(folder.glob("*.fbx")):
            record["meshes"][path.stem]=core.validate(path,a)
            if not path.stem.endswith("_Win"):
                assert not overlaps(core.bpy.context.selected_objects[0]),path.name
        c=record["coverage"]=record["meshes"][name]["coverage"]
        lower,upper=(55,70) if a["zone_key"]=="Z2" else (50,65)
        depth=a["lot"][1]*8;width=a["lot"][0]*8
        court=(depth-a["walls"][3])/depth*100
        assert lower<=c["roofed_pct"]<=upper,(name,c)
        assert court >= (25 if a["zone_key"]=="Z2" else 20),(name,court)
        c["continuous_rear_garden_pct"]=round(court,2)
        base_bounds=record["meshes"][name]["bounds_m"]
        for suffix in LODS[1:]:
            other=record["meshes"][name+suffix]["bounds_m"]
            assert max(abs(x-y) for p,q in zip(base_bounds,other) for x,y in zip(p,q))<=.002,(name,base_bounds,other)
        records.append(record)
        print("ASSET_PASS",name,c,flush=True)
    files=[p for p in OUT.rglob("*") if p.suffix in {".png",".fbx"}]
    write_json(OUT/"manifest.json",dict(batch="R2-0",texture_owner=owner,registrations=len(assets),assets=records,
            sha256={p.relative_to(OUT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}))
    (ROOT/"IMPORT-LIST.txt").write_text("\n".join(a["name"] for a in assets)+"\n",encoding="utf-8")
    print("BAKE_COMPLETE",flush=True)

if __name__=="__main__":
    raise SystemExit("Use bake_batch2.py to bake R2-2.")
