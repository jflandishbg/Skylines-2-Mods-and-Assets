"""Lobstertown CrateBoxMill, lot 2x4. Built from lt_designs/cannery.py."""
from lt_designs.cannery import build as design

ZONE = "ZI1"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')
PRODUCT = "Paper"


def build(lod):
    design(lod, W=2, D=4, **{'masonry': True, 'storeys': 3, 'roof': 'mansard', 'stack': True, 'back': 'store', 'arch': True, 'wall': 'BuffBrick', 'base': 'Greystone', 'roof_mat': 'SlateDark', 'door': 'Black', 'dock': 1.0})
