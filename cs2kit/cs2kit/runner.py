"""Orchestrator CLI and workflow engine for cs2kit."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from .atlas import MAPS, build_atlas, check_atlas
from .config import ConfigError, PackConfig, expand_roster, load_pack
from .preflight import run_preflight
from .review import approved_asset_names, update_review, write_review_files
from .setup import run_setup_cli
from .sheets import build_building_sheet, build_zone_sheets

DEFAULT_BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"


def _blender_exe() -> str:
    return os.environ.get("CS2KIT_BLENDER", DEFAULT_BLENDER)


def _split_csv(val: str | None):
    if not val:
        return None
    return [x.strip() for x in val.split(",") if x.strip()]


def _chunk_round_robin(items: list, n_workers: int) -> list[list]:
    n = max(1, min(int(n_workers), len(items)))
    buckets = [[] for _ in range(n)]
    for i, item in enumerate(items):
        buckets[i % n].append(item)
    return [b for b in buckets if b]


def _write_bake_report(run_dir: Path, pack: PackConfig, ordered_names: list[str], results: dict):
    lines = [f"# Bake report: {pack.title} (`{pack.pack_id}`, run `{run_dir.name}`)", ""]
    passed = sum(1 for n in ordered_names if results.get(n, {}).get("pass"))
    failed = len(ordered_names) - passed
    lines.append(f"**Summary:** {passed}/{len(ordered_names)} PASS, {failed} FAIL.")
    lines.append("")
    for n in ordered_names:
        res = results.get(n, {"pass": False, "fail": ["no worker result"]})
        status = "PASS" if res.get("pass") else "FAIL"
        lines.append(f"## {n}: {status}")
        lines.append("")
        if res.get("pass") and res.get("record"):
            rec = res["record"]
            aud = rec["audit"]
            lods = rec["lods"]
            lines.append(
                f"- Triangles (LOD0/1/2): {lods['main']['triangles']:,} / {lods['_LOD1']['triangles']:,} / {lods['_LOD2']['triangles']:,} "
                f"({rec['tris_per_m2']} / m2)"
            )
            lines.append(
                f"- Height: {aud['height_m']} m | Front setback: {aud['front_m']} m | Coverage: {aud['occupied_pct']}% | "
                f"Eaves: {aud['roof_levels_m']} m | Slits: {aud['gaps_m2']} m2"
            )
            for w in aud.get("warnings", []):
                lines.append(f"- Warning: {w}")
        else:
            for err in res.get("fail", []):
                lines.append(f"- FAIL: {err}")
        lines.append("")
    (run_dir / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def _run_preview_workers(pack: PackConfig, run_dir: Path, passed_assets: list[dict], workers: int):
    if not passed_assets:
        return
    blender = _blender_exe()
    preview_py = Path(__file__).resolve().parent / "blender_preview.py"
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    chunks = _chunk_round_robin(passed_assets, workers)
    procs = []
    plan_files = []
    for i, chunk in enumerate(chunks):
        plan_file = run_dir / f"_worker_preview_{i}.json"
        plan_file.write_text(
            json.dumps(
                {
                    "atlas_build_dir": str(pack.atlas_build_dir),
                    "out_dir": str(run_dir),
                    "assets": chunk,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        plan_files.append(plan_file)
        proc = subprocess.Popen(
            [blender, "-b", "--python-exit-code", "2", "--python", str(preview_py), "--", str(plan_file)],
            cwd=str(pack.pack_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        procs.append((i, proc))

    for i, proc in procs:
        out, err = proc.communicate()
        (logs_dir / f"preview_worker_{i}.log").write_text(out + "\n--- stderr ---\n" + err, encoding="utf-8")
        if proc.returncode != 0:
            raise RuntimeError(f"Preview worker {i} failed (exit {proc.returncode}); see {logs_dir / f'preview_worker_{i}.log'}")

    for pf in plan_files:
        pf.unlink(missing_ok=True)

    for a in passed_assets:
        build_building_sheet(run_dir, a["name"])
    build_zone_sheets(run_dir, passed_assets)


def bake_pack(
    pack: PackConfig,
    zones=None,
    designs=None,
    workers: int = 1,
    no_preview: bool = False,
    skip_preflight: bool = False,
) -> Path:
    """Verify atlas, run preflight, bake/audit in parallel Blender workers, and render preview sheets."""
    layout_path = pack.atlas_build_dir / "atlas_layout.json"
    if not layout_path.exists():
        raise ConfigError(f"Atlas not compiled yet ({layout_path} missing). Run `python -m cs2kit atlas {pack.pack_dir}` first.")
    atlas_errs = check_atlas(pack)
    if atlas_errs:
        raise ConfigError("Atlas check failed: " + "; ".join(atlas_errs))

    if not skip_preflight:
        pre = run_preflight(pack, zones=zones, designs=designs)
        if pre["failed"] > 0 or pre["global_errors"]:
            details = pre["global_errors"] + [
                f"{n}: {'; '.join(r['errors'])}" for n, r in pre["assets"].items() if not r["pass"]
            ]
            raise ConfigError("Preflight failed:\n  " + "\n  ".join(details))

    assets = expand_roster(pack, zones=zones, designs=designs)
    if not assets:
        raise ConfigError("No assets matched the requested zone/design filter.")

    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    run_dir = pack.pack_dir / "runs" / stamp
    while run_dir.exists():
        stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        run_dir = pack.pack_dir / "runs" / stamp
    run_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    asset_dicts = [a.to_dict() for a in assets]
    chunks = _chunk_round_robin(asset_dicts, workers)
    blender = _blender_exe()
    bake_py = Path(__file__).resolve().parent / "blender_bake.py"

    procs = []
    temp_files = []
    for i, chunk in enumerate(chunks):
        plan_file = run_dir / f"_worker_bake_{i}.json"
        res_file = run_dir / f"_worker_bake_{i}_result.json"
        plan_file.write_text(
            json.dumps(
                {
                    "pack_id": pack.pack_id,
                    "designs_dir": str(pack.designs_dir),
                    "atlas_layout_path": str(layout_path),
                    "out_dir": str(run_dir),
                    "result_path": str(res_file),
                    "assets": chunk,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        temp_files.extend([plan_file, res_file])
        proc = subprocess.Popen(
            [blender, "-b", "--python-exit-code", "2", "--python", str(bake_py), "--", str(plan_file)],
            cwd=str(pack.pack_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        procs.append((i, proc, res_file))

    merged_results = {}
    for i, proc, res_file in procs:
        out, err = proc.communicate()
        (logs_dir / f"bake_worker_{i}.log").write_text(out + "\n--- stderr ---\n" + err, encoding="utf-8")
        if res_file.exists():
            merged_results.update(json.loads(res_file.read_text(encoding="utf-8")))
        elif proc.returncode != 0:
            raise RuntimeError(f"Bake worker {i} crashed (exit {proc.returncode}); see {logs_dir / f'bake_worker_{i}.log'}")

    for tf in temp_files:
        tf.unlink(missing_ok=True)

    ordered_names = [a["name"] for a in asset_dicts]
    passed_records = [merged_results[n]["record"] for n in ordered_names if merged_results.get(n, {}).get("pass")]
    passed_names = {r["name"] for r in passed_records}
    passed_asset_dicts = [a for a in asset_dicts if a["name"] in passed_names]

    manifest = {
        "pack_id": pack.pack_id,
        "title": pack.title,
        "prefix": pack.prefix,
        "run": run_dir.name,
        "total": len(ordered_names),
        "passed": len(passed_records),
        "failed": len(ordered_names) - len(passed_records),
        "assets": passed_records,
        "asset_specs": {a["name"]: a for a in asset_dicts},
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (run_dir / "audit.json").write_text(
        json.dumps({n: merged_results.get(n, {}) for n in ordered_names}, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_bake_report(run_dir, pack, ordered_names, merged_results)
    write_review_files(run_dir, pack.pack_id, passed_records)

    if not no_preview and passed_asset_dicts:
        _run_preview_workers(pack, run_dir, passed_asset_dicts, workers)

    return run_dir


def stage_run(pack: PackConfig, run_dir: Path) -> Path:
    """Stage approved assets from `run_dir` with dynamic atlas-owner promotion."""
    run_dir = Path(run_dir).resolve()
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    approved = approved_asset_names(run_dir)
    if not approved:
        raise ConfigError(f"No designs approved in {run_dir / 'REVIEW.json'}; run `review` first.")

    good = [rec for rec in manifest["assets"] if rec["name"] in approved]
    if not good:
        raise ConfigError(f"No passing & approved assets found in {run_dir}.")

    atlas_dir = pack.atlas_build_dir
    for suf in ("", "_LOD1", "_LOD2"):
        for mp in MAPS:
            if not (atlas_dir / f"ATLAS{suf}_{mp}.png").exists():
                raise ConfigError(f"Missing atlas image {atlas_dir / f'ATLAS{suf}_{mp}.png'}")

    # Dynamic Atlas-Owner Promotion: first passing+approved asset owns the 15 PNGs
    owner = good[0]["name"]
    dst = pack.pack_dir / "imports" / f"1_READY_{pack.pack_id}_{run_dir.name}_{len(good)}"
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True, exist_ok=True)

    owner_dir = dst / owner
    owner_dir.mkdir(parents=True, exist_ok=True)
    owner_files = []
    for suf in ("", "_LOD1", "_LOD2"):
        for mp in MAPS:
            src_png = atlas_dir / f"ATLAS{suf}_{mp}.png"
            dst_name = f"{owner}{suf}_{mp}.png"
            shutil.copy2(src_png, owner_dir / dst_name)
            owner_files.append((suf, mp, dst_name))

    for rec in good:
        name = rec["name"]
        src_folder = run_dir / name
        dst_folder = dst / name
        dst_folder.mkdir(parents=True, exist_ok=True)
        for fbx in sorted(src_folder.glob("*.fbx")):
            shutil.copy2(fbx, dst_folder / fbx.name)
        if name != owner:
            shared = {
                f"{name}{suf}_{mp}.png": f"../{owner}/{owner_name}"
                for suf, mp, owner_name in owner_files
            }
            (dst_folder / "settings.json").write_text(json.dumps({"sharedAssets": shared}, indent=2) + "\n", encoding="utf-8")

    # Copy service/landmark thumbnails if present
    thumbs_src = run_dir / "thumbnails"
    thumbs_dst = dst / "thumbnails"
    pack_thumbs = pack.pack_dir / "thumbnails"
    if thumbs_src.exists():
        for rec in good:
            tp = thumbs_src / f"{rec['name']}.png"
            if tp.exists():
                thumbs_dst.mkdir(parents=True, exist_ok=True)
                pack_thumbs.mkdir(parents=True, exist_ok=True)
                shutil.copy2(tp, thumbs_dst / tp.name)
                shutil.copy2(tp, pack_thumbs / tp.name)

    (dst / "IMPORT-LIST.txt").write_text("\n".join(r["name"] for r in good) + "\n", encoding="utf-8")

    asset_specs = manifest.get("asset_specs", {})
    staged_specs = {}
    for rec in good:
        n = rec["name"]
        if n in asset_specs:
            staged_specs[n] = asset_specs[n]

    pack_manifest = {
        "pack_id": pack.pack_id,
        "title": pack.title,
        "prefix": pack.prefix,
        "variation_group": pack.variation_group,
        "colour_random": list(pack.colour_random),
        "texture_owner": owner,
        "run": run_dir.name,
        "assets": staged_specs,
    }
    (dst / "pack_manifest.json").write_text(json.dumps(pack_manifest, indent=2) + "\n", encoding="utf-8")

    reg_path = pack.pack_dir / "staged_registry.json"
    if reg_path.exists():
        reg = json.loads(reg_path.read_text(encoding="utf-8"))
    else:
        reg = {
            "pack_id": pack.pack_id,
            "title": pack.title,
            "prefix": pack.prefix,
            "variation_group": pack.variation_group,
            "colour_random": list(pack.colour_random),
            "assets": {},
        }
    reg["title"] = pack.title
    reg["prefix"] = pack.prefix
    reg["variation_group"] = pack.variation_group
    reg["colour_random"] = list(pack.colour_random)
    reg["assets"].update(staged_specs)
    reg_path.write_text(json.dumps(reg, indent=2) + "\n", encoding="utf-8")

    return dst


def init_pack(dest_dir: Path, pack_id: str, title: str, prefix: str) -> Path:
    """Scaffold a new pack directory ready for atlas/preflight/bake."""
    dest = Path(dest_dir).resolve()
    (dest / "designs").mkdir(parents=True, exist_ok=True)
    (dest / "designs" / "__init__.py").write_text("", encoding="utf-8")

    starter_py = '''"""Starter rowhouse module for newly initialized pack."""
from cs2kit.kit import Mesh, finish, gable_roof, gable_wall, porch, style, wall
from cs2kit.mesh import party

DEFAULT = dict(storeys=2, wall="BrickRed", roof_mat="SlateDark", door="Green")


def build(lod, W=1, D=3, **variant):
    v = dict(DEFAULT, **variant)
    X = 4.0 * W - 0.01
    yF = -4.0 * D + 1.05
    yR = 4.0 * D - 0.6
    top = 6.8 if v["storeys"] == 2 else 9.8
    win = [(0.9, 1.0, 2.7), (0.85, 3.8, 5.4)]
    if v["storeys"] == 3:
        win.append((0.8, 6.9, 8.3))
    st = style(top, [(0.0, top, v["wall"])], win, belts=(3.4,), plinth=(0.65, 0.05, "StoneBase"), corners=False, frieze=0.25)
    trim = dict(door=v["door"], masonry="Dressed", reveal=v["wall"], lean=True)
    m, g = Mesh(), Mesh()

    bays = [-2.2, 0.0, 2.2] if W == 1 else [-6.0, -3.5, -1.0, 1.5, 4.0, 6.0]
    door = (bays[1], 1.0, 2.75)
    wall(m, g, st, (-X, yF), (X, yF), "-", "-", bays, lod, door=door, trim=trim)
    wall(m, g, st, (X, yR), (-X, yR), "-", "-", bays[::-1], lod, trim=trim)
    party(m, (-X, yR), (-X, yF), 0.0, top, v["wall"])
    party(m, (X, yF), (X, yR), 0.0, top, v["wall"])

    porch(m, door[0] - 1.3, door[0] + 1.3, yF, 0.65, lod, zf=0.25, zt=3.0, mat=v["roof_mat"], rail=False, open_sides=())

    zr = top + 2.4
    gable_wall(m, g, (-X, yF), (X, yF), top, zr, lod, v["wall"], trim=trim)
    gable_wall(m, g, (X, yR), (-X, yR), top, zr, lod, v["wall"], trim=trim)
    gable_roof(m, -X, X, yF, yR, top, zr, lod, mat=v["roof_mat"], sides=("p", "p"))
    finish(m, g)
'''
    (dest / "designs" / "starter_row.py").write_text(starter_py, encoding="utf-8")

    atlas_json = {
        "sizes": {"main": 4096, "_LOD1": 2048, "_LOD2": 1024},
        "gutter_px_main": 16,
        "tiles": [
            {"key": "BrickRed", "kind": "flat_paint", "color": [146, 86, 74], "px": [512, 512], "metres": [2.4, 2.4], "tint_channel": 1, "lift_target_rgb": [228, 224, 218]},
            {"key": "StoneBase", "kind": "stucco", "color": [142, 140, 134], "px": [512, 512], "metres": [2.4, 2.4]},
            {"key": "Dressed", "kind": "stucco", "color": [206, 200, 188], "px": [512, 512], "metres": [2.4, 2.4]},
            {"key": "TrimWhite", "kind": "flat_paint", "color": [226, 224, 218], "px": [256, 256], "metres": [3.0, 3.0], "tint_channel": 2},
            {"key": "SlateDark", "kind": "shingle_courses", "color": [68, 72, 78], "px": [512, 512], "metres": [2.4, 2.4], "ncol": 8, "nrow": 8},
            {"key": "Deck", "kind": "board_batten", "color": [132, 124, 114], "px": [256, 256], "metres": [2.0, 2.0]},
            {"key": "Black", "kind": "flat_paint", "color": [32, 34, 36], "px": [256, 256], "metres": [2.0, 2.0]},
            {"key": "Green", "kind": "flat_paint", "color": [48, 78, 62], "px": [256, 256], "metres": [2.0, 2.0]},
        ],
        "signs": [],
    }
    (dest / "atlas.json").write_text(json.dumps(atlas_json, indent=2) + "\n", encoding="utf-8")

    pack_json = {
        "pack_id": pack_id,
        "title": title,
        "prefix": prefix,
        "variation_group": pack_id,
        "textures_roots": [],
        "palette": {
            "sets": {
                "brick": [
                    [[1.0, 1.0, 1.0], [0.76, 0.56, 0.52], [0.96, 0.95, 0.92]],
                    [[1.0, 1.0, 1.0], [0.68, 0.54, 0.48], [0.92, 0.90, 0.85]],
                ]
            },
            "random": [2, 4, 5],
        },
        "zones": {
            "ZL1": {
                "game_name": f"{title} Low Residential",
                "kind": "residential",
                "base_zone": "Residential Low",
                "module": "starter_row",
                "party_mode": "row",
                "default_lots": [[1, 3]],
            }
        },
        "roster": [
            {
                "design": "StarterRow",
                "zone_key": "ZL1",
                "display_name": "Starter Rowhouse",
                "households": 2,
                "palette_key": "brick",
                "params": {"storeys": 2},
            }
        ],
    }
    (dest / "pack.json").write_text(json.dumps(pack_json, indent=2) + "\n", encoding="utf-8")
    (dest / ".gitignore").write_text("runs/\nimports/\natlas_build/\n__pycache__/\n", encoding="utf-8")
    return dest


def cmd_status(pack: PackConfig):
    assets = expand_roster(pack)
    by_zone = {}
    for a in assets:
        by_zone.setdefault(a.zone_key, []).append(a)
    print(f"Pack: {pack.title} ({pack.pack_id}) | Prefix: {pack.prefix} | Total assets: {len(assets)}")
    for zk, z in pack.zones.items():
        items = by_zone.get(zk, [])
        designs = len({a.design for a in items})
        print(f"  {zk:<5} {z.kind:<15} {z.game_name or '(ploppable)':<30} designs={designs:<3} assets={len(items)}")
    atlas_ok = (pack.atlas_build_dir / "atlas_layout.json").exists()
    print(f"Atlas compiled: {'YES' if atlas_ok else 'NO'} ({pack.atlas_build_dir})")
    runs_dir = pack.pack_dir / "runs"
    if runs_dir.exists():
        runs = sorted((d.name for d in runs_dir.iterdir() if d.is_dir()), reverse=True)
        print(f"Runs ({len(runs)}): {', '.join(runs[:5])}")
    imports_dir = pack.pack_dir / "imports"
    if imports_dir.exists():
        ready = sorted((d.name for d in imports_dir.iterdir() if d.is_dir() and d.name.startswith("1_READY_")), reverse=True)
        print(f"Ready imports: {', '.join(ready) or 'none'}")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="cs2kit", description="Cities: Skylines II pack-agnostic asset pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_atlas = sub.add_parser("atlas", help="Compile or check pack texture atlas")
    p_atlas.add_argument("pack_dir")
    p_atlas.add_argument("--check", action="store_true")

    p_pre = sub.add_parser("preflight", help="Pure-Python geometry and rulebook preflight (<2s)")
    p_pre.add_argument("pack_dir")
    p_pre.add_argument("--zones", help="Comma-separated zone keys")
    p_pre.add_argument("--designs", help="Comma-separated design names")

    p_bake = sub.add_parser("bake", help="Bake, validate, audit, and preview assets in Blender")
    p_bake.add_argument("pack_dir")
    p_bake.add_argument("--zones")
    p_bake.add_argument("--designs")
    p_bake.add_argument("--workers", type=int, default=2)
    p_bake.add_argument("--no-preview", action="store_true")
    p_bake.add_argument("--skip-preflight", action="store_true")

    p_prev = sub.add_parser("preview", help="Render previews and zone contact sheets for an existing run")
    p_prev.add_argument("pack_dir")
    p_prev.add_argument("--run", required=True)
    p_prev.add_argument("--workers", type=int, default=2)

    p_rev = sub.add_parser("review", help="Approve or reject designs in a run's REVIEW.json")
    p_rev.add_argument("pack_dir")
    p_rev.add_argument("--run", required=True)
    p_rev.add_argument("--approve", help="Comma-separated designs, zones, or asset names")
    p_rev.add_argument("--reject", help="Comma-separated designs, zones, or asset names")
    p_rev.add_argument("--approve-all", action="store_true")
    p_rev.add_argument("--note", default="")

    p_stage = sub.add_parser("stage", help="Stage passing & approved assets into imports/1_READY_*")
    p_stage.add_argument("pack_dir")
    p_stage.add_argument("--run", required=True)

    p_setup = sub.add_parser("setup", help="Archive duplicates (--pre-import) and patch imported CS2 prefabs")
    p_setup.add_argument("pack_dir")
    p_setup.add_argument("--pre-import", dest="pre_import", help="Staged 1_READY_* folder to clear old duplicates for")
    p_setup.add_argument("--manifest", help="Explicit pack_manifest.json (defaults to staged_registry.json)")
    p_setup.add_argument("--imported-data", dest="imported_data", help="Override CS2 ImportedData directory")
    p_setup.add_argument("--backups-dir", dest="backups_dir", help="Override archive directory for replaced files")
    p_setup.add_argument("--guids", help="Path to vanilla_prefab_guids.json")
    p_setup.add_argument("--dry-run", action="store_true")

    p_stat = sub.add_parser("status", help="Show pack status, runs, and staged folders")
    p_stat.add_argument("pack_dir")

    p_init = sub.add_parser("init-pack", help="Scaffold a new pack directory")
    p_init.add_argument("dest_dir")
    p_init.add_argument("--id", required=True, dest="pack_id")
    p_init.add_argument("--title", required=True)
    p_init.add_argument("--prefix", required=True)

    args = parser.parse_args(argv)

    if args.cmd == "init-pack":
        dest = init_pack(Path(args.dest_dir), args.pack_id, args.title, args.prefix)
        print(f"Initialized pack at {dest}")
        return 0

    pack = load_pack(args.pack_dir)

    if args.cmd == "atlas":
        if not args.check:
            out = build_atlas(pack)
            print(f"Built atlas in {out}")
        errs = check_atlas(pack)
        if errs:
            for e in errs:
                print(f"ATLAS FAIL: {e}")
            return 1
        print("Atlas check PASS (Rule 16 gutters + Rule 27 ControlMask verified)")
        return 0

    if args.cmd == "preflight":
        res = run_preflight(pack, zones=_split_csv(args.zones), designs=_split_csv(args.designs))
        for w in res["warnings"]:
            print(f"WARN: {w}")
        for e in res["global_errors"]:
            print(f"FAIL: {e}")
        for name, r in res["assets"].items():
            for w in r["warnings"]:
                print(f"WARN {name}: {w}")
            if not r["pass"]:
                print(f"FAIL {name}: {' | '.join(r['errors'])}")
        print(f"Preflight: {res['passed']}/{res['total']} PASS in {res['elapsed_s']}s")
        return 0 if (res["failed"] == 0 and not res["global_errors"]) else 1

    if args.cmd == "bake":
        run_dir = bake_pack(
            pack,
            zones=_split_csv(args.zones),
            designs=_split_csv(args.designs),
            workers=args.workers,
            no_preview=args.no_preview,
            skip_preflight=args.skip_preflight,
        )
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        print(f"Bake complete: {manifest['passed']}/{manifest['total']} PASS -> {run_dir}")
        return 0 if manifest["failed"] == 0 else 1

    if args.cmd == "preview":
        run_dir = pack.pack_dir / "runs" / args.run
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        specs = manifest.get("asset_specs", {})
        assets = [specs[r["name"]] for r in manifest["assets"] if r["name"] in specs]
        _run_preview_workers(pack, run_dir, assets, args.workers)
        print(f"Previews and sheets written to {run_dir}")
        return 0

    if args.cmd == "review":
        run_dir = pack.pack_dir / "runs" / args.run
        if args.reject:
            res = update_review(run_dir, _split_csv(args.reject) or (), verdict="REDO", note=args.note)
        else:
            res = update_review(
                run_dir,
                _split_csv(args.approve) or (),
                verdict="PASS",
                note=args.note,
                approve_all=args.approve_all,
            )
        print(f"Updated {res['matched_designs']}/{res['total_designs']} designs -> {res['verdict']} ({run_dir / 'REVIEW.md'})")
        return 0

    if args.cmd == "stage":
        run_dir = pack.pack_dir / "runs" / args.run
        dst = stage_run(pack, run_dir)
        print(f"Staged ready import -> {dst}")
        return 0

    if args.cmd == "setup":
        return run_setup_cli(pack, args)

    if args.cmd == "status":
        cmd_status(pack)
        return 0

    return 1
