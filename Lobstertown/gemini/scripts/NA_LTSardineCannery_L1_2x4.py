"""Lobstertown SardineCannery, lot 2x4. Built from lt_designs/cannery.py."""
from lt_designs.cannery import build as design

ZONE = "ZI1"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')
PRODUCT = "Food"


def build(lod):
    design(lod, W=2, D=4, **{'masonry': True, 'storeys': 2, 'roof': 'side', 'cross': (1,), 'stack': True, 'arch': True, 'wall': 'Brick085', 'base': 'Greystone', 'roof_mat': 'Slate', 'door': 'Oxblood', 'sign': 'QuoddyPacking'})
