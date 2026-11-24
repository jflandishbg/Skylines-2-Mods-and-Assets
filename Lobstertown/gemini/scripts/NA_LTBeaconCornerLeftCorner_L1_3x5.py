"""Lobstertown BeaconCornerLeftCorner, lot 3x5. Built from lt_designs/deco_towers.py."""
from lt_designs.deco_towers import build as design

ZONE = "ZH2"
HOUSEHOLDS = 32
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=5, **{'base_n': 5, 'mid_n': 5, 'top_n': 3, 'plan': 'L_left', 'depth_f': 0.46, 'court_f': 0.38, 'cap': 'hip', 'piers': True, 'arch': True, 'wall': 'BuffBrick', 'base': 'Dressed', 'roof_mat': 'TinGreen', 'door': 'Iron', 'corner': True, 'lots': [(3, 4), (3, 5), (4, 4), (4, 5), (5, 5)]})
