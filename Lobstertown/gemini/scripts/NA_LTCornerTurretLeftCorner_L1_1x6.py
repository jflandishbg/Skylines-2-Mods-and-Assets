"""Lobstertown CornerTurretLeftCorner, lot 1x6. Built from lt_designs/shore_row.py."""
from lt_designs.shore_row import build as design

ZONE = "ZL1"
HOUSEHOLDS = 3
PARTY_WALLS = ('right',)


def build(lod):
    design(lod, D=6, **{'roof': 'gable', 'front': 'turret', 'turret_side': -1, 'corner': True, 'wall': 'ShingleSilver', 'roof_mat': 'SlateDark', 'door': 'Oxblood', 'shutters': 'Black', 'lites': '6', 'back_mat': 'ShingleGrey'})
