"""Lobstertown FireStation, lot 4x4. Built from lt_designs/civic.py."""
from lt_designs.civic import build as design

ZONE = "ZS1"
HOUSEHOLDS = 0
PARTY_WALLS = ()


def build(lod):
    design(lod, W=4, D=4, **{'lot': (4, 4), 'storeys': 2, 'engines': 3, 'tower': 'hose', 'wing': 'low', 'depth': 13.0})
