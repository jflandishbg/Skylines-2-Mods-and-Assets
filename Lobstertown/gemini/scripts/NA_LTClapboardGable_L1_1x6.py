"""Lobstertown ClapboardGable, lot 1x6. Built from lt_designs/shore_row.py."""
from lt_designs.shore_row import build as design

ZONE = "ZL1"
HOUSEHOLDS = 2
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=6, **{'roof': 'gable', 'front': 'porch', 'rear': 'tall', 'decks': True, 'hand': 'R', 'wall': 'Clapboard', 'gable_mat': 'ShingleSilver', 'roof_mat': 'SlateGreen', 'door': 'Black', 'shutters': 'Black', 'lites': '6', 'back_mat': 'ShingleSilver'})
