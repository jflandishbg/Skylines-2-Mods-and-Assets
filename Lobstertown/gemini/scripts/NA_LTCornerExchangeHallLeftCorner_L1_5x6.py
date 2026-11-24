"""Lobstertown CornerExchangeHallLeftCorner, lot 5x6. Built from lt_designs/boardwalk.py."""
from lt_designs.boardwalk import build as design

ZONE = "ZC2"
HOUSEHOLDS = 0
PARTY_WALLS = ('right',)


def build(lod):
    design(lod, W=5, D=6, **{'storeys': 6, 'promenade': True, 'roofs': 'g', 'turret': 'l', 'spire': (3, 0), 'towers': (('c', 3, 'hip'),), 'pitch': 1.5, 'wall': 'ShingleGrey', 'gable_mat': 'ShingleSilver', 'roof_mat': 'SlateDark', 'door': 'Black', 'corner': True, 'lots': [(4, 4), (4, 5), (5, 5), (4, 6), (5, 6), (6, 6)]})
