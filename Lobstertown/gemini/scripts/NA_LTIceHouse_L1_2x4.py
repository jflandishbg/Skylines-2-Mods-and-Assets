"""Lobstertown IceHouse, lot 2x4. Built from lt_designs/cannery.py."""
from lt_designs.cannery import build as design

ZONE = "ZI1"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')
PRODUCT = "Food"


def build(lod):
    design(lod, W=2, D=4, **{'masonry': True, 'storeys': 3, 'roof': 'mansard', 'tower': 'right', 'back': 'store', 'arch': False, 'wall': 'Brick054', 'base': 'Dressed', 'roof_mat': 'Slate', 'door': 'Green', 'sign': 'HarborIce'})
