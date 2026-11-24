"""Lobstertown CornerOrielLeftCorner, lot 1x3. Built from lt_designs/shore_row.py."""
from lt_designs.shore_row import build as design

ZONE = "ZL1"
HOUSEHOLDS = 3
PARTY_WALLS = ('right',)


def build(lod):
    design(lod, D=3, **{'storeys': 4, 'roof': 'gable', 'front': 'oriel', 'corner': True, 'rear': 'cape', 'wall': 'ShingleGrey', 'gable_mat': 'ShingleSilver', 'roof_mat': 'SlateDark', 'door': 'Black', 'lites': '2'})
