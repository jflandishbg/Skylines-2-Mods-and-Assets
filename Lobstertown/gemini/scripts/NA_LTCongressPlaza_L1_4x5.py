"""Lobstertown CongressPlaza, lot 4x5. Built from lt_designs/deco_towers.py."""
from lt_designs.deco_towers import build as design

ZONE = "ZH2"
HOUSEHOLDS = 46
PARTY_WALLS = ()


def build(lod):
    design(lod, W=4, D=5, **{'base_n': 4, 'mid_n': 5, 'top_n': 3, 'plan': 'H', 'depth_f': 0.38, 'court_f': 0.27, 'cap': 'pyramid', 'piers': True, 'arch': False, 'wall': 'BuffBrick', 'base': 'Greystone', 'roof_mat': 'TinGreen', 'door': 'Iron', 'lots': [(3, 4), (3, 5), (4, 4), (4, 5), (5, 5)]})
