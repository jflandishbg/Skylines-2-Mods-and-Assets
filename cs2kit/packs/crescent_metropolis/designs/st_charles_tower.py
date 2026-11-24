"""St. Charles Exchange (ZH1, 4x5 lot): 12-storey Creole Beaux-Arts high-rise with podium iron arcade, loggia balconies, and twin copper belvederes."""
from cs2kit.kit import E, Mesh, finish, lbox, style, wall, wbox
from cs2kit.shapes import cornice_roof, dome, pavilion_roof
from .creole_kit import iron_gallery_run, iron_ground_arcade

WAIVE = {"balance": "grand hotel podium & shaft", "corners": "arched arcade bays"}


def _bays(a: float, b: float, step: float = 3.1, edge: float = 1.65) -> list[float]:
    inner = b - a - 2.0 * edge
    k = max(1, round(inner / step))
    return [a + edge + inner * i / k for i in range(k + 1)]


def _piers(m: Mesh, w, bays: list[float], z0: float, z1: float, lod: int, mat: str = "Dressed"):
    if lod == 2 or len(bays) < 2:
        return
    us = sorted(w.u_of(c) for c in bays)
    mids = [(a + b) * 0.5 for a, b in zip(us, us[1:]) if b - a >= 2.2]
    for u in [0.45] + mids + [w.L - 0.45]:
        lbox(m, w, u - 0.22, u + 0.22, z0, z1, E, 0.14, mat)


