"""Write the building stubs for Lobstertown zone L1 (Shore Rows) into scripts/.

    python lt_roster.py            write every stub, print the names (comma separated, for run.py)
    python lt_roster.py ZM1        ... print only one zone's names
Each design comes in every lot depth from 1x2 to 1x6, like the Toronto rows.
"""
from pathlib import Path

ZONE = "ZL1"
X_, E_ = 3.99, .004                  # shorerows.X and lt_kit.E (the stubs repeat the numbers)


def E(roof, level, mat, rmat, L, mn, **kw):
    """A narrow rear wing for lt_designs/shorerows.py: roof 'gable' | 'cross' | 'shed', eave 'LOW' or 'MID'."""
    return dict(k="ell", roof=roof, h={"LOW": 3.55, "MID": 6.7}[level], mat=mat, rmat=rmat, L=L, min=mn, **kw)


def C(roof, mat, rmat, L, **kw):
    """A carriage house across the back for lt_designs/shorerows.py: roof 'across' | 'gambrel' | 'hip'."""
    return dict(k="carriage", roof=roof, h=3.55, mat=mat, rmat=rmat, L=L, min=6.0, **kw)


DESIGNS = {
    # Shore Rows, second edition (the author 2026-11-17, Direction B): painted ladies - Carpenter Gothic cottages, Queen Anne
    # with small wooden towers, Stick style, painted triple-deckers with gabled porch towers. lt_designs/shorerows.py.
    # hh keeps the first edition's household mix (nine 2s, nine 3s with the four corners, two 4s). Every rear differs:
    # E(...) a narrow wing beside the yard, C(...) the carriage house across the back; LOW / MID eaves.
    "GothicCottage": dict(hh=2, roof="side", storeys=2, depth=8.5, xgables=((0.0, 3.4),), xpitch=1.5,
                          wall="BoardBatten", gable_mat="BoardBatten", roof_mat="SlateGreen", door="Green", door_x=0.0,
                          porch="full", spindles=False, barge=True, finial=True,
                          rear=(E("cross", "LOW", "Clapboard", "TinOxide", 6.5, 3.0, barge=True),
                                E("gable", "LOW", "BoardBatten", "TinFlat", 7.0, 3.0, grow=True),
                                C("gambrel", "BoardBatten", "SlateGreen", 8.0))),
    "GothicGable": dict(hh=2, roof="gable", storeys=2, rise=5.4, band=True, gable_mat="BoardBatten", gwin="lancet",
                        roof_mat="SlateDark", door="Oxblood", bays=[-2.5, 2.0], door_x=-2.5,
                        bay=dict(x=2.0, z1=3.3), porch="half", porch_x=(-X_ + E_, -1.25), spindles=False,
                        barge=True, finial=True,
                        rear=(E("gable", "MID", "Clapboard", "SlateBrown", 7.0, 4.0, piazza=1, grow=True),
                              E("shed", "LOW", "BoardBatten", "TinGreen", 4.5, 3.0, rise=1.4),
                              C("hip", "Clapboard", "TinOxide", 9.0, grow=True))),
    "FishscaleGable": dict(hh=2, roof="gable", rise=4.3, upper=(6.85, "Fishscale"), gwin="triple", roof_mat="Slate",
                           door="Green", bays=[-2.0, 2.5], door_x=2.5, bay=dict(x=-2.0, z1=6.75), porch="full",
                           dormers=True, finial=True, backporch=2,
                           rear=(E("gable", "LOW", "Clapboard", "SlateGreen", 6.0, 3.0),
                                 E("cross", "LOW", "BoardBatten", "TinOxide", 6.0, 3.0, barge=True),
                                 C("across", "Clapboard", "Slate", 9.0, grow=True))),
    "QueenAnneTurret": dict(hh=2, roof="gable", rise=4.3, upper=(3.75, "Fishscale"), roof_mat="SlateBrown",
                            door="GreyBlue", bays=[-2.5, 0.0], door_x=-2.5, porch="half", porch_x=(-X_ + E_, 1.0),
                            tower=dict(kind="oct", x=2.38, a=1.15, above=2.4, rise=3.4), finial=True,
                            rear=(E("gable", "LOW", "Clapboard", "TinGreen", 7.0, 3.0, grow=True),
                                  C("across", "BoardBatten", "SlateBrown", 8.0, cupola=True))),
    "QueenAnneBay": dict(hh=2, roof="gable", rise=4.6, band=True, roof_mat="SlateDark", door="Black",
                         bays=[-2.5, 2.0], door_x=-2.5, bay=dict(x=2.0, z1=6.75, mat="Fishscale"), porch="half",
                         porch_x=(-X_ + E_, -1.25), dormers=True, finial=True, backporch=2, lites="6",
                         rear=(E("cross", "MID", "Clapboard", "Slate", 6.5, 4.5, barge=True),
                               E("gable", "LOW", "BoardBatten", "TinFlat", 6.0, 3.0, grow=True))),
    "StickGable": dict(hh=2, roof="gable", rise=4.8, stick=True, truss=True, gable_mat="BoardBatten", gwin="single",
                       roof_mat="SlateDark", door="Black", door_x=2.5, porch="full", spindles=False, chimney=2,
                       rear=(E("shed", "MID", "BoardBatten", "TinGreen", 6.0, 4.0, rise=1.6),
                             E("gable", "LOW", "Clapboard", "SlateDark", 7.0, 3.0, grow=True),
                             C("across", "BoardBatten", "TinOxide", 8.0, cupola=True))),
    "StickTower": dict(hh=2, roof="gable", rise=4.8, stick=True, truss=True, gable_mat="BoardBatten",
                       roof_mat="SlateGreen", door="Oxblood", bays=[-2.5, 0.0], door_x=-2.5, porch="half",
                       porch_x=(-X_ + E_, 1.1), spindles=False,
                       tower=dict(kind="square", x=2.59, a=1.1, above=2.6, rise=3.0, mat="BoardBatten", roof="TinGreen"),
                       rear=(E("cross", "LOW", "BoardBatten", "SlateGreen", 6.0, 3.0, barge=True),
                             E("shed", "LOW", "Clapboard", "TinFlat", 6.0, 3.0, rise=1.5, grow=True),
                             C("gambrel", "Clapboard", "SlateDark", 8.0, cupola=True))),
    "QueenAnneGambrel": dict(hh=2, roof="gambrel", band=True, roof_mat="SlateDark", door="GreyBlue", door_x=-2.5,
                             porch="full", barge=True, finial=True,
                             rear=(E("gable", "MID", "Clapboard", "SlateBrown", 7.0, 4.0, piazza=1, grow=True),
                                   C("across", "BoardBatten", "TinFlat", 8.0))),
    "GothicBatten": dict(hh=2, roof="gable", storeys=2, rise=5.6, wall="BoardBatten", gable_mat="BoardBatten",
                         gwin="lancet", roof_mat="TinOxide", door="Black", door_x=0.0, shutters="Green", porch="full",
                         spindles=False, barge=True, finial=True,
                         rear=(E("cross", "MID", "Clapboard", "SlateGreen", 6.5, 4.5, piazza=2),
                               E("shed", "LOW", "BoardBatten", "TinFlat", 5.0, 3.0, rise=1.5, grow=True))),
    "PaintedTriple": dict(hh=3, roof="flat", band=True, door="Green", door_x=-2.5, porch="stack", barge=True,
                          finial=True, backporch=2, roof_mat="SlateDark",
                          rear=(E("gable", "MID", "Clapboard", "SlateDark", 6.0, 4.0),
                                E("gable", "LOW", "BoardBatten", "TinGreen", 6.0, 3.0),
                                C("across", "Clapboard", "TinOxide", 8.0, grow=True))),
    "GableTriple": dict(hh=3, roof="gable", rise=4.0, upper=(6.85, "Fishscale"), roof_mat="Slate", door="Oxblood",
                        door_x=2.5, porch="stack", backporch=2, hand="R",
                        rear=(E("gable", "MID", "Clapboard", "TinOxide", 7.0, 4.0, piazza=2, grow=True),
                              E("gable", "MID", "BoardBatten", "TinOxide", 6.0, 4.0))),
    "BayTriple": dict(hh=3, roof="flat", door="Black", bays=[-2.5, -.6, 2.45], door_x=-2.5, porch="stack",
                      porch_x=(-X_ + E_, .95), bay=dict(x=2.45, w=1.2, proj=.6, z1=9.3), roof_mat="SlateGreen",
                      finial=True, hand="R",
                      rear=(E("shed", "LOW", "BoardBatten", "TinGreen", 6.0, 3.0, rise=1.5, grow=True),
                            C("hip", "Clapboard", "TinGreen", 8.0, cupola=True))),
    "QueenAnneDouble": dict(hh=3, roof="gable", rise=4.4, upper=(6.85, "Fishscale"), gwin="triple", roof_mat="Slate",
                            door="Green", door_x=2.5, porch="double", dormers=True, band=True,
                            rear=(E("cross", "MID", "Clapboard", "Slate", 6.0, 4.5, piazza=1, barge=True),
                                  E("gable", "MID", "BoardBatten", "Slate", 7.0, 4.0, grow=True),
                                  C("gambrel", "Clapboard", "TinOxide", 8.0))),
    "StickDouble": dict(hh=3, roof="gable", rise=5.0, stick=True, truss=True, gable_mat="BoardBatten",
                        roof_mat="SlateBrown", door="Black", door_x=0.0, porch="double", spindles=False, chimney=2,
                        backporch=2, hand="R",
                        rear=(E("shed", "MID", "BoardBatten", "SlateDark", 6.0, 4.0, rise=1.6),
                              E("cross", "LOW", "Clapboard", "TinGreen", 6.0, 3.0, barge=True),
                              C("across", "BoardBatten", "TinFlat", 8.0, grow=True))),
    "CornerQueenAnneLeftCorner": dict(hh=3, corner=True, ci=2.0, roof="gable", rise=4.2, upper=(6.85, "Fishscale"),
                                      roof_mat="SlateGreen", door="Oxblood", bays=[1.0, 2.9], door_x=1.0,
                                      porch="wrap", wrap_len=6.0,
                                      tower=dict(kind="oct", x=-1.99 + 1.12, a=1.1, z0=3.95, above=2.4, rise=3.2),
                                      finial=True,
                                      rear=(E("gable", "LOW", "Clapboard", "SlateGreen", 7.0, 3.0, grow=True),
                                            C("hip", "BoardBatten", "TinOxide", 8.0, cupola=True))),
    "CornerStickLeftCorner": dict(hh=3, corner=True, roof="gable", rise=4.8, stick=True, truss=True,
                                  gable_mat="BoardBatten", roof_mat="SlateDark", door="Green", bays=[0.0, 2.5],
                                  door_x=2.5, porch="half", porch_x=(-1.2, X_ - E_), spindles=False,
                                  side_bays=[2.0, 4.5, 7.0, 9.5],
                                  ci=.5, tower=dict(kind="square", x=-3.49 + 1.12, a=1.1, above=2.6, rise=3.0,
                                             mat="BoardBatten", roof="SlateDark"),
                                  rear=(E("gable", "LOW", "BoardBatten", "TinGreen", 5.0, 3.0, grow=True),
                                        C("gambrel", "Clapboard", "SlateBrown", 8.0))),
    "CornerTripleLeftCorner": dict(hh=3, corner=True, ci=.5, roof="flat", band=True, door="Black", door_x=2.5,
                                   porch="stack", barge=True, finial=True, backporch=2, roof_mat="SlateDark",
                                   rear=(E("gable", "MID", "Clapboard", "TinGreen", 7.0, 4.0, piazza=1, grow=True),
                                         C("across", "BoardBatten", "SlateDark", 8.0))),
    "CornerGothicLeftCorner": dict(hh=3, corner=True, roof="side", storeys=2, depth=9.0, xgables=((.2, 3.2),),
                                   xpitch=1.5, wall="BoardBatten", gable_mat="BoardBatten", roof_mat="SlateDark",
                                   door="Oxblood", door_x=.2, porch="full", spindles=False, barge=True, finial=True,
                                   rear=(E("cross", "LOW", "Clapboard", "TinFlat", 6.0, 3.0, barge=True),
                                         C("hip", "BoardBatten", "SlateGreen", 8.0, cupola=True, grow=True))),
    "QuadDecker": dict(hh=4, roof="flat", storeys=4, band=True, door="Black", door_x=-2.5, porch="stack4",
                       barge=True, backporch=2, roof_mat="SlateDark",
                       rear=(E("gable", "MID", "BoardBatten", "TinOxide", 8.0, 4.0, piazza=1, grow=True),
                             E("shed", "LOW", "Clapboard", "TinFlat", 5.0, 3.0, rise=1.6))),
    "QueenAnneQuad": dict(hh=4, roof="gable", storeys=4, rise=4.0, upper=(9.85, "Fishscale"), roof_mat="SlateBrown",
                          door="GreyBlue", bays=[-2.5, 0.0], door_x=-2.5, porch="stack4", porch_x=(-X_ + E_, 1.3),
                          tower=dict(kind="oct", x=2.42, a=1.1, rise=3.6), backporch=2, hand="R",
                          rear=(E("cross", "MID", "BoardBatten", "TinGreen", 6.5, 4.5, piazza=1, barge=True),
                                E("gable", "MID", "Clapboard", "TinGreen", 6.0, 4.0, grow=True))),
}
# Corners carry a plain fascia (no lettering): the game mirrors a LeftCorner for right-hand corners.
# Main Street (the author 2026-11-16, ZM1 rework): a New England brick downtown, its own architecture. 3-4 storey masonry
# commercial blocks (cast-iron or granite shopfronts, stone-trimmed flats above, oriels and bays, corbelled or
# bracketed cornices, mansards, brick gable fronts, a turret and two corner towers) stepping down behind to the lane.
# front="shop" and storeys keep the households (lt_roster.households); lt_designs/mainst.py builds them.
MAIN_STREET = {
    "HardwareBlock": dict(front="shop", storeys=3, ground="iron", roof="flat", cornice="corbel", hood="cap",
                          back=(2, 1), escape=True, awning="Green", wall="Brick074", door="Green", lites="2",
                          sign="HarborHardware", sign_side="r"),
    "BookBlock": dict(front="shop", storeys=4, ground="iron", roof="flat", cornice="bracket", pediment=True,
                      upper="oriel", oriel_mat="Cream", back=(1,), wall="Brick054", door="Black", lites="2",
                      sign="TidewaterBooks", sign_side="l"),
    "DrugGable": dict(front="shop", storeys=3, ground="granite", roof="gable", parapet=True, back=(2, 1),
                      wall="BuffBrick", roof_mat="SlateDark", door="Oxblood", lites="2", sign="PenobscotDrug",
                      sign_side="r"),
    "CafeMansard": dict(front="shop", storeys=3, ground="iron", roof="mansard", hood="pediment", back=(2, 1),
                        decks=True, awning="Oxblood", wall="BrownBrick", roof_mat="SlateGreen", door="Oxblood",
                        lites="2", sign="SeaSmokeCafe", sign_side="l"),
    "DryGoodsBlock": dict(front="shop", storeys=4, ground="granite", roof="flat", cornice="bracket", pediment=True,
                          hall=True, hood="cap", back=(2, 1), wall="Brick085", door="Black", lites="2",
                          sign="KnoxDryGoods", sign_side="r"),
    "BakeryGable": dict(front="shop", storeys=3, ground="iron", roof="gable", upper="bays", back=(1,),
                        awning="GreyBlue", wall="Brick094", roof_mat="SlateGreen", door="GreyBlue", lites="2",
                        sign="BalsamBakery", sign_side="l"),
    "ProvisionsMansard": dict(front="shop", storeys=3, ground="granite", roof="mansard", hood="pediment",
                              quoins=True, back=(2, 1), escape=True, wall="Greystone", back_mat="BrownBrick",
                              roof_mat="SlateDark", door="Green", lites="6", sign="SaltPier", sign_side="r"),
    "OutfittersBlock": dict(front="shop", storeys=3, ground="iron", roof="flat", cornice="bracket", upper="turret",
                            hood="cap", back=(2,), wall="Brick074", roof_mat="SlateGreen", door="GreyBlue",
                            lites="2", sign="GullRock", sign_side="r"),
    "CornerBrickShopLeftCorner": dict(front="shop", storeys=4, ground="iron", roof="flat", cornice="bracket",
                                      hood="cap", corner=True, tower="square", back=(2,), escape=True,
                                      wall="Brick085", roof_mat="SlateDark", door="Green", lites="2"),
    "CornerGableShopLeftCorner": dict(front="shop", storeys=3, ground="granite", roof="gable", corner=True,
                                      tower="octagon", back=(2, 1), wall="BuffBrick", roof_mat="SlateDark",
                                      door="Oxblood", lites="2"),
}
# Prestige Cottages (ZP1) and Cottage Flats (ZP2), second edition (the author 2026-11-17, Direction A): the Federal and Greek
# Revival harbour town of Portland's West End, Bath and Wiscasset, 1800-1850. Painted clapboard (white, cream, straw,
# pale grey-blue) with green or black shutters, Federal brick ends, granite steps, Greek gable fronts; behind, an ell
# to a red or white carriage barn round a service court (rule 17). ZP1: grand detached captains' houses, one family;
# ZP2: doubles, brick rows and twin temples cut into flats. Built by lt_designs/federal.py. The Bar Harbor shingle
# cottages these replace are in lt_roster.pre_federal.py.
F = dict(palette="federal")
PRESTIGE = {
    "CaptainsHip": dict(F, kind="hip", storeys=2, walk=True, entry="fan", shutters="Green", door="Black",
                        ell="MID", barn="gable", barn_h="MID", cupola=True, wings="far"),
    "BrickEndFederal": dict(F, kind="side", storeys=2, brick_ends="Brick074", entry="fan", portico=True,
                            shutters="Black", door="Green", ell="LOW", barn="gambrel", barn_h="LOW"),
    "GreekTemple": dict(F, kind="temple", storeys=2, entry="side", portico=True, shutters="Green", door="Black",
                        ell="LOW", barn="cross", barn_h="LOW", lofts=True),
    "WiscassetGambrel": dict(F, kind="gambrel", storeys=2, dormers=True, entry="fan", shutters="Black",
                             door="Black", ell="MID", woodshed=True, barn="gable", barn_h="LOW", cupola=True,
                             wings="far"),
    "ConnectedCape": dict(F, kind="cape", dormers=True, entry="fan", shutters="Green", door="Green", lites="6",
                          ell="LOW", barn="gable", barn_h="LOW", cupola=True, lofts=True),
    "FederalSquare": dict(F, kind="side", storeys=3, brick="Brick054", walk=True, entry="fan", shutters="Green",
                          door="Black", ell="MID", barn="gambrel", barn_h="MID", wings="twin"),
    "GreekPorch": dict(F, kind="temple", storeys=2, entry="side", porch=True, shutters="Black", door="Green",
                       ell="LOW", barn="gambrel", barn_h="LOW", cupola=True),
    "BathMansion": dict(F, kind="hip", storeys=3, lantern=True, entry="fan", portico=False, shutters="Black",
                        door="Black", ell="MID", woodshed=True, barn="cross", barn_h="LOW", lofts=True, wings="far"),
    # Corners (Antigravity 2026-11-18): LeftCorner Federal/Greek captains' mansions with side-street porch & entrance
    "CaptainsCornerLeftCorner": dict(F, kind="hip", storeys=2, walk=True, entry="fan", shutters="Green", door="Black",
                                     ell="MID", barn="gable", barn_h="MID", cupola=True, corner=True,
                                     lots=[(2, 4), (3, 4), (3, 5)]),
    "FederalCornerLeftCorner": dict(F, kind="side", storeys=3, brick_ends="Brick074", entry="fan",
                                    shutters="Black", door="Green", ell="LOW", barn="gambrel", barn_h="LOW", corner=True,
                                    lots=[(2, 4), (3, 4), (3, 5)]),
    "GreekCornerLeftCorner": dict(F, kind="temple", storeys=2, entry="side", shutters="Black",
                                  door="Black", ell="LOW", barn="cross", barn_h="LOW", lofts=True, corner=True,
                                  lots=[(2, 4), (3, 4), (3, 5)]),
}
# Cottage Flats (Medium, zone ZP2): the same harbour town, denser: Federal doubles, brick rows, twin Greek fronts.
COTTAGE_FLATS = {
    "FederalDouble": dict(F, kind="side", storeys=3, doors=2, entry="fan", shutters="Green", door="Black",
                          ell="MID", wings="twin", barn="gable", barn_h="MID", flats=True),
    "BrickRow": dict(F, kind="side", storeys=3, units=3, brick="Brick074", entry="fan", shutters="Black",
                     door="Green", ell="MID", barn="gable", barn_h="MID", cupola=True, flats=True),
    "GreekTwin": dict(F, kind="twin", storeys=3, entry="side", shutters="Green", door="Black", ell="MID",
                      wings="twin", barn="gambrel", barn_h="MID", flats=True),
    "CapeDouble": dict(F, kind="cape", doors=2, dormers=True, entry="fan", shutters="Black", door="Green",
                       ell="LOW", barn="gable", barn_h="MID", lofts=False, flats=True, wings="far"),
    "HipDouble": dict(F, kind="hip", storeys=3, doors=2, walk=True, entry="fan", shutters="Black", door="Black",
                      ell="MID", wings="twin", barn="cross", barn_h="MID", flats=True),
    "GambrelDouble": dict(F, kind="gambrel", storeys=2, doors=2, dormers=True, entry="fan", shutters="Green",
                          door="Green", ell="MID", barn="gambrel", barn_h="MID", flats=True, wings="far"),
    "BrickEndDouble": dict(F, kind="side", storeys=3, doors=2, brick_ends="Brick054", entry="fan",
                           shutters="Green", door="Black", ell="MID", barn="gambrel", barn_h="MID", flats=True),
    "GreekFlats": dict(F, kind="temple", storeys=3, entry="side", porch=True, shutters="Black", door="Black",
                       ell="MID", barn="gable", barn_h="MID", cupola=True, flats=True),
}
FLATS_HH = {(3, 5): 6, (3, 6): 7, (4, 5): 8, (4, 6): 10}          # households by lot (Toronto's big houses: 6-10)
# Grand Hotels (High, zone ZP3; the author 2026-11-15: "build them, but ... using steroids"): the brief's Brazil-style
# beachfront towers in Maine shingle. The cottage family's last rung: a shingle tower over the double-decker verandah,
# balconies on every floor, the turret running the full height, a four-storey court block behind. Red oxide tin
# roofs on six (the board game's red hotels, as a nod; Wentworth by the Sea's red roofs as the real precedent).
# `storeys` is the 4-wide tower; each extra cell of width adds two (cottage.build).
GRAND_HOTELS = {
    "AtlanticTower": dict(hotel=True, sign="TheAtlantic", storeys=14, roof="gambrel", turret=True, cross=True,
                          base="Greystone", wall="ShingleSilver", gable_mat="ShingleGrey", roof_mat="TinOxide",
                          door="Black", lites="2", car="gable", cupola=True, wing="twin", lantern=True),
    "TennesseeTower": dict(hotel=True, sign="TheTennessee", storeys=12, roof="gable", turret=True, cross=False,
                           hand="R", wall="ShingleGrey", gable_mat="ShingleSilver", roof_mat="TinOxide", door="Green",
                           lites="6", car="gambrel", wing="near", lantern=True),
    "NewYorkTower": dict(hotel=True, sign="TheNewYork", storeys=14, roof="gable", turret=False, cross=True,
                         base="Rubble", wall="Clapboard", gable_mat="ShingleSilver", roof_mat="TinOxide",
                         door="Oxblood", lites="2", car="cross", lofts=True, wing="far"),
    "VirginiaTower": dict(hotel=True, sign="TheVirginia", storeys=12, roof="gambrel", turret=True, cross=False,
                          wall="ShingleSilver", gable_mat="ShingleGrey", roof_mat="SlateDark", door="GreyBlue",
                          lites="6", car="gable", cupola=True, wing="twin"),
    "OrientalTower": dict(hotel=True, sign="TheOriental", storeys=16, roof="gable", turret=True, cross=True, hand="R",
                          base="Greystone", wall="ShingleGrey", gable_mat="ShingleSilver", roof_mat="TinOxide",
                          door="Black", lites="2", car="gambrel", wing="far", lantern=True),
    "VermontTower": dict(hotel=True, sign="TheVermont", storeys=12, roof="gambrel", turret=False, cross=True, hand="R",
                         wall="ClapSage", gable_mat="ShingleSilver", roof_mat="TinOxide", door="Green", lites="2",
                         car="cross", cupola=True, wing="near", lantern=True),
    "StatesTower": dict(hotel=True, sign="TheStates", storeys=14, roof="gable", turret=True, cross=True,
                        wall="Clapboard", gable_mat="ShingleGrey", roof_mat="SlateDark", door="Oxblood", lites="6",
                        car="gable", lofts=True, wing="twin"),
    "PennsylvaniaTower": dict(hotel=True, sign="ThePennsylvania", storeys=16, roof="gambrel", turret=True, cross=True,
                              hand="R", base="Rubble", wall="ShingleSilver", gable_mat="ShingleGrey",
                              roof_mat="TinOxide", door="GreyBlue", lites="6", car="gambrel", cupola=True,
                              wing="twin", lantern=True),
    # Corners (Antigravity 2026-11-18): LeftCorner beachfront shingle towers with wrapped double-decker verandah, no sign
    "AtlanticCornerLeftCorner": dict(hotel=True, storeys=14, roof="gambrel", turret=True, cross=True, corner=True,
                                     base="Greystone", wall="ShingleSilver", gable_mat="ShingleGrey", roof_mat="TinOxide",
                                     door="Black", lites="2", car="gable", cupola=True, pavilions=((.5, 4, "dome"),),
                                     spire=2, lots=[(4, 5), (5, 5), (5, 6), (6, 6)]),
    "VirginiaCornerLeftCorner": dict(hotel=True, storeys=12, roof="gable", turret=True, cross=False, corner=True,
                                     wall="ShingleGrey", gable_mat="ShingleSilver", roof_mat="SlateDark", door="GreyBlue",
                                     lites="6", car="gambrel", cupola=True, pavilions=((.5, 3, "hipl"),),
                                     spire=3, lots=[(4, 5), (5, 5), (5, 6), (6, 6)]),
    "OrientalCornerLeftCorner": dict(hotel=True, storeys=16, roof="gambrel", turret=True, cross=True, corner=True,
                                     base="Rubble", wall="Clapboard", gable_mat="ShingleSilver", roof_mat="TinOxide",
                                     door="Oxblood", lites="2", car="cross", lofts=True, pavilions=((.5, 4, "hip"),),
                                     spire=3, lots=[(4, 5), (5, 5), (5, 6), (6, 6)]),
}
GRAND_HH = {(4, 4): 28, (4, 5): 34, (4, 6): 40, (5, 5): 46, (5, 6): 55, (6, 6): 70}   # households by lot (a High zone tower)
# Boardwalk (the author 2026-11-15, "commercial boardwalk low/high"; Low repurposes his Commercial Waterfront zone): shingle
# shops in a row behind a covered arcade over a plank boardwalk, one front gable per 8 m cell. Built by boardwalk.py.
# Boardwalk Shops, ZC1 (the author 2026-11-16, "mixed, built up over time"): half brick commercial blocks (cast-iron fronts,
# signs painted on the brick, corbelled or bracketed cornices) and half painted clapboard false fronts in stronger
# paint, 1-3 storeys, every door at grade. Built by shops.py (ZC2 stays on boardwalk.py).
BOARDWALK_SHOPS = {
    "TaffyShop": dict(kind="clap", storeys=1, top="step", roof="gable", awning=True, wall="Clapboard",
                      roof_mat="SlateDark", door="Oxblood", lites="6", palette="shopfront", sign="SaltWaterTaffy", stock="shed",
                      stock_mat="TinOxide", vent=True),
    "PennyArcade": dict(kind="brick", storeys=2, ground="iron", cornice="bracket", pediment=True, wall="Brick085",
                        door="Black", sign="PennyArcade", sign_side="l"),
    "OysterHouse": dict(kind="clap", storeys=2, top="flat", roof="shed", awning=True, wall="Clapboard",
                        roof_mat="SlateGreen", door="GreyBlue", palette="shopfront", sign="OysterHouse", sign_side="l", stock="gable"),
    "FudgeKitchen": dict(kind="brick", storeys=2, ground="granite", cornice="corbel", back="store", wall="BuffBrick",
                         door="Green", sign="FudgeKitchen"),
    "BathHouses": dict(kind="brick", storeys=3, ground="iron", cornice="corbel", pediment=True, back="store",
                       wall="Brick054", door="Oxblood", lites="6", sign="BathHouses"),
    "TintypeStudio": dict(kind="brick", storeys=3, ground="granite", cornice="bracket", skylight=True, wall="Brick094",
                          door="Black", sign="TintypeStudio", sign_side="l"),
    "ClamShack": dict(kind="clap", storeys=1, top="flat", roof="shed", awning=True, wall="Clapboard",
                      roof_mat="TinOxide", door="Green", lites="6", palette="shopfront", sign="ClamShack", stock="shed"),
    "KiteShop": dict(kind="clap", storeys=2, top="step", roof="gable", awning=False, wall="Clapboard",
                     roof_mat="SlateGreen", door="Black", lites="6", palette="shopfront", sign="KiteShop", sign_side="l", stock="shed"),
# Corners (the author 2026-11-17): no bare party wall at a block end. LeftCorner, no lettering (the game mirrors them).
    "ChandleryLeftCorner": dict(kind="brick", storeys=3, ground="granite", cornice="bracket", back="store",
                                wall="Brick074", door="Green", lites="2", corner=True),
    "SailLoftLeftCorner": dict(kind="brick", storeys=2, ground="iron", cornice="corbel", wall="Brick054",
                               door="Oxblood", lites="2", corner=True),
    "BaitTackleLeftCorner": dict(kind="clap", storeys=2, top="flat", roof="gable", awning=True, wall="Clapboard",
                                 roof_mat="SlateDark", door="GreyBlue", lites="6", palette="shopfront", stock="gable",
                                 corner=True),
    "IceCreamLeftCorner": dict(kind="clap", storeys=1, top="flat", roof="shed", awning=False, wall="Clapboard",
                               roof_mat="TinOxide", door="Oxblood", lites="6", palette="shopfront", stock="shed",
                               corner=True),
}
BOARDWALK_PALACES = {
    "GrandArcade": dict(storeys=5, promenade=True, roofs="gmg", turret="both", lantern=True, base="Greystone",
                        wall="ShingleSilver", gable_mat="ShingleGrey", roof_mat="TinOxide", door="Green", sign="GrandArcade"),
    "Emporium": dict(storeys=6, promenade=True, roofs="g", turret="l", back="store", lantern=True, wall="Clapboard",
                     gable_mat="ShingleSilver", roof_mat="SlateDark", door="Black", sign="Emporium"),
    "MusicHall": dict(storeys=4, promenade=True, roofs="m", turret="both", lantern=True, wall="ShingleGrey",
                      gable_mat="ShingleSilver", roof_mat="SlateGreen", door="Oxblood", sign="MusicHall"),
    "RollerRink": dict(storeys=4, promenade=True, roofs="mg", turret="r", back="store", wall="ClapSage",
                       gable_mat="ShingleSilver", roof_mat="TinOxide", door="GreyBlue", sign="RollerRink"),
    "Natatorium": dict(storeys=5, promenade=True, roofs="gm", back="store", lantern=True, base="Rubble",
                       wall="ShingleSilver", gable_mat="ShingleGrey", roof_mat="SlateDark", door="Green", sign="Natatorium"),
    "PicturePalace": dict(storeys=6, promenade=True, roofs="mgm", turret="both", wall="Clapboard",
                          gable_mat="ShingleGrey", roof_mat="TinOxide", door="Oxblood", sign="PicturePalace"),
    "Ballroom": dict(storeys=5, promenade=True, roofs="g", turret="l", back="store", lantern=True, wall="ShingleGrey",
                     gable_mat="ShingleSilver", roof_mat="TinOxide", door="Black", sign="Ballroom"),
    "SeasideMarket": dict(storeys=4, promenade=True, roofs="gmmg", turret="r", back="store", base="Greystone",
                          wall="ShingleSilver", gable_mat="ShingleGrey", roof_mat="SlateGreen", door="GreyBlue",
                          sign="SeasideMarket"),
    "TidewaterCasino": dict(storeys=4, promenade=True, roofs="gm", turret="both", spire=(1,1), towers=(("l",2,"hipl"),("r",2,"hipl")), base="Greystone", wall="ShingleSilver", gable_mat="ShingleGrey", roof_mat="SlateGreen", door="Oxblood"),
    "SeaBathhouse": dict(storeys=3, promenade=True, roofs="g", turret="both", back="store", lantern=True, base="Rubble", wall="ClapSage", gable_mat="ShingleSilver", roof_mat="TinOxide", door="GreyBlue"),
    "DancePavilion": dict(storeys=3, promenade=True, roofs="mmg", turret="both", lantern=True, wall="ShingleGrey", gable_mat="ShingleSilver", roof_mat="SlateDark", door="Oxblood"),
    "BathingHotel": dict(storeys=5, promenade=True, roofs="g", turret="l", towers=(("c",2,"hip"),), back="store", base="Greystone", wall="Clapboard", gable_mat="ShingleGrey", roof_mat="SlateGreen", door="Black"),
    # Corners (Antigravity 2026-11-18): LeftCorner only, wrapped two-deck promenade and corner château tower, no lettering
    "CornerCasinoLeftCorner": dict(storeys=5, promenade=True, roofs="m", turret="both", spire=(2, 1),
                                   towers=(("c", 2, "dome"),), base="Greystone", wall="ShingleSilver",
                                   gable_mat="ShingleGrey", roof_mat="TinOxide", door="Oxblood", corner=True,
                                   lots=[(4, 4), (4, 5), (5, 5), (4, 6), (5, 6), (6, 6)]),
    "CornerPavilionLeftCorner": dict(storeys=4, promenade=True, roofs="g", turret="both", spire=(1, 2),
                                     towers=(("l", 2, "hipl"),), back="store", base="Rubble", wall="Clapboard",
                                     gable_mat="ShingleSilver", roof_mat="SlateGreen", door="Green", corner=True,
                                     lots=[(4, 4), (4, 5), (5, 5), (4, 6), (5, 6), (6, 6)]),
    "CornerExchangeHallLeftCorner": dict(storeys=6, promenade=True, roofs="g", turret="l", spire=(3, 0),
                                         towers=(("c", 3, "hip"),), pitch=1.5, wall="ShingleGrey",
                                         gable_mat="ShingleSilver", roof_mat="SlateDark", door="Black", corner=True,
                                         lots=[(4, 4), (4, 5), (5, 5), (4, 6), (5, 6), (6, 6)]),
    "CornerPierPalaceLeftCorner": dict(storeys=5, promenade=True, roofs="mmg", turret="both", spire=(2, 1),
                                       towers=(("r", 2, "dome"),), back="store", base="Greystone", wall="ClapSage",
                                       gable_mat="ShingleGrey", roof_mat="TinOxide", door="GreyBlue", corner=True,
                                       lots=[(4, 4), (4, 5), (5, 5), (4, 6), (5, 6), (6, 6)]),
}
# Cannery Row (Claude 2026-11-15, the author: "do whatever you want"): Eastport and Lubec waterfront industry. Long sheds
# shoulder to shoulder behind a loading dock, ridge ventilators and brick stacks. Green industry: each design makes one
# clean product (setup restricts the building to it). Built by cannery.py.
CANNERY_ROW = {
    "SardineCannery": dict(masonry=True, storeys=2, roof="side", cross=(1,), stack=True, arch=True, wall="Brick085",
                           base="Greystone", roof_mat="Slate", door="Oxblood", sign="QuoddyPacking"),
    "SmokehouseRow": dict(storeys=3, roofs="g", vents="monitor", wall="ShingleGrey", roof_mat="SlateDark", door="Black",
                          sign="SmokedHerring"),
    "LobsterPound": dict(storeys=1, roofs="g", vents="cupola", base="Rubble", wall="ShingleSilver", roof_mat="SlateGreen",
                         door="GreyBlue", sign="LiveLobsters"),
    "IceHouse": dict(masonry=True, storeys=3, roof="mansard", tower="right", back="store", arch=False, wall="Brick054",
                     base="Dressed", roof_mat="Slate", door="Green", sign="HarborIce"),
    "Ropewalk": dict(masonry=True, storeys=2, roof="side", tower="left", back="store", arch=True, wall="BrownBrick",
                     base="Rubble", roof_mat="SlateGreen", door="Oxblood", sign="CordageWorks"),
    "SailLoft": dict(masonry=True, storeys=3, roof="front", roofs="m", arch=False, wall="Brick094", base="Greystone",
                     roof_mat="SlateBrown", door="GreyBlue", sign="SailLoft"),
    "BoatShop": dict(masonry=True, storeys=2, roof="front", roofs="g", vents="monitor", stack=True, back="store", arch=True,
                     wall="Brick074", base="Greystone", roof_mat="SlateGreen", door="Green", sign="BoatBuilders"),
    "Cooperage": dict(masonry=True, storeys=2, roof="front", roofs="mg", stack=True, arch=False, wall="BuffBrick",
                      base="Rubble", roof_mat="Slate", door="Black", sign="Cooperage"),
    # Expansion (Antigravity 2026-11-18): 4 missing clean trades (Paper, Timber, Beverages, Machinery) + 4 LeftCorners
    "CrateBoxMill": dict(masonry=True, storeys=3, roof="mansard", stack=True, back="store", arch=True,
                         wall="BuffBrick", base="Greystone", roof_mat="SlateDark", door="Black", dock=1.0),
    "PlaningMill": dict(masonry=True, storeys=2, roof="front", roofs="g", vents="monitor", back="store", arch=False,
                        wall="BrownBrick", base="Rubble", roof_mat="SlateGreen", door="Green", dock=1.0),
    "SpruceBrewery": dict(masonry=True, storeys=3, roof="mansard", tower="left", stack=True, arch=True, wall="Brick074",
                          base="Dressed", roof_mat="Slate", door="Oxblood", dock=1.0),
    "MarineIronworks": dict(masonry=True, storeys=3, roof="front", roofs="mg", vents="monitor", stack=True, back="store",
                            arch=True, wall="Brick054", base="Greystone", roof_mat="SlateDark", door="Black", dock=1.0),
    "CanneryLeftCorner": dict(masonry=True, storeys=2, roof="side", stack=True, arch=True, wall="Brick085",
                              base="Greystone", roof_mat="Slate", door="Oxblood", corner=True, dock=1.0),
    "CordageLeftCorner": dict(masonry=True, storeys=3, roof="mansard", tower="left", back="store", arch=False,
                              wall="BrownBrick", base="Rubble", roof_mat="SlateGreen", door="Green", corner=True, dock=1.0),
    "BoatyardLeftCorner": dict(masonry=True, storeys=2, roof="front", roofs="g", vents="monitor", stack=True, back="store",
                               arch=True, wall="Brick074", base="Greystone", roof_mat="SlateDark", door="GreyBlue",
                               corner=True, dock=1.0),
    "IronworksLeftCorner": dict(masonry=True, storeys=3, roof="front", roofs="m", stack=True, arch=True, wall="BuffBrick",
                                base="Dressed", roof_mat="SlateBrown", door="Black", corner=True, dock=1.0),
}
PRODUCT = {"SardineCannery": "Food", "SmokehouseRow": "Food", "LobsterPound": "Food", "IceHouse": "Food",
           "Ropewalk": "Textiles", "SailLoft": "Textiles", "BoatShop": "Vehicles", "Cooperage": "Furniture",
           "CrateBoxMill": "Paper", "PlaningMill": "Timber", "SpruceBrewery": "Beverages", "MarineIronworks": "Machinery",
           "CanneryLeftCorner": "Food", "CordageLeftCorner": "Textiles", "BoatyardLeftCorner": "Vehicles",
           "IronworksLeftCorner": "Machinery"}
