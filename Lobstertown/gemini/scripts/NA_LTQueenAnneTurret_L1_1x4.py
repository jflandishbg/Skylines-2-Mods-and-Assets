"""Lobstertown QueenAnneTurret, lot 1x4. Built from lt_designs/shorerows.py."""
from lt_designs.shorerows import build as design

ZONE = "ZL1"
HOUSEHOLDS = 2
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=4, **{'hh': 2, 'roof': 'gable', 'rise': 4.3, 'upper': (3.75, 'Fishscale'), 'roof_mat': 'SlateBrown', 'door': 'GreyBlue', 'bays': [-2.5, 0.0], 'door_x': -2.5, 'porch': 'half', 'porch_x': (-3.986, 1.0), 'tower': {'kind': 'oct', 'x': 2.38, 'a': 1.15, 'above': 2.4, 'rise': 3.4}, 'finial': True, 'rear': ({'k': 'ell', 'roof': 'gable', 'h': 3.55, 'mat': 'Clapboard', 'rmat': 'TinGreen', 'L': 7.0, 'min': 3.0, 'grow': True}, {'k': 'carriage', 'roof': 'across', 'h': 3.55, 'mat': 'BoardBatten', 'rmat': 'SlateBrown', 'L': 8.0, 'min': 6.0, 'cupola': True}), 'palette': 'victorian'})
