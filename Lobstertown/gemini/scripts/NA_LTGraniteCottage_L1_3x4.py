"""Lobstertown GraniteCottage, lot 3x4. Built from lt_designs/cottage.py."""
from lt_designs.cottage import build as design

ZONE = "ZP1"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=4, **{'car': 'gambrel', 'car_base': 'Greystone', 'wing': 'far', 'storeys': 2, 'roof': 'gambrel', 'turret': True, 'cross': True, 'base': 'Greystone', 'wall': 'ShingleSilver', 'roof_mat': 'SlateDark', 'door': 'Black', 'lites': '6'})
