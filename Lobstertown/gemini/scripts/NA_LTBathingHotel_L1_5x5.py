"""Lobstertown BathingHotel, lot 5x5. Built from lt_designs/boardwalk.py."""
from lt_designs.boardwalk import build as design

ZONE = "ZC2"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=5, D=5, **{'storeys': 5, 'promenade': True, 'roofs': 'g', 'turret': 'l', 'towers': (('c', 2, 'hip'),), 'back': 'store', 'base': 'Greystone', 'wall': 'Clapboard', 'gable_mat': 'ShingleGrey', 'roof_mat': 'SlateGreen', 'door': 'Black'})
