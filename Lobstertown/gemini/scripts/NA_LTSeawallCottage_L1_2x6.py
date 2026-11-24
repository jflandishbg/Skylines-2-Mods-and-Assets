"""Lobstertown SeawallCottage, lot 2x6. Built from lt_designs/cottage.py."""
from lt_designs.cottage import build as design

ZONE = "ZP1"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, W=2, D=6, **{'car': 'gable', 'car_base': 'Greystone', 'cupola': True, 'wing': 'far', 'storeys': 3, 'roof': 'gable', 'turret': True, 'cross': False, 'base': 'Greystone', 'hand': 'R', 'wall': 'ShingleGrey', 'roof_mat': 'SlateDark', 'door': 'Oxblood', 'lites': '2'})
