from pathlib import Path
S=Path(__file__).resolve().parent
p=S/"legacy_r12.py"
s=p.read_text(encoding="utf8")
s=s.replace('    raw_faces=[]','    raw_faces=[]\n    raw_tiles=[]').replace('        raw_vertices.extend(p)','        raw_vertices.extend(p)\n        raw_tiles.append(dest)')
x=s.index('        center=midpoint(p)')
y=s.index('        good.append',x)
s=s[:x]+'''        center=midpoint(p)
        tangent=Vector((0,0,1)).cross(n).normalized()
        span=max(abs((v-center).dot(tangent)) for v in p)
        blocked=0
        for shift in (-.65,-.32,.27,.62):
            origin=center+tangent*(shift*span)+n*.019
            hit,normal,j,dist=raw.ray_cast(origin,n,.63)
            if hit is not None and normal.dot(n)>.94 and raw_tiles[j] not in {"Iron","TinGreen","Green","Cream","Dressed","Mustard","GreyBlue","CourtGlass"}:
                blocked+=1
        if blocked>=3 and lod<2:
            continue
'''+s[y:]
s=s.replace('        elif lod<2:\n            h.body.polygon(p,n,"GreyBlue")','        elif lod<2:\n            h.body.polygon([q+n*.006 for q in p],n,"GreyBlue")')
s=s.replace('d=.048 if style==0 else .034','d=.084 if style==0 else .064')
p.write_text(s,encoding="utf8")
p=S/"r12_geometry.py"
s=p.read_text(encoding="utf8")
s=s.replace('    section(h,p,2.86,9.11,2,"hip",3.45,over=.25)','    h.compact_trim=True\n    section(h,p,2.86,9.11,2,"hip",3.45,over=.25)\n    h.compact_trim=False')
p.write_text(s,encoding="utf8")
p=S/"bake_r12.py"
s=p.read_text(encoding="utf8")
s=s.replace('            if a["design"] in seen and zone!="Z1B":','            if (len(args)>1 and a["design"] not in args) or a["design"] in seen and zone!="Z1B":')
p.write_text(s,encoding="utf8")
