"""Lobstertown MerchantsExchange, lot 3x3. Built from lt_designs/exchange.py."""
from lt_designs.exchange import build as design

ZONE = "ZO1"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=3, D=3, **{'storeys': 4, 'ground': 'square', 'order': 'pilasters', 'hood': 'cap', 'roof': 'mansard', 'back': 'full', 'palette': 'exchange'})
