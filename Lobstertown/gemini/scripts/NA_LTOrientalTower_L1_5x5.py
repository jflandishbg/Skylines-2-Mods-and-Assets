"""Lobstertown OrientalTower, lot 5x5. Built from lt_designs/cottage.py."""
from lt_designs.cottage import build as design

ZONE = "ZP3"
HOUSEHOLDS = 46
PARTY_WALLS = ()


def build(lod):
    design(lod, W=5, D=5, **{'hotel': True, 'sign': 'TheOriental', 'storeys': 16, 'roof': 'gable', 'turret': True, 'cross': True, 'hand': 'R', 'base': 'Greystone', 'wall': 'ShingleGrey', 'gable_mat': 'ShingleSilver', 'roof_mat': 'TinOxide', 'door': 'Black', 'lites': '2', 'car': 'gambrel', 'wing': 'far', 'lantern': False, 'pavilions': ((1.0, 5, 'hipl'), (0.0, 4, 'hip')), 'spire': 4})
