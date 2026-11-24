"""Lobstertown RollerRink, lot 5x5. Built from lt_designs/boardwalk.py."""
from lt_designs.boardwalk import build as design

ZONE = "ZC2"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=5, D=5, **{'storeys': 4, 'promenade': True, 'roofs': 'mg', 'turret': 'r', 'back': 'store', 'wall': 'ClapSage', 'gable_mat': 'ShingleSilver', 'roof_mat': 'TinOxide', 'door': 'GreyBlue', 'sign': 'RollerRink', 'towers': (('l', 2, 'hip'),), 'spire': (0, 2), 'pitch': 1.7})
