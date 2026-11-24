"""Lobstertown TintypeStudio, lot 2x3. Built from lt_designs/shops.py."""
from lt_designs.shops import build as design

ZONE = "ZC1"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=2, D=3, **{'kind': 'brick', 'storeys': 3, 'ground': 'granite', 'cornice': 'bracket', 'skylight': True, 'wall': 'Brick094', 'door': 'Black', 'sign': 'TintypeStudio', 'sign_side': 'l'})
