# New France - set up every imported New France building in one go.
# Rebuilt from the Keystone setup (whose file format handling the game accepted), cut down to the level-1 rules.
#
# Run AFTER importing in the editor and making the zones, with the game CLOSED:
#     python newfrance_setup.py            (add --dry-run to only report)
#
# For each imported NA_NewHolland* building it writes, straight into the imported prefab files:
#   - lot width and depth, from the name (..._2x3 -> 2 x 3)
#   - SpawnableBuilding: level 1, and the zone for its type (ZONE_OF below, by the zone names made in the editor)
#   - access type: ...RightCorner... -> RightCorner, ...LeftCorner... -> LeftCorner, everything else Front
#   - households for the residential types (HOUSEHOLDS below); shops take theirs from the zone
# Every file it changes is copied to <file>.bak first. If a zone doesn't exist yet, that building only gets its lot
# and access set, and the script says which zones are missing.
import os, re, sys, json, shutil, math, hashlib, struct

ROOT = os.path.join(os.environ["USERPROFILE"], "AppData", "LocalLow", "Colossal Order", "Cities Skylines II", "ImportedData")
DRY = "--dry-run" in sys.argv

# design -> zone name as made in the editor; first match on the design name wins
# design-name keyword -> zone (by the zone's internal prefab name, which the author sets in the editor; the folder may differ)
ZONE_OF = [("Main", "Napoleon Mixed Main Street"), ("Plex", "Napoleon Row Homes Medium"), ("Row", "Napoleon Row Homes Medium"),
           ("Cottage", "Napoleon Residential Low"), ("House", "Napoleon Residential Low"),
           ("Twin", "Napoleon Residential Low"), ("Double", "Napoleon Residential Low"),
           ("Shop", "Napoleon Commercial Low"), ("Store", "Napoleon Commercial Low")]
# households per building, for residential designs (a twin is two families); anything not listed gets 1
HOUSEHOLDS = {"Triplex": 3, "Twin": 2, "Double": 2, "Plex": 2}   # plex = two stacked flats; Triplex checked first
Z4_HOUSEHOLDS = {3: 12, 4: 14, 5: 16}                            # Z4 Immeubles de la Riviere, by lot depth (2-wide, 4-5 storeys + garret)
# exact zone and households per design, from GPT's design files (rounds 4 and 5 onward); B/C colourways share their A's
DESIGNS = {}
PROPS = {}                                                       # registration name -> (lot, GPT prop list)
# the author, 2026-11-11: buildings stand on their own and Placemaker does the landscaping, so setup adds NO garden props
# (trees, hedges, fences, lamps) to zoned buildings. Props already placed by earlier runs are taken off. True = old way.
GARDEN_PROPS = False
ACCESS_OF = {}                                                   # registration name / design -> LeftCorner|RightCorner (designs.json)
# Z10 Quai Industriel is GREEN industry (the author, 2026-11-10: game industry "emits more smoke than a forest fire").
# A company moves in only if the building's m_AllowedManufactured has its product (decomp PropertyUtils), and pollution
# comes from the product, so every Z10 building gets its own clean product list. Numbers = Game.Economy.ResourceInEditor
# (dumped from Game.dll; verified against the zone's own 18-item list). The dirty ones never appear here: Petrochemicals 17,
# Plastics 19, Metals 20, Steel 27, Minerals 28, Concrete 29, Chemicals 31. An empty m_AllowedInput means "all inputs".
HH_OF = {}                                                       # registration name -> households (by lot size: Cottage Flats)
PRODUCT_OF = {}                                                  # registration name -> product label from designs.json
CLEAN_PRODUCTS = {"Textiles": [34], "Machinery": [30], "Furniture": [10], "Paper": [9],
                  "Food and convenience food": [4, 3], "Food": [4], "Convenience food": [3], "Electronics": [21],
                  "Beverages": [33], "Pharmaceuticals": [32], "Timber": [8], "Vehicles": [11]}
Z10_SPACE_MULTIPLIER = 8                                         # the Quai Industriel zone's own ZoneProperties value
# Paris on the Delaware zone keys (GPT's designs.json) -> the zone's name as the author makes it in the editor
ZONE_KEY = {"ZL1": "Lobstertown Low Residential",     # Lobstertown L1 Shore Rows; the author made it as Residential Low (2026-11-14)
            "ZM1": "Lobstertown Mixed Main Street",   # Main Street shops + flats; a vanilla Mixed Housing clone. Keep "Mixed" in the
                                                      # name: setup gives a building its zone's goods to sell only when it says Mixed
            "ZC1": "Lobstertown Commercial Waterfront",  # Boardwalk Shops; the author's Commercial Low (Waterfront) clone, repurposed
            "ZC2": "Lobstertown Commercial Boardwalk",   # Boardwalk Palaces; a Commercial High clone ("Commercial" in the name: no flats)
            "ZP3": "Lobstertown Grand Hotels",        # shingle beachfront towers, 40-70 households; a Residential High clone
            "ZP2": "Lobstertown Cottage Flats",       # Atlantic City boarding-house flats, 6-10 households; a Residential Medium clone
            "ZI1": "Lobstertown Industrial Cannery Row",   # canneries, ropewalks, boat shops; a vanilla Industrial Manufacturing
                                                      # clone. Green industry like Z10: one clean product per building
            "ZH1": "Lobstertown Harbour Hill",   # Harbour Hill tenements, row and corner blocks; a Residential Medium clone
            "ZP4": "Lobstertown Coastal Inns",   # shingle summer inns (replaces Motor Courts, 2026-11-18); a Residential Medium clone
            "ZO1": "Lobstertown Office Exchange Row",   # Beaux-Arts banks and offices; an Office Low clone (no flats)
            "ZP1": "Lobstertown Prestige Cottages",   # Bar Harbor summer cottages, 1 household; a Residential Low clone (2026-11-15)
            "ZH2": "Lobstertown Beacon Towers",       # 1920s coastal setback Art Deco brick towers, 26-58 hh; Residential High clone
            "ZL2": "Lobstertown Shipyard Bungalows",  # 1910s-1930s working-class Craftsman bungalows & Foursquares, 1 hh; Residential Low clone
            "ZR1": "Lobstertown Hydrostone Courts",   # 1918 Halifax Hydrostone crushed-stone & garden-court flats, 18-46 hh; Residential Low Rent clone
            "Z1A": "Napoleon Maisons Populaires", "Z1B": "Napoleon Maisons Patriciennes",
            "Z1C": "Napoleon Maisons de Ville",   # Z1C: 2-wide compact townhouses (2x2, 2x3), own zone so 1-wide homes still grow
            # Full register: GPT_INBOX\ZONES.md (names = the zone's internal name in the editor, line breaks ignored)
            "Z2": "Napoleon Maisons en Rangee", "Z2B": "Napoleon Immeubles de Rapport",
            "Z4": "Napoleon Immeubles de la Riviere", "Z5": "Napoleon Rue Principale Mixte",
            "Z3": "Napoleon Appartements Haussmann", "Z6": "Napoleon Commerces Populaires",
            "Z7": "Napoleon Galeries des Luminaires", "Z8": "Napoleon Compagnie des Indes",
            "Z9": "Napoleon Tour des Deux-Fleuves", "Z10": "Napoleon Quai Industriel"}
