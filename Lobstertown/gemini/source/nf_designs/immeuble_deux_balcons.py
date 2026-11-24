"""Immeuble à deux balcons: Haussmann apartment house, 3 x 4 lot (Appartements Haussmann).
Seven bays of dressed stone between party walls: rusticated ground floor and entresol with a porte cochère,
continuous balconies with iron railings on the étage noble (2nd) and the 5th floor, belt courses, a deep
dentilled cornice and a zinc mansard with stone lucarnes on every bay. Behind, a rendered courtyard front
and two four-storey wings down the party walls round a cour, stepping down two storeys under the main block.

Variant keys (all optional): stone (upper facade), ground (ground floor and entresol), court (courtyard
render), party, door, deck, roll, steep."""
from nf_kit import (Mesh, Wall, finish, style, wall, cornice, lucarne, chimney, party, balcony, mansard_row)

X = 11.99
F, R = -15.1, -3.1            # main block: street front and courtyard wall
WI, WR = 7.0, 9.0             # wings (mirrored in x): courtyard wall and rear wall; they run from WI to X
TOP, WTOP = 19.0, 13.2
BAYS = [-9.6, -6.4, -3.2, 0.0, 3.2, 6.4, 9.6]
CONSOLES = [-11.0, -8.0, -4.8, -1.6, 1.6, 4.8, 8.0, 11.0]
DEFAULT = dict(stone="Ashlar", ground="Ashlar", court="Render", party="Render", door="Oxblood",
               deck="TinFlat", roll="TinOxide", steep="Tin")


def styles(v):
    front = style(TOP, [(0.0, 6.6, v["ground"]), (6.6, TOP, v["stone"])],
                  [(1.5, 0.9, 3.4), (1.3, 4.6, 6.0), (1.3, 6.84, 9.3, "fwin"), (1.25, 10.6, 12.6),
                   (1.2, 13.75, 15.6), (1.15, 16.42, 17.9, "fwin")], belts=(4.0, 10.0, 13.2),
                  cornice=dict(fascia=(.7, .45, .25), corona=(.45, .55), dentils=True),
                  plinth=(.5, .06, "StoneBase"), rust=(1.2, 1.8, 2.4, 3.0, 3.6, 4.6, 5.2, 5.8), low=(1,))
    court_win = [(1.1, 1.35, 3.1), (1.0, 4.5, 5.9), (1.1, 7.2, 9.3), (1.1, 10.6, 12.6), (1.05, 13.75, 15.6),
                 (1.0, 16.6, 17.9)]
    mats = [(0.0, 1.1, "StoneBase"), (1.1, TOP, v["court"])]
    cor = dict(fascia=(.5, .35, .12), corona=(.35, .25), dentils=False)
    rear = style(TOP, mats, court_win, belts=(4.0,), cornice=cor, cap=(1.06, 1.14, .08, "Dressed"), low=(1,))
    wing = style(WTOP, mats, court_win[:3] + [(1.1, 10.6, 12.3)], belts=(4.0,), cornice=cor,
                 cap=(1.06, 1.14, .08, "Dressed"), quoin_from=1.144, low=(1,))
    return front, rear, wing


def build(lod, **variant):
    v = dict(DEFAULT, **variant)
    front, rear, wing = styles(v)
    trim = dict(door=v["door"])
    m, g = Mesh(), Mesh()

    # street front with its two balconies
    fw = wall(m, g, front, (-X, F), (X, F), "-", "-", BAYS, lod, door=(0.0, 2.6, 3.5), trim=trim)
    balcony(m, fw, 6.84, .75, lod, s=.4, e=.4, consoles=CONSOLES)
    balcony(m, fw, 16.42, .70, lod, s=.4, e=.4, consoles=CONSOLES)
    party(m, (X, F), (X, R), 0.0, TOP, v["party"])
    party(m, (-X, R), (-X, F), 0.0, TOP, v["party"])

    # courtyard front between the wings (carriage way through to the cour), the strips above the wings, one cornice
    court = [5.4, 2.7, 0.0, -2.7, -5.4]
    wall(m, g, rear, (WI, R), (-WI, R), "c", "c", court, lod, door=(0.0, 2.6, 3.5), cornice_on=False, trim=trim)
    wall(m, g, rear, (X, R), (WI, R), "-", "-", [9.5], lod, z0=WTOP, cornice_on=False, trim=trim)
    wall(m, g, rear, (-WI, R), (-X, R), "-", "-", [-9.5], lod, z0=WTOP, cornice_on=False, trim=trim)
    cornice(m, Wall((X, R), (-X, R)), rear, "-", "-", lod)

    # wings down the party walls
    wb = [0.0, 3.0, 6.0]
    lw = (.7, 13.7, 14.6)
    for sx in (1, -1):
        if sx > 0:
            iw = wall(m, g, wing, (WI, WR), (WI, R), "x", "c", wb, lod, door=(3.0, 1.1, 2.8), trim=trim)
            rw = wall(m, g, wing, (X, WR), (WI, WR), "-", "x", [9.5], lod, trim=trim)
            party(m, (X, R), (X, WR), 0.0, WTOP, v["party"])
            mansard_row(m, WI, X, R, WR, WTOP, 2.6, .9, .6, lod, sides=dict(y0="o", x1="e"), ridge="y",
                        steep=v["steep"], deck=v["deck"], roll=v["roll"], end=v["party"])
        else:
            iw = wall(m, g, wing, (-WI, R), (-WI, WR), "c", "x", wb, lod, door=(3.0, 1.1, 2.8), trim=trim)
            rw = wall(m, g, wing, (-WI, WR), (-X, WR), "x", "-", [-9.5], lod, trim=trim)
            party(m, (-X, WR), (-X, R), 0.0, WTOP, v["party"])
            mansard_row(m, -X, -WI, R, WR, WTOP, 2.6, .9, .6, lod, sides=dict(y0="o", x0="e"), ridge="y",
                        steep=v["steep"], deck=v["deck"], roll=v["roll"], end=v["party"])
        if lod < 2:
            for c in wb:
                lucarne(m, g, iw, c, WTOP, 1.1, lw, 14.95, 15.35, 1.3, lod, v["steep"])
        chimney(m, sx * 11.4, 4.0, .45, .6, 15.0, 17.4, lod)

    # main roof: zinc mansard, a lucarne over every bay, stacks on the party walls
    mansard_row(m, -X, X, F, R, TOP, 3.2, 1.2, 1.0, lod, sides=dict(x0="e", x1="e"),
                steep=v["steep"], deck=v["deck"], roll=v["roll"], end=v["party"])
    if lod < 2:
        mw = (.85, 19.6, 20.9)
        for w, cs in ((Wall((-X, F), (X, F)), BAYS), (Wall((X, R), (-X, R)), court + [9.5, -9.5])):
            for c in cs:
                lucarne(m, g, w, c, TOP, 1.3, mw, 21.25, 21.8, 1.6, lod, v["steep"])
    for sx in (1, -1):
        for y in (-12.0, -6.2):
            chimney(m, sx * 11.4, y, .45, .6, 21.0, 24.0, lod)

    finish(m, g)
