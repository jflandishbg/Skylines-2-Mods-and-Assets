"""Park-monument atlas (Claude, 2026-11-09). One 4096 sheet of 16 swatches shared by every monument.
Run with the normal Python:  python make_atlas.py <out_dir>
Writes Atlas_{BaseColor,Normal,MaskMap,ControlMask,Emissive}.png at 4096, plus _LOD1 (2048) and _LOD2 (1024).
Sources are the CC0 ambientCG materials in NewFrance/textures (safe to publish)."""
import os, sys, glob
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = sys.argv[1]
TEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "textures")
T, P, N = 1024, 400, 4                      # tile px, px per texture repeat (tile = 2.56 repeats), tiles per side
rng = np.random.default_rng(1876)

def src(name, kind):
    f = glob.glob(os.path.join(TEX, "*", name, f"{name}_2K-PNG_{kind}.png"))
    return np.asarray(Image.open(f[0]).convert("RGB").resize((P, P), Image.LANCZOS), dtype=np.float32) / 255 if f else None

def tile3(a):                               # repeat a P-px patch across a T-px tile
    return np.tile(a, (3, 3, 1) if a.ndim == 3 else (3, 3))[:T, :T]

def noise(scale, octaves=4):                # tileable noise (periodic, so repeats join invisibly)
    out = np.zeros((P, P), np.float32)
    fy, fx = np.meshgrid(np.fft.fftfreq(P), np.fft.fftfreq(P), indexing="ij")
    for o in range(octaves):
        s = scale / (2 ** o)
        f = np.fft.fft2(rng.standard_normal((P, P))) * np.exp(-(fx ** 2 + fy ** 2) * (s * P) ** 2 * 2)
        n = np.real(np.fft.ifft2(f)); out += (n - n.mean()) / (n.std() + 1e-9) / (1.6 ** o)
    return (out - out.min()) / (out.max() - out.min())

def normal_from(h, strength):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * strength; dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * strength
    n = np.dstack([-dx, dy, np.ones_like(h)]); n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n * .5 + .5

def lum(c): return c @ np.array([.3, .59, .11], np.float32)

def photo(name, mult=(1, 1, 1), tint=None, contrast=1.0, metal=0.0, smooth_scale=.55, smooth_add=0.0):
    c = src(name, "Color"); n = src(name, "NormalGL"); r = src(name, "Roughness")
    if tint is not None:
        l = lum(c); l = 1 + contrast * (l / l.mean() - 1); c = np.clip(l[..., None] * np.array(tint, np.float32), 0, 1)
    c = np.clip(c * np.array(mult, np.float32), 0, 1)
    s = np.clip((1 - lum(r)) * smooth_scale + smooth_add, 0, 1) if r is not None else np.full((P, P), .2, np.float32)
    return c, (n if n is not None else np.dstack([np.full((P, P), .5)] * 2 + [np.ones((P, P))])), np.full((P, P), metal, np.float32), s

def proc(colour, scale, amount, bump, metal, smooth, colour2=None):
    h = noise(scale); c = np.array(colour, np.float32) * (1 + amount * (h[..., None] - .5) * 2)
    if colour2 is not None:
        m = noise(scale * 4, 2)[..., None]; c = c * (1 - m * .5) + np.array(colour2, np.float32) * m * .5
    return np.clip(c, 0, 1), normal_from(h, bump), np.full((P, P), metal, np.float32), np.full((P, P), smooth, np.float32)

