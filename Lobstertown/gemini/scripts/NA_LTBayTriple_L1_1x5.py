"""Lobstertown BayTriple, lot 1x5. Built from lt_designs/shorerows.py."""
from lt_designs.shorerows import build as design

ZONE = "ZL1"
HOUSEHOLDS = 3
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=5, **{'hh': 3, 'roof': 'flat', 'door': 'Black', 'bays': [-2.5, -0.6, 2.45], 'door_x': -2.5, 'porch': 'stack', 'porch_x': (-3.986, 0.95), 'bay': {'x': 2.45, 'w': 1.2, 'proj': 0.6, 'z1': 9.3}, 'roof_mat': 'SlateGreen', 'finial': True, 'hand': 'R', 'rear': ({'k': 'ell', 'roof': 'shed', 'h': 3.55, 'mat': 'BoardBatten', 'rmat': 'TinGreen', 'L': 6.0, 'min': 3.0, 'rise': 1.5, 'grow': True}, {'k': 'carriage', 'roof': 'hip', 'h': 3.55, 'mat': 'Clapboard', 'rmat': 'TinGreen', 'L': 8.0, 'min': 6.0, 'cupola': True}), 'palette': 'victorian'})
