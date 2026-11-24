"""Lobstertown CornerBrickShopRightCorner, lot 1x4. Built from lt_designs/mainst.py."""
from lt_designs.mainst import build as design

ZONE = "ZM1"
HOUSEHOLDS = 3
PARTY_WALLS = ('left',)


def build(lod):
    design(lod, D=4, **{'front': 'shop', 'storeys': 4, 'ground': 'iron', 'roof': 'flat', 'cornice': 'bracket', 'hood': 'cap', 'corner': True, 'tower': 'square', 'back': (2,), 'escape': True, 'wall': 'Brick085', 'roof_mat': 'SlateDark', 'door': 'Green', 'lites': '2', 'hand': 'R', 'hh': 3})
