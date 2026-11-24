"""Demo pack rowhouse and mixed-use shopfront designs exercising party walls, LeftCorner, and signs."""
import math
from cs2kit.kit import (
    E,
    Mesh,
    Wall,
    bay,
    chimney,
    finish,
    gable_roof,
    gable_wall,
    lbox,
    party,
    porch,
    sign_plate,
    style,
    wall,
)
from cs2kit.shapes import cornice_roof

CI = 0.45
WAIVE_ASYM = {"balance": "urban terrace / commercial street front"}


def _bays_in(xa: float, xb: float, pitch: float = 2.4, margin: float = 1.1) -> list[float]:
    inner = xb - xa - 2.0 * margin
    if inner < 1.2:
        return [(xa + xb) * 0.5]
    k = max(2, round(inner / pitch) + 1)
    return [xa + margin + inner * i / (k - 1) for i in range(k)]


def build(lod, W=1, D=3, **variant):
    mode = variant.get("mode", "res")
    storeys = int(variant.get("storeys", 2))
    wall_mat = variant.get("wall", "Brick074")
    roof_mat = variant.get("roof_mat", "SlateDark")
    door_mat = variant.get("door", "Green")
    corner = bool(variant.get("corner", False))
    sign_key = variant.get("sign")

    X = 4.0 * W - 0.01
    XL = -X + CI if corner else -X
    yF = -4.0 * D + 1.00
    yR = 4.0 * D - 0.60

    m, g = Mesh(), Mesh()

    if mode == "mixed":
        # Ground shop storey (3.55 m shop + sign zone 4.06..4.64 + belt at 4.80) + upper flats
        g_h = 4.95
        f_h = 3.1
        win = [(1.0, 5.4, 7.1)]
        if storeys >= 3:
            win.append((0.95, 8.5, 10.1))
        top = win[-1][2] + 1.05
        st = style(
            top,
            [(0.0, g_h, "Greystone"), (g_h, top, wall_mat)],
            win,
            belts=(4.80, 7.85) if storeys >= 3 else (4.80,),
            plinth=None,
            corners=False,
            frieze=0.30,
            belt_mat="Dressed",
        )
        trim = dict(door=door_mat, masonry="Dressed", reveal=wall_mat, lites="6", lean=lod > 0)

        bays_front = _bays_in(XL, X, pitch=2.5, margin=1.2)
        shop_holes = [(0.8, (X - XL) - 0.8, 0.0, 3.55, "shop")]
        trim_f = dict(trim, shopdoor=((X - XL) * 0.5 - 0.55, (X - XL) * 0.5 + 0.55))
        fw = wall(
            m,
            g,
            st,
            (XL, yF),
            (X, yF),
            "-",
            "-",
            bays_front,
            lod,
            trim=trim_f,
            holes=shop_holes,
            waive=WAIVE_ASYM,
        )
        if sign_key:
            # Placed cleanly at x_slot=0 (x=0..3.0), z_slot=7 (z=4.06..4.64) below the 4.80 belt
            sign_plate(m, 0, yF, 7, sign_key)

        rear_win = [(1.0, 1.0, 2.8)] + win
        st_r = style(
            top,
            [(0.0, g_h, "Greystone"), (g_h, top, wall_mat)],
            rear_win,
            belts=st["belts"],
            plinth=None,
            corners=False,
            frieze=0.30,
            belt_mat="Dressed",
        )
        wall(m, g, st_r, (X, yR), (XL, yR), "-", "-", bays_front[::-1], lod, door=(bays_front[0], 1.1, 2.7), trim=trim, waive=WAIVE_ASYM)
        party(m, (XL, yR), (XL, yF), 0.0, top, wall_mat)
        party(m, (X, yF), (X, yR), 0.0, top, wall_mat)
        cornice_roof(m, XL + E, X - E, yF - 0.35, yR + 0.25, top, lod, deep=0.55, top="TinFlat", side="Dressed", ends=wall_mat)
        chimney(m, X - 1.0, (yF + yR) * 0.5, 0.4, 0.55, top + 0.4, top + 1.8, lod)
        finish(m, g)
        return

    # Residential rowhouse (and LeftCorner)
    win = [(0.92, 1.05, 2.75), (0.90, 4.15, 5.75)]
    if storeys >= 3:
        win.append((0.85, 7.25, 8.75))
    top = win[-1][2] + 0.95
    belts = (3.45, 6.55) if storeys >= 3 else (3.45,)
    st = style(
        top,
        [(0.0, top, wall_mat)],
        win,
        belts=belts,
        plinth=(0.68, 0.05, "StoneBase"),
        corners=False,
        frieze=0.28,
        belt_mat="Dressed",
    )
    trim = dict(door=door_mat, masonry="Dressed", reveal=wall_mat, lites="6", lean=lod > 0)

    # Guarantee odd bay count on front so door sits symmetrically
    bays_f = [XL + 1.45 + (X - XL - 2.9) * i / 2 for i in range(3)] if W == 1 else [XL + 1.55 + (X - XL - 3.1) * i / 6 for i in range(7)]

    door_bay = bays_f[len(bays_f) // 2]
    bay_x = bays_f[0] if corner else None
    omit_f = [(bay_x, f) for f in range(storeys)] if bay_x is not None else ()
    sx_l = "x" if corner else "-"
    wall(m, g, st, (XL, yF), (X, yF), sx_l, "-", bays_f, lod, door=(door_bay, 1.05, 2.75), trim=trim, omit=omit_f, waive=WAIVE_ASYM)
    wall(m, g, st, (X, yR), (XL, yR), "-", sx_l, bays_f[::-1], lod, trim=trim, waive=WAIVE_ASYM)

    if corner:
        bays_s = _bays_in(yF, yR, pitch=2.5, margin=1.35)
        wall(m, g, st, (XL, yR), (XL, yF), "x", "x", bays_s, lod, trim=trim, waive=WAIVE_ASYM)
        # Canted projecting bay on front bay_x stopping cleanly under main frieze
        if bay_x is not None:
            bay(
                m,
                g,
                bay_x,
                yF,
                width=1.3,
                proj=0.60,
                z0=0.0,
                z1=top - 0.30 - E,
                lod=lod,
                mat=wall_mat,
                win=[(zb, zt) for _, zb, zt in win],
                trim=trim,
                roof=roof_mat,
                lites="2",
            )
    else:
        party(m, (XL, yR), (XL, yF), 0.0, top, wall_mat)

    party(m, (X, yF), (X, yR), 0.0, top, wall_mat)

    # Compact stoop canopy at front door (<= 2.8 m wide so it doesn't count as a separate eave run)
    if not corner:
        porch(m, door_bay - 1.35, door_bay + 1.35, yF, 0.65, lod, zf=0.20, zt=3.0, mat=roof_mat, rail=False, open_sides=())

    zr = top + (2.6 if W == 1 else 3.4)
    xm = (XL + X) * 0.5
    gable_wall(m, g, (XL, yF), (X, yF), top, zr, lod, wall_mat, wins=[(xm, 0.85, top + 0.5, top + 1.7)], trim=trim)
    gable_wall(m, g, (X, yR), (XL, yR), top, zr, lod, wall_mat, wins=[(xm, 0.85, top + 0.5, top + 1.7)], trim=trim)
    gable_roof(m, XL, X, yF, yR, top, zr, lod, mat=roof_mat, sides=("e" if corner else "p", "p"))
    chimney(m, X - 0.9, (yF + yR) * 0.5, 0.35, 0.5, zr - 0.5, zr + 1.1, lod)
    finish(m, g)
