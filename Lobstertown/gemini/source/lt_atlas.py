"""Lobstertown atlas: swap unused New France slots in atlas_template/ for the Maine materials.

Run once (idempotent):  python lt_atlas.py
Each swap renames a slot key in kit/atlas_layout.json (all three LODs) and repaints that slot in the
15 TEMPLATE PNGs. Map formats follow detail_atlas.py: BaseColor = colour x AO, Normal = NormalGL,
MaskMap = (metal, ao, 0, smoothness), ControlMask clear, Emissive black.
"""
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

G = Path(__file__).resolve().parents[1]
LIB = G.parent / "textures"
LAYOUT = G / "source" / "kit" / "atlas_layout.json"
STEPS = (("main", "", 4096), ("_LOD1", "_LOD1", 2048), ("_LOD2", "_LOD2", 1024))

# new key: (old slot, scan folder, target mean RGB, desaturate 0..1, metres per LOD 0/1/2)
# LOD2 repeats like the kit's own wood (Clapboard 174 m): at that range a material reads as one averaged colour
SWAPS = {
    "ShingleSilver": ("RaceWater", LIB / "shingle/WoodSiding011", (132, 133, 132), .85, (1.2, 4.8, 174)),
    "ShingleGrey": ("CanalWater", LIB / "shingle/WoodSiding012", (98, 98, 97), .85, (1.2, 4.8, 174)),
    "TrimWhite": ("MatteDial", None, (226, 225, 219), 0, (3.0, 6.0, 174)),
}


def scan(folder, key, size):
    f = next(iter(sorted(folder.glob(f"*_{key}.png"))), None) if folder else None
    return Image.open(f).resize(size, Image.Resampling.LANCZOS) if f else None


def tone(color, target, desat):
    a = np.asarray(color.convert("RGB"), dtype=np.float32)
    grey = a.mean(axis=2, keepdims=True)
    a = a * (1 - desat) + grey * desat
    a *= np.array(target, dtype=np.float32) / a.reshape(-1, 3).mean(axis=0)
    return a


def courses(w, h, n, seed=11):
    """Shingle courses that read from a distance: a shadow under each butt line and dark keyways between
    shingles (staggered course to course). Returns a multiplier image (h, w)."""
    rng = np.random.default_rng(seed)
    f = np.ones((h, w), np.float32)
    ch = h / n
    y = np.arange(h, dtype=np.float32)
    pos = (y % ch) / ch                                  # 0 at a course top, 1 at its butt
    shade = 1 - .38 * np.clip((pos - .80) / .20, 0, 1) ** 1.5 - .10 * np.clip((.10 - pos) / .10, 0, 1)
    f *= shade[:, None]
    for k in range(n):
        y0, y1 = int(k * ch), int((k + 1) * ch)
        x = rng.uniform(0, w * .08)
        while x < w:
            c = int(x) % w
            f[y0:y1, max(0, c - 1):c + 2] *= .62
            x += rng.uniform(.10, .21) * w               # shingles 12-25 cm wide on a 1.2 m tile
    return f


def tiles(spec, size):
    _, folder, target, desat, _ = spec
    w, h = size
    if folder is None:                              # flat paint with a faint brush grain
        rng = np.random.default_rng(7)
        grain = rng.normal(0, 2.2, (h, 1)) + rng.normal(0, 1.2, (h, w))
        base = np.clip(np.array(target, np.float32)[None, None, :] + grain[:, :, None], 0, 255)
        colour = Image.fromarray(base.astype("uint8"), "RGB").convert("RGBA")
        normal = Image.new("RGBA", size, (128, 128, 255, 255))
        mask = Image.merge("RGBA", (Image.new("L", size, 0), Image.new("L", size, 0),
                                    Image.new("L", size, 0), Image.new("L", size, 46)))
        return dict(BaseColor=colour, Normal=normal, MaskMap=mask)
    ao = scan(folder, "AmbientOcclusion", size) or scan(folder, "Displacement", size)
    rough = scan(folder, "Roughness", size)
    a = tone(scan(folder, "Color", size), target, desat)
    if ao is not None:
        a *= (.72 + .28 * np.asarray(ao.convert("L"), np.float32) / 255)[:, :, None]
        a *= np.array(target, np.float32) / a.reshape(-1, 3).mean(axis=0)
    a *= courses(w, h, 8)[:, :, None]
    colour = Image.fromarray(np.clip(a, 0, 255).astype("uint8"), "RGB").convert("RGBA")
    normal = scan(folder, "NormalGL", size).convert("RGBA")
    rough = rough.convert("L") if rough else Image.new("L", size, 205)
    aol = ao.convert("L") if ao else Image.new("L", size, 242)
    mask = Image.merge("RGBA", (Image.new("L", size, 3), aol, Image.new("L", size, 0), rough.point(lambda x: 255 - x)))
    return dict(BaseColor=colour, Normal=normal, MaskMap=mask)


