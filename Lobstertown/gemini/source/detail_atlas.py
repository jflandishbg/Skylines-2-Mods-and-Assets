"""Build family atlases from the established layout and CC0 scan inputs."""
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
import json
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from round5_atlas import source_box
from round5_specs import make

ROOT=Path(__file__).resolve().parents[1]
INDUSTRY=ROOT.name.endswith("round10b")
OLD=ROOT.with_name(ROOT.name[:-1])
SCANS=ROOT.parent/"2026-11-10_round10b/source/scans"
LIB=ROOT.parent.parent/"textures"
STEPS=("main","_LOD1","_LOD2")
MAPS=("BaseColor","Normal","MaskMap","ControlMask","Emissive")
BRICKS={"Brick085":"Bricks085","Brick094":"Bricks094","BuffBrick":"Bricks002",
        "BrownBrick":"Bricks094","Brick074":"Bricks074","Brick054":"Bricks054"}
RENAMES={"RenderSide":"RevealStone","RenderGrey":"PaintedDrum","Brick097":"Ivy"}
UV_GLASS=("GreyBlue","GardenGlass")

def read(p):
    return json.loads(p.read_text(encoding="utf8"))

def scan_file(asset,key):
    folder=SCANS/asset if (SCANS/asset).is_dir() else LIB/"brick"/asset
    return next(iter(sorted(folder.glob(f"*_{key}.*"))),None)

def load_scan(asset,key,w,h):
    path=scan_file(asset,key)
    if not path:return None
    with Image.open(path) as f:
        if asset=="Bricks002":
            canvas=Image.new(f.mode,(w,h))
            for y in range(2):
                for x in range(2):
                    a,b=round(x*w/2),round(y*h/2)
                    c,d=round((x+1)*w/2),round((y+1)*h/2)
                    canvas.paste(f.resize((c-a,d-b),Image.Resampling.LANCZOS),(a,b))
            return canvas
        return f.resize((w,h),Image.Resampling.LANCZOS)

