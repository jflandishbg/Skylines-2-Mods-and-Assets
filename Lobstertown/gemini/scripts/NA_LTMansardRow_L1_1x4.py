"""Lobstertown MansardRow, lot 1x4. Built from lt_designs/harbourhill.py."""
from lt_designs.harbourhill import build as design

ZONE = "ZH1"
HOUSEHOLDS = 8
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=1, D=4, **{'roof': 'mansard', 'wall': 'BuffBrick', 'upper': 'bays', 'hood': 'cap', 'roof_mat': 'Slate', 'door': 'Green', 'storeys': 4})