# Château (the author 2026-11-16, CHATEAU_PLAN.md): same materials, a grander form. Clusters of towers at different
# heights, steep pavilion roofs, spired turrets, dome and lantern crowns (rule 11b: crown blocks under 150 m2).
CHATEAU_PALACES = {
    "GrandArcade": dict(towers=(("c", 2, "hipl"),), spire=(1, 1), lantern=False),
    "Emporium": dict(towers=(("l", 2, "hip"),), spire=(3, 0), pitch=1.5),
    "MusicHall": dict(towers=(("c", 2, "dome"),), spire=(2, 1), lantern=False),
    "RollerRink": dict(towers=(("l", 2, "hip"),), spire=(0, 2), pitch=1.7),
    "Natatorium": dict(towers=(("l", 3, "hip"), ("r", 2, "hip"))),
    "PicturePalace": dict(towers=(("c", 3, "dome"),), spire=(1, 1)),
    "Ballroom": dict(towers=(("l", 2, "hipl"),), spire=(2, 0), pitch=1.6, lantern=False),
    "SeasideMarket": dict(towers=(("l", 3, "hip"), ("r", 2, "hip")), spire=(0, 1)),
}
CHATEAU_HOTELS = {
    "AtlanticTower": dict(pavilions=((.5, 4, "dome"),), spire=2, lantern=False),
    "TennesseeTower": dict(pavilions=((1.0, 3, "hip"),), spire=3),
    "NewYorkTower": dict(pavilions=((0.0, 4, "hip"), (1.0, 3, "hip"))),
    "VirginiaTower": dict(pavilions=((.5, 3, "dome"),), spire=2),
    "OrientalTower": dict(pavilions=((1.0, 5, "hipl"), (0.0, 4, "hip")), spire=4, lantern=False),
    "VermontTower": dict(pavilions=((0.0, 3, "hipl"),), lantern=False),
    "StatesTower": dict(pavilions=((0.0, 4, "hip"), (1.0, 3, "hip")), spire=3),
    "PennsylvaniaTower": dict(pavilions=((.5, 3, "dome"),), spire=3, lantern=False, cupola=False),
}
# Exchange Row (ZO1, Claude 2026-11-17, the author: "do something newish"): the office district the town lacked. Beaux-Arts
# banks and offices, c. 1900-1915: a granite banking storey, pale limestone ashlar, stone cornices, green copper roofs,
# bronze sashes, no white trim. Built by lt_designs/exchange.py. Offices: no households.
EXCHANGE_ROW = {
    "SeamensSavings": dict(storeys=3, ground="arch", rust=True, order="columns", crown="pediment", quoins=True,
                           hood="cap", back="hall"),
    "CustomHouse": dict(storeys=3, ground="arch", rust=True, hood="pediment", crown="dome", quoins=True,
                        back="step"),
    "MerchantsExchange": dict(storeys=4, ground="square", order="pilasters", hood="cap", roof="mansard", back="full"),
    "MarineInsurance": dict(storeys=4, ground="square", hood="cap", attic=True, back="court", back_mat="BuffBrick"),
    "CableOffice": dict(storeys=3, ground="arch", rust=True, roof="hip", quoins=True, back="block",
                        back_mat="BuffBrick"),
    "SteamshipAgency": dict(storeys=4, ground="square", oriels=True, crown="balustrade", back="hall",
                            back_mat="BuffBrick"),
    "TrustCompany": dict(storeys=3, ground="arch", rust=True, order="columns", attic=True, back="step"),
    "GazetteBuilding": dict(storeys=4, ground="square", order="pilasters", hood="pediment", crown="tower",
                            back="block", back_mat="BuffBrick"),
    # Corners (Antigravity 2026-11-18): LeftCorner only (game mirrors), wrapped granite arcade and stone cornice
    "HarbourBankLeftCorner": dict(storeys=3, ground="arch", rust=True, order="columns", hood="cap", crown="dome",
                                  back="hall", corner=True),
    "BoardOfTradeLeftCorner": dict(storeys=4, ground="square", order="pilasters", hood="cap", roof="mansard",
                                   back="full", corner=True),
    "MaritimeTrustLeftCorner": dict(storeys=3, ground="arch", rust=True, quoins=True, hood="pediment", roof="hip",
                                    back="step", back_mat="BuffBrick", corner=True),
    "TelegraphBlockLeftCorner": dict(storeys=4, ground="square", order="pilasters", hood="pediment", crown="tower",
                                     back="block", back_mat="BuffBrick", corner=True),
    # Parity expansion (Antigravity 2026-11-20): +4 Beaux-Arts maritime office designs (48 -> 64)
    "SteamshipOffice": dict(storeys=3, ground="arch", rust=True, order="columns", roof="hip", crown="pediment",
                            back="court", back_mat="BuffBrick", main_d=12.4, court_w=4.4),
    "ShippingExchange": dict(storeys=4, ground="arch", rust=True, order="pilasters", hood="pediment", crown="dome",
                             back="hall", main_d=13.2),
    "PortClearinghouse": dict(storeys=3, ground="square", oriels=True, roof="mansard", back="step",
                              back_mat="BuffBrick", main_d=15.0),
    "CustomsBrokerageLeftCorner": dict(storeys=4, ground="arch", rust=True, order="columns", attic=True,
                                       crown="pediment", back="court", back_mat="BuffBrick", corner=True,
                                       main_d=12.8, court_w=4.6),
}
# Civic and service buildings (ZS1, Claude 2026-11-17, the author: fire, police, clinic, schools, post office, town hall,
# library + working power and water, a decorative garbage barn). Fieldstone and shingle, Richardson manner (the author's
# pick). Built by lt_designs/civic.py; one lot per design ("lot"). Not a game zone: tools/newfrance_services.json
# turns each into a service. No households.
CIVIC = {
    "FireStation": dict(lot=(4, 4), storeys=2, engines=3, tower="hose", wing="low", depth=13.0),
    "Constabulary": dict(lot=(4, 4), storeys=2, roof="steep", turret="left", vbays=2, wing="low", depth=12.0),
    "CottageHospital": dict(lot=(4, 4), storeys=2, ground="square", porch=True, vbays=2, wing="twin", depth=12.0,
                            set=2.1),
    "GrammarSchool": dict(lot=(4, 5), storeys=2, cupola=True, wing="twin", depth=13.0),   # the author: rear unlike the police
    "Academy": dict(lot=(5, 6), storeys=3, tower="clock", wing="twin", depth=14.0),
    "PostOffice": dict(lot=(3, 3), storeys=1, roof="gable", turret="right", vbays=1, wing="low", depth=11.0),
    "TownHall": dict(lot=(4, 5), storeys=2, roof="gable", turret="left", tower="belfry", wing="mid", depth=15.0),
    "Library": dict(lot=(4, 4), storeys=1, roof="steep", turret="left", tower="lookout", wing="low", depth=12.0),
    "Waterworks": dict(lot=(3, 3), storeys=1, roof="steep", ground="square", stacks=1, cupola=True, wing="low",
                       depth=10.0),
    "Powerhouse": dict(lot=(4, 5), storeys=2, stacks=2, wing="mid", depth=14.0),
    "TransferBarn": dict(lot=(3, 3), storeys=1, roof="gable", engines=2, wing="low", depth=12.0),
    # Civic additions (Antigravity 2026-11-18): College/University + Full-Capacity General Hospital
    "MaritimeCollege": dict(lot=(6, 6), storeys=3, roof="hip", turret="left", tower="clock", wing="quad", depth=16.0),
    "GeneralHospital": dict(lot=(6, 5), storeys=3, ground="square", porch=True, vbays=3, cupola=True, wing="wards",
                            depth=15.0, set=2.1),
}
# Landmarks (ZS2, Claude 2026-11-17, the author: "lean into the gaudiness: sea animals"). Five one-off ploppables built by
# lt_designs/landmarks.py; one lot each. Not a game zone: tools/newfrance_services.json makes each a landmark.
LANDMARKS = {
    "SirenTheatre": dict(lot=(4, 5), kind="theatre"),
    "CarouselHouse": dict(lot=(3, 3), kind="carousel"),
    "LobstermensLodge": dict(lot=(3, 3), kind="lodge"),
    "TidewaterAquarium": dict(lot=(4, 3), kind="aquarium"),
    "ExhibitionHall": dict(lot=(6, 5), kind="hall"),
    # Gaudy nautical landmarks (Antigravity 2026-11-20): +4 coastal showpieces (5 -> 9)
    "KingCrabPalace": dict(lot=(5, 4), kind="crab"),
    "SacredCodExchange": dict(lot=(5, 4), kind="cod"),
    "SeaTurtlePavilion": dict(lot=(4, 4), kind="turtle"),
    "ClipperBowHall": dict(lot=(4, 5), kind="clipper"),
    "NautilusMarineGallery": dict(lot=(4, 3), kind="nautilus"),
    "WalrusBathhouse": dict(lot=(5, 4), kind="walrus"),
}
for _kv in EXCHANGE_ROW.values():
    _kv["palette"] = "exchange"
