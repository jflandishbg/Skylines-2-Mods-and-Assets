"""Lobstertown CornerCasinoLeftCorner, lot 5x6. Built from lt_designs/boardwalk.py."""
from lt_designs.boardwalk import build as design

ZONE = "ZC2"
HOUSEHOLDS = 0
PARTY_WALLS = ('right',)


def build(lod):
    design(lod, W=5, D=6, **{'storeys': 5, 'promenade': True, 'roofs': 'm', 'turret': 'both', 'spire': (2, 1), 'towers': (('c', 2, 'dome'),), 'base': 'Greystone', 'wall': 'ShingleSilver', 'gable_mat': 'ShingleGrey', 'roof_mat': 'TinOxide', 'door': 'Oxblood', 'corner': True, 'lots': [(4, 4), (4, 5), (5, 5), (4, 6), (5, 6), (6, 6)]})
