"""Lobstertown ExhibitionHall, lot 6x5. Built from lt_designs/landmarks.py."""
from lt_designs.landmarks import build as design

ZONE = "ZS2"
HOUSEHOLDS = 0
PARTY_WALLS = ()


def build(lod):
    design(lod, W=6, D=5, **{'lot': (6, 5), 'kind': 'hall'})
