"""Lobstertown BathCraftsman, lot 2x2. Built from lt_designs/bungalows.py."""
from lt_designs.bungalows import build as design

ZONE = "ZL2"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, W=2, D=2, **{'kind': 'craftsman', 'porch_side': 'L', 'porch_frac': 0.46, 'md_off': 0.8, 'ell_side': 'C', 'ell_w': 0.56, 'gar_align': 'full', 'cd_off': -0.4, 'sun_w': 0.54, 'wall': 'Clapboard', 'base': 'Greystone', 'roof_mat': 'SlateGreen', 'door': 'Green', 'gar': 'hip', 'lots': [(2, 2), (2, 3), (2, 4), (3, 3), (3, 4)]})