# the author renamed these zones in the editor on 2026-11-07; older design files and ZONE_OF still use the old names
RENAMED = {"Napoleon Residential Low": "Napoleon Maisons Populaires", "Napoleon Mixed Main Street": "Napoleon Rue Principale Mixte",
           "Napoleon Commercial Low": "Napoleon Commerces Populaires", "Napoleon Row Homes Medium": "Napoleon Maisons en Rangee"}
_inbox = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "GPT_INBOX")
def _round_order(walk_item):                                      # later delivery overrides earlier: date prefix, then the
    _top = os.path.relpath(walk_item[0], _inbox).split(os.sep)[0]     # round folder's creation time (same-day rounds are not
    _tp = os.path.join(_inbox, _top)                                  # alphabetical: chateau-townhouses revises villas-and-infill)
    return (_top[:10], os.path.getctime(_tp) if os.path.isdir(_tp) else 0, walk_item[0])
for _dp, _dn, _fs in sorted(os.walk(_inbox), key=_round_order):
    _dn.sort()
    for _f in sorted(_fs):
        if _f.endswith("-designs.json"):
            for _a in json.load(open(os.path.join(_dp, _f), encoding="utf-8")).get("assets", []):
                DESIGNS[_a["design"]] = (_a.get("zone"), _a.get("households"))
        elif _f == "designs.json":                                  # square-one format: zone keys
            for _a in json.load(open(os.path.join(_dp, _f), encoding="utf-8")).get("designs", []):
                if "zone_key" in _a:
                    _z = (ZONE_KEY.get(_a["zone_key"], _a["zone_key"]), _a.get("households"))
                    if _a.get("name") and _a.get("households"):
                        HH_OF[_a["name"]] = _a["households"]
                    DESIGNS[_a["design"]] = _z
                    _m = re.match(r"NA_(?:NewFrance|PdD|LT)([A-Za-z]+?)_L1_", _a.get("name", ""))
                    if _m:                                          # also key by the registration's own name, so
                        DESIGNS[_m.group(1)] = _z                   # colourway + hand forms (…BLeft) resolve too
                if _a.get("product") and _a.get("name"):        # Z10 green industry: what each building may make
                    PRODUCT_OF[_a["name"]] = _a["product"]
                if _a.get("access") in ("LeftCorner", "RightCorner"):     # corner access given as data, not in the name
                    ACCESS_OF[_a.get("name", "")] = ACCESS_OF[_a["design"]] = _a["access"]
                if _a.get("props") and _a.get("name"):
                    PROPS[_a["name"]] = (_a["lot"], _a["props"])
                    PROPS[re.sub(r"_L1_\d+x\d+$", "", _a["name"])] = (_a["lot"], _a["props"])   # service import name

def base_design(design):
    if design not in DESIGNS and design[-1:] in ("B", "C") and design[:-1] in DESIGNS:
        return design[:-1]
    return design
ACCESS = {"Front": 0, "LeftCorner": 1, "RightCorner": 2}          # BuildingAccessType

# ---------------------------------------------------------------- the game's JSON dialect <-> JSON (from keystone_setup)
def load(path):
    s = open(path, encoding="utf-8").read()
    s = re.sub(r'\$fstrref:"([^"]*)"', r'"@@FSTR@@\1"', s)
    s = re.sub(r'\{\s*"\$type":\s*("[^"]*"|\d+),\s*((?:-?[\d.eE+]+\s*,\s*)*-?[\d.eE+]+)\s*\}',
               lambda m: '{"$type": %s, "@@VALS@@": [%s]}' % (m.group(1), m.group(2)), s)
    doc = json.loads(s)
    names = {}                                                  # every "N|Type" in the file as loaded, so a type
    def scan(o):                                                # declared in a replaced component can be re-declared
        if isinstance(o, dict):
            t = o.get("$type")
            if isinstance(t, str) and "|" in t:
                n, name = t.split("|", 1); names.setdefault(int(n), name)
            for v in o.values(): scan(v)
        elif isinstance(o, list):
            for v in o: scan(v)
    scan(doc)
    doc["@@TYPENAMES@@"] = names
    return doc

