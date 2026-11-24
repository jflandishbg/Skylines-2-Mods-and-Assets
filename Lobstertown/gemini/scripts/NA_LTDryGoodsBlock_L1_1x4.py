"""Lobstertown DryGoodsBlock, lot 1x4. Built from lt_designs/mainst.py."""
from lt_designs.mainst import build as design

ZONE = "ZM1"
HOUSEHOLDS = 3
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=4, **{'front': 'shop', 'storeys': 4, 'ground': 'granite', 'roof': 'flat', 'cornice': 'bracket', 'pediment': True, 'hall': True, 'hood': 'cap', 'back': (2, 1), 'wall': 'Brick085', 'door': 'Black', 'lites': '2', 'sign': 'KnoxDryGoods', 'sign_side': 'r'})
