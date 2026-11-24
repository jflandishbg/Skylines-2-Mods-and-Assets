"""Lobstertown GreekTwin, lot 3x6. Built from lt_designs/federal.py."""
from lt_designs.federal import build as design

ZONE = "ZP2"
HOUSEHOLDS = 7
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=6, **{'palette': 'federal', 'kind': 'twin', 'storeys': 3, 'entry': 'side', 'shutters': 'Green', 'door': 'Black', 'ell': 'MID', 'wings': 'twin', 'barn': 'gambrel', 'barn_h': 'MID', 'flats': True})
