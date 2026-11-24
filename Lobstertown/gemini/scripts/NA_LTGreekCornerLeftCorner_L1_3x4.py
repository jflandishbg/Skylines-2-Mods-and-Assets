"""Lobstertown GreekCornerLeftCorner, lot 3x4. Built from lt_designs/federal.py."""
from lt_designs.federal import build as design

ZONE = "ZP1"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=4, **{'palette': 'federal', 'kind': 'temple', 'storeys': 2, 'entry': 'side', 'shutters': 'Black', 'door': 'Black', 'ell': 'LOW', 'barn': 'cross', 'barn_h': 'LOW', 'lofts': True, 'corner': True, 'lots': [(2, 4), (3, 4), (3, 5)]})
