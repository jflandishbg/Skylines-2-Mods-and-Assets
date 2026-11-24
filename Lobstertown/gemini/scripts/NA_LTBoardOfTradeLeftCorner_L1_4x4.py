"""Lobstertown BoardOfTradeLeftCorner, lot 4x4. Built from lt_designs/exchange.py."""
from lt_designs.exchange import build as design

ZONE = "ZO1"
HOUSEHOLDS = 0
PARTY_WALLS = ('right',)


def build(lod):
    design(lod, W=4, D=4, **{'storeys': 4, 'ground': 'square', 'order': 'pilasters', 'hood': 'cap', 'roof': 'mansard', 'back': 'full', 'corner': True, 'palette': 'exchange'})
