"""Lobstertown CornerGableLeftCorner, lot 3x3. Built from lt_designs/bungalows.py."""
from lt_designs.bungalows import build as design

ZONE = "ZL2"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=3, **{'kind': 'gable_front', 'porch_side': 'L', 'porch_frac': 0.54, 'md_off': 0.6, 'ell_side': 'twin', 'ell_w': 0.44, 'gar_align': 'full', 'cd_off': -0.2, 'sun_w': 0.6, 'wall': 'Clapboard', 'base': 'Greystone', 'roof_mat': 'SlateDark', 'door': 'Oxblood', 'gar': 'gable', 'corner': True, 'lots': [(2, 2), (2, 3), (2, 4), (3, 3), (3, 4)]})
