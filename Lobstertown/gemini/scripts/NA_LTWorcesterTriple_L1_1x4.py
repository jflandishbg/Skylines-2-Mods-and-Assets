"""Lobstertown WorcesterTriple, lot 1x4. Built from lt_designs/shore_row.py."""
from lt_designs.shore_row import build as design

ZONE = "ZL1"
HOUSEHOLDS = 3
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=4, **{'roof': 'gable', 'front': 'triple', 'decks': True, 'rear': 'tall', 'hand': 'R', 'wall': 'ShingleSilver', 'gable_mat': 'ShingleGrey', 'roof_mat': 'SlateDark', 'door': 'Oxblood', 'lites': '2'})