def atlas_group(a):
    if INDUSTRY:
        return a["family"]
    if a["zone_key"]=="Z1A":
        return "A"
    # Each owner covers three architectural families.
    styles=list(dict.fromkeys(b["design"] for b in make("Z1C")))
    return "ABCD"[styles.index(a["design"])//3]

def owners(plans):
    groups={}
    for a in plans:
        groups.setdefault((a["zone_key"],atlas_group(a)),a["name"])
    return groups

def scan_mask(rough,ao,size,metal=4):
    rough=rough.convert("L") if rough else Image.new("L",size,192)
    ao=ao.convert("L") if ao else Image.new("L",size,242)
    return Image.merge("RGBA",(Image.new("L",size,metal),ao,Image.new("L",size,0),
                               rough.point(lambda x:255-x)))

def bake_color(color,ao=None,cap=None):
    a=np.asarray(color.convert("RGB"),dtype=np.float32).copy()
    if ao is not None:
        f=.78+.22*np.asarray(ao.convert("L"),dtype=np.float32)/255
        a*=f[:,:,None]
    a=np.ceil(a).clip(0,255)
    if cap is not None:
        high=a.max(axis=2)[:,:,None]
        a=np.maximum(a,np.ceil(high*(1-cap)))
    return Image.fromarray(a.astype("uint8"),"RGB").convert("RGBA")

def reflective_glass(w,h,greenhouse):
    t=np.linspace(0,1,h,dtype=np.float32)[:,None]
    x=np.linspace(0,1,w,dtype=np.float32)[None,:]
    value=(.49-.31*t)+.20*np.exp(-((t-.30+.13*x)/.18)**2)
    base=np.array((104,150,154) if greenhouse else (95,123,137))
    a=np.uint8(np.clip(value[:,:,None]*base[None,None,:]+9,0,255))
    im=Image.fromarray(a,"RGB").convert("RGBA")
    if greenhouse:
        leaf=leaf_scan(w,h)
        fade=np.asarray(leaf.getchannel("A"),dtype=np.float32)*np.clip((t-.48)*1.25,0,.52)
        leaf.putalpha(Image.fromarray(np.uint8(fade),"L"))
        im.alpha_composite(leaf)
    return im

def leaf_scan(w,h):
    source=load_scan("LeafSet029","Color",w,h).convert("RGBA")
    alpha=load_scan("LeafSet029","Opacity",w,h).convert("L").point(lambda p:0 if p<46 else 255 if p>175 else p)
    source.putalpha(alpha)
    # Fill multiple UV quadrants with real ivy while retaining leaf-shaped cutouts.
    layer=Image.new("RGBA",(w,h))
    for i,(x,y) in enumerate(((0,0),(.45,.04),(.02,.44),(.44,.44))):
        small=source.transpose(Image.Transpose.FLIP_LEFT_RIGHT) if i%2 else source
        small=small.resize((max(4,round(w*.54)),max(4,round(h*.54))),Image.Resampling.LANCZOS)
        layer.alpha_composite(small,(round(x*w),round(y*h)))
    return layer

def steel(w,h):
    im=Image.new("RGBA",(w,h),(72,91,78,255))
    d=ImageDraw.Draw(im)
    for j in range(5):
        for i in range(4):
            x=round(i*w/4);y=round(j*h/5)
            v=(i*11+j*7)%8
            d.rectangle((x+1,y+1,round((i+1)*w/4)-1,round((j+1)*h/5)-1),
                        fill=(74+v,87+v,79+v,255))
            d.line((x,y,x,round((j+1)*h/5)),fill=(40,51,48,255),width=max(1,w//167))
            d.line((x,y,round((i+1)*w/4),y),fill=(44,56,49,255),width=max(1,h//167))
            r=max(1,w//210)
            for k in range(4):
                xx=x+round((k+.4)*w/16)
                yy=y+max(2,round(h/63))
                d.ellipse((xx-r,yy-r,xx+r,yy+r),fill=(126,137,118,255),outline=(49,58,48,255))
    return im

def reveal(im,old_cells,dim,w,h,kind):
    if kind=="Normal":
        return im.crop(source_box(old_cells["Dressed"]["uv"],dim)).resize((w,h),Image.Resampling.LANCZOS)
    t=np.linspace(0,1,h,dtype=np.float32)[:,None]
    ao=np.uint8(165+77*np.sin(np.pi*t))*np.ones((h,w),dtype=np.uint8)
    alpha=Image.fromarray(ao,"L")
    if kind=="MaskMap":
        return Image.merge("RGBA",(Image.new("L",(w,h),5),alpha,Image.new("L",(w,h),0),Image.new("L",(w,h),35)))
    src=im.crop(source_box(old_cells["Dressed"]["uv"],dim)).resize((w,h),Image.Resampling.LANCZOS)
    return bake_color(src,alpha)

def apply(im,old_cells,cells,kind,dim,lod):
    for key,asset in BRICKS.items():
        l,t,r,b=source_box(cells[key]["uv"],dim)
        w,h=r-l,b-t
        ao=load_scan(asset,"AmbientOcclusion",w,h) if kind in {"BaseColor","MaskMap"} else None
        if kind=="BaseColor":
            crop=bake_color(load_scan(asset,"Color",w,h),ao,.398 if key=="BuffBrick" else .548)
        elif kind=="Normal":
            crop=load_scan(asset,"NormalGL",w,h).convert("RGBA")
        elif kind=="MaskMap":
            crop=scan_mask(load_scan(asset,"Roughness",w,h),ao,(w,h))
        else:
            continue
        im.paste(crop,(l,t))
    for key in ("RoofGreen","Ivy","PaintedDrum","RevealStone",*UV_GLASS):
        if key not in cells:continue
        l,t,r,b=source_box(cells[key]["uv"],dim)
        w,h=r-l,b-t
        crop=None
        if key in ("RoofGreen","Ivy"):
            asset="Grass005" if key=="RoofGreen" else "LeafSet029"
            if kind=="BaseColor":
                if key=="Ivy":
                    crop=leaf_scan(w,h)
                else:
                    cover=load_scan(asset,"Color",w,h).convert("RGBA")
                    shade=Image.new("L",(w,h),170)
                    crop=bake_color(cover,shade)
            elif kind=="Normal":
                crop=load_scan(asset,"NormalGL",w,h).convert("RGBA")
            elif kind=="MaskMap":
                crop=Image.new("RGBA",(w,h),(0,224,0,21))
        elif key=="RevealStone" and kind in ("BaseColor","Normal","MaskMap"):
            crop=reveal(im,old_cells,dim,w,h,kind)
        elif key=="PaintedDrum":
            if kind=="BaseColor":crop=steel(w,h)
            if kind=="MaskMap":crop=Image.new("RGBA",(w,h),(155,242,0,76))
            if kind=="Normal":crop=Image.new("RGBA",(w,h),(128,128,255,255))
        elif key in UV_GLASS:
            if kind=="BaseColor":crop=reflective_glass(w,h,key=="GardenGlass")
            if kind=="MaskMap":crop=Image.new("RGBA",(w,h),(12,243,0,198))
            if kind=="Normal":crop=Image.new("RGBA",(w,h),(128,128,255,255))
        if crop is not None:im.paste(crop,(l,t))
    return im

def main():
    plans=list(make())
    group=owners(plans)
    old=read(OLD/"source/kit/atlas_layout.json")
    reference={a["zone_key"]:a["name"] for a in reversed(plans)}
    result={"lods":{}}
    for j,lod in enumerate(STEPS):
        dim=4096>>j
        cells=deepcopy(old["lods"][lod])
        for src,dst in RENAMES.items():
            cells[dst]=cells.pop(src)
        for key in BRICKS:
            # The scan occupies at least 544 pixels at LOD0, covering at most 2 m.
            cells[key]["metres"]=[[1.91,1.47],[7.64,5.88],[40,40]][j]
        cells["Ivy"]["metres"]=[.69,.69] if j==0 else [2,2] if j==1 else [30,30]
        cells["RoofGreen"]["metres"]=[[1.45,1.45],[6,6],[40,40]][j]
        cells["PaintedDrum"]["metres"]=[[6.85,5.0],[13.7,10.0],[40,40]][j]
        result["lods"][lod]=cells
        suffix="" if j==0 else lod
        old_zone=next(iter(reference))
        n=reference[old_zone]
        for kind in MAPS:
            with Image.open(OLD/f"import_{old_zone}"/n/f"{n}{suffix}_{kind}.png") as src:
                im=apply(src.convert("RGBA"),old["lods"][lod],cells,kind,dim,j)
            for (zone,family),owner in group.items():
                folder=ROOT/f"import_{zone}"/owner
                folder.mkdir(parents=True,exist_ok=True)
                out=im
                if kind=="BaseColor":
                    # An atlas carries only the inscriptions referenced by its own group.
                    out=im.copy()
                    d=ImageDraw.Draw(out)
                    keep={"Sign_"+a["design"] for a in plans if a["zone_key"]==zone and atlas_group(a)==family}
                    for key,cell in cells.items():
                        if key.startswith("Sign_") and key not in keep:
                            l,t,r,b=source_box(cell["uv"],dim)
                            d.rectangle((l,t,r-1,b-1),fill=(74,78,70,255))
                out.save(folder/f"{owner}{suffix}_{kind}.png",compress_level=2)
        print("ATLAS_LOD_READY",lod,len(group),flush=True)
    result["order"]=list(result["lods"]["main"])
    (ROOT/"source/kit/atlas_layout.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")

if __name__=="__main__":
    main()