for _kv in DESIGNS.values():
    _kv["palette"] = "victorian"
for _d, _kv in CHATEAU_PALACES.items():
    BOARDWALK_PALACES[_d].update(_kv)
for _d, _kv in CHATEAU_HOTELS.items():
    GRAND_HOTELS[_d].update(_kv)
ZH_HH = {(1, 3): 6, (1, 4): 8, (1, 5): 9, (1, 6): 10, (2, 3): 10, (2, 4): 12, (2, 5): 14, (2, 6): 16}
HARBOUR_HILL = {
 "MansardRow": dict(roof="mansard", wall="BuffBrick", upper="bays", hood="cap", roof_mat="Slate", door="Green", storeys=4),
 "HillQuadDecker": dict(roof="flat", cornice="bracket", storeys=5, wall="Brick074", door="Black"),
 "BayTenement": dict(roof="flat", cornice="corbel", upper="bays", wall="BrownBrick", door="Oxblood", storeys=4),
 "GraniteBase": dict(roof="flat", cornice="corbel", base="granite", quoins=True, wall="Brick094", hood="pediment", storeys=5, door="GreyBlue"),
 "CorniceBlock": dict(roof="flat", cornice="bracket", hood="pediment", wall="BuffBrick", door="Green", storeys=4, quoins=True),
 "ShingleMansard": dict(roof="mansard", wall="ShingleGrey", upper="bays", roof_mat="SlateGreen", door="GreyBlue", storeys=4),
 "HarbourLeftCorner": dict(corner=True, roof="flat", cornice="bracket", wall="Brick074", hood="cap", door="Oxblood", storeys=5, lots=[(2,3),(2,4),(2,5),(2,6)]),
 # Round-out (Antigravity 2026-11-18): 1-wide LeftCorners + 2-wide mansard LeftCorner
 "HillBrickLeftCorner": dict(corner=True, roof="flat", cornice="corbel", base="granite", wall="Brick094", hood="cap", door="Green", storeys=4, lots=[(1,3),(1,4),(1,5),(1,6)]),
 "HillShingleLeftCorner": dict(corner=True, roof="flat", cornice="bracket", wall="ShingleGrey", hood="cap", door="GreyBlue", storeys=4, lots=[(1,3),(1,4),(1,5),(1,6)]),
 "HillMansardLeftCorner": dict(corner=True, roof="mansard", wall="BuffBrick", upper="bays", hood="pediment", roof_mat="SlateDark", door="Oxblood", storeys=4, lots=[(2,3),(2,4),(2,5),(2,6)]),
}
MOTOR_COURTS = {
 "UCourt": dict(layout="U", wall="ShingleGrey", office_wall="Clapboard", roof_mat="SlateDark", door="Green"),
 "LCourt": dict(layout="L", wall="ShingleSilver", office_wall="ClapSage", roof_mat="TinOxide", door="Oxblood"),
 "DoubleRow": dict(layout="R", wall="Clapboard", office_wall="ShingleGrey", roof_mat="SlateGreen", door="GreyBlue"),
 "GambrelCourt": dict(layout="R", roof="gambrel", wall="ShingleSilver", office_wall="Clapboard", roof_mat="SlateDark", door="Black"),
 "RubbleCourt": dict(layout="L", wall="Rubble", office_wall="ShingleGrey", base=None, roof_mat="SlateGreen", door="Oxblood"),
 "OfficeCourt": dict(layout="R", wall="ClapSage", office_wall="Rubble", roof_mat="TinOxide", door="GreyBlue"),
}
# Corner extensions share the original family's palette and all its rear specifications.
for family in ("CornerQueenAnne", "CornerStick", "CornerTriple"):
    DESIGNS[family + "RightCorner"] = dict(DESIGNS[family + "LeftCorner"], hand="R")

