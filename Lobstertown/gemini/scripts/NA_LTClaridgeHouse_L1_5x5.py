"""Lobstertown ClaridgeHouse, lot 5x5. Built from lt_designs/deco_towers.py."""
from lt_designs.deco_towers import build as design

ZONE = "ZH2"
HOUSEHOLDS = 58
PARTY_WALLS = ()


def build(lod):
    design(lod, W=5, D=5, **{'base_n': 5, 'mid_n': 5, 'top_n': 2, 'plan': 'U', 'depth_f': 0.5, 'court_f': 0.28, 'cap': 'hip', 'piers': True, 'arch': True, 'wall': 'BuffBrick', 'base': 'Dressed', 'roof_mat': 'TinGreen', 'door': 'Iron', 'lots': [(3, 4), (3, 5), (4, 4), (4, 5), (5, 5)]})
