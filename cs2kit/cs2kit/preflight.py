"""Fast pure-Python preflight gate (<2s, zero Blender dependency)."""
import importlib
import json
import sys
import time
from pathlib import Path

from .config import ConfigError, PackConfig, expand_roster, validate_pack_hygiene
from .math_compat import Vector
from .mesh import capture_meshes
from .rules import RuleError


def _poly_planarity_err(pts) -> float:
    if len(pts) <= 3:
        return 0.0
    p0 = Vector(pts[0])
    nrm = Vector((0.0, 0.0, 0.0))
    offsets = [Vector(p) - p0 for p in pts]
    for a, b in zip(offsets, offsets[1:] + offsets[:1]):
        nrm += a.cross(b)
    if nrm.length < 1e-9:
        return 999.0
    n = nrm.normalized()
    return max(abs(pt.dot(n)) for pt in offsets)


def _poly_area(pts) -> float:
    if len(pts) < 3:
        return 0.0
    p0 = Vector(pts[0])
    total = Vector((0.0, 0.0, 0.0))
    for i in range(1, len(pts) - 1):
        a = Vector(pts[i]) - p0
        b = Vector(pts[i + 1]) - p0
        total += a.cross(b)
    return 0.5 * total.length


def _known_materials(pack: PackConfig) -> set[str]:
    layout_path = pack.atlas_build_dir / "atlas_layout.json"
    if layout_path.exists():
        lay = json.loads(layout_path.read_text(encoding="utf-8"))
        return set(lay["lods"]["main"].keys())
    if pack.atlas_file.exists():
        raw = json.loads(pack.atlas_file.read_text(encoding="utf-8"))
        return {t["key"] for t in raw.get("tiles", [])} | {s["key"] for s in raw.get("signs", [])}
    return set()


