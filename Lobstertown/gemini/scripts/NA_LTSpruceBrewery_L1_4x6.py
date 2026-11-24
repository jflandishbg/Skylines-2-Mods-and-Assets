"""Lobstertown SpruceBrewery, lot 4x6. Built from lt_designs/cannery.py."""
from lt_designs.cannery import build as design

ZONE = "ZI1"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')
PRODUCT = "Beverages"


def build(lod):
    design(lod, W=4, D=6, **{'masonry': True, 'storeys': 3, 'roof': 'mansard', 'tower': 'left', 'stack': True, 'arch': True, 'wall': 'Brick074', 'base': 'Dressed', 'roof_mat': 'Slate', 'door': 'Oxblood', 'dock': 1.0})
