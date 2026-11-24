"""Lobstertown TelegraphBlockLeftCorner, lot 3x4. Built from lt_designs/exchange.py."""
from lt_designs.exchange import build as design

ZONE = "ZO1"
HOUSEHOLDS = 0
PARTY_WALLS = ('right',)


def build(lod):
    design(lod, W=3, D=4, **{'storeys': 4, 'ground': 'square', 'order': 'pilasters', 'hood': 'pediment', 'crown': 'tower', 'back': 'block', 'back_mat': 'BuffBrick', 'corner': True, 'palette': 'exchange'})
