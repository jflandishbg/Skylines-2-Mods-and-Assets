"""Lobstertown QueenAnneDouble, lot 1x2. Built from lt_designs/shorerows.py."""
from lt_designs.shorerows import build as design

ZONE = "ZL1"
HOUSEHOLDS = 3
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=2, **{'hh': 3, 'roof': 'gable', 'rise': 4.4, 'upper': (6.85, 'Fishscale'), 'gwin': 'triple', 'roof_mat': 'Slate', 'door': 'Green', 'door_x': 2.5, 'porch': 'double', 'dormers': True, 'band': True, 'rear': ({'k': 'ell', 'roof': 'cross', 'h': 6.7, 'mat': 'Clapboard', 'rmat': 'Slate', 'L': 6.0, 'min': 4.5, 'piazza': 1, 'barge': True}, {'k': 'ell', 'roof': 'gable', 'h': 6.7, 'mat': 'BoardBatten', 'rmat': 'Slate', 'L': 7.0, 'min': 4.0, 'grow': True}, {'k': 'carriage', 'roof': 'gambrel', 'h': 3.55, 'mat': 'Clapboard', 'rmat': 'TinOxide', 'L': 8.0, 'min': 6.0}), 'palette': 'victorian'})
