"""Lobstertown AtlanticTower, lot 5x6. Built from lt_designs/cottage.py."""
from lt_designs.cottage import build as design

ZONE = "ZP3"
HOUSEHOLDS = 55
PARTY_WALLS = ()


def build(lod):
    design(lod, W=5, D=6, **{'hotel': True, 'sign': 'TheAtlantic', 'storeys': 14, 'roof': 'gambrel', 'turret': True, 'cross': True, 'base': 'Greystone', 'wall': 'ShingleSilver', 'gable_mat': 'ShingleGrey', 'roof_mat': 'TinOxide', 'door': 'Black', 'lites': '2', 'car': 'gable', 'cupola': True, 'wing': 'twin', 'lantern': False, 'pavilions': ((0.5, 4, 'dome'),), 'spire': 2})
