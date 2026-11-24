"""Lobstertown QuadDecker, lot 1x5. Built from lt_designs/shorerows.py."""
from lt_designs.shorerows import build as design

ZONE = "ZL1"
HOUSEHOLDS = 4
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=5, **{'hh': 4, 'roof': 'flat', 'storeys': 4, 'band': True, 'door': 'Black', 'door_x': -2.5, 'porch': 'stack4', 'barge': True, 'backporch': 2, 'roof_mat': 'SlateDark', 'rear': ({'k': 'ell', 'roof': 'gable', 'h': 6.7, 'mat': 'BoardBatten', 'rmat': 'TinOxide', 'L': 8.0, 'min': 4.0, 'piazza': 1, 'grow': True}, {'k': 'ell', 'roof': 'shed', 'h': 3.55, 'mat': 'Clapboard', 'rmat': 'TinFlat', 'L': 5.0, 'min': 3.0, 'rise': 1.6}), 'palette': 'victorian'})
