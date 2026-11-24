from pathlib import Path
S=Path(__file__).resolve().parent
def patch(f,rows):
    p=S/f
    t=p.read_text(encoding="utf8")
    for a,b in rows:
        assert a in t,(f,a)
        t=t.replace(a,b)
    p.write_text(t,encoding="utf8")

patch("r12_atlas.py",[
 ('from PIL import Image, ImageDraw','from PIL import Image, ImageDraw\nimport numpy as np'),
 ('def main():','''def water(size,kind):
    width,height=size
    y,x=np.meshgrid(np.arange(height)*2*np.pi/height,np.arange(width)*2*np.pi/width,indexing="ij")
    if kind=="BaseColor":
        wave=np.sin(6*y+1.2*np.sin(2*x+3*y))*.60+np.sin(13*y-2*x)*.23+np.sin(23*y+3*x)*.17
        high=np.clip((wave-.28)*1.12,0,1)
        color=np.stack([47+16*wave+22*high,82+19*wave+24*high,88+21*wave+26*high,np.full_like(wave,255)],axis=2)
        return Image.fromarray(np.uint8(np.clip(color,0,255)))
    if kind=="Normal":
        return Image.new("RGBA",size,(128,128,255,255))
    return Image.new("RGBA",size,(6,244,0,132))

def main():'''),
 ('old_signs=[cells.pop(k) for k in list(cells) if k.startswith("Sign_")]','''old_signs=[cells.pop(k) for k in list(cells) if k.startswith("Sign_")]
        cells["CanalWater"]=cells.pop("PaintedDrum")
        cells["CanalWater"]["metres"]=[4.8,5.9] if not tag else [40,40]
        cells["CourtGlass"]=old_signs.pop()
        cells["CourtGlass"]["metres"]=[2.85,3.65] if not tag else [40,40]'''),
 ('            for zone,owner in sorted(groups):', '''            if kind in ("BaseColor","Normal","MaskMap"):
                l,t,r,b=source_box(cells["CanalWater"]["uv"],im.width)
                im.paste(water((r-l,b-t),kind),(l,t))
                l,t,r,b=source_box(cells["CourtGlass"]["uv"],im.width)
                source=source_box(cells["GreyBlue"]["uv"],im.width)
                im.paste(im.crop(source).resize((r-l,b-t),Image.Resampling.LANCZOS),(l,t))
            for zone,owner in sorted(groups):'''),
])
patch("r12_geometry.py",[
 ('WATER="GardenGlass"','WATER="CanalWater"'),
 ('front="entry",bays=None,roof_mat=None,over=0,side_entry=False):','front="entry",bays=None,roof_mat=None,over=0,side_entry=False):'),
 ('                u=face.length*(j+.5)/n','''                u=face.length*(j+.5)/n
                if entry and j==n//2:
                    u=face.length/2'''),
 ('if h.lod==2:\n                slots=[s for s in slots if side==0 and i==min(1,levels-1) and not s[5]][:1]', '''if h.lod==2:
                slots=[s for s in slots if side==0 and i==min(1,levels-1) and not s[5]][:1]'''),
 ('def glass_panel(h,points,out):\n    # Readable translucent structure at normal camera scale. No body emission.\n    thin_glass(h.body,points,out)', '''def glass_panel(h,points,out):
    normal=Vector(out).normalized()*.0025
    h.body.polygon([Vector(v)+normal for v in points],normal,"CourtGlass")
    h.body.polygon([Vector(v)-normal for v in points],-normal,"CourtGlass")'''),
 ('    f=edges(p)[0]\n    for i in range(12 if h.lod==0 else 6):','    f=edges(p)[0]\n    for i in range(12 if h.lod==0 else 6):'),
 ('    section(h,p,.075,8.12,2,"flat",front="windows")','    section(h,p,.075,8.12,2,"flat",front="entry")'),
 ('        for a,bx in ((pier_l,left-.004),(right+.004,pier_r)):','        for a,bx in ((pier_l,left-.004),(right+.004,pier_r)):'),
 ('            for j in range(segments):\n                aa=math.pi*(j+.05)/segments\n                bb=math.pi*(j+.95)/segments', '''            start=-math.radians(28) if horseshoe else 0
            total=math.pi-2*start
            for j in range(segments):
                aa=start+total*(j+.05)/segments
                bb=start+total*(j+.95)/segments'''),
 ('for q,rr,rise in ((aa,radius,.51),(bb,radius,.51),\n                                  (bb,radius+.17,.69),(aa,radius+.17,.69)):', '''for q,rr,rise in ((aa,radius,.79 if horseshoe else .51),(bb,radius,.79 if horseshoe else .51),
                                  (bb,radius+.17,.97 if horseshoe else .69),(aa,radius+.17,.97 if horseshoe else .69)):'''),
 ('spring+rise*math.sin(q)+(.31 if horseshoe else 0)','spring+rise*math.sin(q)+(.16 if horseshoe else 0)'),
])
patch("r12_flats.py",[
 ('    section(h,p,.057,10.46,3,"flat",0,front="windows",bays=3)','''    section(h,p,.057,10.46,3,"flat",0,omit=(0,),bays=3)
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
        g.row(h,face,low,high,BRICK,points)'''),
 ('for x,height,r in ((3.58,1.48,1.16),(8.08,3.42,1.42),(12.43,6.65,1.45)):', 'for x,height,r in ((3.58,1.48,1.16),(8.08,3.42,1.42),(12.43,6.86,1.45)):'),
 ('for i in range(4):\n        slab(h,(9.79+.17*i,10.75-.13*i,4.13+.45*i,8.04+.25*i),', 'for i in range(4):\n        slab(h,(9.79+.17*i,10.75-.13*i,4.13+.45*i,8.04+.25*i),'),
])
patch("bake_r12.py",[
 ('"TinOxide","GardenGlass","TinGreen"}','"TinOxide","GardenGlass","CourtGlass","TinGreen"}'),
])
patch("audit_round5.py",[
 ('key!="GardenGlass"','key not in {"GardenGlass","CourtGlass"}'),
])
patch("r12_specs.py",[
 ('prop("hedge",w*.79,2.4,w*.29,.52,.82)))','prop("hedge",w*.79,2.4,w*.29,.52,.82)))\n                        if design=="VillaMurHabite":\n                            props[-1]=prop("hedge",14.35,2.4,1.68,.52,.82)'),
])
patch("preview_r12.py",[
 ('    fresh=[new(next(a for a in plans if a["design"]==f and a["lot"][1]==desired)) for f in families]',
  '''    fresh=[new(next(a for a in plans if a["design"]==f and a["lot"][1]==desired
                    and (zone=="Z4" or a["colourway"]=="ABC"[i%3]))) for i,f in enumerate(families)]'''),
])
