"""Lobstertown CrossGableCottage, lot 3x5. Built from lt_designs/cottage.py."""
from lt_designs.cottage import build as design

ZONE = "ZP1"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=5, **{'car': 'cross', 'lofts': True, 'storeys': 2, 'roof': 'gable', 'turret': False, 'cross': True, 'hand': 'R', 'wall': 'Clapboard', 'gable_mat': 'ShingleSilver', 'roof_mat': 'SlateGreen', 'door': 'Black', 'lites': '6', 'wing_mat': 'ShingleSilver'})
