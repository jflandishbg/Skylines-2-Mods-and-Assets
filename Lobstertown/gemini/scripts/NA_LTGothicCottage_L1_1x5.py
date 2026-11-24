"""Lobstertown GothicCottage, lot 1x5. Built from lt_designs/shorerows.py."""
from lt_designs.shorerows import build as design

ZONE = "ZL1"
HOUSEHOLDS = 2
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=5, **{'hh': 2, 'roof': 'side', 'storeys': 2, 'depth': 8.5, 'xgables': ((0.0, 3.4),), 'xpitch': 1.5, 'wall': 'BoardBatten', 'gable_mat': 'BoardBatten', 'roof_mat': 'SlateGreen', 'door': 'Green', 'door_x': 0.0, 'porch': 'full', 'spindles': False, 'barge': True, 'finial': True, 'rear': ({'k': 'ell', 'roof': 'cross', 'h': 3.55, 'mat': 'Clapboard', 'rmat': 'TinOxide', 'L': 6.5, 'min': 3.0, 'barge': True}, {'k': 'ell', 'roof': 'gable', 'h': 3.55, 'mat': 'BoardBatten', 'rmat': 'TinFlat', 'L': 7.0, 'min': 3.0, 'grow': True}, {'k': 'carriage', 'roof': 'gambrel', 'h': 3.55, 'mat': 'BoardBatten', 'rmat': 'SlateGreen', 'L': 8.0, 'min': 6.0}), 'palette': 'victorian'})
