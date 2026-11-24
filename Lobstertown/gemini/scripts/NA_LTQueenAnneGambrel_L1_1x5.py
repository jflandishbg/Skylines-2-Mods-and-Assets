"""Lobstertown QueenAnneGambrel, lot 1x5. Built from lt_designs/shorerows.py."""
from lt_designs.shorerows import build as design

ZONE = "ZL1"
HOUSEHOLDS = 2
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=5, **{'hh': 2, 'roof': 'gambrel', 'band': True, 'roof_mat': 'SlateDark', 'door': 'GreyBlue', 'door_x': -2.5, 'porch': 'full', 'barge': True, 'finial': True, 'rear': ({'k': 'ell', 'roof': 'gable', 'h': 6.7, 'mat': 'Clapboard', 'rmat': 'SlateBrown', 'L': 7.0, 'min': 4.0, 'piazza': 1, 'grow': True}, {'k': 'carriage', 'roof': 'across', 'h': 3.55, 'mat': 'BoardBatten', 'rmat': 'TinFlat', 'L': 8.0, 'min': 6.0}), 'palette': 'victorian'})
