"""Lobstertown HardwareBlock, lot 1x3. Built from lt_designs/mainst.py."""
from lt_designs.mainst import build as design

ZONE = "ZM1"
HOUSEHOLDS = 2
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=3, **{'front': 'shop', 'storeys': 3, 'ground': 'iron', 'roof': 'flat', 'cornice': 'corbel', 'hood': 'cap', 'back': (2, 1), 'escape': True, 'awning': 'Green', 'wall': 'Brick074', 'door': 'Green', 'lites': '2', 'sign': 'HarborHardware', 'sign_side': 'r'})
