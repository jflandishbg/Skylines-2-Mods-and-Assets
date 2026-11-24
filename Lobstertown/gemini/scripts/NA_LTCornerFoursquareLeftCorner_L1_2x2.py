"""Lobstertown CornerFoursquareLeftCorner, lot 2x2. Built from lt_designs/bungalows.py."""
from lt_designs.bungalows import build as design

ZONE = "ZL2"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, W=2, D=2, **{'kind': 'foursquare', 'porch_side': 'full', 'md_off': 0.0, 'ell_side': 'twin', 'ell_w': 0.48, 'gar_align': 'R', 'gar_w': 0.78, 'cd_off': 0.4, 'sun_w': 0.66, 'wall': 'Clapboard', 'base': 'Greystone', 'roof_mat': 'SlateDark', 'door': 'Green', 'gar': 'hip', 'corner': True, 'lots': [(2, 2), (2, 3), (2, 4), (3, 3), (3, 4)]})
