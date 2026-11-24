from pathlib import Path
S=Path(__file__).resolve().parent
def patch(f,rows):
    p=S/f
    t=p.read_text(encoding="utf8")
    for a,b in rows:
        assert a in t,(f,a)
        t=t.replace(a,b)
    p.write_text(t,encoding="utf8")

patch("r12_geometry.py",[
 ('6.30,8.81),.10,3.23,4,horseshoe=True','6.30,8.81),.10,3.23,3,horseshoe=True'),
 ('    slab(h,glass_p,.049,.36,STONE)','''    slab(h,glass_p,.049,.36,STONE)
    mid=front.length/2
    for x in (mid-.68,mid,mid+.68):
        block(h.body,front,x-.041,x+.041,.37,2.67,.084,.138,"BrownBrick")
    block(h.body,front,mid-.72,mid+.72,2.67,2.77,.086,.143,"BrownBrick")
    block(h.body,front,mid-.68,mid+.68,.38,.54,.084,.139,"BrownBrick")'''),
])
patch("r12_flats.py",[
 ('    round_wall(h,8.0,f-.15,.19,3.91,4.25,"Mustard",(24,12,8)[h.lod])','''    y=f+.42
    base=5.03
    slab(h,(7.22,8.78,y-.24,y+.36),base,base+.16,STONE)
    for x in (7.37,8.63):
        post(h,x,y+.04,base+.18,base+1.02,.16,STONE)
    cover(h,(7.15,8.85,y-.27,y+.40),base+1.05,"gable",.76,h.roof)
    segments=(24,12,8)[h.lod]
    rings=[[xyz(8+radius*math.cos(i*math.tau/segments),y+.014+radius*math.sin(i*math.tau/segments),base+z)
            for i in range(segments)] for radius,z in ((.23,.37),(.167,.43),(.119,.71),(.081,.81))]
    h.body.polygon(rings[0],DOWN,"Mustard")
    for lo,hi in zip(rings,rings[1:]):
        g.kit.ring_surfaces(h.body,lo,hi,"Mustard")
    h.body.polygon(rings[-1],UP,"Mustard")'''),
])
patch("r12_atlas.py",[
 ('("Brick085","Brick094","BuffBrick","RoofGreen")','("Brick085","Brick094","BuffBrick")'),
])
patch("r12_delivery.py",[
 ('        density=[a["tris_per_m2"]','        assert not back,(zone,back)\n        density=[a["tris_per_m2"]'),
])
