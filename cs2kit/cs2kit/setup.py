"""Manifest-driven Cities: Skylines II ImportedData patcher, pre-import archiver, and .loc/icon dresser.

Handles the exact CS2 JSON dialect ($fstrref:"...", inline structs, $type/$id renumbering) safely.
Never modifies anything outside the explicit target ImportedData/backups paths.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import tempfile
import zipfile

from .config import CLEAN_PRODUCTS, ConfigError, PackConfig

ACCESS = {"Front": 0, "LeftCorner": 1, "RightCorner": 2}
ALONG = (0.0, 0.0, 0.0, 1.0)

SERVICE_COMPONENTS = {
    "CityServiceBuilding",
    "ServiceConsumption",
    "PlaceableObject",
    "ServiceObject",
    "UIObject",
    "Workplace",
    "ServiceCoverage",
    "Unlockable",
    "Pollution",
    "ServiceFeeCollector",
    "InitialResources",
    "StorageLimit",
    "ResourceConsumer",
    "ObjectSubNets",
    "UniqueObject",
    "Attraction",
    "LeisureProvider",
    "FireStation",
    "PoliceStation",
    "Hospital",
    "School",
    "PostFacility",
    "Park",
    "WaterPumpingStation",
    "PowerPlant",
}

DEFAULT_TEMPLATES = {
    "fire": ("NA_Engine5Firehouse_", "FireStation"),
    "police": ("NA_MaxwellStreetPoliceStation_", "PoliceStation"),
    "hospital": ("NA_StElizabethHospital_", "Hospital"),
    "school": ("NA_SchurzHighSchool_", "School"),
    "elementary": ("NA_BellElementarySchool_", "School"),
    "post": ("NA_LoganSquarePostOffice_", "PostFacility"),
    "landmark": ("NA_BlackstoneBranchLibrary_", "Park"),
    "park": ("NA_BlackstoneBranchLibrary_", "Park"),
    "water": ("NA_DeverCribWaterIntake_", "WaterPumpingStation"),
}


def default_imported_data() -> Path:
    return Path(os.environ.get("USERPROFILE", str(Path.home()))) / "AppData/LocalLow/Colossal Order/Cities Skylines II/ImportedData"


def default_chicago_pack() -> Path:
    return (
        Path(os.environ.get("USERPROFILE", str(Path.home())))
        / "AppData/LocalLow/Colossal Order/Cities Skylines II/.cache/Mods/pdx_mods/165974_2/Chicago Region Pack.cok"
    )


def resolve_guids_path(explicit: str | None = None) -> Path | None:
    cands = []
    if explicit:
        cands.append(Path(explicit))
    if os.environ.get("CS2KIT_GUIDS"):
        cands.append(Path(os.environ["CS2KIT_GUIDS"]))
    cands.append(Path(__file__).resolve().parent / "data" / "vanilla_prefab_guids.json")
    cands.append(Path(__file__).resolve().parents[2] / "Lobstertown" / "tools" / "vanilla_prefab_guids.json")
    for p in cands:
        if p.exists():
            return p
    return None


def load_guids(guids_path: Path | None) -> dict[str, str]:
    if not guids_path or not guids_path.exists():
        return {}
    raw = json.loads(guids_path.read_text(encoding="utf-8"))
    out = {}
    for g, n in raw.items():
        if n:
            out.setdefault(n, g)
    return out


# ---------------------------------------------------------------- CS2 Prefab JSON dialect


def load_prefab(path: Path) -> dict:
    s = Path(path).read_text(encoding="utf-8")
    s = re.sub(r'\$fstrref:"([^"]*)"', r'"@@FSTR@@\1"', s)
    s = re.sub(
        r'\{\s*"\$type":\s*("[^"]*"|\d+),\s*((?:-?[\d.eE+]+\s*,\s*)*-?[\d.eE+]+)\s*\}',
        lambda m: '{"$type": %s, "@@VALS@@": [%s]}' % (m.group(1), m.group(2)),
        s,
    )
    doc = json.loads(s)
    names = {}

    def scan(o):
        if isinstance(o, dict):
            t = o.get("$type")
            if isinstance(t, str) and "|" in t:
                n, name = t.split("|", 1)
                names.setdefault(int(n), name)
            for v in o.values():
                scan(v)
        elif isinstance(o, list):
            for v in o:
                scan(v)

    scan(doc)
    doc["@@TYPENAMES@@"] = names
    return doc


def renumber(doc: dict):
    """Renumber $type indices and $id sequentially in document order as CS2 expects."""
    tmap, ids = {}, [0]
    names = doc.pop("@@TYPENAMES@@", {})

    def walk(o):
        if isinstance(o, dict):
            if "$id" in o:
                o["$id"] = ids[0]
                ids[0] += 1
            t = o.get("$type")
            if isinstance(t, str) and "|" in t:
                old, name = t.split("|", 1)
                if int(old) in tmap:
                    o["$type"] = tmap[int(old)]
                else:
                    tmap[int(old)] = len(tmap)
                    o["$type"] = f"{tmap[int(old)]}|{name}"
            elif isinstance(t, int):
                if t in tmap:
                    o["$type"] = tmap[t]
                else:
                    tmap[t] = len(tmap)
                    o["$type"] = f"{tmap[t]}|{names[t]}"
            for k, v in o.items():
                if k not in ("$type", "$id"):
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(doc)


def save_prefab(path: Path, doc: dict, dry_run: bool = False):
    renumber(doc)
    s = json.dumps(doc, indent=4, ensure_ascii=False)
    s = re.sub(r'"@@FSTR@@([^"]*)"', r'$fstrref:"\1"', s)
    s = re.sub(
        r'"\$type": ("[^"]*"|\d+),\s*"@@VALS@@": \[\s*([^\]]*?)\s*\]',
        lambda m: '"$type": %s, %s' % (m.group(1), ", ".join(x.strip() for x in m.group(2).split(","))),
        s,
    )
    if dry_run:
        return
    p = Path(path)
    bak = Path(str(p) + ".bak")
    if not bak.exists():
        shutil.copyfile(p, bak)
    p.write_text(s, encoding="utf-8", newline="\r\n")


def _max_type(doc: dict) -> int:
    best = [0]

    def walk(o):
        if isinstance(o, dict):
            t = o.get("$type")
            if isinstance(t, str) and "|" in t:
                best[0] = max(best[0], int(t.split("|")[0]))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(doc)
    return best[0]


class Types:
    """Allocate fresh $type indices for new components (deduplicated later by renumber())."""

    def __init__(self, doc: dict):
        self.n = _max_type(doc) + 1
        self.existing = {nm: n for n, nm in doc.get("@@TYPENAMES@@", {}).items()}
        self.seen = {}

    def __call__(self, name: str):
        if name in self.existing:
            return f"{self.existing[name]}|{name}"
        if name in self.seen:
            return self.seen[name]
        self.seen[name] = self.n
        self.n += 1
        return f"{self.seen[name]}|{name}"


def set_component(doc: dict, comp: dict):
    lst = doc["components"]["$rcontent"]
    lst[:] = [c for c in lst if c.get("name") != comp["name"]] + [comp]
    doc["components"]["$rlength"] = len(lst)


# ---------------------------------------------------------------- Pre-import duplicate archiver


def _matches_asset_stem(filename: str, asset_names: set[str]) -> bool:
    stem = filename
    for ext in (".bak", ".cid"):
        if stem.endswith(ext):
            stem = stem[: -len(ext)]
    for name in asset_names:
        if stem == name or stem.startswith(name + "_") or stem.startswith(name + " Mesh_") or stem.startswith(name + " "):
            # Avoid partial prefix overlap such as `Foo_L1_1x2` vs `FooBar_L1_1x2`:
            # asset names always terminate right before `_<hex>`, `_LOD`, `_en-US`, or ` Mesh_`.
            rest = stem[len(name) :]
            if not rest or rest.startswith((" Mesh_", "_LOD", "_en-US")):
                return True
            if re.match(r"^_[0-9a-f]{32}\.", rest):
                return True
    return False


def pre_import_cleanup(ready_dir: Path, imported_data_dir: Path, backups_dir: Path, pack_id: str, dry_run: bool = False) -> dict:
    """Move stale ImportedData copies for assets in `ready_dir` into `backups_dir`."""
    ilist = ready_dir / "IMPORT-LIST.txt"
    if ilist.exists():
        names = {line.strip() for line in ilist.read_text(encoding="utf-8").splitlines() if line.strip()}
    else:
        names = {d.name for d in ready_dir.iterdir() if d.is_dir() and d.name != "thumbnails"}

    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    archive_root = backups_dir / f"ImportedData_{stamp}_{pack_id}"
    moved = []

    if not imported_data_dir.exists():
        return {"matched": 0, "moved": [], "archive_dir": str(archive_root)}

    for dirpath, _, files in os.walk(imported_data_dir):
        dp = Path(dirpath)
        if dp.name.startswith("."):
            continue
        for f in sorted(files):
            if _matches_asset_stem(f, names):
                src = dp / f
                rel = src.relative_to(imported_data_dir)
                dst = archive_root / rel
                moved.append({"src": str(src), "dst": str(dst)})
                if not dry_run:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src), str(dst))

    return {"matched": len(moved), "moved": moved, "archive_dir": str(archive_root)}


# ---------------------------------------------------------------- Locale + Thumbnail + ColorProperties


def _hex(*parts) -> str:
    return hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()


def _lstr(text: str) -> bytes:
    b = text.encode("utf-8")
    n = len(b)
    out = bytearray()
    while True:
        out.append((n & 0x7F) | (0x80 if n > 0x7F else 0))
        n >>= 7
        if not n:
            break
    return bytes(out) + b


def write_locale(folder: Path, name: str, title: str, description: str):
    body = bytes([1, 0]) + _lstr("English") + _lstr("en-US") + _lstr("English") + struct.pack("<i", 2)
    body += _lstr(f"Assets.NAME[{name}]") + _lstr(title) + _lstr(f"Assets.DESCRIPTION[{name}]") + _lstr(description)
    body += struct.pack("<i", 0)
    loc = folder / f"{name}_en-US.loc"
    loc.write_bytes(body)
    (folder / f"{name}_en-US.loc.cid").write_text(_hex(name, "loc"), encoding="ascii")


def write_thumbnail(folder: Path, name: str, thumb_dirs: list[Path], dry_run: bool = False) -> str | None:
    src = next((d / f"{name}.png" for d in thumb_dirs if (d / f"{name}.png").exists()), None)
    if src is None:
        return None
    cid = _hex(name, "icon")
    if not dry_run:
        dst = folder / f"{name}_{_hex(name, 'png')}.png"
        shutil.copyfile(src, dst)
        (folder / f"{dst.name}.cid").write_text(cid, encoding="ascii")
    return "assetdb://global/" + cid


def colour_properties(T, sets: list, rnd: list, group_name: str):
    color = T("UnityEngine.Color, UnityEngine.CoreModule")
    int3 = T("Unity.Mathematics.int3, Unity.Mathematics")
    vsets = [
        {
            "$id": 0,
            "$type": T("Game.Prefabs.ColorProperties+VariationSet, Game"),
            "m_Colors": {
                "$id": 0,
                "$type": T("UnityEngine.Color[], Unity.CoreModule"),
                "$rlength": 3,
                "$rcontent": [{"$type": color, "@@VALS@@": [round(c, 4) for c in rgb] + [1]} for rgb in cs],
            },
            "m_VariationGroup": group_name,
        }
        for cs in sets
    ]
    binding = T("Game.Prefabs.ColorProperties+ColorChannelBinding, Game")
    return {
        "$id": 0,
        "$type": T("Game.Prefabs.ColorProperties, Game"),
        "name": "ColorProperties",
        "active": True,
        "m_ColorVariations": {
            "$id": 0,
            "$type": T("System.Collections.Generic.List`1[[Game.Prefabs.ColorProperties+VariationSet, Game]], mscorlib"),
            "$rlength": len(vsets),
            "$rcontent": vsets,
        },
        "m_ChannelsBinding": {
            "$id": 0,
            "$type": T("System.Collections.Generic.List`1[[Game.Prefabs.ColorProperties+ColorChannelBinding, Game]], mscorlib"),
            "$rlength": 3,
            "$rcontent": [
                {"$id": 0, "$type": binding, "m_ChannelId": i, "m_CanBeModifiedByExternal": False} for i in range(3)
            ],
        },
        "m_VariationGroups": {
            "$id": 0,
            "$type": T("System.Collections.Generic.List`1[[Game.Prefabs.ColorProperties+VariationGroup, Game]], mscorlib"),
            "$rlength": 1,
            "$rcontent": [
                {
                    "$id": 0,
                    "$type": T("Game.Prefabs.ColorProperties+VariationGroup, Game"),
                    "m_Name": group_name,
                    "m_Probability": 100,
                    "m_MeshSyncMode": 2,
                    "m_OverrideRandomness": False,
                    "m_VariationRanges": {"$type": int3, "x": rnd[0], "y": rnd[1], "z": rnd[2]},
                    "m_AlphaRanges": {"$type": int3, "x": 0, "y": 0, "z": 0},
                }
            ],
        },
        "m_VariationRanges": {"$type": int3, "x": rnd[0], "y": rnd[1], "z": rnd[2]},
        "m_AlphaRanges": {"$type": int3, "x": 0, "y": 0, "z": 0},
        "m_ExternalColorSource": 0,
    }


def _zone_cids(imported_data_dir: Path):
    found, files = {}, {}
    for dirpath, _, fs in os.walk(imported_data_dir):
        dp = Path(dirpath)
        if dp.name.startswith("."):
            continue
        for f in fs:
            if not f.endswith(".Prefab"):
                continue
            p = dp / f
            cid_p = dp / (f + ".cid")
            if not cid_p.exists():
                continue
            head = p.read_text(encoding="utf-8", errors="ignore")[:500]
            if "Game.Prefabs.ZonePrefab" not in head:
                continue
            m = re.search(r'"name":\s*"([^"]+)"', head)
            if m:
                nm = re.sub(r"(\\[rnt])+$", "", m.group(1)).strip()
                found[nm] = cid_p.read_text(encoding="utf-8").strip()
                files[nm] = p
    return found, files


def _zone_sold(zone_name: str, zone_files: dict):
    candidates = [zone_name] + [k for k in sorted(zone_files) if "Commercial" in k]
    for z in candidates:
        p = zone_files.get(z)
        if not p:
            continue
        comp = next((c for c in load_prefab(p)["components"]["$rcontent"] if c.get("name") == "ZoneProperties"), None)
        if comp and comp.get("m_AllowedSold"):
            return comp["m_AllowedSold"]
    return None


def _retype(o, names, T):
    if isinstance(o, dict):
        t = o.get("$type")
        if isinstance(t, str) and "|" in t:
            o["$type"] = T(t.split("|", 1)[1])
        elif isinstance(t, int):
            o["$type"] = T(names[t])
        if "$id" in o:
            o["$id"] = 0
        for k, v in o.items():
            if k not in ("$type", "$id"):
                _retype(v, names, T)
    elif isinstance(o, list):
        for v in o:
            _retype(v, names, T)
    return o


def _service_template(kind: str, tpl_cache: dict, chicago_pack: Path):
    if kind in tpl_cache:
        return tpl_cache[kind]
    if kind not in DEFAULT_TEMPLATES:
        raise ConfigError(f"Unsupported service kind {kind!r}; expected one of {sorted(DEFAULT_TEMPLATES)}")
    if not chicago_pack.exists():
        raise ConfigError(f"Service template pack not found at {chicago_pack}")
    prefix, _ = DEFAULT_TEMPLATES[kind]
    with zipfile.ZipFile(chicago_pack) as z:
        n = next(
            (nm for nm in z.namelist() if re.match(re.escape(prefix) + r"[0-9a-f]{32}\.Prefab$", Path(nm).name)),
            None,
        )
        if not n:
            raise ConfigError(f"Service template {prefix!r} not found inside {chicago_pack}")
        with tempfile.NamedTemporaryFile("wb", suffix=".Prefab", delete=False) as tmp:
            tmp.write(z.read(n))
            tmp_path = Path(tmp.name)
    try:
        doc = load_prefab(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)
    comps = [c for c in doc["components"]["$rcontent"] if c.get("name") in SERVICE_COMPONENTS and c["name"] != "ObjectSubNets"]
    tpl_cache[kind] = (comps, doc["@@TYPENAMES@@"])
    return tpl_cache[kind]


def _local_pt(x_lot: float, y_lot: float, lot: list[int]):
    W, D = lot[0] * 8.0, lot[1] * 8.0
    return round(W / 2.0 - x_lot, 3), round(D / 2.0 - y_lot, 3)


def _setup_service(doc: dict, T, lot: list[int], srv: dict, guids: dict, tpl_cache: dict, chicago_pack: Path):
    comps, names = _service_template(srv["kind"], tpl_cache, chicago_pack)
    lst = doc["components"]["$rcontent"]
    lst[:] = [c for c in lst if c.get("name") not in SERVICE_COMPONENTS | {"SpawnableBuilding", "BuildingProperties"}]
    for c in comps:
        if srv["kind"] == "park" and c["name"] == "UniqueObject":
            continue
        if c["name"] in srv.get("drop", ()):
            continue
        c_copy = _retype(json.loads(json.dumps(c)), names, T)
        for k, v in srv.get("values", {}).get(c_copy["name"], {}).items():
            c_copy[k] = v
        if c_copy["name"] == "Unlockable" and srv.get("unlock"):
            if srv["unlock"] not in guids:
                raise ConfigError(f"Unknown unlock node GUID name: {srv['unlock']!r}")
            c_copy["m_RequireAll"]["$rcontent"] = ["@@FSTR@@UnityGUID:" + guids[srv["unlock"]]]
        lst.append(c_copy)

    W, D = lot[0] * 8.0, lot[1] * 8.0
    markers, nets = [], []
    for i, (X, Y) in enumerate(srv.get("vehicle_points_lot_m", [])):
        x, z = _local_pt(X, Y, lot)
        markers.append(("Car Spawn Location", x, z, ALONG))
        f3 = lambda zz: {"$type": T("Unity.Mathematics.float3, Unity.Mathematics"), "x": x, "y": 0, "z": round(zz, 3)}
        end = D / 2.0 - 2.0
        nets.append(
            {
                "$id": 0,
                "$type": T("Game.Prefabs.ObjectSubNetInfo, Game"),
                "m_NetPrefab": "@@FSTR@@UnityGUID:" + guids["Invisible Car Path - 1xTwoway"],
                "m_BezierCurve": {
                    "$type": T("Colossal.Mathematics.Bezier4x3, Colossal.Mathematics"),
                    "a": f3(z),
                    "b": f3(z + (end - z) / 3.0),
                    "c": f3(z + 2.0 * (end - z) / 3.0),
                    "d": f3(end),
                },
                "m_NodeIndex": {"$type": T("Unity.Mathematics.int2, Unity.Mathematics"), "x": 100 + 2 * i, "y": 101 + 2 * i},
                "m_ParentMesh": {"$type": T("Unity.Mathematics.int2, Unity.Mathematics"), "x": -1, "y": -1},
                "m_Upgrades": None,
            }
        )
    if srv.get("pedestrian_point_lot_m"):
        x, z = _local_pt(*srv["pedestrian_point_lot_m"], lot)
        markers.append(("Pedestrian Spawn Location", x, z, ALONG))

    if markers:
        sub_items = []
        for n, x, z, (qx, qy, qz, qw) in markers:
            if n not in guids:
                raise ConfigError(f"Missing vanilla prefab GUID for marker {n!r}")
            sub_items.append(
                {
                    "$id": 0,
                    "$type": T("Game.Prefabs.ObjectSubObjectInfo, Game"),
                    "m_Object": "@@FSTR@@UnityGUID:" + guids[n],
                    "m_Position": {"$type": T("Unity.Mathematics.float3, Unity.Mathematics"), "x": x, "y": 0, "z": z},
                    "m_Rotation": {
                        "$type": T("Unity.Mathematics.quaternion, Unity.Mathematics"),
                        "value": {"$type": T("Unity.Mathematics.float4, Unity.Mathematics"), "x": qx, "y": qy, "z": qz, "w": qw},
                    },
                    "m_ParentMesh": -1,
                    "m_GroupIndex": 0,
                    "m_Probability": 100,
                }
            )
        set_component(
            doc,
            {
                "$id": 0,
                "$type": T("Game.Prefabs.ObjectSubObjects, Game"),
                "name": "ObjectSubObjects",
                "active": True,
                "m_SubObjects": {"$id": 0, "$type": T("Game.Prefabs.ObjectSubObjectInfo[], Game"), "$rlength": len(sub_items), "$rcontent": sub_items},
            },
        )
    if nets:
        set_component(
            doc,
            {
                "$id": 0,
                "$type": T("Game.Prefabs.ObjectSubNets, Game"),
                "name": "ObjectSubNets",
                "active": True,
                "m_SubNets": {"$id": 0, "$type": T("Game.Prefabs.ObjectSubNetInfo[], Game"), "$rlength": len(nets), "$rcontent": nets},
                "m_InvertWhen": 0,
            },
        )
    doc["components"]["$rlength"] = len(lst)


def setup_pack(
    manifest: dict,
    imported_data_dir: Path,
    thumb_dirs: list[Path],
    dry_run: bool = False,
    guids_path: Path | None = None,
    chicago_pack: Path | None = None,
) -> dict:
    """Patch all imported CS2 prefabs matching `manifest['prefix']` inside `imported_data_dir`."""
    prefix = manifest["prefix"]
    assets_map = manifest.get("assets", {})
    group_name = manifest.get("variation_group", manifest["pack_id"])
    rnd = manifest.get("colour_random", [2, 4, 5])

    bldg_re = re.compile(rf"^(?P<name>{re.escape(prefix)}[A-Za-z0-9]+?(?:_L1_\dx\d)?)_[0-9a-f]{{32}}\.Prefab$")
    mesh_re = re.compile(rf"^(?P<name>{re.escape(prefix)}[A-Za-z0-9]+?(?:_L1_\dx\d)?) Mesh_[0-9a-f]{{32}}\.Prefab$")

    zones, zone_files = _zone_cids(imported_data_dir)
    guids = load_guids(guids_path)
    tpl_cache = {}
    cpack = chicago_pack or default_chicago_pack()

    updated_buildings = []
    updated_meshes = []
    missing_zones = set()
    skipped = []

    for dirpath, _, files in os.walk(imported_data_dir):
        dp = Path(dirpath)
        if dp.name.startswith("."):
            continue
        for f in sorted(files):
            mm = mesh_re.match(f)
            if mm:
                aname = mm.group("name")
                spec = assets_map.get(aname)
                if spec and spec.get("colour_sets"):
                    p = dp / f
                    doc = load_prefab(p)
                    set_component(doc, colour_properties(Types(doc), spec["colour_sets"], spec.get("colour_random", rnd), group_name))
                    save_prefab(p, doc, dry_run=dry_run)
                    updated_meshes.append(aname)
                continue

            bm = bldg_re.match(f)
            if not bm:
                continue
            aname = bm.group("name")
            spec = assets_map.get(aname)
            if not spec:
                skipped.append(aname)
                continue

            p = dp / f
            doc = load_prefab(p)
            T = Types(doc)
            lot = spec["lot"]
            doc["m_LotWidth"], doc["m_LotDepth"] = int(lot[0]), int(lot[1])
            doc["m_AccessType"] = ACCESS[spec["access"]]

            kind = spec["zone_kind"]
            if spec.get("service"):
                _setup_service(doc, T, lot, spec["service"], guids, tpl_cache, cpack)
            else:
                # Strip stale service components if repurposed
                lst = doc["components"]["$rcontent"]
                if any(c.get("name") == "CityServiceBuilding" for c in lst):
                    lst[:] = [c for c in lst if c.get("name") not in SERVICE_COMPONENTS]
                    doc["components"]["$rlength"] = len(lst)

                zn = spec.get("game_zone") or ""
                cid = zones.get(zn)
                if not cid:
                    missing_zones.add(zn or spec["zone_key"])
                else:
                    set_component(
                        doc,
                        {
                            "$id": 0,
                            "$type": T("Game.Prefabs.SpawnableBuilding, Game"),
                            "name": "SpawnableBuilding",
                            "active": True,
                            "m_ZoneType": "@@FSTR@@CID:" + cid,
                            "m_LevelUpResources": {
                                "$id": 0,
                                "$type": T("Game.Prefabs.ResourceStackInEditor[], Game"),
                                "$rlength": 0,
                                "$rcontent": [],
                            },
                            "m_Level": int(spec.get("level", 1)),
                        },
                    )
                    empty = lambda: {
                        "$id": 0,
                        "$type": T("Game.Economy.ResourceInEditor[], Game"),
                        "$rlength": 0,
                        "$rcontent": [],
                    }
                    if kind == "green_industry":
                        prod = spec.get("product", "")
                        if prod not in CLEAN_PRODUCTS:
                            raise ConfigError(f"Green-industry asset {aname} has invalid product {prod!r}")
                        items = CLEAN_PRODUCTS[prod]
                        set_component(
                            doc,
                            {
                                "$id": 0,
                                "$type": T("Game.Prefabs.BuildingProperties, Game"),
                                "name": "BuildingProperties",
                                "active": True,
                                "m_ResidentialProperties": 0,
                                "m_AllowedSold": empty(),
                                "m_AllowedInput": empty(),
                                "m_AllowedManufactured": {
                                    "$id": 0,
                                    "$type": T("Game.Economy.ResourceInEditor[], Game"),
                                    "$rlength": len(items),
                                    "$rcontent": list(items),
                                },
                                "m_AllowedStored": empty(),
                                "m_SpaceMultiplier": int(spec.get("space_multiplier", 8)),
                            },
                        )
                    elif kind in ("residential", "mixed"):
                        sold = empty()
                        if kind == "mixed":
                            src_sold = _zone_sold(zn, zone_files)
                            if src_sold:
                                decl = sold["$type"]
                                sold = json.loads(json.dumps(src_sold))
                                sold["$type"] = decl
                                for it in sold.get("$rcontent", []):
                                    if isinstance(it, dict) and isinstance(it.get("$type"), str) and "|" in it["$type"]:
                                        it["$type"] = T(it["$type"].split("|", 1)[1])
                        set_component(
                            doc,
                            {
                                "$id": 0,
                                "$type": T("Game.Prefabs.BuildingProperties, Game"),
                                "name": "BuildingProperties",
                                "active": True,
                                "m_ResidentialProperties": int(spec.get("households", 1)),
                                "m_AllowedSold": sold,
                                "m_AllowedInput": empty(),
                                "m_AllowedManufactured": empty(),
                                "m_AllowedStored": empty(),
                                "m_SpaceMultiplier": 0,
                            },
                        )

            # Localization + optional UI icon dressing for all assets (growables AND services!)
            if spec.get("display_name") and not dry_run:
                write_locale(dp, aname, spec["display_name"], spec.get("description", ""))
            icon_addr = write_thumbnail(dp, aname, thumb_dirs, dry_run=dry_run)
            if icon_addr:
                for c in doc["components"]["$rcontent"]:
                    if c.get("name") == "UIObject":
                        c["m_Icon"] = icon_addr

            save_prefab(p, doc, dry_run=dry_run)
            updated_buildings.append(aname)

    return {
        "updated_buildings": updated_buildings,
        "updated_meshes": updated_meshes,
        "missing_zones": sorted(missing_zones),
        "skipped": sorted(skipped),
    }


def run_setup_cli(pack: PackConfig, args) -> int:
    imported_data = Path(args.imported_data).resolve() if args.imported_data else default_imported_data()
    backups_dir = Path(args.backups_dir).resolve() if args.backups_dir else (pack.pack_dir.parent.parent / "backups")

    if args.pre_import:
        ready = Path(args.pre_import).resolve()
        arch = pre_import_cleanup(ready, imported_data, backups_dir, pack.pack_id, dry_run=args.dry_run)
        print(
            f"{'Would archive' if args.dry_run else 'Archived'} {arch['matched']} stale file(s) -> {arch['archive_dir']}"
        )
        if not args.manifest:
            cand = ready / "pack_manifest.json"
            if cand.exists():
                args.manifest = str(cand)

    manifest_path = Path(args.manifest).resolve() if args.manifest else (pack.pack_dir / "staged_registry.json")
    if not manifest_path.exists():
        print(f"No manifest at {manifest_path}; run `stage` first or pass --manifest.")
        return 1 if not args.pre_import else 0

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    thumb_dirs = [pack.pack_dir / "thumbnails"]
    if args.pre_import:
        thumb_dirs.insert(0, Path(args.pre_import).resolve() / "thumbnails")

    res = setup_pack(
        manifest,
        imported_data,
        thumb_dirs=thumb_dirs,
        dry_run=args.dry_run,
        guids_path=resolve_guids_path(args.guids),
    )
    verb = "Would update" if args.dry_run else "Updated"
    print(f"{verb} {len(res['updated_buildings'])} building(s), {len(res['updated_meshes'])} mesh colour set(s).")
    if res["missing_zones"]:
        print("Missing zones in ImportedData (create in editor first):", ", ".join(res["missing_zones"]))
    return 0
