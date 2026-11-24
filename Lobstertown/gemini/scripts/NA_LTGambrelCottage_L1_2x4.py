"""Lobstertown GambrelCottage, lot 2x4. Built from lt_designs/cottage.py."""
from lt_designs.cottage import build as design

ZONE = "ZP1"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, W=2, D=4, **{'car': 'gambrel', 'cupola': True, 'storeys': 2, 'roof': 'gambrel', 'turret': True, 'cross': False, 'hand': 'R', 'wall': 'ShingleGrey', 'roof_mat': 'SlateDark', 'door': 'Green', 'lites': '6', 'car_mat': 'ShingleSilver'})