SMOOTH_STONE = dict(tint=(.80, .755, .66), contrast=.55, smooth_scale=.35)
TILES = [
    photo("Bricks084", tint=(.80, .74, .63), contrast=.85, smooth_scale=.3),                        # 0 ASH   limestone ashlar
    photo("Plaster001", **SMOOTH_STONE),                                               # 1 SMO   dressed limestone
    photo("PavingStones108", mult=(.93, .91, .87), smooth_scale=.35),                  # 2 PAV   paving
    proc((.70, .63, .50), .012, .16, 9, 0, .12, colour2=(.60, .55, .46)),              # 3 GRV   stabilised gravel
    photo("Metal032", tint=(.085, .165, .125), contrast=.5, metal=.25, smooth_scale=.5, smooth_add=.15),   # 4 IRON  park green iron
    proc((.33, .55, .47), .05, .22, 3, .35, .35, colour2=(.22, .36, .30)),             # 5 VERD  verdigris copper
    proc((.10, .25, .25), .09, .25, 1.5, 0, .93, colour2=(.16, .36, .33)),             # 6 WATER
    proc((.80, .60, .22), .08, .10, 1, 1, .72),                                        # 7 GILT
    photo("Planks023A", mult=(1.05, 1.0, .95), smooth_scale=.4),                       # 8 WOOD  bandstand floor
    photo("Bricks066", mult=(.88, .86, .84), smooth_scale=.4),                         # 9 GRAN  grey base courses
    photo("MetalPlates005", tint=(.36, .40, .43), contrast=.8, metal=.7, smooth_scale=.6, smooth_add=.1),  # 10 ZINC
    None,                                                                              # 11 POST  posters (drawn below)
    None,                                                                              # 12 INSC  inscriptions (drawn below)
    photo("Bricks102", tint=(.66, .61, .52), contrast=.9, smooth_scale=.25),           # 13 RUST  rusticated grotto stone
    photo("Plaster001", tint=(.40, .37, .33), contrast=.5, smooth_scale=.3),           # 14 SHADE niche interiors
    proc((.15, .27, .11), .006, .45, 14, 0, .18, colour2=(.24, .36, .14)),             # 15 HEDGE clipped box
]

