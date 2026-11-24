"""Gemini buildings: one script per building in gemini/scripts/<name>.py. Which ones to bake comes from GEMINI_NAMES."""
import os, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
NAME = re.compile(r"NA_(?:PdD|LT)([A-Za-z]+?)(B|C)?(Left|Right)?_L1_(\d)x(\d)$")

def entry(path):
    n = path.stem
    m = NAME.fullmatch(n)
    if not m: raise ValueError(f"{path.name}: the file name must be the building name, like NA_PdDMaisonDuQuai_L1_1x3.py")
    text = path.read_text(encoding="utf8")
    zone = re.search(r'^ZONE\s*=\s*["\'](Z\w+)["\']', text, re.M)
    hh = re.search(r'^HOUSEHOLDS\s*=\s*(\d+)', text, re.M)
    product = re.search(r'^PRODUCT\s*=\s*["\'](.+?)["\']', text, re.M)   # green industry (ZI1): what it may make
    if not zone: raise ValueError(f"{path.name}: missing a line like  ZONE = \"Z1A\"")
    w, d = int(m[4]), int(m[5])
    pw = re.search(r"^PARTY_WALLS\s*=\s*\(([^)]*)\)", text, re.M)
    party = {x.strip(" '\"").lower() for x in pw[1].split(",") if x.strip(" '\"")} if pw else set()
    skip = [s for s, k in (((0, 1), "left"), ((0, -1), "right")) if k in party]
    # Lobstertown: the whole batch shares one texture set, owned by its first building (Toronto-style, ~70 MB)
    batch = [x for x in os.environ.get("GEMINI_NAMES", "").split(",") if x.startswith("NA_LT")]
    owner = batch[0] if n.startswith("NA_LT") and batch else n
    return dict(name=n, design=m[1], display_title=m[1], inscription=m[1].upper(), zone_key=zone[1], lot=[w, d], level=1,
                access="Front", colourway=m[2] or "A", wall_tile="Brick085", roof_tile="SlateDark",
                budget=[160000, 24000, 3000] if zone[1] in ("ZP3", "ZC2", "ZH2") else [45000, 9000, 1000], props=[], native_surfaces=[], households=int(hh[1]) if hh else 1,
                reimport=False, gemini=True, gemini_script=str(path), atlas_owner=owner, atlas_group="gemini", sign_index=0,
                lineage=dict(dominant="New France", guests=[], signature="Designed by Gemini"), party_skip=skip,
                product=product[1] if product else None)

def make(zone=None):
    names = [x for x in os.environ.get("GEMINI_NAMES", "").split(",") if x]
    for n in names:
        yield entry(ROOT / "scripts" / (n + ".py"))

COUNTS = type("Counts", (), {"__getitem__": lambda self, z: len(list(make(z)))})()

def atlas_owners(a):
    return a["atlas_group"], a["atlas_owner"]
