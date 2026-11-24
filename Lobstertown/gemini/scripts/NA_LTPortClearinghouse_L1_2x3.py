"""Lobstertown PortClearinghouse, lot 2x3. Built from lt_designs/exchange.py."""
from lt_designs.exchange import build as design

ZONE = "ZO1"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=2, D=3, **{'storeys': 3, 'ground': 'square', 'oriels': True, 'roof': 'mansard', 'back': 'step', 'back_mat': 'BuffBrick', 'main_d': 15.0, 'palette': 'exchange'})
