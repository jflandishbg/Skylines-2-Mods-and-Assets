"""Lobstertown GeneralHospital, lot 6x5. Built from lt_designs/civic.py."""
from lt_designs.civic import build as design

ZONE = "ZS1"
HOUSEHOLDS = 0
PARTY_WALLS = ()


def build(lod):
    design(lod, W=6, D=5, **{'lot': (6, 5), 'storeys': 3, 'ground': 'square', 'porch': True, 'vbays': 3, 'cupola': True, 'wing': 'wards', 'depth': 15.0, 'set': 2.1})
