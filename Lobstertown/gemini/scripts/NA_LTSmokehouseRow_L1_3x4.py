"""Lobstertown SmokehouseRow, lot 3x4. Built from lt_designs/cannery.py."""
from lt_designs.cannery import build as design

ZONE = "ZI1"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')
PRODUCT = "Food"


def build(lod):
    design(lod, W=3, D=4, **{'storeys': 3, 'roofs': 'g', 'vents': 'monitor', 'wall': 'ShingleGrey', 'roof_mat': 'SlateDark', 'door': 'Black', 'sign': 'SmokedHerring'})
