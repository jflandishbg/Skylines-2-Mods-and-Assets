"""Lobstertown DoublePorch, lot 1x5. Built from lt_designs/shore_row.py."""
from lt_designs.shore_row import build as design

ZONE = "ZL1"
HOUSEHOLDS = 3
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=5, **{'roof': 'gable', 'front': 'double', 'decks': True, 'wall': 'ShingleSilver', 'roof_mat': 'SlateBrown', 'door': 'Black', 'lites': '2'})
