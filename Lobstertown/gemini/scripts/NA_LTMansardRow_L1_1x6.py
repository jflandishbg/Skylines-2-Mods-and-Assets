"""Lobstertown MansardRow, lot 1x6. Built from lt_designs/harbourhill.py."""
from lt_designs.harbourhill import build as design

ZONE = "ZH1"
HOUSEHOLDS = 10
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=1, D=6, **{'roof': 'mansard', 'wall': 'BuffBrick', 'upper': 'bays', 'hood': 'cap', 'roof_mat': 'Slate', 'door': 'Green', 'storeys': 4})
