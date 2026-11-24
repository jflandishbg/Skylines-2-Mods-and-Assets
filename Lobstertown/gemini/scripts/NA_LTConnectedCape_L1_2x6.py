"""Lobstertown ConnectedCape, lot 2x6. Built from lt_designs/federal.py."""
from lt_designs.federal import build as design

ZONE = "ZP1"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, W=2, D=6, **{'palette': 'federal', 'kind': 'cape', 'dormers': True, 'entry': 'fan', 'shutters': 'Green', 'door': 'Green', 'lites': '6', 'ell': 'LOW', 'barn': 'gable', 'barn_h': 'LOW', 'cupola': True, 'lofts': True})
