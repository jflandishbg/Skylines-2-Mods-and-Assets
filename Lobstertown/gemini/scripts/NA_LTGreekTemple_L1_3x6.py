"""Lobstertown GreekTemple, lot 3x6. Built from lt_designs/federal.py."""
from lt_designs.federal import build as design

ZONE = "ZP1"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=6, **{'palette': 'federal', 'kind': 'temple', 'storeys': 2, 'entry': 'side', 'portico': True, 'shutters': 'Green', 'door': 'Black', 'ell': 'LOW', 'barn': 'cross', 'barn_h': 'LOW', 'lofts': True})