MAIN_STREET["CornerBrickShopRightCorner"] = dict(MAIN_STREET["CornerBrickShopLeftCorner"], hand="R", hh=3)
for hand, suffix in (("L", "LeftCorner"), ("R", "RightCorner")):
    for family, target, kind, households_, material, roof in (
        ("CornerMansardDouble", DESIGNS, "double", 4, "Clapboard", "SlateDark"),
        ("CornerTurretArcade", MAIN_STREET, "arcade", 5, "Brick085", "SlateGreen"),
        ("CornerMansardBlock", MAIN_STREET, "block", 6, "Brick074", "SlateDark"),
    ):
        target[family + suffix] = dict(corner=True, wide_corner=kind, hand=hand, hh=households_,
                                      lots=[(2, 3), (2, 4)], wall=material, roof_mat=roof)

for family, target, kind, hh, material, roof in (
    ("MansardDouble", DESIGNS, "double", 4, "Clapboard", "SlateDark"),
    ("TurretArcade", MAIN_STREET, "arcade", 5, "Brick085", "SlateGreen"),
    ("MansardBlock", MAIN_STREET, "block", 6, "Brick074", "SlateDark"),
):
    target[family] = dict(corner=False, wide_corner=kind, hand="L", hh=hh, lots=[(2, 3), (2, 4)],
                          wall=material, roof_mat=roof)

