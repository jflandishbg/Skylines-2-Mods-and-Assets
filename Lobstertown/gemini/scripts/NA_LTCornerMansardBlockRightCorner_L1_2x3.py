"""Lobstertown CornerMansardBlockRightCorner, lot 2x3. Built from lt_designs/mainst.py."""
from lt_designs.mainst import build as design

ZONE = "ZM1"
HOUSEHOLDS = 6
PARTY_WALLS = ('left',)


def build(lod):
    design(lod, D=3, **{'corner': True, 'wide_corner': 'block', 'hand': 'R', 'hh': 6, 'lots': [(2, 3), (2, 4)], 'wall': 'Brick074', 'roof_mat': 'SlateDark'})
