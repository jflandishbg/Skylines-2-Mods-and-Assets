"""Shared scan atlases for Z4, with exclusive paving and sign tiles."""
import json
import math
from pathlib import Path
import random
from PIL import Image,ImageDraw,ImageFont,ImageStat
from round5_specs import make


ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT.parent/"2026-11-08_round4-3"
REFERENCE="NA_PdDCaserneArcCanal"
MAPS=("BaseColor","Normal","MaskMap","ControlMask","Emissive")
BG={"BaseColor":(82,83,75,255),"Normal":(128,128,255,255),"MaskMap":(21,255,0,32),
    "ControlMask":(0,0,0,255),"Emissive":(0,0,0,255)}
FONT="C:/Windows/Fonts/georgiab.ttf"
SCANS=38
GROUNDS={"FrontFlags":(171,157,133),"CourtSetts":(119,119,108)}

def source_box(rect,dim):
    x,b,r,t=rect
    return tuple(round(v*dim) for v in (x,1-t,r,1-b))

def reserve(dim,slot,split=None):
    side=dim//7;pad=max(3,side//28)
    x=(slot%7)*side;y=(slot//7)*side
    if split is None:return (x+pad,y+pad,x+side-pad,y+side-pad)
    h=side//4
    y+=split*h
    return (x+pad,y+pad,x+side-pad,y+h-pad)

def spec(box,metres,dim):
    l,t,r,b=box
    return dict(uv=[l/dim,1-b/dim,r/dim,1-t/dim],metres=metres)

def sign(w,h,label,index):
    font=ImageFont.truetype(FONT,110)
    l,t,r,b=font.getbbox(label)
    mask=Image.new("L",(r-l+8,b-t+8))
    ImageDraw.Draw(mask).text((4-l,4-t),label,fill=255,font=font)
    mask=mask.crop(mask.getbbox()).resize((round(w*.91),round(h*.65)),Image.Resampling.LANCZOS)
    bg=("#303e34","#3d3432","#30373e","#5b483c")[index%4]
    img=Image.new("RGBA",(w,h),bg)
    pen=ImageDraw.Draw(img)
    for y in (round(h*.075),round(h*.93)):
        pen.line((2,y,w-3,y),fill="#a58652",width=max(1,h//32))
    img.paste((206,174,104,255),((w-mask.width)//2,(h-mask.height)//2),mask)
    return img

def paving(w,h,key,metres):
    img=Image.new("RGBA",(w,h),(99,94,82,255))
    d=ImageDraw.Draw(img)
    rng=random.Random(1615 if key=="FrontFlags" else 4981)
    nx=max(2,round(metres[0]/(.95 if key=="FrontFlags" else .40)))
    ny=max(2,round(metres[1]/(.58 if key=="FrontFlags" else .29)))
    dx,dy=w/nx,h/ny
    gap=min(1.,.17*min(dx,dy))
    for j in range(ny):
        for i in range(-1,nx):
            x=(i+.5*(j%2))*dx;y=j*dy
            tone=rng.randint(-11,11)
            d.rectangle((x+gap,y+gap,x+dx-gap,y+dy-gap),fill=tuple(c+tone for c in GROUNDS[key]))
    return img

def dial(w,h):
    im=Image.new("RGBA",(w,h),"#435049")
    d=ImageDraw.Draw(im);x=w/2;y=h/2
    for frac,col in ((.47,"#b09c70"),(.42,"#e9dfc7")):
        d.ellipse((x-w*frac,y-h*frac,x+w*frac,y+h*frac),fill=col)
    for i in range(12):
        a=i*math.tau/12
        d.line((x+w*.34*math.sin(a),y-h*.34*math.cos(a),x+w*.39*math.sin(a),y-h*.39*math.cos(a)),
               fill="#484a3d",width=max(1,w//90))
    d.line((x-w*.18,y-h*.14,x,y,x+w*.22,y-h*.15),fill="#302c23",width=max(1,w//35))
    return im

def tone_scan(im,box,target):
    patch=im.crop(box)
    channels=patch.split()
    mean=ImageStat.Stat(patch).mean
    remapped=[channel.point([max(0,min(255,round(v*goal/max(1,avg)))) for v in range(256)])
              for channel,goal,avg in zip(channels,target,mean)]
    im.paste(Image.merge("RGBA",(*remapped,channels[3])),box[:2])

def tile_repeat(im,box,factor):
    l,t,r,b=box
    tile=im.crop(box)
    for j in range(factor):
        for i in range(factor):
            a,z=l+round((r-l)*i/factor),t+round((b-t)*j/factor)
            c,u=l+round((r-l)*(i+1)/factor),t+round((b-t)*(j+1)/factor)
            im.paste(tile.resize((c-a,u-z),Image.Resampling.LANCZOS),(a,z))

def main():
    plans=list(make())
    designs=list({a["design"]:a for a in plans if a["colourway"]=="A"}.values())
    assert len(designs)==16
    prev=json.loads((SOURCE/"source"/"kit"/"atlas_layout.json").read_text(encoding="utf8"))
    layout={"lods":{}}
    for j,k in enumerate(("main","_LOD1","_LOD2")):
        suffix="" if j==0 else k
        dim=4096>>j
        cells={key:cell.copy() for key,cell in list(prev["lods"][k].items())[:SCANS]}
        repeat={}
        for key,cell in cells.items():
            if j==0:continue
            factor=3 if j==1 and key in {"Dressed","Cream","Ashlar","Greystone","StoneBase","Render","RenderOchre","RenderSage","Brick085","Brick094","Brick074","SlateDark","SlateGreen","SlateBrown"} else 6 if j==2 else 1
            if factor>1:
                repeat[key]=factor
                cell["metres"]=[x*factor for x in cell["metres"]]
        rects={a["design"]:reserve(dim,38+i//4,i%4) for i,a in enumerate(designs)}
        for key,rect in rects.items():cells["Sign_"+key]=spec(rect,[7,1],dim)
        square=reserve(dim,42)
        sw,sh=(square[2]-square[0])//4,(square[3]-square[1])//4
        for i,a in enumerate(designs):
            x,y=square[0]+(i%4)*sw,square[1]+(i//4)*sh
            cells["Address_"+a["design"]]=spec((x+2,y+2,x+sw-2,y+sh-2),[.2,.15],dim)
        for i,key in enumerate(GROUNDS,43):
            cells[key]=spec(reserve(dim,i),([7,7],[12,12],[38,38])[j],dim)
        cells["MatteDial"]=spec(reserve(dim,45),[2,2],dim)
        for slot,key in enumerate(("SootUnder","ShutterFaded","PatchedLime"),46):
            cells[key]=spec(reserve(dim,slot),[2,2] if slot<48 else [4,4],dim)
        layout["lods"][k]=cells
        ref=SOURCE/"bake"/REFERENCE
        for kind in MAPS:
            if kind=="Emissive":im=Image.new("RGBA",(dim,dim),BG[kind])
            else:
                with Image.open(ref/f"{REFERENCE}{suffix}_{kind}.png") as source:
                    im=source.convert("RGBA")
                for key,factor in repeat.items():
                    tile_repeat(im,source_box(cells[key]["uv"],dim),factor)
                if kind=="BaseColor":
                    for key,target in {"TinFlat":(76,87,97),"Brick085":(158,91,67),
                                       "Brick094":(120,62,57),"Brick074":(175,105,87)}.items():
                        tone_scan(im,source_box(cells[key]["uv"],dim),target)
                pen=ImageDraw.Draw(im)
                side=dim//7
                for slot in range(38,49):
                    x=slot%7*side;y=slot//7*side
                    pen.rectangle((x,y,x+side-1,y+side-1),fill=BG[kind])
                for i,a in enumerate(designs):
                    key=a["design"];l,t,r,b=rects[key]
                    if kind=="BaseColor":
                        im.paste(sign(r-l,b-t,a["inscription"],i),(l,t))
                        if j==0:
                            check=ROOT/"previews";check.mkdir(exist_ok=True)
                            im.crop((l,t,r,b)).save(check/f"{key}-inscription.png")
                if kind=="BaseColor":
                    for i,a in enumerate(designs):
                        l,t,r,b=source_box(cells["Address_"+a["design"]]["uv"],dim)
                        im.paste(sign(r-l,b-t,a["address_number"],i),(l,t))
                for key in GROUNDS:
                    l,t,r,b=source_box(cells[key]["uv"],dim)
                    if kind=="BaseColor":
                        im.paste(paving(r-l,b-t,key,cells[key]["metres"]),(l,t))
                for key,source_key,target in (("SootUnder","Brick094",(95,65,58)),
                                              ("ShutterFaded","ClapSage",(135,148,124)),
                                              ("PatchedLime","Render",(183,176,155))):
                    source_rect=source_box(cells[source_key]["uv"],dim)
                    l,t,r,b=source_box(cells[key]["uv"],dim)
                    im.paste(im.crop(source_rect).resize((r-l,b-t),Image.Resampling.LANCZOS),(l,t))
                    if kind=="BaseColor":
                        tone_scan(im,(l,t,r,b),target)
                l,t,r,b=source_box(cells["MatteDial"]["uv"],dim)
                if kind=="BaseColor":im.paste(dial(r-l,b-t),(l,t))
                if kind=="MaskMap":pen.rectangle((l,t,r-1,b-1),fill=(18,255,0,20))
            for zone in ("Z4",):
                owner=next(a["name"] for a in plans if a["zone_key"]==zone)
                folder=ROOT/f"import_{zone}"/owner;folder.mkdir(parents=True,exist_ok=True)
                path=folder/f"{owner}{suffix}_{kind}.png"
                im.save(path,compress_level=3)
    layout["order"]=list(layout["lods"]["main"])
    (ROOT/"source"/"kit"/"atlas_layout.json").write_text(json.dumps(layout,indent=2)+"\n",encoding="utf8")
    print("ATLASES_READY",flush=True)

if __name__=="__main__":main()
