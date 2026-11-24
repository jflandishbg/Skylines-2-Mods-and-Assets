"""Lobstertown CornerTripleLeftCorner, lot 1x4. Built from lt_designs/shorerows.py."""
from lt_designs.shorerows import build as design

ZONE = "ZL1"
HOUSEHOLDS = 3
PARTY_WALLS = ('right',)


def build(lod):
    design(lod, D=4, **{'hh': 3, 'corner': True, 'ci': 0.5, 'roof': 'flat', 'band': True, 'door': 'Black', 'door_x': 2.5, 'porch': 'stack', 'barge': True, 'finial': True, 'backporch': 2, 'roof_mat': 'SlateDark', 'rear': ({'k': 'ell', 'roof': 'gable', 'h': 6.7, 'mat': 'Clapboard', 'rmat': 'TinGreen', 'L': 7.0, 'min': 4.0, 'piazza': 1, 'grow': True}, {'k': 'carriage', 'roof': 'across', 'h': 3.55, 'mat': 'BoardBatten', 'rmat': 'SlateDark', 'L': 8.0, 'min': 6.0}), 'palette': 'victorian'})
