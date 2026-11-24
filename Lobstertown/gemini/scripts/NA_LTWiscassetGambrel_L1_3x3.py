"""Lobstertown WiscassetGambrel, lot 3x3. Built from lt_designs/federal.py."""
from lt_designs.federal import build as design

ZONE = "ZP1"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod, W=3, D=3, **{'palette': 'federal', 'kind': 'gambrel', 'storeys': 2, 'dormers': True, 'entry': 'fan', 'shutters': 'Black', 'door': 'Black', 'ell': 'MID', 'woodshed': True, 'barn': 'gable', 'barn_h': 'LOW', 'cupola': True, 'wings': 'far'})
