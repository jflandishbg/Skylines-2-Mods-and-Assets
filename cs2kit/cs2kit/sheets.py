"""Per-building contact sheets and zone-wide Rule 20 / Rule 21 comparison sheets."""
from pathlib import Path
from PIL import Image, ImageDraw

BUILDING_VIEWS = [
    ("1_front", "front"),
    ("2_front_left", "front-left"),
    ("3_front_right", "front-right"),
    ("4_right", "right side"),
    ("5_rear", "rear"),
    ("6_left", "left side"),
    ("7_aerial", "aerial"),
    ("8_lod1", "LOD1"),
    ("9_lod2", "LOD2"),
]


def _make_grid(tiles: list[tuple[str, Path]], out_path: Path, cols: int = 3, tile_w: int = 600, tile_h: int = 400):
    if not tiles:
        return False
    cols = max(1, min(cols, len(tiles)))
    rows = (len(tiles) + cols - 1) // cols
    img = Image.new("RGB", (tile_w * cols, tile_h * rows), (240, 240, 240))
    dr = ImageDraw.Draw(img)
    for i, (label, path) in enumerate(tiles):
        x, y = (i % cols) * tile_w, (i // cols) * tile_h
        im = Image.open(path).convert("RGB").resize((tile_w, tile_h), Image.Resampling.LANCZOS)
        img.paste(im, (x, y))
        bar_w = min(tile_w, max(160, len(label) * 7 + 16))
        dr.rectangle((x, y, x + bar_w, y + 20), fill=(18, 18, 22))
        dr.text((x + 6, y + 4), label, fill=(245, 245, 245))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    return True


def build_building_sheet(run_dir: Path, name: str) -> bool:
    pv = run_dir / name / "preview"
    tiles = []
    for stem, label in BUILDING_VIEWS:
        p = pv / f"{stem}.png"
        if p.exists():
            tiles.append((label, p))
    return _make_grid(tiles, run_dir / f"{name}_preview.png", cols=3)


def build_zone_sheets(run_dir: Path, passed_assets: list[dict]) -> list[Path]:
    """Generate <zone>_front.png, _rear.png, _aerial.png, and _allsizes.png inside run_dir/sheets/."""
    sheets_dir = run_dir / "sheets"
    sheets_dir.mkdir(parents=True, exist_ok=True)
    by_zone = {}
    for a in passed_assets:
        by_zone.setdefault(a["zone_key"], []).append(a)

    created = []
    for zk, z_assets in sorted(by_zone.items()):
        # Pick one canonical lot per distinct design (prefer median/middle lot)
        by_design = {}
        for a in z_assets:
            by_design.setdefault(a["design"], []).append(a)
        canonical = []
        for design, items in sorted(by_design.items()):
            items_sorted = sorted(items, key=lambda x: (x["lot"][0] * x["lot"][1], x["lot"][0], x["lot"][1]))
            canonical.append(items_sorted[len(items_sorted) // 2])

        cols = 3 if len(canonical) <= 9 else 4
        for view_stem, suffix in (("1_front", "front"), ("5_rear", "rear"), ("7_aerial", "aerial")):
            tiles = []
            for a in canonical:
                p = run_dir / a["name"] / "preview" / f"{view_stem}.png"
                if p.exists():
                    w, d = a["lot"]
                    tiles.append((f"{a['design']} ({w}x{d})", p))
            out = sheets_dir / f"{zk}_{suffix}.png"
            if _make_grid(tiles, out, cols=cols):
                created.append(out)

        all_tiles = []
        for a in sorted(z_assets, key=lambda x: (x["design"], x["lot"][0], x["lot"][1])):
            p = run_dir / a["name"] / "preview" / "2_front_left.png"
            if p.exists():
                w, d = a["lot"]
                all_tiles.append((f"{a['design']} {w}x{d}", p))
        out_all = sheets_dir / f"{zk}_allsizes.png"
        if _make_grid(all_tiles, out_all, cols=3 if len(all_tiles) <= 9 else 4):
            created.append(out_all)

    return created
