"""Lobstertown StJamesFlats, lot 4x6. Built from lt_designs/cottage.py."""
from lt_designs.cottage import build as design

ZONE = "ZP2"
HOUSEHOLDS = 10
PARTY_WALLS = ()


def build(lod):
    design(lod, W=4, D=6, **{'car_mat': 'Clapboard', 'wing_mat': 'Clapboard', 'flats': True, 'sign': 'TheStJames', 'storeys': 4, 'roof': 'gable', 'turret': False, 'cross': True, 'base': 'Greystone', 'wall': 'Clapboard', 'gable_mat': 'ShingleGrey', 'roof_mat': 'SlateGreen', 'door': 'Oxblood', 'lites': '2', 'car': 'cross', 'lofts': True, 'wing': 'twin'})
