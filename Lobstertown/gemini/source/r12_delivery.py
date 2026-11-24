"""Record installed retirement candidates and verify the Round 12 delivery."""
from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from statistics import median
from PIL import Image
import numpy as np

from r12_specs import make, atlas_owners, COUNTS
from round5_atlas import source_box

ROOT=Path(__file__).resolve().parents[1]
GAME=Path(os.environ["USERPROFILE"])/"AppData/LocalLow/Colossal Order/Cities Skylines II/ImportedData"
CANDIDATES={
    "Z1B": {"HotelParticulier":("3x5",),"ManoirFederal":("2x5",),"VillaJumelle":("2x5",)},
    "Z2B": {"RapportBriqueImmeuble":("2x4","2x5")},
}
NAME=re.compile(r"(NA_PdD\w+_L\d_\d+x\d+)_[0-9a-f]{32}\.Prefab$",re.I)

def read(p):
    return json.loads(p.read_text(encoding="utf8"))

def write(p,value):
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf8")

def inventory():
    installed={}
    for f in GAME.rglob("*.Prefab"):
        m=NAME.fullmatch(f.name)
        if m:
            installed.setdefault(m[1],[]).append(f)
    assert len(installed)>300
    plans=list(make())
    clashes=sorted(set(installed)&{a["name"] for a in plans})
    assert not clashes,clashes
    retired={}
    for zone,families in CANDIDATES.items():
        for design,lots in families.items():
            for lot in lots:
                for color in ("","B","C"):
                    name=f"NA_PdD{design}{color}_L1_{lot}"
                    assert len(installed.get(name,()))==1,(name,installed.get(name))
                    retired[name]=(zone,installed[name][0])
    dependencies={}
    for settings in ROOT.parent.rglob("settings.json"):
        if settings.is_relative_to(ROOT):
            continue
        dependent=settings.parent.name
        if dependent not in installed or dependent in retired:
            continue
        try:
            links=read(settings).get("sharedAssets",{})
        except (ValueError,UnicodeError):
            continue
        for reference in links.values():
            owner=Path(reference).parent.name
            if owner in retired:
                dependencies.setdefault(owner,set()).add(dependent)
    md=["# R12 retirement list","",
        f"Matched all 15 names to installed building Prefab records. Checked the 102 incoming names against {len(installed)} installed registrations. Claude runs the retirement plan with the game closed, in the import session.",
        "",
        "| Zone | Installed registration | Surviving dependents in the import records |",
        "| --- | --- | --- |"]
    for name,(zone,f) in retired.items():
        count=len(dependencies.get(name,()))
        mark=f"**Texture owner** · {count} installed survivors" if count else "None found"
        md.append(f"| {zone} | `{name}` | {mark} |")
    md.extend(("", "Keep all installed texture files."))
    for owner,dependents in dependencies.items():
        md.extend(("",f"## {owner}","",*(f"- `{n}`" for n in sorted(dependents))))
    (ROOT/"RETIREMENT-LIST.md").write_text("\n".join(md)+"\n",encoding="utf8")
    write(ROOT/"inventory-check.json",dict(installed_names=len(installed),new_name_collisions=clashes,
          retired={n:dict(zone=z,prefab=str(p),surviving_dependents=sorted(dependencies.get(n,()))) for n,(z,p) in retired.items()}))
    write(ROOT/"designs.json",dict(project="New France",batch="R12",coordinate_system="Metres from street-side left, +X right, +Y rear, +Z up.",
          designs=[dict(a,atlas_group=atlas_owners(a)[0],atlas_owner=atlas_owners(a)[1]) for a in plans]))
    print("INVENTORY",len(installed),len(retired),{n:len(v) for n,v in dependencies.items()},flush=True)

def material_check(out,owners):
    layout=read(ROOT/"source/kit/atlas_layout.json")["lods"]["main"]
    tile_stats={}
    for n in owners:
        base=Image.open(out/n/f"{n}_BaseColor.png")
        mask=Image.open(out/n/f"{n}_MaskMap.png")
        colors={}
        for tile,lo,hi in (("Brick085",.4,.55),("Brick094",.35,.5),("BuffBrick",.25,.4)):
            uv=source_box(layout[tile]["uv"],base.width)
            pixels=np.asarray(base.crop(uv),dtype=float)[:,:,:3]
            high=pixels.max(axis=2)
            sat=(high-pixels.min(axis=2))/np.maximum(1,high)
            core=sat[(sat>=lo)&(sat<=hi)]
            assert core.size>.42*sat.size and sat.max()<=hi+.008,(n,tile,core.size,sat.size,sat.max())
            density=min((uv[2]-uv[0])/layout[tile]["metres"][0],(uv[3]-uv[1])/layout[tile]["metres"][1])
            assert density>=256
            colors[tile]=dict(px_per_m=round(density,2),face_median_sat=round(float(np.median(core)),4))
        assert mask.crop(source_box(layout["YardSetts"]["uv"],mask.width)).getchannel("A").getextrema()[1]<=40
        for suffix in ("","_LOD1","_LOD2"):
            assert Image.open(out/n/f"{n}{suffix}_Emissive.png").convert("RGB").getextrema()==((0,0),)*3
        tile_stats[n]=colors
    return tile_stats

def finish():
    inventory()
    checks={}
    for zone,count in COUNTS.items():
        out=ROOT/f"import_{zone}"
        plans=list(make(zone))
        names={a["name"] for a in plans}
        m=read(out/"manifest.json")
        assert count==m["registrations"]==len(names)==len(m["assets"])
        window=read(out/"window-coverage.json")
        probe=read(out/"probe-results.json")
        audit=read(out/"audit.json")
        assert names==set(window)==set(probe)==set(audit)=={a["name"] for a in m["assets"]}
        assert len(list(out.glob("*/*.fbx")))==6*count
        for rel,digest in m["sha256"].items():
            assert sha256((out/rel).read_bytes()).hexdigest()==digest,rel
        for a in plans:
            name=a["name"]
            _,owner=atlas_owners(a)
            if name!=owner:
                p=out/name/"settings.json"
                links=read(p)["sharedAssets"]
                assert len(links)==15
                assert all((p.parent/f).is_file() and (p.parent/f).resolve().parent.name==owner for f in links.values())
        covered={n:[k for k in ("main","_LOD1") if window[n][k]["covered"]] for n in window}
        assert not any(covered.values()),{n:k for n,k in covered.items() if k}
        back=sum(v["backface_first_hits"] for a in probe.values() for lod in a.values() for v in lod.values())
        assert not back,(zone,back)
        density=[a["tris_per_m2"] for a in m["assets"]]
        coverage=[a["coverage"]["roofed_pct"] for a in m["assets"]]
        checks[zone]=dict(registrations=count,fbx=6*count,covered_panes=0,exterior_backfaces=back,
            max_triangles=[max(a["lods"][s]["triangles"] for a in m["assets"]) for s in ("main","_LOD1","_LOD2")],
            min_triangles_per_m2=min(density),median_triangles_per_m2=median(density),
            roofed_pct=[min(coverage),max(coverage)],atlas=material_check(out,m["texture_owners"]))
    write(ROOT/"qa-summary.json",checks)
    print("DELIVERY_CHECKS",json.dumps(checks),flush=True)

if __name__=="__main__":
    import sys
    (inventory if "--inventory" in sys.argv else finish)()