def renumber(doc):
    """$type indices and $ids in document order, as the editor writes them"""
    tmap, ids = {}, [0]
    names = doc.pop("@@TYPENAMES@@", {})
    def walk(o):
        if isinstance(o, dict):
            if "$id" in o: o["$id"] = ids[0]; ids[0] += 1
            t = o.get("$type")
            if isinstance(t, str) and "|" in t:
                old, name = t.split("|", 1)
                if int(old) in tmap:                            # already declared earlier in the file: refer to it
                    o["$type"] = tmap[int(old)]
                else:
                    tmap[int(old)] = len(tmap); o["$type"] = f"{tmap[int(old)]}|{name}"
            elif isinstance(t, int):
                if t in tmap:
                    o["$type"] = tmap[t]
                else:                                           # its declaration went with a replaced component
                    tmap[t] = len(tmap); o["$type"] = f"{tmap[t]}|{names[t]}"
            for k, v in o.items():
                if k not in ("$type", "$id"): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(doc)

def save(path, doc):
    renumber(doc)
    s = json.dumps(doc, indent=4, ensure_ascii=False)
    s = re.sub(r'"@@FSTR@@([^"]*)"', r'$fstrref:"\1"', s)
    s = re.sub(r'"\$type": ("[^"]*"|\d+),\s*"@@VALS@@": \[\s*([^\]]*?)\s*\]',
               lambda m: '"$type": %s, %s' % (m.group(1), ", ".join(x.strip() for x in m.group(2).split(","))), s)
    if DRY: return
    if not os.path.exists(path + ".bak"):                          # keep the importer's original, not a re-run
        shutil.copyfile(path, path + ".bak")
    open(path, "w", encoding="utf-8", newline="\r\n").write(s)

def max_type(doc):
    best = [0]
    def walk(o):
        if isinstance(o, dict):
            t = o.get("$type")
            if isinstance(t, str) and "|" in t: best[0] = max(best[0], int(t.split("|")[0]))
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(doc); return best[0]

class Types:
    """fresh $type numbers for new objects (renumber() puts everything in order afterwards)"""
    def __init__(self, doc):
        self.n = max_type(doc) + 1
        self.existing = {nm: n for n, nm in doc.get("@@TYPENAMES@@", {}).items()}   # types the file already declares
        self.seen = {}
    def __call__(self, name):
        if name in self.existing: return f"{self.existing[name]}|{name}"   # same old number; renumber() de-duplicates
        if name in self.seen: return self.seen[name]
        self.seen[name] = self.n; self.n += 1
        return f"{self.seen[name]}|{name}"

def set_component(doc, comp):
    lst = doc["components"]["$rcontent"]
    lst[:] = [c for c in lst if c.get("name") != comp["name"]] + [comp]
    doc["components"]["$rlength"] = len(lst)


# ---------------------------------------------------------------- garden props (fences, hedges, trees) from GPT's lists
# Vanilla prefab IDs, decoded from the game's own PrefabsMap (resources.assets) into vanilla_prefab_guids.json.
_G = {}
for _g, _n in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "vanilla_prefab_guids.json"), encoding="utf-8")).items():
    if _n: _G.setdefault(_n, _g)
# Fence pieces are 4 m long ("Short" = 2 m), placed by their centre; measured from how Toronto Townhouses lays them.
FRONT_FENCE = ("NA_FenceResidentialPieceLow03", "NA_FenceResidentialPieceLowShort03")    # low front fence
BACK_FENCE = ("NA_FenceResidentialPieceHigh03", "NA_FenceResidentialPieceHighShort03")   # side and rear fences
HEDGE_BUSH = ("GreenBushCity01", "GreenBushCity02")              # a clipped hedge = a row of city bushes, 1 m apart
TREES = ("NA_LindenTree01", "NA_LondonPlaneTree01", "OakTree01", "NA_HickoryTree01")
BEDS = ("Flowerbed01", "Flowerbed02")
ACROSS = (0, 0.7071068, 0, 0.7071068)                            # a piece running across the lot (along x)
ALONG = (0, 0, 0, 1)                                             # a piece running front to back

def _local(X, Y, lot):
    """GPT lot metres (front-left origin, +X right seen from the street, +Y to the rear) -> building local (front = +z)"""
    W, D = lot[0] * 8.0, lot[1] * 8.0
    return round(W / 2 - X, 3), round(D / 2 - Y, 3)

def _segments(lo, hi, gaps):
    segs = [(lo, hi)]
    for g0, g1 in sorted(gaps or []):
        segs = [p for a, b in segs for p in ([(a, b)] if g1 <= a or g0 >= b else [(a, g0), (g1, b)]) if p[1] - p[0] > 0.05]
    return segs

def _fence(run_lo, run_hi, fixed, across, pieces, gaps):
    """fill a straight run with 4 m pieces and 2 m pieces at the end; returns (prefab, X, Y, rotation)"""
    out = []
    for a, b in _segments(run_lo, run_hi, gaps):
        L, t = b - a, a
        if L < 0.8: continue
        while b - t >= 4: out.append((pieces[0], t + 2)); t += 4
        while b - t > 0.6:                                       # the last metres: 2 m pieces, the final one flush with the end
            c = min(t + 1, b - 1) if L >= 2 else (a + b) / 2
            out.append((pieces[1], c)); t += 2
    return [(n, c, fixed, ACROSS) if across else (n, fixed, c, ALONG) for n, c in out]

def _bushes(run_lo, run_hi, fixed, across, gaps):
    out, k = [], 0
    for a, b in _segments(run_lo, run_hi, gaps):
        n = max(1, int(round((b - a) / 1.0)))
        for i in range(n):
            c = a + (b - a) * (i + .5) / n; yaw = ((k * 37) % 360) * math.pi / 180; k += 1
            rot = (0, round(math.sin(yaw / 2), 6), 0, round(math.cos(yaw / 2), 6))
            out.append((HEDGE_BUSH[k % 2], c, fixed, rot) if across else (HEDGE_BUSH[k % 2], fixed, c, rot))
    return out

