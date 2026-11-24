"""Lobstertown DrugGable, lot 1x3. Built from lt_designs/mainst.py."""
from lt_designs.mainst import build as design

ZONE = "ZM1"
HOUSEHOLDS = 2
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=3, **{'front': 'shop', 'storeys': 3, 'ground': 'granite', 'roof': 'gable', 'parapet': True, 'back': (2, 1), 'wall': 'BuffBrick', 'roof_mat': 'SlateDark', 'door': 'Oxblood', 'lites': '2', 'sign': 'PenobscotDrug', 'sign_side': 'r'})
