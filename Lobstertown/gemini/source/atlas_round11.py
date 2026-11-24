"""Preserve scan tiles and add the residential plaques, dial and greenhouse glazing."""
import json
import random
from pathlib import Path
from PIL import Image,ImageDraw
from round5_atlas import sign,dial,spec,reserve,source_box
from round5_specs import make

ROOT=Path(__file__).resolve().parents[1]
PRE=ROOT/"previews"/"inscriptions"
REF=ROOT.parent/"2026-11-10_round10"
OWNER="NA_PdDRedentsTissage_L1_4x4"
MAPS=("BaseColor","Normal","MaskMap","ControlMask","Emissive")
BG={"BaseColor":(82,83,75,255),"Normal":(128,128,255,255),"MaskMap":(18,255,0,32),
    "ControlMask":(0,0,0,255),"Emissive":(0,0,0,255)}
EXTRAS=("SolarSlate","RaceWater","YardSetts","RoofGreen","CopperVent","GardenGlass","MatteDial")

def glazed(w,h):
    image=Image.new("RGBA",(w,h))
    pen=ImageDraw.Draw(image)
    for y in range(h):
        t=y/max(1,h-1)
        pen.line((0,y,w,y),fill=(round(110-52*t),round(155-49*t),round(147-52*t),255))
    rng=random.Random(229)
    for i in range(24):
        x=rng.randint(0,w-1)
        y=round(h*rng.uniform(.63,1))
        pen.ellipse((x-w*.046,y-h*.065,x+w*.035,y+h*.04),fill=(61,96,73,255))
    pen.line((0,h*.35,w,h*.13),fill=(152,184,171,255),width=max(1,h//53))
    return image

def main():
    PRE.mkdir(parents=True,exist_ok=True)
    plans=list(make())
    styles=[a for a in plans if a["colourway"]=="A" and a["lot"][1]==2]
    assert len(styles)==15
    owners={z:next(make(z))["name"] for z in ("Z1C","Z1A")}
    for z,n in owners.items():
        (ROOT/f"import_{z}"/n).mkdir(parents=True,exist_ok=True)
    old=json.loads((REF/"source/kit/atlas_layout.json").read_text(encoding="utf8"))["lods"]
    result={"lods":{}}
    for j,k in enumerate(("main","_LOD1","_LOD2")):
        dim=4096>>j
        suffix="" if j==0 else k
        cells={key:cell.copy() for key,cell in list(old[k].items())[:38]}
        signs={a["design"]:reserve(dim,38+i//4,i%4) for i,a in enumerate(styles)}
        for name,rect in signs.items():
            cells["Sign_"+name]=spec(rect,[3,1],dim)
        l,t,r,b=reserve(dim,41,3)
        middle=(l+r)//2
        numbers={"Address12":(l,t,middle-2,b),"Address14":(middle+2,t,r,b)}
        for name,rect in numbers.items():
            cells[name]=spec(rect,[.24,.16],dim)
        for i,key in enumerate(EXTRAS,42):
            metres=old[k][key]["metres"] if key in old[k] else [2.3*(j+1),2.3*(j+1)]
            cells[key]=spec(reserve(dim,i),metres,dim)
        result["lods"][k]=cells
        for kind in MAPS:
            path=REF/"import_Z10"/OWNER/f"{OWNER}{suffix}_{kind}.png"
            with Image.open(path) as src:
                ref=src.convert("RGBA")
            im=Image.new("RGBA",(dim,dim),BG[kind]) if kind=="Emissive" else ref.copy()
            pen=ImageDraw.Draw(im)
            stride=dim//7
            for i in range(38,49):
                x,y=i%7*stride,i//7*stride
                pen.rectangle((x,y,x+stride-1,y+stride-1),fill=BG[kind])
            for key in EXTRAS:
                l,t,r,b=source_box(cells[key]["uv"],dim)
                if key in old[k] and kind!="Emissive":
                    rect=source_box(old[k][key]["uv"],dim)
                    im.paste(ref.crop(rect).resize((r-l,b-t),Image.Resampling.LANCZOS),(l,t))
                elif kind=="BaseColor":
                    graphic=dial(r-l,b-t) if key=="MatteDial" else glazed(r-l,b-t)
                    im.paste(graphic,(l,t))
                elif kind=="MaskMap" and key=="GardenGlass":
                    pen.rectangle((l,t,r-1,b-1),fill=(18,255,0,36))
            if kind=="BaseColor":
                for key,(l,t,r,b) in numbers.items():
                    im.paste(sign(r-l,b-t,key[-2:],0),(l,t))
                for i,a in enumerate(styles):
                    l,t,r,b=signs[a["design"]]
                    graphic=sign(r-l,b-t,a["inscription"],i)
                    im.paste(graphic,(l,t))
                    if j==0:graphic.save(PRE/f'{a["design"]}.png')
            for z,n in owners.items():
                im.save(ROOT/f"import_{z}"/n/f"{n}{suffix}_{kind}.png",compress_level=3)
    result["order"]=list(result["lods"]["main"])
    (ROOT/"source/kit/atlas_layout.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
    print("ATLASES_READY",owners,flush=True)

if __name__=="__main__":
    main()
