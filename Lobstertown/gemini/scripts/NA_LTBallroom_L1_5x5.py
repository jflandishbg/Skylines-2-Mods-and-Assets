"""Lobstertown Ballroom, lot 5x5. Built from lt_designs/boardwalk.py."""
from lt_designs.boardwalk import build as design

ZONE = "ZC2"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=5, D=5, **{'storeys': 5, 'promenade': True, 'roofs': 'g', 'turret': 'l', 'back': 'store', 'lantern': False, 'wall': 'ShingleGrey', 'gable_mat': 'ShingleSilver', 'roof_mat': 'TinOxide', 'door': 'Black', 'sign': 'Ballroom', 'towers': (('l', 2, 'hipl'),), 'spire': (2, 0), 'pitch': 1.6})
