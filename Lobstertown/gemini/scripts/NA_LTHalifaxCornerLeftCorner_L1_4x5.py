"""Lobstertown HalifaxCornerLeftCorner, lot 4x5. Built from lt_designs/hydrostone.py."""
from lt_designs.hydrostone import build as design

ZONE = "ZR1"
HOUSEHOLDS = 46
PARTY_WALLS = ()


def build(lod):
    design(lod, W=4, D=5, **{'storeys': 4, 'plan': 'U_front', 'depth_f': 0.36, 'court_f': 0.28, 'roof': 'hip', 'upper': 'Greystone', 'roof_mat': 'Slate', 'door': 'Oxblood', 'dormers': False, 'corner': True, 'lots': [(2, 4), (3, 4), (3, 5), (4, 5)]})
