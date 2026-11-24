"""Lobstertown SeamensSavings, lot 4x4. Built from lt_designs/exchange.py."""
from lt_designs.exchange import build as design

ZONE = "ZO1"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=4, D=4, **{'storeys': 3, 'ground': 'arch', 'rust': True, 'order': 'columns', 'crown': 'pediment', 'quoins': True, 'hood': 'cap', 'back': 'hall', 'palette': 'exchange'})
