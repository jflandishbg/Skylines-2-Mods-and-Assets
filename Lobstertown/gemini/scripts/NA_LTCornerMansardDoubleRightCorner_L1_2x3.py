"""Lobstertown CornerMansardDoubleRightCorner, lot 2x3. Built from lt_designs/shorerows.py."""
from lt_designs.shorerows import build as design

ZONE = "ZL1"
HOUSEHOLDS = 4
PARTY_WALLS = ('left',)


def build(lod):
    design(lod, D=3, **{'corner': True, 'wide_corner': 'double', 'hand': 'R', 'hh': 4, 'lots': [(2, 3), (2, 4)], 'wall': 'Clapboard', 'roof_mat': 'SlateDark'})
