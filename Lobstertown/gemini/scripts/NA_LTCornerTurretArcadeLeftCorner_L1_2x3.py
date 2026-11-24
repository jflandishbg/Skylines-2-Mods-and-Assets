"""Lobstertown CornerTurretArcadeLeftCorner, lot 2x3. Built from lt_designs/mainst.py."""
from lt_designs.mainst import build as design

ZONE = "ZM1"
HOUSEHOLDS = 5
PARTY_WALLS = ('right',)


def build(lod):
    design(lod, D=3, **{'corner': True, 'wide_corner': 'arcade', 'hand': 'L', 'hh': 5, 'lots': [(2, 3), (2, 4)], 'wall': 'Brick085', 'roof_mat': 'SlateGreen'})
