"""Check same-name exports, record material measurements and assemble the visual proof."""
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json
import sys

sys.dont_write_bytecode=True
import numpy as np
from PIL import Image,ImageDraw,ImageFont

from detail_specs import INDUSTRY, PLANS, atlas_owners
from detail_atlas import BRICKS
from round5_atlas import source_box

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT.with_name(ROOT.name[:-1])
PRE=ROOT/"previews"
ZONES={"Z10":36} if INDUSTRY else {"Z1C":72,"Z1A":18}
INDUSTRIAL=("RedentsAteliers","MoulinFilature","GazometreBatterie","HalleFonderie")
INK="#273f35"
PAPER="#f5f2e8"

def read(p):
    return json.loads(p.read_text(encoding="utf8"))

def write(p,data):
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf8")

def font(n,bold=False):
    return ImageFont.truetype("C:/Windows/Fonts/"+("georgiab.ttf" if bold else "segoeui.ttf"),n)

def headline(im,title,subtitle):
    d=ImageDraw.Draw(im)
    d.rectangle((0,0,im.width,83),fill=INK)
    d.text((24,8),title,fill=PAPER,font=font(32,True))
    d.text((26,49),subtitle,fill="#dce7de",font=font(18))
    return d

def pair(a):
    name=a["design"]
    root=PRE/"closeups"
    with Image.open(root/f"{name}-old.png") as img:
        left=img.convert("RGB")
    with Image.open(root/f"{name}-new.png") as img:
        right=img.convert("RGB")
    assert left.size==right.size and left.tobytes()!=right.tobytes()
    w,h=left.size
    p=Image.new("RGB",(2*w+18+(312 if not INDUSTRY else 0),h+121),PAPER)
    d=headline(p,a["display_title"],"Matched daylight views of exported meshes · camera 25 m away, 30° down")
    d.text((16,88),"BEFORE",font=font(17,True),fill=INK)
    d.text((w+28,88),"DETAIL REBAKE",font=font(17,True),fill=INK)
    p.paste(left,(0,121))
    p.paste(right,(w+18,121))
    if not INDUSTRY:
        with Image.open(root/"R10-reference.png") as img:
            inset=img.convert("RGB")
        inset.thumbnail((282,184),Image.Resampling.LANCZOS)
        x=p.width-inset.width-15
        y=143
        d.rectangle((x-3,y-4,x+inset.width+3,y+inset.height+24),fill=PAPER)
        p.paste(inset,(x,y))
        d.text((x+4,y+inset.height+3),"Original R10 factory reference",font=font(14),fill=INK)
    p.save(PRE/f'{name}-detail-comparison.png')

