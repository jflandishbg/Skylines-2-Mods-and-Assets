"""Lobstertown SailLoft, lot 2x4. Built from lt_designs/cannery.py."""
from lt_designs.cannery import build as design

ZONE = "ZI1"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')
PRODUCT = "Textiles"


def build(lod):
    design(lod, W=2, D=4, **{'masonry': True, 'storeys': 3, 'roof': 'front', 'roofs': 'm', 'arch': False, 'wall': 'Brick094', 'base': 'Greystone', 'roof_mat': 'SlateBrown', 'door': 'GreyBlue', 'sign': 'SailLoft'})
