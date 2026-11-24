"""Lobstertown CornerQueenAnneRightCorner, lot 1x6. Built from lt_designs/shorerows.py."""
from lt_designs.shorerows import build as design

ZONE = "ZL1"
HOUSEHOLDS = 3
PARTY_WALLS = ('left',)


def build(lod):
    design(lod, D=6, **{'hh': 3, 'corner': True, 'ci': 2.0, 'roof': 'gable', 'rise': 4.2, 'upper': (6.85, 'Fishscale'), 'roof_mat': 'SlateGreen', 'door': 'Oxblood', 'bays': [1.0, 2.9], 'door_x': 1.0, 'porch': 'wrap', 'wrap_len': 6.0, 'tower': {'kind': 'oct', 'x': -0.8699999999999999, 'a': 1.1, 'z0': 3.95, 'above': 2.4, 'rise': 3.2}, 'finial': True, 'rear': ({'k': 'ell', 'roof': 'gable', 'h': 3.55, 'mat': 'Clapboard', 'rmat': 'SlateGreen', 'L': 7.0, 'min': 3.0, 'grow': True}, {'k': 'carriage', 'roof': 'hip', 'h': 3.55, 'mat': 'BoardBatten', 'rmat': 'TinOxide', 'L': 8.0, 'min': 6.0, 'cupola': True}), 'palette': 'victorian', 'hand': 'R'})
