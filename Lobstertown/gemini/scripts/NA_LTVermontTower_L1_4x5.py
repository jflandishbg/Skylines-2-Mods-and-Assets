"""Lobstertown VermontTower, lot 4x5. Built from lt_designs/cottage.py."""
from lt_designs.cottage import build as design

ZONE = "ZP3"
HOUSEHOLDS = 34
PARTY_WALLS = ()


def build(lod):
    design(lod, W=4, D=5, **{'hotel': True, 'sign': 'TheVermont', 'storeys': 12, 'roof': 'gambrel', 'turret': False, 'cross': True, 'hand': 'R', 'wall': 'ClapSage', 'gable_mat': 'ShingleSilver', 'roof_mat': 'TinOxide', 'door': 'Green', 'lites': '2', 'car': 'cross', 'cupola': True, 'wing': 'near', 'lantern': False, 'pavilions': ((0.0, 3, 'hipl'),)})
