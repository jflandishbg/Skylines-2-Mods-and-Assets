"""Declarative pack configuration, palette expansion, and roster validation."""
from dataclasses import dataclass, field
from pathlib import Path
import json
import re


VALID_ZONE_KINDS = (
    "residential",
    "mixed",
    "commercial",
    "office",
    "green_industry",
    "service",
    "landmark",
)

CLEAN_PRODUCTS = {
    "Textiles": [34],
    "Machinery": [30],
    "Furniture": [10],
    "Paper": [9],
    "Food and convenience food": [4, 3],
    "Food": [4],
    "Convenience food": [3],
    "Electronics": [21],
    "Beverages": [33],
    "Pharmaceuticals": [32],
    "Timber": [8],
    "Vehicles": [11],
}

DEFAULT_BUDGET = [45000, 9000, 1000]
WHITE = [1.0, 1.0, 1.0]


class ConfigError(ValueError):
    """Raised when pack.json or atlas.json contains an invalid declaration."""


@dataclass
class ZoneConfig:
    key: str
    kind: str
    game_name: str = ""
    base_zone: str = ""
    module: str = ""
    budget: list = field(default_factory=lambda: list(DEFAULT_BUDGET))
    density_floor: float = 8.0
    crown_allowed: bool = False
    crown_max_m2: float = 150.0
    party_mode: str = "none"  # "none" | "row"
    max_front_setback_m: float = 1.2
    min_coverage_pct: float = 70.0
    allow_right_corner: bool = False
    default_lots: list = field(default_factory=list)
    expected_lots: list = field(default_factory=list)
    space_multiplier: int = 0
    households_by_lot: dict = field(default_factory=dict)


@dataclass
class ServiceSpec:
    kind: str  # fire, police, hospital, school, elementary, post, landmark, park, water, power
    values: dict = field(default_factory=dict)
    drop: list = field(default_factory=list)
    unlock: str = ""
    vehicle_points_lot_m: list = field(default_factory=list)
    pedestrian_point_lot_m: list = field(default_factory=list)
    thumbnail: bool = True


@dataclass
class DesignSpec:
    design: str
    zone_key: str
    module: str = ""
    display_name: str = ""
    description: str = ""
    lots: list = field(default_factory=list)
    access: str = ""  # "", "Front", "LeftCorner", "RightCorner"
    households: object = None  # int | dict | None
    product: str = ""
    palette_key: str = ""
    colour_sets: list = field(default_factory=list)
    params: dict = field(default_factory=dict)
    omit_lot_suffix: bool = False
    include_lot_in_name: bool = False
    service: ServiceSpec | None = None


@dataclass
class AssetSpec:
    name: str
    design: str
    zone_key: str
    zone: ZoneConfig
    module: str
    lot: list  # [W, D]
    level: int
    access: str
    households: int
    party_walls: tuple
    party_skip: list
    product: str
    colour_sets: list
    colour_random: list
    params: dict
    display_name: str
    description: str
    render_thumbnail: bool
    service: ServiceSpec | None = None

    def to_dict(self):
        return {
            "name": self.name,
            "design": self.design,
            "zone_key": self.zone_key,
            "zone_kind": self.zone.kind,
            "game_zone": self.zone.game_name,
            "module": self.module,
            "lot": list(self.lot),
            "level": self.level,
            "access": self.access,
            "households": self.households,
            "party_walls": list(self.party_walls),
            "party_skip": [list(p) for p in self.party_skip],
            "budget": list(self.zone.budget),
            "density_floor": float(self.zone.density_floor),
            "crown_allowed": bool(self.zone.crown_allowed),
            "crown_max_m2": float(self.zone.crown_max_m2),
            "max_front_setback_m": float(self.zone.max_front_setback_m),
            "min_coverage_pct": float(self.zone.min_coverage_pct),
            "allow_right_corner": bool(self.zone.allow_right_corner),
            "space_multiplier": int(self.zone.space_multiplier),
            "product": self.product,
            "colour_sets": self.colour_sets,
            "colour_random": list(self.colour_random),
            "params": self.params,
            "display_name": self.display_name,
            "description": self.description,
            "render_thumbnail": bool(self.render_thumbnail),
            "service": None
            if self.service is None
            else {
                "kind": self.service.kind,
                "values": self.service.values,
                "drop": list(self.service.drop),
                "unlock": self.service.unlock,
                "vehicle_points_lot_m": list(self.service.vehicle_points_lot_m),
                "pedestrian_point_lot_m": list(self.service.pedestrian_point_lot_m),
                "thumbnail": bool(self.service.thumbnail),
            },
        }


