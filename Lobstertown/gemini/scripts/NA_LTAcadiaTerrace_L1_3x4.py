"""Lobstertown AcadiaTerrace, lot 3x4. Built from lt_designs/hydrostone.py."""
from lt_designs.hydrostone import build as design

ZONE = "ZR1"
HOUSEHOLDS = 30
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=4, **{'storeys': 4, 'plan': 'C_mirror', 'depth_f': 0.44, 'court_f': 0.3, 'roof': 'gable', 'upper': 'Dressed', 'roof_mat': 'Slate', 'door': 'Green', 'dormers': True, 'lots': [(2, 3), (2, 4), (3, 4), (3, 5), (4, 4), (4, 5)]})
