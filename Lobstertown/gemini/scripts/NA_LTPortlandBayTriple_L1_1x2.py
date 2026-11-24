"""Lobstertown PortlandBayTriple, lot 1x2. Built from lt_designs/shore_row.py."""
from lt_designs.shore_row import build as design

ZONE = "ZL1"
HOUSEHOLDS = 3
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=2, **{'roof': 'flat', 'front': 'baytriple', 'decks': True, 'wall': 'Clapboard', 'roof_mat': 'SlateDark', 'door': 'Green', 'lites': '2', 'back_mat': 'ShingleGrey'})
