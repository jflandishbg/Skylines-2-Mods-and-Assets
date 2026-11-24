"""Hôtel particulier, brique et pierre: Louis XIII manner (Place des Vosges), 3 x 4 lot. The benchmark building.
A three-storey corps de logis on the street with a stone avant-corps (colossal pilasters, pediment, carriage
door on two steps), two lower wings round a rear cour d'honneur, true two-stage mansards with stone lucarnes,
quoins, belt courses and dressed window surrounds on every side.

Variant keys (all optional): brick, ground (ground-floor and frontispiece stone), deck, roll, steep, door."""
from nf_kit import Mesh, Wall, finish, style, wall, surface, cornice, mansard, lucarne, chimney, pediment, pilasters, steps

MX, MF, MB = 11.35, -14.4, -4.4            # corps de logis: half width, front wall, rear wall
AX, AF = 4.2, -15.15                       # avant-corps: half width, front wall
WO, WI, WR = 11.0, 4.9, 10.5               # wings (mirrored in x): outer wall, courtyard wall, rear wall
PIL = [(-4.15, -3.55), (-1.65, -1.05), (1.05, 1.65), (3.55, 4.15)]
DEFAULT = dict(brick="Brick085", ground="Ashlar", deck="TinFlat", roll="TinOxide", steep="SlateDark", door="Green")


def styles(v):
    main = style(12.0, [(0.0, 4.5, v["ground"]), (4.5, 12.0, v["brick"])],
                 [(1.3, 1.0, 3.7), (1.15, 5.45, 7.75), (1.1, 9.4, 11.0)], belts=(4.5, 8.5),
                 cornice=dict(fascia=(.6, .4, .18), corona=(.4, .35), dentils=True),
                 plinth=(.6, .06, "StoneBase"), rust=(1.5, 2.1, 2.7, 3.3, 3.9), quoin_from=4.644)
    wing = style(8.5, [(0.0, 1.1, "StoneBase"), (1.1, 8.5, v["brick"])],
                 [(1.1, 1.35, 3.65), (1.05, 5.4, 7.4)], belts=(4.5,),
                 cornice=dict(fascia=(.5, .35, .12), corona=(.35, .25), dentils=False),
                 cap=(1.06, 1.14, .08, "Dressed"), quoin_from=1.144)
    return main, wing


