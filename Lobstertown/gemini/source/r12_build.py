"""Dispatch Round 12 architecture and derive an envelope measurement from the authored mesh."""
from r12_geometry import *
from r12_flats import apartments, WORKER_BUILDERS

ESTATE_BUILDERS={
    "VillaMurHabite":inhabited,"VillaSurLEau":water_villa,"MaisonPlantationGaleries":plantation,
    "VillaNormande":normandy,"VillaMauresque":moorish,"VillaPalladienne":palladian,
    "VillaJeuDePaume":tennis,"VillaBelvedere":lookout,
    "HotelDeuxPavillons":two_pavilions,"HotelLoggia":loggia_house,
    "HotelMansarde":tall_mansard,"VillaBelvedereCarre":square_belvedere,
}

from estate_revision import BUILDERS as REVISIONS
ESTATE_BUILDERS.update(REVISIONS)

def build(a,lod):
    if a.get("gemini"):
        from gemini_build import build as gemini
        return gemini(a,lod)
    core.setup(a,lod,0)
    nb.REMAP[BRICK]=a["wall_tile"]
    h=nb.House(lod)
    h.name=a["name"]
    h.detail_grade=a.get("detail_grade",0)
    h.window_recess=.355
    h.r12=True
    h.quiet_counter=0
    h.compact_trim=a["zone_key"]=="Z2B" or a["design"]=="Familistere"
    h.hotel=design_is_hotel=a["design"]=="HotelMeublePort"
    h.estate=a["zone_key"]=="Z1B"
    h.roof=a["roof_tile"]
    w,d=(8*v for v in a["lot"])
    design=a["design"]
    fun=ESTATE_BUILDERS.get(design) or WORKER_BUILDERS.get(design) or apartments
    left,right,back=fun(h,a,w,d)
    yard(h,(left,right,.052,max(.30,back)))
    return h
