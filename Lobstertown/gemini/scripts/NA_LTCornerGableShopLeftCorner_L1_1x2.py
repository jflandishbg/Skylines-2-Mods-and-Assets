"""Lobstertown CornerGableShopLeftCorner, lot 1x2. Built from lt_designs/mainst.py."""
from lt_designs.mainst import build as design

ZONE = "ZM1"
HOUSEHOLDS = 2
PARTY_WALLS = ('right',)


def build(lod):
    design(lod, D=2, **{'front': 'shop', 'storeys': 3, 'ground': 'granite', 'roof': 'gable', 'corner': True, 'tower': 'octagon', 'back': (2, 1), 'wall': 'BuffBrick', 'roof_mat': 'SlateDark', 'door': 'Oxblood', 'lites': '2'})
