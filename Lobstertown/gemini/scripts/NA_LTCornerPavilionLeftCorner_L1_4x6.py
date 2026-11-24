"""Lobstertown CornerPavilionLeftCorner, lot 4x6. Built from lt_designs/boardwalk.py."""
from lt_designs.boardwalk import build as design

ZONE = "ZC2"
HOUSEHOLDS = 0
PARTY_WALLS = ('right',)


def build(lod):
    design(lod, W=4, D=6, **{'storeys': 4, 'promenade': True, 'roofs': 'g', 'turret': 'both', 'spire': (1, 2), 'towers': (('l', 2, 'hipl'),), 'back': 'store', 'base': 'Rubble', 'wall': 'Clapboard', 'gable_mat': 'ShingleSilver', 'roof_mat': 'SlateGreen', 'door': 'Green', 'corner': True, 'lots': [(4, 4), (4, 5), (5, 5), (4, 6), (5, 6), (6, 6)]})
