"""Lobstertown HarbourDecoLeftCorner, lot 4x5. Built from lt_designs/deco_towers.py."""
from lt_designs.deco_towers import build as design

ZONE = "ZH2"
HOUSEHOLDS = 46
PARTY_WALLS = ()


def build(lod):
    design(lod, W=4, D=5, **{'base_n': 4, 'mid_n': 6, 'top_n': 2, 'plan': 'C_right', 'depth_f': 0.42, 'court_f': 0.31, 'cap': 'step', 'piers': True, 'arch': False, 'wall': 'TrimWhite', 'base': 'Greystone', 'roof_mat': 'SlateDark', 'door': 'Iron', 'corner': True, 'lots': [(3, 4), (3, 5), (4, 4), (4, 5), (5, 5)]})
