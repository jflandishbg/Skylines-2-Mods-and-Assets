"""Lobstertown PacificFlats, lot 3x6. Built from lt_designs/cottage.py."""
from lt_designs.cottage import build as design

ZONE = "ZP2"
HOUSEHOLDS = 7
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=6, **{'car_base': 'Greystone', 'flats': True, 'sign': 'ThePacific', 'storeys': 4, 'roof': 'gambrel', 'turret': True, 'cross': False, 'hand': 'R', 'wall': 'ShingleSilver', 'roof_mat': 'SlateDark', 'door': 'GreyBlue', 'lites': '6', 'car': 'gambrel', 'wing': 'far'})