def garden_objects(name, lot, props):
    """GPT's props -> [(vanilla prefab, x, z, rotation)] in building space; unknown kinds are reported, not guessed"""
    placed, skipped = [], []
    h = int(hashlib.md5(name.encode()).hexdigest(), 16)
    for p in props:
        kind = p["kind"].lower(); X, Y, _ = p["position_lot_m"]; sx, sy = p["size_m"][0], p["size_m"][1]
        across = sx >= sy; half = (sx if across else sy) / 2
        lo, hi, fixed = ((X - half, X + half, Y) if across else (Y - half, Y + half, X))
        gaps = p.get("gaps_lot_x_m") if across else p.get("gaps_lot_y_m")
        if "lamp" in kind:                                                # before "tree": "sTREEt lamp"
            items = [("StreetlightSingle01", X, Y, ALONG)]
        elif "flag" in kind:
            items = [("FlagPole01", X, Y, ALONG)]
        elif "bollard" in kind:
            items = [("Bollard01", X, Y, ALONG)]
        elif "fountain" in kind:
            items = [("LargeFountain01", X, Y, ALONG)]
        elif "tree" in kind:
            items = [(TREES[h % len(TREES)], X, Y, (0, round(math.sin(h % 360 * math.pi / 360), 6), 0, round(math.cos(h % 360 * math.pi / 360), 6)))]
        elif "hedge" in kind:
            items = _bushes(lo, hi, fixed, across, gaps)
        elif "fence" in kind or "gate" in kind:
            items = _fence(lo, hi, fixed, across, FRONT_FENCE if ("front" in kind or "iron" in kind) else BACK_FENCE, gaps)
        elif "flower" in kind or "bed" in kind:
            items = [(BEDS[h % 2], X, Y, ACROSS if across else ALONG)]
        elif "urn" in kind.split() or "planter" in kind:               # no vanilla stone urn: nearest is a flower pot
            items = [("FlowerPot01", X, Y, ALONG)]
        elif "cafe table" in kind or "café table" in kind:              # round 3: a table with two chairs facing it
            q = math.sqrt(.5)
            items = [("TableCommercial0%d" % (1 + h % 3), X, Y, ALONG),
                     ("ChairCommercial01", X - .6, Y, (0, q, 0, q)), ("ChairCommercial01", X + .6, Y, (0, -q, 0, q))]
        elif "crate" in kind:
            items = [("CratePile0%d" % (1 + h % 3), X, Y, ALONG)]
        elif "barrel" in kind:
            items = [("BarrelPile0%d" % (1 + h % 3), X, Y, ALONG)]
        elif "bench" in kind:                                             # RULE (the author 2026-11-09): NO BENCHES, anywhere.
            continue                                                      # A bench is a seat citizens walk to, so one off
                                                                          # the path raises "no pedestrian access".
        else:
            skipped.append(p["kind"]); continue
        for n, x, y, rot in items:
            lx, lz = _local(x, y, lot)
            placed.append((n, lx, lz, rot))
    return placed, skipped

def subobjects_component(T, placed):
    items = []
    for n, x, z, (qx, qy, qz, qw) in placed:
        items.append({"$id": 0, "$type": T("Game.Prefabs.ObjectSubObjectInfo, Game"),
                      "m_Object": "@@FSTR@@UnityGUID:" + _G[n],
                      "m_Position": {"$type": T("Unity.Mathematics.float3, Unity.Mathematics"), "x": x, "y": 0, "z": z},
                      "m_Rotation": {"$type": T("Unity.Mathematics.quaternion, Unity.Mathematics"),
                                     "value": {"$type": T("Unity.Mathematics.float4, Unity.Mathematics"), "x": qx, "y": qy, "z": qz, "w": qw}},
                      "m_ParentMesh": -1, "m_GroupIndex": 0, "m_Probability": 100})
    return {"$id": 0, "$type": T("Game.Prefabs.ObjectSubObjects, Game"), "name": "ObjectSubObjects", "active": True,
            "m_SubObjects": {"$id": 0, "$type": T("Game.Prefabs.ObjectSubObjectInfo[], Game"), "$rlength": len(items), "$rcontent": items}}

# ---------------------------------------------------------------- service buildings (S0, 2026-11-08)
# A service is an imported building plus the game's service components. The components are copied from a working
# custom service asset (Chicago Region Pack, pdx 165974, in the author's mod cache) and retyped into our file; our own
# numbers (capacity, upkeep) come from newfrance_services.json. Vehicles leave by "Car Spawn Location" markers just
# inside each door, joined to the street by invisible car paths ending 2 m short of the lot front, as that pack does.
SERVICES = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "newfrance_services.json"), encoding="utf-8"))
SERVICES = {k: v for k, v in SERVICES.items() if not k.startswith("_")}
_PACK = os.path.join(os.environ["USERPROFILE"], "AppData", "LocalLow", "Colossal Order", "Cities Skylines II",
                     ".cache", "Mods", "pdx_mods", "165974_2", "Chicago Region Pack.cok")
