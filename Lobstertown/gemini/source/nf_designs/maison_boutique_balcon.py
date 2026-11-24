"""Maison à boutique et balcon: main-street shop with flats above, 1 x 4 lot (Rue Principale Mixte).
A painted timber shopfront (pilasters, fascia board, plate glass, glazed door) beside the stair door to the
flats; a continuous stone balcony with an iron railing on the first floor; rendered upper storeys with stone
sills, lintels and belt; two-stage mansard with lucarnes. A one-storey arrière-boutique fills the back of the
lot under the main block's first-floor balcony line.

Variant keys (all optional): wall (upper render), ground (shop-floor stone), frame (shopfront and doors),
deck, roll, steep, party."""
from nf_kit import (Mesh, Wall, finish, style, wall, cornice, lucarne, chimney, party, flat_roof, balcony,
                    mansard_row)

X = 3.99
F, R, BR = -15.2, -3.2, 3.8      # main front and rear wall; back of the arrière-boutique
TOP, GTOP = 10.8, 4.2
DEFAULT = dict(wall="RenderOchre", ground="Dressed", frame="Green", deck="TinFlat", roll="TinOxide",
               steep="SlateDark", party="Render")


def styles(v):
    mats = [(0.0, GTOP, v["ground"]), (GTOP, TOP, v["wall"])]
    front = style(TOP, mats, [(1.15, 0.9, 3.0), (1.15, 4.42, 6.7, "fwin"), (1.1, 7.75, 9.75)], belts=(7.4,),
                  cornice=dict(fascia=(.6, .4, .18), corona=(.4, .35), dentils=True),
                  plinth=(.5, .06, "StoneBase"))
    rear = style(TOP, mats, [(1.1, 0.9, 3.0), (1.05, 4.7, 6.6), (1.0, 7.75, 9.7)], belts=(7.4,),
                 cornice=dict(fascia=(.5, .35, .12), corona=(.35, .25), dentils=False))
    shop = style(GTOP, [(0.0, 1.1, "StoneBase"), (1.1, GTOP, v["ground"])], [(1.1, 1.35, 3.0)],
                 cornice=dict(fascia=(.5, .35, .12), corona=(.35, .25), dentils=False),
                 cap=(1.06, 1.14, .08, "Dressed"))
    return front, rear, shop


def build(lod, **variant):
    v = dict(DEFAULT, **variant)
    front, rear, shop = styles(v)
    trim = dict(door=v["frame"])
    m, g = Mesh(), Mesh()
    bays = [-2.5, 0.0, 2.7]

    # street front: shopfront on the left two bays, the stair door to the flats under the right bay
    fw = wall(m, g, front, (-X, F), (X, F), "-", "-", bays, lod, door=(2.7, 1.1, 3.0),
              shop=(-3.3, 1.5, 3.4, -1.45, -0.35), trim=trim,
              waive={"balance": "main-street shop: the shopfront and the stair door share the ground floor"})
    balcony(m, fw, 4.42, .7, lod, s=.25, e=.25)
    party(m, (X, F), (X, R), 0.0, TOP, v["party"])
    party(m, (-X, R), (-X, F), 0.0, TOP, v["party"])

    # rear: flats above the arrière-boutique roof
    wall(m, g, rear, (X, R), (-X, R), "-", "-", [2.5, 0.0, -2.5], lod, z0=GTOP, trim=trim)

    # arrière-boutique: one storey to the back of the lot, yard door and windows
    wall(m, g, shop, (X, BR), (-X, BR), "-", "-", [2.5, 0.0, -2.5], lod, door=(2.5, 1.1, 2.7), trim=trim)
    party(m, (X, R), (X, BR), 0.0, GTOP, v["party"])
    party(m, (-X, BR), (-X, R), 0.0, GTOP, v["party"])
    flat_roof(m, -X, X, R, BR, GTOP)

    mansard_row(m, -X, X, F, R, TOP, 3.0, 1.0, .8, lod, sides=dict(x0="e", x1="e"),
                steep=v["steep"], deck=v["deck"], roll=v["roll"], end=v["party"])
    if lod < 2:
        lw = (.75, 11.35, 12.4)
        for w, cs in ((Wall((-X, F), (X, F)), bays), (Wall((X, R), (-X, R)), (2.5, -2.5))):
            for c in cs:
                lucarne(m, g, w, c, TOP, 1.2, lw, 12.7, 13.2, 1.4, lod, v["steep"])
    for sx in (1, -1):
        chimney(m, sx * 3.5, -9.2, .4, .55, 13.6, 15.8, lod)

    finish(m, g)
