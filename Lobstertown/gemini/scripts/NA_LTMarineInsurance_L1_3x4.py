"""Lobstertown MarineInsurance, lot 3x4. Built from lt_designs/exchange.py."""
from lt_designs.exchange import build as design

ZONE = "ZO1"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=3, D=4, **{'storeys': 4, 'ground': 'square', 'hood': 'cap', 'attic': True, 'back': 'court', 'back_mat': 'BuffBrick', 'palette': 'exchange'})
