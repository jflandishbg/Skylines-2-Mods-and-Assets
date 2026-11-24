"""Immeuble à deux balcons: Haussmann apartment house, stone front, balconies on the 2nd and 5th floors, zinc mansard.
Built from the kit design nf_designs/immeuble_deux_balcons.py."""
from nf_designs.immeuble_deux_balcons import build as design

ZONE = "Z3"
HOUSEHOLDS = 30
PARTY_WALLS = ("left", "right")


def build(lod):
    design(lod)
