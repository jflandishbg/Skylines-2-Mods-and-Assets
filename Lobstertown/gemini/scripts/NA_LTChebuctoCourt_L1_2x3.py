"""Lobstertown ChebuctoCourt, lot 2x3. Built from lt_designs/hydrostone.py."""
from lt_designs.hydrostone import build as design

ZONE = "ZR1"
HOUSEHOLDS = 18
PARTY_WALLS = ()


def build(lod):
    design(lod, W=2, D=3, **{'storeys': 3, 'plan': 'L_right', 'depth_f': 0.56, 'court_f': 0.34, 'roof': 'hip', 'upper': 'ShingleSilver', 'roof_mat': 'SlateDark', 'door': 'GreyBlue', 'dormers': False, 'lots': [(2, 3), (2, 4), (3, 4), (3, 5), (4, 4), (4, 5)]})
