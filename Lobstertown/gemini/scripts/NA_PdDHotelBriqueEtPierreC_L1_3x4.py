"""Hôtel Brique et Pierre, variant C: dark brown-red brick, grey ashlar ground floor, blue-grey slate,
green tin deck, black door."""
from nf_designs.hotel_brique_et_pierre import build as design

ZONE = "Z1B"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, brick="Brick054", deck="TinGreen", steep="Slate", door="Black")
