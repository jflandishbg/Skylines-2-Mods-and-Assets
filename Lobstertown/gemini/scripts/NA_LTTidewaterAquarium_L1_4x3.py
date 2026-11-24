"""Lobstertown TidewaterAquarium, lot 4x3. Built from lt_designs/landmarks.py."""
from lt_designs.landmarks import build as design

ZONE = "ZS2"
HOUSEHOLDS = 0
PARTY_WALLS = ()


def build(lod):
    design(lod, W=4, D=3, **{'lot': (4, 3), 'kind': 'aquarium'})
