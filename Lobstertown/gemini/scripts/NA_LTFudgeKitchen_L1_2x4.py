"""Lobstertown FudgeKitchen, lot 2x4. Built from lt_designs/shops.py."""
from lt_designs.shops import build as design

ZONE = "ZC1"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=2, D=4, **{'kind': 'brick', 'storeys': 2, 'ground': 'granite', 'cornice': 'corbel', 'back': 'store', 'wall': 'BuffBrick', 'door': 'Green', 'sign': 'FudgeKitchen'})