INN_HOUSEHOLDS = {(4, 4): 13, (3, 5): 12, (4, 5): 16, (4, 6): 20, (3, 4): 10, (5, 5): 24, (5, 6): 28}


def inn(roof, car, roof_mat, door, *, turret=True, cross=True, stone=True, hand="L", cupola=True, lofts=False):
    base = "StoneBase" if stone else None
    return dict(lots=list(INN_HOUSEHOLDS), palette="coastal_inn", storeys=3, roof=roof, turret=turret,
                cross=cross, base=base, hand=hand, wall="ShingleSilver", gable_mat="ShingleGrey", roof_mat=roof_mat,
                door=door, wing_mat="ShingleSilver", car_mat="ShingleGrey", car=car, cupola=cupola,
                lofts=lofts, car_base=base, flats=False)


COASTAL_INNS = {
    "SamosetInn": inn("gambrel", "gambrel", "SlateDark", "Oxblood", lofts=True),
    "BreakwaterInn": inn("gable", "cross", "SlateGreen", "Green", hand="R"),
    "AcadiaHouse": inn("gambrel", "gambrel", "Slate", "Oxblood", turret=False, cupola=False, lofts=True),
    "CamdenLodge": inn("gable", "gable", "SlateGreen", "Green", cross=False, lofts=True),
    "PenobscotHotel": inn("gambrel", "cross", "Slate", "GreyBlue", stone=False, hand="R"),
}

for inn_name, layout in {"SamosetInn": "quadrangle", "BreakwaterInn": "slip", "AcadiaHouse": "spine",
                         "CamdenLodge": "lodge", "PenobscotHotel": "offset"}.items():
    COASTAL_INNS[inn_name]["layout"] = layout

for inn_name in ("BreakwaterInn", "CamdenLodge"):
    COASTAL_INNS[inn_name + "LeftCorner"] = dict(
        COASTAL_INNS[inn_name], lots=[(3, 4), (4, 5)], corner=True, hand="L"
    )

