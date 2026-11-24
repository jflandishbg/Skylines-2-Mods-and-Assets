"""Hôtel Brique et Pierre (the benchmark): mid red brick, grey ashlar ground floor, slate and lead mansards, green door.
Built from the kit design nf_designs/hotel_brique_et_pierre.py (as imported 2026-11-13: runs/2026-11-13_170327)."""
from nf_designs.hotel_brique_et_pierre import build as design

ZONE = "Z1B"
HOUSEHOLDS = 1
PARTY_WALLS = ()


def build(lod):
    design(lod)
