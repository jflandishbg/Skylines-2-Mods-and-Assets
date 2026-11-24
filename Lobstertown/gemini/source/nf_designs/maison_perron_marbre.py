"""Maison à perron de marbre: Philadelphia brick row house in the Second Empire manner, 1 x 3 lot.
Three storeys of brick on a marble plinth, white marble stoop to a side-hall door, stone sills and lintels,
dentilled cornice, a two-stage mansard with three stone lucarnes front and two behind. A two-storey
back-building runs down the left party wall and tucks under the main block's belt, leaving a side yard.

Variant keys (all optional): brick, deck, roll, steep, door."""
from nf_kit import Mesh, Wall, finish, style, wall, surface, cornice, lucarne, chimney, steps, party, flat_roof, mansard_row

X = 3.99                        # party walls on the side lot lines
F, R = -11.4, -1.4              # main block: front and rear wall
BX, BR = 0.6, 7.0               # back-building: courtyard wall (x) and rear wall (y); it runs from -X to BX
TOP, BTOP = 10.2, 6.9
DEFAULT = dict(brick="Brick085", deck="TinFlat", roll="TinOxide", steep="SlateDark", door="Green")


def styles(v):
    main = style(TOP, [(0.0, TOP, v["brick"])],
                 [(1.15, 0.9, 3.0), (1.1, 4.3, 6.3), (1.05, 7.5, 9.15)], belts=(3.6, 6.9),
                 cornice=dict(fascia=(.6, .4, .18), corona=(.4, .35), dentils=True),
                 plinth=(.6, .06, "StoneBase"))
    back = style(BTOP, [(0.0, 1.1, "StoneBase"), (1.1, BTOP, v["brick"])],
                 [(1.05, 1.35, 3.0), (1.0, 4.4, 6.0)], belts=(3.6,),
                 cornice=dict(fascia=(.5, .35, .12), corona=(.35, .25), dentils=False),
                 cap=(1.06, 1.14, .08, "Dressed"), quoin_from=1.144)
    return main, back


def build(lod, **variant):
    v = dict(DEFAULT, **variant)
    main, back = styles(v)
    trim = dict(door=v["door"])
    m, g = Mesh(), Mesh()
    bays = [-2.5, 0.0, 2.5]

    # main block: street front with the stoop, party walls, rear (side-yard part full height, the rest above the back-building)
    wall(m, g, main, (-X, F), (X, F), "-", "-", bays, lod, door=(-2.5, 1.2, 3.0), steps=(-3.25, -1.75), trim=trim,
         waive={"balance": "side-hall row house: the stoop and door take the end bay"})
    steps(m, -3.25, -1.75, F, lod)
    party(m, (X, F), (X, R), 0.0, TOP, v["brick"])
    party(m, (-X, R), (-X, F), 0.0, TOP, v["brick"])
    wall(m, g, main, (X, R), (BX, R), "-", "c", [2.3], lod, cornice_on=False, belt_shrink={6.9: .254}, trim=trim)
    wall(m, g, main, (BX, R), (-X, R), "-", "-", [-1.7], lod, cornice_on=False, z0=BTOP, trim=trim)
    cornice(m, Wall((X, R), (-X, R)), main, "-", "-", lod)

    # back-building down the left party wall
    wall(m, g, back, (BX, R), (BX, BR), "c", "x", [0.6, 2.9, 5.2], lod, door=(0.6, 1.0, 2.6), trim=trim)
    wall(m, g, back, (BX, BR), (-X, BR), "x", "-", [-1.7], lod, trim=trim)
    party(m, (-X, BR), (-X, R), 0.0, BTOP, v["brick"])
    flat_roof(m, -X, BX, R, BR, BTOP)
    chimney(m, -3.45, 5.6, .4, .35, BTOP - .6, BTOP + 1.6, lod)

    # mansard with stone lucarnes over the bays; brick gable ends on the party lines
    mansard_row(m, -X, X, F, R, TOP, 3.0, 1.0, .8, lod, sides=dict(x0="e", x1="e"),
                steep=v["steep"], deck=v["deck"], roll=v["roll"], end=v["brick"])
    if lod < 2:
        lw = (.75, 10.75, 11.8)
        for w, cs in ((Wall((-X, F), (X, F)), bays), (Wall((X, R), (-X, R)), (2.3, -1.7))):
            for c in cs:
                lucarne(m, g, w, c, TOP, 1.2, lw, 12.1, 12.6, 1.4, lod, v["steep"])
    for sx in (1, -1):
        chimney(m, sx * 3.5, -6.4, .4, .55, 13.0, 15.2, lod)

    finish(m, g)
