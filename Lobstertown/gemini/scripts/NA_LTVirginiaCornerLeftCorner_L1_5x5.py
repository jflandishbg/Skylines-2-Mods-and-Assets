"""Lobstertown VirginiaCornerLeftCorner, lot 5x5. Built from lt_designs/cottage.py."""
from lt_designs.cottage import build as design

ZONE = "ZP3"
HOUSEHOLDS = 46
PARTY_WALLS = ()


def build(lod):
    design(lod, W=5, D=5, **{'hotel': True, 'storeys': 12, 'roof': 'gable', 'turret': True, 'cross': False, 'corner': True, 'wall': 'ShingleGrey', 'gable_mat': 'ShingleSilver', 'roof_mat': 'SlateDark', 'door': 'GreyBlue', 'lites': '6', 'car': 'gambrel', 'cupola': True, 'pavilions': ((0.5, 3, 'hipl'),), 'spire': 3, 'lots': [(4, 5), (5, 5), (5, 6), (6, 6)]})