MAPS = ("BaseColor", "Normal", "MaskMap", "ControlMask", "Emissive")

# In-game colour variations (Toronto lesson, 2026-11-14): the ControlMask's R, G and B mark where colour 0, 1 and 2 of
# a building's ColorProperties set multiply the base colour (wiki: element 0 = R, 1 = G, 2 = B). Colour 0 stays
# white, except as the painted-ladies accent on the Victorian claddings (VIC_SPLIT). G = the wall cladding (weathering or paint), B = the white trim (white or cream).
TINT = {"ShingleSilver": 1, "ShingleGrey": 1, "Clapboard": 1, "ClapSage": 1, "TrimWhite": 2,
        "Fishscale": 0, "DiamondBand": 0, "BoardBatten": 0}     # painted ladies: R = colour 0, the accent
# A multiplier can only darken, so painted clapboard is lifted to near-white and its colour comes from the set.
TONE = {"Clapboard": (236, 234, 228)}


def paint_tint(lay):
    """Paint the TINT channels into every LOD's ControlMask and lift the TONE tiles (idempotent)."""
    for lod, suf, dim in STEPS:
        B = boxes(lay["lods"][lod], dim)
        f = G / "atlas_template" / f"TEMPLATE{suf}_ControlMask.png"
        a = np.asarray(Image.open(f).convert("RGBA")).copy()
        a[..., :3] = 0
        for k, ch in TINT.items():
            x0, y0, x1, y1 = B[k]
            a[y0:y1, x0:x1, ch] = 255
        Image.fromarray(a, "RGBA").save(f)
        f = G / "atlas_template" / f"TEMPLATE{suf}_BaseColor.png"
        b = np.asarray(Image.open(f).convert("RGBA")).astype(np.float32)
        for k, target in TONE.items():
            x0, y0, x1, y1 = B[k]
            t = b[y0:y1, x0:x1, :3]
            t *= np.array(target, np.float32) / t.reshape(-1, 3).mean(axis=0)
            b[y0:y1, x0:x1, :3] = np.clip(t, 0, 255)
        Image.fromarray(b.round().astype("uint8"), "RGBA").save(f)
    print("tint mask painted:", ", ".join(f"{k} {'RGB'[c]}" for k, c in TINT.items()))


def check_tint():
    lay = json.loads(LAYOUT.read_text())
    for lod, suf, dim in STEPS:
        B = boxes(lay["lods"][lod], dim)
        a = np.asarray(Image.open(G / "atlas_template" / f"TEMPLATE{suf}_ControlMask.png").convert("RGBA"))
        for k, ch in TINT.items():
            x0, y0, x1, y1 = B[k]
            if a[y0:y1, x0:x1, ch].min() < 250:
                raise SystemExit(f"Colour variations: {k} is not marked in the {suf or 'LOD0'} ControlMask -> run lt_atlas.py")
    print("Colour variations: tint mask in place")
CLAMP = ("Address", "Sign_")                 # decals: their gutter repeats the edge texel instead of wrapping


def boxes(cells, dim):
    return {k: tuple(round(v * dim) for v in (c["uv"][0], 1 - c["uv"][3], c["uv"][2], 1 - c["uv"][1]))
            for k, c in cells.items()}


