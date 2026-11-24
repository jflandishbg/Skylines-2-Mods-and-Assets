"""Lobstertown DeeringFoursquare, lot 2x4. Built from lt_designs/bungalows.py."""
from lt_designs.bungalows import build as design

ZONE = "ZL2"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, W=2, D=4, **{'kind': 'foursquare', 'porch_side': 'full', 'md_off': 0.4, 'ell_side': 'R', 'ell_w': 0.5, 'gar_align': 'R', 'gar_w': 0.76, 'cd_off': 0.0, 'sun_w': 0.7, 'wall': 'Clapboard', 'base': 'Greystone', 'roof_mat': 'SlateGreen', 'door': 'Green', 'gar': 'hip', 'lots': [(2, 2), (2, 3), (2, 4), (3, 3), (3, 4)]})
