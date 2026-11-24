"""Lobstertown BookBlock, lot 1x4. Built from lt_designs/mainst.py."""
from lt_designs.mainst import build as design

ZONE = "ZM1"
HOUSEHOLDS = 3
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=4, **{'front': 'shop', 'storeys': 4, 'ground': 'iron', 'roof': 'flat', 'cornice': 'bracket', 'pediment': True, 'upper': 'oriel', 'oriel_mat': 'Cream', 'back': (1,), 'wall': 'Brick054', 'door': 'Black', 'lites': '2', 'sign': 'TidewaterBooks', 'sign_side': 'l'})
