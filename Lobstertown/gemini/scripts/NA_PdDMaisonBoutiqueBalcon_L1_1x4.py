"""Maison à boutique et balcon: shop with flats above, ochre render, green shopfront, iron balcony.
Built from the kit design nf_designs/maison_boutique_balcon.py."""
from nf_designs.maison_boutique_balcon import build as design

ZONE = "Z5"
HOUSEHOLDS = 3
PARTY_WALLS = ("left", "right")


def build(lod):
    design(lod)
