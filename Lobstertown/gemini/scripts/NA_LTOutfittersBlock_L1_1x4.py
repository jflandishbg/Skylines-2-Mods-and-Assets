"""Lobstertown OutfittersBlock, lot 1x4. Built from lt_designs/mainst.py."""
from lt_designs.mainst import build as design

ZONE = "ZM1"
HOUSEHOLDS = 2
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=4, **{'front': 'shop', 'storeys': 3, 'ground': 'iron', 'roof': 'flat', 'cornice': 'bracket', 'upper': 'turret', 'hood': 'cap', 'back': (2,), 'wall': 'Brick074', 'roof_mat': 'SlateGreen', 'door': 'GreyBlue', 'lites': '2', 'sign': 'GullRock', 'sign_side': 'r'})