# ---- Maritime Boom Trio (Antigravity 2026-11-19): 1910s-1930s Coastal Setback Towers (ZH2), Shipyard Bungalows (ZL2),
# and Halifax-inspired Hydrostone Garden Courts (ZR1). Strict coastal palette (rule 20: zero red/brown walls or roofs;
# reds/browns only on doors/shutters) and unique per-design footprints at every lot size (rule 21).
ZH2_HH = {(3, 4): 26, (3, 5): 32, (4, 4): 36, (4, 5): 46, (5, 5): 58}
BEACON_TOWERS = {
    "ClaridgeHouse": dict(base_n=5, mid_n=5, top_n=2, plan="U", depth_f=.50, court_f=.28, cap="hip", piers=True, arch=True,
                          wall="BuffBrick", base="Dressed", roof_mat="TinGreen", door="Iron",
                          lots=[(3, 4), (3, 5), (4, 4), (4, 5), (5, 5)]),
    "BeaconTower": dict(base_n=4, mid_n=6, top_n=3, plan="H", depth_f=.44, court_f=.20, cap="step", piers=True, arch=False,
                        wall="TrimWhite", base="Greystone", roof_mat="SlateDark", door="Iron",
                        lots=[(3, 4), (3, 5), (4, 4), (4, 5), (5, 5)]),
    "TraymoreArms": dict(base_n=5, mid_n=4, top_n=2, plan="T", depth_f=.48, court_f=.18, cap="dome", piers=True, arch=True,
                         wall="Render", base="Dressed", roof_mat="TinGreen", door="Iron",
                         lots=[(3, 4), (3, 5), (4, 4), (4, 5), (5, 5)]),
    "EastlandCourt": dict(base_n=6, mid_n=4, top_n=2, plan="U", depth_f=.38, court_f=.36, cap="pyramid", piers=False, arch=True,
                          wall="Cream", base="Greystone", roof_mat="SlateDark", door="Iron",
                          lots=[(3, 4), (3, 5), (4, 4), (4, 5), (5, 5)]),
    "CongressPlaza": dict(base_n=4, mid_n=5, top_n=3, plan="H", depth_f=.38, court_f=.27, cap="pyramid", piers=True, arch=False,
                          wall="BuffBrick", base="Greystone", roof_mat="TinGreen", door="Iron",
                          lots=[(3, 4), (3, 5), (4, 4), (4, 5), (5, 5)]),
    "CumberlandTerrace": dict(base_n=5, mid_n=5, top_n=2, plan="L_right", depth_f=.46, court_f=.40, cap="step", piers=False, arch=False,
                              wall="RevealStone", base="Dressed", roof_mat="SlateGreen", door="Iron",
                              lots=[(3, 4), (3, 5), (4, 4), (4, 5), (5, 5)]),
    "BeaconCornerLeftCorner": dict(base_n=5, mid_n=5, top_n=3, plan="L_left", depth_f=.46, court_f=.38, cap="hip", piers=True, arch=True,
                                   wall="BuffBrick", base="Dressed", roof_mat="TinGreen", door="Iron", corner=True,
                                   lots=[(3, 4), (3, 5), (4, 4), (4, 5), (5, 5)]),
    "HarbourDecoLeftCorner": dict(base_n=4, mid_n=6, top_n=2, plan="C_right", depth_f=.42, court_f=.31, cap="step", piers=True, arch=False,
                                  wall="TrimWhite", base="Greystone", roof_mat="SlateDark", door="Iron", corner=True,
                                  lots=[(3, 4), (3, 5), (4, 4), (4, 5), (5, 5)]),
    "MarinaTowerLeftCorner": dict(base_n=5, mid_n=4, top_n=2, plan="U", depth_f=.58, court_f=.24, cap="dome", piers=True, arch=True,
                                  wall="Render", base="Dressed", roof_mat="TinGreen", door="Iron", corner=True,
                                  lots=[(3, 4), (3, 5), (4, 4), (4, 5), (5, 5)]),
    # Parity expansion (Antigravity 2026-11-20): +3 mid + 1 LeftCorner + 3x5 corners (42 -> 65)
    "AcadiaTowers": dict(base_n=5, mid_n=6, top_n=2, plan="L_left", depth_f=.56, court_f=.30, cap="hip", piers=True, arch=True,
                         wall="Cream", base="Dressed", roof_mat="TinGreen", door="Iron",
                         lots=[(3, 4), (3, 5), (4, 4), (4, 5), (5, 5)]),
    "CascoArms": dict(base_n=4, mid_n=5, top_n=3, plan="C_right", depth_f=.50, court_f=.39, cap="dome", piers=False, arch=True,
                      wall="RevealStone", base="Greystone", roof_mat="SlateGreen", door="Iron",
                      lots=[(3, 4), (3, 5), (4, 4), (4, 5), (5, 5)]),
    "PenobscotHouse": dict(base_n=6, mid_n=4, top_n=2, plan="T", depth_f=.45, court_f=.21, cap="step", piers=True, arch=False,
                           wall="BuffBrick", base="Greystone", roof_mat="SlateDark", door="Iron",
                           lots=[(3, 4), (3, 5), (4, 4), (4, 5), (5, 5)]),
    "OceanViewLeftCorner": dict(base_n=5, mid_n=5, top_n=2, plan="H", depth_f=.52, court_f=.24, cap="pyramid", piers=True, arch=False,
                                wall="Cream", base="Dressed", roof_mat="TinGreen", door="Iron", corner=True,
                                lots=[(3, 4), (3, 5), (4, 4), (4, 5), (5, 5)]),
}
SHIPYARD_BUNGALOWS = {
    "ShipyardBungalow": dict(kind="craftsman", porch_side="L", porch_frac=.58, md_off=0.0, ell_side="L", ell_w=.48,
                             gar_align="full", cd_off=-.2, sun_w=.62,
                             wall="ShingleGrey", base="Rubble", roof_mat="SlateDark", door="Oxblood", gar="gable",
                             lots=[(2, 2), (2, 3), (2, 4), (3, 3), (3, 4)]),
    "DeeringFoursquare": dict(kind="foursquare", porch_side="full", md_off=.4, ell_side="R", ell_w=.50,
                              gar_align="R", gar_w=.76, cd_off=0.0, sun_w=.70,
                              wall="Clapboard", base="Greystone", roof_mat="SlateGreen", door="Green", gar="hip",
                              lots=[(2, 2), (2, 3), (2, 4), (3, 3), (3, 4)]),
    "AtlanticDutch": dict(kind="dutch", porch_side="none", md_off=.6, ell_side="L", ell_w=.54,
                          gar_align="L", gar_w=.76, cd_off=.2, sun_w=.88,
                          wall="ClapSage", base="Rubble", roof_mat="SlateDark", door="Black", gar="gable",
                          lots=[(2, 2), (2, 3), (2, 4), (3, 3), (3, 4)]),
    "KitteryGable": dict(kind="gable_front", porch_side="R", porch_frac=.54, md_off=-.4, ell_side="R", ell_w=.46,
                         gar_align="full", cd_off=.6, sun_w=.58,
                         wall="ShingleSilver", base="StoneBase", roof_mat="SlateDark", door="GreyBlue", gar="hip",
                         lots=[(2, 2), (2, 3), (2, 4), (3, 3), (3, 4)]),
    "BathCraftsman": dict(kind="craftsman", porch_side="L", porch_frac=.46, md_off=.8, ell_side="C", ell_w=.56,
                          gar_align="full", cd_off=-.4, sun_w=.54,
                          wall="Clapboard", base="Greystone", roof_mat="SlateGreen", door="Green", gar="hip",
                          lots=[(2, 2), (2, 3), (2, 4), (3, 3), (3, 4)]),
    "WoodfordsSquare": dict(kind="foursquare", porch_side="R", porch_frac=.60, md_off=1.0, ell_side="L", ell_w=.44,
                            gar_align="L", gar_w=.78, cd_off=-.2, sun_w=.50,
                            wall="ShingleSilver", base="Rubble", roof_mat="SlateDark", door="Oxblood", gar="gable",
                            lots=[(2, 2), (2, 3), (2, 4), (3, 3), (3, 4)]),
    "CornerBungalowLeftCorner": dict(kind="craftsman", porch_side="L", porch_frac=.52, md_off=-.2, ell_side="L", ell_w=.60,
                                     gar_align="full", cd_off=.2, sun_w=.74,
                                     wall="ShingleGrey", base="Rubble", roof_mat="SlateGreen", door="Oxblood", gar="gable", corner=True,
                                     lots=[(2, 2), (2, 3), (2, 4), (3, 3), (3, 4)]),
    "CornerFoursquareLeftCorner": dict(kind="foursquare", porch_side="full", md_off=0.0, ell_side="twin", ell_w=.48,
                                       gar_align="R", gar_w=.78, cd_off=.4, sun_w=.66,
                                       wall="Clapboard", base="Greystone", roof_mat="SlateDark", door="Green", gar="hip", corner=True,
                                       lots=[(2, 2), (2, 3), (2, 4), (3, 3), (3, 4)]),
    # Parity expansion (Antigravity 2026-11-20): +3 mid + 2 LeftCorners across all 5 lots (40 -> 65)
    "CapeCodCottage": dict(kind="capecod", porch_side="none", md_off=-.6, ell_side="R", ell_w=.54,
                           gar_align="R", gar_w=.82, cd_off=.4, sun_w=.64,
                           wall="Clapboard", base="Rubble", roof_mat="SlateDark", door="GreyBlue", gar="gable",
                           lots=[(2, 2), (2, 3), (2, 4), (3, 3), (3, 4)]),
    "SaltboxHouse": dict(kind="saltbox", porch_side="L", porch_frac=.44, md_off=.6, ell_side="R", ell_w=.44,
                         gar_align="L", gar_w=.80, cd_off=.4, sun_w=.76,
                         wall="ShingleGrey", base="Greystone", roof_mat="SlateGreen", door="Black", gar="hip",
                         lots=[(2, 2), (2, 3), (2, 4), (3, 3), (3, 4)]),
    "JerkinheadBungalow": dict(kind="jerkinhead", porch_side="R", porch_frac=.50, md_off=.6, ell_side="C", ell_w=.48,
                               gar_align="full", cd_off=.4, sun_w=.84,
                               wall="ClapSage", base="StoneBase", roof_mat="SlateDark", door="Oxblood", gar="gable",
                               lots=[(2, 2), (2, 3), (2, 4), (3, 3), (3, 4)]),
    "CornerDutchLeftCorner": dict(kind="dutch", porch_side="none", md_off=0.0, ell_side="R", ell_w=.58,
                                  gar_align="R", gar_w=.82, cd_off=-.4, sun_w=.72,
                                  wall="ShingleSilver", base="Rubble", roof_mat="SlateGreen", door="Green", gar="hip", corner=True,
                                  lots=[(2, 2), (2, 3), (2, 4), (3, 3), (3, 4)]),
    "CornerGableLeftCorner": dict(kind="gable_front", porch_side="L", porch_frac=.54, md_off=.6, ell_side="twin", ell_w=.44,
                                  gar_align="full", cd_off=-.2, sun_w=.60,
                                  wall="Clapboard", base="Greystone", roof_mat="SlateDark", door="Oxblood", gar="gable", corner=True,
                                  lots=[(2, 2), (2, 3), (2, 4), (3, 3), (3, 4)]),
}
ZR1_HH = {(2, 3): 18, (2, 4): 24, (3, 4): 30, (3, 5): 36, (4, 4): 38, (4, 5): 46}
HYDROSTONE_COURTS = {
    "HydrostoneRow": dict(storeys=3, plan="U_rear", depth_f=.44, court_f=.32, roof="gable", upper="Cream",
                          roof_mat="SlateDark", door="Green", dormers=True, lots=[(2, 3), (2, 4), (3, 4), (3, 5), (4, 4), (4, 5)]),
    "HalifaxCourt": dict(storeys=3, plan="U_front", depth_f=.25, court_f=.34, roof="hip", upper="Greystone",
                         roof_mat="Slate", door="Oxblood", dormers=False, lots=[(2, 3), (2, 4), (3, 4), (3, 5), (4, 4), (4, 5)]),
    "KayeTerrace": dict(storeys=4, plan="H", depth_f=.36, court_f=.22, roof="flat", upper="Dressed",
                        roof_mat="SlateDark", door="Black", dormers=False, lots=[(2, 3), (2, 4), (3, 4), (3, 5), (4, 4), (4, 5)]),
    "IslevilleFlats": dict(storeys=3, plan="U_front_L", depth_f=.33, court_f=.39, roof="gable", upper="ShingleSilver",
                           roof_mat="SlateGreen", door="Green", dormers=True, lots=[(2, 3), (2, 4), (3, 4), (3, 5), (4, 4), (4, 5)]),
    "RichmondCourt": dict(storeys=4, plan="U_rear", depth_f=.58, court_f=.22, roof="hip", upper="Cream",
                          roof_mat="SlateDark", door="GreyBlue", dormers=False, lots=[(2, 3), (2, 4), (3, 4), (3, 5), (4, 4), (4, 5)]),
    "FortNeedhamBlock": dict(storeys=3, plan="T", depth_f=.48, court_f=.19, roof="gable", upper="Greystone",
                             roof_mat="SlateGreen", door="Oxblood", dormers=True, lots=[(2, 3), (2, 4), (3, 4), (3, 5), (4, 4), (4, 5)]),
    "HydrostoneCornerLeftCorner": dict(storeys=3, plan="L_left", depth_f=.48, court_f=.36, roof="gable", upper="Cream",
                                       roof_mat="SlateDark", door="Green", dormers=True, corner=True, lots=[(2, 4), (3, 4), (3, 5), (4, 5)]),
    "HalifaxCornerLeftCorner": dict(storeys=4, plan="U_front", depth_f=.36, court_f=.28, roof="hip", upper="Greystone",
                                    roof_mat="Slate", door="Oxblood", dormers=False, corner=True, lots=[(2, 4), (3, 4), (3, 5), (4, 5)]),
    "KayeCornerLeftCorner": dict(storeys=4, plan="C_left", depth_f=.38, court_f=.36, roof="flat", upper="Dressed",
                                 roof_mat="SlateGreen", door="Black", dormers=False, corner=True, lots=[(2, 4), (3, 4), (3, 5), (4, 5)]),
    # Parity expansion (Antigravity 2026-11-20): +2 mid (6 lots) + 1 LeftCorner (4 lots) + 3x5/4x5 on existing 6 mid (36 -> 64)
    "AcadiaTerrace": dict(storeys=4, plan="C_mirror", depth_f=.44, court_f=.30, roof="gable", upper="Dressed",
                          roof_mat="Slate", door="Green", dormers=True, lots=[(2, 3), (2, 4), (3, 4), (3, 5), (4, 4), (4, 5)]),
    "ChebuctoCourt": dict(storeys=3, plan="L_right", depth_f=.56, court_f=.34, roof="hip", upper="ShingleSilver",
                          roof_mat="SlateDark", door="GreyBlue", dormers=False, lots=[(2, 3), (2, 4), (3, 4), (3, 5), (4, 4), (4, 5)]),
    "AcadiaCornerLeftCorner": dict(storeys=3, plan="U_rear", depth_f=.38, court_f=.36, roof="flat", upper="Cream",
                                   roof_mat="Slate", door="Oxblood", dormers=False, corner=True, lots=[(2, 4), (3, 4), (3, 5), (4, 5)]),
}

