"""Build zone atlases and carry over the original workers' housing inscriptions."""
from pathlib import Path
import sys
from PIL import Image
from rebake_specs import INBOX,ROOT,make,read
from r12_atlas import MAPS
from round5_atlas import source_box

SLOTS=("VillaJeuDePaume","ImmeubleBowWindows","ImmeubleImprimeur","ImmeubleJardinHiver")
OLD=INBOX/"2026-11-11_round12"

def main(zone):
    out=ROOT/f"import_{zone}"
    plans=list(make(zone))
    layout=read(ROOT/"source/kit/atlas_layout.json")["lods"]
    manifest=read(OLD/f"import_{zone}/manifest.json")
    originals=manifest["texture_owners"]
    groups=sorted({a["atlas_owner"] for a in plans})
    for owner in groups:
        path=out/owner
        path.mkdir(parents=True,exist_ok=True)
        related=[a for a in plans if a["atlas_owner"]==owner]
        existing=related[0]["reimport"]
        base=originals[0] if existing else owner
        for suffix,cells in layout.items():
            tag="" if suffix=="main" else suffix
            for mode in MAPS:
                src=OLD/f"import_{zone}"/base/f"{base}{tag}_{mode}.png"
                with Image.open(src) as image:
                    dest=image.convert("RGBA")
                if mode in {"BaseColor","MaskMap","Normal"}:
                    from r12_atlas import water
                    rect=source_box(cells["CanalWater"]["uv"],dest.width)
                    dest.paste(water((rect[2]-rect[0],rect[3]-rect[1]),mode),rect[:2])
                if mode=="BaseColor" and existing and zone=="Z4":
                    source=INBOX/related[0]["source_batch"]
                    orig=source/related[0]["source_import"]
                    material=read(orig/"manifest.json")["texture_owner"]
                    old_cells=read(source/"source/kit/atlas_layout.json")["lods"][suffix]
                    with Image.open(orig/material/f"{material}{tag}_{mode}.png") as image:
                        for slot,a in {a["sign_index"]:a for a in related}.items():
                            key="Sign_"+a["design"]
                            if key not in old_cells:
                                continue
                            l,t,r,b=source_box(cells["Sign_"+SLOTS[slot]]["uv"],dest.width)
                            tile=image.crop(source_box(old_cells[key]["uv"],image.width))
                            dest.paste(tile.resize((r-l,b-t),Image.Resampling.LANCZOS),(l,t))
                dest.save(path/f"{owner}{tag}_{mode}.png",compress_level=2)
        print("ATLAS_READY",zone,owner,flush=True)

if __name__=="__main__":
    main(sys.argv[-1])
