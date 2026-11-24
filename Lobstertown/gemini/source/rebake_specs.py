"""Round 12 zone-swap roster, using the installed names and their original designs."""
from pathlib import Path
import json
import os
import re
from r12_specs import make as new_plans, atlas_owners as new_owner, prop

ROOT=Path(__file__).resolve().parents[1]
INBOX=ROOT.parent
GAME=Path(os.environ["USERPROFILE"])/"AppData/LocalLow/Colossal Order/Cities Skylines II/ImportedData"
DELIVERIES={"Z1B":("a",39,72),"Z2B":("b",78,18),"Z4":("c",48,36)}
COUNTS={z:old+new for z,(_,old,new) in DELIVERIES.items()}
SOURCES={
 "Z1B":(("2026-11-06_chateau-villas","bake"),("2026-11-06_villas-and-infill","bake")),
 "Z2B":(("2026-11-07_round2-batch2b","bake"),),
 "Z4":(("2026-11-09_round9","import_Z4"),),
}
EXCLUDE={"HotelParticulier","ManoirFederal","VillaJumelle","RapportBriqueImmeuble"}
NAME=re.compile(r"(NA_PdD\w+_L\d_\d+x\d+)_[0-9a-f]{32}\.Prefab$",re.I)

def read(path):
    return json.loads(path.read_text(encoding="utf8"))

def installed():
    return {m[1] for p in GAME.rglob("*.Prefab") if (m:=NAME.fullmatch(p.name))}

def vegetation(a):
    w,d=(v*8 for v in a["lot"])
    estate=a["zone_key"]=="Z1B"
    rear=[prop("tree",2.55,d-3.15,2.4,2.4,4.4),prop("hedge",w*.55,d-1.1,w*.54,.54,.72)]
    if not estate:
        return rear
    gates=[ent.get("gate_lot_m",ent["position_lot_m"])[0]
           for ent in a.get("active_entrances",[]) if ent.get("street_path",True) and "position_lot_m" in ent]
    if a["design"]=="VillaMurHabite":
        gates=[12.1]
    rows=rear+[prop("tree",w-2.25,d-5.2,2.45,2.45,4.6),prop("tree",w*.46,d-4.1,2.1,2.1,3.8)]
    left=.60
    for gate in sorted(gates or [w*.5]):
        right=min(w-.60,gate-1.26)
        if right-left>.90:
            rows.append(prop("hedge",(left+right)/2,1.23,right-left,.49,.78))
        left=max(left,gate+1.26)
    if w-.60-left>.90:
        right=w-.60
        rows.append(prop("hedge",(left+right)/2,1.23,right-left,.49,.78))
    while len(rows)<6:
        rows.append(prop("hedge",.65 if len(rows)%2==0 else w-.65,d-6.4,.48,2.2,.65))
    return rows

def earlier(zone):
    for batch,sub in SOURCES[zone]:
        source=INBOX/batch
        for old in read(source/"designs.json")["designs"]:
            if old.get("zone_key")!=zone or old["design"] in EXCLUDE:
                continue
            a=dict(old)
            title=a.get("display_title") or a.get("title") or re.sub(r"(?<=[a-z])(?=[A-Z])"," ",a["design"])
            a.update(display_title=title,inscription=a.get("inscription",title.upper()),
                     source_batch=batch,source_import=sub,reimport=True,budget=[45000,9000,1000])
            a.setdefault("lineage",dict(dominant="New France",guests=[],signature=a.get("story",title)))
            if zone=="Z4":
                a.pop("households",None)
            yield a

def assign(zone):
    legacy=list(earlier(zone))
    size=4 if zone=="Z4" else 3
    families=list(dict.fromkeys(a["design"] for a in legacy))
    groups=[families[i:i+size] for i in range(0,len(families),size)]
    if zone=="Z2B":
        groups=[families[:4]]+[families[i:i+3] for i in range(4,len(families),3)]
    for j,group in enumerate(groups,1):
        owner=next(a["name"] for a in legacy if a["design"]==group[0])
        for a in legacy:
            if a["design"] in group:
                yield dict(a,atlas_owner=owner,atlas_group=f"existing-{j}",sign_index=group.index(a["design"]),props=[])
    for a in new_plans(zone):
        group,owner=new_owner(a)
        yield dict(a,atlas_group=f"new-{group}",atlas_owner=owner,reimport=False,props=[],budget=[45000,9000,1000])

def make(zone=None):
    for key,(_,old,new) in DELIVERIES.items():
        if zone is not None and key!=zone:
            continue
        a=list(assign(key))
        assert len(a)==old+new and sum(x["reimport"] for x in a)==old,(key,len(a),old,new)
        yield from a

def atlas_owners(a):
    return a["atlas_group"],a["atlas_owner"]


# ---- Villa sur l'Eau was retired by the author on 2026-11-11 (water); the second pass must not bring it back ----
RETIRED_R24={"VillaSurLEau"}
_make_r24=make
def make(zone=None):
    yield from (a for a in _make_r24(zone) if a["design"] not in RETIRED_R24)
COUNTS={z:n-(6 if z=="Z1B" else 0) for z,n in COUNTS.items()}
