"""Lobstertown AtlanticDutch, lot 2x3. Built from lt_designs/bungalows.py."""
from lt_designs.bungalows import build as design

ZONE = "ZL2"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, W=2, D=3, **{'kind': 'dutch', 'porch_side': 'none', 'md_off': 0.6, 'ell_side': 'L', 'ell_w': 0.54, 'gar_align': 'L', 'gar_w': 0.76, 'cd_off': 0.2, 'sun_w': 0.88, 'wall': 'ClapSage', 'base': 'Rubble', 'roof_mat': 'SlateDark', 'door': 'Black', 'gar': 'gable', 'lots': [(2, 2), (2, 3), (2, 4), (3, 3), (3, 4)]})
