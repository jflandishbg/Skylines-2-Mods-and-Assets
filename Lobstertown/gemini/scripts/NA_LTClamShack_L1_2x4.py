"""Lobstertown ClamShack, lot 2x4. Built from lt_designs/shops.py."""
from lt_designs.shops import build as design

ZONE = "ZC1"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=2, D=4, **{'kind': 'clap', 'storeys': 1, 'top': 'flat', 'roof': 'shed', 'awning': True, 'wall': 'Clapboard', 'roof_mat': 'TinOxide', 'door': 'Green', 'lites': '6', 'palette': 'shopfront', 'sign': 'ClamShack', 'stock': 'shed'})
