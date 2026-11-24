"""Demo pack civic service building (TownHall on 3x3 lot) exercising service templates + thumbnail render."""
from cs2kit.kit import E, Mesh, finish, lbox, porch, style, wall, wbox
from cs2kit.shapes import pavilion_roof

WAIVE = {"balance": "asymmetric civic porch/wings"}


def build(lod, W=3, D=3, **variant):
    wall_mat = variant.get("wall", "BoardBatten")
    roof_mat = variant.get("roof_mat", "TinGreen")
    door_mat = variant.get("door", "Oxblood")

    XH = 4.0 * W - 1.2
    XL = -XH
    yF = -4.0 * D + 1.0
    yM = yF + 10.0
    yR = 4.0 * D - 0.8

    G = 4.2
    F = 3.4
    top = G + F
    win_main = [(1.35, 0.95, 3.35, "bay"), (1.0, G + 0.85, G + 2.55)]
    mats_main = [(0.0, G, "Greystone"), (G, top, wall_mat)]
    st_main = style(top, mats_main, win_main, belts=(G,), plinth=None, corners=False, frieze=0.30, belt_mat="Dressed")
    trim = dict(door=door_mat, masonry="Dressed", reveal="Greystone", arch=True, glazed=True, lites="6", lean=lod > 0)

    m, g = Mesh(), Mesh()

    bays_f = [-8.7, -5.8, -2.9, 0.0, 2.9, 5.8, 8.7]
    bays_s = [-8.7, -6.0, -3.3]
    wall(m, g, st_main, (XL, yF), (XH, yF), "x", "x", bays_f, lod, door=(0.0, 1.5, 3.35), trim=trim, waive=WAIVE)
    wall(m, g, st_main, (XH, yF), (XH, yM), "x", "x", bays_s, lod, trim=trim, waive=WAIVE)
    wall(m, g, st_main, (XL, yM), (XL, yF), "x", "x", bays_s[::-1], lod, trim=trim, waive=WAIVE)

    # Rear half of main block outside the wing
    WX = 7.6
    wall(m, g, st_main, (XH, yM), (WX - E, yM), "x", "c", [9.2], lod, trim=trim, waive=WAIVE)
    wall(m, g, st_main, (-WX + E, yM), (XL, yM), "c", "x", [-9.2], lod, trim=trim, waive=WAIVE)
    # Upper rear wall above wing roof
    bays_up = [5.2, 2.6, 0.0, -2.6, -5.2]
    wall(m, g, st_main, (WX - E, yM), (-WX + E, yM), "c", "c", bays_up, lod, z0=4.6, trim=trim, waive=WAIVE)

    # Lower 1-storey rear wing filling the 3x3 lot cleanly
    top_w = 4.6
    st_w = style(top_w, [(0.0, top_w, "Greystone")], [(1.1, 1.0, 3.0)], belts=(), plinth=None, corners=False, frieze=0.28, belt_mat="Dressed")
    bays_ws = [1.4, 4.2, 7.0, 9.6]
    bays_wr = [5.2, 2.6, 0.0, -2.6, -5.2]
    wall(m, g, st_w, (WX, yM - E), (WX, yR), "c", "x", bays_ws, lod, trim=trim, waive=WAIVE)
    wall(m, g, st_w, (-WX, yR), (-WX, yM - E), "x", "c", bays_ws[::-1], lod, trim=trim, waive=WAIVE)
    wall(m, g, st_w, (WX, yR), (-WX, yR), "x", "x", bays_wr, lod, door=(0.0, 1.3, 2.8), trim=trim, waive=WAIVE)

    # Compact front portico canopy (< 3 m wide)
    porch(m, -1.35, 1.35, yF, 0.65, lod, zf=0.22, zt=3.55, mat=roof_mat, deck="Dressed", rail=False, open_sides=())

    # Main pavilion hip roof + wing pavilion hip roof
    pavilion_roof(m, XL - 0.35, XH + 0.35, yF - 0.35, yM + 0.35, top, 3.2, lod, roof_mat, finial=False)
    pavilion_roof(m, -WX - 0.30, WX + 0.30, yM - 0.30, yR + 0.30, top_w, 2.2, lod, roof_mat, finial=False)

    # Cupola on main ridge
    ym_c = (yF + yM) * 0.5
    cup_z0, cup_z1 = top + 1.8, top + 4.8
    cw = 1.4
    st_c = style(cup_z1, [(cup_z0, cup_z1, wall_mat)], [(1.0, cup_z0 + 1.1, cup_z1 - 0.5)], belts=(), plinth=None, corners=True, frieze=0.25, belt_mat="TrimWhite")
    c_holes = [(0.9, 1.9, cup_z0 + 1.2, cup_z1 - 0.6, "win")]
    for A, B in (
        ((-cw, ym_c - cw), (cw, ym_c - cw)),
        ((cw, ym_c - cw), (cw, ym_c + cw)),
        ((cw, ym_c + cw), (-cw, ym_c + cw)),
        ((-cw, ym_c + cw), (-cw, ym_c - cw)),
    ):
        wall(m, g, st_c, A, B, "x", "x", [], lod, z0=cup_z0, holes=c_holes, trim=dict(frame="TrimWhite", lean=True), waive=WAIVE)
    pavilion_roof(m, -cw - 0.22, cw + 0.22, ym_c - cw - 0.22, ym_c + cw + 0.22, cup_z1, 1.9, lod, roof_mat, finial=True)
    finish(m, g)