TEMPLATES = {"fire": ("NA_Engine5Firehouse_", "FireStation"), "police": ("NA_MaxwellStreetPoliceStation_", "PoliceStation"),
             "hospital": ("NA_StElizabethHospital_", "Hospital"), "school": ("NA_SchurzHighSchool_", "School"), "elementary": ("NA_BellElementarySchool_", "School"),
             "post": ("NA_LoganSquarePostOffice_", "PostFacility"),
             # a unique civic landmark (R4 Hôtel de Ville): the pack's library is a one-per-city Park with leisure + attraction
             "landmark": ("NA_BlackstoneBranchLibrary_", "Park"),
             # a park monument (M1, 2026-11-09): the same Park wiring, but placeable as often as you like
             "park": ("NA_BlackstoneBranchLibrary_", "Park"),
             # Lobstertown utilities (ZS1, 2026-11-17): templates from other packs in the author's mod cache (third item = pack)
             "water": ("NA_DeverCribWaterIntake_", "WaterPumpingStation", _PACK),   # its FloatingObject is not copied
             "power": ("battersea_", "PowerPlant", os.path.join(os.path.dirname(os.path.dirname(_PACK)), "154430_5",
                                                                  "battersea_30f63c20667d9fed35deeecb631cdf5d.cok"))}
SERVICE_COMPONENTS = {"CityServiceBuilding", "ServiceConsumption", "PlaceableObject", "ServiceObject", "UIObject",
                      "Workplace", "ServiceCoverage", "Unlockable", "Pollution", "ServiceFeeCollector", "InitialResources",
                      "StorageLimit", "ResourceConsumer", "ObjectSubNets", "UniqueObject", "Attraction", "LeisureProvider"} | {t[1] for t in TEMPLATES.values()}
_TPL = {}

def service_template(kind):
    """the template's service components, as loaded (types still in the template's numbering) + its type names"""
    if kind not in _TPL:
        import zipfile, tempfile
        prefix, _, *pack = TEMPLATES[kind]
        z = zipfile.ZipFile(pack[0] if pack else _PACK)
        n = next(n for n in z.namelist() if re.match(re.escape(prefix) + r"[0-9a-f]{32}\.Prefab$", os.path.basename(n)))
        with tempfile.NamedTemporaryFile("wb", suffix=".Prefab", delete=False) as t:
            t.write(z.read(n))
        doc = load(t.name); os.unlink(t.name)
        comps = [c for c in doc["components"]["$rcontent"] if c.get("name") in SERVICE_COMPONENTS and c["name"] != "ObjectSubNets"]
        _TPL[kind] = (comps, doc["@@TYPENAMES@@"])
    return _TPL[kind]

def _retype(o, names, T):
    if isinstance(o, dict):
        t = o.get("$type")
        if isinstance(t, str) and "|" in t: o["$type"] = T(t.split("|", 1)[1])
        elif isinstance(t, int): o["$type"] = T(names[t])
        if "$id" in o: o["$id"] = 0
        for k, v in o.items():
            if k not in ("$type", "$id"): _retype(v, names, T)
    elif isinstance(o, list):
        for v in o: _retype(v, names, T)
    return o

def setup_service(doc, T, name, lot, spec):
    """turn an imported building into a working service; returns the spawn markers to add to its sub-objects"""
    comps, names = service_template(spec["kind"])
    lst = doc["components"]["$rcontent"]
    lst[:] = [c for c in lst if c.get("name") not in SERVICE_COMPONENTS | {"SpawnableBuilding", "BuildingProperties"}]
    for c in comps:
        if spec["kind"] == "park" and c["name"] == "UniqueObject": continue   # monuments are not one-per-city
        if c["name"] in spec.get("drop", ()): continue                       # e.g. a monument employs nobody
        c = _retype(json.loads(json.dumps(c)), names, T)
        for k, v in spec.get("values", {}).get(c["name"], {}).items():     # our numbers over the template's
            c[k] = v
        if c["name"] == "Unlockable" and spec.get("unlock"):               # a different development-tree node than the template's
            c["m_RequireAll"]["$rcontent"] = ["@@FSTR@@UnityGUID:" + _G[spec["unlock"]]]
        lst.append(c)
    W, D = lot[0] * 8.0, lot[1] * 8.0
    markers, nets = [], []
    for i, (X, Y) in enumerate(spec.get("vehicle_points_lot_m", [])):
        x, z = _local(X, Y, lot)
        markers.append(("Car Spawn Location", x, z, ALONG))
        f3 = lambda zz: {"$type": T("Unity.Mathematics.float3, Unity.Mathematics"), "x": x, "y": 0, "z": round(zz, 3)}
        end = D / 2 - 2
        nets.append({"$id": 0, "$type": T("Game.Prefabs.ObjectSubNetInfo, Game"),
                     "m_NetPrefab": "@@FSTR@@UnityGUID:" + _G["Invisible Car Path - 1xTwoway"],
                     "m_BezierCurve": {"$type": T("Colossal.Mathematics.Bezier4x3, Colossal.Mathematics"),
                                       "a": f3(z), "b": f3(z + (end - z) / 3), "c": f3(z + 2 * (end - z) / 3), "d": f3(end)},
                     "m_NodeIndex": {"$type": T("Unity.Mathematics.int2, Unity.Mathematics"), "x": 100 + 2 * i, "y": 101 + 2 * i},
                     "m_ParentMesh": {"$type": T("Unity.Mathematics.int2, Unity.Mathematics"), "x": -1, "y": -1},
                     "m_Upgrades": None})
    if spec.get("pedestrian_point_lot_m"):
        x, z = _local(*spec["pedestrian_point_lot_m"], lot)
        markers.append(("Pedestrian Spawn Location", x, z, ALONG))
    if nets:
        lst.append({"$id": 0, "$type": T("Game.Prefabs.ObjectSubNets, Game"), "name": "ObjectSubNets", "active": True,
                    "m_SubNets": {"$id": 0, "$type": T("Game.Prefabs.ObjectSubNetInfo[], Game"), "$rlength": len(nets), "$rcontent": nets},
                    "m_InvertWhen": 0})
    doc["components"]["$rlength"] = len(lst)
    return markers

