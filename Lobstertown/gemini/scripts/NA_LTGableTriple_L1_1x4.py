"""Lobstertown GableTriple, lot 1x4. Built from lt_designs/shorerows.py."""
from lt_designs.shorerows import build as design

ZONE = "ZL1"
HOUSEHOLDS = 3
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=4, **{'hh': 3, 'roof': 'gable', 'rise': 4.0, 'upper': (6.85, 'Fishscale'), 'roof_mat': 'Slate', 'door': 'Oxblood', 'door_x': 2.5, 'porch': 'stack', 'backporch': 2, 'hand': 'R', 'rear': ({'k': 'ell', 'roof': 'gable', 'h': 6.7, 'mat': 'Clapboard', 'rmat': 'TinOxide', 'L': 7.0, 'min': 4.0, 'piazza': 2, 'grow': True}, {'k': 'ell', 'roof': 'gable', 'h': 6.7, 'mat': 'BoardBatten', 'rmat': 'TinOxide', 'L': 6.0, 'min': 4.0}), 'palette': 'victorian'})
