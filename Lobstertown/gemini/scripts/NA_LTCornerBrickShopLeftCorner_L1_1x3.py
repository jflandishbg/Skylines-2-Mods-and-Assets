"""Lobstertown CornerBrickShopLeftCorner, lot 1x3. Built from lt_designs/mainst.py."""
from lt_designs.mainst import build as design

ZONE = "ZM1"
HOUSEHOLDS = 3
PARTY_WALLS = ('right',)


def build(lod):
    design(lod, D=3, **{'front': 'shop', 'storeys': 4, 'ground': 'iron', 'roof': 'flat', 'cornice': 'bracket', 'hood': 'cap', 'corner': True, 'tower': 'square', 'back': (2,), 'escape': True, 'wall': 'Brick085', 'roof_mat': 'SlateDark', 'door': 'Green', 'lites': '2'})
