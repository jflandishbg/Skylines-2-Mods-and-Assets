"""Lobstertown IllinoisFlats, lot 4x5. Built from lt_designs/cottage.py."""
from lt_designs.cottage import build as design

ZONE = "ZP2"
HOUSEHOLDS = 8
PARTY_WALLS = ()


def build(lod):
    design(lod, W=4, D=5, **{'car_mat': 'ShingleSilver', 'car_base': 'Greystone', 'flats': True, 'sign': 'TheIllinois', 'storeys': 4, 'roof': 'gambrel', 'turret': True, 'cross': True, 'wall': 'ShingleGrey', 'gable_mat': 'ShingleSilver', 'roof_mat': 'SlateGreen', 'door': 'Black', 'lites': '6', 'car': 'gable', 'cupola': True, 'wing': 'far'})
