"""Lobstertown GreekPorch, lot 3x5. Built from lt_designs/federal.py."""
from lt_designs.federal import build as design

ZONE = "ZP1"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=5, **{'palette': 'federal', 'kind': 'temple', 'storeys': 2, 'entry': 'side', 'porch': True, 'shutters': 'Black', 'door': 'Green', 'ell': 'LOW', 'barn': 'gambrel', 'barn_h': 'LOW', 'cupola': True})