def build(lod, **variant):
    v = dict(DEFAULT, **variant)
    main, wing = styles(v)
    stone = [(0.0, 12.0, v["ground"])]
    trim = dict(door=v["door"])
    m, g = Mesh(), Mesh()

    # corps de logis: street front with the avant-corps
    wall(m, g, main, (-MX, MF), (-AX, MF), "x", "c", [-9.15, -6.15], lod, trim=trim)
    wall(m, g, main, (-AX, MF), (-AX, AF), "c", "x", [], lod, mats=stone, quoin=False, dentils=False)
    av = wall(m, g, main, (-AX, AF), (AX, AF), "x", "x", [-2.7, 0.0, 2.7], lod, mats=stone, door=(0.0, 2.2, 3.9),
              steps=(-1.6, 1.6), belt_cuts={8.5: PIL}, quoin=False, trim=dict(so=.18, door=v["door"]))
    wall(m, g, main, (AX, AF), (AX, MF), "x", "c", [], lod, mats=stone, quoin=False, dentils=False)
    wall(m, g, main, (AX, MF), (MX, MF), "c", "x", [6.15, 9.15], lod, trim=trim)
    # side elevations
    wall(m, g, main, (MX, MF), (MX, MB), "x", "x", [-12.4, -9.4, -6.4], lod)
    wall(m, g, main, (-MX, MB), (-MX, MF), "x", "x", [-12.4, -9.4, -6.4], lod)
    # rear: corner strips beside the wings, the wall above the wing roofs, the courtyard front, one cornice
    for A, B, s, e in (((MX, MB), (WO, MB), "x", "c"), ((-WO, MB), (-MX, MB), "c", "x")):
        wall(m, g, main, A, B, s, e, [], lod, rust=False, quoin=False, cornice_on=False, belt_shrink={8.5: .254})
    for A, B in (((WO, MB), (WI, MB)), ((-WI, MB), (-WO, MB))):
        surface(m, g, Wall(A, B), 8.5, 12.0, main["mats"], [], lod)
    wall(m, g, main, (WI, MB), (-WI, MB), "c", "c", [-2.9, 0.0, 2.9], lod, door=(0.0, 1.6, 3.2),
         quoin=False, cornice_on=False, belt_shrink={8.5: .254}, trim=trim)
    cornice(m, Wall((MX, MB), (-MX, MB)), main, "x", "x", lod)

    # frontispiece: colossal pilasters, front steps, pediment
    pilasters(m, av, PIL, 4.644, 11.396, lod)
    steps(m, -1.6, 1.6, AF, lod)
    pediment(m, AX, AF, 12.0, 2.4, -12.9, lod, steep=v["steep"])

    # wings round the cour d'honneur
    bays = [-3.0, -0.05, 2.9, 5.85, 8.8]
    lw = (.7, 9.05, 9.8)
    for sx in (1, -1):
        if sx > 0:
            ow = wall(m, g, wing, (WO, MB), (WO, WR), "c", "x", bays, lod)
            iw = wall(m, g, wing, (WI, WR), (WI, MB), "x", "c", bays, lod)
            rw = wall(m, g, wing, (WO, WR), (WI, WR), "x", "x", [9.0, 6.9], lod)
            mansard(m, WI, WO, MB, WR, 8.5, 2.3, .85, .5, lod, True, True, v["steep"], v["deck"], v["roll"])
        else:
            ow = wall(m, g, wing, (-WO, WR), (-WO, MB), "x", "c", bays, lod)
            iw = wall(m, g, wing, (-WI, MB), (-WI, WR), "c", "x", bays, lod)
            rw = wall(m, g, wing, (-WI, WR), (-WO, WR), "x", "x", [-6.9, -9.0], lod)
            mansard(m, -WO, -WI, MB, WR, 8.5, 2.3, .85, .5, lod, True, True, v["steep"], v["deck"], v["roll"])
        if lod < 2:
            for w in (ow, iw):
                for c in (-0.05, 2.9, 5.85):
                    lucarne(m, g, w, c, 8.5, 1.1, lw, 10.25, 10.65, 1.3, lod, v["steep"])
            lucarne(m, g, rw, sx * 7.95, 8.5, 1.1, lw, 10.25, 10.65, 1.3, lod, v["steep"])
        chimney(m, sx * 7.95, 6.85, .55, .35, 10.8, 12.6, lod)

    # main roof, lucarnes and chimneys
    mansard(m, -MX, MX, MF, MB, 12.0, 3.3, 1.15, 1.4, lod, steep=v["steep"], deck=v["deck"], roll=v["roll"])
    if lod < 2:
        mw = (.8, 12.6, 13.7)
        front, rear = Wall((-MX, MF), (MX, MF)), Wall((MX, MB), (-MX, MB))
        right, left = Wall((MX, MF), (MX, MB)), Wall((-MX, MB), (-MX, MF))
        for w, cs in ((front, (-9.15, -6.15, 6.15, 9.15)), (rear, (-8.0, -2.9, 0.0, 2.9, 8.0)),
                      (right, (-12.4, -9.4, -6.4)), (left, (-12.4, -9.4, -6.4))):
            for c in cs:
                lucarne(m, g, w, c, 12.0, 1.3, mw, 14.05, 14.6, 1.6, lod, v["steep"],
                        waive={"dormers": "on the axis of the wing below, which carries its own lucarne"} if abs(c) == 8.0 else None)
    for x in (-8.6, -3.2, 3.2, 8.6):
        chimney(m, x, -9.4, .7, .35, 15.3, 18.4, lod)

    finish(m, g)
