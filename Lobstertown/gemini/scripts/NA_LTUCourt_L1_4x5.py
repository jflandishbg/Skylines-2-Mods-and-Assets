"""Lobstertown UCourt, lot 4x5. Built from lt_designs/motorcourt.py."""
from lt_designs.motorcourt import build as design

ZONE = "ZP4"
HOUSEHOLDS = 9
PARTY_WALLS = ()


def build(lod):
    design(lod, W=4, D=5, **{'layout': 'U', 'wall': 'ShingleGrey', 'office_wall': 'Clapboard', 'roof_mat': 'SlateDark', 'door': 'Green'})