# ---------------------------------------------------------------- release dressing: menu name, description, thumbnail
# The game shows a prefab's file name unless a locale file sits beside it, and a stock icon unless UIObject.m_Icon
# points at a picture in the asset database. Both are written the way the Chicago Region Pack ships them:
#   <name>_en-US.loc (+ .cid)            binary: "Assets.NAME[<name>]" and "Assets.DESCRIPTION[<name>]"
#   <name>_<32 hex>.png (+ .png.cid)     512x512 transparent; the icon address is assetdb://global/<the .cid>
# The ids are made from the name, so a re-run writes the same files instead of piling up new ones.
THUMBS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "thumbnails")
DRESS_LOG = []

def _hex(*parts):
    return hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()

def _lstr(text):                                                    # .NET string: 7-bit length prefix, then UTF-8
    b = text.encode("utf-8"); n = len(b); out = bytearray()
    while True:
        out.append((n & 0x7F) | (0x80 if n > 0x7F else 0)); n >>= 7
        if not n: break
    return bytes(out) + b

def write_locale(folder, name, title, description):
    body = bytes([1, 0]) + _lstr("English") + _lstr("en-US") + _lstr("English") + struct.pack("<i", 2)
    body += _lstr(f"Assets.NAME[{name}]") + _lstr(title) + _lstr(f"Assets.DESCRIPTION[{name}]") + _lstr(description)
    body += struct.pack("<i", 0)
    f = os.path.join(folder, name + "_en-US.loc")
    open(f, "wb").write(body); open(f + ".cid", "w", encoding="ascii").write(_hex(name, "loc"))

def write_thumbnail(folder, name):
    """copy thumbnails/<name>.png beside the prefab; returns the icon address, or None if there is no picture"""
    src = os.path.join(THUMBS, name + ".png")
    if not os.path.exists(src): return None
    cid = _hex(name, "icon")
    if not DRY:
        dst = os.path.join(folder, f"{name}_{_hex(name, 'png')}.png")
        shutil.copyfile(src, dst); open(dst + ".cid", "w", encoding="ascii").write(cid)
    return "assetdb://global/" + cid

def dress(doc, folder, name, spec):
    named = bool(spec.get("name"))
    if named and not DRY: write_locale(folder, name, spec["name"], spec.get("description", ""))
    icon = write_thumbnail(folder, name)
    if icon:
        for c in doc["components"]["$rcontent"]:
            if c.get("name") == "UIObject": c["m_Icon"] = icon
    DRESS_LOG.append((name, named, bool(icon)))

# ---------------------------------------------------------------- the edits
# building prefab only: "<name>_<32 hex>.Prefab" (the " Mesh_" and LOD mesh prefabs share the prefix)
# services are named like the Chicago pack's (NA_PdDCaserneArcCanal, no level or lot): the importer reads the lot in a
# name as one digit each way, so a 12x10 monument can't carry it. Their lot comes from newfrance_services.json instead.
FILE = re.compile(r"^(?P<name>NA_(?:NewFrance|PdD|LT)(?P<design>[A-Za-z]+?)(?:_L1_(?P<w>\d)x(?P<d>\d))?)_[0-9a-f]{32}\.Prefab$")

def lot_of(m):
    return (int(m.group("w")), int(m.group("d"))) if m.group("w") else tuple(SERVICES[m.group("name")]["lot"])

ZONE_FILES = {}
PROP_LOG = []
SERVICE_LOG = []
PRODUCT_LOG = {}                                                 # Z10 product label -> buildings restricted to it

def zone_sold(zone):
    """m_AllowedSold from a zone's ZoneProperties (the mixed zone's own, else Commercial Low's), for mixed buildings"""
    for z in (zone, "Napoleon Commerces Populaires"):
        if z not in ZONE_FILES: continue
        comp = next((c for c in load(ZONE_FILES[z])["components"]["$rcontent"] if c.get("name") == "ZoneProperties"), None)
        if comp and comp.get("m_AllowedSold"):
            return comp["m_AllowedSold"], z
    return None, None

def zone_cids():
    """every ZonePrefab in ImportedData, keyed by its internal name (renaming in the editor keeps the old file name)"""
    found = {}
    for dirpath, _, files in os.walk(ROOT):
        for f in files:
            if not f.endswith(".Prefab") or not os.path.exists(os.path.join(dirpath, f + ".cid")): continue
            head = open(os.path.join(dirpath, f), encoding="utf-8", errors="ignore").read(400)
            if "Game.Prefabs.ZonePrefab" not in head: continue
            m = re.search(r'"name":\s*"([^"]+)"', head)
            if m:
                nm = re.sub(r'(\\[rnt])+$', '', m.group(1)).strip()   # pasted names can carry trailing line breaks
                found[nm] = open(os.path.join(dirpath, f + ".cid")).read().strip()
                ZONE_FILES[nm] = os.path.join(dirpath, f)
    return found

def zone_name(design):
    z = DESIGNS.get(base_design(design), (None, None))[0]
    if z: return RENAMED.get(z, z)
    for key, zone in ZONE_OF:
        if key in design: return RENAMED.get(zone, zone)
    return None

