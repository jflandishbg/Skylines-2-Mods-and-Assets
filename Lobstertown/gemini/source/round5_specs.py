"""Round 11 plans, all positions in metres from the lot's front-left corner."""
ROSTER=(
 ("JumellesVerger","Jumelles du Verger","JUMELLES DU VERGER","split","Lille","Delaware Valley",2.42,6.42,"Two gables and two doors around a planted court"),
 ("MaisonPigeonnier","Maison du Pigeonnier","MAISON DU PIGEONNIER","dovecote","Normandy","Delaware Valley",3.22,5.72,"A squat brick dovecote rising through a slate hip"),
 ("MaisonColombages","Maison à Colombages","MAISON À COLOMBAGES","jetty","Normandy","Delaware Valley",2.15,6.56,"A sixty-centimetre jetty with applied oak framing"),
 ("MaisonAtelier","Maison de l’Atelier","MAISON DE L’ATELIER","studio","Paris","Delaware Valley",3.17,8.31,"An asymmetric roof and a tall iron-framed studio window"),
 ("MaisonSurCave","Maison sur Cave","MAISON SUR CAVE","raised","Montréal","Delaware Valley",4.12,7.86,"A raised floor, sweeping iron stair and basement light well"),
 ("MaisonBelvedere","Maison du Belvédère","MAISON DU BELVÉDÈRE","pergola","Paris","Delaware Valley",2.61,6.83,"An open iron pergola with vines on a roof terrace"),
 ("MaisonSerre","Maison de la Serre","MAISON DE LA SERRE","greenhouse","Nantes","Delaware Valley",3.39,5.12,"A low hip with a ribbed garden conservatory"),
 ("ShotgunCamelback","Shotgun à Camelback","RUE DU CAMELBACK","camelback","New Orleans","Delaware Valley",1.52,4.25,"A paired front porch below a rear upper storey"),
 ("MaisonPuits","Maison du Puits","MAISON DU PUITS","court","Lille","Delaware Valley",1.75,5.37,"Two hips, a cobbled court and a stone well"),
 ("MaisonHorloger","Maison de l’Horloger","MAISON DE L’HORLOGER","clock","Flanders","Delaware Valley",3.03,7.96,"A broad matte clock in a tall street gable"),
 ("MaisonSolaire","Maison Solaire","MAISON SOLAIRE","solar","Paris","Delaware Valley",3.44,7.51,"Solar slate mansard, copper and a rainwater cistern"),
 ("MaisonPignonTournant","Maison à Pignon Tournant","PIGNON TOURNANT","barge","Québec","Delaware Valley",2.81,7.26,"A carved gable with a small iron balcony and a cross ridge"),
 ("MaisonPontet","Maison du Pontet","MAISON DU PONTET","bridge","Lille","Delaware Valley",1.93,6.34,"An upper room bridging a two-metre garden passage"),
 ("MaisonPorcheTraversant","Maison du Porche Traversant","PORCHE TRAVERSANT","porch","Normandy","Delaware Valley",1.47,5.72,"An open through-porch under the street gable"),
 ("PlexEscalier","Plex de l’Escalier","PLEX DE L’ESCALIER","spiral","Montréal","Delaware Valley",4.03,6.76,"A black iron spiral stair to the upper flat"),
)
COLORS={"A":("Brick085","SlateDark"),"B":("BuffBrick","SlateGreen"),"C":("RenderRose","SlateBrown")}
TITLES={"Z1C":"Napoleon Maisons de Ville","Z1A":"Napoleon Maisons Populaires"}

def door(x,y,z=.14,width=1.15,street_x=None):
    return dict(position_lot_m=[x,y,z],gate_lot_m=[x if street_x is None else street_x,0,0],
                width_m=width,street_path=True)

