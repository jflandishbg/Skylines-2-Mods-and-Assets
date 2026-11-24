"""Lobstertown HipDouble, lot 3x6. Built from lt_designs/federal.py."""
from lt_designs.federal import build as design

ZONE = "ZP2"
HOUSEHOLDS = 7
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=6, **{'palette': 'federal', 'kind': 'hip', 'storeys': 3, 'doors': 2, 'walk': True, 'entry': 'fan', 'shutters': 'Black', 'door': 'Black', 'ell': 'MID', 'wings': 'twin', 'barn': 'cross', 'barn_h': 'MID', 'flats': True})
