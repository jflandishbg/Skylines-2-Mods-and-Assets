"""Lobstertown GothicGable, lot 1x6. Built from lt_designs/shorerows.py."""
from lt_designs.shorerows import build as design

ZONE = "ZL1"
HOUSEHOLDS = 2
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=6, **{'hh': 2, 'roof': 'gable', 'storeys': 2, 'rise': 5.4, 'band': True, 'gable_mat': 'BoardBatten', 'gwin': 'lancet', 'roof_mat': 'SlateDark', 'door': 'Oxblood', 'bays': [-2.5, 2.0], 'door_x': -2.5, 'bay': {'x': 2.0, 'z1': 3.3}, 'porch': 'half', 'porch_x': (-3.986, -1.25), 'spindles': False, 'barge': True, 'finial': True, 'rear': ({'k': 'ell', 'roof': 'gable', 'h': 6.7, 'mat': 'Clapboard', 'rmat': 'SlateBrown', 'L': 7.0, 'min': 4.0, 'piazza': 1, 'grow': True}, {'k': 'ell', 'roof': 'shed', 'h': 3.55, 'mat': 'BoardBatten', 'rmat': 'TinGreen', 'L': 4.5, 'min': 3.0, 'rise': 1.4}, {'k': 'carriage', 'roof': 'hip', 'h': 3.55, 'mat': 'Clapboard', 'rmat': 'TinOxide', 'L': 9.0, 'min': 6.0, 'grow': True}), 'palette': 'victorian'})
