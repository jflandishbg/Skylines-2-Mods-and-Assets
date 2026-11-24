"""Lobstertown BrickEndFederal, lot 3x6. Built from lt_designs/federal.py."""
from lt_designs.federal import build as design

ZONE = "ZP1"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=6, **{'palette': 'federal', 'kind': 'side', 'storeys': 2, 'brick_ends': 'Brick074', 'entry': 'fan', 'portico': True, 'shutters': 'Black', 'door': 'Green', 'ell': 'LOW', 'barn': 'gambrel', 'barn_h': 'LOW'})