def setup_building(path, m, zone_cid):
    doc = load(path)
    T = Types(doc)
    design = m.group("design")
    access = "RightCorner" if "RightCorner" in design else "LeftCorner" if "LeftCorner" in design else \
             ACCESS_OF.get(m.group("name"), ACCESS_OF.get(base_design(design), "Front"))   # else designs.json "access"
    doc["m_LotWidth"], doc["m_LotDepth"] = lot_of(m)
    doc["m_AccessType"] = ACCESS[access]
    spec = SERVICES.get(m.group("name"))
    markers = []
    if spec:                                                        # a service: no zone, service components instead
        markers = setup_service(doc, T, m.group("name"), lot_of(m), spec)
    elif any(c.get("name") == "CityServiceBuilding" for c in doc["components"]["$rcontent"]):
        lst = doc["components"]["$rcontent"]                        # taken off the services list: back to a growable
        lst[:] = [c for c in lst if c.get("name") not in SERVICE_COMPONENTS]
        doc["components"]["$rlength"] = len(lst)
    if zone_cid and not spec:
        set_component(doc, {
            "$id": 0, "$type": T("Game.Prefabs.SpawnableBuilding, Game"), "name": "SpawnableBuilding", "active": True,
            "m_ZoneType": "@@FSTR@@CID:" + zone_cid,
            "m_LevelUpResources": {"$id": 0, "$type": T("Game.Prefabs.ResourceStackInEditor[], Game"), "$rlength": 0, "$rcontent": []},
            "m_Level": 1,
        })
        zn = zone_name(design) or ""
        nonres = {ZONE_KEY[k] for k in ("Z6", "Z7", "Z8", "Z9", "Z10", "ZI1", "ZO1")}   # shops/offices/industry: no flats. By zone key, not
        if zn in (ZONE_KEY["Z10"], ZONE_KEY["ZI1"]):                # green industry: this building's clean product(s) only
            product = PRODUCT_OF.get(m.group("name"))
            if product not in CLEAN_PRODUCTS:
                raise SystemExit(f"Green-industry building {m.group('name')} has no clean product (designs.json says {product!r})")
            rl = lambda items: {"$id": 0, "$type": T("Game.Economy.ResourceInEditor[], Game"), "$rlength": len(items), "$rcontent": list(items)}
            set_component(doc, {
                "$id": 0, "$type": T("Game.Prefabs.BuildingProperties, Game"), "name": "BuildingProperties", "active": True,
                "m_ResidentialProperties": 0,
                "m_AllowedSold": rl([]), "m_AllowedInput": rl([]), "m_AllowedManufactured": rl(CLEAN_PRODUCTS[product]),
                "m_AllowedStored": rl([]), "m_SpaceMultiplier": Z10_SPACE_MULTIPLIER,
            })
            PRODUCT_LOG[product] = PRODUCT_LOG.get(product, 0) + 1
        elif "Commercial" not in zn and zn not in nonres:           # keyword: the author's names (Commerces...) lack "Commercial"
            empty = lambda: {"$id": 0, "$type": T("Game.Economy.ResourceInEditor[], Game"), "$rlength": 0, "$rcontent": []}
            hh = HH_OF.get(m.group("name")) or DESIGNS.get(base_design(design), (None, None))[1]   # exact size first
            if not hh and zn == ZONE_KEY["Z4"]:                    # low-rent tenements (R9): denser than Z2B's 8-10 a lot,
                depth = int(re.search(r"_L1_\d+x(\d+)$", m.group("name")).group(1))   # well under Z3's 30+; corners +2
                hh = Z4_HOUSEHOLDS.get(depth, 14) + (2 if "Angle" in design else 0)
            if not hh:
                hh = next((n for k, n in HOUSEHOLDS.items() if k in design), 1)
            sold = empty()
            if "Mixed" in zn or "Mixte" in zn:                                       # shop below, flats above: the shop needs goods to sell
                src, _ = zone_sold(zn)
                if src:
                    decl = sold["$type"]                    # keep the declaration the blank list already took
                    sold = json.loads(json.dumps(src))
                    sold["$type"] = decl
                    for it in sold.get("$rcontent", []):
                        if isinstance(it, dict) and "$type" in it: it["$type"] = T(it["$type"].split("|", 1)[1]) if isinstance(it["$type"], str) and "|" in it["$type"] else it["$type"]
            set_component(doc, {
                "$id": 0, "$type": T("Game.Prefabs.BuildingProperties, Game"), "name": "BuildingProperties", "active": True,
                "m_ResidentialProperties": int(hh),
                "m_AllowedSold": sold, "m_AllowedInput": empty(), "m_AllowedManufactured": empty(), "m_AllowedStored": empty(),
                "m_SpaceMultiplier": 0,
            })
    placed, skipped = [], []
    if GARDEN_PROPS and m.group("name") in PROPS:
        lot, props = PROPS[m.group("name")]
        placed, skipped = garden_objects(m.group("name"), lot, props)
        PROP_LOG.append((m.group("name"), len(placed), skipped))
    if placed or markers: set_component(doc, subobjects_component(T, placed + markers))
    else:                                                       # take off garden props an earlier run placed (ours only)
        ours = {"UnityGUID:" + _G[n] for n in _G}
        lst = doc["components"]["$rcontent"]
        old = [x for x in lst if x.get("name") == "ObjectSubObjects"]
        if old and all(str(i.get("m_Object", "")).replace("@@FSTR@@", "") in ours
                       for i in old[0]["m_SubObjects"]["$rcontent"]):
            lst[:] = [x for x in lst if x.get("name") != "ObjectSubObjects"]
            doc["components"]["$rlength"] = len(lst)
    if spec:
        SERVICE_LOG.append((m.group("name"), spec["kind"], len(markers)))
        dress(doc, os.path.dirname(path), m.group("name"), spec)
    save(path, doc)
    return access

# ---------------------------------------------------------------- colour variations (Lobstertown, 2026-11-14)
# The main mesh's RenderPrefab gets a ColorProperties: one set of three colours is picked per building in game and
# multiplies the base colour where the shared ControlMask is R / G / B (the atlas marks walls G and trim B).
# Laid out like the Toronto pack's (one variation group, channels bound 0/1/2); LOD meshes take the main mesh's.
MESH_FILE = re.compile(r"^(?P<name>NA_LT(?P<design>[A-Za-z]+?)_L1_\dx\d) Mesh_[0-9a-f]{32}\.Prefab$")
_cv = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gemini", "colour_variations.json")
COLOURS = json.load(open(_cv, encoding="utf-8")) if os.path.exists(_cv) else {"designs": {}}
COLOUR_LOG = []

