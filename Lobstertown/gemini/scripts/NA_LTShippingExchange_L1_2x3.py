"""Lobstertown ShippingExchange, lot 2x3. Built from lt_designs/exchange.py."""
from lt_designs.exchange import build as design

ZONE = "ZO1"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=2, D=3, **{'storeys': 4, 'ground': 'arch', 'rust': True, 'order': 'pilasters', 'hood': 'pediment', 'crown': 'dome', 'back': 'hall', 'main_d': 13.2, 'palette': 'exchange'})
