"""Lobstertown BalconyTower, lot 1x3. Built from lt_designs/shore_row.py."""
from lt_designs.shore_row import build as design

ZONE = "ZL1"
HOUSEHOLDS = 4
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, D=3, **{'storeys': 4, 'roof': 'flat', 'front': 'quad', 'decks': True, 'hand': 'R', 'wall': 'Clapboard', 'roof_mat': 'SlateDark', 'door': 'GreyBlue', 'lites': '2', 'back_mat': 'ShingleSilver'})
