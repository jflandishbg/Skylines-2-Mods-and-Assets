"""Lobstertown MarineIronworks, lot 4x4. Built from lt_designs/cannery.py."""
from lt_designs.cannery import build as design

ZONE = "ZI1"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')
PRODUCT = "Machinery"


def build(lod):
    design(lod, W=4, D=4, **{'masonry': True, 'storeys': 3, 'roof': 'front', 'roofs': 'mg', 'vents': 'monitor', 'stack': True, 'back': 'store', 'arch': True, 'wall': 'Brick054', 'base': 'Greystone', 'roof_mat': 'SlateDark', 'door': 'Black', 'dock': 1.0})
