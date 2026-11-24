"""Lobstertown Natatorium, lot 4x5. Built from lt_designs/boardwalk.py."""
from lt_designs.boardwalk import build as design

ZONE = "ZC2"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=4, D=5, **{'storeys': 5, 'promenade': True, 'roofs': 'gm', 'back': 'store', 'lantern': True, 'base': 'Rubble', 'wall': 'ShingleSilver', 'gable_mat': 'ShingleGrey', 'roof_mat': 'SlateDark', 'door': 'Green', 'sign': 'Natatorium', 'towers': (('l', 3, 'hip'), ('r', 2, 'hip'))})
