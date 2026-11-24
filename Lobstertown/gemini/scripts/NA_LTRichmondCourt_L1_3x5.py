"""Lobstertown RichmondCourt, lot 3x5. Built from lt_designs/hydrostone.py."""
from lt_designs.hydrostone import build as design

ZONE = "ZR1"
HOUSEHOLDS = 36
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=5, **{'storeys': 4, 'plan': 'U_rear', 'depth_f': 0.58, 'court_f': 0.22, 'roof': 'hip', 'upper': 'Cream', 'roof_mat': 'SlateDark', 'door': 'GreyBlue', 'dormers': False, 'lots': [(2, 3), (2, 4), (3, 4), (3, 5), (4, 4), (4, 5)]})
