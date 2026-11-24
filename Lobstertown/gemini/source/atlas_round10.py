"""Shared Round 10 atlases, with separate industrial material and lettering tiles."""
import json
import math
from pathlib import Path
import random
from PIL import Image, ImageDraw
from round5_atlas import sign, spec, reserve, source_box, tone_scan
from round5_specs import make

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT.parent/"2026-11-09_round9"
REF="NA_PdDCiteGaleries_L1_2x3"
KINDS=("BaseColor","Normal","MaskMap","ControlMask","Emissive")
BG={"BaseColor":(81,83,74,255),"Normal":(128,128,255,255),
    "MaskMap":(18,255,0,32),"ControlMask":(0,0,0,255),"Emissive":(0,0,0,255)}
EXTRAS={
 "SolarSlate":("SlateDark",(52,67,76),48,[10,8]),
 "RaceWater":("GreyBlue",(62,96,91),38,[6,5]),
 "YardSetts":("FrontFlags",(148,143,130),32,[10,10]),
 "RoofGreen":("RenderSage",(113,132,72),20,[7,7]),
 "CopperVent":("TinGreen",(93,133,108),34,[6,6]),
 "LoadingDoor":("TinFlat",(79,95,83),32,[6,5]),
 "TimberStack":("Deck",(164,131,88),29,[4,3]),
 "CanalStone":("Dressed",(163,156,132),32,[8,6]),
}
PAVING="YardSetts"

def tile_image(source,target,w,h,kind):
    tile=source.resize((w,h),Image.Resampling.LANCZOS)
    tone_scan(tile,(0,0,w,h),target)
    pen=ImageDraw.Draw(tile)
    if kind in {"SolarSlate","LoadingDoor"}:
        rows=17 if kind=="SolarSlate" else 11
        for i in range(1,rows):
            y=round(i*h/rows)
            pen.line((0,y,w,y),fill=tuple(c-10 for c in target),width=max(1,h//205))
            if kind=="SolarSlate":
                for j in range(1,9):
                    x=round((j-.46*(i%2))*w/9)
                    pen.line((x,y-h/rows,x,y),fill=tuple(c-6 for c in target),width=max(1,w//230))
    if kind=="RaceWater":
        rng=random.Random(908)
        for i in range(h//2):
            x=rng.randrange(w); y=rng.randrange(h)
            pen.line((x,y,x+rng.randint(2,max(2,w//17)),y),fill=(81,115,110))
    return tile

def main():
    plans=list(make("Z10"))
    designs=[a for a in plans if a["lot"][1]==4]
    owner=plans[0]["name"]
    out=ROOT/"import_Z10"/owner
    out.mkdir(parents=True,exist_ok=True)
    preview=ROOT/"previews"/"inscriptions"
    preview.mkdir(parents=True,exist_ok=True)
    old=json.loads((OLD/"source/kit/atlas_layout.json").read_text(encoding="utf8"))
    layout={"lods":{}}
    for j,k in enumerate(("main","_LOD1","_LOD2")):
        dim=4096>>j
        suffix="" if j==0 else k
        cells={key:cell.copy() for key,cell in list(old["lods"][k].items())[:38]}
        signs={a["design"]:reserve(dim,38+i//4,i%4) for i,a in enumerate(designs)}
        for key,rect in signs.items():
            cells["Sign_"+key]=spec(rect,[8,1],dim)
        for i,(key,(_,_,_,metres)) in enumerate(EXTRAS.items(),41):
            factor=(1,2,6)[j]
            cells[key]=spec(reserve(dim,i),[x*factor for x in metres],dim)
        layout["lods"][k]=cells
        for kind in KINDS:
            old_path=OLD/"import_Z4"/REF/f"{REF}{suffix}_{kind}.png"
            with Image.open(old_path) as src:
                source=src.convert("RGBA")
            im=Image.new("RGBA",(dim,dim),BG[kind]) if kind=="Emissive" else source.copy()
            pen=ImageDraw.Draw(im)
            stride=dim//7
            for i in range(38,49):
                x,y=i%7*stride,i//7*stride
                pen.rectangle((x,y,x+stride-1,y+stride-1),fill=BG[kind])
            for i,a in enumerate(designs):
                if kind!="BaseColor":
                    continue
                l,t,r,b=signs[a["design"]]
                graphic=sign(r-l,b-t,a["inscription"],i)
                if a["design"]=="HalleFrigorifique":
                    px=graphic.load()
                    for y in range(graphic.height):
                        for x in range(graphic.width):
                            cr,cg,cb,alpha=px[x,y]
                            if cr>100:
                                px[x,y]=(min(211,round(cr*.91)),min(225,round(cg*1.23)),min(239,round(cb*1.99)),alpha)
                im.paste(graphic,(l,t))
                if j==0:
                    graphic.save(preview/f'{a["design"]}.png')
            for key,(src,tone,alpha,_) in EXTRAS.items():
                l,t,r,b=source_box(cells[key]["uv"],dim)
                if kind=="BaseColor":
                    sample=source.crop(source_box(old["lods"][k][src]["uv"],dim))
                    im.paste(tile_image(sample,tone,r-l,b-t,key),(l,t))
                if kind=="MaskMap":
                    pen.rectangle((l,t,r-1,b-1),fill=(18,255,0,alpha))
            im.save(out/f"{owner}{suffix}_{kind}.png",compress_level=3)
    layout["order"]=list(layout["lods"]["main"])
    (ROOT/"source/kit/atlas_layout.json").write_text(json.dumps(layout,indent=2)+"\n",encoding="utf8")
    print("ATLASES_READY",owner,flush=True)

if __name__=="__main__":
    main()