ZONES = {"ZL1": DESIGNS, "ZM1": MAIN_STREET, "ZP1": PRESTIGE, "ZP2": {**COTTAGE_FLATS, **COASTAL_INNS}, "ZP3": GRAND_HOTELS,
         "ZC1": BOARDWALK_SHOPS, "ZC2": BOARDWALK_PALACES, "ZI1": CANNERY_ROW, "ZO1": EXCHANGE_ROW, "ZS1": CIVIC, "ZS2": LANDMARKS,
         "ZH1": HARBOUR_HILL, "ZP4": MOTOR_COURTS,
         "ZH2": BEACON_TOWERS, "ZL2": SHIPYARD_BUNGALOWS, "ZR1": HYDROSTONE_COURTS}
MODULE = {"ZP1": "federal", "ZP2": "federal", "ZP3": "cottage", "ZC1": "shops", "ZC2": "boardwalk",
          "ZI1": "cannery", "ZM1": "mainst", "ZL1": "shorerows", "ZO1": "exchange", "ZS1": "civic", "ZS2": "landmarks",
          "ZH1": "harbourhill", "ZP4": "motorcourt",
          "ZH2": "deco_towers", "ZL2": "bungalows", "ZR1": "hydrostone"}   # else shore_row
SIZES = {"ZP1": [(w, d) for w in (2, 3) for d in (3, 4, 5, 6)], "ZP2": sorted(FLATS_HH), "ZP3": sorted(GRAND_HH),
         "ZC1": [(1, 2), (1, 3), (2, 2), (2, 3), (2, 4), (3, 3), (3, 4)], "ZC2": [(4, 4), (4, 5), (5, 5), (6, 6)],
         "ZI1": [(2, 4), (3, 4), (4, 4), (4, 6)], "ZO1": [(2, 3), (3, 3), (3, 4), (4, 4)],
         "ZH1": sorted(ZH_HH), "ZP4": [(3, 5), (4, 5), (4, 6)],
         "ZH2": sorted(ZH2_HH), "ZL2": [(2, 2), (2, 3), (2, 4), (3, 3), (3, 4)], "ZR1": sorted(ZR1_HH)}

# In-game colour variations (Toronto lesson): each set is (colour 0, colour 1, colour 2), sRGB multipliers on the
# base colour where the ControlMask is R / G / B. Colour 0 is unused (white). Colour 1 = the wall cladding, colour 2 =
# the trim. The game picks a set per building at random, so a row of one design comes out in different paints.
WHITE, CREAM, GREYWHITE = (1, 1, 1), (1, .97, .9), (.95, .95, .94)
PALETTES = {
    # weathered cedar shingle: silver, warm grey, young cedar, charcoal, cool grey, driftwood, dark weathered
    "shingle": [((1, 1, 1), WHITE), ((1, .96, .9), WHITE), ((.93, .84, .72), CREAM), ((.8, .8, .82), WHITE),
                ((.9, .94, 1), GREYWHITE), ((.98, .92, .84), CREAM), ((.86, .86, .84), WHITE), ((1, 1, 1), CREAM)],
    # painted clapboard (lifted to near-white in the atlas), all muted (the author: gray + white, no pastels): off-white,
    # cream, pale grey, grey sage, grey blue, straw, barn red, slate
    "clapboard": [((.97, .97, .96), WHITE), ((.98, .95, .88), WHITE), ((.86, .87, .88), WHITE), ((.82, .85, .79), CREAM),
                  ((.8, .83, .87), WHITE), ((.95, .91, .8), WHITE), ((.62, .41, .37), CREAM), ((.66, .69, .74), WHITE)],
    # shopfront paint (ZC1 false fronts, the author: stronger than the grey residential streets, still period colours):
    # mustard, barn red, bottle green, Prussian blue, terracotta, buff, teal, plum brown
    "shopfront": [((.93, .76, .42), WHITE), ((.66, .36, .31), CREAM), ((.5, .62, .48), CREAM), ((.5, .6, .74), WHITE),
                  ((.86, .58, .45), CREAM), ((.98, .88, .68), WHITE), ((.48, .66, .66), WHITE), ((.6, .45, .45), CREAM)],
    # sage clapboard: sage, grey sage, olive, stone, mint
    "sage": [((1, 1, 1), WHITE), ((.94, .97, 1), WHITE), ((1, .97, .86), CREAM), ((.9, .9, .9), WHITE),
             ((.96, 1, .94), GREYWHITE)],
    # brick: the brick itself is not tinted (no G mask); only the trim varies
    "brick": [((1, 1, 1), WHITE), ((1, 1, 1), CREAM), ((1, 1, 1), GREYWHITE)],
    # Federal harbour town (ZP1/ZP2, the author 2026-11-17): (barn, body, trim) = colour 0 on the BoardBatten barns and
    # woodsheds (muted barn red or white), colour 1 on the clapboard (white, cream, pale buff, pale grey-blue, pale grey)
    "federal": [((.52, .3, .26), (.96, .95, .92), WHITE), ((.95, .94, .9), (.97, .93, .82), WHITE),
                ((.52, .3, .26), (.9, .86, .74), WHITE), ((.52, .3, .26), (.78, .83, .86), WHITE),
                ((.95, .94, .9), (.86, .86, .85), WHITE), ((.5, .29, .25), (.97, .93, .82), CREAM),
                ((.95, .94, .9), (.9, .86, .74), CREAM), ((.52, .3, .26), (.86, .86, .85), GREYWHITE)],
    # Exchange Row (ZO1): stone and copper are not tinted; colour 2 tints the few TrimWhite faces (soffits, finials,
    # the dome band) to limestone, warm stone or grey granite, so nothing reads white
    "exchange": [(WHITE, WHITE, (.86, .83, .76)), (WHITE, WHITE, (.8, .78, .72)), (WHITE, WHITE, (.76, .76, .74)),
                 (WHITE, WHITE, (.84, .8, .7))],
    # painted ladies, historic district edition (the author 2026-11-17: "laffy taffy" -> the commission won the colour fight):
    # (accent, body, trim); greyed period colours, the accent shingles a shade off the body, trim cream / off-white /
    # spruce green / black, so a street reads as one coordinated row
    "victorian": [((.56, .6, .5), (.66, .69, .58), (.96, .93, .84)),     # sage, cream trim
                  ((.7, .67, .58), (.8, .76, .66), (.27, .34, .29)),     # putty, stone shingles, spruce trim
                  ((.62, .6, .56), (.72, .71, .67), (.94, .93, .89)),    # stone grey, off-white trim
                  ((.44, .44, .34), (.5, .5, .38), (.93, .9, .8)),       # olive drab, cream trim
                  ((.48, .52, .56), (.55, .6, .64), (.94, .94, .91)),    # slate blue-grey, off-white trim
                  ((.44, .28, .25), (.5, .31, .28), (.92, .88, .78)),    # oxblood, cream trim
                  ((.3, .36, .32), (.34, .41, .36), (.93, .9, .8)),      # deep spruce green, cream trim
                  ((.78, .72, .59), (.86, .8, .66), (.27, .34, .29)),    # buff, spruce trim
                  ((.58, .55, .5), (.66, .63, .58), (.21, .21, .2)),     # warm grey, black trim
                  ((.84, .8, .69), (.93, .9, .8), (.27, .34, .29)),      # cream, putty shingles, spruce trim
                  ((.52, .54, .48), (.6, .62, .55), (.94, .93, .89)),    # lichen grey-green, off-white trim
                  ((.48, .42, .37), (.55, .48, .42), (.92, .88, .78))],  # umber taupe, cream trim
}
PALETTE_OF = {"Clapboard": "clapboard", "ClapSage": "sage", "Brick074": "brick", "Brick054": "brick",
              "BuffBrick": "brick", "BrownBrick": "brick", "Brick085": "brick", "Brick094": "brick",
              "Greystone": "brick"}          # anything else (shingle) -> "shingle"
RANDOM = (2, 4, 5)                                                    # hue, saturation, value jitter in percent


def colour_sets(variant):
    pal = variant.get("palette") or PALETTE_OF.get(variant.get("wall", "Clapboard"), "shingle")
    return [[list(c[0]), list(c[1]), list(c[2])] if len(c) == 3 else [list(WHITE), list(c[0]), list(c[1])]
            for c in PALETTES[pal]]


# ---- Coastal scheme (the author 2026-11-17, OK'd in project chat): five families, one swatch list, per-zone sets ----------
# Blues & Navies, Whites & Creams, Driftwood & Sand, Muted Greens & Sage, Heritage Accents. Swatches are what the eye
# should see; the multiplier is swatch / atlas base (tiles only darken). Doors, shutters, roofs, brick and stone are
# fixed atlas paint and already sit in these families. Sheet: research\coastal\coastal_swatches.png. The palettes
# above stay for reference; coastal_sets() picks the zone's coastal palette (backup: lt_roster.pre_coastal.py).
SW = {"B1": (.68, .71, .73), "B2": (.56, .61, .65), "B3": (.42, .50, .56), "B4": (.20, .27, .35), "B5": (.18, .19, .31),
      "W1": (.95, .95, .93), "W2": (.93, .91, .86), "W3": (.91, .87, .76), "W4": (.86, .84, .79),
      "D1": (.84, .79, .69), "D2": (.74, .71, .65), "D3": (.62, .57, .51), "D4": (.66, .56, .44), "D5": (.43, .38, .32),
      "G1": (.72, .78, .73), "G2": (.62, .66, .56), "G3": (.52, .55, .51), "G4": (.55, .54, .39), "G5": (.27, .34, .29),
      "H1": (.58, .25, .22), "H2": (.48, .31, .22), "H3": (.20, .20, .20)}
