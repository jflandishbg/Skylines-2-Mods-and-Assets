"""Lobstertown StatesTower, lot 5x6. Built from lt_designs/cottage.py."""
from lt_designs.cottage import build as design

ZONE = "ZP3"
HOUSEHOLDS = 55
PARTY_WALLS = ()


def build(lod):
    design(lod, W=5, D=6, **{'hotel': True, 'sign': 'TheStates', 'storeys': 14, 'roof': 'gable', 'turret': True, 'cross': True, 'wall': 'Clapboard', 'gable_mat': 'ShingleGrey', 'roof_mat': 'SlateDark', 'door': 'Oxblood', 'lites': '6', 'car': 'gable', 'lofts': True, 'wing': 'twin', 'pavilions': ((0.0, 4, 'hip'), (1.0, 3, 'hip')), 'spire': 3})
