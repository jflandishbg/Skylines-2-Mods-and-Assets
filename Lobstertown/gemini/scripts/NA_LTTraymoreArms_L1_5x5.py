"""Lobstertown TraymoreArms, lot 5x5. Built from lt_designs/deco_towers.py."""
from lt_designs.deco_towers import build as design

ZONE = "ZH2"
HOUSEHOLDS = 58
PARTY_WALLS = ()


def build(lod):
    design(lod, W=5, D=5, **{'base_n': 5, 'mid_n': 4, 'top_n': 2, 'plan': 'T', 'depth_f': 0.48, 'court_f': 0.18, 'cap': 'dome', 'piers': True, 'arch': True, 'wall': 'Render', 'base': 'Dressed', 'roof_mat': 'TinGreen', 'door': 'Iron', 'lots': [(3, 4), (3, 5), (4, 4), (4, 5), (5, 5)]})
