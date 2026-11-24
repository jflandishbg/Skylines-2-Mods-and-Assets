"""Lobstertown TaffyShop, lot 1x3. Built from lt_designs/shops.py."""
from lt_designs.shops import build as design

ZONE = "ZC1"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=1, D=3, **{'kind': 'clap', 'storeys': 1, 'top': 'step', 'roof': 'gable', 'awning': True, 'wall': 'Clapboard', 'roof_mat': 'SlateDark', 'door': 'Oxblood', 'lites': '6', 'palette': 'shopfront', 'sign': 'SaltWaterTaffy', 'stock': 'shed', 'stock_mat': 'TinOxide', 'vent': True})
