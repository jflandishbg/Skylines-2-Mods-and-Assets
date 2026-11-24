"""Lobstertown EastlandCourt, lot 3x4. Built from lt_designs/deco_towers.py."""
from lt_designs.deco_towers import build as design

ZONE = "ZH2"
HOUSEHOLDS = 26
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=4, **{'base_n': 6, 'mid_n': 4, 'top_n': 2, 'plan': 'U', 'depth_f': 0.38, 'court_f': 0.36, 'cap': 'pyramid', 'piers': False, 'arch': True, 'wall': 'Cream', 'base': 'Greystone', 'roof_mat': 'SlateDark', 'door': 'Iron', 'lots': [(3, 4), (3, 5), (4, 4), (4, 5), (5, 5)]})
