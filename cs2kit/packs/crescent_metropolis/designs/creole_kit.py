"""Creole cast-iron gallery, filigree column, balustrade, and corner return helpers."""
from cs2kit.kit import E, Mesh, Wall, lbox, wbox
from cs2kit.shapes import slab


def _span_columns(length: float, step: float, margin: float = 0.22) -> list[float]:
    inner = length - 2.0 * margin
    if inner < 0.6:
        return [margin, length - margin]
    k = max(1, round(inner / step))
    return [margin + inner * i / k for i in range(k + 1)]


def iron_gallery_run(
    m: Mesh,
    A,
    B,
    depth: float,
    z_deck: float,
    z_top: float,
    lod: int,
    roof: bool = False,
    roof_mat: str = "TinGreen",
    soffit_mat: str = "BayouBlue",
    deck_mat: str = "Deck",
    iron_mat: str = "CastIron",
    cols_step: float = 2.6,
    rail: bool = True,
    end_rails=("l", "r"),
    columns: bool = True,
    valence: bool = True,
    u_inset=(E, E),
):
    """Build a cast-iron gallery tier along wall A->B (d=0 at wall, d=depth outward).

    All touching members observe E = 4 mm clearances so zero coplanar overlaps occur.
    """
    w = Wall(A, B)
    u0, u1 = u_inset[0], w.L - u_inset[1]
    if u1 - u0 < 0.4:
        return

    # Deck top (Deck) + lower BayouBlue soffit ceiling, cleanly separated
    lbox(m, w, u0, u1, z_deck - 0.10, z_deck, E, depth, deck_mat, skip=("in", "bot"))
    lbox(m, w, u0, u1, z_deck - 0.16, z_deck - 0.10 - E, E, depth, soffit_mat, skip=("in", "top"))
    if lod < 2:
        # Outer cast-iron deck fascia trim (stands proud of deck edge)
        lbox(m, w, u0, u1, z_deck - 0.16, z_deck + 0.02, depth + E, depth + 0.045, iron_mat)

    col_u = _span_columns(w.L, cols_step, margin=0.22) if columns else [u0 + 0.12, u1 - 0.12]
    d_in, d_out = depth - 0.12, depth - 0.04

    if columns:
        use_cols = col_u if lod < 2 else [col_u[0], col_u[-1]]
        z_c0, z_c1 = z_deck + E, z_top - 0.22 - E
        shaft_z0 = z_c0 + (0.16 + E if lod == 0 else 0.0)
        shaft_z1 = z_c1 - (0.12 + E if lod == 0 else 0.0)
        for uc in use_cols:
            if lod == 0:
                # Paired wrought-iron trellis posts + lace cross-bars + base pedestal + capital
                lbox(m, w, uc - 0.085, uc - 0.045, shaft_z0, shaft_z1, d_in, d_out, iron_mat)
                lbox(m, w, uc + 0.045, uc + 0.085, shaft_z0, shaft_z1, d_in, d_out, iron_mat)
                lbox(m, w, uc - 0.105, uc + 0.105, z_c0, z_c0 + 0.16, d_in - 0.02, d_out + 0.02, iron_mat)
                lbox(m, w, uc - 0.10, uc + 0.10, z_c1 - 0.12, z_c1, d_in - 0.015, d_out + 0.015, iron_mat)
                z_tie = shaft_z0 + 0.45
                while z_tie < shaft_z1 - 0.25:
                    lbox(m, w, uc - 0.045 + E, uc + 0.045 - E, z_tie - 0.018, z_tie + 0.018, d_in + 0.01, d_out - 0.01, iron_mat)
                    z_tie += 0.55
            else:
                lbox(m, w, uc - 0.06, uc + 0.06, z_c0, z_c1, d_in, d_out, iron_mat)

        if lod < 2:
            # Top gallery beam / frieze header
            lbox(m, w, u0, u1, z_top - 0.22, z_top - E, depth - 0.15, depth - 0.01, iron_mat)
            if lod == 0 and valence:
                # Filigree spandrel brackets & pierced valance under beam between columns
                for ua, ub in zip(col_u, col_u[1:]):
                    if ub - ua < 0.7:
                        continue
                    lbox(m, w, ua + 0.11, ub - 0.11, z_top - 0.36, z_top - 0.22 - E, d_in + 0.01, d_out - 0.01, iron_mat)
                    for side_u, sgn in ((ua + 0.11, 1), (ub - 0.11, -1)):
                        bu0, bu1 = sorted((side_u, side_u + sgn * 0.22))
                        lbox(m, w, bu0, bu1, z_top - 0.54, z_top - 0.36 - E, d_in + 0.015, d_out - 0.015, iron_mat)

    if rail and lod < 2:
        spans = list(zip(col_u, col_u[1:])) if columns else [(u0 + 0.04, u1 - 0.04)]
        pad = 0.11 if (columns and lod == 0) else 0.08 if columns else 0.0
        for ua, ub in spans:
            ra, rb = ua + pad, ub - pad
            if rb - ra < 0.18:
                continue
            lbox(m, w, ra, rb, z_deck + 0.90, z_deck + 0.96, d_in, d_out, iron_mat)
            lbox(m, w, ra, rb, z_deck + 0.08, z_deck + 0.13, d_in, d_out, iron_mat)
            if lod == 0:
                lbox(m, w, ra, rb, z_deck + 0.72, z_deck + 0.76, d_in + 0.008, d_out - 0.008, iron_mat)
                n_pick = max(2, int((rb - ra) / 0.15))
                for k in range(1, n_pick):
                    up = ra + (rb - ra) * k / n_pick
                    lbox(m, w, up - 0.012, up + 0.012, z_deck + 0.13 + E, z_deck + 0.72 - E, d_in + 0.015, d_out - 0.015, iron_mat)
                # Lace frieze rings/squares in the upper rail band
                n_lace = max(1, int((rb - ra) / 0.24))
                for k in range(n_lace):
                    um = ra + (rb - ra) * (k + 0.5) / n_lace
                    lbox(m, w, um - 0.045, um + 0.045, z_deck + 0.76 + E, z_deck + 0.90 - E, d_in + 0.015, d_out - 0.015, iron_mat)

        end_d = (d_in - 0.025) if columns else (d_in - E)
        left_u = (col_u[0] - 0.03) if columns else (u0 + 0.02)
        right_u = (col_u[-1] - 0.03) if columns else (u1 - 0.08)
        for side, uu in (("l", left_u), ("r", right_u)):
            if side in end_rails:
                lbox(m, w, uu, uu + 0.06, z_deck + 0.90, z_deck + 0.96, E, end_d, iron_mat)
                lbox(m, w, uu, uu + 0.06, z_deck + 0.08, z_deck + 0.13, E, end_d, iron_mat)
                if lod == 0:
                    k_end = max(1, int((end_d - 0.10) / 0.16))
                    for i in range(1, k_end):
                        dd = 0.08 + (end_d - 0.10) * i / k_end
                        lbox(m, w, uu + 0.018, uu + 0.042, z_deck + 0.13 + E, z_deck + 0.90 - E, dd - 0.012, dd + 0.012, iron_mat)

    if roof:
        P_roof = lambda a, q, z: w.P(a, z, q)
        prof = [(E, z_top + 0.42), (depth + 0.18, z_top)]
        slab(m, prof, u0, u1, P_roof, lod, roof_mat, end=iron_mat, eave=iron_mat, th=0.10, what="gallery canopy")


