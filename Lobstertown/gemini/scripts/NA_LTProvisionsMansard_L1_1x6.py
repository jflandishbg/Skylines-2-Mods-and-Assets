"""Lobstertown ProvisionsMansard, lot 1x6. Built from lt_designs/mainst.py."""
from lt_designs.mainst import build as design

ZONE = "ZM1"
HOUSEHOLDS = 2
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=6, **{'front': 'shop', 'storeys': 3, 'ground': 'granite', 'roof': 'mansard', 'hood': 'pediment', 'quoins': True, 'back': (2, 1), 'escape': True, 'wall': 'Greystone', 'back_mat': 'BrownBrick', 'roof_mat': 'SlateDark', 'door': 'Green', 'lites': '6', 'sign': 'SaltPier', 'sign_side': 'r'})
