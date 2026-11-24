"""Lobstertown HarbourLeftCorner, lot 2x4. Built from lt_designs/harbourhill.py."""
from lt_designs.harbourhill import build as design

ZONE = "ZH1"
HOUSEHOLDS = 12
PARTY_WALLS = ('right',)


def build(lod):
    design(lod, W=2, D=4, **{'corner': True, 'roof': 'flat', 'cornice': 'bracket', 'wall': 'Brick074', 'hood': 'cap', 'door': 'Oxblood', 'storeys': 5, 'lots': [(2, 3), (2, 4), (2, 5), (2, 6)]})
