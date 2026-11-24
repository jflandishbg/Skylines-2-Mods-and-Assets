"""Build linked Round 12 atlases from the two previously approved material sets."""
from pathlib import Path
import json
from PIL import Image, ImageDraw
import numpy as np
from r12_specs import make, atlas_owners
from round5_atlas import source_box, sign

ROOT=Path(__file__).resolve().parents[1]
REF=ROOT.parent/"2026-11-10_round11b"
COLOR=ROOT.parent/"2026-11-11_round10c"
COLOR_LAYOUT=ROOT.parent/"2026-11-10_round10b/source/kit/atlas_layout.json"
MAPS=("BaseColor","Normal","MaskMap","ControlMask","Emissive")
SIGNS=("VillaJeuDePaume","ImmeubleBowWindows","ImmeubleImprimeur","ImmeubleJardinHiver",
       "CoureePompe","PensionDockers","LavoirHabite","HotelMeublePort")

def read(p):
    return json.loads(p.read_text(encoding="utf8"))

def water(size,kind):
    width,height=size
    y,x=np.meshgrid(np.arange(height)*2*np.pi/height,np.arange(width)*2*np.pi/width,indexing="ij")
    if kind=="BaseColor":
        wave=np.sin(6*y+1.2*np.sin(2*x+3*y))*.60+np.sin(13*y-2*x)*.23+np.sin(23*y+3*x)*.17
        high=np.clip((wave-.28)*1.12,0,1)
        color=np.stack([31+7*wave+8*high,55+9*wave+9*high,57+10*wave+10*high,np.full_like(wave,255)],axis=2)
        return Image.fromarray(np.uint8(np.clip(color,0,255)))
    if kind=="Normal":
        return Image.new("RGBA",size,(128,128,255,255))
    return Image.new("RGBA",size,(0,240,0,34))

def main():
    layouts=read(REF/"source/kit/atlas_layout.json")
    color_layouts=read(COLOR_LAYOUT)
    plans=list(make())
    groups={(a["zone_key"],atlas_owners(a)[1]) for a in plans}
    titles={a["design"]:a["inscription"] for a in plans}
    src=REF/"import_Z1C"
    source_owner=read(src/"manifest.json")["texture_owners"][0]
    color_dir=COLOR/"import_Z10"
    color_owner=read(color_dir/"manifest.json")["texture_owners"][0]
    for suffix,cells in layouts["lods"].items():
        tag="" if suffix=="main" else suffix
        old_signs=[cells.pop(k) for k in list(cells) if k.startswith("Sign_")]
        cells["CanalWater"]=cells.pop("PaintedDrum")
        cells["CanalWater"]["metres"]=[4.8,5.9] if not tag else [40,40]
        cells["CourtGlass"]=old_signs.pop()
        cells["CourtGlass"]["metres"]=[2.85,3.65] if not tag else [40,40]
        cells.update({"Sign_"+key:slot for key,slot in zip(SIGNS,old_signs)})
        for kind in MAPS:
            with Image.open(src/source_owner/f"{source_owner}{tag}_{kind}.png") as asset:
                im=asset.convert("RGBA")
            if kind in ("BaseColor","Normal","MaskMap"):
                with Image.open(color_dir/color_owner/f"{color_owner}{tag}_{kind}.png") as asset:
                    for name in ("Brick085","Brick094","BuffBrick"):
                        cell=source_box(cells[name]["uv"],im.width)
                        source=source_box(color_layouts["lods"][suffix][name]["uv"],asset.width)
                        size=(cell[2]-cell[0],cell[3]-cell[1])
                        im.paste(asset.crop(source).resize(size,Image.Resampling.LANCZOS),cell[:2])
                        if name!="RoofGreen" and not tag:
                            assert min(a/b for a,b in zip(size,cells[name]["metres"]))>=256
            if kind in ("BaseColor","Normal","MaskMap"):
                l,t,r,b=source_box(cells["CanalWater"]["uv"],im.width)
                im.paste(water((r-l,b-t),kind),(l,t))
                l,t,r,b=source_box(cells["CourtGlass"]["uv"],im.width)
                source=source_box(cells["GreyBlue"]["uv"],im.width)
                im.paste(im.crop(source).resize((r-l,b-t),Image.Resampling.LANCZOS),(l,t))
            for zone,owner in sorted(groups):
                out=ROOT/f"import_{zone}"/owner
                out.mkdir(parents=True,exist_ok=True)
                canvas=im
                if kind=="BaseColor":
                    canvas=im.copy()
                    draw=ImageDraw.Draw(canvas)
                    keep={a["design"] for a in plans if atlas_owners(a)[1]==owner}
                    for i,slot in enumerate(old_signs):
                        l,t,r,b=source_box(slot["uv"],im.width)
                        if i<len(SIGNS) and SIGNS[i] in keep:
                            canvas.paste(sign(r-l,b-t,titles[SIGNS[i]],i),(l,t))
                        else:
                            draw.rectangle((l,t,r-1,b-1),fill=(74,78,70,255))
                canvas.save(out/f"{owner}{tag}_{kind}.png",compress_level=2)
        print("R12_ATLASES",suffix,len(groups),flush=True)
    layouts["order"]=list(layouts["lods"]["main"])
    (ROOT/"source/kit/atlas_layout.json").write_text(json.dumps(layouts,indent=2)+"\n",encoding="utf8")

if __name__=="__main__":
    main()