def gutters(cells, dim, shape):
    """For every pixel outside the cells: which cell owns it (nearest by Chebyshev distance, -1 if none within
    reach) and where in that cell its wrapped (or clamped) source texel is. Gutters stop halfway to a neighbour."""
    H, W = shape
    B = boxes(cells, dim)
    names = list(B)
    inside = np.zeros((H, W), bool)
    for x0, y0, x1, y1 in B.values():
        inside[y0:y1, x0:x1] = True
    best = np.full((H, W), 10 ** 6, np.int32)
    owner = np.full((H, W), -1, np.int32)
    sy = np.zeros((H, W), np.int32); sx = np.zeros((H, W), np.int32)
    reach = max(4, dim // 100)
    for i, k in enumerate(names):
        x0, y0, x1, y1 = B[k]
        a0, b0, a1, b1 = max(0, x0 - reach), max(0, y0 - reach), min(W, x1 + reach), min(H, y1 + reach)
        yy, xx = np.mgrid[b0:b1, a0:a1]
        d = np.maximum(np.maximum(x0 - xx, xx - (x1 - 1)), np.maximum(y0 - yy, yy - (y1 - 1)))
        sel = (~inside[b0:b1, a0:a1]) & (d < best[b0:b1, a0:a1])
        best[b0:b1, a0:a1][sel] = d[sel]
        owner[b0:b1, a0:a1][sel] = i
        if k.startswith(CLAMP):
            ty, tx = np.clip(yy, y0, y1 - 1), np.clip(xx, x0, x1 - 1)
        else:
            ty, tx = y0 + (yy - y0) % (y1 - y0), x0 + (xx - x0) % (x1 - x0)
        sy[b0:b1, a0:a1][sel] = ty[sel]
        sx[b0:b1, a0:a1][sel] = tx[sel]
    return owner >= 0, sy, sx


def fill_gutters(lay):
    """Rulebook rule 16: paint every gutter with its own tile, so filtering at a tile edge blends the tile into
    itself and not into a flat or stale colour (the grid of lines on the walls)."""
    for lod, suf, dim in STEPS:
        for mp in MAPS:
            f = G / "atlas_template" / f"TEMPLATE{suf}_{mp}.png"
            a = np.asarray(Image.open(f).convert("RGBA")).copy()
            sel, sy, sx = gutters(lay["lods"][lod], dim, a.shape[:2])
            a[sel] = a[sy[sel], sx[sel]]
            Image.fromarray(a, "RGBA").save(f)
    print("gutters filled")


def check_gutters():
    """Fail (SystemExit) if any gutter pixel differs from the tile texel it should repeat."""
    lay = json.loads(LAYOUT.read_text())
    bad = []
    for lod, suf, dim in STEPS:
        sel = sy = sx = None
        for mp in MAPS:
            a = np.asarray(Image.open(G / "atlas_template" / f"TEMPLATE{suf}_{mp}.png").convert("RGBA")).astype(np.int16)
            if sel is None:
                sel, sy, sx = gutters(lay["lods"][lod], dim, a.shape[:2])
            diff = np.abs(a[sel] - a[sy[sel], sx[sel]]).max(axis=1)
            n = int((diff > 2).sum())
            if n:
                bad.append(f"{suf or 'LOD0'} {mp}: {n} gutter pixels do not repeat their tile")
    if bad:
        raise SystemExit("Rule 16 (materials run continuously) FAILED: " + "; ".join(bad) + " -> run lt_atlas.py")
    print("Rule 16: every atlas gutter repeats its tile")


# Main Street shop signs (2026-11-15): the eight New France inscription slots become painted fascia signs with
# made-up Maine shop names. A slot maps once onto a sign plate SIGN_M metres wide and tall; the plate must sit on a
# tile boundary (x a multiple of 3.0, z a multiple of .58 on LOD 0/1) so the planar mapping does not split it.
SIGN_M = (3.0, .58)
SIGNS = [  # old slot, new key, lettering, board colour, letter colour
    ("Sign_VillaJeuDePaume", "Sign_HarborHardware", "HARBOR HARDWARE", (31, 56, 43), (212, 178, 98)),
    ("Sign_ImmeubleBowWindows", "Sign_TidewaterBooks", "TIDEWATER BOOKS", (26, 27, 30), (226, 220, 200)),
    ("Sign_ImmeubleImprimeur", "Sign_PenobscotDrug", "PENOBSCOT DRUG CO.", (88, 33, 31), (214, 182, 104)),
    ("Sign_ImmeubleJardinHiver", "Sign_SeaSmokeCafe", "SEA SMOKE CAFE", (34, 45, 64), (230, 224, 204)),
    ("Sign_CoureePompe", "Sign_KnoxDryGoods", "KNOX DRY GOODS", (26, 27, 30), (212, 178, 98)),
    ("Sign_PensionDockers", "Sign_BalsamBakery", "BALSAM BAKERY", (31, 56, 43), (232, 226, 206)),
    ("Sign_LavoirHabite", "Sign_SaltPier", "SALT PIER PROVISIONS", (88, 33, 31), (232, 226, 206)),
    ("Sign_HotelMeublePort", "Sign_GullRock", "GULL ROCK OUTFITTERS", (34, 45, 64), (212, 178, 98)),
]
FONT = "C:/Windows/Fonts/georgiab.ttf"

# Cottage Flats name boards (2026-11-15, the author: lean into Boardwalk Empire / Atlantic City). Seaside boarding houses
# had their names painted on the verandah fascia, often after their avenue. Two unused New France square slots are
# each cut into four sign strips (a gap between them for the clamped gutters); same plate size as the shop signs.
HOTEL_PARENTS = ("Ivy", "SolarSlate")
HOTEL_SIGNS = [  # key, lettering, board colour, letter colour
    ("Sign_TheVentnor", "THE VENTNOR", (31, 56, 43), (212, 178, 98)),
    ("Sign_ThePacific", "THE PACIFIC", (34, 45, 64), (226, 220, 200)),
    ("Sign_TheStJames", "THE ST. JAMES", (88, 33, 31), (214, 182, 104)),
    ("Sign_TheIllinois", "THE ILLINOIS", (26, 27, 30), (212, 178, 98)),
    ("Sign_TheKentucky", "THE KENTUCKY", (31, 56, 43), (232, 226, 206)),
    ("Sign_TheChelsea", "THE CHELSEA", (34, 45, 64), (212, 178, 98)),
    ("Sign_TheMargate", "THE MARGATE", (88, 33, 31), (232, 226, 206)),
    ("Sign_TheBrighton", "THE BRIGHTON", (26, 27, 30), (226, 220, 200)),
]

# Grand Hotels name boards (2026-11-15, the author: the High rung "on steroids"): the next eight Atlantic City avenues, cut
# the same way from two more unused square slots.
GRAND_PARENTS = ("Mustard", "RenderSage")
GRAND_SIGNS = [
    ("Sign_TheAtlantic", "THE ATLANTIC", (26, 27, 30), (212, 178, 98)),
    ("Sign_TheTennessee", "THE TENNESSEE", (88, 33, 31), (232, 226, 206)),
    ("Sign_TheNewYork", "THE NEW YORK", (34, 45, 64), (212, 178, 98)),
    ("Sign_TheVirginia", "THE VIRGINIA", (31, 56, 43), (226, 220, 200)),
    ("Sign_TheOriental", "THE ORIENTAL", (88, 33, 31), (214, 182, 104)),
    ("Sign_TheVermont", "THE VERMONT", (26, 27, 30), (226, 220, 200)),
    ("Sign_TheStates", "THE STATES", (34, 45, 64), (232, 226, 206)),
    ("Sign_ThePennsylvania", "THE PENNSYLVANIA", (31, 56, 43), (212, 178, 98)),
]

# Boardwalk name boards (2026-11-15, the author: "commercial boardwalk low/high"): made-up seaside businesses, painted on the
# arcade beams. Four more unused square slots, cut four ways like the hotel boards.
SHOP_PARENTS = ("RenderOchre", "CopperVent")
SHOP_SIGNS = [
    ("Sign_SaltWaterTaffy", "SALT WATER TAFFY", (88, 33, 31), (232, 226, 206)),
    ("Sign_PennyArcade", "PENNY ARCADE", (26, 27, 30), (212, 178, 98)),
    ("Sign_OysterHouse", "OYSTER HOUSE", (34, 45, 64), (226, 220, 200)),
    ("Sign_FudgeKitchen", "FUDGE KITCHEN", (31, 56, 43), (232, 226, 206)),
    ("Sign_BathHouses", "BATH HOUSES", (34, 45, 64), (212, 178, 98)),
    ("Sign_TintypeStudio", "TINTYPE STUDIO", (26, 27, 30), (226, 220, 200)),
    ("Sign_ClamShack", "STEAMED CLAMS", (88, 33, 31), (214, 182, 104)),
    ("Sign_KiteShop", "KITES & PAILS", (31, 56, 43), (212, 178, 98)),
]
PALACE_PARENTS = ("YardSetts", "Ashlar")
PALACE_SIGNS = [
    ("Sign_GrandArcade", "GRAND ARCADE", (26, 27, 30), (212, 178, 98)),
    ("Sign_Emporium", "THE EMPORIUM", (88, 33, 31), (232, 226, 206)),
    ("Sign_MusicHall", "MUSIC HALL", (34, 45, 64), (212, 178, 98)),
    ("Sign_RollerRink", "ROLLER RINK", (31, 56, 43), (232, 226, 206)),
    ("Sign_Natatorium", "NATATORIUM", (34, 45, 64), (226, 220, 200)),
    ("Sign_PicturePalace", "PICTURE PALACE", (88, 33, 31), (214, 182, 104)),
    ("Sign_Ballroom", "BALLROOM", (26, 27, 30), (226, 220, 200)),
    ("Sign_SeasideMarket", "SEASIDE MARKET", (31, 56, 43), (212, 178, 98)),
]

# Cannery Row name boards (2026-11-15): the firms' names on the loading-dock canopy beams. Two more unused square
# slots (New France leftovers), cut four ways like the hotel boards.
CANNERY_PARENTS = ("RenderRose", "GardenGlass")
CANNERY_SIGNS = [
    ("Sign_QuoddyPacking", "QUODDY PACKING CO.", (88, 33, 31), (232, 226, 206)),
    ("Sign_SmokedHerring", "SMOKED HERRING", (26, 27, 30), (212, 178, 98)),
    ("Sign_LiveLobsters", "LIVE LOBSTERS", (34, 45, 64), (226, 220, 200)),
    ("Sign_HarborIce", "HARBOR ICE CO.", (31, 56, 43), (232, 226, 206)),
    ("Sign_CordageWorks", "CORDAGE WORKS", (88, 33, 31), (214, 182, 104)),
    ("Sign_SailLoft", "SAIL LOFT", (34, 45, 64), (212, 178, 98)),
    ("Sign_BoatBuilders", "BOAT BUILDERS", (31, 56, 43), (212, 178, 98)),
    ("Sign_Cooperage", "COOPERAGE", (26, 27, 30), (226, 220, 200)),
]


def sign_tile(text, board, ink, size, aspect=None):
    """A painted signboard: board colour, a thin inset line and centred serif capitals (drawn 4x, then reduced).
    aspect: the plate's true width/height, when the atlas cell has a different shape (drawn true, then squeezed)."""
    from PIL import ImageDraw, ImageFont
    w, h = size
    W = w * 4
    H = round(W / aspect) if aspect else h * 4
    im = Image.new("RGB", (W, H), board)
    d = ImageDraw.Draw(im)
    m = max(2, H // 12)
    d.rectangle([m, m, W - 1 - m, H - 1 - m], outline=ink, width=max(2, H // 40))
    fs = int(H * .52)
    while fs > 6:
        f = ImageFont.truetype(FONT, fs)
        x0, y0, x1, y1 = d.textbbox((0, 0), text, font=f)
        if x1 - x0 <= W * .86:
            break
        fs -= 2
    d.text(((W - (x1 - x0)) / 2 - x0, (H - (y1 - y0)) / 2 - y0), text, font=f, fill=ink)
    colour = im.resize(size, Image.Resampling.LANCZOS).convert("RGBA")
    mask = Image.merge("RGBA", (Image.new("L", size, 0), Image.new("L", size, 255),
                                Image.new("L", size, 0), Image.new("L", size, 60)))     # painted wood: matt
    return dict(BaseColor=colour, Normal=Image.new("RGBA", size, (128, 128, 255, 255)), MaskMap=mask,
                ControlMask=Image.new("RGBA", size, (0, 0, 0, 0)), Emissive=Image.new("RGBA", size, (0, 0, 0, 255)))


def paint_signs(lay):
    """Rename the old inscription slots and paint the shop signs into all three LODs (idempotent)."""
    for lod, suf, dim in STEPS:
        cells = lay["lods"][lod]
        for old, new, *_ in SIGNS:
            if old in cells:
                cells[new] = cells.pop(old)
            cells[new]["metres"] = list(SIGN_M)
        B = boxes(cells, dim)
        ims = {mp: Image.open(G / "atlas_template" / f"TEMPLATE{suf}_{mp}.png").convert("RGBA") for mp in MAPS}
        for _, new, text, board, ink in SIGNS:
            x0, y0, x1, y1 = B[new]
            for mp, im in sign_tile(text, board, ink, (x1 - x0, y1 - y0)).items():
                ims[mp].paste(im, (x0, y0))
        for mp, im in ims.items():
            im.save(G / "atlas_template" / f"TEMPLATE{suf}_{mp}.png")
    if isinstance(lay.get("order"), list):
        ren = {o: n for o, n, *_ in SIGNS}
        lay["order"] = [ren.get(o, o) for o in lay["order"]]
    LAYOUT.write_text(json.dumps(lay, indent=2), encoding="utf-8")
    print("signs painted:", ", ".join(s[1] for s in SIGNS))


def paint_hotel_signs(lay, HOTEL_PARENTS=HOTEL_PARENTS, HOTEL_SIGNS=HOTEL_SIGNS):
    """Cut each parent slot into four sign strips (all LODs) and paint the boarding-house name boards (idempotent:
    once cut, it repaints the strips). Also used for the Grand Hotels' boards."""
    per = len(HOTEL_SIGNS) // len(HOTEL_PARENTS)
    for lod, suf, dim in STEPS:
        cells = lay["lods"][lod]
        gap = max(2, dim // 512) / dim
        for j, parent in enumerate(HOTEL_PARENTS):
            if parent not in cells:
                continue
            x, b, r, t = cells.pop(parent)["uv"]
            h = (t - b - (per - 1) * gap) / per
            for i, (key, *_) in enumerate(HOTEL_SIGNS[j * per:(j + 1) * per]):
                top = t - i * (h + gap)
                cells[key] = {"uv": [x, top - h, r, top], "metres": list(SIGN_M)}
        B = boxes(cells, dim)
        ims = {mp: Image.open(G / "atlas_template" / f"TEMPLATE{suf}_{mp}.png").convert("RGBA") for mp in MAPS}
        for key, text, board, ink in HOTEL_SIGNS:
            x0, y0, x1, y1 = B[key]
            for mp, im in sign_tile(text, board, ink, (x1 - x0, y1 - y0), SIGN_M[0] / SIGN_M[1]).items():
                ims[mp].paste(im, (x0, y0))
        for mp, im in ims.items():
            im.save(G / "atlas_template" / f"TEMPLATE{suf}_{mp}.png")
    if isinstance(lay.get("order"), list):
        order = [o for o in lay["order"] if o not in HOTEL_PARENTS]
        lay["order"] = order + [k for k, *_ in HOTEL_SIGNS if k not in order]
    LAYOUT.write_text(json.dumps(lay, indent=2), encoding="utf-8")
    print("name boards painted:", ", ".join(k for k, *_ in HOTEL_SIGNS))


# Shore Rows painted ladies (the author 2026-11-17, Direction B): three procedural Victorian claddings, painted through the
# ControlMask R channel (colour 0, the accent colour of a painted-lady scheme; every other zone keeps colour 0 white).
# RoofGreen (unused since the chateau) is cut in two: fishscale shingle over board-and-batten. The CourtGlass strip
# becomes the diamond band. Metres along the tile (LOD0 and LOD1 alike, so the band stays on its grid); the height
# follows the cell's pixel shape; LOD2 averages (174 m like the kit's wood).
VIC_SPLIT = ("RoofGreen", (("Fishscale", 1.2), ("BoardBatten", 2.4)))
VIC_RENAME = ("CourtGlass", "DiamondBand", 2.4)


def _periodic_grain(rng, h, w, run=9):
    """Wood grain that tiles: per-pixel noise smeared along the boards (vertical) with a wrapped box filter."""
    n = rng.normal(0, 1, (h, w)).astype(np.float32)
    acc = np.zeros_like(n)
    for k in range(-run, run + 1):
        acc += np.roll(n, k, axis=0)
    return acc / math.sqrt(2 * run + 1)


def _normal_of(hgt, strength):
    """GL normal map (G up) from a height map, wrapped at the tile edges."""
    gx = (np.roll(hgt, -1, axis=1) - np.roll(hgt, 1, axis=1)) * .5 * strength
    gy = (np.roll(hgt, -1, axis=0) - np.roll(hgt, 1, axis=0)) * .5 * strength     # rows run down the tile
    n = np.dstack([-gx, gy, np.ones_like(hgt)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return Image.fromarray(np.dstack([(n + 1) * 127.5, np.full(hgt.shape, 255.0)]).clip(0, 255).astype("uint8"), "RGBA")


def _maps(shade, hgt, strength, rng, smooth=58):
    h, w = shade.shape
    grain = _periodic_grain(rng, h, w)
    c = np.array((236, 234, 228), np.float32)[None, None, :] * (shade * (1 + .025 * grain))[:, :, None]
    colour = Image.fromarray(c.clip(0, 255).astype("uint8"), "RGB").convert("RGBA")
    ao = Image.fromarray((150 + 105 * shade.clip(0, 1)).astype("uint8"), "L")
    mask = Image.merge("RGBA", (Image.new("L", (w, h), 0), ao, Image.new("L", (w, h), 0), Image.new("L", (w, h), smooth)))
    return dict(BaseColor=colour, Normal=_normal_of(hgt, strength), MaskMap=mask)


def shingle_tile(size, ncol, nrow, shape, rise, seed):
    """Fancy-cut shingles in staggered courses (nrow even, so the stagger tiles): 'round' butts (fishscale) or
    'point' butts (pointed shingles, which read as diamonds in a band). Each course's butt hangs over the course
    below: a shadow under every butt line, dark keyways between shingles, a slight tone change shingle to shingle."""
    w, h = size
    rng = np.random.default_rng(seed)
    X, Y = np.meshgrid((np.arange(w) + .5) / w * ncol, (np.arange(h) + .5) / h * nrow)

    def butt(k):                                     # the butt line of course k (in course units, downwards)
        dx = ((X - .5 * (k % 2)) % 1) - .5
        prof = 1 - np.sqrt(np.clip(1 - (2 * dx) ** 2, 0, 1)) if shape == "round" else np.abs(2 * dx)
        return k + 1 - rise * prof

    k0 = np.floor(Y)
    k = np.where(Y >= butt(k0), k0 + 1, k0)
    above, own = butt(k - 1), butt(k)
    s = (Y - above) / (own - above)                  # 0 just under the butt above, 1 at this shingle's own butt
    dx = ((X - .5 * (k % 2)) % 1) - .5
    shade = 1 - .42 * np.clip(1 - s / .22, 0, 1) ** 1.6 - .08 * np.clip((s - .9) / .1, 0, 1)
    shade *= np.where(np.abs(dx) > .5 - .035, .7, 1.0)                       # keyways
    ids = ((k % nrow) * ncol + np.floor((X - .5 * (k % 2)) % ncol)).astype(int)
    tone = rng.uniform(.95, 1.04, nrow * ncol + 1)[ids]
    hgt = .4 + .6 * np.clip(s, 0, 1)                 # thicker towards the butt, a step down past it
    return _maps((shade * tone).astype(np.float32), hgt.astype(np.float32), 9.0 * ncol / 8, rng)


def batten_tile(size, nboard, seed):
    """Board-and-batten: wide vertical boards, a raised batten over every joint casting a shadow to its right."""
    w, h = size
    rng = np.random.default_rng(seed)
    X = np.broadcast_to((np.arange(w) + .5) / w * nboard, (h, w))
    f = X % 1                                        # 0 at a joint
    d = np.minimum(f, 1 - f)                         # distance to the nearest joint, in boards
    bw = .11                                         # half a batten
    hgt = np.clip((bw - d) / .03, 0, 1)              # battens raised, bevelled edges
    shade = np.ones((h, w), np.float32)
    shade -= .42 * np.clip(1 - (f - bw) / .16, 0, 1) * (f > bw)              # shadow right of each batten
    shade += .12 * ((d < bw) & (f > .5))                                      # the lit left bevel
    tone = rng.uniform(.96, 1.03, nboard)[np.floor(X).astype(int) % nboard]
    return _maps((shade * tone).astype(np.float32), hgt.astype(np.float32), 6.0, rng, smooth=52)


def vic_tiles(key, size):
    if key == "Fishscale":
        return shingle_tile(size, 8, 4, "round", .5, 21)
    if key == "DiamondBand":
        return shingle_tile(size, 16, 2, "point", .62, 22)
    return batten_tile(size, 8, 23)


def paint_victorian(lay):
    """Cut RoofGreen into Fishscale over BoardBatten, rename CourtGlass to DiamondBand, and paint all three into
    every map and LOD (idempotent: once cut and renamed, it repaints)."""
    old, parts = VIC_SPLIT
    for lod, suf, dim in STEPS:
        cells = lay["lods"][lod]
        if old in cells:
            x, b, r, t = cells.pop(old)["uv"]
            gap = max(2, dim // 512) / dim
            hh = (t - b - gap) / 2
            cells[parts[0][0]] = {"uv": [x, t - hh, r, t]}
            cells[parts[1][0]] = {"uv": [x, b, r, b + hh]}
        if VIC_RENAME[0] in cells:
            cells[VIC_RENAME[1]] = {"uv": cells.pop(VIC_RENAME[0])["uv"]}
        B = boxes(cells, dim)
        ims = {mp: Image.open(G / "atlas_template" / f"TEMPLATE{suf}_{mp}.png").convert("RGBA") for mp in MAPS}
        for key, mx in parts + ((VIC_RENAME[1], VIC_RENAME[2]),):
            x0, y0, x1, y1 = B[key]
            size = (x1 - x0, y1 - y0)
            for mp, im in vic_tiles(key, size).items():
                ims[mp].paste(im, (x0, y0))
            ims["Emissive"].paste((0, 0, 0, 255), (x0, y0, x1, y1))
            mx = 174.0 if lod == "_LOD2" else mx
            cells[key]["metres"] = [mx, round(mx * size[1] / size[0], 4)]
        for mp, im in ims.items():
            im.save(G / "atlas_template" / f"TEMPLATE{suf}_{mp}.png")
    if isinstance(lay.get("order"), list):
        ren = {old: parts[0][0], VIC_RENAME[0]: VIC_RENAME[1]}
        order = [ren.get(o, o) for o in lay["order"]]
        lay["order"] = order + [parts[1][0]] * (parts[1][0] not in order)
    LAYOUT.write_text(json.dumps(lay, indent=2), encoding="utf-8")
    print("Victorian claddings painted:", ", ".join(k for k, _ in parts), "and", VIC_RENAME[1])


def main():
    import sys
    if "--check" in sys.argv:
        check_tint()
        return check_gutters()
    lay = json.loads(LAYOUT.read_text())
    todo = {k: s for k, s in SWAPS.items() if k not in lay["lods"]["main"]}
    if not todo:
        paint_signs(lay)
        paint_hotel_signs(lay)
        paint_hotel_signs(lay, GRAND_PARENTS, GRAND_SIGNS)
        paint_hotel_signs(lay, SHOP_PARENTS, SHOP_SIGNS)
        paint_hotel_signs(lay, PALACE_PARENTS, PALACE_SIGNS)
        paint_hotel_signs(lay, CANNERY_PARENTS, CANNERY_SIGNS)
        paint_victorian(lay)
        paint_tint(lay)
        fill_gutters(lay)
        check_tint()
        return check_gutters()
    for lod, suf, dim in STEPS:
        cells = lay["lods"][lod]
        ims = {m: Image.open(G / "atlas_template" / f"TEMPLATE{suf}_{m}.png").convert("RGBA")
               for m in ("BaseColor", "Normal", "MaskMap", "ControlMask", "Emissive")}
        for key, spec in todo.items():
            cell = cells.pop(spec[0])
            x, b, r, t = cell["uv"]
            box = tuple(round(v * dim) for v in (x, 1 - t, r, 1 - b))
            size = (box[2] - box[0], box[3] - box[1])
            for m, im in tiles(spec, size).items():
                ims[m].paste(im, box[:2])
            ims["ControlMask"].paste((0, 0, 0, 0), box)
            ims["Emissive"].paste((0, 0, 0, 255), box)
            mt = spec[4][[st[0] for st in STEPS].index(lod)]
            cell["metres"] = [mt, mt]
            cells[key] = cell
        for m, im in ims.items():
            im.save(G / "atlas_template" / f"TEMPLATE{suf}_{m}.png")
    order = lay.get("order")
    if isinstance(order, list):
        lay["order"] = [next((k for k, s in todo.items() if s[0] == o), o) for o in order]
    LAYOUT.write_text(json.dumps(lay, indent=2), encoding="utf-8")
    print("swapped:", ", ".join(f"{s[0]} -> {k}" for k, s in todo.items()))
    fill_gutters(lay)
    check_gutters()


if __name__ == "__main__":
    main()
