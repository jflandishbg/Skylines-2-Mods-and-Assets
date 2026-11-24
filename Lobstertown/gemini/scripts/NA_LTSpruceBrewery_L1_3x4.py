"""Lobstertown SpruceBrewery, lot 3x4. Built from lt_designs/cannery.py."""
from lt_designs.cannery import build as design

ZONE = "ZI1"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')
PRODUCT = "Beverages"


def build(lod):
    design(lod, W=3, D=4, **{'masonry': True, 'storeys': 3, 'roof': 'mansard', 'tower': 'left', 'stack': True, 'arch': True, 'wall': 'Brick074', 'base': 'Dressed', 'roof_mat': 'Slate', 'door': 'Oxblood', 'dock': 1.0})
