"""Lobstertown BayGable, lot 1x4. Built from lt_designs/shore_row.py."""
from lt_designs.shore_row import build as design

ZONE = "ZL1"
HOUSEHOLDS = 2
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=4, **{'roof': 'gable', 'front': 'bay', 'rear': 'cape', 'hand': 'R', 'wall': 'ShingleGrey', 'gable_mat': 'ShingleSilver', 'roof_mat': 'Slate', 'door': 'Green', 'lites': '2', 'dormers': True})
