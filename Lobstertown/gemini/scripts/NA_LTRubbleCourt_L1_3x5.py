"""Lobstertown RubbleCourt, lot 3x5. Built from lt_designs/motorcourt.py."""
from lt_designs.motorcourt import build as design

ZONE = "ZP4"
HOUSEHOLDS = 6
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=5, **{'layout': 'L', 'wall': 'Rubble', 'office_wall': 'ShingleGrey', 'base': None, 'roof_mat': 'SlateGreen', 'door': 'Oxblood'})
