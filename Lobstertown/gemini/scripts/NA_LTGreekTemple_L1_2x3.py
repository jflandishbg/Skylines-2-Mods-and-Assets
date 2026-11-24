"""Lobstertown GreekTemple, lot 2x3. Built from lt_designs/federal.py."""
from lt_designs.federal import build as design

ZONE = "ZP1"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, W=2, D=3, **{'palette': 'federal', 'kind': 'temple', 'storeys': 2, 'entry': 'side', 'portico': True, 'shutters': 'Green', 'door': 'Black', 'ell': 'LOW', 'barn': 'cross', 'barn_h': 'LOW', 'lofts': True})
