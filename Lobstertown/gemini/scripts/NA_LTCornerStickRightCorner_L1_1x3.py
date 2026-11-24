"""Lobstertown CornerStickRightCorner, lot 1x3. Built from lt_designs/shorerows.py."""
from lt_designs.shorerows import build as design

ZONE = "ZL1"
HOUSEHOLDS = 3
PARTY_WALLS = ('left',)


def build(lod):
    design(lod, D=3, **{'hh': 3, 'corner': True, 'roof': 'gable', 'rise': 4.8, 'stick': True, 'truss': True, 'gable_mat': 'BoardBatten', 'roof_mat': 'SlateDark', 'door': 'Green', 'bays': [0.0, 2.5], 'door_x': 2.5, 'porch': 'half', 'porch_x': (-1.2, 3.986), 'spindles': False, 'side_bays': [2.0, 4.5, 7.0, 9.5], 'ci': 0.5, 'tower': {'kind': 'square', 'x': -2.37, 'a': 1.1, 'above': 2.6, 'rise': 3.0, 'mat': 'BoardBatten', 'roof': 'SlateDark'}, 'rear': ({'k': 'ell', 'roof': 'gable', 'h': 3.55, 'mat': 'BoardBatten', 'rmat': 'TinGreen', 'L': 5.0, 'min': 3.0, 'grow': True}, {'k': 'carriage', 'roof': 'gambrel', 'h': 3.55, 'mat': 'Clapboard', 'rmat': 'SlateBrown', 'L': 8.0, 'min': 6.0}), 'palette': 'victorian', 'hand': 'R'})
