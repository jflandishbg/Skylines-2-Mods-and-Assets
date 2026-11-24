from pathlib import Path
p=Path(__file__).resolve().parent/"legacy_r12.py"
s=p.read_text(encoding="utf8")
s=s.replace("ff=g.face((x.x,x.y),(y.x,y.y))","ff=nb.Face((x.x,x.y),(y.x,y.y))")
s=s.replace("ff=g.face((y.x,y.y),(x.x,x.y))","ff=nb.Face((y.x,y.y),(x.x,x.y))")
s=s.replace("ff=g.face(x,y)","ff=nb.Face(x,y)")
s=s.replace('if side in (1,3) and a["access"]!="Front":','if side in (1,3) and a["access"]!="Front" and not grade:')
s=s.replace('    if lod==0:\n        relief_for_wall','    if lod==0:\n        relief_for_wall')
x=s.index('        good.append((local(p),uv,n))')
s=s[:x]+'''        points=local(p)
        if lod<2 and abs(n.z)<.03 and max(v.z for v in p)-min(v.z for v in p)>.64:
            sample=center+tangent*.21*span-n*.013
            hit,_,_,dist=raw.ray_cast(sample,-n,.211)
            if hit is None:
                depth=.190
                inset=[v-n*depth for v in points]
                for j,(x,y) in enumerate(zip(points,points[1:]+points[:1])):
                    k=(j+1)%len(points)
                    inside=(y-x).cross(n)
                    if inside.length>.003:
                        h.body.polygon([x,y,inset[k],inset[j]],inside,"RevealStone")
                points=inset
        good.append((points,uv,n))
'''+s[x+len('        good.append((local(p),uv,n))\n'):]
p.write_text(s,encoding="utf8")
