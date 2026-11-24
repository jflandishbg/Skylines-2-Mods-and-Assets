"""Round 12 programme, lot dimensions, palettes and import metadata."""
from math import hypot

ESTATES = (
    ("VillaMurHabite", "Villa du Mur Habité", 2, "L-plan behind an inhabited garden wall"),
    ("VillaSurLEau", "Villa sur l’Eau", 3, "Hipped villa over a canal, with a stone bridge"),
    ("MaisonPlantationGaleries", "Maison des Quatre Galeries", 3, "Raised house with wraparound galleries"),
    ("VillaNormande", "Villa des Oyats", 2, "Deep tile roof and half-timbered seaside gable"),
    ("VillaMauresque", "Villa des Jasmins", 2, "Striped horseshoe arcade and rooftop kiosk"),
    ("VillaPalladienne", "Villa de l’Orme", 3, "Four-column pediment and paired wings"),
    ("VillaJeuDePaume", "Villa du Jeu de Paume", 3, "Long private tennis hall with clerestory"),
    ("VillaBelvedere", "Villa du Guetteur", 2, "Broad open lookout above the villa roof"),
    ("HotelDeuxPavillons", "Hôtel des Deux Pavillons", 3, "Two tall stone corner pavilions and a mansard corps de logis"),
    ("HotelLoggia", "Hôtel de la Loggia", 2, "Top-floor loggia of four stone arches under one broad roof"),
    ("HotelMansarde", "Hôtel à la Mansarde", 2, "Tall three-storey town palace under a deep slate mansard"),
    ("VillaBelvedereCarre", "Villa au Belvédère Carré", 3, "Long villa with a broad, low square belvedere room"),
)
FLATS = (
    ("ImmeubleBowWindows", "Les Oriellets", 2, "Paired iron-and-glass bowed stacks"),
    ("ImmeubleImprimeur", "Imprimerie du Grèbe", 2, "Three iron-shuttered press bays beneath flats"),
    ("ImmeubleJardinHiver", "Les Jardins d’Hiver", 2, "Vertically stacked planted winter gardens"),
)
WORKERS = (
    ("Familistere", "Familistère des Saules", 2, "Open-ended glass-roofed residential court"),
    ("Beguinage", "Béguinage du Lin", 2, "Small houses around a green behind a bell gate"),
    ("Coron", "Coron des Lampes", 2, "End-on mining terrace and individual garden strips"),
    ("CoureePompe", "Courée de la Pompe", 2, "Covered passage to the shared courtyard pump"),
    ("CiteCoursives", "Cité des Cordes", 2, "Open street galleries with doorways"),
    ("EscaliersMontreal", "Les Trois Escaliers", 2, "Three separately curved outdoor iron stairs"),
    ("CiteJardin", "Cité du Merle", 2, "Paired cottages under deep eaves and a shared roof"),
    ("PensionDockers", "Pension de la Bitture", 2, "Dockers’ canteen and a gable hoist"),
    ("MaisonPasseur", "Maison du Passeur", 2, "Ferryman’s stone steps and mooring"),
    ("LavoirHabite", "Lavoir de l’Aulne", 2, "Flats above an open public wash house"),
    ("HotelMeublePort", "Hôtel du Cabestan", 2, "Slender furnished hotel with enamel blade sign"),
    ("CiteEcluse", "Cité du Bief", 2, "Lock-keepers’ flats and stepped stone quay"),
)
ZONES = {"Z1B": ESTATES, "Z2B": FLATS, "Z4": WORKERS}
COUNTS = {"Z1B": 72, "Z2B": 18, "Z4": 36}
BRICK = {"A":"Brick085", "B":"Brick094", "C":"BuffBrick"}
ROOF = {"A":"SlateDark", "B":"SlateGreen", "C":"SlateBrown"}

def prop(kind,x,y,w,d,h):
    return dict(kind=kind,position_lot_m=[x,y,0],size_m=[w,d,h])

def make(zone=None):
    for key, roster in ZONES.items():
        if zone not in (None,key):
            continue
        for index,(design,title,width,signature) in enumerate(roster):
            w=width*8
            for depth in {"Z1B":(5,6),"Z2B":(4,5),"Z4":(3,4,5)}[key]:
                d=depth*8
                colors=("ABC"[(index+depth-3)%3],) if key=="Z4" else "ABC"
                for c in colors:
                    props=[prop("tree",w-2.1,d-2.9,2.6,2.6,4.2),
                           prop("hedge",w*.26,d-1.0,w*.34,.5,.72)]
                    if key=="Z1B":
                        props.extend((prop("tree",2.0,d-6.6,2.3,2.3,4.0),
                                      prop("hedge",w*.21,2.4,w*.29,.52,.82),
                                      prop("hedge",w*.79,2.4,w*.29,.52,.82)))
                        if design=="VillaMurHabite":
                            props[-1]=prop("hedge",14.35,2.4,1.68,.52,.82)
                    elif design in {"Beguinage","Coron","CiteJardin"}:
                        props.append(prop("hedge",w-2.1,3.8,.48,3.2,.66))
                    entry=dict(name=f"NA_PdD{design}{'' if c=='A' else c}_L1_{width}x{depth}",
                               design=design,display_title=title,inscription=title.upper(),
                               zone_key=key,lot=[width,depth],level=1,access="Front",colourway=c,
                               wall_tile=BRICK[c],roof_tile=ROOF[c],budget=[20000,6000,500],
                               props=props,native_surfaces=[],
                               lineage=dict(dominant={"Z1B":"Garden estates","Z2B":"Belle Époque flats","Z4":"River workers’ housing"}[key],
                                            guests=[],signature=signature,fiction=title+" stands in the Delaware district."))
                    if key!="Z4":
                        entry["households"]=1 if key=="Z1B" else {4:8,5:10}[depth]
                    yield entry

def atlas_owners(entry):
    zone=entry["zone_key"]
    roster=ZONES[zone]
    count=4 if zone in {"Z1B","Z4"} else 3
    group=next(i for i,record in enumerate(roster) if record[0]==entry["design"])//count
    if zone=="Z1B":group%=2   # R24: the new families share the existing estate atlases
    first=roster[group*count][0]
    owner=next(a["name"] for a in make(zone) if a["design"]==first)
    return chr(65+group),owner
