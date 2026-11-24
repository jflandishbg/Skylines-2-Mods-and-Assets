"""Royal Street Corner Gallery (ZM1, 2x3 LeftCorner): 3-storey French Quarter block with double-tiered iron lace galleries."""
from cs2kit.kit import E, Mesh, chimney, finish, party, style, wall
from cs2kit.shapes import dormer, pavilion_roof
from .creole_kit import gallery_corner_ground_arcade, gallery_corner_square, iron_gallery_run, iron_ground_arcade

WAIVE = {"balance": "French Quarter commercial corner block", "corners": "corner ground portals"}


def build(lod, W=2, D=3, **variant):
    X = 4.0 * W - 0.01
    XL = -4.0 * W + 1.15
    yF = -4.0 * D + 1.15
    yR = 4.0 * D - 0.60

    G = 4.20
    F1 = 3.50
    F2 = 3.30
    top = G + F1 + F2  # 11.0 m

    win_u = [(1.35, 0.85, 3.65, "bay"), (0.94, G + 0.65, G + 2.85), (0.90, G + F1 + 0.65, G + F1 + 2.70)]
    st = style(
        top,
        [(0.0, G, "Dressed"), (G, top, "StuccoOchre")],
        win_u,
        belts=(G, G + F1),
        plinth=None,
        corners=False,
        frieze=0.32,
        belt_mat="Dressed",
    )
    trim_g = dict(
        frame="CastIron",
        door="CharlestonGreen",
        masonry="Dressed",
        reveal="Dressed",
        arch=True,
        glazed=True,
        shutters="CharlestonGreen",
        lites="6",
        lean=lod > 0,
    )
    # Upper floors use TrimWhite sashes + CharlestonGreen shutters
    win_no_arch = [(0.94, 0.90, 2.95), (0.94, G + 0.65, G + 2.85), (0.90, G + F1 + 0.65, G + F1 + 2.70)]
    st_r = style(
        top,
        [(0.0, G, "Dressed"), (G, top, "StuccoOchre")],
        win_no_arch,
        belts=(G, G + F1),
        plinth=None,
        corners=False,
        frieze=0.32,
        belt_mat="Dressed",
    )
    trim_r = dict(frame="TrimWhite", door="Oxblood", shutters="CharlestonGreen", lites="6", lean=lod > 0)

    m, g = Mesh(), Mesh()

    # Front bays (-Y)
    bays_f = [XL + 1.45 + (X - XL - 2.9) * i / 4 for i in range(5)]
    wall(m, g, st, (XL, yF), (X, yF), "x", "-", bays_f, lod, trim=trim_g, waive=WAIVE)

    # Left side-street bays (-X)
    bays_s = [yF + 1.7 + (yR - yF - 3.4) * i / 6 for i in range(7)]
    wall(m, g, st, (XL, yR), (XL, yF), "x", "x", bays_s, lod, trim=trim_g, waive=WAIVE)

    # Rear facade (+Y)
    wall(m, g, st_r, (X, yR), (XL, yR), "-", "x", bays_f[::-1], lod, door=(bays_f[2], 1.15, 2.95), trim=trim_r, waive=WAIVE)

    # Right party wall (+X)
    party(m, (X, yF), (X, yR), 0.0, top, "StuccoOchre")

    # Double-tiered wrap-around cast-iron lace galleries grounded on sidewalk banquette + ground columns
    gal_d = 0.92
    z_tier1_top = G + F1 - 0.16 - E
    iron_ground_arcade(m, (XL, yF), (X, yF), depth=gal_d, z_top=G - 0.16 - E, lod=lod, cols_step=2.8, u_inset=(E, 0.15))
    iron_ground_arcade(m, (XL, yR), (XL, yF), depth=gal_d, z_top=G - 0.16 - E, lod=lod, cols_step=2.9, u_inset=(0.25, E))
    gallery_corner_ground_arcade(m, XL, yF, gal_d, G - 0.16 - E, lod)
    # Front runs
    iron_gallery_run(m, (XL, yF), (X, yF), depth=gal_d, z_deck=G, z_top=z_tier1_top, lod=lod, roof=False, end_rails=(), cols_step=2.8, u_inset=(E, 0.15))
    iron_gallery_run(m, (XL, yF), (X, yF), depth=gal_d, z_deck=G + F1, z_top=top - 0.18, lod=lod, roof=True, end_rails=(), cols_step=2.8, u_inset=(E, 0.15))
    # Left side runs
    iron_gallery_run(m, (XL, yR), (XL, yF), depth=gal_d, z_deck=G, z_top=z_tier1_top, lod=lod, roof=False, end_rails=("l",), cols_step=2.9, u_inset=(0.25, E))
    iron_gallery_run(m, (XL, yR), (XL, yF), depth=gal_d, z_deck=G + F1, z_top=top - 0.18, lod=lod, roof=True, end_rails=("l",), cols_step=2.9, u_inset=(0.25, E))
    # Clean corner connectors
    gallery_corner_square(m, XL, yF, gal_d, G, z_tier1_top, lod, roof=False)
    gallery_corner_square(m, XL, yF, gal_d, G + F1, top - 0.18, lod, roof=True)

    # Steep hipped slate pavilion roof with front & left dormers
    over = 0.30
    rise = 3.60
    pavilion_roof(m, XL - over, X - E, yF - over, yR + over, top, rise, lod, "SlateDark", finial=False)

    # Front dormers (on -Y hip slope)
    rate_f = rise / 7.3
    top_f = lambda o: top + 0.16 + (yF - over + 7.3 - o) * rate_f if False else top + 0.16 + max(0.0, (yF - o) * rate_f)
    # Front slope rises inward (+Y) from yF - over: o runs outward (-Y) so P(o, t, z) = (t, yF - o, z)
    P_front = lambda o, t, z: (t, yF - o, z)
    rt_front = lambda o: top + 0.16 + (over - o) * (rise / 7.2)
    dtrim = dict(frame="TrimWhite", lites="6", lean=lod > 0)
    for cx in (bays_f[1], bays_f[3]):
        dormer(m, g, P_front, rt_front, -1.35, cx, 1.35, lod, "StuccoOchre", "SlateDark", dtrim, rise=0.72, height=1.35)

    P_left = lambda o, t, z: (XL - o, t, z)
    rt_left = lambda o: top + 0.16 + (over - o) * (rise / 7.2)
    for cy in (bays_s[1], bays_s[3], bays_s[5]):
        dormer(m, g, P_left, rt_left, -1.35, cy, 1.35, lod, "StuccoOchre", "SlateDark", dtrim, rise=0.72, height=1.35)

    chimney(m, X - 1.2, (yF + yR) * 0.5 - 2.0, 0.42, 0.55, top + 2.2, top + 4.3, lod)
    chimney(m, X - 1.2, (yF + yR) * 0.5 + 3.0, 0.42, 0.55, top + 2.2, top + 4.3, lod)
    finish(m, g)
