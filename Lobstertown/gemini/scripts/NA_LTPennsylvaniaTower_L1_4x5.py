"""Lobstertown PennsylvaniaTower, lot 4x5. Built from lt_designs/cottage.py."""
from lt_designs.cottage import build as design

ZONE = "ZP3"
HOUSEHOLDS = 34
PARTY_WALLS = ()


def build(lod):
    design(lod, W=4, D=5, **{'hotel': True, 'sign': 'ThePennsylvania', 'storeys': 16, 'roof': 'gambrel', 'turret': True, 'cross': True, 'hand': 'R', 'base': 'Rubble', 'wall': 'ShingleSilver', 'gable_mat': 'ShingleGrey', 'roof_mat': 'TinOxide', 'door': 'GreyBlue', 'lites': '6', 'car': 'gambrel', 'cupola': False, 'wing': 'twin', 'lantern': False, 'pavilions': ((0.5, 3, 'dome'),), 'spire': 3})
