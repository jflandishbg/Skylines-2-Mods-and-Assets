"""Lobstertown DoubleRow, lot 4x6. Built from lt_designs/motorcourt.py."""
from lt_designs.motorcourt import build as design

ZONE = "ZP4"
HOUSEHOLDS = 10
PARTY_WALLS = ()


def build(lod):
    design(lod, W=4, D=6, **{'layout': 'R', 'wall': 'Clapboard', 'office_wall': 'ShingleGrey', 'roof_mat': 'SlateGreen', 'door': 'GreyBlue'})
