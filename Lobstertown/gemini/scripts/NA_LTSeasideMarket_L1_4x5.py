"""Lobstertown SeasideMarket, lot 4x5. Built from lt_designs/boardwalk.py."""
from lt_designs.boardwalk import build as design

ZONE = "ZC2"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=4, D=5, **{'storeys': 4, 'promenade': True, 'roofs': 'gmmg', 'turret': 'r', 'back': 'store', 'base': 'Greystone', 'wall': 'ShingleSilver', 'gable_mat': 'ShingleGrey', 'roof_mat': 'SlateGreen', 'door': 'GreyBlue', 'sign': 'SeasideMarket', 'towers': (('l', 3, 'hip'), ('r', 2, 'hip')), 'spire': (0, 1)})
