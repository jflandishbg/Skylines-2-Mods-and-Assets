"""Lobstertown PacificFlats, lot 4x6. Built from lt_designs/cottage.py."""
from lt_designs.cottage import build as design

ZONE = "ZP2"
HOUSEHOLDS = 10
PARTY_WALLS = ()


def build(lod):
    design(lod, W=4, D=6, **{'car_base': 'Greystone', 'flats': True, 'sign': 'ThePacific', 'storeys': 4, 'roof': 'gambrel', 'turret': True, 'cross': False, 'hand': 'R', 'wall': 'ShingleSilver', 'roof_mat': 'SlateDark', 'door': 'GreyBlue', 'lites': '6', 'car': 'gambrel', 'wing': 'far'})