@dataclass
class PackConfig:
    pack_dir: Path
    pack_id: str
    title: str
    prefix: str
    variation_group: str
    atlas_file: Path
    atlas_build_dir: Path
    designs_dir: Path
    textures_roots: list
    colour_random: list
    colour_sets_by_key: dict
    zones: dict
    roster: list


def _resolve_color_item(item, swatches, base_levels):
    if isinstance(item, (list, tuple)) and len(item) == 3:
        return [round(float(c), 4) for c in item]
    if isinstance(item, str):
        if item in swatches:
            return [round(float(c), 4) for c in swatches[item]]
        raise ConfigError(f"Unknown swatch reference {item!r}")
    if isinstance(item, dict):
        sw_name = item["swatch"]
        if sw_name not in swatches:
            raise ConfigError(f"Unknown swatch reference {sw_name!r}")
        sw = swatches[sw_name]
        base_name = item.get("base", "default")
        base = base_levels.get(base_name, [1.0, 1.0, 1.0])
        k = float(item.get("k", 1.0))
        return [round(min(1.0, float(s) * k / float(b)), 4) for s, b in zip(sw, base)]
    raise ConfigError(f"Invalid palette colour entry: {item!r}")


def _resolve_palette_sets(raw_sets, swatches, base_levels):
    out = {}
    for key, entries in (raw_sets or {}).items():
        resolved = []
        for entry in entries:
            if isinstance(entry, dict) and ("c0" in entry or "c1" in entry or "c2" in entry):
                c0 = _resolve_color_item(entry.get("c0", WHITE), swatches, base_levels)
                c1 = _resolve_color_item(entry.get("c1", WHITE), swatches, base_levels)
                c2 = _resolve_color_item(entry.get("c2", WHITE), swatches, base_levels)
                resolved.append([c0, c1, c2])
            elif isinstance(entry, (list, tuple)) and len(entry) == 3:
                resolved.append([_resolve_color_item(x, swatches, base_levels) for x in entry])
            elif isinstance(entry, (list, tuple)) and len(entry) == 2:
                resolved.append([list(WHITE), _resolve_color_item(entry[0], swatches, base_levels), _resolve_color_item(entry[1], swatches, base_levels)])
            else:
                raise ConfigError(f"Palette {key!r} has malformed entry: {entry!r}")
        out[key] = resolved
    return out


def _humanize_design(design: str) -> str:
    s = re.sub(r"(Left|Right)Corner$", "", design)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", s)
    return s.strip() or design


