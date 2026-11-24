"""Lobstertown KiteShop, lot 2x2. Built from lt_designs/shops.py."""
from lt_designs.shops import build as design

ZONE = "ZC1"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=2, D=2, **{'kind': 'clap', 'storeys': 2, 'top': 'step', 'roof': 'gable', 'awning': False, 'wall': 'Clapboard', 'roof_mat': 'SlateGreen', 'door': 'Black', 'lites': '6', 'palette': 'shopfront', 'sign': 'KiteShop', 'sign_side': 'l', 'stock': 'shed'})
