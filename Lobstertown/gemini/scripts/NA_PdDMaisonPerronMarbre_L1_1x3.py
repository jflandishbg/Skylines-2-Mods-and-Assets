"""Maison à perron de marbre: Philadelphia brick row house, Second Empire mansard, marble stoop, back-building.
Built from the kit design nf_designs/maison_perron_marbre.py."""
from nf_designs.maison_perron_marbre import build as design

ZONE = "Z1A"
HOUSEHOLDS = 1
PARTY_WALLS = ("left", "right")


def build(lod):
    design(lod)
