"""Lobstertown FederalCornerLeftCorner, lot 2x4. Built from lt_designs/federal.py."""
from lt_designs.federal import build as design

ZONE = "ZP1"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, W=2, D=4, **{'palette': 'federal', 'kind': 'side', 'storeys': 3, 'brick_ends': 'Brick074', 'entry': 'fan', 'shutters': 'Black', 'door': 'Green', 'ell': 'LOW', 'barn': 'gambrel', 'barn_h': 'LOW', 'corner': True, 'lots': [(2, 4), (3, 4), (3, 5)]})
