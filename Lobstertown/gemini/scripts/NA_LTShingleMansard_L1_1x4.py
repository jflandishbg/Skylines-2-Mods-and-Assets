"""Lobstertown ShingleMansard, lot 1x4. Built from lt_designs/harbourhill.py."""
from lt_designs.harbourhill import build as design

ZONE = "ZH1"
HOUSEHOLDS = 8
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=1, D=4, **{'roof': 'mansard', 'wall': 'ShingleGrey', 'upper': 'bays', 'roof_mat': 'SlateGreen', 'door': 'GreyBlue', 'storeys': 4})
