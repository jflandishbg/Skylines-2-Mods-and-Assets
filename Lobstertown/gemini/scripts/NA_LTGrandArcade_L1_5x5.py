"""Lobstertown GrandArcade, lot 5x5. Built from lt_designs/boardwalk.py."""
from lt_designs.boardwalk import build as design

ZONE = "ZC2"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=5, D=5, **{'storeys': 5, 'promenade': True, 'roofs': 'gmg', 'turret': 'both', 'lantern': False, 'base': 'Greystone', 'wall': 'ShingleSilver', 'gable_mat': 'ShingleGrey', 'roof_mat': 'TinOxide', 'door': 'Green', 'sign': 'GrandArcade', 'towers': (('c', 2, 'hipl'),), 'spire': (1, 1)})
