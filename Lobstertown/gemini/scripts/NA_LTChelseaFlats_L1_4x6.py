"""Lobstertown ChelseaFlats, lot 4x6. Built from lt_designs/cottage.py."""
from lt_designs.cottage import build as design

ZONE = "ZP2"
HOUSEHOLDS = 10
PARTY_WALLS = ()


def build(lod):
    design(lod, W=4, D=6, **{'car_base': 'Rubble', 'flats': True, 'sign': 'TheChelsea', 'storeys': 4, 'roof': 'gable', 'turret': False, 'cross': True, 'hand': 'R', 'base': 'Rubble', 'wall': 'ShingleSilver', 'gable_mat': 'ShingleGrey', 'roof_mat': 'SlateGreen', 'door': 'GreyBlue', 'lites': '6', 'car': 'cross', 'cupola': True, 'wing': 'twin'})
