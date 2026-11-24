"""Hôtel Brique et Pierre, variant B: light red brick, cream limestone ground floor and frontispiece,
green-slate deck, oxblood door."""
from nf_designs.hotel_brique_et_pierre import build as design

ZONE = "Z1B"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, brick="Brick094", ground="Dressed", deck="SlateGreen", door="Oxblood")
