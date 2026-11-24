"""Verify each zone and publish its standalone raw imports and handoff."""
from hashlib import sha256
import json
from pathlib import Path
import shutil
from statistics import median
import sys

from PIL import Image
from assemble_r12 import board, shape, font, INK, image, ZONES
from rebake_specs import ROOT, INBOX, DELIVERIES, make, read, installed
import assemble_r12 as sheets

PRE=ROOT/"previews"

def write(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf8")

def visual(zone,dest,review):
    out=dest/"previews"
    out.mkdir(exist_ok=True)
    cards=[(design,title+(" · rebake" if old else "")) for design,title,old in review["families"]]
    cards.extend((design,title+" · original") for design,title in review["original"])
    im,d=board(1380,94+170*((len(cards)+3)//4),ZONES[zone],
              "Same scale · front and side · two original exports included")
    for i,(key,label) in enumerate(cards):
        x,y=10+i%4*345,90+i//4*170
        d.text((x,y),label,font=font(14,True),fill=INK)
        for j,v in enumerate(("front","side")):
            im.paste(shape(key,v,128),(x+130*j,y+22))
    im.save(out/f"{zone}-silhouettes.png")
    all_styles=review["families"]
    im,d=board(1340,100+170*((len(all_styles)+4)//5),f"Round 12 at 128 pixels · {zone}",
               "Front and side silhouettes in 128 × 128 pixel tiles")
    for i,(key,label,_) in enumerate(all_styles):
        x,y=10+i%5*266,89+i//5*170
        d.text((x,y),label,font=font(13,True),fill=INK)
        for j,v in enumerate(("front","side")):
            im.paste(shape(key,v,128),(x+j*130,y+25))
    im.save(out/"128px-sheet.png")
    for mode in ("day","night"):
        if out!=PRE:shutil.copy2(PRE/f"{zone}-street-{mode}.png",out)
    sheets.OUT=out/"family-closeups"
    sheets.OUT.mkdir(exist_ok=True)
    house=image("close-R11b-reference").crop((200,35,640,585))
    for key,label,_ in all_styles:
        sheets.closeup(key,label,house)
    write(out/"street-lineup.json",review["lineup"])

def verify(zone,plans):
    manifest=read(ROOT/f"import_{zone}/manifest.json")
    source=ROOT/f"import_{zone}"
    n=len(plans)
    installed_names=installed()
    prior={a["name"] for a in plans if a["reimport"]}
    fresh={a["name"] for a in plans if not a["reimport"]}
    assert prior<=installed_names,sorted(prior-installed_names)
    assert not fresh&installed_names,sorted(fresh&installed_names)
    assert manifest["registrations"]==n and len(list(source.glob("*/*.fbx")))==6*n
    for rel,digest in manifest["sha256"].items():
        assert sha256((source/rel).read_bytes()).hexdigest()==digest,rel
    for a in plans:
        assert len(a["props"])>=(6 if zone=="Z1B" else 2)
        assert {"tree","hedge"}<={p["kind"] for p in a["props"]}
        assert (zone!="Z4")==("households" in a),a["name"]
        owner=a["atlas_owner"]
        if a["name"]!=owner:
            path=source/a["name"]/"settings.json"
            links=read(path)["sharedAssets"]
            assert len(links)==15 and all((path.parent/ref).is_file() and (path.parent/ref).resolve().parent.name==owner for ref in links.values())
    windows=read(source/"window-coverage.json")
    audit=read(source/"audit.json")
    probe=read(source/"probe-results.json")
    assert set(windows)==set(audit)==set(probe)==prior|fresh
    covered={n:[s for s in ("main","_LOD1") if a[s]["covered"]] for n,a in windows.items() if a["main"]["covered"] or a["_LOD1"]["covered"]}
    back={n:sum(k["backface_first_hits"] for record in a.values() for k in record.values())
          for n,a in probe.items()}
    back={n:v for n,v in back.items() if v}
    plant={"RoofGreen","Ivy"}
    assert not any(plant&set(k["material_tiles"]) for a in audit.values() for k in a.values())
    for owner in manifest["texture_owners"]:
        for suffix in ("","_LOD1","_LOD2"):
            with Image.open(source/owner/f"{owner}{suffix}_Emissive.png") as e:
                assert e.convert("RGB").getextrema()==((0,0),)*3
    density=[a["tris_per_m2"] for a in manifest["assets"]]
    coverage=[a["coverage"]["roofed_pct"] for a in manifest["assets"] if not a["reimport"]]
    assert min(density)>=8
    return dict(registrations=n,same_name=len(prior),new=len(fresh),fbxs=6*n,
                triangles=[max(a["lods"][s]["triangles"] for a in manifest["assets"]) for s in ("main","_LOD1","_LOD2")],
                density_min=min(density),density_median=round(median(density),3),new_roofed_pct=[min(coverage),max(coverage)],
                covered_windows=covered,exterior_backface_hits=back,
                minor_trim_ties={a["name"]:{k:v["minor_trim_ties"] for k,v in a["lods"].items() if v.get("minor_trim_ties")}
                                 for a in manifest["assets"] if any(v.get("minor_trim_ties") for v in a["lods"].values())})

def main(zone):
    plans=list(make(zone))
    letter,retained,fresh=DELIVERIES[zone]
    title=f"R12{letter}"
    dest=INBOX/f"2026-11-11_round12{letter}"
    checks=verify(zone,plans)
    print("VERIFY",zone,json.dumps(checks),flush=True)
    assert not checks["covered_windows"],checks["covered_windows"]
    assert not checks["exterior_backface_hits"],checks["exterior_backface_hits"]
    review=read(PRE/f"{zone}-rebake-review.json")
    dest.mkdir(exist_ok=True)
    shutil.copytree(ROOT/f"import_{zone}",dest/f"import_{zone}",dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("progress.json"))
    write(dest/"designs.json",dict(project="New France",batch=title,designs=plans))
    write(dest/"qa-summary.json",checks)
    retirement=(INBOX/"2026-11-11_round12"/"RETIREMENT-LIST.md").read_text(encoding="utf8").splitlines()
    rows=[line for line in retirement if line.startswith(f"| {zone} |")]
    note=["# "+title+" retirement list","","Use these installed names for the retirement plan on import day. Keep all installed textures.",""]
    if rows:
        note+=["| Zone | Installed registration | Surviving dependents before the swap |","| --- | --- | --- |",*rows]
    else:
        note+=["There are no retirements in Z4."]
    (dest/"RETIREMENT-LIST.md").write_text("\n".join(note)+"\n",encoding="utf8")
    visual(zone,dest,review)
    text=f"""# {title} · {ZONES[zone]}

{checks['registrations']} Level 1 registrations: {retained} same-name rebakes and {fresh} new assets. This zone delivery replaces the matching portion of the original Round 12 delivery.

## Claude’s import sequence

1. Stage [import_{zone}](import_{zone}/) as `1_READY_{title}_{zone}_{checks['registrations']}`. Keep each atlas owner with its dependents.
2. With the game closed, regenerate the [retirement plan](RETIREMENT-LIST.md) and recycle the same-name old models and the listed retirees. Keep all installed textures.
3. the author imports the zone set. Run setup with the household, access, and native prop records in [designs.json](designs.json).

## Review

[Silhouette comparison](previews/{zone}-silhouettes.png) · [128 px sheet](previews/128px-sheet.png) · [Day street](previews/{zone}-street-day.png) · [Night street](previews/{zone}-street-night.png) · [Family close-ups](previews/family-closeups/)

The street shows six new buildings and two retained families. The silhouettes include the original exports of those two retained families. Close-ups include the approved R11b Maison de la Serre for colour. Preview greenery indicates native prop placement.

## File checks

[QA summary](qa-summary.json) · [Manifest](import_{zone}/manifest.json) · [Probe](import_{zone}/probe-results.json) · [Material audit](import_{zone}/audit.json) · [Window coverage](import_{zone}/window-coverage.json)

{checks['fbxs']} FBXs passed file-level reimport. The minimum projected-envelope density is {checks['density_min']:.2f} triangles per square metre and the median is {checks['density_median']:.2f}. The window probe found zero covered panes at LOD0 and LOD1. No first-hit backfaces were found. Final appearance and behaviour still need in-game review.
"""
    if checks["minor_trim_ties"]:
        text+="\nThe QA summary lists any remaining small coplanar trim intersections in retained models.\n"
    text+="\nThe retained buildings preserve their original architectural massing. Secondary openings and distance proxies retain source joinery where deepening would cut through the old wall or exceed the mesh budget.\n"
    (dest/"READ-ME-FIRST.md").write_text(text,encoding="utf8")
    print("PUBLISHED",dest,flush=True)

if __name__=="__main__":
    main(sys.argv[-1])
