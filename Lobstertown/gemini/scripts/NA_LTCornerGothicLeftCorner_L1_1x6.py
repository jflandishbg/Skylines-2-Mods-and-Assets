"""Lobstertown CornerGothicLeftCorner, lot 1x6. Built from lt_designs/shorerows.py."""
from lt_designs.shorerows import build as design

ZONE = "ZL1"
HOUSEHOLDS = 3
PARTY_WALLS = ('right',)


def build(lod):
    design(lod, D=6, **{'hh': 3, 'corner': True, 'roof': 'side', 'storeys': 2, 'depth': 9.0, 'xgables': ((0.2, 3.2),), 'xpitch': 1.5, 'wall': 'BoardBatten', 'gable_mat': 'BoardBatten', 'roof_mat': 'SlateDark', 'door': 'Oxblood', 'door_x': 0.2, 'porch': 'full', 'spindles': False, 'barge': True, 'finial': True, 'rear': ({'k': 'ell', 'roof': 'cross', 'h': 3.55, 'mat': 'Clapboard', 'rmat': 'TinFlat', 'L': 6.0, 'min': 3.0, 'barge': True}, {'k': 'carriage', 'roof': 'hip', 'h': 3.55, 'mat': 'BoardBatten', 'rmat': 'SlateGreen', 'L': 8.0, 'min': 6.0, 'cupola': True, 'grow': True}), 'palette': 'victorian'})
