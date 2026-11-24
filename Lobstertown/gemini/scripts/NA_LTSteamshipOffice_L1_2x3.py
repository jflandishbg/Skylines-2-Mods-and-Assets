"""Lobstertown SteamshipOffice, lot 2x3. Built from lt_designs/exchange.py."""
from lt_designs.exchange import build as design

ZONE = "ZO1"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=2, D=3, **{'storeys': 3, 'ground': 'arch', 'rust': True, 'order': 'columns', 'roof': 'hip', 'crown': 'pediment', 'back': 'court', 'back_mat': 'BuffBrick', 'main_d': 12.4, 'court_w': 4.4, 'palette': 'exchange'})
