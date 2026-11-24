"""Lobstertown OrielGable, lot 1x3. Built from lt_designs/shore_row.py."""
from lt_designs.shore_row import build as design

ZONE = "ZL1"
HOUSEHOLDS = 3
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=3, **{'storeys': 4, 'roof': 'gable', 'front': 'oriel', 'decks': True, 'rear': 'cape', 'wall': 'ShingleSilver', 'gable_mat': 'ShingleGrey', 'roof_mat': 'Slate', 'door': 'Green', 'lites': '2', 'dormers': True})
