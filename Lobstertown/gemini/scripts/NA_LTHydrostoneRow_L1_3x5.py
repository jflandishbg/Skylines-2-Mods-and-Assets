"""Lobstertown HydrostoneRow, lot 3x5. Built from lt_designs/hydrostone.py."""
from lt_designs.hydrostone import build as design

ZONE = "ZR1"
HOUSEHOLDS = 36
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=5, **{'storeys': 3, 'plan': 'U_rear', 'depth_f': 0.44, 'court_f': 0.32, 'roof': 'gable', 'upper': 'Cream', 'roof_mat': 'SlateDark', 'door': 'Green', 'dormers': True, 'lots': [(2, 3), (2, 4), (3, 4), (3, 5), (4, 4), (4, 5)]})
