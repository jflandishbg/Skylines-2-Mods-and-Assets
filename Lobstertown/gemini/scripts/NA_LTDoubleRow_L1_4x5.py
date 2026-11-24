"""Lobstertown DoubleRow, lot 4x5. Built from lt_designs/motorcourt.py."""
from lt_designs.motorcourt import build as design

ZONE = "ZP4"
HOUSEHOLDS = 8
PARTY_WALLS = ()


def build(lod):
    design(lod, W=4, D=5, **{'layout': 'R', 'wall': 'Clapboard', 'office_wall': 'ShingleGrey', 'roof_mat': 'SlateGreen', 'door': 'GreyBlue'})