def colour_properties(T, sets, rnd):
    color = T("UnityEngine.Color, UnityEngine.CoreModule")
    int3 = T("Unity.Mathematics.int3, Unity.Mathematics")
    vsets = [{"$id": 0, "$type": T("Game.Prefabs.ColorProperties+VariationSet, Game"),
              "m_Colors": {"$id": 0, "$type": T("UnityEngine.Color[], UnityEngine.CoreModule"), "$rlength": 3,
                           "$rcontent": [{"$type": color, "@@VALS@@": [round(c, 4) for c in rgb] + [1]} for rgb in cs]},
              "m_VariationGroup": "Shore"} for cs in sets]
    binding = T("Game.Prefabs.ColorProperties+ColorChannelBinding, Game")
    return {"$id": 0, "$type": T("Game.Prefabs.ColorProperties, Game"), "name": "ColorProperties", "active": True,
            "m_ColorVariations": {"$id": 0, "$type": T("System.Collections.Generic.List`1[[Game.Prefabs.ColorProperties+VariationSet, Game]], mscorlib"),
                                  "$rlength": len(vsets), "$rcontent": vsets},
            "m_ChannelsBinding": {"$id": 0, "$type": T("System.Collections.Generic.List`1[[Game.Prefabs.ColorProperties+ColorChannelBinding, Game]], mscorlib"),
                                  "$rlength": 3, "$rcontent": [{"$id": 0, "$type": binding, "m_ChannelId": i,
                                                               "m_CanBeModifiedByExternal": False} for i in range(3)]},
            "m_VariationGroups": {"$id": 0, "$type": T("System.Collections.Generic.List`1[[Game.Prefabs.ColorProperties+VariationGroup, Game]], mscorlib"),
                                  "$rlength": 1, "$rcontent": [{"$id": 0, "$type": T("Game.Prefabs.ColorProperties+VariationGroup, Game"),
                                                               "m_Name": "Shore", "m_Probability": 100, "m_MeshSyncMode": 2,
                                                               "m_OverrideRandomness": False,
                                                               "m_VariationRanges": {"$type": int3, "x": rnd[0], "y": rnd[1], "z": rnd[2]},
                                                               "m_AlphaRanges": {"$type": int3, "x": 0, "y": 0, "z": 0}}]},
            "m_VariationRanges": {"$type": int3, "x": rnd[0], "y": rnd[1], "z": rnd[2]},
            "m_AlphaRanges": {"$type": int3, "x": 0, "y": 0, "z": 0},
            "m_ExternalColorSource": 0}

def setup_colours(path, m):
    sets = COLOURS["designs"].get(f"NA_LT{m.group('design')}")
    if not sets: return
    doc = load(path)
    set_component(doc, colour_properties(Types(doc), sets, COLOURS.get("random", [2, 4, 5])))
    save(path, doc)
    COLOUR_LOG.append(m.group("name"))

def main():
    zones = zone_cids()
    print("Zones found:", ", ".join(f"{k} (CID {v})" for k, v in sorted(zones.items())) or "none")
    missing, done = set(), 0
    for dirpath, _, files in os.walk(ROOT):
        if os.path.basename(dirpath).startswith("."): continue            # the author's dot-disabled folders
        for f in sorted(files):
            mm = MESH_FILE.match(f)
            if mm: setup_colours(os.path.join(dirpath, f), mm)
            m = FILE.match(f)
            if not m or (not m.group("w") and m.group("name") not in SERVICES): continue
            zn = zone_name(m.group("design"))
            cid = zones.get(zn)
            if not cid and m.group("name") not in SERVICES: missing.add(zn)
            access = setup_building(os.path.join(dirpath, f), m, cid); done += 1
            if m.group("name") in SERVICES:
                print(f"  {m.group('name')}: lot {'x'.join(map(str, lot_of(m)))}, access {access}, SERVICE {SERVICES[m.group('name')]['kind']}"); continue
            print(f"  {m.group('name')}: lot {m.group('w')}x{m.group('d')}, access {access}, "
                  f"zone {zn + '' if cid else zn + ' (MISSING - lot and access only)'}")
    print(f"{'Would set up' if DRY else 'Set up'} {done} buildings.")
    if COLOUR_LOG:
        print(f"Colour variations on {len(COLOUR_LOG)} main meshes.")
    if PROP_LOG:
        print(f"Garden props on {sum(1 for _, n, _ in PROP_LOG if n)} buildings, {sum(n for _, n, _ in PROP_LOG)} objects in all.")
        sk = sorted({k for _, _, s in PROP_LOG for k in s})
        if sk: print("Prop kinds not placed (no vanilla match):", ", ".join(sk))
    if PRODUCT_LOG:
        print("Z10 clean products:", ", ".join(f"{k} {v}" for k, v in sorted(PRODUCT_LOG.items())), f"({sum(PRODUCT_LOG.values())} buildings)")
    for n, k, nm in SERVICE_LOG:
        print(f"Service: {n} wired as {k} ({nm} spawn markers)")
    if DRESS_LOG:
        print(f"Menu names on {sum(1 for _, n, _ in DRESS_LOG if n)} of {len(DRESS_LOG)} services, thumbnails on {sum(1 for _, _, i in DRESS_LOG if i)}.")
        for n, named, icon in DRESS_LOG:
            if not (named and icon): print(f"  {n}: missing {'name ' if not named else ''}{'thumbnail' if not icon else ''}")
    if missing:
        print("Missing zones (make these in the editor, then run again):", ", ".join(sorted(missing)))

if __name__ == "__main__":
    main()