def shape(style,w,d,f,e):
    target=.436*w*d
    feature={}
    if style=="split":
        l,r=1.06,14.94
        a,c=6.02,9.94
        b=f+(target-(c-a)*1.65)/((a-l)+(r-c))
        feature=dict(left_end=a,right_start=c,court_width_m=round(c-a,2))
        entrances={"west":dict(door(3.31,f),address_number="12"),"east":dict(door(12.71,f+.14),address_number="14")}
    elif style=="court":
        l,r=1.38,9.66
        wing=14.66
        b=f+(target-(wing-r)*3.62)/(r-l)
        feature=dict(wing=wing,wing_depth=3.62)
        entrances={"front":door(4.08,f)}
    elif style=="greenhouse":
        l,r=1.47,10.73
        extension=2.82
        b=f+target/(r-l+extension*.67)
        feature=dict(greenhouse_width=extension)
        entrances={"front":door(4.18,f)}
    elif style=="bridge":
        l,r=.65,5.26
        b=f+(target-2.16*2.34)/(r-l)
        feature=dict(passage_right=7.42,passage_width_m=2.16)
        entrances={"front":door(2.32,f)}
    elif style=="porch":
        l,r=.78,7.05
        b=f+target/(r-l)
        feature=dict(porch_depth=2.62,porch_clear_height_m=2.70)
        entrances={"front":door(3.01,f+2.62)}
    else:
        width={"dovecote":11.48,"jetty":11.18,"studio":11.06,"raised":11.77,"pergola":11.47,
               "camelback":10.78,"clock":10.60,"solar":11.22,"barge":11.70,"spiral":5.77}[style]
        l,r=(w-width)/2,(w+width)/2
        length=target/width
        b=f+length
        if style=="jetty":
            entrances={"front":door(l+2.10,f+.60)}
        elif style=="camelback":
            feature=dict(porch_depth=1.61)
            entrances={"west":door(l+2.12,f+1.61),"east":door(r-2.12,f+1.61)}
        elif style=="raised":
            entrances={"front":door(l+4.14,f,1.50,street_x=l+6.16)}
        elif style=="spiral":
            entrances={"lower":door(l+1.38,f),"upper":door(r-1.38,f,3.18,street_x=6.77)}
        else:
            entrances={"front":door(l+2.17,f)}
    return [l,r,f,round(b,4)],feature,entrances

def make(zone=None):
    for i,(name,title,sign,style,dominant,guest,f,e,signature) in enumerate(ROSTER):
        key="Z1C" if i<12 else "Z1A"
        if zone not in (None,key):
            continue
        cells=2 if key=="Z1C" else 1
        width=cells*8
        for dep in (2,3):
            d=dep*8
            wall,feature,entrances=shape(style,width,d,f,e)
            for color,(mat,roof) in COLORS.items():
                if style=="barge":
                    mat={"A":"RenderSage","B":"RenderOchre","C":"RenderRose"}[color]
                if style=="jetty":
                    mat={"A":"RenderOchre","B":"Cream","C":"RenderRose"}[color]
                if style=="dovecote":
                    mat={"A":"Brick085","B":"BuffBrick","C":"BrownBrick"}[color]
                if style=="pergola":
                    mat={"A":"Greystone","B":"Dressed","C":"RenderSage"}[color]
                if style=="camelback":
                    mat={"A":"ClapSage","B":"Clapboard","C":"RenderRose"}[color]
                if style in {"jetty","camelback"}:
                    roof={"A":"TinOxide","B":"SlateGreen","C":"SlateBrown"}[color]
                if style=="solar":roof="SolarSlate"
                active=[dict(kind=k,**v) for k,v in entrances.items()]
                walks=[]
                for v in active:
                    x,y,z=v["position_lot_m"]
                    street=v["gate_lot_m"][0]
                    walks.append(dict(bounds_lot_m=[min(x,street)-.48,max(x,street)+.48,0,y+.015],
                        connects_to=v["kind"]))
                family_id="" if color=="A" else color
                yield dict(name=f"NA_PdD{name}{family_id}_L1_{cells}x{dep}",design=name,style=style,
                    zone_key=key,display_title=title,inscription=sign,lot=[cells,dep],level=1,
                    access="Front",households=2 if style in {"split","camelback","spiral"} else 1,
                    colourway=color,wall_tile=mat,roof_tile=roof,eave_m=e,walls=wall,
                    entrances=entrances,active_entrances=active,front_walks=walks,**feature,
                    budget=[20000,6000,500],
                    props=[
                        dict(kind="tree",position_lot_m=[width-(2.2 if cells==2 else 1.73),d-1.16,0],size_m=[2.0,2.0,3.7]),
                        dict(kind="hedge",position_lot_m=[2.65 if cells==2 else 1.54,d-.42,0],size_m=[3.6 if cells==2 else 1.9,.47,.66])],
                    lineage=dict(dominant=dominant,guests=[guest],signature=signature,
                                 fiction=f"{title} grew out of the river city's small garden lots."))

def footprint(a):
    l,r,f,b=a["walls"]
    return [(l,f),(r,f),(r,b),(l,b)]
