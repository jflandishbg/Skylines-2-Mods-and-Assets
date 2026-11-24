"""Lobstertown KentuckyFlats, lot 4x6. Built from lt_designs/cottage.py."""
from lt_designs.cottage import build as design

ZONE = "ZP2"
HOUSEHOLDS = 10
PARTY_WALLS = ()


def build(lod):
    design(lod, W=4, D=6, **{'car_mat': 'ClapSage', 'wing_mat': 'ShingleGrey', 'flats': True, 'sign': 'TheKentucky', 'storeys': 4, 'roof': 'gable', 'turret': True, 'cross': False, 'hand': 'R', 'wall': 'ClapSage', 'gable_mat': 'ShingleSilver', 'roof_mat': 'SlateDark', 'door': 'Green', 'lites': '2', 'car': 'gambrel', 'cupola': True, 'wing': 'near'})
