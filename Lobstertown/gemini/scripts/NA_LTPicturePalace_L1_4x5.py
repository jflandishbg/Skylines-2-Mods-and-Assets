"""Lobstertown PicturePalace, lot 4x5. Built from lt_designs/boardwalk.py."""
from lt_designs.boardwalk import build as design

ZONE = "ZC2"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=4, D=5, **{'storeys': 6, 'promenade': True, 'roofs': 'mgm', 'turret': 'both', 'wall': 'Clapboard', 'gable_mat': 'ShingleGrey', 'roof_mat': 'TinOxide', 'door': 'Oxblood', 'sign': 'PicturePalace', 'towers': (('c', 3, 'dome'),), 'spire': (1, 1)})
