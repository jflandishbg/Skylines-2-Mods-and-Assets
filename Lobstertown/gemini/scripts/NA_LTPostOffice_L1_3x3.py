"""Lobstertown PostOffice, lot 3x3. Built from lt_designs/civic.py."""
from lt_designs.civic import build as design

ZONE = "ZS1"
HOUSEHOLDS = 0
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=3, **{'lot': (3, 3), 'storeys': 1, 'roof': 'gable', 'turret': 'right', 'vbays': 1, 'wing': 'low', 'depth': 11.0})
