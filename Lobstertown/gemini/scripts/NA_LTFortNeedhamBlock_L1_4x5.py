"""Lobstertown FortNeedhamBlock, lot 4x5. Built from lt_designs/hydrostone.py."""
from lt_designs.hydrostone import build as design

ZONE = "ZR1"
HOUSEHOLDS = 46
PARTY_WALLS = ()


def build(lod):
    design(lod, W=4, D=5, **{'storeys': 3, 'plan': 'T', 'depth_f': 0.48, 'court_f': 0.19, 'roof': 'gable', 'upper': 'Greystone', 'roof_mat': 'SlateGreen', 'door': 'Oxblood', 'dormers': True, 'lots': [(2, 3), (2, 4), (3, 4), (3, 5), (4, 4), (4, 5)]})
