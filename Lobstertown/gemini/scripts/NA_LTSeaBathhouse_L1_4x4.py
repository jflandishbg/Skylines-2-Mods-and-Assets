"""Lobstertown SeaBathhouse, lot 4x4. Built from lt_designs/boardwalk.py."""
from lt_designs.boardwalk import build as design

ZONE = "ZC2"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=4, D=4, **{'storeys': 3, 'promenade': True, 'roofs': 'g', 'turret': 'both', 'back': 'store', 'lantern': True, 'base': 'Rubble', 'wall': 'ClapSage', 'gable_mat': 'ShingleSilver', 'roof_mat': 'TinOxide', 'door': 'GreyBlue'})
