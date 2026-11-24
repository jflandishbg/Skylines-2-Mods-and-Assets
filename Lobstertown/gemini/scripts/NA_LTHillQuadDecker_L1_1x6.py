"""Lobstertown HillQuadDecker, lot 1x6. Built from lt_designs/harbourhill.py."""
from lt_designs.harbourhill import build as design

ZONE = "ZH1"
HOUSEHOLDS = 10
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=1, D=6, **{'roof': 'flat', 'cornice': 'bracket', 'storeys': 5, 'wall': 'Brick074', 'door': 'Black'})
