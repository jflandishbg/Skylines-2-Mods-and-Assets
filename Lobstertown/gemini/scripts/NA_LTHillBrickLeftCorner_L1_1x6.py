"""Lobstertown HillBrickLeftCorner, lot 1x6. Built from lt_designs/harbourhill.py."""
from lt_designs.harbourhill import build as design

ZONE = "ZH1"
HOUSEHOLDS = 10
PARTY_WALLS = ('right',)


def build(lod):
    design(lod, W=1, D=6, **{'corner': True, 'roof': 'flat', 'cornice': 'corbel', 'base': 'granite', 'wall': 'Brick094', 'hood': 'cap', 'door': 'Green', 'storeys': 4, 'lots': [(1, 3), (1, 4), (1, 5), (1, 6)]})
