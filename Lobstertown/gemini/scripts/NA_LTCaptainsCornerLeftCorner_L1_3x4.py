"""Lobstertown CaptainsCornerLeftCorner, lot 3x4. Built from lt_designs/federal.py."""
from lt_designs.federal import build as design

ZONE = "ZP1"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=4, **{'palette': 'federal', 'kind': 'hip', 'storeys': 2, 'walk': True, 'entry': 'fan', 'shutters': 'Green', 'door': 'Black', 'ell': 'MID', 'barn': 'gable', 'barn_h': 'MID', 'cupola': True, 'corner': True, 'lots': [(2, 4), (3, 4), (3, 5)]})
