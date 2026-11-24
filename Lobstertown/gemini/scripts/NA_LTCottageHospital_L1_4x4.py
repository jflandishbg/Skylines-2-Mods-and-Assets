"""Lobstertown CottageHospital, lot 4x4. Built from lt_designs/civic.py."""
from lt_designs.civic import build as design

ZONE = "ZS1"
HOUSEHOLDS = 0
PARTY_WALLS = ()


def build(lod):
    design(lod, W=4, D=4, **{'lot': (4, 4), 'storeys': 2, 'ground': 'square', 'porch': True, 'vbays': 2, 'wing': 'twin', 'depth': 12.0, 'set': 2.1})
