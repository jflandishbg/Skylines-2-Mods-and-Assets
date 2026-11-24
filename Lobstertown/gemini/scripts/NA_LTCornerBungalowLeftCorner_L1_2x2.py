"""Lobstertown CornerBungalowLeftCorner, lot 2x2. Built from lt_designs/bungalows.py."""
from lt_designs.bungalows import build as design

ZONE = "ZL2"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, W=2, D=2, **{'kind': 'craftsman', 'porch_side': 'L', 'porch_frac': 0.52, 'md_off': -0.2, 'ell_side': 'L', 'ell_w': 0.6, 'gar_align': 'full', 'cd_off': 0.2, 'sun_w': 0.74, 'wall': 'ShingleGrey', 'base': 'Rubble', 'roof_mat': 'SlateGreen', 'door': 'Oxblood', 'gar': 'gable', 'corner': True, 'lots': [(2, 2), (2, 3), (2, 4), (3, 3), (3, 4)]})
