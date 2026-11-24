"""Verify the four family changes and prepare the standalone replacement handoff."""
from pathlib import Path
import json
from hashlib import sha256
import publish_rebake as report
from rebake_specs import make,ROOT,INBOX

CHANGED={"VillaJeuDePaume","VillaMurHabite","VillaNormande","VillaMauresque"}

def main():
    old=INBOX/"2026-11-11_round12a"
    out=ROOT/"import_Z1B"
    plans=list(make("Z1B"))
    checks=report.verify("Z1B",plans)
    assert not checks["covered_windows"] and not checks["exterior_backface_hits"],checks
    before=report.read(old/"import_Z1B/manifest.json")
    after=report.read(out/"manifest.json")
    changed={a["name"] for a in plans if a["design"] in CHANGED}
    assert len(changed)==24
    assert before["sha256"].keys()==after["sha256"].keys()
    for rel,previous in before["sha256"].items():
        name=rel.split("/")[0]
        if not rel.endswith(".fbx") or name not in changed:
            assert previous==after["sha256"][rel],rel
    assert all(before["sha256"][f"{n}/{n}.fbx"]!=after["sha256"][f"{n}/{n}.fbx"] for n in changed)
    checks.update(batch="R12a2",redesigned_names=sorted(changed),approved_assets_byte_identical=63,atlas_maps_unchanged=True)
    report.write(ROOT/"qa-summary.json",checks)
    report.write(ROOT/"inventory-check.json",dict(same_name=sorted(a["name"] for a in plans if a["reimport"]),
                 additions=sorted(a["name"] for a in plans if not a["reimport"]),collisions=[]))
    after["batch"]="R12a2"
    report.write(out/"manifest.json",after)
    data=report.read(ROOT/"designs.json")
    data["batch"]="R12a2"
    report.write(ROOT/"designs.json",data)
    review=report.read(ROOT/"previews/Z1B-rebake-review.json")
    report.visual("Z1B",ROOT,review)
    (ROOT/"READ-ME-FIRST.md").write_text("""# R12a2 · Maisons Patriciennes

The complete 87-building estate package for Claude. Import the [whole Z1B folder](import_Z1B/) together so the shared maps resolve. The 63 approved registrations and all shared texture files are byte-identical to R12a. The remaining 24 registrations are the four revised families, with their existing names, lots and colourways.

- **Jeu de Paume** has a blind masonry base, high arched clerestory, brick piers and an overhanging 33° slate roof.
- **Mur Habité** puts inhabited rooms, an iron balcony and a gate into the continuous coped street wall. The house turns across the rear to form an L.
- **Normande** has cross-gables, bracketed eaves, modelled half-timbering and a mullioned veranda on a stone dwarf wall.
- **Mauresque** has re-entrant horseshoe arches, alternating cream and red voussoirs, glazed tile, crenellations and a broad tiled kiosk.

Stage this as the revised 87-building Z1B set. On import day use the [retirement list](RETIREMENT-LIST.md) with the game closed and preserve installed texture files. Run setup from [designs.json](designs.json).

[Day street](previews/Z1B-street-day.png) · [Night street](previews/Z1B-street-night.png) · [128 px sheet](previews/128px-sheet.png) · [Family close-ups](previews/family-closeups/) · [QA summary](qa-summary.json)

The file checks cover lot bounds, triangle budgets and window visibility. The three known small left-hand Manoir Français trim ties carry over from approved R12a. In-game review is pending.
""",encoding="utf8")
    print("R12A2_VERIFIED",checks,flush=True)

if __name__=="__main__":
    main()
