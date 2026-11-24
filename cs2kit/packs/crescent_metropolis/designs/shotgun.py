"""Creole Camelback Shotgun (ZL1, 1x4 lot): clapboard front cottage with cast-iron porch + 2-storey sage hump."""
from cs2kit.kit import E, Mesh, chimney, finish, gable_roof, gable_wall, party, style, wall
from .creole_kit import iron_gallery_run

WAIVE = {"balance": "Creole shotgun rowhouse"}


def build(lod, W=1, D=4, **variant):
    X = 4.0 * W - 0.01
    yF = -4.0 * D + 1.15
    yM = 1.60
    yR = 4.0 * D - 1.05

    top1 = 4.60
    top2 = 8.65
    zr1 = 6.60
    zr2 = 10.75

    m, g = Mesh(), Mesh()

    # Front 1-storey clapboard shotgun
    win1 = [(0.96, 0.85, 3.00)]
    st1 = style(top1, [(0.0, top1, "Clapboard")], win1, belts=(), plinth=(0.55, 0.05, "StoneBase"), corners=False, frieze=0.26, belt_mat="TrimWhite")
    trim1 = dict(frame="TrimWhite", door="Oxblood", shutters="CharlestonGreen", lites="6", lean=lod > 0)
    bays = [-2.4, 0.0, 2.4]
    wall(m, g, st1, (-X, yF), (X, yF), "-", "-", bays, lod, door=(0.0, 1.0, 2.95), trim=trim1)
    gable_wall(m, g, (-X, yF), (X, yF), top1, zr1, lod, "Clapboard", wins=[(0.0, 0.82, top1 + 0.35, top1 + 1.35)], trim=dict(frame="TrimWhite", lites="6", lean=lod > 0))
    gable_roof(m, -X, X, yF, yM, top1, zr1, lod, mat="SlateDark", over=(0.30, -E), sides=("p", "p"))

    # Full-width covered cast-iron front porch
    iron_gallery_run(m, (-X, yF), (X, yF), depth=0.92, z_deck=0.35, z_top=3.55, lod=lod, roof=True, end_rails=(), cols_step=2.55)

    # Rear 2-storey StuccoSage Camelback Hump
    win2 = [(0.94, 0.90, 3.00), (0.88, 6.75, 8.00)]
    st2 = style(top2, [(0.0, top2, "StuccoSage")], win2, belts=(4.60,), plinth=(0.55, 0.05, "StoneBase"), corners=False, frieze=0.26, belt_mat="Dressed")
    trim2 = dict(frame="TrimWhite", door="Oxblood", shutters="CharlestonGreen", lites="6", lean=lod > 0)

    # Upper front face of hump above lower gable roof (z0 = 4.60)
    wall(m, g, st2, (-X, yM), (X, yM), "-", "-", bays, lod, z0=top1, trim=trim2, waive=WAIVE)
    gable_wall(m, g, (-X, yM), (X, yM), top2, zr2, lod, "StuccoSage", wins=[(0.0, 0.78, top2 + 0.35, top2 + 1.35)], trim=dict(frame="TrimWhite", lites="6", lean=lod > 0))
    # Rear 2-storey facade with upper cast-iron balcony
    wall(m, g, st2, (X, yR), (-X, yR), "-", "-", bays[::-1], lod, door=(0.0, 1.0, 2.85), trim=trim2, waive=WAIVE)
    iron_gallery_run(m, (X, yR), (-X, yR), depth=0.82, z_deck=4.60, z_top=7.90, lod=lod, roof=False, columns=False, end_rails=("l", "r"))

    # Party walls along both sides for full depth
    party(m, (-X, yR), (-X, yF), 0.0, top1, "Clapboard")
    party(m, (-X, yR), (-X, yM), top1, top2, "StuccoSage")
    party(m, (X, yF), (X, yR), 0.0, top1, "Clapboard")
    party(m, (X, yM), (X, yR), top1, top2, "StuccoSage")

    gable_wall(m, g, (X, yR), (-X, yR), top2, zr2, lod, "StuccoSage", wins=[(0.0, 0.80, top2 + 0.35, top2 + 1.35)], trim=dict(frame="TrimWhite", lites="6", lean=lod > 0))
    gable_roof(m, -X, X, yM, yR, top2, zr2, lod, mat="SlateDark", over=(-E, 0.30), sides=("p", "p"))
    chimney(m, -X + 0.85, (yM + yR) * 0.5, 0.35, 0.48, zr2 - 0.4, zr2 + 1.25, lod)
    finish(m, g)