def iron_ground_arcade(
    m: Mesh,
    A,
    B,
    depth: float,
    z_top: float,
    lod: int,
    cols_step: float = 2.6,
    curb_h: float = 0.28,
    curb_mat: str = "StoneBase",
    iron_mat: str = "CastIron",
    u_inset=(E, E),
):
    """Build ground-floor granite banquette curb + cast-iron arcade posts supporting an upper gallery."""
    w = Wall(A, B)
    u0, u1 = u_inset[0], w.L - u_inset[1]
    if u1 - u0 < 0.4:
        return
    wbox_curb = curb_h > 0.0
    if wbox_curb:
        lbox(m, w, u0, u1, 0.0, curb_h, E, depth, curb_mat, skip=("in", "bot"))
    col_u = _span_columns(w.L, cols_step, margin=0.22)
    use_cols = col_u if lod < 2 else [col_u[0], col_u[-1]]
    d_in, d_out = depth - 0.12, depth - 0.04
    z_c0 = (curb_h + E) if wbox_curb else 0.0
    z_c1 = z_top - E
    shaft_z0 = z_c0 + (0.20 + E if lod == 0 else 0.0)
    shaft_z1 = z_c1 - (0.14 + E if lod == 0 else 0.0)
    for uc in use_cols:
        if lod == 0:
            lbox(m, w, uc - 0.085, uc - 0.045, shaft_z0, shaft_z1, d_in, d_out, iron_mat)
            lbox(m, w, uc + 0.045, uc + 0.085, shaft_z0, shaft_z1, d_in, d_out, iron_mat)
            lbox(m, w, uc - 0.11, uc + 0.11, z_c0, z_c0 + 0.20, d_in - 0.025, d_out + 0.025, iron_mat)
            lbox(m, w, uc - 0.10, uc + 0.10, z_c1 - 0.14, z_c1, d_in - 0.015, d_out + 0.015, iron_mat)
            z_tie = shaft_z0 + 0.55
            while z_tie < shaft_z1 - 0.30:
                lbox(m, w, uc - 0.045 + E, uc + 0.045 - E, z_tie - 0.018, z_tie + 0.018, d_in + 0.01, d_out - 0.01, iron_mat)
                z_tie += 0.65
        else:
            lbox(m, w, uc - 0.065, uc + 0.065, z_c0, z_c1, d_in, d_out, iron_mat)


