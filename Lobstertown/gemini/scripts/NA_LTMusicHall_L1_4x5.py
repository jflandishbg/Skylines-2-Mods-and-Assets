"""Lobstertown MusicHall, lot 4x5. Built from lt_designs/boardwalk.py."""
from lt_designs.boardwalk import build as design

ZONE = "ZC2"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=4, D=5, **{'storeys': 4, 'promenade': True, 'roofs': 'm', 'turret': 'both', 'lantern': False, 'wall': 'ShingleGrey', 'gable_mat': 'ShingleSilver', 'roof_mat': 'SlateGreen', 'door': 'Oxblood', 'sign': 'MusicHall', 'towers': (('c', 2, 'dome'),), 'spire': (2, 1)})