# fog grey, watery slate, harbour blue, Atlantic navy, twilight indigo / crisp white, alabaster, soft cream, beadboard
# linen / dune sand, greige, driftwood, weathered tan, boardwalk brown / seafoam, sage, gray-green, marsh grass, deep
# spruce / buoy red, rust brown, charcoal
_BASE = {"clap": (.92, .92, .89), "trim": (.88, .88, .86), "accent": (.87, .86, .84), "batten": (.89, .89, .86)}
_SHINGLE = {"silver": (1, 1, 1), "driftwood": (1, .95, .88), "sand": (1, .97, .9), "taupe": (.96, .9, .84),
            "cool": (.92, .96, 1), "bluegrey": (.86, .92, 1), "brown": (.95, .86, .76)}


def _t(name, base, k=1.0):
    return tuple(round(min(1.0, s * k / b), 3) for s, b in zip(SW[name], _BASE[base]))


def _paint(sets):          # (body, trim); accent shingles a shade off the body
    return [(_t(b, "accent", .88), _t(b, "clap"), _t(t, "trim")) for b, t in sets]


def _shingle(sets):        # (shingle tint, trim)
    return [(WHITE, _SHINGLE[s], _t(t, "trim")) for s, t in sets]


def _trim(names):          # brick and stone: trim only
    return [(WHITE, WHITE, _t(t, "trim")) for t in names]


def _clap(names):
    return [(WHITE, _t(b, "clap"), _t("W1", "trim")) for b in names]


COASTAL = {
    "ZL1": _paint([("G2", "W3"), ("G3", "W1"), ("G4", "W3"), ("G5", "W3"), ("G1", "W1"), ("B2", "W1"), ("B3", "W2"),
                   ("B4", "W2"), ("D2", "G5"), ("D3", "H3"), ("W3", "B4"), ("H1", "W3")]),
    "FED": [(_t(r, "batten"), _t(b, "clap"), _t(t, "trim")) for r, b, t in
            [("H1", "W1", "W1"), ("W1", "W2", "W1"), ("H1", "W3", "W1"), ("H1", "B1", "W1"), ("D3", "W4", "W1"),
             ("H1", "D1", "W2"), ("W1", "G1", "W1"), ("D3", "W2", "W3")]],
    "ZP3_sh": _shingle([("silver", "W1"), ("driftwood", "W1"), ("sand", "W3"), ("taupe", "W2"), ("driftwood", "G5"),
                        ("silver", "W3")]),
    "ZP3_clap": _clap(["D1", "D2", "W2", "W3"]),
    "ZC2_sh": _shingle([("cool", "W1"), ("bluegrey", "W1"), ("silver", "W1"), ("bluegrey", "W2"), ("cool", "B4"),
                        ("silver", "B3")]),
    "ZC2_clap": _clap(["B1", "B2", "W1", "G1"]),
    "ZC1": _paint([("H1", "W3"), ("B4", "W2"), ("G5", "W3"), ("B3", "W1"), ("D4", "W2"), ("G4", "W3"), ("H2", "W3"),
                   ("D1", "B4")]),
    "ZC1_brick": _trim(["W3", "H3", "B4", "G5"]),
    "ZM1": _trim(["W3", "H3", "B4", "G5", "W2", "D2"]),
    "ZI1_brick": _trim(["H3", "H2", "D4", "W4"]),
    "ZI1_sh": _shingle([("brown", "W4"), ("driftwood", "H3"), ("silver", "H2")]),
    "ZO1": _trim(["W2", "D2", "D1", "B1"]),
    "ZH1": _trim(["W3", "H3", "B4", "G5", "W2", "D2"]),
    "ZH1_sh": _shingle([("silver", "W1"), ("driftwood", "H3"), ("bluegrey", "W2")]),
    "ZP4": _shingle([("silver", "W1"), ("driftwood", "H3"), ("bluegrey", "W2")]),
    # civic (ZS1): fieldstone is fixed paint; the shingle storeys weather silver, driftwood or taupe, trim white/cream
    # (the author 2026-11-17: silver read too close to the fieldstone) darker weathered shingle: storm grey, dark driftwood,
    # umber, slate blue-grey, dark taupe
    "ZS1": [(WHITE, s, _t(t, "trim")) for s, t in [((.66, .66, .68), "W1"), ((.66, .6, .52), "W2"), ((.56, .5, .44), "W1"),
                                                   ((.6, .64, .7), "W3"), ((.64, .58, .52), "W2")]],
    # landmarks (ZS2): the coastal sheet's Landmarks row, one list per building
    "ZS2_theatre": _trim(["W3", "W1"]),
    "ZS2_carousel": _paint([("B5", "W3"), ("B4", "W1")]),
    "ZS2_lodge": _paint([("B4", "W3"), ("B5", "W3")]),
    "ZS2_aquarium": _trim(["W3", "W1"]),
    "ZS2_hall": _trim(["W3", "W1"]),
    "ZS2_crab": _trim(["W3", "W1"]),
    "ZS2_cod": _trim(["W3", "W1"]),
    "ZS2_turtle": _trim(["W3", "W1"]),
    "ZS2_clipper": _trim(["W3", "W1"]),
    "ZS2_nautilus": _trim(["W3", "W1"]),
    "ZS2_walrus": _trim(["W3", "W1"]),
    # Maritime Boom Trio (Antigravity 2026-11-19): strict coastal palette (zero reds/browns on walls or roofs)
    # ZH2 Beacon Towers: buff/sand/cream/greige stone, plus muted blue-grey & sage painted masonry on TrimWhite towers
    "ZH2": _trim(["W2", "D1", "D2", "W4"]),
    "ZH2_paint": _trim(["B1", "B2", "G1", "G2", "D2", "W4"]),
    # ZL2 Shipyard Bungalows: coastal Craftsman shingles & clapboard (blues, driftwood, sand, sage, creams)
    "ZL2_sh": _shingle([("silver", "W2"), ("driftwood", "W2"), ("sand", "W3"), ("cool", "W1"), ("bluegrey", "W1")]),
    "ZL2_clap": _paint([("B1", "W1"), ("B2", "W2"), ("G1", "W1"), ("G2", "W2"), ("G3", "W2"), ("D1", "W2"), ("D2", "W1"), ("W4", "G5")]),
    # ZR1 Hydrostone Courts: crushed-stone base + muted coastal trim/shingle
    "ZR1": _trim(["W2", "W3", "W4", "G5", "B2"]),
    "ZR1_sh": _shingle([("silver", "W2"), ("driftwood", "W3"), ("sand", "W2"), ("cool", "W1")]),
}


def coastal_sets(zone, variant):
    wall = variant.get("wall", "Clapboard")
    if zone == "ZL1" and variant.get("wide_corner") == "double" and not variant.get("corner", True):
        # Use the coastal green, blue, driftwood and cream clapboard variations for this interior double.
        return [[list(c) for c in paint] for paint in COASTAL["ZL1"][:9] + COASTAL["ZL1"][10:11]]
    if zone == "ZL1": key = "ZL1"
    elif zone == "ZP2" and variant.get("palette") == "coastal_inn": key = "ZP3_sh"
    elif zone in ("ZP1", "ZP2"): key = "FED"
    elif zone in ("ZP3", "ZC2"):          # ClapSage is already dark, so it takes the gentle shingle tints
        key = zone + ("_clap" if wall == "Clapboard" else "_sh")
    elif zone == "ZC1": key = "ZC1" if variant.get("palette") == "shopfront" else "ZC1_brick"
    elif zone == "ZI1": key = "ZI1_brick" if PALETTE_OF.get(wall) == "brick" else "ZI1_sh"
    elif zone == "ZS2": key = "ZS2_" + variant["kind"]
    elif zone == "ZH1": key = "ZH1_sh" if wall.startswith("Shingle") else "ZH1"
    elif zone == "ZH2": key = "ZH2_paint" if wall == "TrimWhite" else "ZH2"
    elif zone == "ZL2": key = "ZL2_clap" if wall == "Clapboard" else "ZL2_sh"
    elif zone == "ZR1": key = "ZR1_sh" if variant.get("upper", "").startswith("Shingle") else "ZR1"
    else: key = zone
    return [[list(c) for c in s] for s in COASTAL[key]]


TEXT = '''"""Lobstertown {design}, lot {w}x{d}. Built from lt_designs/{module}.py."""
from lt_designs.{module} import build as design

ZONE = "{zone}"
HOUSEHOLDS = {hh}
PARTY_WALLS = {party}
{extra}

def build(lod):
    design(lod, {size}**{variant!r})
'''


def households(v):
    if "hh" in v:                                   # Shore Rows (shorerows.py) states its households
        return v["hh"]
    if "front" not in v:                            # a prestige cottage: one family
        return 1
    if v["front"] == "shop":                         # the shop is the zone's commercial part; flats above it
        return 3 if v.get("storeys") == 4 else 2
    if v["front"] == "quad":
        return 4
    return 3 if (v["front"] in ("double", "triple", "baytriple") or v.get("storeys") == 4 or v.get("corner")) else 2


def main():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent / "source"))
    from lt_designs.courtplan import plan
    out = Path(__file__).resolve().parent / "scripts"
    names, only = [], sys.argv[1:]
    for zone, designs in ZONES.items():
      for design, variant in designs.items():
        for w, d in variant.get("lots") or ([variant["lot"]] if "lot" in variant else SIZES.get(zone, [(1, d) for d in range(2, 7)])):
            name = f"NA_LT{design}_L1_{w}x{d}"
            hh = INN_HOUSEHOLDS[(w, d)] if design in COASTAL_INNS else FLATS_HH[(w, d)] if zone == "ZP2" else GRAND_HH[(w, d)] if zone == "ZP3" else \
                ZH_HH[(w, d)] if zone == "ZH1" else ZH2_HH[(w, d)] if zone == "ZH2" else ZR1_HH[(w, d)] if zone == "ZR1" else \
                1 if zone == "ZL2" else plan(variant["layout"], w, d)["hh"] if zone == "ZP4" else \
                0 if zone in ("ZC1", "ZC2", "ZI1", "ZO1", "ZS1", "ZS2") else households(variant)         # shops, industry: no flats
            party = () if zone in ("ZP1", "ZP2", "ZP3", "ZS1", "ZS2", "ZP4", "ZH2", "ZL2", "ZR1") else ("right",) if variant.get("corner") else ("left", "right")
            if variant.get("corner") and variant.get("hand") == "R":
                party = ("left",)
            module = MODULE.get(zone, "shore_row")
            size = f"W={w}, D={d}, " if module in ("cottage", "federal", "boardwalk", "cannery", "shops", "exchange", "civic", "landmarks", "harbourhill", "motorcourt", "deco_towers", "bungalows", "hydrostone") else f"D={d}, "
            params = variant
            if design in COASTAL_INNS:
                module = "coastal_inn"
                params = {k: v for k, v in variant.items() if k not in ("lots", "palette")}
                params.update(lites="1" if w == 5 or d == 6 else "6")
            (out / f"{name}.py").write_text(TEXT.format(design=design, w=w, d=d, zone=zone, hh=hh, variant=params,
                                                        party=party, module=module, size=size,
                                                        extra=f'PRODUCT = "{PRODUCT[design]}"\n' if zone == "ZI1" else ""),
                                           encoding="utf-8")
            if not only or zone in only:
                names.append(name)
    import json
    (out.parent / "colour_variations.json").write_text(json.dumps(
        {"random": list(RANDOM), "designs": {f"NA_LT{d}": coastal_sets(zk, v) for zk, z in ZONES.items() for d, v in z.items()}}, indent=1),
        encoding="utf-8")
    print(",".join(names))


if __name__ == "__main__":
    main()
