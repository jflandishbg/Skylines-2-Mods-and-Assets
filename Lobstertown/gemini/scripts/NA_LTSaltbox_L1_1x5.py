"""Lobstertown Saltbox, lot 1x5. Built from lt_designs/shore_row.py."""
from lt_designs.shore_row import build as design

ZONE = "ZL1"
HOUSEHOLDS = 2
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=5, **{'roof': 'saltbox', 'front': 'stoop', 'wall': 'ShingleGrey', 'roof_mat': 'SlateDark', 'door': 'Oxblood', 'shutters': 'Black', 'lites': '6', 'dormers': True})
