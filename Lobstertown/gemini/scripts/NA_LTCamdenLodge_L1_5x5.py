"""Lobstertown CamdenLodge, lot 5x5. Built from lt_designs/coastal_inn.py."""
from lt_designs.coastal_inn import build as design

ZONE = "ZP2"
HOUSEHOLDS = 24
PARTY_WALLS = ()


def build(lod):
    design(lod, W=5, D=5, **{'storeys': 3, 'roof': 'gable', 'turret': True, 'cross': False, 'base': 'StoneBase', 'hand': 'L', 'wall': 'ShingleSilver', 'gable_mat': 'ShingleGrey', 'roof_mat': 'SlateGreen', 'door': 'Green', 'wing_mat': 'ShingleSilver', 'car_mat': 'ShingleGrey', 'car': 'gable', 'cupola': True, 'lofts': True, 'car_base': 'StoneBase', 'flats': False, 'layout': 'lodge', 'lites': '1'})
