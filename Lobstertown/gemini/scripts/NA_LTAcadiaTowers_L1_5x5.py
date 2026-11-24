"""Lobstertown AcadiaTowers, lot 5x5. Built from lt_designs/deco_towers.py."""
from lt_designs.deco_towers import build as design

ZONE = "ZH2"
HOUSEHOLDS = 58
PARTY_WALLS = ()


def build(lod):
    design(lod, W=5, D=5, **{'base_n': 5, 'mid_n': 6, 'top_n': 2, 'plan': 'L_left', 'depth_f': 0.56, 'court_f': 0.3, 'cap': 'hip', 'piers': True, 'arch': True, 'wall': 'Cream', 'base': 'Dressed', 'roof_mat': 'TinGreen', 'door': 'Iron', 'lots': [(3, 4), (3, 5), (4, 4), (4, 5), (5, 5)]})
