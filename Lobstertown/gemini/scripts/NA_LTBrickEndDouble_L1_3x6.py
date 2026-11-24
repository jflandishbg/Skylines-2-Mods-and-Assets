"""Lobstertown BrickEndDouble, lot 3x6. Built from lt_designs/federal.py."""
from lt_designs.federal import build as design

ZONE = "ZP2"
HOUSEHOLDS = 7
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=6, **{'palette': 'federal', 'kind': 'side', 'storeys': 3, 'doors': 2, 'brick_ends': 'Brick054', 'entry': 'fan', 'shutters': 'Green', 'door': 'Black', 'ell': 'MID', 'barn': 'gambrel', 'barn_h': 'MID', 'flats': True})
