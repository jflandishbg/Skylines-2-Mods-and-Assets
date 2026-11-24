"""Lobstertown TintypeStudio, lot 1x2. Built from lt_designs/shops.py."""
from lt_designs.shops import build as design

ZONE = "ZC1"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=1, D=2, **{'kind': 'brick', 'storeys': 3, 'ground': 'granite', 'cornice': 'bracket', 'skylight': True, 'wall': 'Brick094', 'door': 'Black', 'sign': 'TintypeStudio', 'sign_side': 'l'})
