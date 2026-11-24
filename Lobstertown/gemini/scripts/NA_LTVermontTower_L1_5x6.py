"""Lobstertown VermontTower, lot 5x6. Built from lt_designs/cottage.py."""
from lt_designs.cottage import build as design

ZONE = "ZP3"
HOUSEHOLDS = 55
PARTY_WALLS = ()


def build(lod):
    design(lod, W=5, D=6, **{'hotel': True, 'sign': 'TheVermont', 'storeys': 12, 'roof': 'gambrel', 'turret': False, 'cross': True, 'hand': 'R', 'wall': 'ClapSage', 'gable_mat': 'ShingleSilver', 'roof_mat': 'TinOxide', 'door': 'Green', 'lites': '2', 'car': 'cross', 'cupola': True, 'wing': 'near', 'lantern': False, 'pavilions': ((0.0, 3, 'hipl'),)})
