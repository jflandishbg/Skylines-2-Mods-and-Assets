"""Lobstertown FederalDouble, lot 4x5. Built from lt_designs/federal.py."""
from lt_designs.federal import build as design

ZONE = "ZP2"
HOUSEHOLDS = 8
PARTY_WALLS = ()


def build(lod):
    design(lod, W=4, D=5, **{'palette': 'federal', 'kind': 'side', 'storeys': 3, 'doors': 2, 'entry': 'fan', 'shutters': 'Green', 'door': 'Black', 'ell': 'MID', 'wings': 'twin', 'barn': 'gable', 'barn_h': 'MID', 'flats': True})
