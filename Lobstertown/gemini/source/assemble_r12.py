"""Build labelled silhouettes and the matched street-camera comparisons."""
from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
PRE=ROOT/"previews"
OUT=PRE/"family-closeups"
PAPER="#f6f1e7"
INK="#263c32"
MUTED="#e1e9df"
ZONES={"Z1B":"Maisons Patriciennes","Z2B":"Immeubles de Rapport","Z4":"Immeubles de la Rivière"}
OLD_TITLES={"ManoirFederalRoyal":"Manoir Fédéral Royal","VillaDuParc":"Villa du Parc",
 "RapportLoggiaToscane":"Loggia Toscane","RapportRotondeAngleLeftCorner":"Rotonde d’Angle",
 "CiteHorloge":"Cité de l’Horloge","GarniAngle":"Garni d’Angle"}

def read(p):
    return json.loads(p.read_text(encoding="utf8"))

def font(n,serif=False):
    return ImageFont.truetype("C:/Windows/Fonts/"+("georgiab.ttf" if serif else "segoeui.ttf"),n)

def board(width,height,title,subtitle):
    im=Image.new("RGB",(width,height),PAPER)
    d=ImageDraw.Draw(im)
    d.rectangle((0,0,width,82),fill=INK)
    d.text((19,7),title,font=font(28,True),fill=PAPER)
    d.text((20,48),subtitle,font=font(17),fill=MUTED)
    return im,d

def image(name,mode="RGB"):
    with Image.open(PRE/(name+".png")) as src:
        return src.convert(mode)

def shape(design,view,px):
    src=image(f"profile-{design}-{view}","RGBA")
    src.thumbnail((px,px),Image.Resampling.LANCZOS)
    alpha=src.getchannel("A")
    assert alpha.getbbox()
    tile=Image.new("RGBA",(px,px),MUTED)
    tile.alpha_composite(src,((px-src.width)//2,(px-src.height)//2))
    return tile.convert("RGB")

def silhouettes(zone,new,old):
    cards=new+[(x,OLD_TITLES[x]+"  ·  Existing") for x in old]
    stride=326
    im,d=board(stride*4,99+186*((len(cards)+3)//4),ZONES[zone],
         "New and existing families at the same scale · street and side")
    for i,(design,title) in enumerate(cards):
        x=12+i%4*stride
        y=92+i//4*186
        d.text((x,y),title,font=font(15,True),fill=INK)
        for j,view in enumerate(("front","side")):
            im.paste(shape(design,view,141),(x+j*148,y+28))
    im.save(PRE/f"{zone}-silhouettes.png")

def closeup(design,title,house):
    im,d=board(1284,748,title,
       "Exported building at the street camera · matched daylight with the R11b house")
    main=image("close-"+design)
    im.paste(main,(0,120))
    im.paste(house,(844,120))
    d.text((15,91),"ROUND 12",font=font(17,True),fill=INK)
    d.text((857,91),"R11b · MAISON DE LA SERRE",font=font(15,True),fill=INK)
    im.save(OUT/(design+".jpg"),quality=94)

def main():
    OUT.mkdir(exist_ok=True)
    house=image("close-R11b-reference")
    house=house.crop((200,35,640,585))
    all_new=[]
    for zone in ZONES:
        review=read(PRE/f"{zone}-review.json")
        fresh=review["new"]
        all_new.extend(fresh)
        silhouettes(zone,fresh,review["old"])
        for name,title in fresh:
            closeup(name,title,house)
    im,d=board(1340,100+170*((len(all_new)+4)//5),"Round 12 at 128 pixels",
       "Each view occupies a true 128 × 128 pixel tile at a shared world scale")
    for i,(design,title) in enumerate(all_new):
        x=10+i%5*266
        y=89+i//5*170
        d.text((x,y),title,font=font(13,True),fill=INK)
        for j,view in enumerate(("front","side")):
            im.paste(shape(design,view,128),(x+j*130,y+25))
    im.save(PRE/"128px-sheet.png")
    assert len(all_new)==len(list(OUT.glob("*.jpg")))==23

if __name__=="__main__":
    main()
