"""Declarative rect-packing texture atlas compiler and Rule 16 / Rule 27 verifier."""
from pathlib import Path
import json
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .config import ConfigError, PackConfig

MAPS = ("BaseColor", "Normal", "MaskMap", "ControlMask", "Emissive")
STEPS = (("main", "", 4096), ("_LOD1", "_LOD1", 2048), ("_LOD2", "_LOD2", 1024))
DEFAULT_FONT = "C:/Windows/Fonts/georgiab.ttf"


def _snap4_up(val: int, minimum: int = 4) -> int:
    val = max(minimum, int(val))
    return ((val + 3) // 4) * 4


def _channel_idx(ch):
    if ch is None:
        return None
    if isinstance(ch, str):
        u = ch.strip().upper()
        if u in ("R", "0"):
            return 0
        if u in ("G", "1"):
            return 1
        if u in ("B", "2"):
            return 2
        raise ConfigError(f"Invalid tint_channel {ch!r}; expected null, 0/1/2, or R/G/B")
    idx = int(ch)
    if idx not in (0, 1, 2):
        raise ConfigError(f"Invalid tint_channel {ch!r}; expected 0, 1, or 2")
    return idx


def _pack_rects(items, dim: int, gutter: int, margin: int):
    """MaxRects Best-Short-Side-Fit packer aligned on a 4-pixel grid."""
    free = [(margin, margin, dim - 2 * margin, dim - 2 * margin)]
    placed = {}
    ordered = sorted(items, key=lambda it: (max(it["pw"], it["ph"]), it["pw"] * it["ph"], it["key"]), reverse=True)

    for it in ordered:
        rw = it["pw"] + gutter
        rh = it["ph"] + gutter
        best_idx = -1
        best_score = None
        best_rect = None
        for idx, (fx, fy, fw, fh) in enumerate(free):
            if fw >= rw and fh >= rh:
                rem_w = fw - rw
                rem_h = fh - rh
                short_side = min(rem_w, rem_h)
                long_side = max(rem_w, rem_h)
                score = (short_side, long_side, fy, fx)
                if best_score is None or score < best_score:
                    best_score = score
                    best_idx = idx
                    best_rect = (fx, fy, rw, rh)
        if best_rect is None:
            used_px = sum(v["pw"] * v["ph"] for v in placed.values()) + it["pw"] * it["ph"]
            raise ConfigError(
                f"Atlas overflow at {dim}x{dim}: could not place {it['key']!r} ({it['pw']}x{it['ph']} + gutter {gutter}). "
                f"Requested tile area ~{100.0 * used_px / (dim * dim):.1f}% of canvas; shrink tile `px` sizes."
            )
        px, py, pw_g, ph_g = best_rect
        x0 = _snap4_up(px + gutter // 2, 0)
        y0 = _snap4_up(py + gutter // 2, 0)
        placed[it["key"]] = (x0, y0, x0 + it["pw"], y0 + it["ph"])

        new_free = []
        ux0, uy0, ux1, uy1 = px, py, px + pw_g, py + ph_g
        for fx, fy, fw, fh in free:
            fx1, fy1 = fx + fw, fy + fh
            if ux1 <= fx or ux0 >= fx1 or uy1 <= fy or uy0 >= fy1:
                new_free.append((fx, fy, fw, fh))
                continue
            if ux0 > fx:
                new_free.append((fx, fy, ux0 - fx, fh))
            if ux1 < fx1:
                new_free.append((ux1, fy, fx1 - ux1, fh))
            if uy0 > fy:
                new_free.append((fx, fy, fw, uy0 - fy))
            if uy1 < fy1:
                new_free.append((fx, uy1, fw, fy1 - uy1))

        # Prune rectangles contained inside another free rectangle
        pruned = []
        for i, a in enumerate(new_free):
            ax, ay, aw, ah = a
            if aw < 4 or ah < 4:
                continue
            contained = False
            for j, b in enumerate(new_free):
                if i == j:
                    continue
                bx, by, bw, bh = b
                if bx <= ax and by <= ay and ax + aw <= bx + bw and ay + ah <= by + bh:
                    contained = True
                    break
            if not contained:
                pruned.append(a)
        free = pruned
    return placed


def _find_scan_dir(source: str, textures_roots: list[Path], pack_dir: Path) -> Path:
    p = Path(source)
    if p.is_absolute() and p.is_dir():
        return p
    for root in textures_roots:
        cand = root / source
        if cand.is_dir():
            return cand
    cand = pack_dir / source
    if cand.is_dir():
        return cand
    raise ConfigError(f"Could not find texture scan folder {source!r} in textures_roots {[str(r) for r in textures_roots]}")


def _load_scan_file(folder: Path, key: str, size: tuple[int, int]):
    f = next(iter(sorted(folder.glob(f"*_{key}.*"))), None)
    if f is None:
        return None
    return Image.open(f).resize(size, Image.Resampling.LANCZOS)


def _tone_rgb(img: Image.Image, target, desat: float) -> np.ndarray:
    a = np.asarray(img.convert("RGB"), dtype=np.float32)
    if desat > 0.0:
        grey = a.mean(axis=2, keepdims=True)
        a = a * (1.0 - desat) + grey * desat
    if target is not None:
        mean = np.maximum(1.0, a.reshape(-1, 3).mean(axis=0))
        a *= np.array(target, dtype=np.float32) / mean
    return a


def _shingle_courses_mult(w: int, h: int, n: int, seed: int = 11) -> np.ndarray:
    rng = np.random.default_rng(seed)
    f = np.ones((h, w), np.float32)
    ch = h / n
    y = np.arange(h, dtype=np.float32)
    pos = (y % ch) / ch
    shade = 1.0 - 0.38 * np.clip((pos - 0.80) / 0.20, 0.0, 1.0) ** 1.5 - 0.10 * np.clip((0.10 - pos) / 0.10, 0.0, 1.0)
    f *= shade[:, None]
    for k in range(n):
        y0, y1 = int(k * ch), int((k + 1) * ch)
        x = rng.uniform(0.0, w * 0.08)
        while x < w:
            c = int(x) % w
            f[y0:y1, max(0, c - 1) : c + 2] *= 0.62
            x += rng.uniform(0.10, 0.21) * w
    return f


def _periodic_grain(rng, h: int, w: int, run: int = 9) -> np.ndarray:
    n = rng.normal(0.0, 1.0, (h, w)).astype(np.float32)
    acc = np.zeros_like(n)
    for k in range(-run, run + 1):
        acc += np.roll(n, k, axis=0)
    return acc / math.sqrt(2 * run + 1)


def _normal_from_height(hgt: np.ndarray, strength: float) -> Image.Image:
    gx = (np.roll(hgt, -1, axis=1) - np.roll(hgt, 1, axis=1)) * 0.5 * strength
    gy = (np.roll(hgt, -1, axis=0) - np.roll(hgt, 1, axis=0)) * 0.5 * strength
    n = np.dstack([-gx, gy, np.ones_like(hgt)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return Image.fromarray(np.dstack([(n + 1.0) * 127.5, np.full(hgt.shape, 255.0)]).clip(0, 255).astype("uint8"), "RGBA")


def _procedural_maps(shade, hgt, strength, rng, base_rgb=(236, 234, 228), smooth=58, metal=0):
    h, w = shade.shape
    grain = _periodic_grain(rng, h, w)
    c = np.array(base_rgb, np.float32)[None, None, :] * (shade * (1.0 + 0.025 * grain))[:, :, None]
    colour = Image.fromarray(c.clip(0, 255).astype("uint8"), "RGB").convert("RGBA")
    ao = Image.fromarray((150.0 + 105.0 * shade.clip(0, 1)).astype("uint8"), "L")
    mask = Image.merge("RGBA", (Image.new("L", (w, h), metal), ao, Image.new("L", (w, h), 0), Image.new("L", (w, h), smooth)))
    return dict(BaseColor=colour, Normal=_normal_from_height(hgt, strength), MaskMap=mask)


def _shingle_tile(size, ncol, nrow, shape, rise, seed, base_rgb=(236, 234, 228), smooth=58):
    w, h = size
    rng = np.random.default_rng(seed)
    X, Y = np.meshgrid((np.arange(w) + 0.5) / w * ncol, (np.arange(h) + 0.5) / h * nrow)

    def butt(k):
        dx = ((X - 0.5 * (k % 2)) % 1.0) - 0.5
        if shape == "round":
            prof = 1.0 - np.sqrt(np.clip(1.0 - (2.0 * dx) ** 2, 0.0, 1.0))
        elif shape == "point":
            prof = np.abs(2.0 * dx)
        else:
            prof = np.zeros_like(dx)
        return k + 1.0 - rise * prof

    k0 = np.floor(Y)
    k = np.where(Y >= butt(k0), k0 + 1.0, k0)
    above, own = butt(k - 1.0), butt(k)
    s = (Y - above) / np.maximum(1e-4, own - above)
    dx = ((X - 0.5 * (k % 2)) % 1.0) - 0.5
    shade = 1.0 - 0.42 * np.clip(1.0 - s / 0.22, 0.0, 1.0) ** 1.6 - 0.08 * np.clip((s - 0.9) / 0.1, 0.0, 1.0)
    shade *= np.where(np.abs(dx) > 0.5 - 0.035, 0.7, 1.0)
    ids = ((k.astype(int) % nrow) * ncol + np.floor((X - 0.5 * (k % 2)) % ncol).astype(int))
    tone = rng.uniform(0.95, 1.04, nrow * ncol + 1)[ids]
    hgt = 0.4 + 0.6 * np.clip(s, 0.0, 1.0)
    return _procedural_maps((shade * tone).astype(np.float32), hgt.astype(np.float32), 9.0 * ncol / 8.0, rng, base_rgb, smooth)


def _batten_tile(size, nboard, seed, base_rgb=(236, 234, 228), smooth=52):
    w, h = size
    rng = np.random.default_rng(seed)
    X = np.broadcast_to((np.arange(w) + 0.5) / w * nboard, (h, w))
    f = X % 1.0
    d = np.minimum(f, 1.0 - f)
    bw = 0.11
    hgt = np.clip((bw - d) / 0.03, 0.0, 1.0)
    shade = np.ones((h, w), np.float32)
    shade -= 0.42 * np.clip(1.0 - (f - bw) / 0.16, 0.0, 1.0) * (f > bw)
    shade += 0.12 * ((d < bw) & (f > 0.5))
    tone = rng.uniform(0.96, 1.03, nboard)[np.floor(X).astype(int) % nboard]
    return _procedural_maps((shade * tone).astype(np.float32), hgt.astype(np.float32), 6.0, rng, base_rgb, smooth)


def _standing_seam_tile(size, seam_count, seed, base_rgb=(90, 102, 98), smooth=108, metal=175):
    w, h = size
    rng = np.random.default_rng(seed)
    X = np.broadcast_to((np.arange(w) + 0.5) / w * seam_count, (h, w))
    f = X % 1.0
    d = np.minimum(f, 1.0 - f)
    rw = 0.055
    hgt = np.clip((rw - d) / 0.018, 0.0, 1.0)
    shade = np.ones((h, w), np.float32)
    shade -= 0.30 * np.clip(1.0 - (f - rw) / 0.12, 0.0, 1.0) * (f > rw)
    shade += 0.14 * ((d < rw) & (f > 0.5))
    grain = _periodic_grain(rng, h, w, run=5)
    c = np.array(base_rgb, np.float32)[None, None, :] * (shade * (1.0 + 0.015 * grain))[:, :, None]
    colour = Image.fromarray(c.clip(0, 255).astype("uint8"), "RGB").convert("RGBA")
    ao = Image.fromarray((185.0 + 70.0 * shade.clip(0, 1)).astype("uint8"), "L")
    mask = Image.merge("RGBA", (Image.new("L", (w, h), metal), ao, Image.new("L", (w, h), 0), Image.new("L", (w, h), smooth)))
    return dict(BaseColor=colour, Normal=_normal_from_height(hgt.astype(np.float32), 7.5), MaskMap=mask)


def _stucco_tile(size, seed, base_rgb=(220, 214, 200), smooth=32):
    w, h = size
    rng = np.random.default_rng(seed)
    coarse = rng.normal(0.0, 1.0, (max(4, h // 4), max(4, w // 4))).astype(np.float32)
    coarse_im = Image.fromarray(((coarse * 20.0 + 128.0).clip(0, 255)).astype("uint8"), "L").resize((w, h), Image.Resampling.BILINEAR)
    hc = (np.asarray(coarse_im, dtype=np.float32) - 128.0) / 128.0
    fine = rng.normal(0.0, 0.35, (h, w)).astype(np.float32)
    hgt = 0.5 + 0.3 * hc + 0.1 * fine
    shade = 1.0 + 0.04 * hc + 0.015 * fine
    c = np.array(base_rgb, np.float32)[None, None, :] * shade[:, :, None]
    colour = Image.fromarray(c.clip(0, 255).astype("uint8"), "RGB").convert("RGBA")
    ao = Image.fromarray((220.0 + 35.0 * shade.clip(0, 1)).astype("uint8"), "L")
    mask = Image.merge("RGBA", (Image.new("L", (w, h), 0), ao, Image.new("L", (w, h), 0), Image.new("L", (w, h), smooth)))
    return dict(BaseColor=colour, Normal=_normal_from_height(hgt.astype(np.float32), 2.5), MaskMap=mask)


def _sign_tile(text: str, board, ink, size: tuple[int, int], aspect: float, font_path: str):
    w, h = size
    W = w * 4
    H = max(16, round(W / aspect)) if aspect else h * 4
    im = Image.new("RGB", (W, H), tuple(board))
    d = ImageDraw.Draw(im)
    m = max(2, H // 12)
    d.rectangle([m, m, W - 1 - m, H - 1 - m], outline=tuple(ink), width=max(2, H // 40))

    font_file = Path(font_path) if font_path else None
    use_ttf = font_file is not None and font_file.exists()
    if use_ttf:
        fs = max(8, int(H * 0.52))
        f = ImageFont.truetype(str(font_file), fs)
        x0, y0, x1, y1 = d.textbbox((0, 0), text, font=f)
        while fs > 8 and (x1 - x0) > W * 0.86:
            fs -= 2
            f = ImageFont.truetype(str(font_file), fs)
            x0, y0, x1, y1 = d.textbbox((0, 0), text, font=f)
    else:
        f = ImageFont.load_default()
        x0, y0, x1, y1 = d.textbbox((0, 0), text, font=f)
    d.text(((W - (x1 - x0)) / 2 - x0, (H - (y1 - y0)) / 2 - y0), text, font=f, fill=tuple(ink))

    colour = im.resize(size, Image.Resampling.LANCZOS).convert("RGBA")
    mask = Image.merge("RGBA", (Image.new("L", size, 0), Image.new("L", size, 255), Image.new("L", size, 0), Image.new("L", size, 60)))
    return dict(
        BaseColor=colour,
        Normal=Image.new("RGBA", size, (128, 128, 255, 255)),
        MaskMap=mask,
    )


def _generate_tile_lod0(spec: dict, size: tuple[int, int], pack: PackConfig, font_path: str) -> dict:
    kind = spec["kind"]
    w, h = size
    if kind == "scan":
        folder = _find_scan_dir(spec["source"], pack.textures_roots, pack.pack_dir)
        col = _load_scan_file(folder, "Color", size)
        nrm = _load_scan_file(folder, "NormalGL", size)
        if col is None or nrm is None:
            raise ConfigError(f"Tile {spec['key']!r}: scan folder {folder} missing Color or NormalGL PNG")
        ao = _load_scan_file(folder, "AmbientOcclusion", size) or _load_scan_file(folder, "Displacement", size)
        rough = _load_scan_file(folder, "Roughness", size)
        metal_img = _load_scan_file(folder, "Metalness", size)
        target = spec.get("target_rgb")
        desat = float(spec.get("desat", 0.0))
        a = _tone_rgb(col, target, desat)
        ao_w = float(spec.get("ao_weight", 0.28))
        if ao is not None:
            a *= (1.0 - ao_w) + ao_w * (np.asarray(ao.convert("L"), np.float32) / 255.0)[:, :, None]
            if target is not None:
                mean = np.maximum(1.0, a.reshape(-1, 3).mean(axis=0))
                a *= np.array(target, dtype=np.float32) / mean
        if spec.get("courses"):
            a *= _shingle_courses_mult(w, h, int(spec["courses"]), seed=int(spec.get("seed", 11)))[:, :, None]
        colour = Image.fromarray(np.clip(a, 0, 255).astype("uint8"), "RGB").convert("RGBA")
        normal = nrm.convert("RGBA")
        rough_l = rough.convert("L") if rough else Image.new("L", size, 205)
        ao_l = ao.convert("L") if ao else Image.new("L", size, 242)
        metal_l = metal_img.convert("L") if metal_img else Image.new("L", size, int(spec.get("metalness", 3)))
        mask = Image.merge("RGBA", (metal_l, ao_l, Image.new("L", size, 0), rough_l.point(lambda x: 255 - x)))
        out = dict(BaseColor=colour, Normal=normal, MaskMap=mask)
    elif kind == "flat_paint":
        rng = np.random.default_rng(int(spec.get("seed", 7)))
        target = np.array(spec.get("color", [226, 225, 219]), np.float32)
        grain = rng.normal(0.0, 2.2, (h, 1)) + rng.normal(0.0, 1.2, (h, w))
        base = np.clip(target[None, None, :] + grain[:, :, None], 0.0, 255.0)
        colour = Image.fromarray(base.astype("uint8"), "RGB").convert("RGBA")
        normal = Image.new("RGBA", size, (128, 128, 255, 255))
        ao_val = int(spec.get("ao", 240))
        smooth = int(spec.get("smoothness", 46))
        metal = int(spec.get("metalness", 0))
        mask = Image.merge("RGBA", (Image.new("L", size, metal), Image.new("L", size, ao_val), Image.new("L", size, 0), Image.new("L", size, smooth)))
        out = dict(BaseColor=colour, Normal=normal, MaskMap=mask)
    elif kind == "shingle_courses":
        out = _shingle_tile(
            size,
            int(spec.get("ncol", 8)),
            int(spec.get("nrow", 8)),
            "flat",
            0.0,
            int(spec.get("seed", 19)),
            tuple(spec.get("color", (236, 234, 228))),
            int(spec.get("smoothness", 58)),
        )
    elif kind == "shingle_fishscale":
        out = _shingle_tile(
            size,
            int(spec.get("ncol", 8)),
            int(spec.get("nrow", 4)),
            "round",
            float(spec.get("rise", 0.5)),
            int(spec.get("seed", 21)),
            tuple(spec.get("color", (236, 234, 228))),
            int(spec.get("smoothness", 58)),
        )
    elif kind == "shingle_diamond":
        out = _shingle_tile(
            size,
            int(spec.get("ncol", 16)),
            int(spec.get("nrow", 2)),
            "point",
            float(spec.get("rise", 0.62)),
            int(spec.get("seed", 22)),
            tuple(spec.get("color", (236, 234, 228))),
            int(spec.get("smoothness", 58)),
        )
    elif kind == "board_batten":
        out = _batten_tile(
            size,
            int(spec.get("nboard", 8)),
            int(spec.get("seed", 23)),
            tuple(spec.get("color", (236, 234, 228))),
            int(spec.get("smoothness", 52)),
        )
    elif kind == "stucco":
        out = _stucco_tile(
            size,
            int(spec.get("seed", 31)),
            tuple(spec.get("color", (222, 216, 202))),
            int(spec.get("smoothness", 32)),
        )
    elif kind == "standing_seam":
        out = _standing_seam_tile(
            size,
            int(spec.get("seam_count", 6)),
            int(spec.get("seed", 37)),
            tuple(spec.get("color", (90, 102, 98))),
            int(spec.get("smoothness", 108)),
            int(spec.get("metalness", 175)),
        )
    elif kind == "sign":
        mw, mh = spec.get("metres", [3.0, 0.58])
        out = _sign_tile(spec["text"], spec["board"], spec["ink"], size, float(mw) / float(mh), font_path)
    else:
        raise ConfigError(f"Unknown atlas tile kind {kind!r} for tile {spec['key']!r}")

    if spec.get("lift_target_rgb"):
        target = np.array(spec["lift_target_rgb"], np.float32)
        b = np.asarray(out["BaseColor"], dtype=np.float32)
        mean = np.maximum(1.0, b[..., :3].reshape(-1, 3).mean(axis=0))
        b[..., :3] = np.clip(b[..., :3] * (target / mean), 0.0, 255.0)
        out["BaseColor"] = Image.fromarray(b.round().astype("uint8"), "RGBA")
    return out


def boxes(cells: dict, dim: int) -> dict:
    return {
        k: tuple(round(v * dim) for v in (c["uv"][0], 1.0 - c["uv"][3], c["uv"][2], 1.0 - c["uv"][1]))
        for k, c in cells.items()
    }


def gutters(cells: dict, dim: int, shape: tuple[int, int]):
    """For every gutter pixel outside cells, compute nearest owning cell and wrapped/clamped source texel."""
    H, W = shape
    B = boxes(cells, dim)
    names = list(B)
    inside = np.zeros((H, W), bool)
    for x0, y0, x1, y1 in B.values():
        inside[y0:y1, x0:x1] = True
    best = np.full((H, W), 10**6, np.int32)
    owner = np.full((H, W), -1, np.int32)
    sy = np.zeros((H, W), np.int32)
    sx = np.zeros((H, W), np.int32)
    reach = max(4, dim // 100)
    for i, k in enumerate(names):
        x0, y0, x1, y1 = B[k]
        a0, b0, a1, b1 = max(0, x0 - reach), max(0, y0 - reach), min(W, x1 + reach), min(H, y1 + reach)
        yy, xx = np.mgrid[b0:b1, a0:a1]
        d = np.maximum(np.maximum(x0 - xx, xx - (x1 - 1)), np.maximum(y0 - yy, yy - (y1 - 1)))
        sel = (~inside[b0:b1, a0:a1]) & (d < best[b0:b1, a0:a1])
        best[b0:b1, a0:a1][sel] = d[sel]
        owner[b0:b1, a0:a1][sel] = i
        if cells[k].get("gutter") == "clamp" or k.startswith(("Sign_", "Address")):
            ty, tx = np.clip(yy, y0, y1 - 1), np.clip(xx, x0, x1 - 1)
        else:
            ty, tx = y0 + (yy - y0) % max(1, y1 - y0), x0 + (xx - x0) % max(1, x1 - x0)
        sy[b0:b1, a0:a1][sel] = ty[sel]
        sx[b0:b1, a0:a1][sel] = tx[sel]
    return owner >= 0, sy, sx


def _write_atlas_preview(base_img: Image.Image, cells: dict, dim: int, out_path: Path, util_pct: float):
    prev = base_img.resize((1024, 1024), Image.Resampling.LANCZOS).convert("RGB")
    dr = ImageDraw.Draw(prev)
    scale = 1024.0 / dim
    B = boxes(cells, dim)
    for k, (x0, y0, x1, y1) in B.items():
        rx0, ry0, rx1, ry1 = int(x0 * scale), int(y0 * scale), int(x1 * scale), int(y1 * scale)
        dr.rectangle([rx0, ry0, rx1, ry1], outline=(255, 220, 80), width=1)
        if rx1 - rx0 >= 28 and ry1 - ry0 >= 14:
            dr.rectangle([rx0 + 1, ry0 + 1, min(rx1 - 1, rx0 + len(k) * 6 + 6), min(ry1 - 1, ry0 + 13)], fill=(0, 0, 0))
            dr.text((rx0 + 3, ry0 + 2), k[:20], fill=(255, 255, 255))
    dr.rectangle([4, 1004, 340, 1022], fill=(0, 0, 0))
    dr.text((8, 1007), f"Tiles: {len(B)} | Packed area: {util_pct:.1f}%", fill=(180, 255, 180))
    prev.save(out_path)


def build_atlas(pack: PackConfig) -> Path:
    """Compile the pack's atlas.json into 15 PNGs, atlas_layout.json, and atlas_preview.png."""
    if not pack.atlas_file.exists():
        raise ConfigError(f"Missing atlas.json at {pack.atlas_file}")
    spec = json.loads(pack.atlas_file.read_text(encoding="utf-8"))

    sizes = spec.get("sizes", {})
    dim_main = int(sizes.get("main", 4096))
    dim_lod1 = int(sizes.get("_LOD1", dim_main // 2))
    dim_lod2 = int(sizes.get("_LOD2", dim_main // 4))
    steps = (("main", "", dim_main), ("_LOD1", "_LOD1", dim_lod1), ("_LOD2", "_LOD2", dim_lod2))

    gutter_main = _snap4_up(int(spec.get("gutter_px_main", 16)), 8)
    margin = _snap4_up(gutter_main // 2, 4)
    font_path = str(spec.get("font", DEFAULT_FONT))

    items = []
    seen = set()
    for t in spec.get("tiles", []):
        k = t["key"]
        if k in seen:
            raise ConfigError(f"Duplicate tile key {k!r} in {pack.atlas_file}")
        seen.add(k)
        px = t.get("px", [512, 512])
        item = dict(t)
        item["pw"] = _snap4_up(px[0], 16)
        item["ph"] = _snap4_up(px[1], 16)
        item["gutter"] = t.get("gutter", "wrap")
        item["tint_channel"] = _channel_idx(t.get("tint_channel"))
        items.append(item)

    for s in spec.get("signs", []):
        k = s["key"]
        if k in seen:
            raise ConfigError(f"Duplicate sign key {k!r} in {pack.atlas_file}")
        seen.add(k)
        px = s.get("px", [512, 100])
        items.append(
            {
                "key": k,
                "kind": "sign",
                "text": s["text"],
                "board": s["board"],
                "ink": s["ink"],
                "pw": _snap4_up(px[0], 16),
                "ph": _snap4_up(px[1], 16),
                "metres": s.get("metres", [3.0, 0.58]),
                "lod1_metres": s.get("lod1_metres", s.get("metres", [3.0, 0.58])),
                "lod2_metres": s.get("lod2_metres", [174.0, 174.0]),
                "gutter": "clamp",
                "tint_channel": None,
            }
        )

    if not items:
        raise ConfigError(f"{pack.atlas_file} defines no tiles or signs")

    rects = _pack_rects(items, dim_main, gutter_main, margin)
    by_key = {it["key"]: it for it in items}

    layout = {"order": [it["key"] for it in items], "lods": {}}
    for lod_name, _, dim in steps:
        lod_cells = {}
        for k in layout["order"]:
            x0, y0, x1, y1 = rects[k]
            it = by_key[k]
            uv = [
                round(x0 / dim_main, 8),
                round(1.0 - y1 / dim_main, 8),
                round(x1 / dim_main, 8),
                round(1.0 - y0 / dim_main, 8),
            ]
            m0 = it.get("metres", [2.0, 2.0])
            if lod_name == "main":
                metres = [float(m0[0]), float(m0[1])]
            elif lod_name == "_LOD1":
                m1 = it.get("lod1_metres", [float(m0[0]) * 2.0, float(m0[1]) * 2.0])
                metres = [float(m1[0]), float(m1[1])]
            else:
                m2 = it.get("lod2_metres", [174.0, 174.0])
                metres = [float(m2[0]), float(m2[1])]
            cell = {"uv": uv, "metres": metres, "gutter": it["gutter"]}
            if it["tint_channel"] is not None:
                cell["tint_channel"] = it["tint_channel"]
            lod_cells[k] = cell
        layout["lods"][lod_name] = lod_cells

    out_dir = pack.atlas_build_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "atlas_layout.json").write_text(json.dumps(layout, indent=2) + "\n", encoding="utf-8")

    # Generate LOD0 tiles once, then downsample cleanly for LOD1 & LOD2
    lod0_tiles = {}
    for k in layout["order"]:
        x0, y0, x1, y1 = rects[k]
        lod0_tiles[k] = _generate_tile_lod0(by_key[k], (x1 - x0, y1 - y0), pack, font_path)

    for lod_name, suf, dim in steps:
        scale = dim_main // dim
        cells = layout["lods"][lod_name]
        B = boxes(cells, dim)
        canvases = {
            "BaseColor": Image.new("RGBA", (dim, dim), (128, 128, 128, 255)),
            "Normal": Image.new("RGBA", (dim, dim), (128, 128, 255, 255)),
            "MaskMap": Image.new("RGBA", (dim, dim), (0, 240, 0, 40)),
            "ControlMask": Image.new("RGBA", (dim, dim), (0, 0, 0, 255)),
            "Emissive": Image.new("RGBA", (dim, dim), (0, 0, 0, 255)),
        }
        for k in layout["order"]:
            x0, y0, x1, y1 = B[k]
            sz = (x1 - x0, y1 - y0)
            src_maps = lod0_tiles[k]
            for mp in ("BaseColor", "Normal", "MaskMap"):
                tile_im = src_maps[mp] if scale == 1 else src_maps[mp].resize(sz, Image.Resampling.LANCZOS)
                canvases[mp].paste(tile_im, (x0, y0))
            ch = by_key[k]["tint_channel"]
            if ch is not None:
                rgb = [0, 0, 0]
                rgb[ch] = 255
                canvases["ControlMask"].paste((rgb[0], rgb[1], rgb[2], 255), (x0, y0, x1, y1))

        sel, sy, sx = gutters(cells, dim, (dim, dim))
        for mp in MAPS:
            arr = np.asarray(canvases[mp]).copy()
            arr[sel] = arr[sy[sel], sx[sel]]
            Image.fromarray(arr, "RGBA").save(out_dir / f"ATLAS{suf}_{mp}.png")

        if lod_name == "main":
            used = sum((x1 - x0) * (y1 - y0) for x0, y0, x1, y1 in rects.values())
            _write_atlas_preview(canvases["BaseColor"], cells, dim, out_dir / "atlas_preview.png", 100.0 * used / (dim * dim))

    return out_dir


def check_atlas(pack: PackConfig) -> list[str]:
    """Verify Rule 16 (continuous gutter wrap/clamp) and Rule 27 (ControlMask) across all 3 LODs."""
    out_dir = pack.atlas_build_dir
    layout_path = out_dir / "atlas_layout.json"
    if not layout_path.exists():
        raise ConfigError(f"Atlas not built yet ({layout_path} missing); run `atlas` first.")
    lay = json.loads(layout_path.read_text(encoding="utf-8"))
    errors = []

    for lod_name, suf, _ in STEPS:
        cells = lay["lods"][lod_name]
        # Check non-overlap
        items = list(cells.items())
        for i in range(len(items)):
            ka, ca = items[i]
            la, ba, ra, ta = ca["uv"]
            for j in range(i + 1, len(items)):
                kb, cb = items[j]
                lb, bb, rb, tb = cb["uv"]
                if min(ra, rb) > max(la, lb) + 1e-6 and min(ta, tb) > max(ba, bb) + 1e-6:
                    errors.append(f"{lod_name}: overlapping tiles {ka} and {kb}")

        base_path = out_dir / f"ATLAS{suf}_BaseColor.png"
        if not base_path.exists():
            errors.append(f"Missing {base_path}")
            continue
        with Image.open(base_path) as bim:
            dim = bim.size[0]
        sel, sy, sx = gutters(cells, dim, (dim, dim))
        for mp in MAPS:
            p = out_dir / f"ATLAS{suf}_{mp}.png"
            if not p.exists():
                errors.append(f"Missing {p}")
                continue
            with Image.open(p) as mim:
                a = np.asarray(mim.convert("RGBA")).astype(np.int16)
            diff = np.abs(a[sel] - a[sy[sel], sx[sel]]).max(axis=1)
            bad_px = int((diff > 2).sum())
            if bad_px:
                errors.append(f"Rule 16 ({lod_name} {mp}): {bad_px} gutter pixel(s) do not match tile edge/wrap")
            if mp == "ControlMask":
                B = boxes(cells, dim)
                for k, c in cells.items():
                    ch = c.get("tint_channel")
                    if ch is not None:
                        x0, y0, x1, y1 = B[k]
                        if int(a[y0:y1, x0:x1, ch].min()) < 250:
                            errors.append(f"Rule 27 ({lod_name}): tile {k} missing ControlMask channel {ch}")
    return errors
