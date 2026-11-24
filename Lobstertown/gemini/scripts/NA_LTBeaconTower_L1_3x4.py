"""Lobstertown BeaconTower, lot 3x4. Built from lt_designs/deco_towers.py."""
from lt_designs.deco_towers import build as design

ZONE = "ZH2"
HOUSEHOLDS = 26
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=4, **{'base_n': 4, 'mid_n': 6, 'top_n': 3, 'plan': 'H', 'depth_f': 0.44, 'court_f': 0.2, 'cap': 'step', 'piers': True, 'arch': False, 'wall': 'TrimWhite', 'base': 'Greystone', 'roof_mat': 'SlateDark', 'door': 'Iron', 'lots': [(3, 4), (3, 5), (4, 4), (4, 5), (5, 5)]})
