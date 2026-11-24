"""Lobstertown HydrostoneCornerLeftCorner, lot 3x5. Built from lt_designs/hydrostone.py."""
from lt_designs.hydrostone import build as design

ZONE = "ZR1"
HOUSEHOLDS = 36
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=5, **{'storeys': 3, 'plan': 'L_left', 'depth_f': 0.48, 'court_f': 0.36, 'roof': 'gable', 'upper': 'Cream', 'roof_mat': 'SlateDark', 'door': 'Green', 'dormers': True, 'corner': True, 'lots': [(2, 4), (3, 4), (3, 5), (4, 5)]})
