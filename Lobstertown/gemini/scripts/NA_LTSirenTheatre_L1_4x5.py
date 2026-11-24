"""Lobstertown SirenTheatre, lot 4x5. Built from lt_designs/landmarks.py."""
from lt_designs.landmarks import build as design

ZONE = "ZS2"
HOUSEHOLDS = 0
PARTY_WALLS = ()


def build(lod):
    design(lod, W=4, D=5, **{'lot': (4, 5), 'kind': 'theatre'})
