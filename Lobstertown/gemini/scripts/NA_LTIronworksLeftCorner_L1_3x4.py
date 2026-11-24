"""Lobstertown IronworksLeftCorner, lot 3x4. Built from lt_designs/cannery.py."""
from lt_designs.cannery import build as design

ZONE = "ZI1"
HOUSEHOLDS = 0
PARTY_WALLS = ('right',)
PRODUCT = "Machinery"


def build(lod):
    design(lod, W=3, D=4, **{'masonry': True, 'storeys': 3, 'roof': 'front', 'roofs': 'm', 'stack': True, 'arch': True, 'wall': 'BuffBrick', 'base': 'Dressed', 'roof_mat': 'SlateBrown', 'door': 'Black', 'corner': True, 'dock': 1.0})
