"""Lobstertown BayTenement, lot 2x6. Built from lt_designs/harbourhill.py."""
from lt_designs.harbourhill import build as design

ZONE = "ZH1"
HOUSEHOLDS = 16
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=2, D=6, **{'roof': 'flat', 'cornice': 'corbel', 'upper': 'bays', 'wall': 'BrownBrick', 'door': 'Oxblood', 'storeys': 4})
