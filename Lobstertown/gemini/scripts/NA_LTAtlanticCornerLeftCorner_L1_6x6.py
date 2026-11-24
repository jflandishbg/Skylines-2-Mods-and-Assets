"""Lobstertown AtlanticCornerLeftCorner, lot 6x6. Built from lt_designs/cottage.py."""
from lt_designs.cottage import build as design

ZONE = "ZP3"
HOUSEHOLDS = 70
PARTY_WALLS = ()


def build(lod):
    design(lod, W=6, D=6, **{'hotel': True, 'storeys': 14, 'roof': 'gambrel', 'turret': True, 'cross': True, 'corner': True, 'base': 'Greystone', 'wall': 'ShingleSilver', 'gable_mat': 'ShingleGrey', 'roof_mat': 'TinOxide', 'door': 'Black', 'lites': '2', 'car': 'gable', 'cupola': True, 'pavilions': ((0.5, 4, 'dome'),), 'spire': 2, 'lots': [(4, 5), (5, 5), (5, 6), (6, 6)]})
