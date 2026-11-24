"""Lobstertown WalrusBathhouse, lot 5x4. Built from lt_designs/landmarks.py."""
from lt_designs.landmarks import build as design

ZONE = "ZS2"
HOUSEHOLDS = 0
PARTY_WALLS = ()


def build(lod):
    design(lod, W=5, D=4, **{'lot': (5, 4), 'kind': 'walrus'})
