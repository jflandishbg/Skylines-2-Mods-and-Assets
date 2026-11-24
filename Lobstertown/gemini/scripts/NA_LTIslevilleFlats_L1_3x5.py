"""Lobstertown IslevilleFlats, lot 3x5. Built from lt_designs/hydrostone.py."""
from lt_designs.hydrostone import build as design

ZONE = "ZR1"
HOUSEHOLDS = 36
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=5, **{'storeys': 3, 'plan': 'U_front_L', 'depth_f': 0.33, 'court_f': 0.39, 'roof': 'gable', 'upper': 'ShingleSilver', 'roof_mat': 'SlateGreen', 'door': 'Green', 'dormers': True, 'lots': [(2, 3), (2, 4), (3, 4), (3, 5), (4, 4), (4, 5)]})
