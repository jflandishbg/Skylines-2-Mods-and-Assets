"""Lobstertown CordageLeftCorner, lot 3x4. Built from lt_designs/cannery.py."""
from lt_designs.cannery import build as design

ZONE = "ZI1"
HOUSEHOLDS = 0
PARTY_WALLS = ('right',)
PRODUCT = "Textiles"


def build(lod):
    design(lod, W=3, D=4, **{'masonry': True, 'storeys': 3, 'roof': 'mansard', 'tower': 'left', 'back': 'store', 'arch': False, 'wall': 'BrownBrick', 'base': 'Rubble', 'roof_mat': 'SlateGreen', 'door': 'Green', 'corner': True, 'dock': 1.0})
