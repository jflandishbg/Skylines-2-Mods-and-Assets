"""Lobstertown GothicBatten, lot 1x4. Built from lt_designs/shorerows.py."""
from lt_designs.shorerows import build as design

ZONE = "ZL1"
HOUSEHOLDS = 2
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=4, **{'hh': 2, 'roof': 'gable', 'storeys': 2, 'rise': 5.6, 'wall': 'BoardBatten', 'gable_mat': 'BoardBatten', 'gwin': 'lancet', 'roof_mat': 'TinOxide', 'door': 'Black', 'door_x': 0.0, 'shutters': 'Green', 'porch': 'full', 'spindles': False, 'barge': True, 'finial': True, 'rear': ({'k': 'ell', 'roof': 'cross', 'h': 6.7, 'mat': 'Clapboard', 'rmat': 'SlateGreen', 'L': 6.5, 'min': 4.5, 'piazza': 2}, {'k': 'ell', 'roof': 'shed', 'h': 3.55, 'mat': 'BoardBatten', 'rmat': 'TinFlat', 'L': 5.0, 'min': 3.0, 'rise': 1.5, 'grow': True}), 'palette': 'victorian'})
