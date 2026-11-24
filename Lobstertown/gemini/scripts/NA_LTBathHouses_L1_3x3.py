"""Lobstertown BathHouses, lot 3x3. Built from lt_designs/shops.py."""
from lt_designs.shops import build as design

ZONE = "ZC1"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=3, D=3, **{'kind': 'brick', 'storeys': 3, 'ground': 'iron', 'cornice': 'corbel', 'pediment': True, 'back': 'store', 'wall': 'Brick054', 'door': 'Oxblood', 'lites': '6', 'sign': 'BathHouses'})
