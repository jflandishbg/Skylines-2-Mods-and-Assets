"""Lobstertown PenobscotHotel, lot 5x5. Built from lt_designs/coastal_inn.py."""
from lt_designs.coastal_inn import build as design

ZONE = "ZP2"
HOUSEHOLDS = 24
PARTY_WALLS = ()


def build(lod):
    design(lod, W=5, D=5, **{'storeys': 3, 'roof': 'gambrel', 'turret': True, 'cross': True, 'base': None, 'hand': 'R', 'wall': 'ShingleSilver', 'gable_mat': 'ShingleGrey', 'roof_mat': 'Slate', 'door': 'GreyBlue', 'wing_mat': 'ShingleSilver', 'car_mat': 'ShingleGrey', 'car': 'cross', 'cupola': True, 'lofts': False, 'car_base': None, 'flats': False, 'layout': 'offset', 'lites': '1'})