def build(lod, W=4, D=5, **variant):
    # Lot: 32 x 40 m -> x: -16..+16, y: -20..+20
    XH = 4.0 * W - 1.2  # 14.8
    XL = -XH
    yF = -4.0 * D + 1.0  # -19.0
    yM = 4.0
    yR = 4.0 * D - 0.8  # 19.2
    wing_x = 5.4  # twin rear wings x: -14.8..-5.4 and +5.4..+14.8 -> 10.8 m courtyard

    G = 4.6
    F_POD = 3.6
    z_pod = G + F_POD  # 8.2

    m, g = Mesh(), Mesh()

    # ---- 1. Limestone 2-storey U-shaped Podium (z = 0..8.2)
    win_pod = [(1.55, 0.90, 3.85, "bay"), (1.15, G + 0.85, G + 2.75)]
    st_pod = style(z_pod, [(0.0, z_pod, "Dressed")], win_pod, belts=(G,), plinth=None, corners=False, frieze=0.35, belt_mat="Dressed")
    trim_pod = dict(frame="CastIron", door="Oxblood", masonry="Dressed", reveal="Dressed", arch=True, glazed=True, lites="6", lean=lod > 0)

    bays_pf = _bays(XL, XH, step=3.2, edge=1.7)
    bays_ps_bar = _bays(yF, yM, step=3.2, edge=1.7)
    bays_ps_wing = _bays(yM, yR, step=3.2, edge=1.7)
    bays_ps_all = sorted(bays_ps_bar + bays_ps_wing)
    bays_pw = _bays(wing_x, XH, step=3.0, edge=1.6)

    wall(m, g, st_pod, (XL, yF), (XH, yF), "x", "x", bays_pf, lod, trim=trim_pod, waive=WAIVE)
    wall(m, g, st_pod, (XH, yF), (XH, yR), "x", "x", bays_ps_all, lod, trim=trim_pod, waive=WAIVE)
    wall(m, g, st_pod, (XL, yR), (XL, yF), "x", "x", bays_ps_all[::-1], lod, trim=trim_pod, waive=WAIVE)
    # Rear ends of twin wings
    wall(m, g, st_pod, (XH, yR), (wing_x, yR), "x", "x", bays_pw[::-1], lod, trim=trim_pod, waive=WAIVE)
    wall(m, g, st_pod, (-wing_x, yR), (XL, yR), "x", "x", [-c for c in bays_pw[::-1]], lod, trim=trim_pod, waive=WAIVE)
    # Inner courtyard walls
    wall(m, g, st_pod, (wing_x, yR), (wing_x, yM), "x", "c", bays_ps_wing[::-1], lod, trim=trim_pod, waive=WAIVE)
    wall(m, g, st_pod, (-wing_x, yM), (-wing_x, yR), "c", "x", [-c for c in bays_ps_wing[::-1]], lod, trim=trim_pod, waive=WAIVE)
    bays_court = _bays(-wing_x, wing_x, step=3.2, edge=1.8)
    wall(m, g, st_pod, (wing_x - E, yM), (-wing_x + E, yM), "c", "c", bays_court[::-1], lod, trim=trim_pod, waive=WAIVE)

    # Podium roofs (closed cornice roofs)
    cornice_roof(m, XL - 0.15, XH + 0.15, yF - 0.15, yM, z_pod, lod, deep=0.45, top="TinFlat", side="Dressed")
    cornice_roof(m, wing_x - 0.15, XH + 0.15, yM + E, yR + 0.15, z_pod, lod, deep=0.45, top="TinFlat", side="Dressed")
    cornice_roof(m, XL - 0.15, -wing_x + 0.15, yM + E, yR + 0.15, z_pod, lod, deep=0.45, top="TinFlat", side="Dressed")

    # Continuous 2nd-floor cast-iron promenade gallery grounded on sidewalk banquette + arcade columns
    iron_ground_arcade(m, (XL + 0.4, yF), (XH - 0.4, yF), depth=0.85, z_top=G - 0.16 - E, lod=lod, cols_step=3.2)
    iron_gallery_run(m, (XL + 0.4, yF), (XH - 0.4, yF), depth=0.85, z_deck=G, z_top=z_pod - 0.15, lod=lod, roof=False, cols_step=3.2, end_rails=("l", "r"))

    # ---- 2. 8-Storey StuccoCoral Shaft (z = 8.65..34.65)
    z_s0 = z_pod + 0.45
    n_shaft = 8
    F_SH = 3.25
    z_s1 = z_s0 + n_shaft * F_SH  # 34.65
    sx0, sx1 = XL + 0.6, XH - 0.6  # -14.2 .. +14.2
    sy0, sy1 = yF + 0.25, yM - 0.4  # -18.75 .. +3.60

    win_sh = [(1.05, z_s0 + j * F_SH + 0.75, z_s0 + j * F_SH + 2.45) for j in range(n_shaft)]
    st_sh = style(
        z_s1,
        [(z_s0, z_s1, "StuccoCoral")],
        win_sh,
        belts=(z_s0 + 3 * F_SH, z_s0 + 6 * F_SH),
        plinth=None,
        corners=False,
        frieze=0.45,
        belt_mat="Dressed",
    )
    trim_sf = dict(frame="TrimWhite", door="Oxblood", shutters="CharlestonGreen", lites="6", lean="bare" if lod == 1 else False)
    trim_sr = dict(frame="TrimWhite", door="Oxblood", lites="2", simple=True, lite_above=12.0, lean="bare" if lod == 1 else False)

    bays_sf = _bays(sx0, sx1, step=3.1, edge=1.6)
    bays_ss = _bays(sy0, sy1, step=3.2, edge=1.6)

    wf = wall(m, g, st_sh, (sx0, sy0), (sx1, sy0), "x", "x", bays_sf, lod, z0=z_s0, trim=trim_sf, waive=WAIVE)
    _piers(m, wf, bays_sf, z_s0, z_s1 - 0.45 - E, lod)
    ws_r = wall(m, g, st_sh, (sx1, sy0), (sx1, sy1), "x", "x", bays_ss, lod, z0=z_s0, trim=trim_sr, waive=WAIVE)
    _piers(m, ws_r, bays_ss, z_s0, z_s1 - 0.45 - E, lod)
    ws_l = wall(m, g, st_sh, (sx0, sy1), (sx0, sy0), "x", "x", bays_ss[::-1], lod, z0=z_s0, trim=trim_sr, waive=WAIVE)
    _piers(m, ws_l, bays_ss[::-1], z_s0, z_s1 - 0.45 - E, lod)
    wr = wall(m, g, st_sh, (sx1, sy1), (sx0, sy1), "x", "x", bays_sf[::-1], lod, z0=z_s0, trim=trim_sr, waive=WAIVE)
    _piers(m, wr, bays_sf[::-1], z_s0, z_s1 - 0.45 - E, lod)

    # Stacked cast-iron loggia balconies along front (0.72 m deep, strictly inside podium gallery)
    for flr in (2, 4, 6):
        zb = z_s0 + flr * F_SH
        iron_gallery_run(
            m,
            (sx0 + 1.6, sy0),
            (sx1 - 1.6, sy0),
            depth=0.72,
            z_deck=zb,
            z_top=zb + F_SH,
            lod=lod,
            roof=False,
            columns=False,
            end_rails=("l", "r"),
        )

    cornice_roof(m, sx0 - 0.25, sx1 + 0.25, sy0 - 0.25, sy1 + 0.25, z_s1, lod, deep=0.55, top="TinFlat", side="Dressed")

    # ---- 3. 2-Storey Beaux-Arts Penthouse Pavilion + Twin Copper Belvederes (z = 35.2..47.5)
    z_p0 = z_s1 + 0.55
    z_p1 = z_p0 + 6.4
    px0, px1 = -9.0, 9.0
    py0, py1 = -15.2, -1.2

    win_ph = [(1.0, z_p0 + 0.7, z_p0 + 2.4), (0.95, z_p0 + 3.7, z_p0 + 5.3)]
    st_ph = style(z_p1, [(z_p0, z_p1, "StuccoCream")], win_ph, belts=(z_p0 + 3.1,), plinth=None, corners=False, frieze=0.35, belt_mat="Dressed")
    bays_pf_top = _bays(px0, px1, step=3.0, edge=1.5)
    bays_ps_top = _bays(py0, py1, step=3.0, edge=1.5)

    wall(m, g, st_ph, (px0, py0), (px1, py0), "x", "x", bays_pf_top, lod, z0=z_p0, trim=trim_sr, waive=WAIVE)
    wall(m, g, st_ph, (px1, py0), (px1, py1), "x", "x", bays_ps_top, lod, z0=z_p0, trim=trim_sr, waive=WAIVE)
    wall(m, g, st_ph, (px1, py1), (px0, py1), "x", "x", bays_pf_top[::-1], lod, z0=z_p0, trim=trim_sr, waive=WAIVE)
    wall(m, g, st_ph, (px0, py1), (px0, py0), "x", "x", bays_ps_top[::-1], lod, z0=z_p0, trim=trim_sr, waive=WAIVE)
    pavilion_roof(m, px0 - 0.30, px1 + 0.30, py0 - 0.30, py1 + 0.30, z_p1, 4.1, lod, "SlateDark", finial=True, trim_mat="Dressed")

    # Twin octagonal copper-domed belvederes flanking front corners (< 14 m2 each -> crown exempt)
    for cx in (-11.7, 11.7):
        cy = -16.0
        wbox(m, cx - 1.55, cx + 1.55, cy - 1.55, cy + 1.55, z_p0 - 0.1, z_p0 + 1.4, "Dressed")
        dome(m, g, cx, cy, 1.5, z_p0 + 1.4, lod, "TinGreen", "StuccoCream", drum=2.2, trim_mat="Dressed")

    finish(m, g)
