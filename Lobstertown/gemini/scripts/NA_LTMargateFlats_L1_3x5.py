"""Lobstertown MargateFlats, lot 3x5. Built from lt_designs/cottage.py."""
from lt_designs.cottage import build as design

ZONE = "ZP2"
HOUSEHOLDS = 6
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=5, **{'car_mat': 'Clapboard', 'wing_mat': 'ShingleSilver', 'flats': True, 'sign': 'TheMargate', 'storeys': 4, 'roof': 'gambrel', 'turret': False, 'cross': True, 'hand': 'R', 'wall': 'Clapboard', 'gable_mat': 'ShingleSilver', 'roof_mat': 'SlateGreen', 'door': 'Oxblood', 'lites': '2', 'car': 'gable', 'lofts': True, 'wing': 'far'})
