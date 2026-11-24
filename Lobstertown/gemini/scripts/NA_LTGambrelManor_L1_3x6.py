"""Lobstertown GambrelManor, lot 3x6. Built from lt_designs/cottage.py."""
from lt_designs.cottage import build as design

ZONE = "ZP1"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=6, **{'car': 'gambrel', 'cupola': True, 'wing': 'far', 'storeys': 3, 'roof': 'gambrel', 'turret': False, 'cross': True, 'wall': 'ShingleGrey', 'gable_mat': 'ShingleSilver', 'roof_mat': 'SlateDark', 'door': 'GreyBlue', 'lites': '6'})
