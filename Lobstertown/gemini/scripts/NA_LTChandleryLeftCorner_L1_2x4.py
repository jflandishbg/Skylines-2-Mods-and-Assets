"""Lobstertown ChandleryLeftCorner, lot 2x4. Built from lt_designs/shops.py."""
from lt_designs.shops import build as design

ZONE = "ZC1"
HOUSEHOLDS = 0
PARTY_WALLS = ('right',)


def build(lod):
    design(lod, W=2, D=4, **{'kind': 'brick', 'storeys': 3, 'ground': 'granite', 'cornice': 'bracket', 'back': 'store', 'wall': 'Brick074', 'door': 'Green', 'lites': '2', 'corner': True})
