"""Lobstertown ShingleMansard, lot 2x6. Built from lt_designs/harbourhill.py."""
from lt_designs.harbourhill import build as design

ZONE = "ZH1"
HOUSEHOLDS = 16
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=2, D=6, **{'roof': 'mansard', 'wall': 'ShingleGrey', 'upper': 'bays', 'roof_mat': 'SlateGreen', 'door': 'GreyBlue', 'storeys': 4})
