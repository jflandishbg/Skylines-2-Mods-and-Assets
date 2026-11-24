"""Lobstertown GreekFlats, lot 4x6. Built from lt_designs/federal.py."""
from lt_designs.federal import build as design

ZONE = "ZP2"
HOUSEHOLDS = 10
PARTY_WALLS = ()


def build(lod):
    design(lod, W=4, D=6, **{'palette': 'federal', 'kind': 'temple', 'storeys': 3, 'entry': 'side', 'porch': True, 'shutters': 'Black', 'door': 'Black', 'ell': 'MID', 'barn': 'gable', 'barn_h': 'MID', 'cupola': True, 'flats': True})