def gallery_corner_ground_arcade(
    m: Mesh,
    cx_wall: float,
    cy_wall: float,
    depth: float,
    z_top: float,
    lod: int,
    curb_h: float = 0.28,
    curb_mat: str = "StoneBase",
    iron_mat: str = "CastIron",
):
    """Ground-floor corner banquette + cast-iron arcade post beneath a wrap-around gallery corner."""
    x0, x1 = cx_wall - depth, cx_wall - E
    y0, y1 = cy_wall - depth, cy_wall - E
    wbox(m, x0, x1, y0, y1, 0.0, curb_h, curb_mat, ("z-",))
    if lod < 2:
        px, py = x0 + 0.08, y0 + 0.08
        wbox(m, px - 0.07, px + 0.07, py - 0.07, py + 0.07, curb_h + E, z_top - E, iron_mat)


def gallery_corner_square(
    m: Mesh,
    cx_wall: float,
    cy_wall: float,
    depth: float,
    z_deck: float,
    z_top: float,
    lod: int,
    roof: bool = False,
    roof_mat: str = "TinGreen",
    soffit_mat: str = "BayouBlue",
    deck_mat: str = "Deck",
    iron_mat: str = "CastIron",
):
    """Connect a -X gallery and a -Y gallery cleanly at the front-left outside corner."""
    x0, x1 = cx_wall - depth, cx_wall - E
    y0, y1 = cy_wall - depth, cy_wall - E
    wbox(m, x0, x1, y0, y1, z_deck - 0.10, z_deck, deck_mat, ("z-",))
    wbox(m, x0, x1, y0, y1, z_deck - 0.16, z_deck - 0.10 - E, soffit_mat, ("z+",))
    if lod < 2:
        wbox(m, x0 - 0.045, x1, y0 - 0.045, y0 - E, z_deck - 0.16, z_deck + 0.02, iron_mat)
        wbox(m, x0 - 0.045, x0 - E, y0, y1, z_deck - 0.16, z_deck + 0.02, iron_mat)
        # Corner iron post + rail returns
        px, py = x0 + 0.08, y0 + 0.08
        wbox(m, px - 0.06, px + 0.06, py - 0.06, py + 0.06, z_deck + E, z_top - 0.22 - E, iron_mat)
        wbox(m, px + 0.06 + E, x1, py - 0.04, py + 0.04, z_deck + 0.90, z_deck + 0.96, iron_mat)
        wbox(m, px - 0.04, px + 0.04, py + 0.06 + E, y1, z_deck + 0.90, z_deck + 0.96, iron_mat)
        wbox(m, px - 0.04, x1, py - 0.06, py + 0.06, z_top - 0.22, z_top - E, iron_mat)
        wbox(m, px - 0.06, px + 0.06, py + 0.06 + E, y1, z_top - 0.22, z_top - E, iron_mat)

    if roof:
        # Closed mitered canopy cap linking front and left canopies
        from cs2kit.shapes import pavilion_roof

        pavilion_roof(
            m,
            x0 - 0.18,
            x1,
            y0 - 0.18,
            y1,
            z_top,
            0.42,
            lod,
            roof_mat,
            finial=False,
            trim_mat=iron_mat,
        )
