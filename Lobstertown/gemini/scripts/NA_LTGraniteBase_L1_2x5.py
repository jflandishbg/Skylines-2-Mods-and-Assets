"""Lobstertown GraniteBase, lot 2x5. Built from lt_designs/harbourhill.py."""
from lt_designs.harbourhill import build as design

ZONE = "ZH1"
HOUSEHOLDS = 14
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=2, D=5, **{'roof': 'flat', 'cornice': 'corbel', 'base': 'granite', 'quoins': True, 'wall': 'Brick094', 'hood': 'pediment', 'storeys': 5, 'door': 'GreyBlue'})
