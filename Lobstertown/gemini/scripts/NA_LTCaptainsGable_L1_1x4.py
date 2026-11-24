"""Lobstertown CaptainsGable, lot 1x4. Built from lt_designs/shore_row.py."""
from lt_designs.shore_row import build as design

ZONE = "ZL1"
HOUSEHOLDS = 2
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=4, **{'roof': 'gable', 'front': 'porch', 'rear': 'tall', 'wall': 'ShingleSilver', 'roof_mat': 'SlateDark', 'door': 'Oxblood', 'shutters': 'Black', 'lites': '6'})
