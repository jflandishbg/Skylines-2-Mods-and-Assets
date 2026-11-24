"""Lobstertown PicturePalace, lot 6x6. Built from lt_designs/boardwalk.py."""
from lt_designs.boardwalk import build as design

ZONE = "ZC2"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=6, D=6, **{'storeys': 6, 'promenade': True, 'roofs': 'mgm', 'turret': 'both', 'wall': 'Clapboard', 'gable_mat': 'ShingleGrey', 'roof_mat': 'TinOxide', 'door': 'Oxblood', 'sign': 'PicturePalace', 'towers': (('c', 3, 'dome'),), 'spire': (1, 1)})
