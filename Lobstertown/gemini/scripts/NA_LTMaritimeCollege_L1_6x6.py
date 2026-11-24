"""Lobstertown MaritimeCollege, lot 6x6. Built from lt_designs/civic.py."""
from lt_designs.civic import build as design

ZONE = "ZS1"
HOUSEHOLDS = 0
PARTY_WALLS = ()


def build(lod):
    design(lod, W=6, D=6, **{'lot': (6, 6), 'storeys': 3, 'roof': 'hip', 'turret': 'left', 'tower': 'clock', 'wing': 'quad', 'depth': 16.0})