def font(size, bold=True):
    for f in (("georgiab.ttf", "timesbd.ttf") if bold else ("georgia.ttf", "times.ttf")):
        try: return ImageFont.truetype(os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts", f), size)
        except OSError: pass
    return ImageFont.load_default()

def fit_text(d, box, text, fill, maxsize=200, bold=True, spacing=0):
    x0, y0, x1, y1 = box; size = maxsize
    while size > 8:
        f = font(size, bold); l, t, r, b = d.textbbox((0, 0), text, font=f)
        if r - l <= (x1 - x0) and b - t <= (y1 - y0): break
        size -= 2
    d.text(((x0 + x1) / 2 - (r - l) / 2 - l, (y0 + y1) / 2 - (b - t) / 2 - t), text, font=f, fill=fill)

INSCRIPTIONS = ["AUX BATELIERS DES DEUX RIVES", "LA VILLE RECONNAISSANTE", "FONTAINE DE LA GROTTE",
                "À L’ÉCLUSE · MDCCCXXXIV", "MDCCCLXXVI", "KIOSQUE DES MARINIERS"]
def inscription_tile():
    c, n, m, s = photo("Plaster001", **SMOOTH_STONE)
    base = Image.fromarray((tile3(c) * 255).astype(np.uint8)); mask = Image.new("L", (T, T), 0); d = ImageDraw.Draw(mask)
    rows = len(INSCRIPTIONS); rh = T // rows
    for i, text in enumerate(INSCRIPTIONS):
        fit_text(d, (40, i * rh + 34, T - 40, (i + 1) * rh - 34), text, 255)
    mk = np.asarray(mask, np.float32) / 255
    col = np.asarray(base, np.float32) / 255 * (1 - mk[..., None] * .62)            # letters cut and shadowed
    nrm = tile3(n).copy(); cut = normal_from(-mk, 2.5); nrm = np.where(mk[..., None] > .02, cut * .6 + nrm * .4, nrm)
    return col, nrm, tile3(m), tile3(s)

POSTERS = [("OPÉRA", "des Deux Rives", (.72, .16, .12), (.95, .90, .76)), ("GRAND BAL", "du Quai", (.93, .87, .70), (.13, .22, .36)),
           ("CIRQUE", "d’Hiver", (.85, .62, .15), (.16, .12, .10)), ("RÉGATES", "sur la Delaware", (.16, .33, .42), (.95, .92, .82)),
           ("THÉÂTRE", "des Lanternes", (.20, .30, .20), (.93, .85, .55)), ("CONCERT", "au Kiosque", (.92, .88, .78), (.60, .14, .12)),
           ("EXPOSITION", "Universelle", (.55, .22, .30), (.95, .90, .80)), ("CHOCOLAT", "de la Ruelle", (.30, .18, .12), (.92, .80, .50))]
def poster_tile():
    im = Image.new("RGB", (T, T), (60, 70, 62)); d = ImageDraw.Draw(im); w, h = T // 4, T // 2
    for i, (a, b, bg, fg) in enumerate(POSTERS):
        x, y = (i % 4) * w, (i // 4) * h; B = tuple(int(v * 255) for v in bg); F = tuple(int(v * 255) for v in fg)
        d.rectangle((x + 8, y + 8, x + w - 8, y + h - 8), fill=B)
        d.rectangle((x + 20, y + 20, x + w - 20, y + h - 20), outline=F, width=4)
        fit_text(d, (x + 30, y + 60, x + w - 30, y + 170), a, F, 90)
        d.ellipse((x + w / 2 - 55, y + 195, x + w / 2 + 55, y + 305), outline=F, width=5)
        d.line((x + 40, y + 345, x + w - 40, y + 345), fill=F, width=3)
        fit_text(d, (x + 30, y + 360, x + w - 30, y + 430), b, F, 44, bold=False)
        fit_text(d, (x + 30, y + 440, x + w - 30, y + 480), "TOUS LES SOIRS", F, 22)
    c = np.asarray(im, np.float32) / 255 * (.9 + .1 * tile3(noise(.03))[..., None])    # a little weathering
    flat = np.dstack([np.full((T, T), .5, np.float32)] * 2 + [np.ones((T, T), np.float32)])
    return c * .92, flat, np.zeros((T, T), np.float32), np.full((T, T), .22, np.float32)

S = T * N
col = np.zeros((S, S, 3), np.float32); nrm = np.zeros((S, S, 3), np.float32); met = np.zeros((S, S), np.float32); smo = np.zeros((S, S), np.float32)
for i, t in enumerate(TILES):
    c, n, m, s = poster_tile() if i == 11 else inscription_tile() if i == 12 else tuple(tile3(a) for a in t)
    y, x = (i // N) * T, (i % N) * T
    col[y:y + T, x:x + T], nrm[y:y + T, x:x + T], met[y:y + T, x:x + T], smo[y:y + T, x:x + T] = c, n, m, s

def u8(a): return (np.clip(a, 0, 1) * 255 + .5).astype(np.uint8)
alpha = np.full((S, S), 255, np.uint8); zero = np.zeros((S, S), np.uint8)
maps = {"BaseColor": Image.fromarray(np.dstack([u8(col), alpha]), "RGBA"),
        "Normal": Image.fromarray(np.dstack([u8(nrm), alpha]), "RGBA"),
        "MaskMap": Image.fromarray(np.dstack([u8(met), zero, zero, u8(smo)]), "RGBA"),      # R metal, G coat, A smoothness
        "ControlMask": Image.fromarray(np.dstack([zero, zero, zero, zero]), "RGBA"),          # no colour variation
        "Emissive": Image.fromarray(np.dstack([zero, zero, zero, alpha]), "RGBA")}           # never glows
os.makedirs(OUT, exist_ok=True)
for lod, size in (("", S), ("_LOD1", S // 2), ("_LOD2", S // 4)):
    for k, im in maps.items():
        (im if size == S else im.resize((size, size), Image.LANCZOS)).save(os.path.join(OUT, f"Atlas{lod}_{k}.png"))
print("atlas written to", OUT)
