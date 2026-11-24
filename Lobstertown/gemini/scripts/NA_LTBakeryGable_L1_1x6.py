"""Lobstertown BakeryGable, lot 1x6. Built from lt_designs/mainst.py."""
from lt_designs.mainst import build as design

ZONE = "ZM1"
HOUSEHOLDS = 2
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=6, **{'front': 'shop', 'storeys': 3, 'ground': 'iron', 'roof': 'gable', 'upper': 'bays', 'back': (1,), 'awning': 'GreyBlue', 'wall': 'Brick094', 'roof_mat': 'SlateGreen', 'door': 'GreyBlue', 'lites': '2', 'sign': 'BalsamBakery', 'sign_side': 'l'})
