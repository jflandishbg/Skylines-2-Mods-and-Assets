"""Lobstertown QueenAnneBay, lot 1x5. Built from lt_designs/shorerows.py."""
from lt_designs.shorerows import build as design

ZONE = "ZL1"
HOUSEHOLDS = 2
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=5, **{'hh': 2, 'roof': 'gable', 'rise': 4.6, 'band': True, 'roof_mat': 'SlateDark', 'door': 'Black', 'bays': [-2.5, 2.0], 'door_x': -2.5, 'bay': {'x': 2.0, 'z1': 6.75, 'mat': 'Fishscale'}, 'porch': 'half', 'porch_x': (-3.986, -1.25), 'dormers': True, 'finial': True, 'backporch': 2, 'lites': '6', 'rear': ({'k': 'ell', 'roof': 'cross', 'h': 6.7, 'mat': 'Clapboard', 'rmat': 'Slate', 'L': 6.5, 'min': 4.5, 'barge': True}, {'k': 'ell', 'roof': 'gable', 'h': 3.55, 'mat': 'BoardBatten', 'rmat': 'TinFlat', 'L': 6.0, 'min': 3.0, 'grow': True}), 'palette': 'victorian'})
