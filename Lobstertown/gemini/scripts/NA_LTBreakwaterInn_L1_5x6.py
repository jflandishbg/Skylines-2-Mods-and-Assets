"""Lobstertown BreakwaterInn, lot 5x6. Built from lt_designs/coastal_inn.py."""
from lt_designs.coastal_inn import build as design

ZONE = "ZP2"
HOUSEHOLDS = 28
PARTY_WALLS = ()


def build(lod):
    design(lod, W=5, D=6, **{'storeys': 3, 'roof': 'gable', 'turret': True, 'cross': True, 'base': 'StoneBase', 'hand': 'R', 'wall': 'ShingleSilver', 'gable_mat': 'ShingleGrey', 'roof_mat': 'SlateGreen', 'door': 'Green', 'wing_mat': 'ShingleSilver', 'car_mat': 'ShingleGrey', 'car': 'cross', 'cupola': True, 'lofts': False, 'car_base': 'StoneBase', 'flats': False, 'layout': 'slip', 'lites': '1'})
