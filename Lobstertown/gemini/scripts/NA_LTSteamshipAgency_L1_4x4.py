"""Lobstertown SteamshipAgency, lot 4x4. Built from lt_designs/exchange.py."""
from lt_designs.exchange import build as design

ZONE = "ZO1"
HOUSEHOLDS = 0
PARTY_WALLS = ('left', 'right')


def build(lod):
    design(lod, W=4, D=4, **{'storeys': 4, 'ground': 'square', 'oriels': True, 'crown': 'balustrade', 'back': 'hall', 'back_mat': 'BuffBrick', 'palette': 'exchange'})
