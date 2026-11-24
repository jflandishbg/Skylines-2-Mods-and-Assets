"""Lobstertown OrientalCornerLeftCorner, lot 5x5. Built from lt_designs/cottage.py."""
from lt_designs.cottage import build as design

ZONE = "ZP3"
HOUSEHOLDS = 46
PARTY_WALLS = ()


def build(lod):
    design(lod, W=5, D=5, **{'hotel': True, 'storeys': 16, 'roof': 'gambrel', 'turret': True, 'cross': True, 'corner': True, 'base': 'Rubble', 'wall': 'Clapboard', 'gable_mat': 'ShingleSilver', 'roof_mat': 'TinOxide', 'door': 'Oxblood', 'lites': '2', 'car': 'cross', 'lofts': True, 'pavilions': ((0.5, 4, 'hip'),), 'spire': 3, 'lots': [(4, 5), (5, 5), (5, 6), (6, 6)]})
