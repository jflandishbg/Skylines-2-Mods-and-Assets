"""Run-level consolidated review table (REVIEW.json + REVIEW.md) replacing per-building boilerplate."""
import json
from pathlib import Path

CHECKLIST = [
    ("composition", "One composition: blocks touch/overlap with no slits; wings step cleanly"),
    ("grounded", "Grounded: porticos, pavilions and bays stand on walls to ground"),
    ("all_sides", "Every camera-facing side has windows and trim (only party walls bare)"),
    ("roofs", "Clean roofs: no slivers, gaps, or pile-up of eave heights"),
    ("hierarchy", "Hierarchy reads: base, main floors, roof; front door is obvious"),
    ("style", "Reads as its architectural style and Rule 20 material family"),
    ("far_lods", "Far views (LOD1, LOD2) keep the outline and roofline"),
    ("standalone", "Standalone rules: no props, water, benches, or needle spires"),
]


def _render_markdown(data: dict) -> str:
    lines = [
        f"# Review: {data['pack_id']} ({data['run']})",
        "",
        "Approve/reject designs via `python -m cs2kit review <pack> --run <stamp> --approve <design|zone> --note \"...\"`.",
        "",
        "| Zone | Design | Lots | Height (m) | Front (m) | Cov (%) | Eaves (m) | Verdict | Notes |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in data["designs"]:
        lots_s = ", ".join(f"{w}x{d}" for w, d in row["lots"])
        hs = sorted({round(v["height_m"], 1) for v in row["stats"] if v.get("height_m") is not None})
        fs = sorted({round(v["front_m"], 2) for v in row["stats"] if v.get("front_m") is not None})
        cs = sorted({round(v["occupied_pct"], 1) for v in row["stats"] if v.get("occupied_pct") is not None})
        eaves = sorted({round(e, 1) for v in row["stats"] for e in v.get("roof_levels_m", [])})
        h_str = f"{hs[0]}..{hs[-1]}" if len(hs) > 1 else (str(hs[0]) if hs else "-")
        f_str = f"{fs[0]}..{fs[-1]}" if len(fs) > 1 else (str(fs[0]) if fs else "-")
        c_str = f"{cs[0]}..{cs[-1]}" if len(cs) > 1 else (str(cs[0]) if cs else "-")
        e_str = ", ".join(str(x) for x in eaves) or "-"
        note = (row.get("notes") or "").replace("|", "/")
        lines.append(
            f"| {row['zone_key']} | {row['design']} | {lots_s} | {h_str} | {f_str} | {c_str} | {e_str} | {row['verdict']} | {note} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_review_files(run_dir: Path, pack_id: str, manifest_assets: list[dict]):
    """Create initial REVIEW.json and REVIEW.md from passing baked assets (preserving prior verdicts if re-run)."""
    jpath = run_dir / "REVIEW.json"
    prev = {}
    if jpath.exists():
        old = json.loads(jpath.read_text(encoding="utf-8"))
        prev = {(r["zone_key"], r["design"]): r for r in old.get("designs", [])}

    grouped = {}
    for rec in manifest_assets:
        key = (rec["zone_key"], rec["design"])
        grouped.setdefault(key, []).append(rec)

    rows = []
    for (zk, design), items in sorted(grouped.items()):
        items_sorted = sorted(items, key=lambda x: (x["lot"][0], x["lot"][1]))
        old_row = prev.get((zk, design), {})
        rows.append(
            {
                "zone_key": zk,
                "design": design,
                "assets": [x["name"] for x in items_sorted],
                "lots": [x["lot"] for x in items_sorted],
                "stats": [
                    {
                        "name": x["name"],
                        "height_m": x["audit"]["height_m"],
                        "front_m": x["audit"]["front_m"],
                        "occupied_pct": x["audit"]["occupied_pct"],
                        "roof_levels_m": x["audit"]["roof_levels_m"],
                    }
                    for x in items_sorted
                ],
                "checks": old_row.get("checks") or {ck: "PENDING" for ck, _ in CHECKLIST},
                "verdict": old_row.get("verdict", "PENDING"),
                "notes": old_row.get("notes", ""),
            }
        )

    data = {"pack_id": pack_id, "run": run_dir.name, "checklist": [c[0] for c in CHECKLIST], "designs": rows}
    jpath.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    (run_dir / "REVIEW.md").write_text(_render_markdown(data), encoding="utf-8")
    return jpath


def update_review(run_dir: Path, targets=(), verdict: str = "PASS", note: str = "", approve_all: bool = False) -> dict:
    jpath = run_dir / "REVIEW.json"
    if not jpath.exists():
        raise FileNotFoundError(f"Missing {jpath}")
    data = json.loads(jpath.read_text(encoding="utf-8"))
    tset = set(targets)
    matched = 0
    check_val = "PASS" if verdict == "PASS" else "FAIL"
    for row in data["designs"]:
        hit = approve_all or (row["design"] in tset) or (row["zone_key"] in tset) or any(a in tset for a in row["assets"])
        if hit:
            row["verdict"] = verdict
            row["checks"] = {ck: check_val for ck, _ in CHECKLIST}
            if note:
                row["notes"] = note
            matched += 1
    jpath.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    (run_dir / "REVIEW.md").write_text(_render_markdown(data), encoding="utf-8")
    return {"matched_designs": matched, "total_designs": len(data["designs"]), "verdict": verdict}


def approved_asset_names(run_dir: Path) -> set[str]:
    jpath = run_dir / "REVIEW.json"
    if not jpath.exists():
        return set()
    data = json.loads(jpath.read_text(encoding="utf-8"))
    out = set()
    for row in data["designs"]:
        if row.get("verdict") == "PASS":
            out.update(row.get("assets", []))
    return out
