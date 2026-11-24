"""Lobstertown CapeDouble, lot 3x6. Built from lt_designs/federal.py."""
from lt_designs.federal import build as design

ZONE = "ZP2"
HOUSEHOLDS = 7
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=6, **{'palette': 'federal', 'kind': 'cape', 'doors': 2, 'dormers': True, 'entry': 'fan', 'shutters': 'Black', 'door': 'Green', 'ell': 'LOW', 'barn': 'gable', 'barn_h': 'MID', 'lofts': False, 'flats': True, 'wings': 'far'})
