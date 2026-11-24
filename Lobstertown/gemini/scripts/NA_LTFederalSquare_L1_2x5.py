"""Lobstertown FederalSquare, lot 2x5. Built from lt_designs/federal.py."""
from lt_designs.federal import build as design

ZONE = "ZP1"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, W=2, D=5, **{'palette': 'federal', 'kind': 'side', 'storeys': 3, 'brick': 'Brick054', 'walk': True, 'entry': 'fan', 'shutters': 'Green', 'door': 'Black', 'ell': 'MID', 'barn': 'gambrel', 'barn_h': 'MID', 'wings': 'twin'})
