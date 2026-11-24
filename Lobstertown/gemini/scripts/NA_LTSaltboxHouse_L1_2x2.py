"""Lobstertown SaltboxHouse, lot 2x2. Built from lt_designs/bungalows.py."""
from lt_designs.bungalows import build as design

ZONE = "ZL2"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, W=2, D=2, **{'kind': 'saltbox', 'porch_side': 'L', 'porch_frac': 0.44, 'md_off': 0.6, 'ell_side': 'R', 'ell_w': 0.44, 'gar_align': 'L', 'gar_w': 0.8, 'cd_off': 0.4, 'sun_w': 0.76, 'wall': 'ShingleGrey', 'base': 'Greystone', 'roof_mat': 'SlateGreen', 'door': 'Black', 'gar': 'hip', 'lots': [(2, 2), (2, 3), (2, 4), (3, 3), (3, 4)]})
