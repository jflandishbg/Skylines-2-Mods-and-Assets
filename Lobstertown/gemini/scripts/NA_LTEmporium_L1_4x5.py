"""Lobstertown Emporium, lot 4x5. Built from lt_designs/boardwalk.py."""
from lt_designs.boardwalk import build as design

ZONE = "ZC2"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=4, D=5, **{'storeys': 6, 'promenade': True, 'roofs': 'g', 'turret': 'l', 'back': 'store', 'lantern': True, 'wall': 'Clapboard', 'gable_mat': 'ShingleSilver', 'roof_mat': 'SlateDark', 'door': 'Black', 'sign': 'Emporium', 'towers': (('l', 2, 'hip'),), 'spire': (3, 0), 'pitch': 1.5})
