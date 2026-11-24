"""Lobstertown BrightonFlats, lot 3x5. Built from lt_designs/cottage.py."""
from lt_designs.cottage import build as design

ZONE = "ZP2"
HOUSEHOLDS = 6
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=5, **{'flats': True, 'sign': 'TheBrighton', 'storeys': 4, 'roof': 'gable', 'turret': True, 'cross': True, 'hand': 'R', 'base': 'Greystone', 'wall': 'ShingleSilver', 'gable_mat': 'ShingleGrey', 'roof_mat': 'SlateDark', 'door': 'Black', 'lites': '6', 'car': 'gambrel', 'cupola': True, 'wing': 'twin'})
