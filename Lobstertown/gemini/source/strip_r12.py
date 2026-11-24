"""Apply the amended building-first brief to the Round 12 new designs."""
from pathlib import Path
S=Path(__file__).resolve().parent

def edit(file,changes):
    p=S/file
    s=p.read_text(encoding="utf8")
    for a,b in changes:
        assert a in s,(file,a)
        s=s.replace(a,b)
    p.write_text(s,encoding="utf8")

edit("r12_geometry.py",[
 ('    q=(c+2.45,c+7.42,d-9.44,d-4.70)\n    section(h,q,.047,3.32,1,"gable",2.48,front="blind",roof_mat="TinOxide")\n',''),
 ('    boat(h,c+1.08,d-7.82)\n',''),
 ('front="blind",roof_mat="TinOxide")','front="windows",roof_mat="TinOxide")'),
 ('WATER="CanalWater"','WATER="CanalWater"'),
])
edit("r12_flats.py",[
 ('    garden_mat="RoofGreen"\n    for x in (l+.91,r-.87):\n        q=(x-.58,x+.58,f+.41,b-.16)\n        slab(h,q,z+.28,z+.67,"TinGreen")\n        surface(h,(q[0]+.05,q[1]-.05,q[2]+.045,q[3]-.045),z+.675,garden_mat)\n        if h.lod==0:\n            detail.ivy(h,x,(f+b)/2,z+.68,.55)\n            detail.ivy(h,x+.27,(f+b)/2,z+.87,.40)\n',''),
 ('"GardenGlass"','"CourtGlass"'),
 ('    garden(h,(5.14,10.74,8.06,d-5.0))\n',''),
 ('            garden(h,q)','            yard(h,q)'),
 ('        if h.lod<2:\n            for x in (3.6,7.6,11.6):\n                beam(h,xyz(x,q[2]+.13,z+1.82),xyz(x+1.98,q[2]+.61,z+1.91),.022,IRON)\n',''),
 ('    for l,r in ((1.75,3.18),(5.22,10.78),(12.81,14.26)):\n        garden(h,(l,r,2.71,4.04))\n',''),
 ('    boat(h,12.62,7.93)\n',''),
 ('z+.016,"RoofGreen"','z+.016,"YardSetts"'),
 ('    section(h,p,.07,12.46,4,"shed",1.85,front="entry")','    section(h,p,.07,12.46,4,"shed",1.85,front="gallery")'),
])
edit("r12_geometry.py",[
 ('                if side==0 and front=="blind":','''                if side==0 and front=="gallery" and j==n//2 and i>0 and h.lod<2:
                    deck=(3.09,6.17,9.25)[i-1]
                    slots.append((face.length/2,min(1.15,face.length/n*.42),max(deck+.035,low+.04),high-.43,.11,True,False))
                    continue
                if side==0 and front=="blind":'''),
 ('"entry","shop","dock","hotel"','"entry","shop","dock","hotel","gallery"'),
])
edit("r12_specs.py",[
 ('with bridge and boathouse','with a stone bridge'),
 ('open street galleries with laundry lines','open street galleries with doorways'),
 ('Open street galleries with laundry lines','Open street galleries with doorways'),
 ('Ferryman’s stone steps, mooring and boat','Ferryman’s stone steps and mooring'),
 ('Lock-keepers’ flats and stepped waterside garden','Lock-keepers’ flats and stepped stone quay'),
])
edit("r12_atlas.py",[
 ('return Image.new("RGBA",size,(6,244,0,132))','return Image.new("RGBA",size,(0,240,0,34))'),
 ('47+16*wave+22*high,82+19*wave+24*high,88+21*wave+26*high','31+7*wave+8*high,55+9*wave+9*high,57+10*wave+10*high'),
])