def load_pack(pack_dir) -> PackConfig:
    pdir = Path(pack_dir).resolve()
    pfile = pdir / "pack.json"
    if not pfile.exists():
        raise ConfigError(f"Missing pack.json in {pdir}")
    raw = json.loads(pfile.read_text(encoding="utf-8"))

    for req in ("pack_id", "title", "prefix"):
        if not raw.get(req):
            raise ConfigError(f"{pfile}: missing required field {req!r}")
    for req in ("zones", "roster"):
        if req not in raw:
            raise ConfigError(f"{pfile}: missing required field {req!r}")

    prefix = str(raw["prefix"])
    if not re.fullmatch(r"[A-Za-z0-9_]+", prefix):
        raise ConfigError(f"{pfile}: prefix {prefix!r} must be alphanumeric/underscore")

    pal = raw.get("palette", {})
    swatches = {k: [float(x) for x in v] for k, v in pal.get("swatches", {}).items()}
    base_levels = {k: [float(x) for x in v] for k, v in pal.get("base_levels", {}).items()}
    base_levels.setdefault("default", [1.0, 1.0, 1.0])
    colour_sets_by_key = _resolve_palette_sets(pal.get("sets", {}), swatches, base_levels)
    colour_random = [int(x) for x in pal.get("random", [2, 4, 5])]

    zones = {}
    for zk, zd in raw["zones"].items():
        kind = zd.get("kind")
        if kind not in VALID_ZONE_KINDS:
            raise ConfigError(f"{pfile}: zone {zk!r} has invalid kind {kind!r}; expected one of {VALID_ZONE_KINDS}")
        party_mode = zd.get("party_mode", "none")
        if party_mode not in ("none", "row"):
            raise ConfigError(f"{pfile}: zone {zk!r} has invalid party_mode {party_mode!r}")
        default_min_cov = 0.0 if kind in ("service", "landmark") else 70.0
        default_space = 8 if kind == "green_industry" else 0
        zones[zk] = ZoneConfig(
            key=zk,
            kind=kind,
            game_name=str(zd.get("game_name", "") or ""),
            base_zone=str(zd.get("base_zone", "") or ""),
            module=str(zd.get("module", "") or ""),
            budget=[int(x) for x in zd.get("budget", DEFAULT_BUDGET)],
            density_floor=float(zd.get("density_floor", 8.0)),
            crown_allowed=bool(zd.get("crown_allowed", False)),
            crown_max_m2=float(zd.get("crown_max_m2", 150.0)),
            party_mode=party_mode,
            max_front_setback_m=float(zd.get("max_front_setback_m", 1.2)),
            min_coverage_pct=float(zd.get("min_coverage_pct", default_min_cov)),
            allow_right_corner=bool(zd.get("allow_right_corner", False)),
            default_lots=[[int(w), int(d)] for w, d in zd.get("default_lots", [])],
            expected_lots=[[int(w), int(d)] for w, d in zd.get("expected_lots", [])],
            space_multiplier=int(zd.get("space_multiplier", default_space)),
            households_by_lot={str(k): int(v) for k, v in zd.get("households_by_lot", {}).items()},
        )

    roster = []
    for item in raw["roster"]:
        zk = item["zone_key"]
        if zk not in zones:
            raise ConfigError(f"{pfile}: roster design {item.get('design')!r} references unknown zone_key {zk!r}")
        z = zones[zk]
        srv_raw = item.get("service")
        srv = None
        if srv_raw:
            srv = ServiceSpec(
                kind=str(srv_raw["kind"]),
                values=dict(srv_raw.get("values", {})),
                drop=list(srv_raw.get("drop", [])),
                unlock=str(srv_raw.get("unlock", "")),
                vehicle_points_lot_m=[[float(x), float(y)] for x, y in srv_raw.get("vehicle_points_lot_m", [])],
                pedestrian_point_lot_m=list(srv_raw.get("pedestrian_point_lot_m", [])),
                thumbnail=bool(srv_raw.get("thumbnail", True)),
            )
        explicit_sets = item.get("colour_sets")
        if explicit_sets is not None:
            resolved_explicit = _resolve_palette_sets({"_": explicit_sets}, swatches, base_levels)["_"]
        else:
            resolved_explicit = []
        design_name = str(item["design"])
        if not re.fullmatch(r"[A-Za-z0-9]+", design_name):
            raise ConfigError(f"{pfile}: design {design_name!r} must be alphanumeric PascalCase (no underscores/spaces)")
        roster.append(
            DesignSpec(
                design=design_name,
                zone_key=zk,
                module=str(item.get("module") or z.module or ""),
                display_name=str(item.get("display_name") or _humanize_design(design_name)),
                description=str(item.get("description") or ""),
                lots=[[int(w), int(d)] for w, d in item.get("lots", [])],
                access=str(item.get("access", "")),
                households=item.get("households"),
                product=str(item.get("product", "")),
                palette_key=str(item.get("palette_key", "")),
                colour_sets=resolved_explicit,
                params=dict(item.get("params", {})),
                omit_lot_suffix=bool(item.get("omit_lot_suffix", False)),
                include_lot_in_name=bool(item.get("include_lot_in_name", False)),
                service=srv,
            )
        )

    tex_roots = []
    for troot in raw.get("textures_roots", []):
        tp = Path(troot)
        tex_roots.append(tp if tp.is_absolute() else (pdir / tp).resolve())

    return PackConfig(
        pack_dir=pdir,
        pack_id=str(raw["pack_id"]),
        title=str(raw["title"]),
        prefix=prefix,
        variation_group=str(raw.get("variation_group") or raw["pack_id"]),
        atlas_file=(pdir / raw.get("atlas_file", "atlas.json")).resolve(),
        atlas_build_dir=(pdir / raw.get("atlas_build_dir", "atlas_build")).resolve(),
        designs_dir=(pdir / raw.get("designs_dir", "designs")).resolve(),
        textures_roots=tex_roots,
        colour_random=colour_random,
        colour_sets_by_key=colour_sets_by_key,
        zones=zones,
        roster=roster,
    )


def _infer_access(d_spec: DesignSpec) -> str:
    if d_spec.access:
        return d_spec.access
    if "RightCorner" in d_spec.design or d_spec.params.get("hand") == "R":
        return "RightCorner"
    if "LeftCorner" in d_spec.design or d_spec.params.get("corner"):
        return "LeftCorner"
    return "Front"


def _resolve_households(d_spec: DesignSpec, zone: ZoneConfig, w: int, d: int) -> int:
    if zone.kind not in ("residential", "mixed"):
        return 0
    lot_key = f"{w}x{d}"
    hh = d_spec.households
    if isinstance(hh, dict):
        if lot_key in hh:
            return int(hh[lot_key])
        if str(d) in hh:
            return int(hh[str(d)])
    elif isinstance(hh, int):
        return hh
    if lot_key in zone.households_by_lot:
        return int(zone.households_by_lot[lot_key])
    return 1


