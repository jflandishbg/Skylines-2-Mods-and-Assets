from pathlib import Path
S=Path(__file__).resolve().parent
p=S/"legacy_r12.py"
s=p.read_text(encoding="utf8")
s=s.replace('        ff=nb.Face(x,y)\n        if ff.length<2.3:', '        if a.get("compact",0)>=4 and side!=0:\n            continue\n        ff=nb.Face(x,y)\n        if ff.length<2.3:')
s=s.replace('            if compact==3:\n                cell["metres"]=[2.11,2.11]','            if compact>=3:\n                cell["metres"]=[2.11,2.11]')
s=s.replace('and (compact<2 or i%2==0))','and (compact<2 or i%(2 if compact<5 else 3)==0))')
s=s.replace('if lod==0:\n        relief_for_wall','if lod==0 and compact<5:\n        relief_for_wall')
p.write_text(s,encoding="utf8")
p=S/"bake_r12.py"
s=p.read_text(encoding="utf8").replace('([0,1,2,3] if legacy else [0])','([0,1,2,3,4,5] if legacy else [0])')
p.write_text(s,encoding="utf8")
