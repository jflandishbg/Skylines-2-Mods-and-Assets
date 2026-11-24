"""Lobstertown StickGable, lot 1x5. Built from lt_designs/shorerows.py."""
from lt_designs.shorerows import build as design

ZONE = "ZL1"
HOUSEHOLDS = 2
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=5, **{'hh': 2, 'roof': 'gable', 'rise': 4.8, 'stick': True, 'truss': True, 'gable_mat': 'BoardBatten', 'gwin': 'single', 'roof_mat': 'SlateDark', 'door': 'Black', 'door_x': 2.5, 'porch': 'full', 'spindles': False, 'chimney': 2, 'rear': ({'k': 'ell', 'roof': 'shed', 'h': 6.7, 'mat': 'BoardBatten', 'rmat': 'TinGreen', 'L': 6.0, 'min': 4.0, 'rise': 1.6}, {'k': 'ell', 'roof': 'gable', 'h': 3.55, 'mat': 'Clapboard', 'rmat': 'SlateDark', 'L': 7.0, 'min': 3.0, 'grow': True}, {'k': 'carriage', 'roof': 'across', 'h': 3.55, 'mat': 'BoardBatten', 'rmat': 'TinOxide', 'L': 8.0, 'min': 6.0, 'cupola': True}), 'palette': 'victorian'})
