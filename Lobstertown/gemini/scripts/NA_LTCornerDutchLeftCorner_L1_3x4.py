"""Lobstertown CornerDutchLeftCorner, lot 3x4. Built from lt_designs/bungalows.py."""
from lt_designs.bungalows import build as design

ZONE = "ZL2"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=4, **{'kind': 'dutch', 'porch_side': 'none', 'md_off': 0.0, 'ell_side': 'R', 'ell_w': 0.58, 'gar_align': 'R', 'gar_w': 0.82, 'cd_off': -0.4, 'sun_w': 0.72, 'wall': 'ShingleSilver', 'base': 'Rubble', 'roof_mat': 'SlateGreen', 'door': 'Green', 'gar': 'hip', 'corner': True, 'lots': [(2, 2), (2, 3), (2, 4), (3, 3), (3, 4)]})
