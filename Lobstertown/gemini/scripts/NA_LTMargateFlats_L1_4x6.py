"""Lobstertown MargateFlats, lot 4x6. Built from lt_designs/cottage.py."""
from lt_designs.cottage import build as design

ZONE = "ZP2"
HOUSEHOLDS = 10
PARTY_WALLS = ()


def build(lod):
    design(lod, W=4, D=6, **{'car_mat': 'Clapboard', 'wing_mat': 'ShingleSilver', 'flats': True, 'sign': 'TheMargate', 'storeys': 4, 'roof': 'gambrel', 'turret': False, 'cross': True, 'hand': 'R', 'wall': 'Clapboard', 'gable_mat': 'ShingleSilver', 'roof_mat': 'SlateGreen', 'door': 'Oxblood', 'lites': '2', 'car': 'gable', 'lofts': True, 'wing': 'far'})
