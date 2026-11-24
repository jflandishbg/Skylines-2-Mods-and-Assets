"""Lobstertown HillMansardLeftCorner, lot 2x3. Built from lt_designs/harbourhill.py."""
from lt_designs.harbourhill import build as design

ZONE = "ZH1"
HOUSEHOLDS = 10
PARTY_WALLS = ('right',)


def build(lod):
    design(lod, W=2, D=3, **{'corner': True, 'roof': 'mansard', 'wall': 'BuffBrick', 'upper': 'bays', 'hood': 'pediment', 'roof_mat': 'SlateDark', 'door': 'Oxblood', 'storeys': 4, 'lots': [(2, 3), (2, 4), (2, 5), (2, 6)]})
