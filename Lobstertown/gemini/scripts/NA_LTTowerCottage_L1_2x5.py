"""Lobstertown TowerCottage, lot 2x5. Built from lt_designs/cottage.py."""
from lt_designs.cottage import build as design

ZONE = "ZP1"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, W=2, D=5, **{'car': 'gable', 'cupola': True, 'lofts': True, 'wing': 'far', 'storeys': 3, 'roof': 'gable', 'turret': True, 'cross': True, 'wall': 'ShingleSilver', 'gable_mat': 'ShingleGrey', 'roof_mat': 'SlateDark', 'door': 'Oxblood', 'lites': '6'})
