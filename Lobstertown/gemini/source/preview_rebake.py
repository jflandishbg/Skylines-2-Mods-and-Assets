"""Review the complete zone-swap packages and matched original families."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from preview_r12 import (ROOT,INBOX,PRE,REFS,HOUSE,previous,profile,closeup,street)
from rebake_specs import make,atlas_owners,DELIVERIES

def new(a):
    return dict(a,folder=ROOT/f'import_{a["zone_key"]}',owner=atlas_owners(a)[1])

def representatives(plans):
    families=list(dict.fromkeys(a["design"] for a in plans))
    out=[]
    for i,f in enumerate(families):
        variants=[a for a in plans if a["design"]==f]
        color="ABC"[i%3]
        entry=next((a for a in variants if a["colourway"]==color),variants[0])
        out.append(new(entry))
    return out

def main(zone):
    p,refs=REFS[zone]
    comparison=[previous(INBOX/p,n) for n in refs]
    for a in comparison:
        a["design"]+="-original"
    plans=list(make(zone))
    all_styles=representatives(plans)
    for a in all_styles+comparison:
        profile(a)
    for a in all_styles:
        closeup(a)
    if zone=="Z1B" or not (PRE/"close-R11b-reference.png").exists():
        closeup(previous(INBOX/"2026-11-10_round11b/import_Z1C",HOUSE),house=True)
    fresh=[a for a in all_styles if not a["reimport"]]
    picks=([fresh[i] for i in (0,1,2,3,4,6)] if zone=="Z1B" else
           fresh+[new(next(a for a in plans if a["design"]==f["design"] and a["lot"][1]==5 and a["colourway"]=="C")) for f in fresh]
           if zone=="Z2B" else [fresh[i] for i in (0,1,3,5,8,9)])
    old=[new(next(a for a in plans if a["name"]==n)) for n in refs]
    lineup=[picks[0],old[0],*picks[1:4],old[1],*picks[4:]]
    for mode in ("day","night"):
        street(zone,lineup,mode)
    (PRE/(zone+"-rebake-review.json")).write_text(json.dumps(
        dict(families=[(a["design"],a["display_title"],a["reimport"]) for a in all_styles],
             original=[(a["design"],a["display_title"]) for a in comparison],lineup=[a["name"] for a in lineup]),
        ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("R12_VISUALS",zone,len(all_styles),flush=True)

if __name__=="__main__":
    main(sys.argv[-1])
