"""Lobstertown BathMansion, lot 2x4. Built from lt_designs/federal.py."""
from lt_designs.federal import build as design

ZONE = "ZP1"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, W=2, D=4, **{'palette': 'federal', 'kind': 'hip', 'storeys': 3, 'lantern': True, 'entry': 'fan', 'portico': False, 'shutters': 'Black', 'door': 'Black', 'ell': 'MID', 'woodshed': True, 'barn': 'cross', 'barn_h': 'LOW', 'lofts': True, 'wings': 'far'})
