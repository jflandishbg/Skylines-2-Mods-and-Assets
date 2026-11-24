"""Lobstertown CascoArms, lot 3x5. Built from lt_designs/deco_towers.py."""
from lt_designs.deco_towers import build as design

ZONE = "ZH2"
HOUSEHOLDS = 32
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=5, **{'base_n': 4, 'mid_n': 5, 'top_n': 3, 'plan': 'C_right', 'depth_f': 0.5, 'court_f': 0.39, 'cap': 'dome', 'piers': False, 'arch': True, 'wall': 'RevealStone', 'base': 'Greystone', 'roof_mat': 'SlateGreen', 'door': 'Iron', 'lots': [(3, 4), (3, 5), (4, 4), (4, 5), (5, 5)]})
