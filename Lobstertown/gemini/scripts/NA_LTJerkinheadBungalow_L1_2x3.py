"""Lobstertown JerkinheadBungalow, lot 2x3. Built from lt_designs/bungalows.py."""
from lt_designs.bungalows import build as design

ZONE = "ZL2"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, W=2, D=3, **{'kind': 'jerkinhead', 'porch_side': 'R', 'porch_frac': 0.5, 'md_off': 0.6, 'ell_side': 'C', 'ell_w': 0.48, 'gar_align': 'full', 'cd_off': 0.4, 'sun_w': 0.84, 'wall': 'ClapSage', 'base': 'StoneBase', 'roof_mat': 'SlateDark', 'door': 'Oxblood', 'gar': 'gable', 'lots': [(2, 2), (2, 3), (2, 4), (3, 3), (3, 4)]})
