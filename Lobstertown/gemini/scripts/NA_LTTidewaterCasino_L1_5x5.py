"""Lobstertown TidewaterCasino, lot 5x5. Built from lt_designs/boardwalk.py."""
from lt_designs.boardwalk import build as design

ZONE = "ZC2"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=5, D=5, **{'storeys': 4, 'promenade': True, 'roofs': 'gm', 'turret': 'both', 'spire': (1, 1), 'towers': (('l', 2, 'hipl'), ('r', 2, 'hipl')), 'base': 'Greystone', 'wall': 'ShingleSilver', 'gable_mat': 'ShingleGrey', 'roof_mat': 'SlateGreen', 'door': 'Oxblood'})
