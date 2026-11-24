"""Lobstertown Ropewalk, lot 4x6. Built from lt_designs/cannery.py."""
from lt_designs.cannery import build as design

ZONE = "ZI1"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')
PRODUCT = "Textiles"


def build(lod):
    design(lod, W=4, D=6, **{'masonry': True, 'storeys': 2, 'roof': 'side', 'tower': 'left', 'back': 'store', 'arch': True, 'wall': 'BrownBrick', 'base': 'Rubble', 'roof_mat': 'SlateGreen', 'door': 'Oxblood', 'sign': 'CordageWorks'})
