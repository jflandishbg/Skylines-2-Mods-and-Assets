"""Lobstertown HillShingleLeftCorner, lot 1x5. Built from lt_designs/harbourhill.py."""
from lt_designs.harbourhill import build as design

ZONE = "ZH1"
HOUSEHOLDS = 9
PARTY_WALLS = ('right',)


def build(lod):
    design(lod, W=1, D=5, **{'corner': True, 'roof': 'flat', 'cornice': 'bracket', 'wall': 'ShingleGrey', 'hood': 'cap', 'door': 'GreyBlue', 'storeys': 4, 'lots': [(1, 3), (1, 4), (1, 5), (1, 6)]})
