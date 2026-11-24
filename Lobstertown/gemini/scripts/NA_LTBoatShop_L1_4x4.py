"""Lobstertown BoatShop, lot 4x4. Built from lt_designs/cannery.py."""
from lt_designs.cannery import build as design

ZONE = "ZI1"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')
PRODUCT = "Vehicles"


def build(lod):
    design(lod, W=4, D=4, **{'masonry': True, 'storeys': 2, 'roof': 'front', 'roofs': 'g', 'vents': 'monitor', 'stack': True, 'back': 'store', 'arch': True, 'wall': 'Brick074', 'base': 'Greystone', 'roof_mat': 'SlateGreen', 'door': 'Green', 'sign': 'BoatBuilders'})
