"""Lobstertown CafeMansard, lot 1x4. Built from lt_designs/mainst.py."""
from lt_designs.mainst import build as design

ZONE = "ZM1"
HOUSEHOLDS = 2
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=4, **{'front': 'shop', 'storeys': 3, 'ground': 'iron', 'roof': 'mansard', 'hood': 'pediment', 'back': (2, 1), 'decks': True, 'awning': 'Oxblood', 'wall': 'BrownBrick', 'roof_mat': 'SlateGreen', 'door': 'Oxblood', 'lites': '2', 'sign': 'SeaSmokeCafe', 'sign_side': 'l'})
