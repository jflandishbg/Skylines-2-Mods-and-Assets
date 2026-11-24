"""Lobstertown LobsterPound, lot 2x4. Built from lt_designs/cannery.py."""
from lt_designs.cannery import build as design

ZONE = "ZI1"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')
PRODUCT = "Food"


def build(lod):
    design(lod, W=2, D=4, **{'storeys': 1, 'roofs': 'g', 'vents': 'cupola', 'base': 'Rubble', 'wall': 'ShingleSilver', 'roof_mat': 'SlateGreen', 'door': 'GreyBlue', 'sign': 'LiveLobsters'})
