"""Lobstertown OceanViewLeftCorner, lot 4x4. Built from lt_designs/deco_towers.py."""
from lt_designs.deco_towers import build as design

ZONE = "ZH2"
HOUSEHOLDS = 36
PARTY_WALLS = ()


def build(lod):
    design(lod, W=4, D=4, **{'base_n': 5, 'mid_n': 5, 'top_n': 2, 'plan': 'H', 'depth_f': 0.52, 'court_f': 0.24, 'cap': 'pyramid', 'piers': True, 'arch': False, 'wall': 'Cream', 'base': 'Dressed', 'roof_mat': 'TinGreen', 'door': 'Iron', 'corner': True, 'lots': [(3, 4), (3, 5), (4, 4), (4, 5), (5, 5)]})
