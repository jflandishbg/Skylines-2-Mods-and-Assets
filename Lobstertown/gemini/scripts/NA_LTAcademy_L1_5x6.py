"""Lobstertown Academy, lot 5x6. Built from lt_designs/civic.py."""
from lt_designs.civic import build as design

ZONE = "ZS1"
HOUSEHOLDS = 0
PARTY_WALLS = ()


def build(lod):
    design(lod, W=5, D=6, **{'lot': (5, 6), 'storeys': 3, 'tower': 'clock', 'wing': 'twin', 'depth': 14.0})