def thumbnails(styles):
    grid=3 if INDUSTRY else 3
    im=Image.new("RGB",(1152,96+((len(styles)+grid-1)//grid)*168),PAPER)
    d=headline(im,"128 px silhouettes","Front and side · representative lots · original 128-pixel images")
    for i,a in enumerate(styles):
        x,y=16+(i%grid)*382,97+(i//grid)*168
        d.text((x,y),a["display_title"],font=font(17,True),fill=INK)
        for j,label in enumerate(("front","side")):
            src=PRE/"thumbnails"/f'{a["name"]}-{label}-128.png'
            with Image.open(src) as obj:
                thumb=obj.convert("RGBA")
            bounds=thumb.getchannel("A").getbbox()
            assert thumb.size==(128,128) and bounds and min(bounds[:2])>0 and max(bounds[2:])<128,src
            ox,oy=x+7+j*147,y+27
            d.rectangle((ox,oy,ox+127,oy+127),fill="#e1e8dd")
            im.paste(thumb,(ox,oy),thumb)
    im.save(PRE/"128px-sheet.png")

def inspect_atlas(folder,owner,layout):
    texture=folder/owner
    def image(kind,suffix=""):
        return Image.open(texture/f"{owner}{suffix}_{kind}.png").convert("RGBA")
    scan=image("BaseColor")
    mask=image("MaskMap")
    material=layout["main"]
    boxes={k:source_box(v["uv"],scan.width) for k,v in material.items()}
    density={}
    for k in BRICKS:
        l,t,r,b=boxes[k]
        w,h=material[k]["metres"]
        pixels=min((r-l)/w,(b-t)/h)
        assert pixels>=256,(owner,k,pixels)
        density[k]=round(pixels,1)
        data=np.asarray(scan.crop(boxes[k]),dtype=np.float32)[:,:,:3]
        high=data.max(axis=2)
        sat=((high-data.min(axis=2))/np.maximum(high,1))[high>=40]
        assert float(sat.max()) <= (.4005 if k=="BuffBrick" else .5505),(owner,k,sat.max())
    assert mask.crop(boxes["GreyBlue"]).getchannel("A").getextrema()==(198,198)
    if "GardenGlass" in boxes:
        assert mask.crop(boxes["GardenGlass"]).getchannel("A").getextrema()==(198,198)
    assert mask.crop(boxes["PaintedDrum"]).getchannel("A").getextrema()[1]<=90
    assert mask.crop(boxes["RevealStone"]).getchannel("G").getextrema()[0]<180
    assert mask.crop(boxes["YardSetts"]).getchannel("A").getextrema()[1]<=40
    assert mask.crop(boxes["SolarSlate"]).getchannel("A").getextrema()[1]<=60
    assert scan.crop(boxes["Ivy"]).getchannel("A").getextrema()==(0,255)
    for suffix in ("","_LOD1","_LOD2"):
        assert image("Emissive",suffix).convert("RGB").getextrema()==((0,0),(0,0),(0,0))
    return min(density.values())

def verify_zone(zone,layout):
    out=ROOT/f"import_{zone}"
    plans=[a for a in PLANS if a["zone_key"]==zone]
    names={a["name"] for a in plans}
    wanted=ZONES[zone]
    manifest=read(out/"manifest.json")
    records=manifest["assets"]
    probe=read(out/"probe-results.json")
    audit=read(out/"audit.json")
    windows=read(out/"window-coverage.json")
    assert wanted==len(names)==manifest["registrations"]
    assert names==set(probe)==set(audit)==set(windows)=={a["name"] for a in records}
    atlases=set(manifest["texture_owners"])
    assert len(atlases)==(1 if zone=="Z1A" else 4)
    assert len(manifest["sha256"])==wanted*7+14*len(atlases)
    for name,h in manifest["sha256"].items():
        assert sha256((out/name).read_bytes()).hexdigest()==h,name
    assert len(list(out.rglob("*.fbx")))==wanted*6
    assert len(list(out.rglob("*.png")))==15*len(atlases)
    assert all(not v["backface_first_hits"] for a in probe.values() for lod in a.values() for v in lod.values())
    assert all(v["covered"]==0 for a in windows.values() for k,v in a.items() if k in ("main","_LOD1"))
    owner_check={owner:inspect_atlas(out,owner,layout) for owner in sorted(atlases)}
    for a in plans:
        n=a["name"]
        _,owner=atlas_owners(a)
        if n==owner:continue
        path=out/n
        links=read(path/"settings.json")["sharedAssets"]
        assert len(links)==15 and all((path/ref).resolve().parent.name==owner and (path/ref).is_file() for ref in links.values())
    density=[a["tris_per_m2"] for a in records]
    assert min(density)>=8
    top=[max(a["lods"][k]["triangles"] for a in records) for k in ("main","_LOD1","_LOD2")]
    assert all(a<=b for a,b in zip(top,plans[0]["budget"]))
    coverage=[a["coverage"]["roofed_pct"] for a in records]
    limits=(45,55) if INDUSTRY else (40,48)
    assert limits[0]<=min(coverage)<=max(coverage)<=limits[1]
    return dict(registrations=wanted,fbxs=wanted*6,atlases=owner_check,
                tris_per_m2=[min(density),max(density)],roofed_pct=[min(coverage),max(coverage)],
                triangle_maxima=top,covered_panes_near_and_mid=0,exposed_backfaces=0)

def main():
    old=read(OLD/"designs.json")
    prior={a["name"]:a for a in old["designs"]}
    assert set(prior)=={a["name"] for a in PLANS}
    immutable=("product","truck_strip_lot_m","pedestrian_gate_lot_m","vehicle_gate_lot_m",
               "vehicle_doors_lot_m","pedestrian_point_lot_m","working_points") if INDUSTRY else (
               "lot","roof_tile","households","entrances","front_walks","zone_key","access")
    assert all(all(a[k]==prior[a["name"]][k] for k in immutable) for a in PLANS)
    layout=read(ROOT/"source/kit/atlas_layout.json")["lods"]
    results={z:verify_zone(z,layout) for z in ZONES}
    styles=[a for a in PLANS if a["lot"][1]==(5 if INDUSTRY else 3) and (INDUSTRY or a["colourway"]=="A")]
    assert len(styles)==(12 if INDUSTRY else 15)
    for a in styles:
        if not INDUSTRY or a["design"] in INDUSTRIAL:
            pair(a)
    thumbnails(styles)
    old["batch"]="R10b" if INDUSTRY else "R11b"
    old["designs"]=[dict(a,atlas_group=atlas_owners(a)[0],atlas_owner=atlas_owners(a)[1]) for a in PLANS]
    write(ROOT/"designs.json",old)
    if not INDUSTRY:
        s=(OLD/"RETIREMENT-LIST.md").read_text(encoding="utf8")
        s+="\nMercer Mansard Pair is a texture owner. Preserve its installed atlas maps for the surviving Z1C houses.\n"
        (ROOT/"RETIREMENT-LIST.md").write_text(s,encoding="utf8")
    write(ROOT/"qa-summary.json",dict(zones=results,comparison_pairs=4 if INDUSTRY else 15))
    print(json.dumps(results),flush=True)

if __name__=="__main__":
    main()
