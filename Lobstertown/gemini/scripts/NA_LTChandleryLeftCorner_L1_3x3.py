"""Lobstertown ChandleryLeftCorner, lot 3x3. Built from lt_designs/shops.py."""
from lt_designs.shops import build as design

ZONE = "ZC1"
HOUSEHOLDS = 0
PARTY_WALLS = ('right',)


def build(lod):
    design(lod, W=3, D=3, **{'kind': 'brick', 'storeys': 3, 'ground': 'granite', 'cornice': 'bracket', 'back': 'store', 'wall': 'Brick074', 'door': 'Green', 'lites': '2', 'corner': True})
