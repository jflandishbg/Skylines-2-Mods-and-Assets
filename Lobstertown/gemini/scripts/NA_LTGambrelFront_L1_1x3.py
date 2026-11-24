"""Lobstertown GambrelFront, lot 1x3. Built from lt_designs/shore_row.py."""
from lt_designs.shore_row import build as design

ZONE = "ZL1"
HOUSEHOLDS = 2
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=3, **{'roof': 'gambrel', 'front': 'porch', 'rear': 'cape', 'hand': 'R', 'wall': 'ShingleGrey', 'roof_mat': 'SlateDark', 'door': 'GreyBlue', 'shutters': 'Green', 'lites': '6'})
