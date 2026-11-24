"""Lobstertown SamosetInn, lot 3x4. Built from lt_designs/coastal_inn.py."""
from lt_designs.coastal_inn import build as design

ZONE = "ZP2"
HOUSEHOLDS = 10
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=4, **{'storeys': 3, 'roof': 'gambrel', 'turret': True, 'cross': True, 'base': 'StoneBase', 'hand': 'L', 'wall': 'ShingleSilver', 'gable_mat': 'ShingleGrey', 'roof_mat': 'SlateDark', 'door': 'Oxblood', 'wing_mat': 'ShingleSilver', 'car_mat': 'ShingleGrey', 'car': 'gambrel', 'cupola': True, 'lofts': True, 'car_base': 'StoneBase', 'flats': False, 'layout': 'quadrangle', 'lites': '6'})
