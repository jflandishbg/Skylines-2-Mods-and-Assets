"""Lobstertown CorniceBlock, lot 2x4. Built from lt_designs/harbourhill.py."""
from lt_designs.harbourhill import build as design

ZONE = "ZH1"
HOUSEHOLDS = 12
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=2, D=4, **{'roof': 'flat', 'cornice': 'bracket', 'hood': 'pediment', 'wall': 'BuffBrick', 'door': 'Green', 'storeys': 4, 'quoins': True})
