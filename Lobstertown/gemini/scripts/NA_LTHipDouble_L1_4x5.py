"""Lobstertown HipDouble, lot 4x5. Built from lt_designs/federal.py."""
from lt_designs.federal import build as design

ZONE = "ZP2"
HOUSEHOLDS = 8
PARTY_WALLS = ()


def build(lod):
    design(lod, W=4, D=5, **{'palette': 'federal', 'kind': 'hip', 'storeys': 3, 'doors': 2, 'walk': True, 'entry': 'fan', 'shutters': 'Black', 'door': 'Black', 'ell': 'MID', 'wings': 'twin', 'barn': 'cross', 'barn_h': 'MID', 'flats': True})
