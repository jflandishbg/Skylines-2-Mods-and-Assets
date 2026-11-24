"""Lobstertown RubbleCourt, lot 4x6. Built from lt_designs/motorcourt.py."""
from lt_designs.motorcourt import build as design

ZONE = "ZP4"
HOUSEHOLDS = 9
PARTY_WALLS = ()


def build(lod):
    design(lod, W=4, D=6, **{'layout': 'L', 'wall': 'Rubble', 'office_wall': 'ShingleGrey', 'base': None, 'roof_mat': 'SlateGreen', 'door': 'Oxblood'})