def expand_roster(pack: PackConfig, zones=None, designs=None) -> list[AssetSpec]:
    zone_filter = set(zones) if zones else None
    design_filter = set(designs) if designs else None
    seen_names = set()
    assets = []

    for d_spec in pack.roster:
        if zone_filter and d_spec.zone_key not in zone_filter:
            continue
        if design_filter and d_spec.design not in design_filter:
            continue
        zone = pack.zones[d_spec.zone_key]
        lots = d_spec.lots or zone.default_lots
        if not lots:
            raise ConfigError(f"Design {d_spec.design!r} (zone {zone.key}) has no lots and zone has no default_lots")
        if not d_spec.module:
            raise ConfigError(f"Design {d_spec.design!r} (zone {zone.key}) has no design module")

        access = _infer_access(d_spec)
        if "party_walls" in d_spec.params:
            party_walls = tuple(d_spec.params["party_walls"])
        elif zone.party_mode == "row":
            if access == "LeftCorner":
                party_walls = ("right",)
            elif access == "RightCorner":
                party_walls = ("left",)
            else:
                party_walls = ("left", "right")
        else:
            party_walls = ()
        party_skip = [s for s, k in (((0, 1), "left"), ((0, -1), "right")) if k in party_walls]

        if d_spec.colour_sets:
            csets = d_spec.colour_sets
        elif d_spec.palette_key:
            if d_spec.palette_key not in pack.colour_sets_by_key:
                raise ConfigError(f"Design {d_spec.design!r} references unknown palette_key {d_spec.palette_key!r}")
            csets = pack.colour_sets_by_key[d_spec.palette_key]
        else:
            csets = []

        is_ploppable = zone.kind in ("service", "landmark")
        for w, d in lots:
            if is_ploppable and not d_spec.include_lot_in_name:
                name = f"{pack.prefix}{d_spec.design}"
            elif d_spec.omit_lot_suffix or w > 9 or d > 9:
                name = f"{pack.prefix}{d_spec.design}"
            else:
                name = f"{pack.prefix}{d_spec.design}_L1_{w}x{d}"

            if name in seen_names:
                raise ConfigError(f"Duplicate asset name generated: {name!r}")
            seen_names.add(name)

            hh = _resolve_households(d_spec, zone, w, d)
            render_thumb = bool(d_spec.service.thumbnail) if d_spec.service else is_ploppable
            assets.append(
                AssetSpec(
                    name=name,
                    design=d_spec.design,
                    zone_key=zone.key,
                    zone=zone,
                    module=d_spec.module,
                    lot=[int(w), int(d)],
                    level=1,
                    access=access,
                    households=hh,
                    party_walls=party_walls,
                    party_skip=party_skip,
                    product=d_spec.product,
                    colour_sets=csets,
                    colour_random=list(pack.colour_random),
                    params=dict(d_spec.params),
                    display_name=d_spec.display_name,
                    description=d_spec.description,
                    render_thumbnail=render_thumb,
                    service=d_spec.service,
                )
            )
    return assets


def validate_pack_hygiene(pack: PackConfig, assets: list[AssetSpec]):
    """Return (errors, warnings) covering roster rules, products, corners, and lot coverage."""
    errors = []
    warnings = []

    by_zone = {}
    for a in assets:
        by_zone.setdefault(a.zone_key, []).append(a)
        if a.access not in ("Front", "LeftCorner", "RightCorner"):
            errors.append(f"{a.name}: invalid access {a.access!r}")
        if a.access == "RightCorner" and not a.zone.allow_right_corner:
            errors.append(
                f"{a.name}: explicit RightCorner is forbidden in zone {a.zone_key} "
                "(CS2 mirrors LeftCorner automatically; set allow_right_corner=true only if intentional)"
            )
        if a.zone.kind == "green_industry":
            if not a.product:
                errors.append(f"{a.name}: green_industry asset is missing 'product'")
            elif a.product not in CLEAN_PRODUCTS:
                errors.append(
                    f"{a.name}: product {a.product!r} is not in CLEAN_PRODUCTS ({sorted(CLEAN_PRODUCTS)})"
                )
        if a.zone.kind in ("service", "landmark") and not a.service:
            warnings.append(f"{a.name}: zone kind is {a.zone.kind!r} but no 'service' wiring spec is defined")

    for zk, zone in pack.zones.items():
        z_assets = by_zone.get(zk, [])
        if not z_assets:
            continue
        present_lots = {tuple(a.lot) for a in z_assets}
        if zone.expected_lots:
            missing_lots = [tuple(x) for x in zone.expected_lots if tuple(x) not in present_lots]
            if missing_lots:
                warnings.append(f"Zone {zk}: missing expected_lots {missing_lots}")
        if zone.party_mode == "row" and not any(a.access == "LeftCorner" for a in z_assets):
            warnings.append(f"Zone {zk}: party_mode='row' has 0 LeftCorner designs (block ends will show bare party walls)")

    return errors, warnings
