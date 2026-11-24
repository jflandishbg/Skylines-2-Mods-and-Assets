"""Lobstertown QueenAnneQuad, lot 1x4. Built from lt_designs/shorerows.py."""
from lt_designs.shorerows import build as design

ZONE = "ZL1"
HOUSEHOLDS = 4
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=4, **{'hh': 4, 'roof': 'gable', 'storeys': 4, 'rise': 4.0, 'upper': (9.85, 'Fishscale'), 'roof_mat': 'SlateBrown', 'door': 'GreyBlue', 'bays': [-2.5, 0.0], 'door_x': -2.5, 'porch': 'stack4', 'porch_x': (-3.986, 1.3), 'tower': {'kind': 'oct', 'x': 2.42, 'a': 1.1, 'rise': 3.6}, 'backporch': 2, 'hand': 'R', 'rear': ({'k': 'ell', 'roof': 'cross', 'h': 6.7, 'mat': 'BoardBatten', 'rmat': 'TinGreen', 'L': 6.5, 'min': 4.5, 'piazza': 1, 'barge': True}, {'k': 'ell', 'roof': 'gable', 'h': 6.7, 'mat': 'Clapboard', 'rmat': 'TinGreen', 'L': 6.0, 'min': 4.0, 'grow': True}), 'palette': 'victorian'})
