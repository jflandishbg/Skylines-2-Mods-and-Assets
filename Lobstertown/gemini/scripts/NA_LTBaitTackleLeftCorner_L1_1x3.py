"""Lobstertown BaitTackleLeftCorner, lot 1x3. Built from lt_designs/shops.py."""
from lt_designs.shops import build as design

ZONE = "ZC1"
HOUSEHOLDS = 0
PARTY_WALLS = ('right',)


def build(lod):
    design(lod, W=1, D=3, **{'kind': 'clap', 'storeys': 2, 'top': 'flat', 'roof': 'gable', 'awning': True, 'wall': 'Clapboard', 'roof_mat': 'SlateDark', 'door': 'GreyBlue', 'lites': '6', 'palette': 'shopfront', 'stock': 'gable', 'corner': True})
