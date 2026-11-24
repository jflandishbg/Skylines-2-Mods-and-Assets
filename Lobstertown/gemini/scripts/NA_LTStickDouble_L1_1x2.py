"""Lobstertown StickDouble, lot 1x2. Built from lt_designs/shorerows.py."""
from lt_designs.shorerows import build as design

ZONE = "ZL1"
HOUSEHOLDS = 3
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=2, **{'hh': 3, 'roof': 'gable', 'rise': 5.0, 'stick': True, 'truss': True, 'gable_mat': 'BoardBatten', 'roof_mat': 'SlateBrown', 'door': 'Black', 'door_x': 0.0, 'porch': 'double', 'spindles': False, 'chimney': 2, 'backporch': 2, 'hand': 'R', 'rear': ({'k': 'ell', 'roof': 'shed', 'h': 6.7, 'mat': 'BoardBatten', 'rmat': 'SlateDark', 'L': 6.0, 'min': 4.0, 'rise': 1.6}, {'k': 'ell', 'roof': 'cross', 'h': 3.55, 'mat': 'Clapboard', 'rmat': 'TinGreen', 'L': 6.0, 'min': 3.0, 'barge': True}, {'k': 'carriage', 'roof': 'across', 'h': 3.55, 'mat': 'BoardBatten', 'rmat': 'TinFlat', 'L': 8.0, 'min': 6.0, 'grow': True}), 'palette': 'victorian'})
