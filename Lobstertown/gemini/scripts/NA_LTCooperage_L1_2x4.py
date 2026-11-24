"""Lobstertown Cooperage, lot 2x4. Built from lt_designs/cannery.py."""
from lt_designs.cannery import build as design

ZONE = "ZI1"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')
PRODUCT = "Furniture"


def build(lod):
    design(lod, W=2, D=4, **{'masonry': True, 'storeys': 2, 'roof': 'front', 'roofs': 'mg', 'stack': True, 'arch': False, 'wall': 'BuffBrick', 'base': 'Rubble', 'roof_mat': 'Slate', 'door': 'Black', 'sign': 'Cooperage'})
