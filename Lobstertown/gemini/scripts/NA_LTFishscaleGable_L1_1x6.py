"""Lobstertown FishscaleGable, lot 1x6. Built from lt_designs/shorerows.py."""
from lt_designs.shorerows import build as design

ZONE = "ZL1"
HOUSEHOLDS = 2
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=6, **{'hh': 2, 'roof': 'gable', 'rise': 4.3, 'upper': (6.85, 'Fishscale'), 'gwin': 'triple', 'roof_mat': 'Slate', 'door': 'Green', 'bays': [-2.0, 2.5], 'door_x': 2.5, 'bay': {'x': -2.0, 'z1': 6.75}, 'porch': 'full', 'dormers': True, 'finial': True, 'backporch': 2, 'rear': ({'k': 'ell', 'roof': 'gable', 'h': 3.55, 'mat': 'Clapboard', 'rmat': 'SlateGreen', 'L': 6.0, 'min': 3.0}, {'k': 'ell', 'roof': 'cross', 'h': 3.55, 'mat': 'BoardBatten', 'rmat': 'TinOxide', 'L': 6.0, 'min': 3.0, 'barge': True}, {'k': 'carriage', 'roof': 'across', 'h': 3.55, 'mat': 'Clapboard', 'rmat': 'Slate', 'L': 9.0, 'min': 6.0, 'grow': True}), 'palette': 'victorian'})
