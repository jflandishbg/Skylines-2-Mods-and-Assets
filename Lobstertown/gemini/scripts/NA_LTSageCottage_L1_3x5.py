"""Lobstertown SageCottage, lot 3x5. Built from lt_designs/cottage.py."""
from lt_designs.cottage import build as design

ZONE = "ZP1"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=5, **{'car': 'cross', 'cupola': True, 'wing': 'far', 'storeys': 2, 'roof': 'gable', 'turret': True, 'cross': True, 'hand': 'R', 'wall': 'ClapSage', 'gable_mat': 'ShingleSilver', 'roof_mat': 'SlateDark', 'door': 'Oxblood', 'lites': '6', 'wing_mat': 'ShingleGrey', 'car_mat': 'ShingleGrey'})
