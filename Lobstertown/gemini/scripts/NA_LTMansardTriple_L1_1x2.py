"""Lobstertown MansardTriple, lot 1x2. Built from lt_designs/shore_row.py."""
from lt_designs.shore_row import build as design

ZONE = "ZL1"
HOUSEHOLDS = 3
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=2, **{'roof': 'mansard', 'front': 'triple', 'decks': True, 'rear': 'cape', 'hand': 'R', 'wall': 'Clapboard', 'roof_mat': 'SlateDark', 'door': 'Black', 'lites': '2', 'back_mat': 'ShingleSilver'})
