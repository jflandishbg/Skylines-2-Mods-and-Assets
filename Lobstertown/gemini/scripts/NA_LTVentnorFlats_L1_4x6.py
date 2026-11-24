"""Lobstertown VentnorFlats, lot 4x6. Built from lt_designs/cottage.py."""
from lt_designs.cottage import build as design

ZONE = "ZP2"
HOUSEHOLDS = 10
PARTY_WALLS = ()


def build(lod):
    design(lod, W=4, D=6, **{'car_mat': 'ShingleSilver', 'flats': True, 'sign': 'TheVentnor', 'storeys': 4, 'roof': 'gable', 'turret': True, 'cross': True, 'wall': 'Clapboard', 'gable_mat': 'ShingleSilver', 'roof_mat': 'SlateGreen', 'door': 'Green', 'lites': '2', 'car': 'gable', 'cupola': True, 'wing': 'near'})
