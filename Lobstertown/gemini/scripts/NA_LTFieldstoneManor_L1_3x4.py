"""Lobstertown FieldstoneManor, lot 3x4. Built from lt_designs/cottage.py."""
from lt_designs.cottage import build as design

ZONE = "ZP1"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=4, **{'car': 'gable', 'car_base': 'Rubble', 'lofts': True, 'storeys': 3, 'roof': 'gable', 'turret': False, 'cross': True, 'base': 'Rubble', 'hand': 'R', 'wall': 'ShingleSilver', 'gable_mat': 'ShingleGrey', 'roof_mat': 'SlateDark', 'door': 'Green', 'lites': '6'})
