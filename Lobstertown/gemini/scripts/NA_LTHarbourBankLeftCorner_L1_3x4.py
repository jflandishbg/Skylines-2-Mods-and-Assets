"""Lobstertown HarbourBankLeftCorner, lot 3x4. Built from lt_designs/exchange.py."""
from lt_designs.exchange import build as design

ZONE = "ZO1"
HOUSEHOLDS = 0
PARTY_WALLS = ('right',)


def build(lod):
    design(lod, W=3, D=4, **{'storeys': 3, 'ground': 'arch', 'rust': True, 'order': 'columns', 'hood': 'cap', 'crown': 'dome', 'back': 'hall', 'corner': True, 'palette': 'exchange'})