def load_design_module(pack: PackConfig, module_name: str):
    designs_dir = pack.designs_dir.resolve()
    dstr = str(designs_dir)
    if dstr not in sys.path:
        sys.path.insert(0, dstr)
    pkg_name = f"_cs2kit_designs_{pack.pack_id}"
    if pkg_name not in sys.modules:
        pkg_spec = importlib.util.spec_from_file_location(
            pkg_name,
            designs_dir / "__init__.py" if (designs_dir / "__init__.py").exists() else None,
            submodule_search_locations=[dstr],
        )
        if pkg_spec is not None:
            pkg_mod = importlib.util.module_from_spec(pkg_spec)
            pkg_mod.__path__ = [dstr]
            sys.modules[pkg_name] = pkg_mod
            if pkg_spec.loader is not None and (designs_dir / "__init__.py").exists():
                pkg_spec.loader.exec_module(pkg_mod)
    full_name = f"{pkg_name}.{module_name}"
    if full_name in sys.modules:
        return importlib.reload(sys.modules[full_name])
    spec = importlib.util.spec_from_file_location(full_name, designs_dir / f"{module_name}.py")
    if spec is None or spec.loader is None:
        raise ConfigError(f"Cannot load design module {module_name!r} from {pack.designs_dir}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = mod
    spec.loader.exec_module(mod)
    return mod


def check_asset_geometry(pack: PackConfig, asset, mod, known_mats: set[str]):
    """Run all 3 LODs of an AssetSpec in pure Python and return (errors, warnings, stats)."""
    errors = []
    warnings = []
    w_cells, d_cells = asset.lot
    half_x = 4.0 * w_cells
    half_y = 4.0 * d_cells
    lod_tris = {}
    front_m = None
    height_m = 0.0

    for lod in (0, 1, 2):
        kwargs = dict(asset.params)
        kwargs["W"] = w_cells
        kwargs["D"] = d_cells
        try:
            with capture_meshes() as captured:
                mod.build(lod, **kwargs)
        except RuleError as exc:
            errors.append(f"LOD{lod} {exc}")
            continue
        except Exception as exc:
            errors.append(f"LOD{lod} build crash ({type(exc).__name__}: {exc})")
            continue

        if len(captured) != 1:
            errors.append(f"LOD{lod}: expected finish(m, g) to be called once, got {len(captured)}")
            continue

        body, win = captured[0]
        raw_tris = sum(max(0, len(f) - 2) for f in body.f) + sum(max(0, len(f) - 2) for f in win.f)
        lod_tris[lod] = raw_tris

        if known_mats:
            unknown = sorted(set(body.mats) - known_mats)
            if unknown:
                errors.append(f"LOD{lod}: unknown atlas material(s) {unknown}")

        # Bounds check across body and windows (+/- 2 mm)
        for label, msh in (("body", body), ("windows", win)):
            if not msh.v:
                continue
            xs = [v[0] for v in msh.v]
            ys = [v[1] for v in msh.v]
            zs = [v[2] for v in msh.v]
            lo_x, hi_x = min(xs), max(xs)
            lo_y, hi_y = min(ys), max(ys)
            lo_z, hi_z = min(zs), max(zs)
            if lo_x < -half_x - 0.002 or hi_x > half_x + 0.002:
                errors.append(f"LOD{lod} {label}: X bounds [{lo_x:.3f}, {hi_x:.3f}] exceed lot +/-{half_x:.2f}")
            if lo_y < -half_y - 0.002 or hi_y > half_y + 0.002:
                errors.append(f"LOD{lod} {label}: Y bounds [{lo_y:.3f}, {hi_y:.3f}] exceed lot +/-{half_y:.2f}")
            if lo_z < -0.002:
                errors.append(f"LOD{lod} {label}: lowest Z {lo_z:.4f} drops below ground (-0.002)")
            if lod == 0 and label == "body":
                height_m = round(hi_z, 2)
                tall_y = [v[1] for v in msh.v if v[2] > 2.0]
                if tall_y:
                    front_m = round(min(tall_y) + half_y, 3)
                    if front_m > asset.zone.max_front_setback_m + 1e-3:
                        errors.append(
                            f"Rule 29 (front setback): main front at {front_m:.2f} m from street > max {asset.zone.max_front_setback_m:.2f} m"
                        )

        # Degenerate and non-planar face checks
        zero_faces = 0
        nonplanar_faces = 0
        for label, msh in (("body", body), ("windows", win)):
            for f in msh.f:
                pts = [msh.v[i] for i in f]
                if _poly_area(pts) <= 1e-8:
                    zero_faces += 1
                elif _poly_planarity_err(pts) > 0.0005:
                    nonplanar_faces += 1
        if zero_faces:
            errors.append(f"LOD{lod}: {zero_faces} degenerate zero-area face(s)")
        if nonplanar_faces:
            errors.append(f"LOD{lod}: {nonplanar_faces} non-planar polygon(s) (> 0.5 mm)")

        if raw_tris > asset.zone.budget[lod]:
            warnings.append(
                f"LOD{lod}: raw untiled triangles ({raw_tris:,}) already exceed budget ({asset.zone.budget[lod]:,})"
            )

    return errors, warnings, {"raw_tris": lod_tris, "front_m": front_m, "height_m": height_m}


def run_preflight(pack: PackConfig, zones=None, designs=None) -> dict:
    t0 = time.perf_counter()
    assets = expand_roster(pack, zones=zones, designs=designs)
    hygiene_errors, hygiene_warnings = validate_pack_hygiene(pack, assets)
    known_mats = _known_materials(pack)

    mod_cache = {}
    asset_results = {}
    total_fail = 0

    for a in assets:
        if a.module not in mod_cache:
            try:
                mod_cache[a.module] = load_design_module(pack, a.module)
            except Exception as exc:
                mod_cache[a.module] = exc

        mod_or_err = mod_cache[a.module]
        if isinstance(mod_or_err, Exception):
            errs = [f"Failed loading module {a.module!r}: {mod_or_err}"]
            warns = []
            stats = {}
        else:
            errs, warns, stats = check_asset_geometry(pack, a, mod_or_err, known_mats)

        # Attach any asset-specific hygiene errors
        prefix_match = f"{a.name}: "
        for he in hygiene_errors:
            if he.startswith(prefix_match):
                errs.append(he[len(prefix_match) :])

        if errs:
            total_fail += 1
        asset_results[a.name] = {"pass": not errs, "errors": errs, "warnings": warns, "stats": stats}

    # Global hygiene errors not tied to a single asset name prefix
    matched = {f"{a.name}: " for a in assets}
    global_errors = [he for he in hygiene_errors if not any(he.startswith(p) for p in matched)]
    elapsed = round(time.perf_counter() - t0, 3)

    return {
        "pack_id": pack.pack_id,
        "total": len(assets),
        "passed": len(assets) - total_fail,
        "failed": total_fail,
        "elapsed_s": elapsed,
        "global_errors": global_errors,
        "warnings": hygiene_warnings,
        "assets": asset_results,
    }
