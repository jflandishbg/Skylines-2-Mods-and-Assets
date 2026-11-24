"""Lobstertown ShingleQuad, lot 1x4. Built from lt_designs/shore_row.py."""
from lt_designs.shore_row import build as design

ZONE = "ZL1"
HOUSEHOLDS = 4
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=4, **{'storeys': 4, 'roof': 'flat', 'front': 'quad', 'decks': True, 'wall': 'ShingleGrey', 'roof_mat': 'SlateDark', 'door': 'Oxblood', 'lites': '6', 'back_mat': 'Clapboard'})
