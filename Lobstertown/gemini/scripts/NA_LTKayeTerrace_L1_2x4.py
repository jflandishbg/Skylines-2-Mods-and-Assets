"""Lobstertown KayeTerrace, lot 2x4. Built from lt_designs/hydrostone.py."""
from lt_designs.hydrostone import build as design

ZONE = "ZR1"
HOUSEHOLDS = 24
PARTY_WALLS = ()


def build(lod):
    design(lod, W=2, D=4, **{'storeys': 4, 'plan': 'H', 'depth_f': 0.36, 'court_f': 0.22, 'roof': 'flat', 'upper': 'Dressed', 'roof_mat': 'SlateDark', 'door': 'Black', 'dormers': False, 'lots': [(2, 3), (2, 4), (3, 4), (3, 5), (4, 4), (4, 5)]})
