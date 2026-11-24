"""Lobstertown WoodfordsSquare, lot 2x2. Built from lt_designs/bungalows.py."""
from lt_designs.bungalows import build as design

ZONE = "ZL2"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, W=2, D=2, **{'kind': 'foursquare', 'porch_side': 'R', 'porch_frac': 0.6, 'md_off': 1.0, 'ell_side': 'L', 'ell_w': 0.44, 'gar_align': 'L', 'gar_w': 0.78, 'cd_off': -0.2, 'sun_w': 0.5, 'wall': 'ShingleSilver', 'base': 'Rubble', 'roof_mat': 'SlateDark', 'door': 'Oxblood', 'gar': 'gable', 'lots': [(2, 2), (2, 3), (2, 4), (3, 3), (3, 4)]})
