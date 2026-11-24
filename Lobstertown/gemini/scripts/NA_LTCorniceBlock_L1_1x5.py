"""Lobstertown CorniceBlock, lot 1x5. Built from lt_designs/harbourhill.py."""
from lt_designs.harbourhill import build as design

ZONE = "ZH1"
HOUSEHOLDS = 9
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=1, D=5, **{'roof': 'flat', 'cornice': 'bracket', 'hood': 'pediment', 'wall': 'BuffBrick', 'door': 'Green', 'storeys': 4, 'quoins': True})
