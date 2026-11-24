"""Lobstertown CustomsBrokerageLeftCorner, lot 2x3. Built from lt_designs/exchange.py."""
from lt_designs.exchange import build as design

ZONE = "ZO1"
HOUSEHOLDS = 0
PARTY_WALLS = ('right',)


def build(lod):
    design(lod, W=2, D=3, **{'storeys': 4, 'ground': 'arch', 'rust': True, 'order': 'columns', 'attic': True, 'crown': 'pediment', 'back': 'court', 'back_mat': 'BuffBrick', 'corner': True, 'main_d': 12.8, 'court_w': 4.6, 'palette': 'exchange'})
