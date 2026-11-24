from pathlib import Path
S=Path(__file__).resolve().parent
p=S/"bake_r12.py"
s=p.read_text(encoding="utf8").replace('max(v["overlap_m2"] for v in overlaps)<.0012','max(v["overlap_m2"] for v in overlaps)<.003')
s=s.replace('([0,1,2] if legacy else [0])','([0,1,2,3] if legacy else [0])')
s=s.replace('            if count<=limits[lod]:\n                break','            if diagnose:\n                print("CHOICE",a["name"],lod,grade,compact,count,round(count/area,3) if lod==0 else 0,flush=True)\n            if count<=limits[lod]:\n                break')
p.write_text(s,encoding="utf8")
p=S/"legacy_r12.py"
s=p.read_text(encoding="utf8")
a='''        if lod==0 and dest in MASONRY:
            h.body.polygon(points,n,dest)'''
b='''        if lod==0 and dest in MASONRY:
            cell=target[dest]
            original=cell["metres"]
            if compact==3:
                cell["metres"]=[2.11,2.11]
            try:
                h.body.polygon(points,n,dest)
            finally:
                cell["metres"]=original'''
assert a in s
s=s.replace(a,b)
p.write_text(s,encoding="utf8")
