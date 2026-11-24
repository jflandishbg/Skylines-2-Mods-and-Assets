"""R4-0 art and placement specifications, in metres from the front-left lot corner."""

FIRE_NAME="NA_PdDCaserneArcCanal_L1_12x10"
HALL_NAME="NA_PdDHotelDeVilleDeuxRives_L1_16x12"
FIRE_AXIS=(32,48,64)
FIRE_ARCH_Y=(14,32)
FIRE_DOOR_Y=43
FIRE_BACK_Y=48.6
FIRE_BAY=(6.2,6.4)
PORTALS=((32,8.6,8.8,3.3),(48,13.4,10.1,4.8),(64,8.6,8.8,3.3))

def props(kind, positions, size):
    return [dict(kind=kind,position_lot_m=[x,y,0],size_m=size) for x,y in positions]

def plans():
    fire=dict(name=FIRE_NAME,design="CaserneArcCanal",title="Caserne de l’Arc du Canal",
              service="fire",lot=[12,10],crown_m=49,budget=[60000,15000,2000],zone_key=None,
              vehicle_doors_lot_m=[[x,FIRE_DOOR_Y+2] for x in FIRE_AXIS],
              pedestrian_point_lot_m=[13.5,1.5],
              entrances={
                  "public":dict(position_lot_m=[13.5,37.0,0.12],approach_lot_m=[[13.5,1.5],[13.5,37.0]]),
                  "vehicles":[dict(position_lot_m=[x,FIRE_DOOR_Y,0.03],width_m=FIRE_BAY[0],height_m=FIRE_BAY[1],
                                   recess_depth_m=FIRE_BACK_Y-FIRE_DOOR_Y) for x in FIRE_AXIS]},
              props=props("street lamp",[(17,7),(77,8),(82,32)],[.50,.5,5.5])+
                    props("flagpole",[(18,10)],[.60,.60,9.0])+
                    props("bollard",[(17,18),(17,28)],[.3,.3,.9]),
              lineage=dict(dominant="Paris",guests=["Lille"],
                           signature="A freestanding three-bay triumphal arch with a coffered centre barrel and a 49 m hose campanile",
                           fiction="A canal brigade used stone from an abandoned victory gate to frame the exits of its Lille-brick engine house."))
    hall=dict(name=HALL_NAME,design="HotelDeVilleDeuxRives",title="Hôtel de Ville des Deux-Rives",
              service="town_hall",lot=[16,12],crown_m=86,budget=[80000,20000,2500],zone_key=None,
              vehicle_doors_lot_m=[],pedestrian_point_lot_m=[64,1.5],
              entrances={
                  "public":dict(position_lot_m=[64,55.2,0.84],
                                approach_lot_m=[[64,1.5],[64,13],[53,20],[53,40],[64,47],[64,55.2]]),
                  "vehicles":[]},
              props=props("fountain",[(64,30)],[10,10,3.25])+
                    props("street lamp",[(39,15),(89,15),(42,29),(86,29),(41,45),(87,45)],[.58,.58,5.7])+
                    props("bench",[(47,26),(81,26),(47,36),(81,36)],[2.05,.62,1.0])+
                    props("tree",[(15,18),(113,18),(16,45),(112,47)],[6,6,10])+
                    props("flagpole",[(49,49),(79,49)],[.65,.65,10]),
              lineage=dict(dominant="Lille",guests=["Paris","Philadelphia"],
                           signature="An 86 m quay-side brick belfry with four luminous clocks and a gilt figure of La Delaware",
                           fiction="The city surveyor left the court clear for public assemblies and set the belfry on the quay side so bargemen could see the clock."))
    for a in (fire,hall):
        a.update(colourway="A",level=1,households=0,access="Front",native_surfaces=[])
    return [fire,hall]

