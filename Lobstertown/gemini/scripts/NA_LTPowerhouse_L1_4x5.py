"""Lobstertown Powerhouse, lot 4x5. Built from lt_designs/civic.py."""
from lt_designs.civic import build as design

ZONE = "ZS1"
HOUSEHOLDS = 0
PARTY_WALLS = ()


def build(lod):
    design(lod, W=4, D=5, **{'lot': (4, 5), 'storeys': 2, 'stacks': 2, 'wing': 'mid', 'depth': 14.0})
