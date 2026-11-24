"""Lobstertown BrickRow, lot 3x6. Built from lt_designs/federal.py."""
from lt_designs.federal import build as design

ZONE = "ZP2"
HOUSEHOLDS = 7
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=6, **{'palette': 'federal', 'kind': 'side', 'storeys': 3, 'units': 3, 'brick': 'Brick074', 'entry': 'fan', 'shutters': 'Black', 'door': 'Green', 'ell': 'MID', 'barn': 'gable', 'barn_h': 'MID', 'cupola': True, 'flats': True})
