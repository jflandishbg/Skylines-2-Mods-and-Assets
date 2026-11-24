"""Verify the Round 11 package and assemble the comparison sheets and handoff lists."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode=True
from PIL import Image,ImageDraw,ImageFont
from round5_atlas import source_box
from round5_specs import make

ROOT=Path(__file__).resolve().parents[1]
PRE=ROOT/"previews"
ZONE_COUNTS={"Z1C":72,"Z1A":18}
PAPER="#f5f2e8"
INK="#253d33"

def read(p):
    return json.loads(p.read_text(encoding="utf8"))

def write(p,data):
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf8")

def font(n,bold=False):
    return ImageFont.truetype("C:/Windows/Fonts/"+("georgiab.ttf" if bold else "segoeui.ttf"),n)

def sheet(w,h,title,subtitle):
    im=Image.new("RGB",(w,h),PAPER)
    pen=ImageDraw.Draw(im)
    pen.rectangle((0,0,w,94),fill=INK)
    pen.text((24,10),title,fill=PAPER,font=font(35,True))
    pen.text((26,56),subtitle,fill="#dce7de",font=font(20))
    return im,pen

def paste(im,path,xy,size=None):
    with Image.open(path) as src:
        cell=src.convert("RGBA")
    assert cell.getchannel("A").getbbox(),path
    if size:cell=cell.resize(size,Image.Resampling.LANCZOS)
    im.paste(cell,xy,cell)

def profiles(styles):
    items=[*styles,dict(design="CouronnePavilionPair",display_title="Couronne Pavilion Pair",zone_key="Existing")]
    im,pen=sheet(1344,1010,"R11 · Rooflines at one scale",
        "Fifteen new families beside the existing Couronne Pavilion Pair · same orthographic camera and scale")
    for i,a in enumerate(items):
        x,y=(i%4)*336,102+(i//4)*225
        if a["zone_key"]=="Existing":
            pen.rectangle((x+9,y+2,x+327,y+218),fill="#e3eadf",outline="#9fae9e",width=1)
        paste(im,PRE/f'{a["design"]}-shape.png',(x+13,y),(310,198))
        pen.text((x+168,y+187),a["display_title"],anchor="mt",fill=INK,font=font(17,True))
        pen.text((x+168,y+208),a["zone_key"],anchor="mt",fill="#566c5e",font=font(13))
    im.save(PRE/"R11-silhouettes.png")

def thumbnails(styles):
    im,pen=sheet(1122,941,"R11 · 128 px silhouettes",
        "Front and right side views at native 128 px · fifteen families on representative short lots")
    for i,a in enumerate(styles):
        x,y=19+(i%3)*371,104+(i//3)*165
        pen.text((x,y),a["display_title"],font=font(17,True),fill=INK)
        for j,label in enumerate(("front","side")):
            path=PRE/"thumbnails"/f'{a["name"]}-{label}-128.png'
            with Image.open(path) as src:
                alpha=src.convert("RGBA").getchannel("A")
                bounds=alpha.getbbox()
                assert src.size==(128,128) and bounds and min(bounds[:2])>0 and max(bounds[2:])<128,path
            xx,yy=x+8+j*151,y+27
            pen.rectangle((xx,yy,xx+127,yy+127),fill="#e1e8dd")
            paste(im,path,(xx,yy))
    im.save(PRE/"R11-128px-sheet.png")

def street():
    day=Image.open(PRE/"R11-street-day.png").convert("RGB")
    night=Image.open(PRE/"R11-street-night.png").convert("RGB")
    assert day.size==night.size and day.tobytes()!=night.tobytes()
    im,pen=sheet(day.width,2*day.height+155,"R11 · Maisons de Ville",
        "Eight new homes with the existing Couronne Pavilion Pair and Basin Loggia House · same camera at day and night")
    pen.text((26,98),"DAY",font=font(19,True),fill=INK)
    im.paste(day,(0,125))
    pen.text((26,128+day.height),"NIGHT",font=font(19,True),fill=INK)
    im.paste(night,(0,155+day.height))
    im.save(PRE/"R11-street-day-night.png")

def inventory(names):
    imported=Path("C:/Users/<you>/AppData/LocalLow/Colossal Order/Cities Skylines II/ImportedData")
    assert imported.is_dir()
    pattern=re.compile(r"^(.+)_[0-9a-fA-F]{32}\.Prefab$",re.I)
    live=set()
    for p in imported.rglob("*.Prefab"):
        match=pattern.fullmatch(p.name)
        if match and match[1]==p.parent.name:
            live.add(match[1])
    assert len(live)>=800,len(live)
    collisions={n.casefold() for n in names}&{n.casefold() for n in live}
    assert not collisions,collisions
    retirees={
       "Z1A":[n for n in live if re.match(
           r"^NA_PdD(?:SideHallParapetHouse[BC]?(?:Left|Right)|Delaware(?:Bay|Tall)MansardHouse[BC]?|"
           r"SideHall(?:FullGalerie|Galerie|Loggia)HouseC(?:Left|Right))_L1_1x[456]$",n)],
       "Z1C":[n for n in live if re.match(r"^NA_PdD(?:MercerMansardPair|RueDesTilleulsPair)[BC]?_L1_2x[23]$",n)],
    }
    assert {k:len(v) for k,v in retirees.items()}=={"Z1A":54,"Z1C":6},retirees
    lines=["# Round 11 retirement candidates","",
           "These names were matched to installed prefab records. Claude and the author handle the Recycle Bin step with the game closed, in the same session as the new imports.",
           ""]
    for key in ("Z1C","Z1A"):
        lines.extend([f"## {key} · {len(retirees[key])}","","\n".join("- "+n for n in sorted(retirees[key])),""])
    (ROOT/"RETIREMENT-LIST.md").write_text("\n".join(lines),encoding="utf8")
    return len(live)

def check_zone(zone,plans,layout):
    out=ROOT/f"import_{zone}"
    expected=ZONE_COUNTS[zone]
    names={a["name"] for a in plans}
    manifest,probe,audit,window=(read(out/f) for f in ("manifest.json","probe-results.json","audit.json","window-coverage.json"))
    assert len(names)==manifest["registrations"]==expected
    assert names==set(probe)==set(audit)==set(window)=={a["name"] for a in manifest["assets"]}
    assert len(manifest["sha256"])==expected*7+14
    for p,h in manifest["sha256"].items():
        assert sha256((out/p).read_bytes()).hexdigest()==h,p
    assert len(list(out.rglob("*.fbx")))==expected*6
    assert len(list(out.rglob("*.png")))==15
    assert all(not x["backface_first_hits"] for d in probe.values() for lod in d.values() for x in lod.values())
    near=[v for p in window.values() for k,v in p.items() if k in ("main","_LOD1")]
    assert all(v["covered"]==0 for v in near)
    routes=[rec["routes"] for a in audit.values() for rec in a.values()]
    assert sum(len(v["door_leaf_rays"]) for v in routes)==3*sum(len(a["entrances"]) for a in plans)
    owner=manifest["texture_owner"]
    smooth={"YardSetts":0,"SolarSlate":0}
    for suffix in ("","_LOD1","_LOD2"):
        prefix=out/owner/f"{owner}{suffix}_"
        im=Image.open(str(prefix)+"Emissive.png").convert("RGB")
        assert im.getextrema()==((0,0),(0,0),(0,0))
        mask=Image.open(str(prefix)+"MaskMap.png")
        for key in smooth:
            rect=source_box(layout[suffix or "main"][key]["uv"],mask.width)
            smooth[key]=max(smooth[key],mask.crop(rect).getchannel("A").getextrema()[1])
    assert smooth["YardSetts"]<=40 and smooth["SolarSlate"]<=60
    atlas=Image.open(out/owner/f"{owner}_BaseColor.png").convert("RGBA")
    for a in plans:
        if a["name"]!=owner:
            p=out/a["name"]
            shares=read(p/"settings.json")["sharedAssets"]
            assert len(shares)==15 and all((p/v).resolve().is_file() for v in shares.values())
        if a["lot"][1]==2 and a["colourway"]=="A":
            rect=source_box(layout["main"]["Sign_"+a["design"]]["uv"],atlas.width)
            with Image.open(PRE/"inscriptions"/f'{a["design"]}.png') as crop:
                assert crop.convert("RGBA").tobytes()==atlas.crop(rect).tobytes()
    roof=[a["coverage"]["roofed_pct"] for a in manifest["assets"]]
    height=max(a["lods"]["main"]["bounds_m"][1][2] for a in manifest["assets"])
    triangles=[max(a["lods"][key]["triangles"] for a in manifest["assets"]) for key in ("main","_LOD1","_LOD2")]
    assert 40<=min(roof)<=max(roof)<=48 and height<=14
    assert all(t<=l for t,l in zip(triangles,plans[0]["budget"]))
    return dict(registrations=expected,fbxs=6*expected,roofed_pct=[min(roof),max(roof)],
                tallest_m=height,max_triangles=triangles,covered_near_mid_panes=0,
                near_mid_panes=sum(v["panes"] for v in near),exposed_backfaces=0,
                open_passage_rays=sum(v["open_passage_rays"] for v in routes),mask_smoothness_max=smooth)

def main():
    plans=list(make())
    assert len(plans)==90
    assert set(Counter(a["design"] for a in plans).values())=={6}
    assert all(a["level"]==1 and a["access"]=="Front" and {p["kind"] for p in a["props"]}=={"tree","hedge"} for a in plans)
    styles=[a for a in plans if a["colourway"]=="A" and a["lot"][1]==3]
    wide=[a for a in styles if a["zone_key"]=="Z1C"]
    assert len(styles)==15 and sum(a["walls"][2]>=3 for a in wide)>=4
    eaves=sorted(a["eave_m"] for a in wide)
    assert all(b-a>.5 for a,b in zip(eaves,eaves[3:]))
    live=inventory({a["name"] for a in plans})
    layout=read(ROOT/"source/kit/atlas_layout.json")["lods"]
    checks={z:check_zone(z,[a for a in plans if a["zone_key"]==z],layout) for z in ZONE_COUNTS}
    profiles(styles)
    thumbnails(styles)
    street()
    write(ROOT/"designs.json",dict(project="New France",batch="R11",coordinate_system="Metres from front-left lot corner. +X right, +Y rear, +Z up.",designs=plans))
    result=dict(zones=checks,installed_prefab_names_checked=live,name_collisions=0,
                retirement_candidates={"Z1C":6,"Z1A":54},thumbnail_pairs=15)
    write(ROOT/"qa-summary.json",result)
    print(json.dumps(result),flush=True)

if __name__=="__main__":
    main()
