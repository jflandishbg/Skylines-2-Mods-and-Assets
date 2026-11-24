"""Lobstertown StickTower, lot 1x4. Built from lt_designs/shorerows.py."""
from lt_designs.shorerows import build as design

ZONE = "ZL1"
HOUSEHOLDS = 2
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=4, **{'hh': 2, 'roof': 'gable', 'rise': 4.8, 'stick': True, 'truss': True, 'gable_mat': 'BoardBatten', 'roof_mat': 'SlateGreen', 'door': 'Oxblood', 'bays': [-2.5, 0.0], 'door_x': -2.5, 'porch': 'half', 'porch_x': (-3.986, 1.1), 'spindles': False, 'tower': {'kind': 'square', 'x': 2.59, 'a': 1.1, 'above': 2.6, 'rise': 3.0, 'mat': 'BoardBatten', 'roof': 'TinGreen'}, 'rear': ({'k': 'ell', 'roof': 'cross', 'h': 3.55, 'mat': 'BoardBatten', 'rmat': 'SlateGreen', 'L': 6.0, 'min': 3.0, 'barge': True}, {'k': 'ell', 'roof': 'shed', 'h': 3.55, 'mat': 'Clapboard', 'rmat': 'TinFlat', 'L': 6.0, 'min': 3.0, 'rise': 1.5, 'grow': True}, {'k': 'carriage', 'roof': 'gambrel', 'h': 3.55, 'mat': 'Clapboard', 'rmat': 'SlateDark', 'L': 8.0, 'min': 6.0, 'cupola': True}), 'palette': 'victorian'})
