"""Lobstertown VirginiaTower, lot 4x5. Built from lt_designs/cottage.py."""
from lt_designs.cottage import build as design

ZONE = "ZP3"
HOUSEHOLDS = 34
PARTY_WALLS = ()


def build(lod):
    design(lod, W=4, D=5, **{'hotel': True, 'sign': 'TheVirginia', 'storeys': 12, 'roof': 'gambrel', 'turret': True, 'cross': False, 'wall': 'ShingleSilver', 'gable_mat': 'ShingleGrey', 'roof_mat': 'SlateDark', 'door': 'GreyBlue', 'lites': '6', 'car': 'gable', 'cupola': True, 'wing': 'twin', 'pavilions': ((0.5, 3, 'dome'),), 'spire': 2})
