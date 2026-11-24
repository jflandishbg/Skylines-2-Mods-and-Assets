"""Lobstertown OfficeCourt, lot 4x5. Built from lt_designs/motorcourt.py."""
from lt_designs.motorcourt import build as design

ZONE = "ZP4"
HOUSEHOLDS = 8
PARTY_WALLS = ()


def build(lod):
    design(lod, W=4, D=5, **{'layout': 'R', 'wall': 'ClapSage', 'office_wall': 'Rubble', 'roof_mat': 'TinOxide', 'door': 'GreyBlue'})
