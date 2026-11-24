"""Lobstertown CanneryLeftCorner, lot 4x4. Built from lt_designs/cannery.py."""
from lt_designs.cannery import build as design

ZONE = "ZI1"
HOUSEHOLDS = 0
PARTY_WALLS = ('right',)
PRODUCT = "Food"


def build(lod):
    design(lod, W=4, D=4, **{'masonry': True, 'storeys': 2, 'roof': 'side', 'stack': True, 'arch': True, 'wall': 'Brick085', 'base': 'Greystone', 'roof_mat': 'Slate', 'door': 'Oxblood', 'corner': True, 'dock': 1.0})
