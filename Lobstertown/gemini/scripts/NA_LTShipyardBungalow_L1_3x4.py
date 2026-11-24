"""Lobstertown ShipyardBungalow, lot 3x4. Built from lt_designs/bungalows.py."""
from lt_designs.bungalows import build as design

ZONE = "ZL2"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=4, **{'kind': 'craftsman', 'porch_side': 'L', 'porch_frac': 0.58, 'md_off': 0.0, 'ell_side': 'L', 'ell_w': 0.48, 'gar_align': 'full', 'cd_off': -0.2, 'sun_w': 0.62, 'wall': 'ShingleGrey', 'base': 'Rubble', 'roof_mat': 'SlateDark', 'door': 'Oxblood', 'gar': 'gable', 'lots': [(2, 2), (2, 3), (2, 4), (3, 3), (3, 4)]})
