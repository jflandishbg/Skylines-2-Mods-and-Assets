"""Lobstertown NewYorkTower, lot 4x5. Built from lt_designs/cottage.py."""
from lt_designs.cottage import build as design

ZONE = "ZP3"
HOUSEHOLDS = 34
PARTY_WALLS = ()


def build(lod):
    design(lod, W=4, D=5, **{'hotel': True, 'sign': 'TheNewYork', 'storeys': 14, 'roof': 'gable', 'turret': False, 'cross': True, 'base': 'Rubble', 'wall': 'Clapboard', 'gable_mat': 'ShingleSilver', 'roof_mat': 'TinOxide', 'door': 'Oxblood', 'lites': '2', 'car': 'cross', 'lofts': True, 'wing': 'far', 'pavilions': ((0.0, 4, 'hip'), (1.0, 3, 'hip'))})
