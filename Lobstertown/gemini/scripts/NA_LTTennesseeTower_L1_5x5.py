"""Lobstertown TennesseeTower, lot 5x5. Built from lt_designs/cottage.py."""
from lt_designs.cottage import build as design

ZONE = "ZP3"
HOUSEHOLDS = 46
PARTY_WALLS = ()


def build(lod):
    design(lod, W=5, D=5, **{'hotel': True, 'sign': 'TheTennessee', 'storeys': 12, 'roof': 'gable', 'turret': True, 'cross': False, 'hand': 'R', 'wall': 'ShingleGrey', 'gable_mat': 'ShingleSilver', 'roof_mat': 'TinOxide', 'door': 'Green', 'lites': '6', 'car': 'gambrel', 'wing': 'near', 'lantern': True, 'pavilions': ((1.0, 3, 'hip'),), 'spire': 3})
